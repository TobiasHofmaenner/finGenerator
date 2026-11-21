"""A twin set through the lattice, beside its set CFD: what each fin carries.

    uv run python scripts/twin_set_lattice.py <twin-set.json> [--md=out.md]

`twin-set.json` is what finGenerator-cfd scripts/twin_set.py wrote: two equal
side fins on a flat wall at their toe and cant, swept over leeway, lift and
drag per fin. For every leeway the same pair is solved with the linear lattice
(attached flow, no section data) and the viscous one (strips on section table
v1), with a perfect mirror (the CFD's wall).

Lift is counted across the flow in the set's frame, the same direction for
both fins, on each fin's own area. The share is the loaded fin's part of the
pair's side force; `fingen.sizing` assumes 0.75 for a twin.

Then, lattice only: the toe at which a fin of the pair carries nothing going
straight, and the share over leeway at three toes.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

from fingen import lattice
from fingen.optimize import fin_from_dict
from fingen.params import FinConfig, FinParams, FinSetParams

SLOTS = ("right", "left")


def twin(fin: FinParams, layout: dict) -> FinSetParams:
    return FinSetParams(config=FinConfig.TWIN, side=fin, center=None, toe=layout["toe"],
                        cant=layout["cant"], side_x=0.0, side_y=layout["side_y"])


def share(cl: dict[str, float]) -> float:
    """The loaded fin's part of the pair's side force (above 1 when the other fin pushes back)."""
    total = cl["right"] + cl["left"]
    return max(cl.values(), key=abs) / total if abs(total) > 1e-4 else float("nan")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    if not args:
        sys.exit(__doc__)
    data = json.loads(Path(args[0]).read_text())
    fin, layout, speed = fin_from_dict(data["fin"]), data["layout"], float(data["speed"])
    sp = twin(fin, layout)
    blades = lattice.set_blades(sp, nz=10, nx=2)
    pol = {b.name: lattice.strip_sections(fin, b, speed, "v1") for b in blades}
    lines = ["# A twin set through the lattice, beside its set CFD", "",
             f"Written by `scripts/twin_set_lattice.py`. Fin {data['fin_area_mm2']:.0f} mm² "
             f"({fin.foil.family.value}, t/c {fin.foil.thickness_ratio:g}), toe "
             f"{layout['toe']:g}°, cant {layout['cant']:g}°, ±{layout['side_y']:g} mm off the "
             f"centreline, {speed:g} m/s, CFD mesh level {data['mesh_level']}. Lattice with a "
             f"perfect mirror.", "",
             "| leeway ° | fin | lift: linear lattice | viscous lattice | set CFD | "
             "drag: viscous lattice | set CFD |", "|---|---|---|---|---|---|---|"]
    shares = []
    for row in sorted(data["rows"], key=lambda r: r["angle"]):
        lee = row["angle"]
        lin = lattice.solve(blades, speed, lee, mirror_strength=1.0)
        vis = lattice.solve_viscous(blades, pol, speed, lee, mirror_strength=1.0).loads
        for slot in SLOTS:
            c = row["coeffs"][slot]
            lines.append(f"| {lee:g} | {slot} | {lin[slot].cl:+.3f} | {vis[slot].cl:+.3f} | "
                         f"{c['cl']:+.3f} | {vis[slot].cd:.4f} | {c['cd']:.4f} |")
        shares.append((lee, share({s: lin[s].cl for s in SLOTS}),
                       share({s: vis[s].cl for s in SLOTS}),
                       share({s: row["coeffs"][s]["cl"] for s in SLOTS})))
    lines += ["", "| leeway ° | share of the loaded fin: linear lattice | viscous lattice | "
                  "set CFD |", "|---|---|---|---|"]
    lines += [f"| {lee:g} | {a:.2f} | {b:.2f} | {c:.2f} |" for lee, a, b, c in shares]

    # lattice only: the toe at which a fin carries nothing going straight, and the share over toe
    def right_cl(toe: float, lee: float) -> dict[str, float]:
        b = lattice.set_blades(dataclasses.replace(sp, toe=toe), nz=10, nx=2)
        return {s: v.cl for s, v in lattice.solve(b, speed, lee, mirror_strength=1.0).items()}

    c0, c4 = right_cl(0.0, 0.0)["right"], right_cl(4.0, 0.0)["right"]
    toe0 = -4.0 * c0 / (c4 - c0)
    lines += ["", f"Going straight, a fin of this pair carries no side force at {toe0:.2f}° of "
                  f"toe (linear lattice).", "",
              "| toe ° | share of the loaded fin at leeway 2° | 4° | 6° | 8° | 12° |",
              "|---|---|---|---|---|---|"]
    for toe in (0.0, 2.0, 4.0):
        cells = " | ".join(f"{share(right_cl(toe, lee)):.2f}"
                           for lee in (2.0, 4.0, 6.0, 8.0, 12.0))
        lines.append(f"| {toe:g} | {cells} |")
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
