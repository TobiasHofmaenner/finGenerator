"""The section gate's tables: runs of one section side by side, against a measured polar.

    uv run python scripts/section_gate_tables.py naca0012 old-inlet quiet quieter held
    uv run python scripts/section_gate_tables.py naca4415 old-inlet held-gate
    uv run python scripts/section_gate_tables.py camb3-tc070-re140k old-inlet held quiet

Reads bench/section-gate/runs.json (lift and drag of every run of the gate and of the
stream study) and, for the two measured sections, the reference polars in bench/.
"(i)" marks a measured value interpolated between two angles, "*" a row that did not
settle within the iteration limit.
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
REF = {"naca0012": "bench/ref-sk81-naca0012-re0.7M.dat",
       "naca4415": "bench/ref-osu-naca4415-re0.75M.dat"}


def measured(path: Path) -> np.ndarray:
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append([float(x) for x in line.split()[:3]])
        except ValueError:
            continue
    return np.array([r for r in rows if len(r) == 3])


def main() -> None:
    section, labels = sys.argv[1], sys.argv[2:]
    runs = json.loads((REPO / "bench/section-gate/runs.json").read_text())["runs"]
    have = [(lab, {round(r["alpha"], 2): r for r in runs[f"{section}/{lab}"]["rows"]})
            for lab in labels]
    ref = measured(REPO / REF[section]) if section in REF else None
    angles = sorted({a for _, rows in have for a in rows})
    head = "| α ° |" + (" measured c_l | c_d |" if ref is not None else "")
    head += "".join(f" {lab} c_l | c_d |" for lab, _ in have)
    print(head)
    print("|" + "---|" * (head.count("|") - 1))
    for a in angles:
        line = f"| {a:g} |"
        if ref is not None:
            if ref[:, 0].min() <= a <= ref[:, 0].max():
                mark = "" if np.any(np.abs(ref[:, 0] - a) < 0.06) else " (i)"
                ok = ref[:, 2] > 0
                inside = ref[ok, 0].min() <= a <= ref[ok, 0].max()
                cd = f"{np.interp(a, ref[ok, 0], ref[ok, 2]):.4f}" if inside else ""
                line += f" {np.interp(a, ref[:, 0], ref[:, 1]):.3f}{mark} | {cd} |"
            else:
                line += " | |"
        for _, rows in have:
            r = rows.get(a)
            flag = "" if r is None or r["settled"] else "*"
            line += f" {r['cl']:.4f}{flag} | {r['cd']:.5f} |" if r else " | |"
        print(line)
    print()
    for lab, _ in have:
        e = runs[f"{section}/{lab}"]
        m = e["mesh"]
        first = m.get("first_layer", float("nan")) * 1e6
        note = f"; {e['note']}" if e["note"] else ""
        print(f"- {lab}: `{e['run']}`, {e['stream']}; {m.get('cells')} cells, "
              f"{m.get('n_layers')} layers from {first:.1f} µm{note}")


if __name__ == "__main__":
    main()
