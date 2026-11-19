"""Pareto-frontier characterisation of the fingen design space (gen-3 item 0.1).

    uv run python scripts/frontier.py <rider> [--n1 N] [--n2 N] [--workers W] [--seed S]

    rider:  omar   = 60 kg PRO thruster, 8.5 m/s, ppa-cf, FCS II
            ref75  = 75 kg INTERMEDIATE thruster, skill-default speed, ppa-cf, FCS II

Question (docs/GEN3-PLAN.md §0.1): before we rebuild the objective as "maximise
the monotone goods, then consult the spider for tradeoffs", what does the
frontier of those goods look like for a real rider, which knobs move along it,
where does it sit relative to the stall knee and the gates, and how much range
do the TASTE quantities (yaw stiffness, roll damping, release proxy) span
across it? A lever whose quantity barely moves across the frontier cannot be
offered as a lever.

Method: stage-A slider cube (8 genes, offsets and grooves off, exactly
`optimize._decode`), uniform census of n1 points, then n2 points resampled
around the feasible ones (the feasible shell is 2–5 % of the cube). Every
feasible design is measured in PHYSICAL units through the same tier-0 code the
optimizer uses (spider.raw_scores + evaluate margins + a turn-load drag). The
non-dominated set in (−trim drag, L/D at the working load, effective max side
force, peak-turn margin) is the frontier. Everything is written to
out/frontier-<rider>.json; a markdown summary to out/frontier-<rider>.md.
"""

from __future__ import annotations

import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from fingen import spider
from fingen.hydro import (lift_curve_slope, stall_alpha_deg, stall_cl_knee,
                          stall_drag_cd, zero_lift_alpha_deg)
from fingen.optimize import (_DEPTH_CORRIDOR_MM, _SLIDER_BOUNDS, RiderSpec,
                             _decode, evaluate)
from fingen.outline import metrics
from fingen.params import FinConfig, TabSystem
from fingen.sizing import RHO_SEAWATER, Skill, anchor

SLIDERS = tuple(b[0] for b in _SLIDER_BOUNDS)
GOODS = ("drag_trim_n", "ld_work", "f_max_eff_n", "margin_peak_deg")  # min, max, max, max
GOOD_SIGN = (-1.0, 1.0, 1.0, 1.0)
TASTES = ("yaw_stiffness_nm_rad", "roll_damping_nm_s", "release_proxy")
FIELDS = SLIDERS + (
    "area_mm2", "aspect_ratio", "t_c",
    "drag_trim_n", "drag_peak_n", "ld_work", "ld_peak", "f_max_eff_n", "f_max_raw_n",
    "margin_peak_deg", "alpha_peak_deg", "a_break_deg", "cl_work_over_knee", "cl_peak_over_knee",
    "yaw_stiffness_nm_rad", "roll_damping_nm_s", "release_proxy",
    "stress_sf", "stress_sf_roll", "tip_deflection_mm", "washout_pct", "objective_today",
)

RIDERS = {
    "omar": dict(weight_kg=60.0, skill="PRO", speed_ms=8.5),
    "ref75": dict(weight_kg=75.0, skill="INTERMEDIATE", speed_ms=None),
}

_R: RiderSpec | None = None
_FPEAK: float = float("nan")


def _rider(preset: str) -> RiderSpec:
    p = RIDERS[preset]
    return RiderSpec(weight_kg=p["weight_kg"], skill=Skill[p["skill"]], speed_ms=p["speed_ms"],
                     config=FinConfig.THRUSTER, material="ppa-cf", tabs=TabSystem("click_tab"),
                     stress_sf_min=1.5, washout_max=0.015, tip_deflection_max_frac=0.15)


def _init(preset: str) -> None:
    global _R, _FPEAK
    _R = _rider(preset)
    _FPEAK = anchor(_R.weight_kg, _R.skill, design_speed=_R.speed, config=_R.config,
                    material=_R.material, tabs=_R.tabs).force_peak_n


def _measure(x: np.ndarray) -> tuple[float, ...] | None:
    """One slider vector -> physical measurements, or None if infeasible/reject."""
    assert _R is not None
    try:
        fin = _decode(np.asarray(x, dtype=float), _R.config, use_offsets=False, use_grooves=False)
        ev = evaluate(fin, _R)
    except ValueError:
        return None
    if not ev.feasible:
        return None
    speed = _R.speed
    q = 0.5 * RHO_SEAWATER * speed**2
    m = metrics(fin.outline)
    area = m.area * 1e-6
    raw = spider.raw_scores(fin, speed, _R.weight_kg, _FPEAK)
    slope, ar_eff = lift_curve_slope(fin)
    a_break = stall_alpha_deg(ar_eff)
    a0 = zero_lift_alpha_deg(fin)
    cd0 = spider._cd0(fin, speed)
    knee = stall_cl_knee(slope, ar_eff)
    cl_max = slope * math.radians(a_break - a0)
    cl_work = spider.work_force_n(_R.weight_kg) / (q * area)
    cl_peak = _FPEAK / (q * area)
    washout = max(0.0, min(1.0, 1.0 + ev.flex.lift_knockdown))
    if cl_peak <= cl_max:
        cd_peak = cd0 + cl_peak**2 / (math.pi * 0.9 * ar_eff) + stall_drag_cd(cl_peak, slope, ar_eff)
        drag_peak = q * area * cd_peak
        ld_peak = cl_peak / cd_peak
    else:
        drag_peak = ld_peak = float("nan")  # cannot make the peak force at any angle
    vals = {name: lo + min(1.0, max(0.0, float(x[i]))) * (hi - lo)
            for i, (name, lo, hi) in enumerate(_SLIDER_BOUNDS)}
    mg = ev.margins
    rec = dict(vals)
    rec.update({
        "area_mm2": m.area, "aspect_ratio": m.aspect_ratio, "t_c": fin.foil.thickness_ratio,
        "drag_trim_n": 1.0 / raw["speed"], "drag_peak_n": drag_peak,
        "ld_work": raw["drive"] * washout, "ld_peak": ld_peak,
        "f_max_eff_n": raw["hold"] * washout, "f_max_raw_n": raw["hold"],
        "margin_peak_deg": raw["forgiveness"], "alpha_peak_deg": mg["alpha_peak_deg"],
        "a_break_deg": a_break, "cl_work_over_knee": cl_work / knee, "cl_peak_over_knee": cl_peak / knee,
        "yaw_stiffness_nm_rad": 1.0 / raw["pivot"], "roll_damping_nm_s": raw["stability"],
        "release_proxy": raw["release"],
        "stress_sf": mg["stress_sf"], "stress_sf_roll": mg["stress_sf_roll"],
        "tip_deflection_mm": mg["tip_deflection_mm"], "washout_pct": mg["washout_pct"],
        "objective_today": ev.objective,
    })
    return tuple(float(rec[f]) for f in FIELDS)


def _batch(X: np.ndarray) -> list[tuple[float, ...] | None]:
    return [_measure(x) for x in X]


def _harvest(ex: ProcessPoolExecutor, X: np.ndarray, chunk: int = 128) -> np.ndarray:
    chunks = [X[i:i + chunk] for i in range(0, len(X), chunk)]
    rows = [r for sub in ex.map(_batch, chunks) for r in sub if r is not None]
    return np.array(rows, dtype=float) if rows else np.zeros((0, len(FIELDS)))


def pareto_mask(G: np.ndarray) -> np.ndarray:
    """Non-dominated rows of G (all columns to be MAXIMISED)."""
    n = len(G)
    keep = np.ones(n, dtype=bool)
    for i in range(0, n, 256):
        block = G[i:i + 256]                       # (b, k)
        ge = (G[None, :, :] >= block[:, None, :]).all(axis=2)   # j dominates-or-equals i
        gt = (G[None, :, :] > block[:, None, :]).any(axis=2)
        dominated = (ge & gt).any(axis=1)
        keep[i:i + 256] &= ~dominated
    return keep


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 4 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or args[0] not in RIDERS:
        sys.exit(__doc__)
    preset = args[0]
    opt = {k: v for k, v in (a.lstrip("-").split("=") for a in sys.argv[1:] if a.startswith("--") and "=" in a)}
    n1, n2 = int(opt.get("n1", 100_000)), int(opt.get("n2", 100_000))
    workers, seed = int(opt.get("workers", 16)), int(opt.get("seed", 0))
    rng = np.random.default_rng(seed)
    rider = _rider(preset)
    f_peak = anchor(rider.weight_kg, rider.skill, design_speed=rider.speed, config=rider.config,
                    material=rider.material, tabs=rider.tabs).force_peak_n
    d_board = (rider.weight_kg + 3.0) * 9.81 / 5.0  # planing board, L/D ~ 5: the drag yardstick
    print(f"[{preset}] {rider.weight_kg:.0f} kg {rider.skill.name} {rider.speed:.1f} m/s  "
          f"F_peak {f_peak:.0f} N  F_work {spider.work_force_n(rider.weight_kg):.0f} N  "
          f"board drag yardstick ~{d_board:.0f} N", flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(preset,)) as ex:
        X1 = rng.random((n1, len(SLIDERS)))
        F1 = _harvest(ex, X1)
        print(f"  census: {len(F1)}/{n1} feasible ({len(F1) / n1:.2%}) in {time.time() - t0:.0f}s", flush=True)
        if len(F1) == 0:
            sys.exit("no feasible points in the census")
        # resample around feasible points: back-project their slider values, perturb
        S1 = np.array([[(row[SLIDERS.index(n)] - lo) / (hi - lo) for n, lo, hi in _SLIDER_BOUNDS] for row in F1])
        picks = S1[rng.integers(0, len(S1), n2)]
        X2 = np.clip(picks + rng.normal(0.0, 0.06, picks.shape), 0.0, 1.0)
        F2 = _harvest(ex, X2)
        print(f"  refine: {len(F2)}/{n2} feasible ({len(F2) / n2:.2%}) in {time.time() - t0:.0f}s", flush=True)
    F = np.vstack([F1, F2])
    col = {f: i for i, f in enumerate(FIELDS)}
    G = np.column_stack([GOOD_SIGN[k] * F[:, col[g]] for k, g in enumerate(GOODS)])
    front = pareto_mask(G)
    P = F[front]
    # frontier including turn-load drag, among designs that can make the peak force
    can = ~np.isnan(F[:, col["drag_peak_n"]])
    G5 = np.column_stack([G[can], -F[can, col["drag_peak_n"]]])
    front5 = pareto_mask(G5)
    print(f"  feasible {len(F)}, frontier(4 goods) {len(P)}, can-make-peak {can.sum()}, "
          f"frontier(5 goods incl. peak drag) {front5.sum()}  [{time.time() - t0:.0f}s]", flush=True)

    def ext(A: np.ndarray, f: str) -> tuple[float, float]:
        v = A[:, col[f]]; v = v[~np.isnan(v)]
        return (float(v.min()), float(v.max())) if len(v) else (float("nan"), float("nan"))

    lines = [f"# Frontier — {preset}: {rider.weight_kg:.0f} kg {rider.skill.name}, {rider.speed:.1f} m/s, "
             f"F_peak {f_peak:.0f} N, F_work {spider.work_force_n(rider.weight_kg):.0f} N, board-drag yardstick ≈ {d_board:.0f} N\n",
             f"feasible designs {len(F)} of {n1 + n2} sampled; frontier in the 4 monotone goods: {len(P)} designs; "
             f"{can.sum()} feasible designs can make the peak force; 5-good frontier (with peak drag): {front5.sum()}.\n",
             "## Extent of the goods: whole feasible set vs the frontier\n",
             "| quantity | feasible min | feasible max | frontier min | frontier max | frontier range in rider terms |", "|---|---|---|---|---|---|"]
    rider_terms = {
        "drag_trim_n": lambda lo, hi: f"{(hi - lo) / d_board * 100:.1f} % of board drag",
        "drag_peak_n": lambda lo, hi: f"{(hi - lo) / d_board * 100:.1f} % of board drag",
        "ld_work": lambda lo, hi: f"×{hi / lo:.2f}",
        "ld_peak": lambda lo, hi: f"×{hi / lo:.2f}" if lo > 0 else "n/a",
        "f_max_eff_n": lambda lo, hi: f"{lo / f_peak:.2f}–{hi / f_peak:.2f} × F_peak",
        "margin_peak_deg": lambda lo, hi: f"{hi - lo:.1f}°",
    }
    for g in ("drag_trim_n", "drag_peak_n", "ld_work", "ld_peak", "f_max_eff_n", "margin_peak_deg"):
        a, b = ext(F, g); c, d = ext(P, g)
        lines.append(f"| {g} | {a:.2f} | {b:.2f} | {c:.2f} | {d:.2f} | {rider_terms[g](c, d)} |")
    lines += ["\n## Taste quantities: range across the frontier (what a lever could span)\n",
              "| quantity | frontier min | frontier max | ratio max/min | feasible-set ratio |", "|---|---|---|---|---|"]
    for t in TASTES:
        c, d = ext(P, t); a, b = ext(F, t)
        lines.append(f"| {t} | {c:.3g} | {d:.3g} | ×{d / c:.2f} | ×{b / a:.2f} |")
    lines += ["\n## Which knobs move along the frontier (Spearman of slider vs each good, frontier points)\n",
              "| slider | frontier min | frontier max | vs −trim drag | vs L/D work | vs F_max | vs margin |", "|---|---|---|---|---|---|---|"]
    for s in SLIDERS + ("area_mm2", "aspect_ratio"):
        c, d = ext(P, s)
        cors = [_spearman(P[:, col[s]], GOOD_SIGN[k] * P[:, col[g]]) for k, g in enumerate(GOODS)]
        lines.append(f"| {s} | {c:.3g} | {d:.3g} | " + " | ".join(f"{v:+.2f}" for v in cors) + " |")
    # regime and gates on the frontier
    lo_d, hi_d = _DEPTH_CORRIDOR_MM[rider.config]
    on = {
        "stress SF within 5 % of the minimum": np.minimum(P[:, col["stress_sf"]], P[:, col["stress_sf_roll"]]) < 1.5 * 1.05,
        "tip deflection within 5 % of 15 % depth": P[:, col["tip_deflection_mm"]] > 0.95 * 0.15 * P[:, col["depth"]],
        "washout within 5 % of 1.5 %": np.abs(P[:, col["washout_pct"]]) > 0.95 * 1.5,
        f"depth at corridor edge ({lo_d:.0f}/{hi_d:.0f} mm)": (np.abs(P[:, col["depth"]] - lo_d) < 1.0) | (np.abs(P[:, col["depth"]] - hi_d) < 1.0),
        "base at FCS II limits (98 / 123.5 mm)": (np.abs(P[:, col["base"]] - 98.0) < 1.0) | (np.abs(P[:, col["base"]] - 123.5) < 1.0),
        "t/c at the 0.04 floor": P[:, col["t_c"]] < 0.042,
        "working load above the stall knee": P[:, col["cl_work_over_knee"]] > 1.0,
        "peak load above the stall knee": P[:, col["cl_peak_over_knee"]] > 1.0,
        "cannot make the peak force": np.isnan(P[:, col["drag_peak_n"]]),
    }
    lines += ["\n## Where the frontier sits: gates and the stall knee (share of frontier designs)\n",
              "| condition | share of frontier | share of feasible set |", "|---|---|---|"]
    for k, mask in on.items():
        allmask = {
            0: np.minimum(F[:, col["stress_sf"]], F[:, col["stress_sf_roll"]]) < 1.5 * 1.05,
            1: F[:, col["tip_deflection_mm"]] > 0.95 * 0.15 * F[:, col["depth"]],
            2: np.abs(F[:, col["washout_pct"]]) > 0.95 * 1.5,
            3: (np.abs(F[:, col["depth"]] - lo_d) < 1.0) | (np.abs(F[:, col["depth"]] - hi_d) < 1.0),
            4: (np.abs(F[:, col["base"]] - 98.0) < 1.0) | (np.abs(F[:, col["base"]] - 123.5) < 1.0),
            5: F[:, col["t_c"]] < 0.042,
            6: F[:, col["cl_work_over_knee"]] > 1.0,
            7: F[:, col["cl_peak_over_knee"]] > 1.0,
            8: np.isnan(F[:, col["drag_peak_n"]]),
        }[list(on).index(k)]
        lines.append(f"| {k} | {mask.mean() * 100:.0f} % | {allmask.mean() * 100:.0f} % |")
    # a handful of frontier corners for intuition
    lines += ["\n## Frontier corners (the design that is best in each good)\n",
              "| best in | depth | base | sweep | t/c | area | AR | trim drag N | peak drag N | L/D work | F_max N | margin ° | yaw stiff | roll damp |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, g in enumerate(GOODS):
        i = int(np.argmax(GOOD_SIGN[k] * P[:, col[g]]))
        r = P[i]
        lines.append(f"| {g} | {r[col['depth']]:.0f} | {r[col['base']]:.0f} | {r[col['sweep']]:.0f} | {r[col['t_c']]:.3f} | "
                     f"{r[col['area_mm2']]:.0f} | {r[col['aspect_ratio']]:.2f} | {r[col['drag_trim_n']]:.1f} | {r[col['drag_peak_n']]:.1f} | "
                     f"{r[col['ld_work']]:.1f} | {r[col['f_max_eff_n']]:.0f} | {r[col['margin_peak_deg']]:.1f} | "
                     f"{r[col['yaw_stiffness_nm_rad']]:.0f} | {r[col['roll_damping_nm_s']]:.2f} |")
    text = "\n".join(lines)
    out = Path("out"); out.mkdir(exist_ok=True)
    (out / f"frontier-{preset}.md").write_text(text + "\n")
    json.dump({"rider": {"preset": preset, "weight_kg": rider.weight_kg, "skill": rider.skill.name,
                         "speed_ms": rider.speed, "f_peak_n": f_peak, "f_work_n": spider.work_force_n(rider.weight_kg),
                         "board_drag_yardstick_n": d_board},
               "sampling": {"n1": n1, "n2": n2, "seed": seed, "n_feasible": int(len(F))},
               "fields": list(FIELDS), "frontier": P.tolist(), "frontier5_count": int(front5.sum()),
               "feasible_extent": {f: ext(F, f) for f in FIELDS}},
              open(out / f"frontier-{preset}.json", "w"))
    print(text)
    print(f"\nwritten out/frontier-{preset}.md, out/frontier-{preset}.json  [{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    main()
