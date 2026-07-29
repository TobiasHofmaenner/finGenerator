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

import contextlib
import functools
import json
import math
import os
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
    FinSetParams,
    FoilFamily,
    FoilParams,
    GrooveParams,
    GrooveSurface,
    OutlineParams,
    TabParams,
    TabSystem,
)
from fingen.roll import roll_report, roll_set_report
from fingen.sizing import (
    AnchorSheet,
    Skill,
    anchor,
    check_anchor,
    required_side_force_n,
    tab_neck_stress_mpa,
)

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

# Practical planform corridor (graded gates, not hard walls). Depth bounds
# per config reflect board clearance / swing weight / commercial practice:
# side fins cluster near 110-125 mm, singles run far deeper. Geometric AR
# band from the replicated references (BW04 1.51, Merrick 1.78) with slack.
_DEPTH_CORRIDOR_MM = {
    FinConfig.SINGLE: (160.0, 290.0),
    FinConfig.TWIN: (95.0, 150.0),
    FinConfig.THRUSTER: (90.0, 140.0),
    FinConfig.QUAD: (85.0, 135.0),
    FinConfig.TWO_PLUS_ONE: (90.0, 140.0),
}
AR_GEO_MIN, AR_GEO_MAX = 1.05, 2.6

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

# Design roll rate per skill (rad/s) for the roll-augmented stress case (#23):
# a rail-to-rail (90° = π/2 rad) reversal in 0.63/0.39/0.26/0.20 s → p ≈
# 2.5/4.0/6.0/8.0 rad/s. Documented engineering estimates of how hard each skill
# tier throws the board; a bench/IMU study calibrates them later.
_P_DESIGN_RAD_S = {
    Skill.CRUISER: 2.5,
    Skill.INTERMEDIATE: 4.0,
    Skill.ADVANCED: 6.0,
    Skill.PRO: 8.0,
}

# Stability (roll-damping) target base per skill — a provisional PERCEPTUAL
# prior (the Bali cohort calibrates it): cruisers want a planted, damped blade
# (high), pros a loose/agile one (low). High = damped/locked-in, low = agile.
_STABILITY_SKILL_BASE = {
    Skill.CRUISER: 0.70,
    Skill.INTERMEDIATE: 0.55,
    Skill.ADVANCED: 0.45,
    Skill.PRO: 0.35,
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
        stability   base(skill) + 0.10·(m−77.5)/32.5  planted vs agile roll feel

    The stability base is a per-skill PERCEPTUAL prior (CRUISER 0.70 planted …
    PRO 0.35 agile, `_STABILITY_SKILL_BASE`, Bali-cohort-calibrated later); the
    weight term is control-torque scaling — a heavier rider needs more roll
    damping for the same feel, +0.10 at 110 kg, −0.10 at 45 kg about W_REF 77.5.

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
        "stability": _STABILITY_SKILL_BASE[skill] + 0.10 * (weight_kg - 77.5) / 32.5,
    }
    # Damp toward the achievable envelope: undamped heavy/aggressive profiles
    # demand hold+drive+speed simultaneously (physically antagonistic), which
    # floors the best feasible distance ~0.7 and flattens the landscape into
    # seed lottery. Compression keeps the ORDERING of the rider's priorities
    # while placing the vector near the reachable frontier; the result card
    # reports predicted-vs-target shortfall honestly either way.
    return {axis: float(min(0.85, max(0.12, 0.5 + 0.72 * (raw[axis] - 0.5))))
            for axis in spider.AXES}


@dataclass
class RiderSpec:
    """The optimizer's input: who the fin is for and how it is mounted.

    speed_ms defaults from skill; config selects the fin's family (single →
    symmetric center fin, everything else → flat-inside side fin) and its
    interference environment. spider_targets, when given, MERGES over the
    derived defaults (pass just the axes you want to override).

    practical_corridor (default True, the product contract) gates the two
    CONVENTION penalties — the per-config depth band and the geometric-AR band
    — that encode board clearance / swing weight / commercial practice, NOT
    physics. Set it False to let the search run free of them (the free-run
    exploit study): the load-bearing PHYSICS gates (area anchor, side-force
    capacity, base minimum, bending stress SF, wet fundamental, divergence)
    always stay on. See docs/… / scripts/freerun.py.
    """

    weight_kg: float
    skill: Skill = Skill.INTERMEDIATE
    speed_ms: float | None = None
    config: FinConfig = FinConfig.THRUSTER
    material: str = "pet-cf"
    # The rider's BOARD mounting system. Not cosmetic: it sets the base-chord
    # minimum (the tab set has to fit — FCS II spans 98 mm) and activates the
    # tab-neck stress gate. Left at NONE (glass-on) the optimizer is free to
    # design a blade too short-based to mount, which is exactly what happened
    # before this was threaded through.
    tabs: TabSystem = TabSystem.NONE
    # Required structural safety factor on the bending gate (the WORSE of the
    # steady and roll-augmented cases). 1.0 means "design right up to the
    # allowable", which is only honest when the material card is measured — the
    # PAHT-CF card is an APPROXIMATION good to ~+-20-30% on modulus, so a fin
    # meant to be surfed wants real headroom above the gate, not none.
    stress_sf_min: float = 1.0
    # Maximum tolerable flex lift-knockdown (washout), as a FRACTION. None = no
    # gate (the original behaviour). This is a HANDLING requirement, not a
    # structural one: nothing else in the objective bounds deflection, and
    # washout is applied as a MULTIPLIER on drive/hold — a floppier blade sheds
    # tip load, which the fleet ranking can read as a better L/D. So the search
    # can buy score with floppiness right up to the strength wall. A rider who
    # asks for "locked-in" wants the opposite.
    washout_max: float | None = None
    # Required tab safety factor, or None to REPORT ONLY (no penalty).
    #
    # The analytic tab model (sizing.tab_neck_stress_mpa) is beam theory across
    # a stepped section with a GUESSED stress-concentration factor for a fillet
    # the generator does not build. It is the right order of magnitude and the
    # wrong tool for a gate: it cannot see the actual junction geometry, and
    # S_tab is fixed by the box standard, so the search cannot satisfy it by
    # designing a better tab — only by degrading the blade until the moment
    # drops (observed: it widens the base to drag the load centroid inboard,
    # exploiting flex.py's unvalidated w ∝ c(z) load shape, and stability
    # collapses). Gating on a model that crude buys a worse fin, not a safer one.
    #
    # None = let tier-1 adjudicate: CFD surface pressure -> FEM with the mesh
    # fixed at the BOX interface, which resolves the tab junction directly
    # instead of guessing K_t. That is task #24's stated plan.
    tab_sf_min: float | None = 1.0
    spider_targets: dict[str, float] | None = None
    practical_corridor: bool = True

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

    def resolved_targets(self, *, rear_member: bool = False) -> dict[str, float]:
        """Derived defaults with any explicit override merged over them.

        `rear_member` returns the target vector for the aft/CENTER blade of a
        set. It is a DIFFERENT machine from the side fin and must not be scored
        against the side's wishes: a symmetric 50/50 blade on the stringer
        cannot reach a side fin's forgiveness or stability numbers at all, so
        holding it to them drives it into the corner of the feasible box
        (base-min, area-max, AR-max, t/c-max simultaneously) chasing points it
        can never score. Its job is to anchor the tail — hold and pivot — while
        the fronts drive; forgiveness and stability belong to the side blade.
        """
        targets = default_spider_targets(self.weight_kg, self.skill)
        if self.spider_targets:
            targets.update({a: float(v) for a, v in self.spider_targets.items()})
        if rear_member:
            targets = dict(targets)
            targets.update(_CENTER_TARGET_OVERRIDES)
        return targets


def family_for_config(config: FinConfig) -> FoilFamily:
    """The blade family the optimizer builds for a config: a symmetric center
    fin for a single, a flat-inside side fin for every set (the dominant,
    chiral blade exported both hands)."""
    return FoilFamily.SYMMETRIC if config is FinConfig.SINGLE else FoilFamily.FLAT_INSIDE


def _roll_context(fin: FinParams, config: FinConfig) -> FinSetParams:
    """Place the optimized blade into its set at DEFAULT placements, so the
    report-only roll metrics can show the set-level damping the fin lives in.
    The MVP designs the dominant blade — the center fin for a single, the side
    blade for every set (family_for_config) — so it goes in that slot; the other
    slot keeps the template default (context only, not designed here)."""
    if config is FinConfig.SINGLE:
        return FinSetParams(config=config, center=fin)
    return FinSetParams(config=config, side=fin)


# --- multi-fin interference environment (bench/falk) -------------------------
# Digitized from bench/falk/thruster-run-summary.json: a fingen THRUSTER swept
# in leeway, per-fin CFD side force. The center fin is the REAR member (rides
# the stringer aft of the forward side pair) and reads a side-force DEFICIT vs
# the dominant (leeward) front fin — the measured multi-fin interference the
# single-fin spider/hydro model cannot see. deficit(α) = 1 − CL_center/CL_front
# where CL_front is the more-loaded of the two fronts. Reproduces the [Falk20]
# Fig 10 anchor (front→rear ≈ 23% at the 20° lift peak) and grows into the
# post-peak wake shadow. Baked as the portable authority (the JSON is not
# packaged); regenerate with the thruster CFD driver (separate private repo).
_FALK_ANGLE_DEG = np.array([0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0])
_FALK_REAR_DEFICIT = np.array([0.00, 0.296, 0.239, 0.223, 0.262, 0.276, 0.416])
# Configs whose optimized blade lives in a downwash environment (a rear member
# exists behind another fin). SINGLE/TWIN have no aft-shadowed member here, so
# they run at the isolated (factor 1.0) spider model; QUAD reuses the thruster
# curve as the best available proxy (no quad-specific summary yet — documented
# gap, conservative).
_INTERFERENCE_CONFIGS = frozenset(
    {FinConfig.THRUSTER, FinConfig.TWO_PLUS_ONE, FinConfig.QUAD})

# Configs whose CENTER fin is co-designed (a symmetric rear member on the
# stringer) rather than left at the template default. THRUSTER only for now: its
# center is unambiguously the aft-shadowed symmetric member the Falk deficit
# describes. QUAD (front==rear side blade, no true center) and 2+1 (its
# physically dominant blade IS the center — family_for_config/anchor currently
# treat the side as dominant, a separate fix) are deferred, documented gaps.
_CENTER_DESIGN_CONFIGS = frozenset({FinConfig.THRUSTER})
# The center's weight in the REPORTED set objective (the search is separable —
# the side is scored unchanged and the center independently — so this only sets
# how the two sub-distances combine for display). Anchored to the Falk load
# split: two front fins + one rear making (1−deficit) of a front → the center is
# ~0.27–0.35 of the fin-force at working leeway. A share, not new physics.
CENTER_OBJECTIVE_WEIGHT = 0.35
# Target overrides for the aft/CENTER member (see RiderSpec.resolved_targets).
# Reachability, not preference: a SYMMETRIC blade on the stringer tops out far
# below a flat-inside side fin on forgiveness and stability, so those targets
# are set where the member can actually live. Its role is to ANCHOR the tail —
# hold and pivot — while the forward pair drives, hence pivot up and drive down.
_CENTER_TARGET_OVERRIDES = {
    "forgiveness": 0.10,
    "stability": 0.30,
    "pivot": 0.55,
    "drive": 0.60,
}


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


@functools.lru_cache(maxsize=64)
def _fleet_raw(speed_key: float, weight_key: float
               ) -> tuple[tuple[tuple[str, float], ...], ...]:
    """Reference-fleet raw axis values at `speed_key`/`weight_key`, cached (the
    fleet is fixed; recomputing six fins' raw scores every evaluate would blow
    the budget). Keyed on weight too because the drive/forgiveness working point
    scales with the rider's force (spider.work_force_n), so the fleet must be
    ranked at the same weight as the candidate. Returned as hashable sorted-item
    tuples."""
    fleet = spider.reference_fleet()
    return tuple(tuple(sorted(spider.raw_scores(f, speed_key, weight_key).items()))
                 for f in fleet.values())


def _normalize(raw: dict[str, float], fleet: tuple) -> dict[str, float]:
    """0..100 per axis, interpolated rank against the fleet (spider.py's rule)."""
    fleet_dicts = [dict(f) for f in fleet]
    out = {}
    for axis in spider.AXES:
        values = np.sort([f[axis] for f in fleet_dicts])
        ranks = np.linspace(0.0, 100.0, len(values))
        # Tied fleet values (e.g. four fins at the stall-limited forgiveness
        # floor) make np.interp's rank flip 0<->40 on sub-ULP input changes —
        # a deterministic noise band that polluted ~10% of feasible space
        # (found by the landscape characterization). Collapse ties to their
        # mean rank so the interpolant is single-valued and stable.
        uniq, inverse = np.unique(np.round(values, 9), return_inverse=True)
        mean_ranks = np.array([ranks[inverse == i].mean()
                               for i in range(len(uniq))])
        out[axis] = float(np.interp(raw[axis], uniq, mean_ranks))
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


def evaluate(fin: FinParams, rider: RiderSpec, *,
             rear_member: bool = False) -> EvalResult:
    """Score `fin` for `rider`. <= 50 ms: all tier-0 analytic, no OCCT.

    `rear_member` scores the fin as the aft/center member of a set (thruster/2+1
    center), which sits in the forward pair's downwash: its produced side force
    is derated by the measured Falk interference factor on the capacity gate and
    the hold axis. Default False = the dominant/side blade, unchanged (env 1.0).

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
    # The rear/center member carries its OWN (smaller) share of the load — see
    # sizing.CONFIG_CENTER_SHARE. Sizing it against the dominant share while
    # also derating its produced force would demand it out-produce the front
    # through the same downwash (systematic oversizing).
    sheet: AnchorSheet = anchor(rider.weight_kg, rider.skill, design_speed=speed,
                                config=rider.config, material=rider.material,
                                tabs=rider.tabs,
                                member="center" if rear_member else "dominant")

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
    # A designed REAR/center member (thruster/2+1) sits in the forward pair's
    # downwash: derate its produced side force by the measured Falk factor
    # (interference_factor) — at the break angle for the capacity gate here, at
    # the working angle for the hold axis below. The dominant/side blade keeps 1.
    env_cap = interference_factor(rider.config, a_break) if rear_member else 1.0
    f_capacity *= env_cap
    req = required_side_force_n(sheet)  # F_req: also the hold axis reference
    if f_capacity < req:
        penalties["capacity"] = (req - f_capacity) / req
    if fin.outline.base < sheet.base_min_mm:
        penalties["base_min"] = ((sheet.base_min_mm - fin.outline.base)
                                 / max(sheet.base_min_mm, 1.0))

    # Practical planform corridor — constraints reality imposes that no hydro
    # axis prices: board clearance / swing weight bound the span per config,
    # and commercial fins live in a narrow geometric-AR band (BW04 replica
    # 1.51, Merrick template 1.78). Without these the search ships pancakes
    # (base 3.5x depth) or longboard-depth "side fins" as feasible winners.
    # CONVENTION, not physics: rider.practical_corridor=False skips exactly
    # this block (the free-run exploit study); the physics gates above/below
    # always apply.
    if rider.practical_corridor:
        d_lo, d_hi = _DEPTH_CORRIDOR_MM[rider.config]
        depth = fin.outline.depth
        if depth < d_lo:
            penalties["depth_low"] = (d_lo - depth) / d_lo
        if depth > d_hi:
            penalties["depth_high"] = (depth - d_hi) / d_hi
        ar_geo = m.aspect_ratio
        if ar_geo < AR_GEO_MIN:
            penalties["ar_low"] = (AR_GEO_MIN - ar_geo) / AR_GEO_MIN
        if ar_geo > AR_GEO_MAX:
            penalties["ar_high"] = (ar_geo - AR_GEO_MAX) / AR_GEO_MAX

    # Structural gates: stress at the transient PEAK load, washout/frequency at
    # the working speed (the knockdown is load-independent — see flex.py). The
    # roll-augmented case (#23) adds the rider's skill-scaled roll rate on top of
    # the steady peak; the gate takes the WORSE of steady-only and combined.
    flex = flex_report(fin, sheet.force_peak_n, speed, material=rider.material,
                       p_design_rad_s=_P_DESIGN_RAD_S[rider.skill])
    stress_sf = flex.stress_margin
    stress_sf_roll = flex.stress_margin_roll
    worst_stress_sf = min(stress_sf, stress_sf_roll)
    if worst_stress_sf < rider.stress_sf_min:
        penalties["stress"] = ((rider.stress_sf_min - worst_stress_sf)
                               / rider.stress_sf_min)
    if flex.f_wet_hz < F_WET_MIN_HZ:
        penalties["f_wet"] = (F_WET_MIN_HZ - flex.f_wet_hz) / F_WET_MIN_HZ
    div_req = DIVERGENCE_SF * speed
    if flex.divergence_speed_ms < div_req:
        penalties["divergence"] = (div_req - flex.divergence_speed_ms) / div_req
    # Stiffness gate (handling): cap how much lift the blade sheds to flex.
    if rider.washout_max is not None:
        washout_frac = abs(flex.lift_knockdown)
        if washout_frac > rider.washout_max:
            penalties["washout"] = ((washout_frac - rider.washout_max)
                                    / max(rider.washout_max, 1e-6))

    # Tab-mounting gate (#24): the combined-case root moment + shear through the
    # TABS' own section at the base plane (fingen.sizing.tab_neck_stress_mpa),
    # against the SAME material allowable the blade gate uses. LIVE whenever the
    # rider's board has boxes (RiderSpec.tabs); inactive (tab_sf = ∞) only for
    # glass-on / TabSystem.NONE.
    #
    # Held to the SAME safety factor as the blade, not a laxer 1.0: the tab is a
    # smaller, notched, stress-concentrated section carrying the full root
    # moment — S_tab is BELOW the blade root's own S — so giving it less margin
    # than the blade is backwards.
    tab_stress = tab_neck_stress_mpa(fin, flex.root_moment_roll_nm,
                                     flex.root_shear_roll_n)
    tab_sf = math.inf if tab_stress is None else sheet.allow_mpa / max(tab_stress, 1e-12)
    if rider.tab_sf_min is not None and tab_sf < rider.tab_sf_min:
        penalties["tab_sf"] = (rider.tab_sf_min - tab_sf) / rider.tab_sf_min

    penalty_sum = float(sum(penalties.values()))
    feasible = penalty_sum <= 1e-9

    # Tier-0 roll dynamics (fingen.roll). Roll damping NOW prices into the
    # objective through the `stability` spider axis (below, via spider.raw_scores
    # → the CORRECTED |L_p|). These blocks compute the REPORT-ONLY roll margins:
    # the blade's own damping/inertia/agility and the set-level damping it lives
    # in (default placements) — surfaced for the card/JSON but NOT summed into
    # the objective (the stability axis is the only roll term that scores).
    # ROLL INERTIA stays report-only, never an axis. The practical DEPTH CORRIDOR
    # above stays a hard-ish gate until the study rerun confirms roll pricing —
    # so the corridor is NOT demoted here.
    roll = roll_report(fin, speed)
    roll_set = roll_set_report(_roll_context(fin, rider.config), speed)

    # Raw spider axes at the rider's working point, then washout on the
    # lift-magnitude axes. work_force_n scales the drive/forgiveness working
    # point with rider weight (spider.raw_scores takes it), so a light rider's
    # drive is read at a lighter force budget than an adult's.
    raw = spider.raw_scores(fin, speed, rider.weight_kg)
    cl_work = min(spider.work_force_n(rider.weight_kg) / (q * area * 1e-6),
                  0.95 * slope * math.radians(a_break))
    alpha_work = math.degrees(cl_work / slope)
    washout = max(0.0, 1.0 + flex.lift_knockdown)  # knockdown < 0 = lift lost
    # Interference: the measured Falk deficit belongs to the REAR/center
    # member relative to the dominant front — and the MVP designs the
    # dominant blade, so it does NOT carry that knockdown (front-in-set vs
    # isolated is unmeasured; treated as 1.0 and documented). The deficit
    # curve stays available (interference_factor) for the future set-level
    # optimizer that designs the rear member too.
    #
    # DRIVE stays fleet-ranked (an intensive L/D), so the washout multiplies its
    # raw value before ranking. HOLD is EXTENSIVE (side force in N): ranking it
    # against the adult fleet is what put the light rider's target out of reach,
    # so it becomes requirement-relative (spider.hold_score) against F_req — the
    # same threshold the capacity gate uses. Washout still knocks the effective
    # f_max down (a floppy blade makes less side force).
    # Rear/center member: the Falk downwash derates the side force it can hold
    # (at the working angle). The dominant/side blade stays at env 1.0. DRIVE
    # (an intensive L/D) is left un-derated for now — the in-set L/D change is
    # second-order and unmeasured; documented, revisited with the set solve.
    env_work = interference_factor(rider.config, alpha_work) if rear_member else 1.0
    raw["drive"] *= washout
    f_max_eff = raw["hold"] * washout * env_work

    predicted = _normalize(raw, _fleet_raw(round(speed, 2),
                                           round(rider.weight_kg, 2)))
    predicted["hold"] = spider.hold_score(f_max_eff, req)
    targets = rider.resolved_targets(rear_member=rear_member)
    distance = 0.0
    for axis in spider.AXES:
        tgt = targets[axis]
        weight = 1.0 + abs(tgt - 0.5)  # axes pushed to extremes matter more
        distance += weight * (predicted[axis] / 100.0 - tgt) ** 2

    objective = distance + PENALTY_WEIGHT * penalty_sum
    margins = {
        "stress_sf": stress_sf,
        "stress_sf_roll": stress_sf_roll,
        "tab_sf": tab_sf,
        "f_wet_hz": flex.f_wet_hz,
        "divergence_ms": flex.divergence_speed_ms,
        "area_mm2": area,
        "area_min_mm2": sheet.area_min_mm2,
        "area_max_mm2": sheet.area_max_mm2,
        "capacity_n": f_capacity,
        "capacity_req_n": req,
        "alpha_work_deg": alpha_work,
        "washout_pct": 100.0 * flex.lift_knockdown,
        "env_factor": env_work,  # rear member: Falk downwash; dominant blade 1.0
        "tip_deflection_mm": flex.tip_deflection_mm,
        # Roll dynamics (report-only margins — the scoring |L_p| rides the
        # stability axis via spider.raw_scores): blade damping |L_p| and added
        # inertia, the fin-only roll time constant, the rail-to-rail agility
        # proxy (1/|L_p|, higher = looser), and the set-level damping.
        "roll_damping_nm_s": roll.roll_damping_nm_s,
        "roll_inertia_kgm2": roll.added_inertia_kgm2,
        "roll_tau_ms": roll.tau_ms,
        "roll_agility": roll.agility_proxy,
        "roll_set_damping_nm_s": roll_set.roll_damping_nm_s,
    }
    issues = check_anchor(fin, sheet, flex.stress_max_mpa)
    if stress_sf < rider.stress_sf_min:
        issues.append(f"flex bending SF {stress_sf:.2f} < {rider.stress_sf_min:.2f} "
                      "at the peak load")
    if stress_sf_roll < rider.stress_sf_min:
        issues.append(f"roll-augmented bending SF {stress_sf_roll:.2f} < "
                      f"{rider.stress_sf_min:.2f} "
                      f"(p_design {_P_DESIGN_RAD_S[rider.skill]:.1f} rad/s)")
    if rider.tab_sf_min is not None and tab_sf < rider.tab_sf_min:
        issues.append(f"tab SF {tab_sf:.2f} < {rider.tab_sf_min:.2f} at the "
                      f"combined load ({fin.tabs.system.value})")
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
            use_grooves: bool, family: FoilFamily | None = None,
            tabs: TabSystem = TabSystem.NONE) -> FinParams:
    """Normalized vector → FinParams. Raises ValueError for combinations the
    params/planform checks reject (the search treats that as a penalty).

    `family` overrides the config's default foil family — used to decode the
    SYMMETRIC center of a set while `config` still selects its corridor/anchor."""
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
    foil = FoilParams(family=family or family_for_config(config),
                      thickness_ratio=vals["thickness_ratio"])
    return FinParams(outline=outline, foil=foil,
                     thickness_tip_factor=vals["thickness_tip_factor"], grooves=grooves,
                     tabs=TabParams(system=tabs))


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


def _fin_to_sliders(fin: FinParams) -> list[float]:
    """Back-project any fin's level-1 params to the [0,1] gene box (clamped) —
    a warm start for the center search from the rider-sized side blade."""
    src = {
        "depth": fin.outline.depth, "base": fin.outline.base,
        "sweep": fin.outline.sweep, "tip_width_ratio": fin.outline.tip_width_ratio,
        "le_fullness": fin.outline.le_fullness, "te_shape": fin.outline.te_shape,
        "thickness_ratio": fin.foil.thickness_ratio,
        "thickness_tip_factor": fin.thickness_tip_factor,
    }
    return [_clip01((src[name] - lo) / (hi - lo)) for name, lo, hi in _SLIDER_BOUNDS]


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
    # Co-designed set members (center-design configs only; None otherwise). `fin`
    # stays the dominant/side blade; `center` is the symmetric rear member and
    # `fin_set` the assembled set ready for placement/export.
    center: FinParams | None = None
    center_result: EvalResult | None = None
    fin_set: FinSetParams | None = None


_SIGMA_A = 0.25  # broad in the normalized box: level-1 sliders explore widely
_SIGMA_B = 0.08  # tight: refine near the stage-A optimum, gently open offsets


def _score_candidate(payload: tuple) -> float:
    """Decode + score ONE candidate. Module-level (hence picklable) so a whole
    CMA generation can be farmed out to a process pool — every candidate in a
    generation is independent, which is the only parallelism this search needs."""
    x, rider, use_offsets, use_grooves, family, rear_member = payload
    try:
        fin = _decode(np.asarray(x), rider.config, use_offsets=use_offsets,
                      use_grooves=use_grooves, family=family, tabs=rider.tabs)
        return evaluate(fin, rider, rear_member=rear_member).objective
    except ValueError:
        # Production contract: rejection paths live beyond _decode too
        # (chord_schedule's needle-tip/waist guards fire inside flex_report
        # for outlines planform() accepts).
        return DECODE_PENALTY


def resolve_workers(workers: int | None, popsize: int) -> int:
    """How many processes to score a generation with. More than `popsize` is
    useless (that is all the work there is), and one core is left for the rest
    of the machine. FINGEN_WORKERS overrides; 1 forces the serial path."""
    if workers is None:
        env = os.environ.get("FINGEN_WORKERS")
        workers = int(env) if env else (os.cpu_count() or 1) - 1
    return max(1, min(int(workers), popsize))


def _probe() -> int:
    """Trivial task proving a start method actually round-trips."""
    return 1


@functools.lru_cache(maxsize=1)
def _mp_context():
    """The multiprocessing context to score generations with, probed once.

    Prefer `forkserver`: numpy/OpenBLAS keep worker threads, and forking a
    multi-threaded parent can deadlock the child (CPython warns about exactly
    this). But forkserver re-imports `__main__` in the child, which fails when
    the entry point is not importable (a REPL, `python -`, a heredoc). So probe
    it with one cheap round-trip and fall back to plain `fork`, then to serial.
    """
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor

    for method in ("forkserver", "fork"):
        try:
            ctx = mp.get_context(method)
        except ValueError:  # pragma: no cover - method missing on this platform
            continue
        try:
            with ProcessPoolExecutor(max_workers=1, mp_context=ctx) as ex:
                if ex.submit(_probe).result(timeout=60) == 1:
                    return ctx
        except Exception:  # noqa: BLE001 — any breakage means "try the next one"
            continue
    return None


@contextlib.contextmanager
def _generation_mapper(n_workers: int):
    """Yield a `map(fn, items) -> list` for one CMA stage. Order is preserved
    (Executor.map does), so the values handed to `es.tell` are identical to the
    serial path and the search stays deterministic under seed."""
    if n_workers <= 1:
        yield lambda fn, items: [fn(i) for i in items]
        return
    from concurrent.futures import ProcessPoolExecutor

    ctx = _mp_context()
    if ctx is None:  # no usable start method — correctness over speed
        yield lambda fn, items: [fn(i) for i in items]
        return
    with ProcessPoolExecutor(max_workers=n_workers, mp_context=ctx) as ex:
        yield lambda fn, items: list(ex.map(fn, items))


def _run_cma(rider: RiderSpec, x0: list[float], sigma0: float, *, use_offsets: bool,
             use_grooves: bool, budget: int, seed: int,
             family: FoilFamily | None = None, rear_member: bool = False,
             workers: int | None = None
             ) -> tuple[np.ndarray, float, list[float], int]:
    """One CMA-ES stage in the [0,1]^n box. Returns (best_x, best_f, best-so-far
    history per generation, evals spent).

    `family`/`rear_member` select what is being designed: the default is the
    dominant blade; the center search passes SYMMETRIC + rear_member=True. They
    are plain values rather than a closure so the work is picklable and a
    generation can be scored in parallel (see `_score_candidate`)."""
    import cma

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
    with _generation_mapper(resolve_workers(workers, es.popsize)) as run_generation:
        while not es.stop() and n_evals < budget:
            xs = es.ask()
            fs = run_generation(_score_candidate,
                                [(x, rider, use_offsets, use_grooves, family,
                                  rear_member) for x in xs])
            es.tell(xs, fs)
            n_evals += len(xs)
            i = int(np.argmin(fs))
            if fs[i] < best_f:
                best_f = float(fs[i])
                best_x = np.asarray(xs[i], dtype=float)
            history.append(best_f)
    return best_x, best_f, history, n_evals


def optimize(rider: RiderSpec, budget_evals: int = 4000, seed: int = 0,
             x0: list[float] | None = None,
             workers: int | None = None) -> OptimizationResult:
    """Search the design space for the fin closest to the rider's targets.

    Stage A optimizes the eight level-1 sliders (CMA-ES, broad sigma). Stage B
    unlocks the twelve level-2 le_dx/te_dx Bézier offsets from the stage-A
    optimum with a tight sigma, plus grooves when `groove_trigger` fires. Decode
    is ValueError→penalty; deterministic under `seed`.

    `x0` overrides the stage-A start: a level-1 slider vector in the normalized
    [0,1]^8 box (default None → the template default via `_x0_sliders`, i.e. the
    original behavior). Only stage A's mean moves; stage B still unlocks from
    stage A's optimum. This lets a multistart study spread starts across the
    grid without touching the search internals.
    """
    if x0 is None:
        x0_a = _x0_sliders(rider.config)
    elif len(x0) != _N_SLIDERS:
        raise ValueError(f"x0 must hold {_N_SLIDERS} level-1 sliders, got {len(x0)}")
    else:
        x0_a = [float(v) for v in x0]

    # Center-design configs carve the center's search OUT of budget_evals (a
    # third of it) rather than spending extra on top, so `budget_evals` stays
    # the honest total cost and n_evals never exceeds it.
    designs_center = rider.config in _CENTER_DESIGN_CONFIGS
    budget_c = max(int(budget_evals / 3.0), 1) if designs_center else 0
    budget_side = max(budget_evals - budget_c, 1)
    budget_a = max(int(budget_side * 0.6), 1)
    budget_b = max(budget_side - budget_a, 0)
    use_grooves = groove_trigger(rider)

    xa, fa, hist_a, na = _run_cma(rider, x0_a, _SIGMA_A,
                                  use_offsets=False, use_grooves=False,
                                  budget=budget_a, seed=seed, workers=workers)
    fin_a = _decode(xa, rider.config, use_offsets=False, use_grooves=False,
                    tabs=rider.tabs)

    best_fin = fin_a
    hist_b: list[float] = []
    nb = 0
    if budget_b > 0:
        x0_b = list(xa) + [0.5] * _N_OFFSETS + ([0.5] * _N_GROOVES if use_grooves else [])
        xb, fb, hist_b, nb = _run_cma(rider, x0_b, _SIGMA_B, use_offsets=True,
                                      use_grooves=use_grooves, budget=budget_b,
                                      seed=seed, workers=workers)
        if fb <= fa:
            try:
                best_fin = _decode(xb, rider.config, use_offsets=True,
                                   use_grooves=use_grooves, tabs=rider.tabs)
            except ValueError:
                best_fin = fin_a

    # Best-so-far across both stages (a monotone convergence curve for the card).
    combined: list[float] = []
    run = float("inf")
    for h in hist_a + hist_b:
        run = min(run, h)
        combined.append(run)

    result = evaluate(best_fin, rider)

    # Co-design the SYMMETRIC center for center-design configs (thruster): its
    # own CMA over the level-1 genes, scored as the aft/rear member (Falk
    # downwash via evaluate(rear_member=True)), warm-started from the rider-sized
    # side blade. The objective is separable — the side score does not depend on
    # the center — so this independent search IS the co-optimum, and it leaves
    # the validated side path untouched (full budget, unchanged winner). The
    # side/center coupling (cant/toe on the side, a real force balance) is the
    # documented next stage.
    center: FinParams | None = None
    center_result: EvalResult | None = None
    fin_set: FinSetParams | None = None
    nc = 0
    if designs_center:
        xc, _fc, _hc, nc = _run_cma(
            rider, _fin_to_sliders(best_fin), _SIGMA_A, use_offsets=False,
            use_grooves=False, budget=budget_c, seed=seed + 7,
            family=FoilFamily.SYMMETRIC, rear_member=True, workers=workers)
        # Guarded like the side stage-B decode: the in-search closure swallows
        # ValueError, so a run whose every candidate rejected leaves best_x on a
        # rejecting vector. Re-raising here would abort optimize() and discard
        # the already-computed, valid SIDE result — so fall back to no center.
        try:
            center = _decode(xc, rider.config, use_offsets=False,
                             use_grooves=False, family=FoilFamily.SYMMETRIC,
                             tabs=rider.tabs)
            center_result = evaluate(center, rider, rear_member=True)
            fin_set = FinSetParams(config=rider.config, side=best_fin,
                                   center=center)
        except ValueError:
            center = center_result = fin_set = None

    return OptimizationResult(
        fin=best_fin,
        result=result,
        rider=rider,
        history=combined,
        stage_boundary=len(hist_a),
        n_evals=na + nb + nc,
        seed=seed,
        grooves_enabled=use_grooves and best_fin.grooves.count > 0,
        center=center,
        center_result=center_result,
        fin_set=fin_set,
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


def fin_set_to_dict(fin_set: FinSetParams) -> dict:
    """FinSetParams → plain JSON-able dict (round-trips through
    `fin_set_from_dict`). Carries the per-slot blades AND the placement
    transforms, so a consumer — the multi-fin CFD writer above all — can
    reconstruct the exact set that was designed."""
    return {
        "config": fin_set.config.value,
        "center": fin_to_dict(fin_set.center) if fin_set.center else None,
        "side": fin_to_dict(fin_set.side) if fin_set.side else None,
        "toe": fin_set.toe, "cant": fin_set.cant,
        "side_x": fin_set.side_x, "side_y": fin_set.side_y,
        "rear_x": fin_set.rear_x, "rear_y": fin_set.rear_y,
        "rear_toe": fin_set.rear_toe, "rear_cant": fin_set.rear_cant,
    }


def fin_set_from_dict(data: dict) -> FinSetParams:
    """Inverse of `fin_set_to_dict`. Placement keys are optional — omitted ones
    fall back to the production-convention defaults on FinSetParams."""
    defaults = FinSetParams()
    return FinSetParams(
        config=FinConfig(data["config"]),
        center=fin_from_dict(data["center"]) if data.get("center") else None,
        side=fin_from_dict(data["side"]) if data.get("side") else None,
        toe=float(data.get("toe", defaults.toe)),
        cant=float(data.get("cant", defaults.cant)),
        side_x=float(data.get("side_x", defaults.side_x)),
        side_y=float(data.get("side_y", defaults.side_y)),
        rear_x=float(data.get("rear_x", defaults.rear_x)),
        rear_y=float(data.get("rear_y", defaults.rear_y)),
        rear_toe=float(data.get("rear_toe", defaults.rear_toe)),
        rear_cant=float(data.get("rear_cant", defaults.rear_cant)),
    )


def result_to_dict(result: OptimizationResult) -> dict:
    """Full result → JSON dict for the web tier and the CFD verification stage.

    Carries the fin params, every scored number, and the search metadata. The
    frozen CFD polar (verification stage, now a separate private repo) reads `fin` + `rider`.
    """
    r = result.result
    rider = result.rider
    out = {
        "rider": {
            "weight_kg": rider.weight_kg, "skill": rider.skill.name,
            "speed_ms": rider.speed, "config": rider.config.value,
            "material": rider.material,
            "tabs": rider.tabs.value,
            "stress_sf_min": rider.stress_sf_min,
            "washout_max": rider.washout_max,
            "tab_sf_min": rider.tab_sf_min,
            "spider_targets": rider.resolved_targets(),
            "practical_corridor": rider.practical_corridor,
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
    # Co-designed set: the symmetric center and the assembled set (center-design
    # configs only). `fin` above stays the dominant/side blade for back-compat.
    if result.center is not None and result.center_result is not None:
        cr = result.center_result
        out["center_fin"] = fin_to_dict(result.center)
        out["center"] = {
            "objective": cr.objective,
            "distance": cr.distance,
            "penalty": cr.penalty,
            "feasible": cr.feasible,
            "spider_predicted": cr.spider_predicted,
            "margins": cr.margins,
            "planform": {
                "area_mm2": metrics(result.center.outline).area,
                "aspect_ratio": metrics(result.center.outline).aspect_ratio,
            },
        }
        # Blend the members' full OBJECTIVES (distance + penalty), not bare
        # distances: a penalized center must not read as a healthy set. Both
        # `distance` (the pure spider blend) and `feasible` are surfaced too, so
        # a consumer can never mistake an infeasible member for a good set.
        out["set"] = {
            "config": result.rider.config.value,
            # The assembled set, placements included — what the multi-fin CFD
            # (fincfd.setcase) meshes to resolve the real inter-fin interference.
            "fin_set": (fin_set_to_dict(result.fin_set)
                        if result.fin_set is not None else None),
            "objective_weight_center": CENTER_OBJECTIVE_WEIGHT,
            "objective": ((1.0 - CENTER_OBJECTIVE_WEIGHT) * r.objective
                          + CENTER_OBJECTIVE_WEIGHT * cr.objective),
            "distance": ((1.0 - CENTER_OBJECTIVE_WEIGHT) * r.distance
                         + CENTER_OBJECTIVE_WEIGHT * cr.distance),
            "feasible": bool(r.feasible and cr.feasible),
        }
    return out


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
    # HOLD carries a * — it is requirement-relative (headroom over F_req), not
    # fleet-ranked like the other five axes (spider.hold_score).
    ax.set_xticklabels([(a.upper() + "*" if a == "hold" else a.upper())
                        for a in axes], color=_INK, fontsize=8, family="monospace")
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75])
    ax.set_yticklabels(["25", "50", "75"], color=_MUTED, fontsize=6)
    ax.grid(color=_GRID, lw=0.8)
    ax.set_facecolor(_BG)
    ax.spines["polar"].set_color(_GRID)
    ax.legend(loc="upper right", bbox_to_anchor=(1.32, 1.14), facecolor=_PANEL,
              edgecolor=_GRID, labelcolor=_INK, fontsize=8)
    ax.set_title("spider: predicted vs target", color=_INK, fontsize=10, pad=18)
    ax.text(0.5, -0.13, "* hold = requirement-relative (f_max / F_req)",
            color=_MUTED, fontsize=6.5, family="monospace", ha="center",
            va="top", transform=ax.transAxes)


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
        (f"stress SF {mg['stress_sf']:.2f} (roll {mg['stress_sf_roll']:.2f})   "
         f"f_wet {mg['f_wet_hz']:.0f} Hz", _MUTED),
        (f"divergence {mg['divergence_ms']:.0f} m/s   "
         f"washout {mg['washout_pct']:+.1f}%", _MUTED),
        (f"working {mg['alpha_work_deg']:.1f}deg  env x{mg['env_factor']:.2f}"
         f"  tipdefl {mg['tip_deflection_mm']:.2f}mm", _MUTED),
        (f"roll Lp {mg['roll_damping_nm_s']:.3f}Nms  tau {mg['roll_tau_ms']:.1f}ms"
         f"  set {mg['roll_set_damping_nm_s']:.2f}", _MUTED),
    ]
    y = 0.97
    for text, color in lines:
        ax.text(0.02, y, text, color=color, fontsize=9, family="monospace",
                va="top", transform=ax.transAxes)
        y -= 0.077
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
