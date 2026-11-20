"""Vortex-lattice feasibility probe (gen-3 model extension, step B0).

    uv run python scripts/vlm_probe.py [--md=out/vlm-probe.md]

Question: can a method that runs in milliseconds — so it can live inside the
optimizer loop — see what tier-0's formulas cannot (outline shape, spanwise
loading, tip thickness, the set's interference, toe and cant), and does it
agree with the CFD we already have?

The probe drives fingen.lattice (the kernel started here and moved into the
library): a plain-numpy 3-D vortex lattice — horseshoe vortices on each
blade's planform (bound leg on the panel quarter chord, legs run in the blade
plane to the trailing edge, then downstream along the freestream), a mirror
image in the board plane z = 0 (the CFD cases use a symmetry plane there),
flow tangency at the panel three-quarter-chord points, Kutta-Joukowski forces.
Section camber enters as a per-strip incidence offset (thin-airfoil alpha_0,
scaled along the span with the local thickness on a flat-inside foil). Blades
are placed exactly as `fingen.assembly.place_fin` does (toe about z, cant
about x, right/left hands), so the same code runs one fin or the whole set.

Checks: (1) textbook wings, (2) the three isolated CFD polars, (3) the 48-point
set CFD of bench/mount (per-fin forces, interference, toe), (4) what the
outline-shape sliders do at fixed area, (5) wall-clock cost.
"""

from __future__ import annotations

import dataclasses
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from fingen.hydro import RHO_SEAWATER, lift_curve_slope, zero_lift_alpha_deg
from fingen.optimize import fin_from_dict
from fingen.outline import metrics, planform
from fingen.params import FinParams, FoilFamily

# The kernel lives in the library now (fingen.lattice, tests/test_lattice.py). The
# thin wrappers below keep this probe's dict-style interface, which the sibling
# probes (board_edge_probe.py, section_probe.py) also import.
from fingen import lattice  # noqa: E402
from fingen.lattice import Blade, _horseshoe, _seg, _semi  # noqa: E402,F401  (re-exported)


def blade_from_planform(name, z_mm, xle_mm, chord_mm, *, toe=0.0, cant=0.0, **kw) -> Blade:
    return lattice.blade_from_planform(name, z_mm, xle_mm, chord_mm, toe_deg=toe, cant_deg=cant, **kw)


def blade_from_fin(name, fin: FinParams, *, toe=0.0, cant=0.0, **kw) -> Blade:
    return lattice.blade_from_fin(name, fin, toe_deg=toe, cant_deg=cant, **kw)


def solve(blades: list[Blade], speed: float, leeway_deg: float, mirror: bool = True) -> dict:
    return {name: {"cl": r.cl, "cdi": r.cdi, "cl_local": r.cl_local, "z": r.z, "dz": r.dz,
                   "z_wake": r.z_wake,
                   "x_cp_m": r.x_cp_m, "z_cp_m": r.z_cp_m, "gamma_strip": r.gamma_strip}
            for name, r in lattice.solve(blades, speed, leeway_deg, mirror=mirror).items()}


def trefftz_cdi(res: dict, area: float, speed: float) -> float:
    return lattice.trefftz_cdi(res["gamma_strip"], res["dz"], res["z_wake"], area, speed)


def isolated(fin: FinParams, speed=8.5, nz=16, nx=4) -> dict:
    """Linear characteristics of one blade on the mirror: slope, CL(0), e, CP, local-cl peak."""
    i = lattice.isolated(fin, speed, nz=nz, nx=nx)
    return {"slope": i.slope, "cl0": i.cl0, "alpha0_deg": i.alpha0_deg, "e": i.span_efficiency,
            "x_cp_mm": i.x_cp_mm, "z_cp_frac": i.z_cp_frac, "peak_ratio": i.peak_ratio,
            "peak_z_frac": i.peak_z_frac}


# -------------------------------------------------------------------- checks
def _load(path):
    d = json.loads(Path(path).read_text())
    return d["fin"] if "fin" in d else d


def _patch(d, p):
    import copy
    out = copy.deepcopy(d)
    for k, v in p.items():
        out[k] = _patch(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def main() -> None:
    L: list[str] = []
    w = L.append
    w("# Vortex-lattice feasibility probe\n")

    # 1. textbook wings ------------------------------------------------------
    w("## 1. Textbook checks (published lifting-surface values for rectangular wings; e = 1 for an elliptic loading)\n")
    w("| wing (full span, via the mirror) | AR | CLα VLM /rad | reference | span efficiency e (far wake) |")
    w("|---|---|---|---|---|")
    z = np.linspace(0.0, 100.0, 400)
    for ar, ref in ((2.0, "≈ 2.47"), (4.0, "≈ 3.6"), (6.0, "≈ 4.2")):
        chord = np.full_like(z, 200.0 / ar)              # semi-span 100 mm, rectangular
        b = blade_from_planform("w", z, np.zeros_like(z), chord, nz=24, nx=6)
        r = solve([b], 8.5, 4.0)["w"]
        w(f"| rectangular | {ar:g} | {r['cl'] / math.radians(4):.2f} | {ref} | {r['cl']**2 / (math.pi * ar * trefftz_cdi(r, b.area, 8.5)):.3f} |")
    chord = 60.0 * np.sqrt(np.clip(1.0 - (z / 100.0) ** 2, 0.0, None))
    ar_e = 2.0 * 100.0**2 / float(np.trapezoid(chord, z))
    b = blade_from_planform("w", z, -0.25 * chord, chord, nz=24, nx=6)   # straight quarter-chord line
    r = solve([b], 8.5, 4.0)["w"]
    w(f"| elliptic, straight c/4 line | {ar_e:.2f} | {r['cl'] / math.radians(4):.2f} | "
      f"{2 * math.pi * ar_e / (ar_e + 2):.2f} (lifting-line; surface theory lower) | {r['cl']**2 / (math.pi * ar_e * trefftz_cdi(r, b.area, 8.5)):.3f} |")

    # 2. isolated fins vs CFD ------------------------------------------------
    fins = {
        "gen-2 side": (fin_from_dict(_load("bench/mount/fins/side-shipped-gen2.json")), "out/cfd/omar-big-gen2-m2-shipped/verify-polar.json"),
        "gen-1 side": (fin_from_dict(_load("bench/mount/fins/side-asridden-gen1.json")), "out/cfd/omar-big-asridden/verify-polar.json"),
        "ridden centre": (fin_from_dict(_load("bench/mount/fins/centre-ridden-gen1.json")), "out/cfd/omar-ridden-centre/verify-polar.json"),
    }
    w("\n## 2. Isolated fins against the CFD polars (board = symmetry plane in both)\n")
    w("| fin | CLα CFD (0–4°) | VLM inviscid | VLM/CFD | tier-0 DATCOM (k = 1.7) | tier-0/CFD | CL at 0° CFD | VLM | tier-0 | e VLM (tier-0: 0.90) |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    iso = {}
    for name, (fin, polar) in fins.items():
        rows = json.loads(Path(polar).read_text())["rows"]
        s_cfd = (rows[1]["cl"] - rows[0]["cl"]) / math.radians(rows[1]["alpha"] - rows[0]["alpha"])
        v = isolated(fin)
        iso[name] = v
        s_t0, _ = lift_curve_slope(fin)
        cl0_t0 = -s_t0 * math.radians(zero_lift_alpha_deg(fin))
        w(f"| {name} | {s_cfd:.2f} | {v['slope']:.2f} | {v['slope'] / s_cfd:.2f} | {s_t0:.2f} | {s_t0 / s_cfd:.2f} | "
          f"{rows[0]['cl']:.3f} | {v['cl0']:.3f} | {cl0_t0:.3f} | {v['e']:.2f} |")
    w("\nSpanwise loading at 4° (local cl / fin CL of the incidence loading; where it peaks is where the fin stalls first):\n")
    w("| fin | peak local cl / CL | at span fraction | spanwise CP (fraction of depth) | implied section cl_max if the CFD CL_max is first-stall |")
    w("|---|---|---|---|---|")
    for name, (fin, polar) in fins.items():
        rows = json.loads(Path(polar).read_text())["rows"]
        clmax = max(r["cl"] for r in rows)
        v = iso[name]
        w(f"| {name} | {v['peak_ratio']:.2f} | {v['peak_z_frac']:.2f} | {v['z_cp_frac']:.2f} | {clmax * v['peak_ratio']:.2f} (CFD CL_max {clmax:.2f}) |")

    # 3. the set -------------------------------------------------------------
    w("\n## 3. The placed thruster set against the 48-point set CFD (bench/mount)\n")
    plan = json.loads(Path("bench/mount/plan.json").read_text())
    cfd = json.loads(Path("bench/mount/results.json").read_text())["cases"]
    root = Path("bench/mount")

    def set_blades(case, nz=14, nx=3):  # noqa: E306
        side = fin_from_dict(_patch(_load(root / case.get("side", plan["side"])), case.get("side_patch", {})))
        cen = fin_from_dict(_patch(_load(root / case.get("center", plan["center"])), case.get("center_patch", {})))
        g = {k: float(case.get(k, plan[k])) for k in ("toe", "cant", "side_x", "side_y")}
        return [blade_from_fin("center", cen, nz=nz, nx=nx),
                blade_from_fin("right", side, nz=nz, nx=nx, hand="right", toe=g["toe"], cant=g["cant"], xy_mm=(g["side_x"], g["side_y"])),
                blade_from_fin("left", side, nz=nz, nx=nx, hand="left", toe=g["toe"], cant=g["cant"], xy_mm=(g["side_x"], -g["side_y"]))], cen

    w("Per-fin lift coefficient (own planform area), CFD → VLM. Linear method: read 0° and 5°; at 10° the fin working against its camber has stalled in the CFD.\n")
    w("| case | β | centre CFD | VLM | right (with camber) CFD | VLM | left (against camber) CFD | VLM |")
    w("|---|---|---|---|---|---|---|---|")
    err5 = {"center": [], "right": [], "left": []}
    inter = []
    t_set = []
    for case in plan["cases"]:
        blades, cen = set_blades(case)
        cb = blade_from_fin("c", cen, nz=14, nx=3)
        for beta in (0.0, 5.0, 10.0):
            t0 = time.perf_counter()
            r = solve(blades, plan["speed"], beta)
            t_set.append(time.perf_counter() - t0)
            c = next(x["coeffs"] for x in cfd[case["name"]]["rows"] if x["angle"] == beta)
            if case["name"] in ("baseline", "toe-2.5", "toe-4.5", "sidey-103", "sidey-133", "G1-side-asridden-gen1", "G2-centre-depth131") or beta == 5.0:
                w(f"| {case['name']} | {beta:g} | {c['center']['cl']:+.3f} | {r['center']['cl']:+.3f} | {c['right']['cl']:+.3f} | {r['right']['cl']:+.3f} | "
                  f"{c['left']['cl']:+.3f} | {r['left']['cl']:+.3f} |")
            if beta == 5.0:
                for s in err5:
                    err5[s].append((r[s]["cl"], c[s]["cl"]))
                iso_c = solve([cb], plan["speed"], beta)["c"]["cl"]
                inter.append((case["name"], r["center"]["cl"] / iso_c, c["center"]["cl"]))
    w("\nAt 5° over all 12 cases:\n")
    w("| fin | mean VLM/CFD | spread (min–max) | correlation across cases |")
    w("|---|---|---|---|")
    for s, pairs in err5.items():
        a = np.array(pairs)
        ratio = a[:, 0] / a[:, 1]
        w(f"| {s} | {ratio.mean():.2f} | {ratio.min():.2f}–{ratio.max():.2f} | {np.corrcoef(a[:, 0], a[:, 1])[0, 1]:+.2f} |")
    w("\nCentre-fin interference factor at 5° (centre in the set / the same centre alone). CFD isolated value taken from the ridden-centre polar where the blade is the ridden one:\n")
    w("| case | VLM factor | CFD factor |")
    w("|---|---|---|")
    rows_c = json.loads(Path("out/cfd/omar-ridden-centre/verify-polar.json").read_text())["rows"]
    iso_cfd5 = rows_c[1]["cl"] + (rows_c[2]["cl"] - rows_c[1]["cl"]) * (5 - 4) / 4
    for name, f, c_cl in inter:
        cf = f"{c_cl / iso_cfd5:.2f}" if not name.startswith(("G2", "G3")) else "n/a (no isolated polar)"
        w(f"| {name} | {f:.2f} | {cf} |")

    # 4. shape awareness -----------------------------------------------------
    w("\n## 4. What the outline-shape sliders do at FIXED area and depth (tier-0 hydro: all zero)\n")
    side = fins["gen-2 side"][0]
    base = isolated(side)
    a0 = metrics(side.outline).area

    def iso_area(f):
        def g(b):
            try:
                return metrics(dataclasses.replace(f.outline, base=b)).area - a0
            except ValueError:
                return float("nan")
        grid = np.linspace(0.6 * f.outline.base, 1.6 * f.outline.base, 41)
        vals = [g(b) for b in grid]
        for (b1, v1), (b2, v2) in zip(zip(grid, vals), zip(grid[1:], vals[1:])):
            if not (math.isnan(v1) or math.isnan(v2)) and v1 * v2 <= 0:
                return dataclasses.replace(f, outline=dataclasses.replace(f.outline, base=float(brentq(g, b1, b2))))
        return None

    w(f"Baseline gen-2 side: CLα {base['slope']:.2f}, e {base['e']:.2f}, chordwise CP {base['x_cp_mm']:+.1f} mm from the base centre, "
      f"spanwise CP {base['z_cp_frac']:.2f}, peak local cl/CL {base['peak_ratio']:.2f} at {base['peak_z_frac']:.2f} span.\n")
    w("| step (area and depth held) | ΔCLα | Δe | Δ chordwise CP mm | Δ spanwise CP | peak local cl / CL | peak at span |")
    w("|---|---|---|---|---|---|---|")
    o = side.outline
    steps = [("sweep +10°", dataclasses.replace(o, sweep=o.sweep + 10)), ("sweep −10°", dataclasses.replace(o, sweep=o.sweep - 10)),
             ("tip_width_ratio +0.15", dataclasses.replace(o, tip_width_ratio=o.tip_width_ratio + 0.15)),
             ("tip_width_ratio −0.10", dataclasses.replace(o, tip_width_ratio=max(0.05, o.tip_width_ratio - 0.10))),
             ("le_fullness +0.25", dataclasses.replace(o, le_fullness=min(1.0, o.le_fullness + 0.25))),
             ("te_shape +0.50", dataclasses.replace(o, te_shape=min(1.0, o.te_shape + 0.5))),
             ("te_shape −0.50", dataclasses.replace(o, te_shape=max(-1.0, o.te_shape - 0.5)))]
    for label, ol in steps:
        try:
            f = iso_area(dataclasses.replace(side, outline=ol))
            v = isolated(f)
            w(f"| {label} | {(v['slope'] / base['slope'] - 1) * 100:+.1f} % | {v['e'] - base['e']:+.3f} | {v['x_cp_mm'] - base['x_cp_mm']:+.1f} | "
              f"{v['z_cp_frac'] - base['z_cp_frac']:+.3f} | {v['peak_ratio']:.2f} | {v['peak_z_frac']:.2f} |")
        except (ValueError, AttributeError) as ex:
            w(f"| {label} | rejected: {str(ex)[:50]} |")
    for tf in (0.6, 1.2):
        f = dataclasses.replace(side, thickness_tip_factor=tf)
        v = isolated(f)
        w(f"| thickness_tip_factor {side.thickness_tip_factor:.2f} → {tf} (camber follows thickness) | {(v['slope'] / base['slope'] - 1) * 100:+.1f} % | "
          f"{v['e'] - base['e']:+.3f} | {v['x_cp_mm'] - base['x_cp_mm']:+.1f} | {v['z_cp_frac'] - base['z_cp_frac']:+.3f} | "
          f"{v['peak_ratio']:.2f} | {v['peak_z_frac']:.2f} | CL at 0°: {v['cl0']:.3f} vs {base['cl0']:.3f} |")

    # 5. cost ----------------------------------------------------------------
    w("\n## 5. Cost\n")
    w("| problem | panels | wall time per solve |")
    w("|---|---|---|")
    for nz, nx in ((10, 2), (12, 3), (16, 4), (24, 6)):
        b = blade_from_fin("b", side, nz=nz, nx=nx)
        solve([b], 8.5, 4.0)
        ts = []
        for _ in range(15):
            t0 = time.perf_counter(); solve([b], 8.5, 4.0); ts.append(time.perf_counter() - t0)
        w(f"| one blade | {nz * nx} | {np.median(ts) * 1e3:.1f} ms |")
    for nz, nx in ((10, 2), (14, 3)):
        bl, _ = set_blades(plan["cases"][0], nz=nz, nx=nx)
        solve(bl, 8.5, 5.0)
        ts = []
        for _ in range(10):
            t0 = time.perf_counter(); solve(bl, 8.5, 5.0); ts.append(time.perf_counter() - t0)
        w(f"| thruster set, 3 blades | {3 * nz * nx} | {np.median(ts) * 1e3:.1f} ms |")
    # resolution sensitivity of the headline numbers
    w("\nResolution sensitivity (gen-2 side): CLα and peak local cl / CL\n")
    w("| panels | CLα | peak local cl / CL |")
    w("|---|---|---|")
    for nz, nx in ((10, 2), (12, 3), (16, 4), (24, 6)):
        v = isolated(side, nz=nz, nx=nx)
        w(f"| {nz}×{nx} | {v['slope']:.3f} | {v['peak_ratio']:.3f} |")
    w("\nThe influence matrix depends on geometry and wake direction only, so further angles on the same geometry "
      "cost one back-substitution each; tier-0 `evaluate` is ≈ 10 ms today.")

    text = "\n".join(L)
    print(text)
    for a in sys.argv[1:]:
        if a.startswith("--md="):
            Path(a.split("=", 1)[1]).write_text(text + "\n")


if __name__ == "__main__":
    main()
