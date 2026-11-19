"""Which design parameters can the tier-0 physical model actually SEE? (gen-3 item 0.5)

    uv run python scripts/model_reach.py [--md out/model-reach.md]

For every parameter the optimizer may move (8 level-1 sliders, the level-2
edge offsets, grooves) this perturbs ONE parameter by a step a rider or a
shaper would call noticeable and records the change of every tier-0 output.
Two modes:

  raw   only that parameter moves (area and aspect ratio move with it);
  iso   for the outline SHAPE parameters the base chord is re-solved so the
        planform AREA is restored at the same depth — area and aspect ratio
        are then unchanged, and whatever still moves is the model's genuine
        awareness of shape (as opposed to size).

Base points: Omar's shipped gen-2 side (flat-inside, scored as the dominant
blade) and the gen-1 centre he rides (symmetric, scored as the rear member),
both at 60 kg / 8.5 m/s / ppa-cf / FCS II. Outputs are grouped the way the
model computes them (hydro.py, spider.py, roll.py, flex.py), so a row of
zeros in a group means that module is blind to the parameter.

Part 2 reads out/frontier-<rider>.json (scripts/frontier.py) and splits the
"taste" quantity yaw stiffness into what is physics (tail lateral stiffness
q·A·CLα) and what is the reference-point arm, and splits max side force into
area, slope and usable angle (break − zero-lift) to show what thickness does
on a flat-inside foil.
"""

from __future__ import annotations

import dataclasses
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from fingen import spider
from fingen.hydro import (RHO_SEAWATER, half_chord_sweep, lift_curve_slope,
                          stall_alpha_deg, stall_drag_cd, zero_lift_alpha_deg)
from fingen.optimize import _SLIDER_BOUNDS, RiderSpec, _decode, evaluate, fin_from_dict
from fingen.outline import metrics, planform
from fingen.params import (FinConfig, FinParams, FoilFamily, GrooveParams, GrooveSurface,
                           TabSystem)
from fingen.sizing import Skill, anchor

RIDER = RiderSpec(weight_kg=60.0, skill=Skill.PRO, speed_ms=8.5, config=FinConfig.THRUSTER,
                  material="ppa-cf", tabs=TabSystem("click_tab"), stress_sf_min=1.5,
                  washout_max=0.015, tip_deflection_max_frac=0.15)


def _f_peak(member: str) -> float:
    return anchor(RIDER.weight_kg, RIDER.skill, design_speed=RIDER.speed, config=RIDER.config,
                  material=RIDER.material, tabs=RIDER.tabs, member=member).force_peak_n


def measure(fin: FinParams, rear: bool) -> dict[str, float]:
    speed = RIDER.speed
    q = 0.5 * RHO_SEAWATER * speed**2
    f_peak = _f_peak("center" if rear else "dominant")
    m = metrics(fin.outline)
    area = m.area * 1e-6
    slope, ar_eff = lift_curve_slope(fin)
    a_break, a0 = stall_alpha_deg(ar_eff), zero_lift_alpha_deg(fin)
    cd0 = spider._cd0(fin, speed)
    raw = spider.raw_scores(fin, speed, RIDER.weight_kg, f_peak)
    ev = evaluate(fin, RIDER, rear_member=rear)
    z, x_le, chord = planform(fin.outline)
    x_cp = float(np.trapezoid((x_le + 0.25 * chord) * chord, z) / np.trapezoid(chord, z))
    arm = spider.YAW_ARM_REF_MM + (x_cp - fin.outline.base / 2.0)   # generation 3: signed, board-level
    cl_peak, cl_max = f_peak / (q * area), slope * math.radians(a_break - a0)
    if cl_peak <= cl_max:
        d_peak = q * area * (cd0 + cl_peak**2 / (math.pi * 0.9 * ar_eff) + stall_drag_cd(cl_peak, slope, ar_eff))
    else:
        d_peak = float("nan")
    mg = ev.margins
    return {
        "area": m.area, "AR_eff": ar_eff, "Λc/2°": math.degrees(half_chord_sweep(fin)),
        "CLα": slope, "α_break°": a_break, "α0°": a0, "cd0": cd0,
        "D_trim N": 1.0 / raw["speed"], "D_peak N": d_peak, "L/D work": raw["drive"],
        "F_max N": raw["hold"], "margin°": raw["forgiveness"],
        "K_lat N/°": q * area * slope * math.pi / 180.0, "arm mm": arm,
        "yaw stiff": 1.0 / raw["pivot"], "roll damp": raw["stability"], "release": raw["release"],
        "SF roll": mg["stress_sf_roll"], "tip defl mm": mg["tip_deflection_mm"],
        "washout %": mg["washout_pct"], "f_wet Hz": mg["f_wet_hz"], "V_div m/s": mg["divergence_ms"],
        "safety pen": sum(v for k, v in ev.penalties.items() if k in ("hook", "tip_radius", "tip_sharp")),
    }


ABS_DELTA = {"α_break°", "α0°", "margin°", "Λc/2°", "release", "washout %", "safety pen"}
GROUPS = {
    "geometry": ("area", "AR_eff", "Λc/2°"),
    "hydro (hydro.py)": ("CLα", "α_break°", "α0°", "cd0", "D_trim N", "D_peak N", "L/D work", "F_max N", "margin°"),
    "handling (spider.py, roll.py)": ("K_lat N/°", "arm mm", "yaw stiff", "roll damp", "release"),
    "structure (flex.py)": ("SF roll", "tip defl mm", "washout %", "f_wet Hz", "V_div m/s"),
}


def _with_outline(fin: FinParams, **kw) -> FinParams:
    return dataclasses.replace(fin, outline=dataclasses.replace(fin.outline, **kw))


def _iso_area(fin: FinParams, area0: float) -> FinParams | None:
    """Re-solve the base chord so the planform area returns to area0 (depth fixed)."""
    b0 = fin.outline.base

    def f(b: float) -> float:
        try:
            return metrics(dataclasses.replace(fin.outline, base=b)).area - area0
        except ValueError:
            return float("nan")

    grid = np.linspace(0.6 * b0, 1.6 * b0, 41)
    vals = [f(b) for b in grid]
    for (b1, v1), (b2, v2) in zip(zip(grid, vals), zip(grid[1:], vals[1:])):
        if not (math.isnan(v1) or math.isnan(v2)) and v1 * v2 <= 0.0:
            return _with_outline(fin, base=float(brentq(f, b1, b2)))
    return None


def _offset(fin: FinParams, which: str, idx: int, d: float) -> FinParams:
    cur = list(getattr(fin.outline, which))
    cur[idx] += d
    return _with_outline(fin, **{which: tuple(cur)})


def perturbations(fin: FinParams) -> list[tuple[str, FinParams, bool]]:
    o, f = fin.outline, fin.foil
    sgn = lambda v, lo, hi, d: d if v + d <= hi else -d
    out = [
        ("depth %+.0f mm" % (d := sgn(o.depth, 40, 290, 10.0)), _with_outline(fin, depth=o.depth + d), False),
        ("base %+.0f mm" % (d := sgn(o.base, 40, 240, 10.0)), _with_outline(fin, base=o.base + d), False),
        ("sweep %+.0f°" % (d := sgn(o.sweep, 0, 60, 10.0)), _with_outline(fin, sweep=o.sweep + d), True),
        ("tip_width_ratio %+.2f" % (d := sgn(o.tip_width_ratio, 0.05, 0.6, 0.15)),
         _with_outline(fin, tip_width_ratio=o.tip_width_ratio + d), True),
        ("le_fullness %+.2f" % (d := sgn(o.le_fullness, 0, 1, 0.25)), _with_outline(fin, le_fullness=o.le_fullness + d), True),
        ("te_shape %+.2f" % (d := sgn(o.te_shape, -1, 1, 0.5)), _with_outline(fin, te_shape=o.te_shape + d), True),
        ("LE offset mid-span +5 mm", _offset(fin, "le_dx", 3, 5.0), True),
        ("TE offset mid-span −5 mm", _offset(fin, "te_dx", 3, -5.0), True),
        ("thickness_ratio +0.03", dataclasses.replace(fin, foil=dataclasses.replace(f, thickness_ratio=f.thickness_ratio + 0.03)), False),
        ("thickness_tip_factor %+.1f" % (d := sgn(fin.thickness_tip_factor, 0.5, 1.2, 0.2)),
         dataclasses.replace(fin, thickness_tip_factor=fin.thickness_tip_factor + d), False),
        ("grooves 0 → 3 (depth 0.3)", dataclasses.replace(fin, grooves=GrooveParams(
            count=3, length=55.0, pitch=6.0, width=3.0, depth_ratio=0.3, span_start=0.3,
            surface=GrooveSurface.OUTER)), False),
    ]
    return out


def _fmt(key: str, new: float, old: float) -> str:
    if math.isnan(new) or math.isnan(old):
        return "n/a"
    if key in ABS_DELTA:
        d = new - old
        return "·" if abs(d) < 0.05 else f"{d:+.1f}"
    d = (new / old - 1.0) * 100.0 if old else 0.0
    return "·" if abs(d) < 0.5 else f"{d:+.0f}%"


def reach_table(name: str, fin: FinParams, rear: bool, w) -> None:
    base = measure(fin, rear)
    w(f"\n## {name}\n")
    w("Baseline: " + ", ".join(f"{k} {v:.3g}" for k, v in base.items() if k != "safety pen") + "\n")
    w("Entries are the change for the stated step: % for most, absolute (°, proxy units, pp) for "
      + ", ".join(sorted(ABS_DELTA - {"safety pen"})) + ". `·` = no change (< 0.5 % or < 0.05).\n")
    for gname, keys in GROUPS.items():
        w(f"\n**{gname}**\n")
        w("| parameter step | mode | " + " | ".join(keys) + " |")
        w("|---|---|" + "---|" * len(keys))
        for label, pf, shape in perturbations(fin):
            rows = [("raw", pf)]
            if shape:
                iso = _iso_area(pf, base["area"])
                if iso is not None:
                    rows.append((f"iso-area (base → {iso.outline.base:.0f})", iso))
            for mode, cand in rows:
                try:
                    r = measure(cand, rear)
                    w(f"| {label} | {mode} | " + " | ".join(_fmt(k, r[k], base[k]) for k in keys) + " |")
                except ValueError as e:
                    w(f"| {label} | {mode} | rejected: {str(e)[:60]} |")


def frontier_split(path: Path, w) -> None:
    d = json.loads(path.read_text())
    F = np.array(d["frontier"], dtype=float)
    col = {f: i for i, f in enumerate(d["fields"])}
    r = d["rider"]
    speed, fp = r["speed_ms"], r["f_peak_n"]
    q = 0.5 * RHO_SEAWATER * speed**2
    rows = []
    for row in F:
        x = np.array([(row[col[n]] - lo) / (hi - lo) for n, lo, hi in _SLIDER_BOUNDS])
        fin = _decode(x, FinConfig.THRUSTER, use_offsets=False, use_grooves=False, tabs=TabSystem("click_tab"))
        slope, ar_eff = lift_curve_slope(fin)
        a_break, a0 = stall_alpha_deg(ar_eff), zero_lift_alpha_deg(fin)
        area = row[col["area_mm2"]] * 1e-6
        k_lat = q * area * slope * math.pi / 180.0
        rows.append((k_lat, row[col["yaw_stiffness_nm_rad"]] / (q * area * slope) * 1e3, a_break, a0,
                     a_break - a0, slope, ar_eff))
    R = np.array(rows)
    c = lambda k: F[:, col[k]]
    w(f"\n## Frontier split — {r['preset']} ({r['weight_kg']:.0f} kg {r['skill']}, {speed:.1f} m/s, F_peak {fp:.0f} N), {len(F)} designs\n")
    real = c("margin_peak_deg") >= 2.0
    band = real & (c("f_max_eff_n") >= fp) & (c("f_max_eff_n") <= 1.3 * fp)
    if band.sum():
        band &= c("drag_trim_n") <= np.median(c("drag_trim_n")[band])
    B = R[band]
    rng = lambda v: f"{v.min():.3g} – {v.max():.3g} (×{v.max() / v.min():.2f})"
    w(f"Band of near-equivalent goods (margin ≥ 2°, F_max 1–1.3 × F_peak, trim drag ≤ median): {band.sum()} designs.\n")
    w("| quantity in the band | range | what it is |")
    w("|---|---|---|")
    w(f"| yaw stiffness (the `pivot` axis) | {rng(c('yaw_stiffness_nm_rad')[band])} | q·A·CLα × arm |")
    w(f"| … tail lateral stiffness K_lat, N/° | {rng(B[:, 0])} | q·A·CLα: the physics |")
    w(f"| … arm, mm | {rng(B[:, 1])} | CP offset from the fin's own base centre + c̄/4: the reference point |")
    for L in (400.0, 600.0):
        board = B[:, 0] * (L + B[:, 1] - B[:, 1].mean())
        w(f"| board-level yaw stiffness, fin {L:.0f} mm behind the yaw centre | ×{board.max() / board.min():.2f} | K_lat × (L + CP shift) |")
    w(f"| usable angle α_break − α0, ° | {rng(B[:, 4])} | trades against K_lat at fixed F_max |")
    w(f"| AR_eff | {rng(B[:, 6])} | the knob behind both |")
    w(f"| roll damping | {rng(c('roll_damping_nm_s')[band])} | strip integral ∫c·z² |")
    w(f"| release proxy | {rng(c('release_proxy')[band])} | 0.6·sweep/50 + 0.4·elliptic deviation: geometry only |")
    w("\nWhat makes max side force on the whole frontier (F_max = q · A · CLα · (α_break − α0) · washout):\n")
    w("| factor | frontier range | Spearman with t/c |")
    w("|---|---|---|")
    tc = c("t_c")
    sp = lambda a, b: float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1])
    for lab, v in (("area mm²", c("area_mm2")), ("CLα /rad", R[:, 5]), ("α_break °", R[:, 2]),
                   ("−α0 ° (camber)", -R[:, 3]), ("usable angle °", R[:, 4]),
                   ("CL_max (model)", R[:, 5] * np.radians(R[:, 4])), ("F_max N", c("f_max_eff_n")),
                   ("trim drag N", c("drag_trim_n"))):
        w(f"| {lab} | {rng(v)} | {sp(v, tc):+.2f} |")


def main() -> None:
    lines: list[str] = []
    w = lines.append
    w("# Model reach — which design parameters tier-0 can see\n")
    side = fin_from_dict(json.loads(Path("bench/mount/fins/side-shipped-gen2.json").read_text())["fin"])
    cen = fin_from_dict(json.loads(Path("bench/mount/fins/centre-ridden-gen1.json").read_text())["fin"])
    reach_table("Side fin — shipped gen-2 side (flat-inside foil), scored as the dominant blade", side, False, w)
    reach_table("Centre fin — ridden gen-1 centre (symmetric foil), scored as the rear member", cen, True, w)
    w("\n## Zero-lift angle and model CL_max vs thickness on a FLAT-INSIDE foil (gen-2 side planform)\n")
    w("| t/c | camber = t/2 | α0 ° | usable angle ° | CL_max (model) | cd0 | D_trim N (isolated, α = 1°) |")
    w("|---|---|---|---|---|---|---|")
    for tc in (0.05, 0.07, 0.09, 0.12, 0.15, 0.18, 0.22):
        f = dataclasses.replace(side, foil=dataclasses.replace(side.foil, thickness_ratio=tc))
        slope, ar = lift_curve_slope(f)
        a0, ab = zero_lift_alpha_deg(f), stall_alpha_deg(ar)
        raw = spider.raw_scores(f, RIDER.speed, RIDER.weight_kg, _f_peak("dominant"))
        w(f"| {tc:.2f} | {tc / 2 * 100:.1f} % | {a0:+.2f} | {ab - a0:.1f} | {slope * math.radians(ab - a0):.2f} | "
          f"{spider._cd0(f, RIDER.speed):.4f} | {1 / raw['speed']:.1f} |")
    for name in ("omar", "ref75"):
        p = Path(f"out/frontier-{name}.json")
        if p.exists():
            frontier_split(p, w)
    text = "\n".join(lines)
    print(text)
    if "--md" in sys.argv:
        Path(sys.argv[sys.argv.index("--md") + 1]).write_text(text + "\n")


if __name__ == "__main__":
    main()
