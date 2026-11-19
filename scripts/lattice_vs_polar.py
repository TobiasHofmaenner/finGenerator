"""The lattice model against an isolated-fin CFD polar, angle by angle.

    uv run python scripts/lattice_vs_polar.py <bench dir> [<bench dir> ...] [--md=out.md]

Each bench directory holds what finGenerator-cfd/scripts/polar_angles.py wrote:
`plan.json` (speed, fin file, variants with an optional foil patch) and
`results.json` (CL, CD per own incidence). For every variant the same blade is
solved with `bladehydro.point` — the viscous lattice on the section table, the
board as a weakened mirror — at the CFD's speed and angles, and the two are
printed side by side: lift coefficient, drag in N, and the ratio.

This is the check that says where the fast model may be trusted. Read it per
REGIME (negative incidence = going straight at toe; small positive = working
load; past ~8 deg = toward the break, where the strip model has no knee and
wall-function RANS is itself a lower bound on lift, docs/CFD-BENCH.md).
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

from fingen import bladehydro
from fingen.hydro import RHO_SEAWATER
from fingen.optimize import fin_from_dict
from fingen.outline import metrics
from fingen.params import FoilFamily


def _patched(fin, patch: dict):
    foil = dict(patch.get("foil", {}))
    if "family" in foil:
        foil["family"] = FoilFamily(foil["family"])
    return dataclasses.replace(fin, foil=dataclasses.replace(fin.foil, **foil)) if foil else fin


def compare(bench: Path) -> list[str]:
    plan = json.loads((bench / "plan.json").read_text())
    res = json.loads((bench / "results.json").read_text())["variants"]
    raw = json.loads((bench / plan["fin"]).read_text())
    base = fin_from_dict(raw.get("fin", raw))
    speed = float(plan["speed"])
    out: list[str] = []
    for variant in plan["variants"]:
        name = variant["name"]
        if name not in res:
            continue
        fin = _patched(base, variant.get("patch", {}))
        f = fin.foil
        q_area = 0.5 * RHO_SEAWATER * speed**2 * metrics(fin.outline).area * 1e-6
        out.append(f"\n### {bench.name} / {name} — {f.family.value}, t/c {f.thickness_ratio:.3f}, camber "
                   f"{f.camber_ratio * 100:.1f} %, {metrics(fin.outline).area:.0f} mm², {speed:g} m/s\n")
        out.append("| own incidence ° | CL CFD | CL lattice | drag CFD N | drag lattice N | lattice / CFD | CFD iterations |")
        out.append("|---|---|---|---|---|---|---|")
        for row in sorted(res[name]["rows"], key=lambda r: r["alpha"]):
            loads, converged = bladehydro.point(fin, speed, row["alpha"])
            capped = row.get("iterations", 0) >= plan.get("end_time", 1e9)
            out.append(f"| {row['alpha']:+.1f} | {row['cl']:+.3f} | {loads.cl:+.3f} | {row['cd'] * q_area:.1f} | "
                       f"{loads.cd * q_area:.1f}{'' if converged else ' (strips not converged)'} | "
                       f"{loads.cd / row['cd']:.2f} | {row.get('iterations', float('nan')):.0f}{' (cap)' if capped else ''} |")
    return out


def main() -> None:
    dirs = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
    if not dirs:
        sys.exit(__doc__)
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    lines = ["# Lattice model vs isolated-fin CFD"]
    for d in dirs:
        lines += compare(d)
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
