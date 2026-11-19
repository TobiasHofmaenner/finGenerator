"""The shipped section table against resolved-wall 2-D RANS, section by section.

    uv run python scripts/section_table_check.py [bench/section-tables/results.json ...] [--md=out.md]

Each results file is what finGenerator-cfd/scripts/section_polar.py wrote: per
section its spec (family, t/c, camber, Reynolds number) and one row per angle
(cl, cd). For every finished section the same section is looked up in
`fingen.sections` (table v0: NeuralFoil, boundary layer tripped) and printed
beside the RANS values, with the drag ratio.

This is the referee for the section data and the input for table v1: where the
ratio sits near one the table stands; where it does not, the RANS rows replace
or correct it. A section still running is listed with the rows it has.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fingen import sections
from fingen.params import FoilFamily

FAMILY = {"flat_inside": FoilFamily.FLAT_INSIDE, "cambered": FoilFamily.CAMBERED,
          "symmetric": FoilFamily.SYMMETRIC}


def check(path: Path) -> list[str]:
    data = json.loads(path.read_text())
    out: list[str] = []
    planned = len(data.get("plan", {}).get("sections", []))
    for name, sec in data["sections"].items():
        spec, rows = sec["spec"], sorted(sec.get("rows", []), key=lambda r: r["alpha"])
        if not rows:
            continue
        pol = sections.polar(FAMILY[spec["family"]], spec["thickness_ratio"], spec["re"],
                             spec.get("camber_ratio") or 0.0)
        done = len(rows) >= len(spec["angles"])
        out.append(f"\n### {name} — {spec['family']}, t/c {spec['thickness_ratio']:.3f}, camber "
                   f"{(spec.get('camber_ratio') or 0.0) * 100:.1f} %, Re {spec['re']:.2g}"
                   f"{'' if done else f' (running: {len(rows)} of {len(spec['angles'])} angles)'}"
                   f"{' — table value clamped to its edge' if pol.clipped else ''}\n")
        out.append("| α ° | cl RANS | cl table | cd RANS | cd table | table / RANS cd | iterations |")
        out.append("|---|---|---|---|---|---|---|")
        for r in rows:
            a = r["alpha"]
            cd_t = float(pol.cd_at(a))
            out.append(f"| {a:+g} | {r['cl']:+.3f} | {float(pol.cl_at(a)):+.3f} | {r['cd']:.4f} | {cd_t:.4f} | "
                       f"{cd_t / r['cd']:.2f} | {r.get('iters', float('nan')):.0f} |")
    done_n = sum(len(s.get("rows", [])) >= len(s["spec"]["angles"]) for s in data["sections"].values())
    out.insert(0, f"\n## {path} — {done_n} of {planned or len(data['sections'])} sections finished")
    return out


def main() -> None:
    bench = Path("bench/section-tables")
    paths = [Path(a) for a in sys.argv[1:] if not a.startswith("--")] or [
        p for p in (bench / "results.json", bench / "thin-cambered/results.json",
                    bench / "third-batch/results.json") if p.exists()]
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    lines = ["# Section table v0 against resolved-wall 2-D RANS"]
    for p in paths:
        lines += check(p)
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
