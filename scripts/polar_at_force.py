"""CFD polars read the way a rider loads a fin: drag at EQUAL side force.

    uv run python scripts/polar_at_force.py <bench dir> [<bench dir> ...]
        [--forces=0,93,200,318] [--merge=<bench name>/<variant>=<polar.json>]
        [--polar=<label>:<area mm²>:<polar.json>] [--md=out.md]

Each bench directory holds `plan.json` and `results.json` as written by
finGenerator-cfd/scripts/polar_angles.py (isolated fin, CL and CD per own
incidence). For every variant: the largest side force in the polar and the
angle it occurs at, then the drag in N while making each requested force,
interpolated along the rising branch of the polar. A force the fin never
reaches is printed as "—" — it cannot hold that load at this speed.

Coefficients hide size; this table does not: a larger blade makes the same
force at a smaller lift coefficient. --merge adds rows from another polar file
(same fin, other angles) to a variant; --polar adds a fin that has only a
single polar file (`speed` and `rows` inside, as the verify stage writes it).

Wall-function RANS: the largest force is a LOWER bound (docs/CFD-BENCH.md).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from fingen.hydro import RHO_SEAWATER


def polars(bench: Path, merge: dict[str, Path]) -> list[tuple[str, float, float, np.ndarray]]:
    """[(label, speed, area mm², rows[alpha, cl, cd] sorted by alpha)]"""
    plan = json.loads((bench / "plan.json").read_text())
    out = []
    for name, v in json.loads((bench / "results.json").read_text())["variants"].items():
        rows = list(v["rows"])
        extra = merge.get(f"{bench.name}/{name}")
        if extra:
            rows += json.loads(extra.read_text())["rows"]
        by_alpha = {round(r["alpha"], 3): r for r in rows}
        arr = np.array([[a, r["cl"], r["cd"]] for a, r in sorted(by_alpha.items())])
        out.append((f"{bench.name} / {name}", float(plan["speed"]), float(v["area_mm2"]), arr))
    return out


def drag_at(force_n: float, q_area: float, arr: np.ndarray) -> float | None:
    """Drag in N at side force `force_n`, on the branch that rises to the maximum."""
    k = int(np.argmax(arr[:, 1]))
    lift, drag = arr[: k + 1, 1] * q_area, arr[: k + 1, 2] * q_area
    if not lift[0] <= force_n <= lift[-1] or np.any(np.diff(lift) <= 0.0):
        if force_n > lift[-1] or force_n < lift.min():
            return None
        order = np.argsort(lift)
        lift, drag = lift[order], drag[order]
    return float(np.interp(force_n, lift, drag))


def main() -> None:
    dirs = [Path(a) for a in sys.argv[1:] if not a.startswith("--")]
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    flags = [a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a]
    forces = [93.0, 200.0, 318.0]
    merge: dict[str, Path] = {}
    single: list[tuple[str, float, float, np.ndarray]] = []
    md = None
    for key, value in flags:
        if key == "forces":
            forces = [float(x) for x in value.split(",")]
        elif key == "merge":
            target, path = value.split("=", 1)
            merge[target] = Path(path)
        elif key == "polar":
            label, area, path = value.split(":", 2)
            raw = json.loads(Path(path).read_text())
            arr = np.array(sorted([r["alpha"], r["cl"], r["cd"]] for r in raw["rows"]))
            single.append((label, float(raw["speed"]), float(area), arr))
        elif key == "md":
            md = Path(value)
    lines = ["| fin | area mm² | going straight (−3.5°) N | largest force N | at ° | "
             + " | ".join(f"drag at {f:.0f} N" for f in forces) + " |",
             "|---|---|---|---|---|" + "---|" * len(forces)]
    for group in [single, *(polars(d, merge) for d in dirs)]:
        for label, speed, area, arr in group:
            q_area = 0.5 * RHO_SEAWATER * speed**2 * area * 1e-6
            k = int(np.argmax(arr[:, 1]))
            straight = arr[np.isclose(arr[:, 0], -3.5), 2]
            cells = []
            for f in forces:
                dn = drag_at(f, q_area, arr)
                cells.append("—" if dn is None else f"{dn:.1f}")
            lines.append(f"| {label} | {area:.0f} | {f'{straight[0] * q_area:.1f}' if len(straight) else '—'} | "
                         f"{arr[k, 1] * q_area:.0f} | {arr[k, 0]:.0f}{' (last angle run)' if k == len(arr) - 1 else ''} | "
                         + " | ".join(cells) + " |")
    text = "\n".join(lines)
    print(text)
    if md:
        md.write_text(text + "\n")


if __name__ == "__main__":
    main()
