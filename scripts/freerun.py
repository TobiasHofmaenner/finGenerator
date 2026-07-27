"""Free-run exploit study for the fingen optimizer.

Usage:
    uv run python scripts/freerun.py <out_prefix> [n_starts=10] [budget=6000] [seed=0] [workers=5]
    (defaults land three riders in ~8-15 min wall on 5 workers)

The user's framing: the optimizer's "exploits" are the gateway to
understanding, not bugs to fence off. The BUGS stay fixed (crash guard,
deficit application, washout). But the PRACTICAL CORRIDOR (per-config depth
band + geometric-AR band, optimize._DEPTH_CORRIDOR_MM / AR_GEO_*) encodes
CONVENTION — board clearance, swing weight, commercial look — not physics.
This study runs the search free of that corridor (RiderSpec(
practical_corridor=False)) on a deep budget, collects what it builds, and
writes a physics dossier per exploit: which objective term rewards the shape,
why we don't ship it (physical / model-deficiency / merely conventional), and
how the validated CFD/flex tiers would adjudicate it.

The PHYSICS gates always stay on — area anchor, side-force capacity, base
minimum, bending stress SF, wet fundamental, torsional divergence — so a free
winner is still a structurally real, force-capable blade; it just isn't
corseted into the commercial planform box.

For each of three thruster riders (60 kg cruiser, 75 kg intermediate, 95 kg
pro) the study:

  1. STARTS   Latin-hypercube samples `n_starts` points in the level-1 slider
     cube [0,1]^8 (seeded); start #0 is the template default (so the corridored
     product behaviour is literally one restart).
  2. RUNS     fires the two-stage optimize() from each start, TWICE — once
     corridored (the product baseline) and once free — with identical starts,
     seeds and `budget`. Parallel across <=6 processes.
  3. CLUSTER  groups the finals into basins (single-link agglomerative on
     euclidean distance in normalized slider space, threshold 0.10).
  4. SIGNATURE for every basin representative: the slider bounds it corners
     (<=2 %), the physics gates it rides (margin <=5 %), the spider axes it
     maxes vs the fleet envelope (rank >= 99 = extrapolation), and its distance
     outside the old corridor (depth / AR excess).
  5. DOSSIERS one markdown section per distinct exploit pattern -> the physics
     writeup (out/…-dossiers.md).
  6. VIZ      corridored winner vs free basins per rider, the signature table,
     and the free-vs-corridored objective gap (what the corridor was costing).

Winner JSONs are written for the scripts/verify_candidate.py handoff. Tier-0
analytic evaluate; nominated exploits are adjudicated by CFD/flex on demand.
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.stats import qmc

from fingen.optimize import (
    _DEPTH_CORRIDOR_MM,
    _N_SLIDERS,
    _SLIDER_BOUNDS,
    AR_GEO_MAX,
    AR_GEO_MIN,
    RiderSpec,
    _x0_sliders,
    evaluate,
    fin_from_dict,
    fin_to_dict,
    optimize,
)
from fingen.outline import metrics, planform
from fingen.params import FinConfig, FinParams
from fingen.sizing import Skill
from fingen.spider import AXES

# --- house palette (near-black bg, cyan primary, orange accent) --------------
_BG = "#0b0e11"
_PANEL = "#12171c"
_CYAN = "#7fd4e0"
_CYAN_LT = "#a7e0ea"
_ORANGE = "#f2a154"
_INK = "#e8edf0"
_MUTED = "#8a97a0"
_GREY = "#3a4650"
_GRID = (1.0, 1.0, 1.0, 0.12)
# Free-basin categorical colours: cyan / orange / light-cyan variants (the
# task's "cyan/orange variants"), each outline DIRECTLY LABELLED so identity is
# never colour-alone (the dataviz secondary-encoding rule). Corridored = grey.
_FREE_COLORS = [_CYAN, _ORANGE, _CYAN_LT, "#d55181", "#9085e9"]

# --- study config ------------------------------------------------------------
# Each rider carries its own config: the depth corridor + interference model are
# per-config, so the free-run acid test (does the search escape the band once the
# corridor is off?) has to be run in the config whose band is under test. The
# three thruster riders are the original committed study; the three non-thruster
# riders (2026-07 corridor-demotion sweep) are one representative per untested
# depth band — SINGLE (160,290), TWIN (95,150), QUAD (85,135) — matched to the
# multistart riders so the corridors-ON and corridors-OFF evidence align.
RIDERS: tuple[tuple[str, str, float, Skill, FinConfig], ...] = (
    ("60kg-cruiser", "60 kg cruiser · thruster", 60.0, Skill.CRUISER, FinConfig.THRUSTER),
    ("75kg-intermediate", "75 kg intermediate · thruster", 75.0, Skill.INTERMEDIATE, FinConfig.THRUSTER),
    ("95kg-pro", "95 kg pro · thruster", 95.0, Skill.PRO, FinConfig.THRUSTER),
    ("82kg-advanced-single", "82 kg advanced · single", 82.0, Skill.ADVANCED, FinConfig.SINGLE),
    ("72kg-intermediate-twin", "72 kg intermediate · twin", 72.0, Skill.INTERMEDIATE, FinConfig.TWIN),
    ("78kg-pro-quad", "78 kg pro · quad", 78.0, Skill.PRO, FinConfig.QUAD),
)

_CLUSTER_THRESHOLD = 0.10   # normalized-slider euclidean, matches multistart
_CORNER_EPS = 0.02          # slider within 2 % of a [0,1] bound = cornered
_GATE_EPS = 0.05            # physics-gate margin within 5 % = "riding" it
_RANK_EXTRAP = 99.0         # spider rank >= 99 = at/above the fleet envelope
_NEAR_FRAC = 0.05
# Display caps (the full data stays in the study JSON): keep the gallery and the
# signature table readable when a rough free landscape scatters into many basins.
_MAX_GALLERY = 5
_MAX_TABLE = 6
_MAX_HANDOFF = 3

_SLIDER_NAMES = tuple(name for name, _lo, _hi in _SLIDER_BOUNDS)


# --- encode / decode helpers (duplicated from multistart to avoid coupling) --


def encode_sliders(fin: FinParams) -> list[float]:
    o, f = fin.outline, fin.foil
    src = {
        "depth": o.depth, "base": o.base, "sweep": o.sweep,
        "tip_width_ratio": o.tip_width_ratio, "le_fullness": o.le_fullness,
        "te_shape": o.te_shape, "thickness_ratio": f.thickness_ratio,
        "thickness_tip_factor": fin.thickness_tip_factor,
    }
    return [(src[name] - lo) / (hi - lo) for name, lo, hi in _SLIDER_BOUNDS]


def geom_of(fin: FinParams) -> dict[str, float]:
    o = fin.outline
    return {
        "depth": o.depth, "base": o.base, "sweep": o.sweep,
        "tipw": o.tip_width_ratio, "le_full": o.le_fullness, "te_shape": o.te_shape,
        "t_c": fin.foil.thickness_ratio, "tip_factor": fin.thickness_tip_factor,
    }


def make_starts(n_starts: int, config: FinConfig, seed: int) -> list[list[float]]:
    """`n_starts` starts in [0,1]^8: #0 the template default, the rest a seeded
    Latin-hypercube sample (reproducible for a given seed)."""
    template = _x0_sliders(config)
    if n_starts <= 1:
        return [template]
    sampler = qmc.LatinHypercube(d=_N_SLIDERS, seed=seed)
    lhs = sampler.random(n_starts - 1)
    return [template] + [list(row) for row in lhs]


# --- one restart (runs in a worker process) ----------------------------------


def _run_start(task: tuple) -> dict:
    idx, rider, x0, budget, seed = task
    try:
        opt = optimize(rider, budget_evals=budget, seed=seed, x0=x0)
        fin = opt.fin
        r = opt.result
        sliders = encode_sliders(fin)
        cornered = [name for name, v in zip(_SLIDER_NAMES, sliders, strict=True)
                    if v <= _CORNER_EPS or v >= 1.0 - _CORNER_EPS]
        m = metrics(fin.outline)
        return {
            "idx": idx,
            "start": [float(v) for v in x0],
            "seed": seed,
            "final_sliders": [float(v) for v in sliders],
            "geom": geom_of(fin),
            "depth": float(fin.outline.depth),
            "base": float(fin.outline.base),
            "aspect_ratio": float(m.aspect_ratio),
            "area_mm2": float(m.area),
            "objective": float(r.objective),
            "distance": float(r.distance),
            "penalty": float(r.penalty),
            "feasible": bool(r.feasible),
            "penalties": {k: float(v) for k, v in r.penalties.items()},
            "spider_predicted": {a: float(r.spider_predicted[a]) for a in AXES},
            "spider_target": {a: float(r.spider_target[a]) for a in AXES},
            "margins": {k: float(v) for k, v in r.margins.items()},
            "grooves": int(fin.grooves.count),
            "cornered_sliders": cornered,
            "n_evals": int(opt.n_evals),
            "fin": fin_to_dict(fin),
            "error": None,
        }
    except Exception as exc:  # a crashed restart is data, not a study failure
        return {"idx": idx, "start": [float(v) for v in x0], "seed": seed,
                "error": f"{type(exc).__name__}: {exc}"}


# --- clustering into basins --------------------------------------------------


def cluster_basins(records: list[dict]) -> tuple[list[dict], list[float]]:
    valid = [r for r in records if r.get("error") is None]
    if not valid:
        return [], []
    x = np.array([r["final_sliders"] for r in valid], dtype=float)
    merges: list[float] = []
    if len(valid) == 1:
        labels = np.array([1])
    else:
        z = linkage(x, method="single", metric="euclidean")
        merges = sorted(float(d) for d in z[:, 2])
        labels = fcluster(z, t=_CLUSTER_THRESHOLD, criterion="distance")

    groups: dict[int, list[dict]] = {}
    for rec, lab in zip(valid, labels, strict=True):
        groups.setdefault(int(lab), []).append(rec)

    ordered = sorted(groups.values(), key=lambda g: min(r["objective"] for r in g))
    basins: list[dict] = []
    for rank, group in enumerate(ordered, start=1):
        rep = min(group, key=lambda r: r["objective"])
        for rec in group:
            rec["basin_rank"] = rank
        basins.append({
            "rank": rank,
            "count": len(group),
            "best_obj": rep["objective"],
            "worst_obj": max(r["objective"] for r in group),
            "representative_idx": rep["idx"],
            "geom": rep["geom"],
            "aspect_ratio": rep["aspect_ratio"],
            "area_mm2": rep["area_mm2"],
            "feasible_count": sum(1 for r in group if r["feasible"]),
            "members": sorted(r["idx"] for r in group),
        })
    return basins, merges


def verdict(records: list[dict], basins: list[dict]) -> dict:
    valid = [r for r in records if r.get("error") is None]
    objs = [r["objective"] for r in valid] or [float("nan")]
    best = min(objs)
    within = sum(1 for o in objs if o <= best * (1.0 + _NEAR_FRAC))
    return {
        "n_basins": len(basins),
        "n_valid": len(valid),
        "n_crashed": sum(1 for r in records if r.get("error") is not None),
        "n_infeasible": sum(1 for r in valid if not r["feasible"]),
        "global_best": best,
        "worst": max(objs),
        "n_within_5pct": within,
        "total_evals": sum(r["n_evals"] for r in valid),
    }


# --- exploit signature -------------------------------------------------------


def exploit_signature(rec: dict, config: FinConfig) -> dict:
    """The exploit fingerprint of one basin representative (task 3)."""
    mg = rec["margins"]
    # Physics gates the fin RIDES (feasible side within 5 %, or violated).
    gates: list[str] = []

    def rides(value: float, gate: float, *, lower: bool) -> bool:
        # lower=True: value must stay >= gate (stress/f_wet/divergence/capacity);
        #             riding = within 5 % above, or below (violated).
        # lower=False: value must stay <= gate (area_max); mirror.
        if gate <= 0:
            return False
        frac = (value - gate) / gate
        return -1.0 <= frac <= _GATE_EPS if lower else -_GATE_EPS <= frac <= 1.0

    if rides(mg["stress_sf"], 1.0, lower=True):
        gates.append("stress_sf")
    if rides(mg["f_wet_hz"], 8.0, lower=True):
        gates.append("f_wet")
    # Divergence gate is 1.6·working-speed; speed is stamped on the record.
    if rides(mg["divergence_ms"], 1.6 * rec.get("speed_ms", 0.0), lower=True):
        gates.append("divergence")
    if rides(mg["capacity_n"], mg["capacity_req_n"], lower=True):
        gates.append("capacity")
    if abs(mg["area_mm2"] - mg["area_min_mm2"]) / mg["area_min_mm2"] <= _GATE_EPS:
        gates.append("area_min")
    if abs(mg["area_mm2"] - mg["area_max_mm2"]) / mg["area_max_mm2"] <= _GATE_EPS:
        gates.append("area_max")

    maxed = [a for a in AXES if rec["spider_predicted"][a] >= _RANK_EXTRAP]

    d_lo, d_hi = _DEPTH_CORRIDOR_MM[config]
    depth = rec["depth"]
    if depth > d_hi:
        depth_excess = (depth - d_hi) / d_hi
    elif depth < d_lo:
        depth_excess = -(d_lo - depth) / d_lo
    else:
        depth_excess = 0.0
    ar = rec["aspect_ratio"]
    if ar > AR_GEO_MAX:
        ar_excess = (ar - AR_GEO_MAX) / AR_GEO_MAX
    elif ar < AR_GEO_MIN:
        ar_excess = -(AR_GEO_MIN - ar) / AR_GEO_MIN
    else:
        ar_excess = 0.0

    return {
        "cornered": rec["cornered_sliders"],
        "gates_ridden": gates,
        "maxed_axes": maxed,
        "depth_excess": depth_excess,
        "ar_excess": ar_excess,
        "patterns": basin_patterns(rec, config),
    }


def basin_patterns(rec: dict, config: FinConfig) -> list[str]:
    """Which exploit archetype(s) a basin exhibits (drives which dossiers fire)."""
    d_lo, d_hi = _DEPTH_CORRIDOR_MM[config]
    depth, ar, tc = rec["depth"], rec["aspect_ratio"], rec["geom"]["t_c"]
    mg = rec["margins"]
    pats: list[str] = []
    if depth > d_hi * 1.02:
        pats.append("deep-blade")
    if depth < d_lo * 0.98:
        pats.append("shallow-stub")
    if ar > AR_GEO_MAX * 1.02:
        pats.append("high-ar-needle")
    if ar < AR_GEO_MIN * 0.98:
        pats.append("low-ar-pancake")
    if tc <= 0.041 or mg["stress_sf"] <= 1.0 + _GATE_EPS:
        pats.append("thin-foil")
    if not pats:
        pats.append("in-corridor")
    return pats


# --- 1D probe along an exploit direction -------------------------------------


def probe_1d(fin: FinParams, rider: RiderSpec, field: str,
             values: np.ndarray) -> list[dict]:
    """Vary ONE decoded field, re-evaluate free (corridor off), tabulate the
    spider distance and per-axis ranks. `values` ordered so the last row is the
    exploit extreme. Undecodable/ invalid perturbations are skipped."""
    rows: list[dict] = []
    for v in values:
        try:
            if field == "thickness_ratio":
                f2 = replace(fin, foil=replace(fin.foil, thickness_ratio=float(v)))
            else:
                f2 = replace(fin, outline=replace(fin.outline, **{field: float(v)}))
            r = evaluate(f2, rider)
        except Exception:
            continue
        rows.append({
            "v": float(v),
            "ar": float(metrics(f2.outline).aspect_ratio),
            "distance": float(r.distance),
            "objective": float(r.objective),
            "feasible": bool(r.feasible),
            "pred": {a: float(r.spider_predicted[a]) for a in AXES},
            "penalties": {k: round(float(x), 3) for k, x in r.penalties.items()},
        })
    return rows


def reward_axis(rows: list[dict], targets: dict[str, float]) -> tuple[str | None, float]:
    """Axis whose distance contribution drops most from rows[0] -> rows[-1]
    (the exploit direction). Returns (axis, distance reduction)."""
    if len(rows) < 2:
        return None, 0.0
    a, b = rows[0], rows[-1]
    best, best_delta = None, 0.0
    for ax in AXES:
        w = 1.0 + abs(targets[ax] - 0.5)
        ca = w * (a["pred"][ax] / 100.0 - targets[ax]) ** 2
        cb = w * (b["pred"][ax] / 100.0 - targets[ax]) ** 2
        if ca - cb > best_delta:
            best, best_delta = ax, ca - cb
    return best, best_delta


# --- study a rider (both modes) ----------------------------------------------


def run_mode(rider: RiderSpec, starts: list[list[float]], budget: int, seed: int,
             workers: int) -> dict:
    tasks = [(i, rider, x0, budget, seed + i) for i, x0 in enumerate(starts)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(_run_start, tasks))
    records.sort(key=lambda r: r["idx"])
    # Stamp working speed onto each record so the divergence gate is checkable.
    for rec in records:
        if rec.get("error") is None:
            rec["speed_ms"] = rider.speed
    basins, merges = cluster_basins(records)
    return {"records": records, "basins": basins, "merges": merges,
            "verdict": verdict(records, basins)}


# --- dossiers ----------------------------------------------------------------


def _fmt_probe(rows: list[dict], vlabel: str, axes_show: tuple[str, ...]) -> list[str]:
    if not rows:
        return ["    (probe produced no valid points)"]
    head = f"    {vlabel:>9} {'AR':>6} {'dist':>7} " + " ".join(f"{a[:4]:>5}" for a in axes_show)
    out = [head]
    for r in rows:
        cells = " ".join(f"{r['pred'][a]:5.0f}" for a in axes_show)
        flag = "" if r["feasible"] else "  (infeasible)"
        out.append(f"    {r['v']:9.3f} {r['ar']:6.2f} {r['distance']:7.3f} {cells}{flag}")
    return out


_DOSSIER_META = {
    "deep-blade": ("DEEP BLADE — span beyond the per-config depth band", "depth"),
    "high-ar-needle": ("HIGH-ASPECT NEEDLE — AR beyond the commercial band", "depth"),
    "thin-foil": ("THIN FOIL — section driven to the t/c floor", "thickness_ratio"),
    "low-ar-pancake": ("LOW-ASPECT PANCAKE — AR below the commercial band", "depth"),
    "shallow-stub": ("SHALLOW STUB — span below the per-config depth band", "depth"),
}

# The intellectual core: the physics prose per exploit, reasoned from the model
# internals (hydro.py / spider.py / flex.py / sizing.py). {…} slots are filled
# with the exemplar's measured numbers at render time.
_DOSSIER_PROSE = {
    "deep-blade": {
        "reward": (
            "hold = q·S·slope·α_break (spider.raw_scores) and the "
            "hold/drive lift axes climb with span: a deeper blade at fixed base "
            "raises geometric AR, and lift_curve_slope() (DATCOM §4.1.3.2) is "
            "monotone in AR_eff = 1.7·AR_geo, so both max side force and L/D "
            "improve. A bigger blade ALSO works at a lower angle of attack "
            "(α_work = CL_work/slope falls as area and slope rise), so the "
            "margin-to-break axis (forgiveness) climbs too — that is the route "
            "that pulls a light/casual rider here, distinct from the hold/drive "
            "route that pulls a heavy one. The model prices NONE of the costs of "
            "a long blade — see below."),
        "tier0_wrong": (
            "The model has NO swing-weight and NO board-clearance term at all — "
            "depth is free in every objective axis. A blade this deep would foul "
            "the board's rocker/rail in a real bottom turn and its polar moment "
            "of inertia (∝ span^2 about the box) slows the whip a surfer feels "
            "as 'drive'. Neither quantity exists anywhere in evaluate(). The "
            "reflection factor 1.7 (hydro.REFLECTION_FACTOR, the board-as-endplate "
            "boost) is a constant; a very deep fin loads span far from the board "
            "where the end-plate effect must weaken, so AR_eff — and every axis "
            "that reads it — is optimistic at the tip. The spider ranks are "
            "normalized against a six-fin fleet that tops out near longboard-single "
            "depth; ranks >= 99 here are extrapolation past the basis."),
        "right": (
            "Deeper fins genuinely make more hold and lower induced drag — that "
            "is why guns and step-ups run longer blades. If the rider truly wants "
            "hold+drive and rides a board with the rocker clearance for it, the "
            "extra span is a real performance lever, not an artifact. The corridor "
            "bounds it by convention (side fins cluster 90–140 mm) and by the "
            "swing-weight physics the model can't see — both real, neither hydro."),
        "adjudication": (
            "verify_candidate.py L2 polar measures the lift slope vs DATCOM (gate "
            "<25 %): if CFD tracks, the hold/drive claim stands hydrodynamically. "
            "Swing weight is a rigid-body number — compute the fin's inertia "
            "about the box directly (no CFD needed) and add a clearance check "
            "against the target board's rocker; this is a MODEL GAP to close, not "
            "a tier to run. Feel is the user's Bali session. The flex track "
            "already gates that the longer cantilever survives (divergence / f_wet "
            "below)."),
    },
    "high-ar-needle": {
        "reward": (
            "speed = 1/drag and drive = L/D both improve as AR rises: induced "
            "drag cdi = CL^2/(π·0.9·AR_eff) (spider.raw_scores) collapses, "
            "and lift_curve_slope() rises with AR_eff. So a narrow, deep, "
            "high-aspect blade buys the speed and drive axes almost for free in "
            "tier-0. The stall_alpha_deg(AR_eff) heuristic floors at 12° for "
            "AR_eff > 2.5, so hold does not fall to meet it."),
        "tier0_wrong": (
            "Three tier-0 assumptions break in needle territory. (1) The DATCOM "
            "slope and the stall_alpha_deg(AR) break heuristic are anchored on the "
            "single AR≈3 [BW04] measurement (hydro.py docstrings say so "
            "explicitly, 'pending CFD calibration') — a fin whose AR ranks >= 99 "
            "is beyond the fleet basis the ranks are normalized against. (2) There "
            "is NO tip-chord Reynolds correction: a needle's tip runs at a fraction "
            "of the section Re the SK81/Zarruk validations cover (bench/sk81, "
            "Re 700k), and at low Re the section slope softens and the LE laminar-"
            "separates early — the model still hands it 2π (SECTION_SLOPE). (3) No "
            "ventilation model exists (CFD-BENCH 'Parked: free-surface "
            "ventilation'): a deep narrow blade near the surface is exactly the "
            "geometry that ventilates and dumps the lift the ranks assume."),
        "right": (
            "High-aspect foils really do have lower induced drag — this is the "
            "least controversial claim in the study. Race and downwind hydrofoils "
            "chase exactly this. If the section holds its polar at the tip Re and "
            "the blade stays submerged, a high-AR fin is a legitimate speed/drive "
            "tool; the fleet simply doesn't contain one, so it reads as "
            "extrapolation rather than error."),
        "adjudication": (
            "verify_candidate.py L2 polar first — the slope-vs-DATCOM gate tests "
            "the induced-drag lever directly. The tip-Re / early-separation "
            "question is the level-4 resolved-wall + γ-Reθ transition tier "
            "(bench/bw04-polar-transition, the validated machinery) run at the "
            "tip-chord Re. Ventilation needs the parked multiphase tier — it "
            "CANNOT be adjudicated today, so a needle ships only with that caveat "
            "flagged. Bali confirms whether the speed is usable or twitchy."),
    },
    "thin-foil": {
        "reward": (
            "speed and drive rise as t/c falls: profile drag cd0 = 2·cf·(1 + "
            "2t + 60t^4) (spider._cd0, a Hoerner form factor) drops monotonically "
            "with thickness, so 1/drag and L/D both climb. The search drives t/c "
            "to the 0.04 FoilParams floor and rides the bending-stress gate down "
            "toward SF = 1."),
        "tier0_wrong": (
            "The stress gate is base_bending_stress_mpa vs the material allowable "
            "(sizing.py: datasheet XY bending × 0.5 print knockdown / SF 2) at "
            "the STATIC transient peak load only. It has NO impact term and NO "
            "fatigue term: a t/c-0.04 printed blade that clears static SF=1 can "
            "still fail on a rock strike or on O(1 Hz) wave-forced cyclic loading "
            "over a session's millions of cycles, and seawater soak lowers the "
            "modulus the gate trusts (all three are explicit open items in "
            "CFD-BENCH item 7, the user's structure bench). On the hydro side the "
            "section is now thinner than the SK81/Zarruk validated t/c band, so "
            "the 2π slope and the cd0 form factor are extrapolated, and a sharp "
            "thin LE separates earlier than the attached-flow model assumes."),
        "right": (
            "Thin foils are genuinely lower-drag, and the stress allowable is "
            "already doubly conservative (0.5 anisotropy knockdown AND a factor-2 "
            "SF baked in before the gate). If the CF-thermoplastic actually carries "
            "the static, impact and fatigue loads, a thin race section is a real "
            "speed gain the corridor never restricted — the corridor is about "
            "planform, not thickness, so a thin winner is a pure physics-gate "
            "story, not a convention one."),
        "adjudication": (
            "FEM (scripts/fin_fem_stress.py) recomputes the peak-load stress off "
            "the beam idealization for the static claim. The impact/fatigue/soak "
            "questions are the user's physical structure rig (CFD-BENCH 7: "
            "load-to-failure vs FORCE_SF, seawater-soak stiffness recheck) — the "
            "ONLY tier that can kill or clear them. Whether the thin section keeps "
            "its polar is the SK81/Zarruk section tier + the transition tier at "
            "the fin Re. A thin winner is nominated to the STRUCTURE bench, not "
            "CFD, first."),
    },
    "low-ar-pancake": {
        "reward": (
            "forgiveness = α_break − α_work (spider.raw_scores), and "
            "stall_alpha_deg(AR_eff) = min(12 + 8·(2.5 − AR_eff), 30) grows as "
            "AR falls — a low-AR blade is handed a break angle up to 30°, so its "
            "forgiveness (and often pivot, via the low yaw stiffness of a short "
            "span) rank climbs. A cruiser's high forgiveness target pulls the "
            "search straight down here."),
        "tier0_wrong": (
            "stall_alpha_deg is the SINGLE least-calibrated line in the hydro "
            "model — its own docstring calls it 'Heuristic anchored at the AR-3 "
            "measurement [BW04], pending CFD calibration' and reaches for "
            "delta-wing vortex-lift data (25–35°) with no low-AR fin measurement "
            "behind it. The URANS study (CFD-BENCH 5) is explicit: post-knee "
            "magnitudes are transition physics steady RANS cannot produce, so "
            "'near-stall axes use the knee LOCATION and treat post-knee magnitudes "
            "as lower bounds' — forgiveness for a pancake is riding an "
            "un-validated break-angle extrapolation. And at AR < 1 the lifting-"
            "line induced-drag and the constant reflection-factor end-plate model "
            "are both stretched well past where they were built."),
        "right": (
            "Low-AR planforms really do stall late — delta-wing vortex lift is "
            "genuine physics [Pol66, Tra23], and fish keels ARE low-aspect and "
            "forgiving by reputation. For a cruiser who wants a loose, hard-to-"
            "spin-out fin, a low-AR blade is a real, rideable idiom; the model's "
            "instinct is directionally right even where its magnitude is a guess."),
        "adjudication": (
            "The break LOCATION is validated to ±1–3° but only at AR≈3; a "
            "low-AR CFD polar (verify_candidate.py, angles extended past the knee, "
            "or a dedicated high-α URANS) measures the actual break for THIS "
            "planform — confirm the late break and the pancake earns its "
            "forgiveness; find an early break and it's a model artifact. The "
            "vortex-lift magnitude needs URANS/transition (known-hard, parked "
            "honestly). Bali arbitrates whether 'forgiving' reads as intended."),
    },
    "shallow-stub": {
        "reward": (
            "a short blade cuts area and span: pivot rises (low yaw stiffness) and "
            "the fin is cheap on swing weight the model can't price. The search "
            "reaches here when pivot/looseness targets dominate and no physics "
            "gate floors the span."),
        "tier0_wrong": (
            "Below the depth band the area anchor usually binds first (capacity / "
            "area_min), so a stub is often ALREADY infeasible on physics — check "
            "the gates ridden. Where it is feasible, the same low-AR caveats apply "
            "(uncalibrated break angle, stretched end-plate model), and the model "
            "still has no swing-weight term to reward the stub for the one thing it "
            "is actually good at."),
        "right": (
            "Small, shallow fins are a real category (skimboard / small-wave "
            "loosening fins). If the rider wants maximum looseness and the anchor "
            "still passes, a stub is a legitimate answer the depth band forbids by "
            "convention."),
        "adjudication": (
            "Confirm feasibility first (the anchor is physics, not convention); "
            "then a low-AR CFD polar for the break, and the field session for "
            "whether the looseness is fun or uncontrollable."),
    },
}


def build_dossiers(riders_out: list[dict], out_md: Path) -> list[tuple[str, str]]:
    """Write out/…-dossiers.md; return [(pattern, headline)] for the summary."""
    # Collect, per pattern, the strongest exemplar basin across all riders.
    exemplars: dict[str, dict] = {}
    for ro in riders_out:
        rider = ro["rider_free"]
        for basin in ro["free"]["basins"]:
            rep = next(r for r in ro["free"]["records"]
                       if r["idx"] == basin["representative_idx"])
            sig = basin["signature"]
            for pat in sig["patterns"]:
                if pat == "in-corridor":
                    continue
                score = _pattern_strength(pat, rep)
                cur = exemplars.get(pat)
                if cur is None or score > cur["score"]:
                    exemplars[pat] = {"score": score, "rep": rep, "sig": sig,
                                      "rider": rider, "rider_label": ro["label"],
                                      "basin": basin}

    lines: list[str] = []
    lines.append("# Free-run exploit dossiers")
    lines.append("")
    lines.append("Generated by `scripts/freerun.py`. Each dossier is one exploit "
                 "pattern the optimizer built once the PRACTICAL CORRIDOR "
                 "(per-config depth band + geometric-AR band) was switched off "
                 "(`RiderSpec(practical_corridor=False)`). The load-bearing "
                 "PHYSICS gates — area anchor, side-force capacity, base minimum, "
                 "bending stress SF, wet fundamental, torsional divergence — "
                 "stayed ON, so every shape below is a structurally real, "
                 "force-capable blade. The question each dossier answers: which "
                 "objective term rewards the shape, why we don't ship it (physical "
                 "/ model-deficiency / merely conventional), and how the validated "
                 "tiers would adjudicate it.")
    lines.append("")

    headlines: list[tuple[str, str]] = []
    if not exemplars:
        lines.append("## No exploits escaped the physics gates")
        lines.append("")
        lines.append("For these three riders the free search stayed inside the "
                     "old corridor on every basin: the PHYSICS gates (area / "
                     "capacity / stress / divergence) bind before the convention "
                     "corridor does, so the depth and AR bands were slack, not "
                     "load-bearing, here. That is itself the finding — the "
                     "objective-gap panel in the gallery quantifies it at ~0.")
        out_md.write_text("\n".join(lines) + "\n")
        return [("none", "no exploit escaped the physics gates for these riders")]

    order = ["low-ar-pancake", "high-ar-needle", "deep-blade", "thin-foil", "shallow-stub"]
    for pat in order:
        if pat not in exemplars:
            continue
        ex = exemplars[pat]
        rep, sig, rider = ex["rep"], ex["sig"], ex["rider"]
        title, field = _DOSSIER_META[pat]
        prose = _DOSSIER_PROSE[pat]
        g = rep["geom"]
        targets = rider.resolved_targets()

        # 1D probe along the exploit direction from the corridor edge outward.
        rows = _probe_for_pattern(pat, rep, rider, field)
        raxis, rdelta = reward_axis(rows, targets)
        axes_show = _axes_for_pattern(pat)

        headline = _headline(pat, ex, raxis)
        headlines.append((pat, headline))

        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"*Exemplar: {ex['rider_label']}, free basin "
                     f"{ex['basin']['rank']} (restart #{rep['idx']}).*  "
                     f"Headline: {headline}")
        lines.append("")
        # THE SHAPE
        lines.append("### The shape")
        lines.append("")
        lines.append(f"- depth **{g['depth']:.0f} mm**  base **{g['base']:.0f} mm**  "
                     f"sweep {g['sweep']:.0f}°  AR_geo **{rep['aspect_ratio']:.2f}**  "
                     f"t/c **{g['t_c']:.3f}**  tip-width {g['tipw']:.2f}  "
                     f"grooves {rep['grooves']}")
        lines.append(f"- area {rep['area_mm2']:.0f} mm²  objective "
                     f"{rep['objective']:.3f} (distance {rep['distance']:.3f}, "
                     f"penalty {rep['penalty']:.3f})  "
                     f"{'FEASIBLE' if rep['feasible'] else 'INFEASIBLE'}")
        de, ae = sig["depth_excess"], sig["ar_excess"]
        lines.append(f"- outside the old corridor by: depth "
                     f"{de * 100:+.0f} %, AR {ae * 100:+.0f} %  "
                     f"({rider.config.value} corridor depth "
                     f"{_DEPTH_CORRIDOR_MM[rider.config][0]:.0f}–"
                     f"{_DEPTH_CORRIDOR_MM[rider.config][1]:.0f} mm, AR "
                     f"{AR_GEO_MIN:.2f}–{AR_GEO_MAX:.2f})")
        corners = ", ".join(sig["cornered"]) or "none"
        gates = ", ".join(sig["gates_ridden"]) or "none"
        maxed = ", ".join(sig["maxed_axes"]) or "none"
        lines.append(f"- signature: corners [{corners}] · rides gates [{gates}] "
                     f"· maxes fleet axes [{maxed}]")
        lines.append(f"- outline: gallery panel for {ex['rider_label']} "
                     f"(free basin {ex['basin']['rank']})")
        lines.append("")
        # WHAT REWARDS IT
        lines.append("### What rewards it")
        lines.append("")
        lines.append(prose["reward"])
        lines.append("")
        lines.append(f"1D probe along `{field}` (free eval, corridor off; last row "
                     f"is the exploit extreme):")
        lines.append("")
        lines.append("```")
        lines.extend(_fmt_probe(rows, field, axes_show))
        lines.append("```")
        lines.append("")
        if raxis is not None:
            lines.append(f"The probe moves **{raxis}** most toward its target "
                         f"(distance contribution −{rdelta:.3f} over the sweep) — "
                         f"that is the term paying for this exploit.")
        else:
            lines.append("The probe shows no single axis improving — the exploit "
                         "is driven by a gate the free search unlocked, not a "
                         "spider axis; read the gates-ridden line above.")
        lines.append("")
        # WHY TIER-0 MIGHT BE WRONG
        lines.append("### Why tier-0 might be wrong there")
        lines.append("")
        lines.append(prose["tier0_wrong"])
        lines.append("")
        # WHY IT MIGHT BE RIGHT
        lines.append("### Why it might be right (the honest lucky-punch case)")
        lines.append("")
        lines.append(prose["right"])
        lines.append("")
        # ADJUDICATION
        lines.append("### Adjudication path")
        lines.append("")
        lines.append(prose["adjudication"])
        lines.append("")

    out_md.write_text("\n".join(lines) + "\n")
    return headlines


def _pattern_strength(pat: str, rep: dict) -> float:
    if pat == "deep-blade":
        return rep["depth"]
    if pat == "shallow-stub":
        return -rep["depth"]
    if pat == "high-ar-needle":
        return rep["aspect_ratio"]
    if pat == "low-ar-pancake":
        return -rep["aspect_ratio"]
    if pat == "thin-foil":
        return -rep["geom"]["t_c"]
    return 0.0


def _axes_for_pattern(pat: str) -> tuple[str, ...]:
    return {
        "deep-blade": ("hold", "drive", "speed", "forgiveness"),
        "high-ar-needle": ("speed", "drive", "hold", "forgiveness"),
        "thin-foil": ("speed", "drive", "hold", "pivot"),
        "low-ar-pancake": ("forgiveness", "pivot", "hold", "drive"),
        "shallow-stub": ("pivot", "forgiveness", "hold", "speed"),
    }.get(pat, AXES[:4])


def _probe_for_pattern(pat: str, rep: dict, rider: RiderSpec, field: str) -> list[dict]:
    fin = fin_from_dict(rep["fin"])
    d_lo, d_hi = _DEPTH_CORRIDOR_MM[rider.config]
    if field == "thickness_ratio":
        # From a healthy 0.10 section down to the 0.04 floor (exploit extreme).
        values = np.linspace(0.10, 0.04, 7)
    elif pat in ("low-ar-pancake", "shallow-stub"):
        # From the corridor floor DOWN past the exemplar (exploit extreme) — a
        # wide span so the trend dominates the rank-quantization jitter.
        lo = max(45.0, min(rep["depth"] - 10.0, d_lo - 30.0))
        values = np.linspace(d_lo, lo, 7)
    else:
        # Deep / needle: from the corridor ceiling UP past the exemplar (extreme).
        hi = min(290.0, max(rep["depth"] + 20.0, d_hi + 60.0))
        values = np.linspace(d_hi, hi, 7)
    return probe_1d(fin, rider, field, values)


def _headline(pat: str, ex: dict, raxis: str | None) -> str:
    g = ex["rep"]["geom"]
    ar = ex["rep"]["aspect_ratio"]
    axis = raxis or "a gate"
    if pat == "deep-blade":
        return (f"a {g['depth']:.0f} mm blade (AR {ar:.2f}) buys {axis} the "
                f"model never charges for span/swing-weight")
    if pat == "high-ar-needle":
        return (f"AR {ar:.2f} collapses induced drag to lift {axis}, on a DATCOM/"
                f"stall/Re extrapolation past the fleet")
    if pat == "thin-foil":
        return (f"t/c {g['t_c']:.3f} rides the static stress gate to lift {axis} "
                f"with no impact/fatigue term behind it")
    if pat == "low-ar-pancake":
        return (f"AR {ar:.2f} banks {axis} on the least-calibrated line in the "
                f"model, stall_alpha_deg(AR)")
    if pat == "shallow-stub":
        return (f"a {g['depth']:.0f} mm stub banks {axis}; check the anchor still "
                f"passes on physics")
    return f"exploits {axis}"


# --- gallery -----------------------------------------------------------------


def _outline_xy(fin: FinParams) -> tuple[np.ndarray, np.ndarray]:
    z, x_le, chord = planform(fin.outline)
    live = chord > 0.3
    x = np.concatenate((x_le[live], (x_le + chord)[live][::-1]))
    y = np.concatenate((z[live], z[live][::-1]))
    return x, y


def render_gallery(out_png: Path, riders_out: list[dict], n_starts: int,
                   budget: int, seed: int, wall_s: float) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(riders_out)
    fig = plt.figure(figsize=(17.5, 16.0), facecolor=_BG)
    fig.text(0.5, 0.982, "T-FINS optimizer — free-run exploit study",
             color=_INK, fontsize=23, family="monospace", ha="center", weight="bold")
    fig.text(0.5, 0.962,
             f"corridored (grey) vs free basins (cyan/orange) · {n_starts} "
             f"starts · {budget} evals/restart · seed {seed} · wall {wall_s:.0f}s",
             color=_MUTED, fontsize=13, family="monospace", ha="center")

    gs = fig.add_gridspec(3, n, left=0.05, right=0.975, top=0.93, bottom=0.05,
                          hspace=0.34, wspace=0.22,
                          height_ratios=[1.25, 0.85, 1.35])

    # Row 0: outline overlays, one per rider.
    for i, ro in enumerate(riders_out):
        ax = fig.add_subplot(gs[0, i])
        _draw_overlay(ax, ro)

    # Row 1: free-vs-corridored objective gap (grouped bars).
    ax_obj = fig.add_subplot(gs[1, :])
    _draw_objective_gap(ax_obj, riders_out)

    # Row 2: exploit-signature table.
    ax_tab = fig.add_subplot(gs[2, :])
    _draw_signature_table(ax_tab, riders_out)

    fig.savefig(out_png, dpi=115, facecolor=_BG)
    plt.close(fig)


def _draw_overlay(ax, ro: dict) -> None:
    ax.set_facecolor(_PANEL)
    # Corridored winner (best corridored basin) in grey.
    cbasins = ro["corridored"]["basins"]
    if cbasins:
        crep = next(r for r in ro["corridored"]["records"]
                    if r["idx"] == cbasins[0]["representative_idx"])
        fin = fin_from_dict(crep["fin"])
        x, y = _outline_xy(fin)
        ax.fill(x, y, color=_GREY, alpha=0.28)
        ax.plot(x, y, color=_GREY, lw=2.0,
                label=f"corridored  obj {crep['objective']:.3f}")
    # Free basins in cyan/orange variants, directly labelled (top few by obj).
    for bi, basin in enumerate(ro["free"]["basins"][:_MAX_GALLERY]):
        rep = next(r for r in ro["free"]["records"]
                   if r["idx"] == basin["representative_idx"])
        fin = fin_from_dict(rep["fin"])
        x, y = _outline_xy(fin)
        color = _FREE_COLORS[bi % len(_FREE_COLORS)]
        pats = [p for p in basin["signature"]["patterns"] if p != "in-corridor"]
        tag = pats[0] if pats else "in-corridor"
        ax.plot(x, y, color=color, lw=2.3,
                label=f"free b{basin['rank']} ({basin['count']}) {tag} "
                      f"obj {rep['objective']:.3f}")
        ax.fill(x, y, color=color, alpha=0.10)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_title(ro["label"], color=_INK, fontsize=11, family="monospace")
    ax.tick_params(colors=_MUTED, labelsize=6)
    for s in ax.spines.values():
        s.set_color("#2a333b")
    ax.legend(loc="lower right", facecolor=_PANEL, edgecolor=_GRID,
              labelcolor=_INK, fontsize=6.5)


def _draw_objective_gap(ax, riders_out: list[dict]) -> None:
    ax.set_facecolor(_PANEL)
    labels = [ro["label"].split(" ·")[0] for ro in riders_out]
    corr = [ro["corridored"]["verdict"]["global_best"] for ro in riders_out]
    free = [ro["free"]["verdict"]["global_best"] for ro in riders_out]
    x = np.arange(len(labels))
    w = 0.36
    ax.bar(x - w / 2, corr, w, color=_GREY, edgecolor=_BG, linewidth=1.0,
           label="corridored best", zorder=3)
    ax.bar(x + w / 2, free, w, color=_CYAN, edgecolor=_BG, linewidth=1.0,
           label="free best", zorder=3)
    for xi, (c, f) in enumerate(zip(corr, free, strict=True)):
        drop = 100.0 * (c - f) / c if c else 0.0
        ax.text(xi, max(c, f), f" corridor cost {drop:+.0f}%", color=_ORANGE,
                fontsize=9, family="monospace", ha="center", va="bottom")
        ax.text(xi - w / 2, c, f"{c:.3f}", color=_INK, fontsize=8,
                family="monospace", ha="center", va="bottom")
        ax.text(xi + w / 2, f, f"{f:.3f}", color=_INK, fontsize=8,
                family="monospace", ha="center", va="bottom")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, color=_INK, fontsize=10, family="monospace")
    ax.set_ylabel("best objective (lower = better)", color=_MUTED, fontsize=9)
    ax.set_title("what the corridor was costing — free vs corridored best objective",
                 color=_INK, fontsize=11, family="monospace")
    ax.tick_params(colors=_MUTED, labelsize=8)
    ax.grid(color=_GRID, lw=0.6, axis="y")
    for s in ax.spines.values():
        s.set_color("#2a333b")
    ax.legend(loc="upper right", facecolor=_PANEL, edgecolor=_GRID,
              labelcolor=_INK, fontsize=9)


def _draw_signature_table(ax, riders_out: list[dict]) -> None:
    ax.set_facecolor(_PANEL)
    ax.axis("off")
    ax.set_title("exploit signatures — free basin representatives",
                 color=_INK, fontsize=11, family="monospace", loc="left")
    header = (f"{'rider':<10}{'b':>2} {'obj':>6} {'depth':>6}{'base':>6}{'AR':>6}"
              f"{'t/c':>6}  {'corners':<20}{'gates':<18}{'maxed':<16}"
              f"{'d%':>5}{'AR%':>6}  pattern")
    rows = [(header, _MUTED)]
    for ro in riders_out:
        short = ro["label"].split(" ·")[0]
        for basin in ro["free"]["basins"][:_MAX_TABLE]:
            rep = next(r for r in ro["free"]["records"]
                       if r["idx"] == basin["representative_idx"])
            sig = basin["signature"]
            g = rep["geom"]
            corners = ",".join(s[:6] for s in sig["cornered"])[:19] or "-"
            gates = ",".join(sig["gates_ridden"])[:17] or "-"
            maxed = ",".join(a[:4] for a in sig["maxed_axes"])[:15] or "-"
            pats = [p for p in sig["patterns"] if p != "in-corridor"] or ["in-corridor"]
            color = _FREE_COLORS[(basin["rank"] - 1) % len(_FREE_COLORS)]
            line = (f"{short:<10}{basin['rank']:>2} {rep['objective']:>6.3f} "
                    f"{g['depth']:>6.0f}{g['base']:>6.0f}{rep['aspect_ratio']:>6.2f}"
                    f"{g['t_c']:>6.3f}  {corners:<20}{gates:<18}{maxed:<16}"
                    f"{sig['depth_excess'] * 100:>5.0f}{sig['ar_excess'] * 100:>6.0f}"
                    f"  {'/'.join(pats)}")
            rows.append((line, color))
    y = 0.98
    for text, color in rows:
        ax.text(0.005, y, text, color=color, fontsize=8.0, family="monospace",
                va="top", transform=ax.transAxes)
        y -= 0.052


# --- handoff JSONs (verify_candidate compatible) -----------------------------


def build_handoff(rider: RiderSpec, rec: dict, sig: dict | None) -> dict:
    return {
        "rider": {
            "weight_kg": rider.weight_kg, "skill": rider.skill.name,
            "speed_ms": rider.speed, "config": rider.config.value,
            "material": rider.material,
            "spider_targets": rider.resolved_targets(),
            "practical_corridor": rider.practical_corridor,
        },
        "fin": rec["fin"],
        "objective": rec["objective"], "distance": rec["distance"],
        "penalty": rec["penalty"], "feasible": rec["feasible"],
        "spider_predicted": rec["spider_predicted"],
        "spider_target": rec["spider_target"],
        "margins": rec["margins"], "penalties": rec["penalties"],
        "planform": {"area_mm2": rec["area_mm2"], "aspect_ratio": rec["aspect_ratio"]},
        "search": {"n_evals": rec["n_evals"], "seed": rec["seed"]},
        "exploit_signature": sig,
    }


# --- driver ------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out_prefix = Path(sys.argv[1])
    n_starts = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    # Cap at 5: a sibling multistart study shares the box (it too runs 5).
    workers = int(sys.argv[5]) if len(sys.argv) > 5 else min(5, os.cpu_count() or 5)
    # argv[6]: comma-separated slug subset (run only these riders — used to run
    # just the new non-thruster reps without recomputing the committed thruster
    # three). None -> all riders in the table.
    only = set(sys.argv[6].split(",")) if len(sys.argv) > 6 else None
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    riders = [r for r in RIDERS if only is None or r[0] in only]
    print(f"freerun: {n_starts} starts x {budget} evals x {len(riders)} riders "
          f"x 2 modes, seed {seed}, {workers} workers", flush=True)

    t0 = time.time()
    riders_out: list[dict] = []
    for slug, label, weight, skill, config in riders:
        starts = make_starts(n_starts, config, seed)
        rider_corr = RiderSpec(weight_kg=weight, skill=skill, config=config,
                               practical_corridor=True)
        rider_free = RiderSpec(weight_kg=weight, skill=skill, config=config,
                               practical_corridor=False)
        corr = run_mode(rider_corr, starts, budget, seed, workers)
        free = run_mode(rider_free, starts, budget, seed, workers)
        # Annotate free basins with their exploit signatures.
        for basin in free["basins"]:
            rep = next(r for r in free["records"]
                       if r["idx"] == basin["representative_idx"])
            basin["signature"] = exploit_signature(rep, config)
        riders_out.append({
            "slug": slug, "label": label,
            "rider_corr": rider_corr, "rider_free": rider_free,
            "corridored": corr, "free": free,
        })
        cv, fv = corr["verdict"], free["verdict"]
        drop = 100.0 * (cv["global_best"] - fv["global_best"]) / cv["global_best"] \
            if cv["global_best"] else 0.0
        print(f"[{slug}] corridored: {cv['n_basins']} basin(s) best "
              f"{cv['global_best']:.3f}  |  free: {fv['n_basins']} basin(s) best "
              f"{fv['global_best']:.3f}  (corridor cost {drop:+.0f}%)", flush=True)
        for basin in free["basins"]:
            sig = basin["signature"]
            g = basin["geom"]
            pats = "/".join(p for p in sig["patterns"] if p != "in-corridor") or "in-corridor"
            print(f"    free b{basin['rank']}: {basin['count']}/{fv['n_valid']} "
                  f"depth {g['depth']:.0f} base {g['base']:.0f} AR "
                  f"{basin['aspect_ratio']:.2f} t/c {g['t_c']:.3f}  "
                  f"gates[{','.join(sig['gates_ridden']) or '-'}] "
                  f"maxed[{','.join(sig['maxed_axes']) or '-'}] "
                  f"d{sig['depth_excess'] * 100:+.0f}% AR{sig['ar_excess'] * 100:+.0f}%  "
                  f"-> {pats}", flush=True)
    wall_s = time.time() - t0

    # Dossiers, gallery, handoffs, study JSON.
    dossiers_md = Path(f"{out_prefix}-dossiers.md")
    headlines = build_dossiers(riders_out, dossiers_md)

    gallery_png = Path(f"{out_prefix}-gallery.png")
    render_gallery(gallery_png, riders_out, n_starts, budget, seed, wall_s)

    written = [dossiers_md, gallery_png]
    for ro in riders_out:
        slug = ro["slug"]
        cbasins = ro["corridored"]["basins"]
        if cbasins:
            crep = next(r for r in ro["corridored"]["records"]
                        if r["idx"] == cbasins[0]["representative_idx"])
            p = Path(f"{out_prefix}-{slug}-corridored.json")
            p.write_text(json.dumps(build_handoff(ro["rider_corr"], crep, None),
                                    indent=2) + "\n")
            written.append(p)
        for basin in ro["free"]["basins"][:_MAX_HANDOFF]:
            rep = next(r for r in ro["free"]["records"]
                       if r["idx"] == basin["representative_idx"])
            p = Path(f"{out_prefix}-{slug}-free-b{basin['rank']}.json")
            p.write_text(json.dumps(
                build_handoff(ro["rider_free"], rep, basin["signature"]),
                indent=2) + "\n")
            written.append(p)

    # Full study JSON (records carry fins + signatures + margins).
    study = {
        "study": {"n_starts": n_starts, "budget": budget, "seed": seed,
                  "workers": workers, "wall_s": wall_s,
                  "cluster_threshold": _CLUSTER_THRESHOLD},
        "ar_band": [AR_GEO_MIN, AR_GEO_MAX],
        "riders": [{
            "slug": ro["slug"], "label": ro["label"],
            "weight_kg": ro["rider_free"].weight_kg,
            "skill": ro["rider_free"].skill.name,
            "config": ro["rider_free"].config.value,
            "corridor": {"depth_mm": list(_DEPTH_CORRIDOR_MM[ro["rider_free"].config]),
                         "ar_band": [AR_GEO_MIN, AR_GEO_MAX]},
            "corridored": {"verdict": ro["corridored"]["verdict"],
                           "basins": ro["corridored"]["basins"]},
            "free": {"verdict": ro["free"]["verdict"], "basins": ro["free"]["basins"],
                     "records": ro["free"]["records"]},
        } for ro in riders_out],
    }
    def _jsafe(o):
        if isinstance(o, np.integer | np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)

    study_json = Path(f"{out_prefix}-study.json")
    study_json.write_text(json.dumps(study, indent=2, default=_jsafe) + "\n")
    written.append(study_json)

    print(f"\nwall {wall_s:.0f}s  wrote:", flush=True)
    for p in written:
        print(f"  {p}", flush=True)
    print("\ndossier headlines:", flush=True)
    for pat, hl in headlines:
        print(f"  [{pat}] {hl}", flush=True)


if __name__ == "__main__":
    main()
