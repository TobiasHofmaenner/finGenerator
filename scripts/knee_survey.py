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

Two more columns bracket it: where the most loaded strip reaches the END of its
section's attached lift (a share of one), and where the lattice's own polar,
run through its sections' ends with no criterion at all, is 5 % below its line.
Thin symmetric blades follow those two; side blades and the thick centre leave
their line long before (bench/knee/one-degree).
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
    cl_limit = np.array([p.cl_limit for p in pol])
    rate = (hi.cl_local - lo.cl_local) / 4.0
    reach = np.where(rate > 1e-6, 2.0 + (fraction * cl_limit - lo.cl_local) / np.maximum(rate, 1e-6),
                     np.inf)
    alpha = float(reach.min())
    return alpha, lo.cl + (hi.cl - lo.cl) / 4.0 * (alpha - 2.0)


def own_knee(fin: FinParams, speed: float, drop: float = 0.05, table: str = "v1") -> str:
    """Where the lattice's own polar, run through its sections' ends with no criterion, is
    `drop` below its line through 2 and 6 deg (perfect mirror; half-degree steps to 20 deg)."""
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pol = {"blade": lattice.strip_sections(fin, blade, speed, table)}

    def cl(a: float) -> float:
        return lattice.solve_viscous([blade], pol, speed, a, mirror_strength=1.0).loads["blade"].cl

    lo, hi = cl(2.0), cl(6.0)
    before = 0.0
    for a in np.arange(6.5, 20.01, 0.5):
        dep = cl(float(a)) / (lo + (hi - lo) / 4.0 * (a - 2.0)) - 1.0
        if dep < -drop:
            return f"{a - 0.5 + 0.5 * (-drop - before) / (dep - before):.1f}"
        before = dep
    return "beyond 20"


def cases() -> list[tuple[str, FinParams, float, tuple[np.ndarray, np.ndarray]]]:
    shipped = _fin("mount/fins/side-shipped-gen2.json")
    centre = _fin("mount/fins/centre-ridden-gen1.json")
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
        # one mesh level finer on the fin the hold floor is anchored on (bench/knee/one-degree)
        ("gen-2 side as shipped, mesh level 6, one-degree steps", shipped, 8.5,
         _polar("knee/one-degree/results-L6-flat.json", "flat-inside-L6")),
        ("gen-1 centre as ridden, symmetric, mesh level 6, one-degree steps",
         _fin("mount/fins/centre-ridden-gen1.json"), 8.5,
         _polar("knee/one-degree/results-L6-centre.json", "centre-gen1-L6")),
        # the generation-3 side for 8.5 m/s and 55 deg of lean, and its twin with a narrow tip
        # (bench/design-points/cfd): the first pair of polars that differs in tip width alone
        ("gen-3 side for 8.5 m/s, 55° (4.5 % camber, tip 0.60 of the base), mesh level 5, "
         "one-degree steps",
         _fin("design-points/cfd/fin-sliders.json"), 8.5,
         _polar("design-points/cfd/sliders-L5.json", "gen3-side-sliders-L5")),
        ("the same fin with its tip at 0.35 of the base, mesh level 5, one-degree steps",
         _fin("design-points/cfd/fin-sliders-tip035.json"), 8.5,
         _polar("design-points/cfd/tip035-L5.json", "gen3-side-sliders-tip035-L5")),
        ("gen-3 side for the same turn as the search made it with the twelve edge offsets, "
         "mesh level 5, one-degree steps",
         _fin("design-points/cfd/fin-offsets.json"), 8.5,
         _polar("design-points/cfd/offsets-L5.json", "gen3-side-L5")),
        # blades for the other setups, mesh level 5 (bench/phase2b)
        ("longboard single (stand-in, 240 mm, raked 45°), symmetric t/c 0.08, mesh level 5",
         _fin("phase2b/single-longboard/fins/single-longboard.json"), 5.0,
         _polar("phase2b/single-longboard/results.json", "single-longboard-L5")),
        ("gen-1 centre with t/c 0.09 instead of 0.046, mesh level 5", dataclasses.replace(centre, foil=dataclasses.replace(
            centre.foil, thickness_ratio=0.09)), 8.5,
         _polar("phase2b/centre-thick/results.json", "centre-gen1-tc090-L5")),
        # the test with its prediction written first (bench/knee/one-degree, 2026-11-23): the
        # gen-2 side's planform with a thin symmetric foil
        ("gen-2 side's planform with a symmetric foil of t/c 0.05, mesh level 5, one-degree steps",
         _fin("knee/one-degree/fin-gen2-planform-sym-tc050.json"), 8.5,
         _polar("knee/one-degree/results-L5-thin-sym.json", "sym-tc050-gen2-planform-L5")),
        ("the same, mesh level 6",
         _fin("knee/one-degree/fin-gen2-planform-sym-tc050.json"), 8.5,
         _polar("knee/one-degree/results-L6-thin-sym.json", "sym-tc050-gen2-planform-L6")),
        # the thickness series on that planform (predictions filed first)
        ("gen-2 side's planform, symmetric t/c 0.066, mesh level 5, one-degree steps",
         _fin("knee/one-degree/fin-gen2-planform-sym-tc066.json"), 8.5,
         _polar("knee/one-degree/results-L5-sym-tc066.json", "sym-tc066-gen2-planform-L5")),
        ("gen-2 side's planform, symmetric t/c 0.080, mesh level 5, one-degree steps",
         _fin("knee/one-degree/fin-gen2-planform-sym-tc080.json"), 8.5,
         _polar("knee/one-degree/results-L5-sym-tc080.json", "sym-tc080-gen2-planform-L5")),
        # the controls on that series (bench/knee/one-degree): one level finer, half the speed, and
        # a finer nose (level 7), which moves the break where level 6 did not; all three on the
        # coarsely faceted surface found afterwards (the record has the reruns)
        ("the same, mesh level 6",
         _fin("knee/one-degree/fin-gen2-planform-sym-tc080.json"), 8.5,
         _polar("knee/one-degree/results-L6-sym-tc080.json", "sym-tc080-gen2-planform-L6")),
        ("the same, mesh level 7 (level 6 with the nose split once more)",
         _fin("knee/one-degree/fin-gen2-planform-sym-tc080.json"), 8.5,
         _polar("knee/one-degree/results-L7-sym-tc080.json", "sym-tc080-gen2-planform-L7")),
        ("gen-2 side's planform, symmetric t/c 0.066, mesh level 5, at 5 m/s",
         _fin("knee/one-degree/fin-gen2-planform-sym-tc066.json"), 5.0,
         _polar("knee/one-degree/results-L5-sym-tc066-5ms.json", "sym-tc066-gen2-planform-5ms-L5")),
        ("twin keel (stand-in, 95 mm deep), flat inside t/c 0.10, mesh level 5",
         _fin("phase2b/twin-keel/fins/twin-keel.json"), 7.0,
         _polar("phase2b/twin-keel/results.json", "twin-keel-L5")),
    ]


def main() -> None:
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    fraction = float(opt.get("fraction", bladehydro.KNEE_FRACTION))
    lines = [f"# Where each blade leaves its lift line (strip criterion at {fraction:g} of the most lift the section carries attached)",
             "",
             "| blade | geometric aspect ratio | polar: 5 % below its line between ° | aspect-ratio rule ° | "
             "strip criterion °: perfect mirror / board mirror | C_L at the knee: rule / criterion (perfect mirror) | "
             "highest C_L in the polar | most loaded strip at the end of its section's attached lift "
             "(a share of one), perfect mirror ° | the lattice's own polar, run through its sections' "
             "ends: 5 % below its line at ° |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, fin, speed, (a, cl) in cases():
        slope0, ar_eff = hydro.lift_curve_slope(fin)
        a_rule = hydro.break_alpha_deg(fin, ar_eff)
        cl_rule = slope0 * math.radians(a_rule - hydro.zero_lift_alpha_deg(fin))
        a_full, cl_full = strip_knee(fin, speed, fraction, 1.0)
        a_board, _ = strip_knee(fin, speed, fraction, bladehydro.BOARD_MIRROR_STRENGTH)
        a_one, _ = strip_knee(fin, speed, 1.0, 1.0)
        bracket, cl_max = polar_knee(a, cl)
        cells = [name, f"{ar_eff / hydro.REFLECTION_FACTOR:.2f}", bracket, f"{a_rule:.1f}",
                 f"{a_full:.1f} / {a_board:.1f}", f"{cl_rule:.2f} / {cl_full:.2f}", f"{cl_max:.2f}",
                 f"{a_one:.1f}", own_knee(fin, speed)]
        lines.append("| " + " | ".join(cells) + " |")
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
