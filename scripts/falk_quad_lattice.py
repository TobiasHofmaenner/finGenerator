"""The [Falk20] four-fin layout through the lattice, beside our set CFD and the paper's per-fin forces.

    uv run python scripts/falk_quad_lattice.py [--md=bench/falk/quad-level5-foils/lattice.md]

Three stand-in foils have a set run on mesh level 5 (bench/falk/quad-level5 and
quad-level5-foils), one of them a second time with less toe on the rear pair.
For each, every fin's lift from the linear lattice (attached
flow, no section data), lift and drag from the viscous lattice on section table
v1, the set CFD and the paper. The CFD has the fins on a flat wall, so the
lattice is solved with a perfect mirror.

Then the rear pair's toe is varied in the linear lattice. The paper gives one
toe (3.5 deg); our set run put it on all four fins. If the rear split of the
paper is a matter of the rear toe, the lattice says which.
"""

from __future__ import annotations

import csv
import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

from fingen import lattice
from fingen.params import FinConfig, FinParams, FinSetParams, FoilFamily, FoilParams, OutlineParams

BENCH = Path(__file__).resolve().parent.parent / "bench/falk"
SPEED = 10.0
SLOTS = ("front_right", "front_left", "rear_right", "rear_left")       # inside rail = right
NAMES = ("front inside", "front outside", "rear inside", "rear outside")
REF_COLS = ("front_IF", "front_OF", "rear_IF", "rear_OF")
RUNS = (("flat inside, t/c 0.09 (the first stand-in)", "quad-level5/falk-quad.json"),
        ("flat inside, t/c 0.065", "quad-level5-foils/flat-tc065/falk-quad.json"),
        ("3 % camber, t/c 0.065", "quad-level5-foils/camb3-tc065/falk-quad.json"),
        ("flat inside, t/c 0.065, rear pair at 2° of toe",
         "quad-level5-foils/flat-tc065-reartoe2/falk-quad.json"))


def reference() -> dict[tuple[str, float], dict[str, float]]:
    out = {}
    with (BENCH / "falk20_perfin_forces.csv").open() as fh:
        for row in csv.reader(line for line in fh if not line.startswith("#")):
            out[(row[0], float(row[1]))] = dict(zip(REF_COLS, map(float, row[2:6]), strict=True))
    return out


def quad(foil: dict, rear_toe: float = 3.5) -> tuple[FinParams, FinSetParams]:
    """The stand-in fin and the layout of finGenerator-cfd scripts/falk_quad.py."""
    f = dataclasses.replace(FoilParams(family=FoilFamily(foil["family"])),
                            thickness_ratio=foil["thickness_ratio"], camber_ratio=foil["camber_ratio"])
    fin = FinParams(outline=OutlineParams(depth=116.0, base=111.0, sweep=33.0, tip_width_ratio=0.36,
                                          le_fullness=1.0, te_shape=0.0), foil=f)
    return fin, FinSetParams(config=FinConfig.QUAD, side=fin, toe=3.5, cant=8.5, side_x=-150.0,
                             side_y=165.0, rear_toe=rear_toe, rear_cant=8.5, rear_x=0.0, rear_y=85.0)


def main() -> None:
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    ref = reference()
    lines = ["# The four-fin layout of [Falk20] through the lattice", "",
             "Written by `scripts/falk_quad_lattice.py`. Lattice with a perfect mirror (the set CFD has the "
             "fins on a flat wall), 10 m/s. Linear: attached flow, no section data. Viscous: strips on "
             "section table v1. Held: the same with a flat-inside strip's lift held "
             f"{lattice.LOWER_HOLD_DEG:g}° past the lower end of its attached range (`lattice.held_below`). "
             "CFD: our set run on mesh level 5.", ""]
    for title, rel in RUNS:
        data = json.loads((BENCH / rel).read_text())
        foil = data.get("foil", {"family": "flat_inside", "thickness_ratio": 0.09, "camber_ratio": 0.0})
        fin, sp = quad(foil, data.get("layout", {}).get("rear_toe", 3.5))
        blades = lattice.set_blades(sp, nz=10, nx=2)
        pol = {b.name: lattice.strip_sections(fin, b, SPEED, "v1") for b in blades}
        held = {name: lattice.held_below(p) for name, p in pol.items()}
        lines += [f"## {title}", "",
                  "| leeway ° | fin | lift: linear lattice | viscous lattice | viscous, held | set CFD | "
                  "[Falk20] | drag: viscous lattice | viscous, held | set CFD | [Falk20] |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for row in sorted(data["rows"], key=lambda r: r["angle"]):
            lee = row["angle"]
            lin = lattice.solve(blades, SPEED, lee, mirror_strength=1.0)
            vis = lattice.solve_viscous(blades, pol, SPEED, lee, mirror_strength=1.0).loads
            hld = lattice.solve_viscous(blades, held, SPEED, lee, mirror_strength=1.0).loads
            for slot, name, col in zip(SLOTS, NAMES, REF_COLS, strict=True):
                c = row["coeffs"][slot]
                lines.append(f"| {lee:.0f} | {name} | {lin[slot].cl:.3f} | {vis[slot].cl:.3f} | "
                             f"{hld[slot].cl:.3f} | {c['cl']:.3f} | {ref[('CL', lee)][col]:.3f} | "
                             f"{vis[slot].cd:.3f} | {hld[slot].cd:.3f} | {c['cd']:.3f} | "
                             f"{ref[('CD', lee)][col]:.3f} |")
        lines.append("")
    # the rear pair's toe, linear lattice, flat inside t/c 0.065 (the foil whose front pair matches theirs)
    foil = {"family": "flat_inside", "thickness_ratio": 0.065, "camber_ratio": 0.0}
    angles = (5.0, 10.0, 15.0)
    lines += ["## The rear pair's toe (linear lattice, flat inside t/c 0.065, front toe 3.5°)", "",
              "| rear toe ° | rear inside at 5 / 10 / 15° | rear outside at 5 / 10 / 15° | "
              "front inside | front outside | rear fins against [Falk20], rms |", "|---|---|---|---|---|---|"]
    for rear_toe in (3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0):
        blades = lattice.set_blades(quad(foil, rear_toe)[1], nz=10, nx=2)
        cl = {lee: {s: v.cl for s, v in lattice.solve(blades, SPEED, lee, mirror_strength=1.0).items()}
              for lee in angles}
        miss = [cl[lee][s] - ref[("CL", lee)][c] for lee in angles
                for s, c in (("rear_right", "rear_IF"), ("rear_left", "rear_OF"))]
        cells = [" / ".join(f"{cl[lee][s]:.3f}" for lee in angles) for s in
                 ("rear_right", "rear_left", "front_right", "front_left")]
        lines.append(f"| {rear_toe:.1f} | " + " | ".join(cells) + f" | {np.sqrt(np.mean(np.square(miss))):.3f} |")
    for rel in (RUNS[1][1], RUNS[3][1]):          # the two set runs of this foil
        data = json.loads((BENCH / rel).read_text())
        cfd = {r["angle"]: {s: r["coeffs"][s]["cl"] for s in SLOTS} for r in data["rows"]}
        miss = [cfd[lee][s] - ref[("CL", lee)][c] for lee in angles
                for s, c in (("rear_right", "rear_IF"), ("rear_left", "rear_OF"))]
        cells = [" / ".join(f"{cfd[lee][s]:.3f}" for lee in angles) for s in
                 ("rear_right", "rear_left", "front_right", "front_left")]
        lines.append(f"| set CFD, {data['layout'].get('rear_toe', 3.5):.1f} | " + " | ".join(cells)
                     + f" | {np.sqrt(np.mean(np.square(miss))):.3f} |")
    lines.append("| [Falk20] | " + " | ".join(" / ".join(f"{ref[('CL', lee)][c]:.3f}" for lee in angles)
                                             for c in ("rear_IF", "rear_OF", "front_IF", "front_OF")) + " | |")
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
