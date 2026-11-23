"""A flat-inside side fin driven from its curved side, alone: the lattice beside its polar.

    uv run python scripts/outside_fin_lattice.py [--md=bench/phase2b/outside-fin/lattice.md]

bench/phase2b/outside-fin has the shipped gen-2 side at own incidence -6 to -16 deg on mesh
levels 5 and 6, on a symmetry plane: what the fin on the outside of a turn does when it is
not in a set. Beside each row the viscous lattice (perfect mirror) with the strips on section
table v1 as it is, and with a flat-inside strip's lift held past the lower end of its attached
range (`lattice.held_below`, LOWER_HOLD_DEG). Then the hold tried at other values: the number
is fitted on this polar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from fingen import bladehydro, lattice
from fingen.optimize import fin_from_dict

BENCH = Path(__file__).resolve().parent.parent / "bench"
RECORD = BENCH / "phase2b/outside-fin"
SPEED = 8.5


def rows(level: int) -> dict[float, tuple[float, float]]:
    data = json.loads((RECORD / f"level{level}.json").read_text())
    (variant,) = data["variants"].values()
    return {r["alpha"]: (r["cl"], r["cd"]) for r in variant["rows"]}


def main() -> None:
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    fin = fin_from_dict(
        json.loads((BENCH / "mount/fins/side-shipped-gen2.json").read_text())["fin"])
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pol = lattice.strip_sections(fin, blade, SPEED, "v1")
    l5, l6 = rows(5), rows(6)
    angles = sorted(set(l5) | set(l6), reverse=True)

    def solve(polars: list, a: float):
        return lattice.solve_viscous([blade], {"blade": polars}, SPEED, a,
                                     mirror_strength=1.0).loads["blade"]

    def cell(row: tuple[float, float] | None) -> str:
        return "–" if row is None else f"{row[0]:+.3f}, {row[1]:.4f}"

    held = lattice.held_below(pol)
    lines = ["# A flat-inside side fin driven from its curved side: the lattice beside its polar",
             "",
             f"Written by `scripts/outside_fin_lattice.py`. The shipped gen-2 side alone, "
             f"{SPEED:g} m/s, perfect mirror. C_L, C_D. \"Held\": a flat-inside strip's lift held "
             f"{lattice.LOWER_HOLD_DEG:g}° past the lower end of its attached range.", "",
             "| own incidence ° | lattice, table as it is | lattice, held | mesh level 5 | "
             "mesh level 6 | strips past their lower end, of 10 |", "|---|---|---|---|---|---|"]
    for a in angles:
        plain, hld = solve(pol, a), solve(held, a)
        low = np.array([p.attached_deg[0] for p in pol])
        lines.append(f"| {a:g} | {plain.cl:+.3f}, {plain.cd:.4f} | {hld.cl:+.3f}, {hld.cd:.4f} | "
                     f"{cell(l5.get(a))} | {cell(l6.get(a))} | "
                     f"{int((plain.alpha_eff_deg < low).sum())} |")
    ref = {a: np.mean([r[a][0] for r in (l5, l6) if a in r]) for a in angles}
    lines += ["", "The hold at other values: lift at each angle, and the rms of lattice over "
                  "simulation less one (the mean of the two levels where both ran).", "",
              "| held from ° past the lower end | " + " | ".join(f"{a:g}°" for a in angles)
              + " | rms |", "|---|" + "---|" * (len(angles) + 1)]
    for delta in (None, 0.5, 1.0, 1.5, 2.0, 2.5):
        polars = pol if delta is None else lattice.held_below(pol, delta)
        cl = {a: solve(polars, a).cl for a in angles}
        rms = float(np.sqrt(np.mean([(cl[a] / ref[a] - 1.0) ** 2 for a in angles])))
        lines.append(f"| {'not held' if delta is None else f'{delta:g}'} | "
                     + " | ".join(f"{cl[a]:+.3f}" for a in angles) + f" | {100 * rms:.0f} % |")
    lines.append("| simulation | " + " | ".join(f"{ref[a]:+.3f}" for a in angles) + " | |")
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
