"""The optimizer: rider data → a fin the rider will want (docs/PHYSICS.md §10).

This is the piece the whole `fingen` library exists to feed. The geometry
(`params`/`outline`/`foil`/`loft`), the fast physics (`hydro`/`flex`/`sizing`)
and the surfer-language objective (`spider`) are all upstream of one question:
given a rider, what fin parameters land closest to what that rider wants while
staying inside the absolute constraints? This module answers it.

Three moving parts, all tier-0 and analytic (no OCCT in the hot loop — every
`evaluate` is milliseconds, so a few-thousand-evaluation search is seconds):

1. RiderSpec — the input. Weight, skill, speed, config, material, and a
   *derived* spider target: a documented mapping from rider inputs to the six
   0..1 axis wishes (heavier/faster/more-skilled riders weight drive+hold;
   beginners weight forgiveness/pivot/release). An explicit `spider_targets`
   override merges over the derived defaults.

2. evaluate(fin, rider) — the objective. Hard gates first, cheap-to-expensive
   (sizing area/force/stress corridor, then the flex report's structural
   margins), each failure a GRADED penalty so the search has a gradient toward
   feasibility rather than a cliff. Then the spider axes at the rider's working
   point, washed out by the flex model's lift knockdown and knocked down by the
   config's measured multi-fin interference environment, scored as a weighted
   quadratic distance to the rider's targets. Lower is better.

3. optimize(rider) — the search. CMA-ES in two stages: level-1 sliders first
   (the human/template interface), then the level-2 Bézier control-point
   offsets (`le_dx`/`te_dx`) unlocked from the stage-A optimum with a tight
   sigma, plus grooves when the rider profile asks for flex/forgiveness. Decode
   is ValueError→penalty (the production contract), deterministic under seed.

The interference environment (constant `_FALK_REAR_DEFICIT`) is the measured
thruster anchor from bench/falk/thruster-run-summary.json: the aft (center) fin
sits in the forward pair's downwash and makes measurably less side force than a
front fin. See `falk_rear_deficit`/`interference_factor` for the mapping.
"""

from __future__ import annotations

import functools
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from fingen import spider
from fingen.flex import FlexReport, flex_report
from fingen.hydro import RHO_SEAWATER, lift_curve_slope, stall_alpha_deg
from fingen.outline import metrics, planform
from fingen.params import (
    FinConfig,
    FinParams,
    FoilFamily,
    FoilParams,
    GrooveParams,
    GrooveSurface,
    OutlineParams,
)
from fingen.sizing import FORCE_SF, AnchorSheet, Skill, anchor, check_anchor

# --- objective tuning constants ---------------------------------------------
# Structural floors the flex report is gated against. f_wet 8 Hz keeps the wet
# fundamental clear of the O(1 Hz) wave/maneuver forcing band (flexy commercial
# fins sit ~10 Hz [Krz24]); divergence must clear the working speed with margin
# (the tow-in envelope motivates the >15 m/s screen in test_flex).
F_WET_MIN_HZ = 8.0
DIVERGENCE_SF = 1.6
# Penalties are fractional margins (O(0.1-1)); the feasible objective is a
# weighted quadratic distance in [0, ~2]. Scale infeasibility far above it so a
# single violated constraint dominates any score gain, but keep it a slope, not
# a cliff — the search needs a gradient back toward the feasible set.
PENALTY_WEIGHT = 100.0
# Undecodable vectors (level-2 offsets that cross the planform, or groove bands
# that fail the FinParams checks) return this flat, larger-than-any-feasible
# value: the search simply routes around the pocket.
DECODE_PENALTY = 1.0e4

# --- rider → working-point mapping ------------------------------------------
# Design riding speed per skill (m/s): the sizing default 6.4 [Forsyth24] is the
# intermediate anchor; cruisers ride slower, advanced/pro faster (the working
# point q scales the area corridor and every lift-dependent axis).
_SKILL_SPEED_MS = {
    Skill.CRUISER: 5.5,
    Skill.INTERMEDIATE: 6.4,
    Skill.ADVANCED: 7.5,
    Skill.PRO: 8.5,
}


def _skill_norm(skill: Skill) -> float:
    """Skill on 0..1 from its design bank angle (CRUISER 0 … PRO 1)."""
    return (skill.value - Skill.CRUISER.value) / (Skill.PRO.value - Skill.CRUISER.value)


def _weight_norm(weight_kg: float) -> float:
    """Rider mass on 0..1 over a 55-100 kg shortboard band (clipped)."""
    return float(min(max((weight_kg - 55.0) / (100.0 - 55.0), 0.0), 1.0))


def default_spider_targets(weight_kg: float, skill: Skill) -> dict[str, float]:
    """Derive the rider's six 0..1 axis wishes from weight and skill.

    A documented, deliberately simple prior (NOT physics — the physics lives in
    `evaluate`'s scoring). Two drivers: skill `s` (bank-angle intensity) and
    mass `w`. Heavier and more aggressive riders load the fin harder, so they
    weight the extensive/driving axes (drive, hold, speed); lighter and less
    aggressive riders want a forgiving, loose, pivoty fin. The coefficients are
    calibrated so a mid rider (75 kg intermediate) lands near mid-fleet on every
    axis and the extremes push sensibly:

        speed       0.40 + 0.30·s + 0.10·w    faster riders want low drag
        drive       0.45 + 0.30·s + 0.15·w    L/D-at-load rises with skill+mass
        hold        0.40 + 0.30·s + 0.25·w    max side force scales with both
        pivot       0.60 − 0.30·s − 0.10·w    tight pivot favours light/casual
        release     0.35 + 0.40·s             drawn-out release is an advanced want
        forgiveness 0.75 − 0.55·s − 0.10·w    beginners need it; pros trade it away

    Clipped to [0.05, 0.95] so no axis is an unreachable 0 or 1.
    """
    s = _skill_norm(skill)
    w = _weight_norm(weight_kg)
    raw = {
        "speed": 0.40 + 0.30 * s + 0.10 * w,
        "drive": 0.45 + 0.30 * s + 0.15 * w,
        "hold": 0.40 + 0.30 * s + 0.25 * w,
        "pivot": 0.60 - 0.30 * s - 0.10 * w,
        "release": 0.35 + 0.40 * s,
        "forgiveness": 0.75 - 0.55 * s - 0.10 * w,
    }
    return {axis: float(min(0.95, max(0.05, raw[axis]))) for axis in spider.AXES}


@dataclass
class RiderSpec:
    """The optimizer's input: who the fin is for and how it is mounted.

    speed_ms defaults from skill; config selects the fin's family (single →
    symmetric center fin, everything else → flat-inside side fin) and its
    interference environment. spider_targets, when given, MERGES over the
    derived defaults (pass just the axes you want to override).
    """

    weight_kg: float
    skill: Skill = Skill.INTERMEDIATE
    speed_ms: float | None = None
    config: FinConfig = FinConfig.THRUSTER
    material: str = "pet-cf"
    spider_targets: dict[str, float] | None = None

    def __post_init__(self) -> None:
        if not 30.0 <= self.weight_kg <= 160.0:
            raise ValueError(f"weight_kg {self.weight_kg} outside 30-160 kg")
        if self.spider_targets is not None:
            unknown = set(self.spider_targets) - set(spider.AXES)
            if unknown:
                raise ValueError(f"unknown spider target axes: {sorted(unknown)}")

    @property
    def speed(self) -> float:
        """Resolved design riding speed (m/s)."""
        return self.speed_ms if self.speed_ms is not None else _SKILL_SPEED_MS[self.skill]

    def resolved_targets(self) -> dict[str, float]:
        """Derived defaults with any explicit override merged over them."""
        targets = default_spider_targets(self.weight_kg, self.skill)
        if self.spider_targets:
            targets.update({a: float(v) for a, v in self.spider_targets.items()})
        return targets


def family_for_config(config: FinConfig) -> FoilFamily:
    """The blade family the optimizer builds for a config: a symmetric center
    fin for a single, a flat-inside side fin for every set (the dominant,
    chiral blade exported both hands)."""
    return FoilFamily.SYMMETRIC if config is FinConfig.SINGLE else FoilFamily.FLAT_INSIDE


# --- multi-fin interference environment (bench/falk) -------------------------
# Digitized from bench/falk/thruster-run-summary.json: a fingen THRUSTER swept
# in leeway, per-fin CFD side force. The center fin is the REAR member (rides
# the stringer aft of the forward side pair) and reads a side-force DEFICIT vs
# the dominant (leeward) front fin — the measured multi-fin interference the
# single-fin spider/hydro model cannot see. deficit(α) = 1 − CL_center/CL_front
# where CL_front is the more-loaded of the two fronts. Reproduces the [Falk20]
# Fig 10 anchor (front→rear ≈ 23% at the 20° lift peak) and grows into the
# post-peak wake shadow. Baked as the portable authority (the JSON is not
# packaged); regenerate with scripts/falk_thruster.py on the EPYC.
_FALK_ANGLE_DEG = np.array([0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0])
_FALK_REAR_DEFICIT = np.array([0.00, 0.296, 0.239, 0.223, 0.262, 0.276, 0.416])
# Configs whose optimized blade lives in a downwash environment (a rear member
# exists behind another fin). SINGLE/TWIN have no aft-shadowed member here, so
# they run at the isolated (factor 1.0) spider model; QUAD reuses the thruster
# curve as the best available proxy (no quad-specific summary yet — documented
# gap, conservative).
_INTERFERENCE_CONFIGS = frozenset(
    {FinConfig.THRUSTER, FinConfig.TWO_PLUS_ONE, FinConfig.QUAD})


def falk_rear_deficit(alpha_deg: float) -> float:
    """Measured rear-fin side-force deficit fraction at working leeway α."""
    a = min(max(abs(alpha_deg), 0.0), float(_FALK_ANGLE_DEG[-1]))
    return float(np.interp(a, _FALK_ANGLE_DEG, _FALK_REAR_DEFICIT))


def interference_factor(config: FinConfig, alpha_deg: float) -> float:
    """Lift-axis multiplier (0..1] for operating inside a set at working α.

    The single-fin spider model scores an isolated blade; a fin in a set makes
    less side force per fin (downwash interference). For the interference
    configs we apply the measured rear-fin deficit as the environment factor —
    the honest, data-backed magnitude of that loss — leaving isolated configs
    at 1.0.
    """
    if config in _INTERFERENCE_CONFIGS:
        return 1.0 - falk_rear_deficit(alpha_deg)
    return 1.0


# --- normalization against the reference fleet -------------------------------


@functools.lru_cache(maxsize=16)
def _fleet_raw(speed_key: float) -> tuple[tuple[tuple[str, float], ...], ...]:
    """Reference-fleet raw axis values at `speed_key`, cached (the fleet is
    fixed; recomputing six fins' raw scores every evaluate would blow the
    budget). Returned as hashable sorted-item tuples."""
    fleet = spider.reference_fleet()
    return tuple(tuple(sorted(spider.raw_scores(f, speed_key).items()))
                 for f in fleet.values())


def _normalize(raw: dict[str, float], fleet: tuple) -> dict[str, float]:
    """0..100 per axis, interpolated rank against the fleet (spider.py's rule)."""
    fleet_dicts = [dict(f) for f in fleet]
    out = {}
    for axis in spider.AXES:
        values = np.sort([f[axis] for f in fleet_dicts])
        ranks = np.linspace(0.0, 100.0, len(values))
        out[axis] = float(np.interp(raw[axis], values, ranks))
    return out


# --- the objective -----------------------------------------------------------


@dataclass
class EvalResult:
    """One fin scored for one rider. objective is what the search minimizes:
    the weighted quadratic spider distance plus the scaled penalty sum (0 when
    feasible). Lower is better."""

    objective: float
    distance: float
    penalty: float
    feasible: bool
    spider_predicted: dict[str, float]  # 0..100, washout+interference applied
    spider_target: dict[str, float]  # 0..100 (targets ×100, for plotting)
    flex: FlexReport
    margins: dict[str, float]
    penalties: dict[str, float]
    issues: list[str]


def evaluate(fin: FinParams, rider: RiderSpec) -> EvalResult:
    """Score `fin` for `rider`. <= 50 ms: all tier-0 analytic, no OCCT.

    Gates, cheap-to-expensive, each a graded (fractional-margin) penalty:
      * sizing area corridor, steady side-force capacity, mounting base min;
      * flex structural: bending SF >= 1 (incl. the groove band via stress_max),
        wet fundamental >= 8 Hz, divergence speed clear of the working speed.
    Then the six spider axes at the rider's working point, with the flex lift
    knockdown (washout) and the config interference factor applied to the
    lift-dependent axes (hold, drive), scored as a weighted quadratic distance
    to the rider's targets.
    """
    speed = rider.speed
    sheet: AnchorSheet = anchor(rider.weight_kg, rider.skill, design_speed=speed,
                                config=rider.config, material=rider.material)

    penalties: dict[str, float] = {}
    m = metrics(fin.outline)
    area = m.area
    if area < sheet.area_min_mm2:
        penalties["area_low"] = (sheet.area_min_mm2 - area) / sheet.area_min_mm2
    if area > sheet.area_max_mm2:
        penalties["area_high"] = (area - sheet.area_max_mm2) / sheet.area_max_mm2

    slope, ar_eff = lift_curve_slope(fin)
    a_break = stall_alpha_deg(ar_eff)
    q = 0.5 * RHO_SEAWATER * speed**2
    f_capacity = q * area * 1e-6 * slope * math.radians(a_break)
    req = sheet.force_work_n * FORCE_SF
    if f_capacity < req:
        penalties["capacity"] = (req - f_capacity) / req
    if fin.outline.base < sheet.base_min_mm:
        penalties["base_min"] = ((sheet.base_min_mm - fin.outline.base)
                                 / max(sheet.base_min_mm, 1.0))

    # Structural gates: stress at the transient PEAK load, washout/frequency at
    # the working speed (the knockdown is load-independent — see flex.py).
    flex = flex_report(fin, sheet.force_peak_n, speed, material=rider.material)
    stress_sf = flex.stress_margin
    if stress_sf < 1.0:
        penalties["stress"] = 1.0 - stress_sf
    if flex.f_wet_hz < F_WET_MIN_HZ:
        penalties["f_wet"] = (F_WET_MIN_HZ - flex.f_wet_hz) / F_WET_MIN_HZ
    div_req = DIVERGENCE_SF * speed
    if flex.divergence_speed_ms < div_req:
        penalties["divergence"] = (div_req - flex.divergence_speed_ms) / div_req

    penalty_sum = float(sum(penalties.values()))
    feasible = penalty_sum <= 1e-9

    # Raw spider axes, then washout + interference on the lift-magnitude axes.
    raw = spider.raw_scores(fin, speed)
    cl_work = min(spider.WORK_FORCE_N / (q * area * 1e-6),
                  0.95 * slope * math.radians(a_break))
    alpha_work = math.degrees(cl_work / slope)
    washout = max(0.0, 1.0 + flex.lift_knockdown)  # knockdown < 0 = lift lost
    env = interference_factor(rider.config, alpha_work)
    for axis in ("hold", "drive"):
        raw[axis] *= washout * env

    predicted = _normalize(raw, _fleet_raw(round(speed, 2)))
    targets = rider.resolved_targets()
    distance = 0.0
    for axis in spider.AXES:
        tgt = targets[axis]
        weight = 1.0 + abs(tgt - 0.5)  # axes pushed to extremes matter more
        distance += weight * (predicted[axis] / 100.0 - tgt) ** 2

    objective = distance + PENALTY_WEIGHT * penalty_sum
    margins = {
        "stress_sf": stress_sf,
        "f_wet_hz": flex.f_wet_hz,
        "divergence_ms": flex.divergence_speed_ms,
        "area_mm2": area,
        "area_min_mm2": sheet.area_min_mm2,
        "area_max_mm2": sheet.area_max_mm2,
        "capacity_n": f_capacity,
        "capacity_req_n": req,
        "alpha_work_deg": alpha_work,
        "washout_pct": 100.0 * flex.lift_knockdown,
        "env_factor": env,
        "tip_deflection_mm": flex.tip_deflection_mm,
    }
    issues = check_anchor(fin, sheet)
    if stress_sf < 1.0:
        issues.append(f"flex bending SF {stress_sf:.2f} < 1.0 at the peak load")
    if flex.f_wet_hz < F_WET_MIN_HZ:
        issues.append(f"wet fundamental {flex.f_wet_hz:.1f} Hz < {F_WET_MIN_HZ:.0f} Hz")
    if flex.divergence_speed_ms < div_req:
        issues.append(f"divergence speed {flex.divergence_speed_ms:.1f} m/s below "
                      f"{div_req:.1f} m/s margin")
    return EvalResult(
        objective=objective,
        distance=distance,
        penalty=penalty_sum,
        feasible=feasible,
        spider_predicted=predicted,
        spider_target={a: 100.0 * targets[a] for a in spider.AXES},
        flex=flex,
        margins=margins,
        penalties=penalties,
        issues=issues,
    )


# --- design-vector decode ----------------------------------------------------
# Level-1 sliders, in the params-validation order/bounds. The search works in a
# normalized [0,1]^n box; decode maps each gene back to its physical range.
_SLIDER_BOUNDS: tuple[tuple[str, float, float], ...] = (
    ("depth", 40.0, 300.0),
    ("base", 40.0, 250.0),
    ("sweep", 0.0, 60.0),
    ("tip_width_ratio", 0.05, 0.6),
    ("le_fullness", 0.0, 1.0),
    ("te_shape", -1.0, 1.0),
    ("thickness_ratio", 0.04, 0.15),
    ("thickness_tip_factor", 0.5, 1.2),
)
_N_SLIDERS = len(_SLIDER_BOUNDS)
# Level-2 offsets: 6 le + 6 te, each ±_OFFSET_FRAC·base. Kept just inside the
# params bound (0.3·base) so a decoded vector is always in range for the offset
# check; a level-2 shape that crosses the planform still fails in planform() and
# is caught as a ValueError→penalty.
_OFFSET_FRAC = 0.29
_N_OFFSETS = 12
# Groove genes (relaxed-continuous, rounded): count, depth_ratio, span_start.
# length/pitch/width/surface are fixed to a sensible printable band so the band
# fits inside the depth for typical fins (edge cases fail → penalty).
_GROOVE_BOUNDS: tuple[tuple[str, float, float], ...] = (
    ("count", 0.0, 6.49),
    ("depth_ratio", 0.10, 0.50),
    ("span_start", 0.18, 0.55),
)
_N_GROOVES = len(_GROOVE_BOUNDS)


def _clip01(v: float) -> float:
    return float(min(1.0, max(0.0, v)))


def _decode(x: np.ndarray, config: FinConfig, *, use_offsets: bool,
            use_grooves: bool) -> FinParams:
    """Normalized vector → FinParams. Raises ValueError for combinations the
    params/planform checks reject (the search treats that as a penalty)."""
    vals = {name: lo + _clip01(x[i]) * (hi - lo)
            for i, (name, lo, hi) in enumerate(_SLIDER_BOUNDS)}
    base = vals["base"]

    idx = _N_SLIDERS
    if use_offsets:
        le_dx = tuple((2.0 * _clip01(x[idx + j]) - 1.0) * _OFFSET_FRAC * base
                      for j in range(6))
        te_dx = tuple((2.0 * _clip01(x[idx + 6 + j]) - 1.0) * _OFFSET_FRAC * base
                      for j in range(6))
        idx += _N_OFFSETS
    else:
        le_dx = te_dx = (0.0,) * 6

    grooves = GrooveParams()
    if use_grooves:
        g = {name: lo + _clip01(x[idx + i]) * (hi - lo)
             for i, (name, lo, hi) in enumerate(_GROOVE_BOUNDS)}
        count = int(round(g["count"]))
        if count > 0:
            grooves = GrooveParams(count=count, length=55.0, pitch=6.0, width=3.0,
                                   depth_ratio=g["depth_ratio"],
                                   span_start=g["span_start"],
                                   surface=GrooveSurface.OUTER)

    outline = OutlineParams(depth=vals["depth"], base=base, sweep=vals["sweep"],
                            tip_width_ratio=vals["tip_width_ratio"],
                            le_fullness=vals["le_fullness"], te_shape=vals["te_shape"],
                            le_dx=le_dx, te_dx=te_dx)
    # Force the planform check now (edge crossing from level-2 offsets) so the
    # caller's ValueError→penalty contract catches it before any scoring.
    planform(outline)
    foil = FoilParams(family=family_for_config(config),
                      thickness_ratio=vals["thickness_ratio"])
    return FinParams(outline=outline, foil=foil,
                     thickness_tip_factor=vals["thickness_tip_factor"], grooves=grooves)


def _x0_sliders(config: FinConfig) -> list[float]:
    """Stage-A start: the template default fin, back-projected to [0,1] genes."""
    template = FinParams(foil=FoilParams(family=family_for_config(config)))
    src = {
        "depth": template.outline.depth,
        "base": template.outline.base,
        "sweep": template.outline.sweep,
        "tip_width_ratio": template.outline.tip_width_ratio,
        "le_fullness": template.outline.le_fullness,
        "te_shape": template.outline.te_shape,
        "thickness_ratio": template.foil.thickness_ratio,
        "thickness_tip_factor": template.thickness_tip_factor,
    }
    return [(src[name] - lo) / (hi - lo) for name, lo, hi in _SLIDER_BOUNDS]


def groove_trigger(rider: RiderSpec) -> bool:
    """Stage B unlocks grooves only when the rider profile weights flex: a high
    forgiveness or release target. Grooves add tip flex and +11% L/D at high
    incidence [Els22] — a forgiveness/looseness feature, not a driver's."""
    t = rider.resolved_targets()
    return t["forgiveness"] >= 0.6 or t["release"] >= 0.6


# --- the search --------------------------------------------------------------


@dataclass
class OptimizationResult:
    """The optimizer's output: the winning blade, its full evaluation, the
    convergence history (best-so-far per generation across both stages) and the
    stage-A/B boundary index into that history."""

    fin: FinParams
    result: EvalResult
    rider: RiderSpec
    history: list[float]
    stage_boundary: int
    n_evals: int
    seed: int
    grooves_enabled: bool


_SIGMA_A = 0.25  # broad in the normalized box: level-1 sliders explore widely
_SIGMA_B = 0.08  # tight: refine near the stage-A optimum, gently open offsets


def _run_cma(rider: RiderSpec, x0: list[float], sigma0: float, *, use_offsets: bool,
             use_grooves: bool, budget: int, seed: int
             ) -> tuple[np.ndarray, float, list[float], int]:
    """One CMA-ES stage in the [0,1]^n box. Returns (best_x, best_f, best-so-far
    history per generation, evals spent)."""
    import cma

    config = rider.config

    def objective(x: np.ndarray) -> float:
        try:
            fin = _decode(np.asarray(x), config, use_offsets=use_offsets,
                          use_grooves=use_grooves)
        except ValueError:
            return DECODE_PENALTY
        return evaluate(fin, rider).objective

    es = cma.CMAEvolutionStrategy(list(x0), sigma0, {
        "bounds": [0.0, 1.0],
        "seed": seed + 1,  # cma treats 0/None as time-randomized
        "maxfevals": budget,
        "verbose": -9,
    })
    best_x = np.asarray(x0, dtype=float)
    best_f = float("inf")
    history: list[float] = []
    n_evals = 0
    while not es.stop() and n_evals < budget:
        xs = es.ask()
        fs = [objective(x) for x in xs]
        es.tell(xs, fs)
        n_evals += len(xs)
        i = int(np.argmin(fs))
        if fs[i] < best_f:
            best_f = float(fs[i])
            best_x = np.asarray(xs[i], dtype=float)
        history.append(best_f)
    return best_x, best_f, history, n_evals


def optimize(rider: RiderSpec, budget_evals: int = 4000, seed: int = 0
             ) -> OptimizationResult:
    """Search the design space for the fin closest to the rider's targets.

    Stage A optimizes the eight level-1 sliders (CMA-ES, broad sigma). Stage B
    unlocks the twelve level-2 le_dx/te_dx Bézier offsets from the stage-A
    optimum with a tight sigma, plus grooves when `groove_trigger` fires. Decode
    is ValueError→penalty; deterministic under `seed`.
    """
    budget_a = max(int(budget_evals * 0.6), 1)
    budget_b = max(budget_evals - budget_a, 0)
    use_grooves = groove_trigger(rider)

    xa, fa, hist_a, na = _run_cma(rider, _x0_sliders(rider.config), _SIGMA_A,
                                  use_offsets=False, use_grooves=False,
                                  budget=budget_a, seed=seed)
    fin_a = _decode(xa, rider.config, use_offsets=False, use_grooves=False)

    best_fin = fin_a
    hist_b: list[float] = []
    nb = 0
    if budget_b > 0:
        x0_b = list(xa) + [0.5] * _N_OFFSETS + ([0.5] * _N_GROOVES if use_grooves else [])
        xb, fb, hist_b, nb = _run_cma(rider, x0_b, _SIGMA_B, use_offsets=True,
                                      use_grooves=use_grooves, budget=budget_b, seed=seed)
        if fb <= fa:
            try:
                best_fin = _decode(xb, rider.config, use_offsets=True,
                                   use_grooves=use_grooves)
            except ValueError:
                best_fin = fin_a

    # Best-so-far across both stages (a monotone convergence curve for the card).
    combined: list[float] = []
    run = float("inf")
    for h in hist_a + hist_b:
        run = min(run, h)
        combined.append(run)

    result = evaluate(best_fin, rider)
    return OptimizationResult(
        fin=best_fin,
        result=result,
        rider=rider,
        history=combined,
        stage_boundary=len(hist_a),
        n_evals=na + nb,
        seed=seed,
        grooves_enabled=use_grooves and best_fin.grooves.count > 0,
    )


# --- serialization (web tier + verification handoff) -------------------------


def fin_to_dict(fin: FinParams) -> dict:
    """FinParams → plain JSON-able dict (round-trips through `fin_from_dict`)."""
    o, f, g = fin.outline, fin.foil, fin.grooves
    return {
        "outline": {
            "depth": o.depth, "base": o.base, "sweep": o.sweep,
            "tip_width_ratio": o.tip_width_ratio, "le_fullness": o.le_fullness,
            "te_shape": o.te_shape, "le_dx": list(o.le_dx), "te_dx": list(o.te_dx),
        },
        "foil": {
            "family": f.family.value, "thickness_ratio": f.thickness_ratio,
            "camber_ratio": f.camber_ratio, "camber_position": f.camber_position,
            "te_thickness": f.te_thickness,
        },
        "thickness_tip_factor": fin.thickness_tip_factor,
        "grooves": {
            "count": g.count, "length": g.length, "pitch": g.pitch, "width": g.width,
            "depth_ratio": g.depth_ratio, "span_start": g.span_start,
            "surface": g.surface.value,
        },
    }


def fin_from_dict(data: dict) -> FinParams:
    """Inverse of `fin_to_dict`."""
    o, f, g = data["outline"], data["foil"], data["grooves"]
    return FinParams(
        outline=OutlineParams(
            depth=o["depth"], base=o["base"], sweep=o["sweep"],
            tip_width_ratio=o["tip_width_ratio"], le_fullness=o["le_fullness"],
            te_shape=o["te_shape"], le_dx=tuple(o["le_dx"]), te_dx=tuple(o["te_dx"])),
        foil=FoilParams(
            family=FoilFamily(f["family"]), thickness_ratio=f["thickness_ratio"],
            camber_ratio=f["camber_ratio"], camber_position=f["camber_position"],
            te_thickness=f["te_thickness"]),
        thickness_tip_factor=data["thickness_tip_factor"],
        grooves=GrooveParams(
            count=g["count"], length=g["length"], pitch=g["pitch"], width=g["width"],
            depth_ratio=g["depth_ratio"], span_start=g["span_start"],
            surface=GrooveSurface(g["surface"])),
    )


def result_to_dict(result: OptimizationResult) -> dict:
    """Full result → JSON dict for the web tier and the CFD verification stage.

    Carries the fin params, every scored number, and the search metadata. The
    frozen CFD polar (scripts/verify_candidate.py) reads `fin` + `rider`.
    """
    r = result.result
    rider = result.rider
    return {
        "rider": {
            "weight_kg": rider.weight_kg, "skill": rider.skill.name,
            "speed_ms": rider.speed, "config": rider.config.value,
            "material": rider.material,
            "spider_targets": rider.resolved_targets(),
        },
        "fin": fin_to_dict(result.fin),
        "objective": r.objective,
        "distance": r.distance,
        "penalty": r.penalty,
        "feasible": r.feasible,
        "spider_predicted": r.spider_predicted,
        "spider_target": r.spider_target,
        "margins": r.margins,
        "penalties": r.penalties,
        "issues": r.issues,
        "planform": {
            "area_mm2": metrics(result.fin.outline).area,
            "aspect_ratio": metrics(result.fin.outline).aspect_ratio,
        },
        "search": {
            "n_evals": result.n_evals, "seed": result.seed,
            "stage_boundary": result.stage_boundary,
            "grooves_enabled": result.grooves_enabled,
            "history": result.history,
        },
    }


def write_result_json(result: OptimizationResult, path: str | Path) -> Path:
    """Write the result dict to `path` (creating parent dirs)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result_to_dict(result), indent=2) + "\n")
    return path


# --- result card -------------------------------------------------------------
# House style (brief): near-black bg, cyan primary, orange accent.
_BG = "#0b0e11"
_PANEL = "#12171c"
_CYAN = "#7fd4e0"
_ORANGE = "#f2a154"
_INK = "#e8edf0"
_MUTED = "#8a97a0"
_GRID = (1.0, 1.0, 1.0, 0.12)


def _draw_radar(ax, result: OptimizationResult) -> None:
    axes = spider.AXES
    ang = np.linspace(0.0, 2.0 * np.pi, len(axes), endpoint=False)
    ang_c = np.concatenate((ang, ang[:1]))
    pred = np.array([result.result.spider_predicted[a] for a in axes])
    tgt = np.array([result.result.spider_target[a] for a in axes])
    for values, color, label, fill in ((tgt, _ORANGE, "target", 0.06),
                                        (pred, _CYAN, "predicted", 0.14)):
        v = np.concatenate((values, values[:1]))
        ax.plot(ang_c, v, color=color, lw=2.0, label=label)
        ax.fill(ang_c, v, color=color, alpha=fill)
    ax.set_xticks(ang)
    ax.set_xticklabels([a.upper() for a in axes], color=_INK, fontsize=8,
                       family="monospace")
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75])
    ax.set_yticklabels(["25", "50", "75"], color=_MUTED, fontsize=6)
    ax.grid(color=_GRID, lw=0.8)
    ax.set_facecolor(_BG)
    ax.spines["polar"].set_color(_GRID)
    ax.legend(loc="upper right", bbox_to_anchor=(1.32, 1.14), facecolor=_PANEL,
              edgecolor=_GRID, labelcolor=_INK, fontsize=8)
    ax.set_title("spider: predicted vs target", color=_INK, fontsize=10, pad=18)


def _draw_convergence(ax, result: OptimizationResult) -> None:
    hist = result.history
    ax.set_facecolor(_PANEL)
    if hist:
        gens = np.arange(1, len(hist) + 1)
        ax.plot(gens, hist, color=_CYAN, lw=2.0)
        b = result.stage_boundary
        if 0 < b < len(hist):
            ax.axvline(b, color=_ORANGE, lw=1.2, ls="--")
            ax.text(b, ax.get_ylim()[1], " stage B", color=_ORANGE, fontsize=8,
                    va="top", ha="left", family="monospace")
        ax.set_yscale("log" if min(hist) > 0 else "linear")
    ax.set_xlabel("generation", color=_MUTED, fontsize=9)
    ax.set_ylabel("best objective", color=_MUTED, fontsize=9)
    ax.set_title("convergence (best-so-far)", color=_INK, fontsize=10)
    ax.tick_params(colors=_MUTED, labelsize=7)
    for s in ax.spines.values():
        s.set_color("#2a333b")


def _draw_outline(ax, fin: FinParams) -> None:
    z, x_le, chord = planform(fin.outline)
    live = chord > 0.3
    x = np.concatenate((x_le[live], (x_le + chord)[live][::-1]))
    y = np.concatenate((z[live], z[live][::-1]))
    ax.set_facecolor(_PANEL)
    ax.fill(x, y, color=_CYAN, alpha=0.10)
    ax.plot(x, y, color=_CYAN, lw=2.0)
    if fin.grooves.count:
        g = fin.grooves
        for i in range(g.count):
            zc = g.span_start * fin.outline.depth + i * g.pitch
            x0 = float(np.interp(zc, z, x_le))
            run = min(g.length, 0.55 * float(np.interp(zc, z, chord)))
            ax.plot([x0 + 2, x0 + 2 + run], [zc, zc], color=_ORANGE, lw=2.0,
                    solid_capstyle="round", alpha=0.9)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_title("winning outline", color=_INK, fontsize=10)
    ax.tick_params(colors=_MUTED, labelsize=7)
    for s in ax.spines.values():
        s.set_color("#2a333b")


def _draw_numbers(ax, result: OptimizationResult) -> None:
    ax.set_facecolor(_PANEL)
    ax.axis("off")
    r = result.result
    o = result.fin.outline
    f = result.fin.foil
    mg = r.margins
    verdict = "FEASIBLE" if r.feasible else "INFEASIBLE"
    vcolor = _CYAN if r.feasible else _ORANGE
    lines = [
        (f"{verdict}   objective {r.objective:.3f}", vcolor),
        (f"distance {r.distance:.3f}   penalty {r.penalty:.3f}", _MUTED),
        ("", _INK),
        (f"depth {o.depth:.0f}  base {o.base:.0f}  sweep {o.sweep:.0f}deg", _INK),
        (f"t/c {f.thickness_ratio:.3f}  tip x{result.fin.thickness_tip_factor:.2f}"
         f"  tipw {o.tip_width_ratio:.2f}", _INK),
        (f"le_full {o.le_fullness:.2f}  te_shape {o.te_shape:+.2f}", _INK),
        (f"grooves {result.fin.grooves.count}"
         + (f" d{result.fin.grooves.depth_ratio:.2f}"
            if result.fin.grooves.count else ""), _INK),
        ("", _INK),
        (f"area {mg['area_mm2']:.0f} mm2  "
         f"[{mg['area_min_mm2']:.0f}-{mg['area_max_mm2']:.0f}]", _MUTED),
        (f"stress SF {mg['stress_sf']:.2f}   "
         f"f_wet {mg['f_wet_hz']:.0f} Hz", _MUTED),
        (f"divergence {mg['divergence_ms']:.0f} m/s   "
         f"washout {mg['washout_pct']:+.1f}%", _MUTED),
        (f"working {mg['alpha_work_deg']:.1f}deg  env x{mg['env_factor']:.2f}"
         f"  tipdefl {mg['tip_deflection_mm']:.2f}mm", _MUTED),
    ]
    y = 0.97
    for text, color in lines:
        ax.text(0.02, y, text, color=color, fontsize=9, family="monospace",
                va="top", transform=ax.transAxes)
        y -= 0.083
    ax.set_title("margins & headline params", color=_INK, fontsize=10)


def render_result_card(result: OptimizationResult, path: str | Path) -> Path:
    """Dark-style PNG result card: spider radar (predicted vs target),
    convergence curve, winning outline, and a margins/params panel."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rider = result.rider
    fig = plt.figure(figsize=(12.5, 9.0), facecolor=_BG)
    fig.suptitle(
        f"fingen optimize  ·  {rider.weight_kg:.0f} kg {rider.skill.name.lower()}"
        f"  ·  {rider.config.value}  ·  {rider.material}"
        f"  ·  {rider.speed:.1f} m/s",
        color=_INK, fontsize=13, family="monospace")
    ax_r = fig.add_subplot(2, 2, 1, projection="polar")
    _draw_radar(ax_r, result)
    _draw_convergence(fig.add_subplot(2, 2, 2), result)
    _draw_outline(fig.add_subplot(2, 2, 3), result.fin)
    _draw_numbers(fig.add_subplot(2, 2, 4), result)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=110, facecolor=_BG)
    plt.close(fig)
    return path
