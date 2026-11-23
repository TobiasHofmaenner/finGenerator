"""Section table against measured sections of its own families [SDF89].

    uv run python scripts/section_measured_check.py [--table=v1] \
        [--md=bench/section-gate/measured/against-table-v1.md]

The symmetric and the cambered family are NACA 4-digit constructions (fingen.foil), so three of
the models in Selig, Donovan & Fraser's low-speed tests are members of them: NACA 0009,
NACA 2.5411 (2.5 % camber at 40 %, t/c 0.11) and NACA 6409 (6 % camber at 40 %, t/c 0.09; the
table ends at 5 % camber, so it is read there and marked). bench/section-gate/measured/ has the
tabulated rows: Reynolds numbers 6e4 to 3e5, smooth models in a low-turbulence tunnel.

For every measured polar at a Reynolds number the table covers (from 1.0e5; the table's lowest
is 1.4e5 and it is read there below that), beside the table's section at the same Reynolds number:
  * lift at 4, 6, 8 and 9 deg;
  * where the lift is 5 % below the line through its own rows nearest 2 and 4 deg, and the lift
    there
    (the measure a blade's knee is read by);
  * the highest lift in the measured rows (marked where the rows end there) and the table's
    `cl_limit`, with their angles;
  * drag at 4 deg.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from fingen import sections
from fingen.params import FoilFamily

MEASURED = Path(__file__).resolve().parent.parent / "bench/section-gate/measured"
CASES = (("NACA 0009", "sdf89-naca0009.csv", FoilFamily.SYMMETRIC, 0.09, 0.0, ""),
         ("NACA 2.5411", "sdf89-naca2.5411.csv", FoilFamily.CAMBERED, 0.11, 0.025, ""),
         ("NACA 6409", "sdf89-naca6409.csv", FoilFamily.CAMBERED, 0.09, 0.06,
          " (table read at its edge, 5 % camber)"))
RE_MIN = 1.0e5
ANGLES = (4.0, 6.0, 8.0, 9.0)


def read(name: str) -> dict[float, np.ndarray]:
    rows: dict[float, list] = {}
    for line in (MEASURED / name).read_text().splitlines():
        if line.startswith("#") or line.startswith("re,"):
            continue
        re, a, cl, cd = (float(x) for x in line.split(","))
        rows.setdefault(re, []).append((a, cl, cd))
    return {re: np.array(r) for re, r in rows.items()}


def line_2_4(a: np.ndarray, cl: np.ndarray) -> tuple[float, float]:
    """(slope per deg, lift at 0) of the line through the rows nearest 2 and 4 deg."""
    i, j = int(np.argmin(abs(a - 2.0))), int(np.argmin(abs(a - 4.0)))
    k = (cl[j] - cl[i]) / (a[j] - a[i])
    return k, cl[i] - k * a[i]


def five_below(a: np.ndarray, cl: np.ndarray) -> tuple[float, float] | None:
    """(angle, lift) where the lift is first 5 % below its line through 2 and 4 deg, past 4 deg."""
    k, c0 = line_2_4(a, cl)
    before = None
    for x, y in zip(a, cl, strict=True):
        if x < 4.0:
            continue
        dep = y / (k * x + c0) - 1.0
        if before is not None and dep < -0.05 <= before[1]:
            t = (before[1] + 0.05) / (before[1] - dep)
            return before[0] + t * (x - before[0]), before[2] + t * (y - before[2])
        before = (x, dep, y)
    return None


def fmt(v: tuple[float, float] | None, last: float) -> str:
    return f"{v[0]:.1f}°, {v[1]:.2f}" if v else f"beyond {last:.1f}°"


def main() -> None:
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    table = opt.get("table", "v1")
    lines = [f"# Section table {table} against measured sections of its own families [SDF89]", "",
             "Written by `scripts/section_measured_check.py`. Measured: smooth models, "
             "low-turbulence tunnel, no trip. Table: fully turbulent, on the held stream. "
             "\"5 % below\" is against each polar's own line through its rows nearest 2° and 4°. "
             "The measured highest lift is the highest tabulated row, marked `+` where that is "
             "the last row (the drag survey ends where the wake gets too wide).", "",
             "| section | Re | c_l at 4° / 6° / 8° / 9°: measured | table | 5 % below its line: "
             "measured | table | highest lift: measured | table's limit, end of attached range | "
             "c_d at 4°: measured / table |",
             "|---|---|---|---|---|---|---|---|---|"]
    for label, name, family, tc, camber, note in CASES:
        for re, rows in sorted(read(name).items()):
            if re < RE_MIN:
                continue
            a, cl, cd = rows.T
            pol = sections.polar(family, tc, re, camber, table)
            grid = np.arange(0.0, 16.01, 0.25)
            end = pol.attached_deg[1] if pol.attached_deg else pol.alpha_break_deg
            inside = grid <= end + 1e-9
            tcl = np.array([float(pol.cl_at(x)) for x in grid])
            k = int(np.argmax(cl))
            rising = "+" if k == len(cl) - 1 else ""

            def at(x: float, arr_a=a, arr=cl) -> str:
                return f"{np.interp(x, arr_a, arr):.3f}" if arr_a[-1] >= x - 0.3 else "–"

            lines.append(
                f"| {label}{note} | {re:.3g} | " + " / ".join(at(x) for x in ANGLES) + " | "
                + " / ".join(f"{float(pol.cl_at(x)):.3f}" if x <= end + 0.01 else "(past its end)"
                             for x in ANGLES) + " | "
                + fmt(five_below(a, cl), a[-1]) + " | "
                + fmt(five_below(grid[inside], tcl[inside]), end)
                + f" | {cl[k]:.2f}{rising} at {a[k]:.1f}° | {pol.cl_limit:.2f}, {end:.1f}°"
                + (" (clipped)" if pol.clipped else "")
                + f" | {np.interp(4.0, a, cd):.4f} / {float(pol.cd_at(4.0)):.4f} |")
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
