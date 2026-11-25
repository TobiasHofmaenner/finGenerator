"""Section table against maximum lift measured in a turbulent stream [JS37].

    uv run python scripts/section_vdt_check.py [--table=v1] \\
        [--md=bench/section-gate/measured/vdt-against-table-v1.md]

Jacobs & Sherman (1937, NACA Report 586) ran NACA 4-digit sections, which are the symmetric and
the cambered family of fingen.foil, in the variable-density tunnel from a test Reynolds number of
4e4 to 3e6. That tunnel's stream is turbulent (turbulence factor 2.64), about what the table's
held stream assumes (2.6 %), and the models are polished metal. Table I of the report gives the
section maximum lift at each "effective" Reynolds number (2.64 times the test value);
bench/section-gate/measured/js37-clmax.csv has those rows.

For every row from an effective Reynolds number of 2e5 to 2e6 (test 0.8e5 to 7e5: a fin's strips)
this prints the measured maximum beside the table's `cl_limit` at the TEST Reynolds number (the
same viscous scale; the table is turbulent from the nose, the tunnel's layer becomes so where its
stream makes it) and at the effective one (the Reynolds number at which a quiet stream would do
the same, by the report's own reading).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from fingen import sections
from fingen.params import FoilFamily

CSV = Path(__file__).resolve().parent.parent / "bench/section-gate/measured/js37-clmax.csv"
TURBULENCE_FACTOR = 2.64
RE_EFF = (2.0e5, 2.0e6)


def _section(name: str) -> tuple[FoilFamily, float, float]:
    camber, thickness = int(name[0]) / 100.0, int(name[2:]) / 100.0
    return (FoilFamily.CAMBERED if camber else FoilFamily.SYMMETRIC), thickness, camber


def main() -> None:
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    table = opts.get("table", "v1")
    lines = [
        f"# Section table {table} against maximum lift measured in a turbulent stream [JS37]",
        "",
        "Written by `scripts/section_vdt_check.py` from `js37-clmax.csv` (NACA Report 586, "
        "Table I). "
        "Measured: variable-density tunnel, turbulence factor 2.64, polished models; section value "
        "= 1.07 times the maximum of a rectangular wing of aspect ratio 6. Peak: A drops at once, "
        "C breaks between two branches, D is rounded and gradual. Table: turbulent from the nose, "
        "held stream; `cl_limit`, read at the test Reynolds number and at the effective one. "
        "A `*` marks a table value read at its edge (camber above 5 %, or thickness or Reynolds "
        "number outside it).",
        "",
        "| section | Re effective | Re test | measured c_l max | peak | table limit at Re test | "
        "table over measured | table limit at Re effective | table over measured |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    with CSV.open() as fh:
        rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))
    for row in rows:
        re_eff = float(row["re_effective_millions"]) * 1e6
        if not RE_EFF[0] <= re_eff <= RE_EFF[1]:
            continue
        family, thickness, camber = _section(row["section"])
        measured = float(row["cl_max"])
        cells = []
        for re in (re_eff / TURBULENCE_FACTOR, re_eff):
            polar = sections.polar(family, thickness, re, camber, table=table)
            mark = "*" if polar.clipped else ""
            cells += [f"{polar.cl_limit:.2f}{mark}", f"{polar.cl_limit / measured - 1.0:+.0%}"]
        lines.append(
            f"| NACA {row['section']} | {re_eff:.3g} | {re_eff / TURBULENCE_FACTOR:.3g} | "
            f"{measured:.2f} | {row['peak']} | " + " | ".join(cells) + " |"
        )
    text = "\n".join(lines) + "\n"
    if "md" in opts:
        Path(opts["md"]).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
