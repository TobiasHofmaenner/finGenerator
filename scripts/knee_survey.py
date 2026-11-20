"""Where each benchmarked blade leaves its lift line: the stored 3-D polars against
the aspect-ratio rule (hydro.break_alpha_deg) and the strip criterion (bladehydro.knee).

    uv run python scripts/knee_survey.py [--fraction=0.70] [--md=out.md]

A polar's knee is read as the angle at which its lift has fallen 5 % below the
line through its 0…6 deg samples; with 4-degree steps that is a bracket, and the
interpolated value inside it is indicative. All polars are wall-function RANS
(docs/CFD-BENCH.md): rows up to the knee are evidence, the lift past it is a
lower bound. The tunnel fin [BW04] has a measurement: on its line at 12 deg,
6 % below it at 14.

The strip criterion is solved twice: on a perfect mirror (the boundary condition
of the CFD polars, a symmetry plane) and on the board mirror the model uses
(bladehydro.BOARD_MIRROR_STRENGTH), which is the one KNEE_FRACTION is fitted on.
"""

from __future__ import annotations

import dataclasses
import json
import math
import sys
from pathlib import Path

import numpy as np

from fingen import bladehydro, hydro, lattice
from fingen.optimize import fin_from_dict
from fingen.params import FinParams, FoilFamily, FoilParams, OutlineParams

BENCH = Path(__file__).resolve().parent.parent / "bench"


def bw04() -> FinParams:
    """The [BW04] water-tunnel fin replica (finGenerator-cfd/scripts/bw04_polar.py)."""
    return FinParams(outline=OutlineParams(depth=120.0, base=100.0, sweep=25.0,
                                           tip_width_ratio=0.45, le_fullness=0.75, te_shape=0.8),
                     foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.09),
                     thickness_tip_factor=1.0)


def _fin(path: str) -> FinParams:
    raw = json.loads((BENCH / path).read_text())
    return fin_from_dict(raw.get("fin", raw))


def _polar(path: str, variant: str | None = None) -> tuple[np.ndarray, np.ndarray]:
    data = json.loads((BENCH / path).read_text())
    rows = data if isinstance(data, list) else (
        data["variants"][variant]["rows"] if variant else data["rows"])
    a = np.array([r["alpha"] for r in rows], float)
    cl = np.array([r["cl"] for r in rows], float)
    order = np.argsort(a)
    return a[order], cl[order]


def polar_knee(a: np.ndarray, cl: np.ndarray, drop: float = 0.05) -> tuple[str, float]:
    """(bracket and interpolated angle at which the polar is `drop` below its line, highest CL)."""
    lin = (a >= 0.0) & (a <= 6.01)
    slope, cl0 = np.polyfit(a[lin], cl[lin], 1)
    dep = cl / (slope * a + cl0) - 1.0
    for k in range(1, len(a)):
        if a[k] > 6.0 and dep[k] < -drop:
            inside = a[k - 1] + (a[k] - a[k - 1]) * (-drop - dep[k - 1]) / (dep[k] - dep[k - 1])
            digits = 1 if a[k] - a[k - 1] < 2.0 else 0     # one-degree steps resolve a tenth
            return f"{a[k - 1]:.0f}–{a[k]:.0f} (≈ {inside:.{digits}f})", float(cl.max())
    return "not within the polar", float(cl.max())


def strip_knee(fin: FinParams, speed: float, fraction: float, mirror: float,
               table: str = "v1") -> tuple[float, float]:
    """bladehydro.knee at any mirror strength and fraction (same two solves, same rule)."""
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pol = lattice.strip_sections(fin, blade, speed, table)
    lo, hi = (lattice.solve_viscous([blade], {"blade": pol}, speed, a,
                                    mirror_strength=mirror).loads["blade"] for a in (2.0, 6.0))
    cl_break = np.array([float(p.cl_at(p.alpha_break_deg)) for p in pol])
    rate = (hi.cl_local - lo.cl_local) / 4.0
    reach = np.where(rate > 1e-6, 2.0 + (fraction * cl_break - lo.cl_local) / np.maximum(rate, 1e-6),
                     np.inf)
    alpha = float(reach.min())
    return alpha, lo.cl + (hi.cl - lo.cl) / 4.0 * (alpha - 2.0)


def cases() -> list[tuple[str, FinParams, float, tuple[np.ndarray, np.ndarray]]]:
    shipped = _fin("mount/fins/side-shipped-gen2.json")
    cam3 = dataclasses.replace(shipped, foil=dataclasses.replace(
        shipped.foil, family=FoilFamily.CAMBERED, camber_ratio=0.03, camber_position=0.4))
    return [
        ("tunnel fin [BW04], flat inside (tunnel: on its line at 12°, 6 % below at 14°)", bw04(), 7.0,
         _polar("bw04-polar-ideal.json")),
        ("gen-2 side as shipped, flat inside", shipped, 8.5,
         _polar("foil-family/flat-inside-verify-polar.json")),
        ("same planform, 3 % camber, mesh level 2", cam3, 8.5,
         _polar("foil-family/results.json", "cambered-3pct")),
        ("same planform, 3 % camber, mesh level 5", cam3, 8.5,
         _polar("cambered-candidate/mesh-level-5/results.json", "cambered-3pct-L5")),
        ("cambered candidate (4.3 %, t/c 0.074)", _fin("cambered-candidate/fins/side-cambered-candidate.json"),
         8.5, _polar("cambered-candidate/results.json", "cambered-candidate")),
        ("gen-1 side as ridden, flat inside", _fin("mount/fins/side-asridden-gen1.json"), 8.5,
         _polar("mount/side-asridden-gen1-verify-polar.json")),
        ("gen-1 centre as ridden, symmetric", _fin("mount/fins/centre-ridden-gen1.json"), 8.5,
         _polar("mount/centre-ridden-gen1-verify-polar.json")),
        ("large low fin (paddle probe), 3.5 % camber", _fin("paddle-probe/fins/side-paddle-probe.json"), 8.5,
         _polar("paddle-probe/results.json", "paddle-probe")),
        # mesh level 5 in one-degree steps around the knee (bench/knee/one-degree)
        ("tunnel fin [BW04], mesh level 5, one-degree steps", bw04(), 7.0,
         _polar("knee/one-degree/results-L5bw04.json", "bw04-L5")),
        ("gen-2 side as shipped, mesh level 5, one-degree steps", shipped, 8.5,
         _polar("knee/one-degree/results-L5.json", "flat-inside-L5")),
        ("best v1-model side (4.2 % camber, t/c 0.089), mesh level 5, one-degree steps",
         _fin("cambered-candidate/mesh-level-5-v1-neutral/fins/side-v1-neutral.json"), 8.5,
         _polar("knee/one-degree/results-L5v1.json", "v1-neutral-L5")),
        ("gen-1 centre as ridden, symmetric, mesh level 5, one-degree steps",
         _fin("mount/fins/centre-ridden-gen1.json"), 8.5,
         _polar("knee/one-degree/results-L5centre.json", "centre-gen1-L5")),
    ]


def main() -> None:
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    fraction = float(opt.get("fraction", bladehydro.KNEE_FRACTION))
    lines = [f"# Where each blade leaves its lift line (strip criterion at {fraction:g} of the section's lift at its break)",
             "",
             "| blade | geometric aspect ratio | polar: 5 % below its line between ° | aspect-ratio rule ° | "
             "strip criterion °: perfect mirror / board mirror | C_L at the knee: rule / criterion (perfect mirror) | "
             "highest C_L in the polar |",
             "|---|---|---|---|---|---|---|"]
    for name, fin, speed, (a, cl) in cases():
        slope0, ar_eff = hydro.lift_curve_slope(fin)
        a_rule = hydro.break_alpha_deg(fin, ar_eff)
        cl_rule = slope0 * math.radians(a_rule - hydro.zero_lift_alpha_deg(fin))
        a_full, cl_full = strip_knee(fin, speed, fraction, 1.0)
        a_board, _ = strip_knee(fin, speed, fraction, bladehydro.BOARD_MIRROR_STRENGTH)
        bracket, cl_max = polar_knee(a, cl)
        lines.append(f"| {name} | {ar_eff / hydro.REFLECTION_FACTOR:.2f} | {bracket} | {a_rule:.1f} | "
                     f"{a_full:.1f} / {a_board:.1f} | {cl_rule:.2f} / {cl_full:.2f} | {cl_max:.2f} |")
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
