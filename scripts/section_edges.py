"""Where each section's attached range ends: resolved-wall 2-D RANS against the table.

    uv run python scripts/section_edges.py [results.json ...] [--md=out.md]

For a side fin the two numbers that matter most in a section polar are the
ends of its attached range. Below the lower end the inside face lets go and
the drag rises two- to fourfold within a degree: a cambered side fin going
straight at the 3.5 deg toe works at −2.5 to −4.5 deg, within a degree of it.
Above the upper end (the knee) the lift stops rising: that is where the
blade's hold comes from.

Per finished section this prints, RANS beside the shipped table: lift slope
and zero-lift angle of the 0…+6 deg range, minimum drag, and both ends. An end
is bracketed by the last sample inside the range and the first outside it —
outside meaning, below the drag minimum, cd above 1.5 x the minimum or a run
that hit its iteration cap; above it, a run that hit its cap. The table's
ends are read the same way on a 0.25 deg grid (drag criterion below; above,
the angle where its lift slope has fallen to 30 % — `SectionPolar.alpha_break_deg`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from fingen import sections
from fingen.params import FoilFamily

FAMILY = {"flat_inside": FoilFamily.FLAT_INSIDE, "cambered": FoilFamily.CAMBERED,
          "symmetric": FoilFamily.SYMMETRIC}
FACTOR = 1.5


def rans_ends(rows: list[dict], cap: int) -> tuple[tuple[float, float], tuple[float, float]]:
    """((last inside, first outside) below the drag minimum, the same above it)."""
    k_min = min(range(len(rows)), key=lambda k: rows[k]["cd"])
    limit = FACTOR * rows[k_min]["cd"]
    capped = lambda r: r.get("iters", 0) >= cap  # noqa: E731
    out = {-1: lambda r: r["cd"] > limit or capped(r), 1: capped}
    ends = []
    for step in (-1, 1):
        k = k_min
        while 0 <= k + step < len(rows) and not out[step](rows[k + step]):
            k += step
        beyond = rows[k + step]["alpha"] if 0 <= k + step < len(rows) else float("nan")
        ends.append((rows[k]["alpha"], beyond))
    return ends[0], ends[1]


def table_lower_end(pol: sections.SectionPolar) -> float:
    a = np.arange(-14.0, 6.01, 0.25)
    cd = pol.cd_at(a)
    k = int(np.argmin(cd))
    below = np.nonzero(cd[:k] > FACTOR * cd[k])[0]
    return float(a[below[-1]]) if len(below) else float("nan")


def summarise(path: Path) -> list[str]:
    data = json.loads(path.read_text())
    cap = int(data["plan"].get("end_time", 4000))
    out = []
    for name, sec in data["sections"].items():
        spec, rows = sec["spec"], sorted(sec.get("rows", []), key=lambda r: r["alpha"])
        if len(rows) < len(spec["angles"]) or spec.get("wall", data["plan"].get("wall")) == "wf":
            continue
        pol = sections.polar(FAMILY[spec["family"]], spec["thickness_ratio"], spec["re"],
                             spec.get("camber_ratio") or 0.0)
        a = np.array([r["alpha"] for r in rows])
        cl = np.array([r["cl"] for r in rows])
        lin = (a >= 0.0) & (a <= 6.0)
        s_r, i_r = np.polyfit(a[lin], cl[lin], 1)
        s_t, i_t = np.polyfit(a[lin], pol.cl_at(a[lin]), 1)
        (lo_in, lo_out), (hi_in, hi_out) = rans_ends(rows, cap)
        cl_knee = next(r["cl"] for r in rows if r["alpha"] == hi_in)
        out.append(
            f"| {name} | {spec['thickness_ratio']:.3f} | "
            f"{(spec.get('camber_ratio') or 0) * 100:.1f} | {spec['re']:.2g} | "
            f"{s_r:.4f} / {s_t:.4f} | {-i_r / s_r:+.2f} / {-i_t / s_t:+.2f} | "
            f"{min(r['cd'] for r in rows):.4f} / {float(pol.cd.min()):.4f} | "
            f"{lo_in:+g} … {lo_out:+g} / {table_lower_end(pol):+.2f} | "
            f"{hi_in:+g} … {hi_out:+g} / {pol.alpha_break_deg:+.1f} | "
            f"{cl_knee:.2f} / {float(pol.cl_at(hi_in)):.2f} |")
    return out


def main() -> None:
    bench = Path("bench/section-tables")
    paths = [Path(a) for a in sys.argv[1:] if not a.startswith("--")] or [
        p for p in (bench / "results.json", bench / "thin-cambered/results.json",
                    bench / "third-batch/results.json") if p.exists()]
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:]
               if a.startswith("--") and "=" in a)
    lines = ["# Ends of the attached range: resolved-wall 2-D RANS / table v0", "",
             "| section | t/c | camber % | Re | lift slope per deg | zero-lift angle ° | "
             "minimum cd | "
             "lower end °: RANS bracket / table | knee °: RANS bracket / table | "
             "cl at the last attached angle |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for p in paths:
        lines += summarise(p)
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
