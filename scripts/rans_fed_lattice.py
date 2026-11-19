"""The lattice with 2-D RANS section data in place of the table, against 3-D CFD.

    uv run python scripts/rans_fed_lattice.py [--md=out.md]

A preview of section table v1 for the cambered block, and the test of one
question: when the model and the isolated-fin CFD disagree on a cambered fin's
drag below its zero-lift angle, how much of the gap is the section table?

The resolved-wall section runs (bench/section-tables/, Re 5.7e5) cover cambered
sections at t/c 0.070 and 0.092 with 3 and 4.5 % camber. For each of those four
nodes the script takes the ratio RANS / table in cd and the difference in cl,
interpolates both bilinearly in thickness and camber (clamped at the nodes),
and applies them to the table polar of every strip — so the table still
carries the Reynolds-number trend. A node whose run has not finished is filled
from the other three. Rows above +8° are not used: past the knee a steady RANS
polar is a lower bound, not a referee (docs/CFD-BENCH.md).

The lattice is solved with a perfect mirror, as the CFD's symmetry plane is one
(bladehydro's 0.85 stands for a real board and reads 8 % less lift). The
section-table v1 that grew out of this script carries the ends of the
attached range instead of blending ratios; `--table=v1` is not needed here
because the ratios ARE the correction — use scripts/lattice_vs_polar.py
--table=v1 to see v1 against the same polars.

Linear interpolation between a section that is inside its low-drag range and
one that has left it smears a step; the numbers at the edge are good to about
the 1° spacing of the section runs.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

from fingen import bladehydro, lattice, sections
from fingen.hydro import RHO_SEAWATER
from fingen.optimize import fin_from_dict
from fingen.outline import metrics
from fingen.params import FoilFamily
from fingen.spider import SIDE_TOE_DEFAULT_DEG

BENCH = Path(__file__).resolve().parent.parent / "bench"
RANS_FILES = (BENCH / "section-tables/results.json",
              BENCH / "section-tables/thin-cambered/results.json")
TC = (0.070, 0.092)
CAMBER = (0.030, 0.045)
RE = 5.7e5
ALPHA_RANGE = (-10.0, 8.0)
SPEED = 8.5
MIRROR = 1.0            # the CFD's symmetry plane, not bladehydro's weakened board mirror


def load_nodes() -> dict:
    nodes: dict = {}
    for path in RANS_FILES:
        for name, sec in json.loads(path.read_text())["sections"].items():
            spec = sec["spec"]
            if spec["family"] != "cambered" or abs(spec["re"] - RE) > 1.0:
                continue
            key = (round(spec["thickness_ratio"], 3), round(spec["camber_ratio"], 3))
            if key[0] not in TC or key[1] not in CAMBER or len(sec["rows"]) < len(spec["angles"]):
                continue
            rows = sorted(sec["rows"], key=lambda r: r["alpha"])
            a = np.array([r["alpha"] for r in rows])
            tab = sections.polar(FoilFamily.CAMBERED, key[0], RE, key[1])
            nodes[key] = {"name": name, "alpha": a,
                          "ratio": np.array([r["cd"] for r in rows]) / tab.cd_at(a),
                          "dcl": np.array([r["cl"] for r in rows]) - tab.cl_at(a)}
    return nodes


def _node(nodes: dict, key: tuple, alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = nodes.get(key)
    if n is not None:
        return np.interp(alpha, n["alpha"], n["ratio"]), np.interp(alpha, n["alpha"], n["dcl"])
    # the unfinished corner, from the other three: ratios multiply, shifts add
    (r_t, d_t), (r_c, d_c), (r_0, d_0) = (_node(nodes, k, alpha) for k in (
        (TC[1], CAMBER[0]), (TC[0], CAMBER[1]), (TC[0], CAMBER[0])))
    return r_t * r_c / r_0, d_t + d_c - d_0


def rans_fed(pol: sections.SectionPolar, nodes: dict) -> sections.SectionPolar:
    """`pol` with the RANS correction of its thickness and camber applied."""
    w_t = min(max((pol.thickness_ratio - TC[0]) / (TC[1] - TC[0]), 0.0), 1.0)
    w_c = min(max((pol.camber_ratio - CAMBER[0]) / (CAMBER[1] - CAMBER[0]), 0.0), 1.0)
    alpha = np.clip(pol.alpha_deg, *ALPHA_RANGE)
    ratio, dcl = np.zeros_like(alpha), np.zeros_like(alpha)
    for t, wt in ((TC[0], 1.0 - w_t), (TC[1], w_t)):
        for c, wc in ((CAMBER[0], 1.0 - w_c), (CAMBER[1], w_c)):
            r, d = _node(nodes, (t, c), alpha)
            ratio += wt * wc * r
            dcl += wt * wc * d
    return dataclasses.replace(pol, cl=pol.cl + dcl, cd=pol.cd * ratio)


def solve(fin, alpha_deg: float, nodes: dict | None):
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pols = lattice.strip_sections(fin, blade, SPEED)
    if nodes is not None:
        pols = [rans_fed(p, nodes) for p in pols]
    sol = lattice.solve_viscous([blade], {"blade": pols}, SPEED, alpha_deg,
                                mirror_strength=MIRROR)
    return sol.loads["blade"]


def _fin(path: Path, foil_patch: dict | None = None):
    raw = json.loads(path.read_text())
    fin = fin_from_dict(raw.get("fin", raw))
    if foil_patch:
        patch = {**foil_patch, "family": FoilFamily(foil_patch["family"])}
        fin = dataclasses.replace(fin, foil=dataclasses.replace(fin.foil, **patch))
    return fin


def _rows(path: Path, variant: str) -> dict:
    return {r["alpha"]: r for r in json.loads(path.read_text())["variants"][variant]["rows"]}


def cases() -> list:
    cam3 = {"family": "cambered", "camber_ratio": 0.03, "camber_position": 0.4}
    return [
        ("3 % camber on the shipped gen-2 planform (t/c 0.092 at the root, 0.072 at the tip)",
         _fin(BENCH / "foil-family/fins/side-shipped-gen2.json", cam3),
         _rows(BENCH / "foil-family/results.json", "cambered-3pct"),
         _rows(BENCH / "cambered-candidate/mesh-level-3/results.json", "cambered-3pct-L3")),
        ("the cambered candidate: 4.3 % camber, t/c 0.074 at the root, 0.083 at the tip",
         _fin(BENCH / "cambered-candidate/fins/side-cambered-candidate.json"),
         _rows(BENCH / "cambered-candidate/results.json", "cambered-candidate"), {}),
    ]


def main() -> None:
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:]
               if a.startswith("--") and "=" in a)
    nodes = load_nodes()
    lines = ["# Lattice with RANS section data against isolated-fin CFD", "",
             "Section nodes used: " + ", ".join(sorted(n["name"] for n in nodes.values()))
             + f" ({4 - len(nodes)} filled from the others)."]
    toe = SIDE_TOE_DEFAULT_DEG
    for title, fin, level2, level3 in cases():
        qa = 0.5 * RHO_SEAWATER * SPEED**2 * metrics(fin.outline).area * 1e-6
        lines += ["", f"### {title} — {metrics(fin.outline).area:.0f} mm², {SPEED:g} m/s", "",
                  "| own incidence ° | CL: CFD / table / RANS-fed | drag N: CFD level 2 | "
                  "CFD level 3 | lattice, table v0 | lattice, RANS sections | "
                  "share of the level-2 gap closed |",
                  "|---|---|---|---|---|---|---|"]
        drag = {}
        for a in sorted(x for x in level2 if x <= 4.0):
            v0, v1 = solve(fin, a, None), solve(fin, a, nodes)
            cfd = level2[a]["cd"] * qa
            drag[a] = (cfd, v0.cd * qa, v1.cd * qa)
            gap = cfd - v0.cd * qa
            closed = (v1.cd - v0.cd) * qa / gap if gap > 0.0 else float("nan")
            l3 = f"{level3[a]['cd'] * qa:.1f}" if a in level3 else "–"
            lines.append(f"| {a:+.1f} | {level2[a]['cl']:+.3f} / {v0.cl:+.3f} / {v1.cl:+.3f} | "
                         f"{cfd:.1f} | {l3} | {v0.cd * qa:.1f} | {v1.cd * qa:.1f} | "
                         f"{closed * 100:.0f} % |")
        lo, hi = -bladehydro.TRIM_LEEWAY_DEG - toe, bladehydro.TRIM_LEEWAY_DEG - toe
        if lo in drag and hi in drag:
            trim = [0.5 * (drag[lo][k] + drag[hi][k]) for k in range(3)]
            lines += ["", f"Going straight at the {toe:g}° toe (mean of {lo:+g}° and {hi:+g}°): "
                          f"{trim[0]:.1f} N level-2 CFD, {trim[1]:.1f} N table v0, "
                          f"{trim[2]:.1f} N RANS sections."]
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
