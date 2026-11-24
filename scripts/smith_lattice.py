"""The NACA 0012 blades of [Smi21] on the viscous lattice: two more measured breaks.

    uv run python scripts/smith_lattice.py [--table=v1] [--md=bench/smith2021/lattice.md]

The blades: unswept trapezoids, root chord 120 mm, tip 80 mm, span 240 mm and 120 mm (a fin's
size), hung from the ceiling of the tunnel of [BW04] and [Zar14]. Measured normal and axial force
in half-degree steps up through stall and back, read out of the paper's vector figures
(bench/smith2021/measured/, `extract_curves.py`); lift is derived from the two. Used here: the
runs with the least of the ceiling's boundary layer on the blade (8 % of the long blade's span,
16 % of the short one's).

The lattice has a perfect mirror at the root and a uniform stream: no ceiling boundary layer, no
tunnel walls (0.6 m square). The blades are smooth; the paper reads the bump in their lift slope
between 5 and 9 deg and the sudden stall as a laminar separation bubble, which the section table
(fully turbulent) does not have. Each strip reads the symmetric section of t/c 0.12 at its own
Reynolds number.

Asked, as of the hydrofoil of [Zar14] (`zarruk_lattice.py`): the lift slope; what the most loaded
strip is doing where the measured blade stalls; where the strip criterion puts the knee and where
the measured polar stands against its own line there.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

from fingen import bladehydro, lattice, sections
from fingen.params import FoilFamily

MEASURED = Path(__file__).resolve().parent.parent / "bench/smith2021/measured"
NU = 1.14e-6  # water at 15 °C; only the strips' Reynolds numbers use it
ROOT_MM, TIP_MM, MEAN_M, TC = 120.0, 80.0, 0.10, 0.12
RUNS = (
    ("long", 240.0, "long-b240-db0.08-Re0.4e6", 0.4e6),
    ("long", 240.0, "long-b240-db0.08-Re0.6e6", 0.6e6),
    ("long", 240.0, "long-b240-db0.08-Re0.8e6", 0.8e6),
    ("long", 240.0, "long-b240-db0.08-Re1.0e6", 1.0e6),
    ("short", 120.0, "short-b120-Re1.0e6-db0.16", 1.0e6),
)


def blade(span_mm: float) -> lattice.Blade:
    z = np.linspace(0.0, span_mm, 61)
    chord = ROOT_MM + (TIP_MM - ROOT_MM) * z / span_mm
    return lattice.blade_from_planform(
        "blade", z, 0.5 * (ROOT_MM - chord), chord, nz=16, nx=3, x_ref_mm=0.5 * ROOT_MM
    )


def measured(name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(angle, lift, normal force) on the way up."""
    rows = [
        r
        for r in csv.DictReader(
            line for line in (MEASURED / f"{name}.csv").open() if not line.startswith("#")
        )
        if r["sweep"] == "up"
    ]
    a = np.array([float(r["alpha_deg"]) for r in rows])
    return a, np.array([float(r["CL"]) for r in rows]), np.array([float(r["CN"]) for r in rows])


def five_below(a: np.ndarray, cl: np.ndarray) -> float:
    """Where the lift is 5 % below the line through its rows at 0 and 4 deg (nan if nowhere)."""
    k = (np.interp(4.0, a, cl) - np.interp(0.0, a, cl)) / 4.0
    d = cl / (np.interp(0.0, a, cl) + k * a) - 1.0
    for i in np.flatnonzero((a[:-1] >= 5.0) & (d[:-1] > -0.05) & (d[1:] <= -0.05)):
        return float(a[i] + (a[i + 1] - a[i]) * (-0.05 - d[i]) / (d[i + 1] - d[i]))
    return float("nan")


def against(a: np.ndarray, cl: np.ndarray, at: float) -> str:
    """The lift at `at` degrees against the line through the rows at 0 and 4 deg, in percent."""
    k = (np.interp(4.0, a, cl) - np.interp(0.0, a, cl)) / 4.0
    return f"{100.0 * (np.interp(at, a, cl) / (np.interp(0.0, a, cl) + k * at) - 1.0):+.0f} %"


def main() -> None:
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    table = opt.get("table", "v1")
    lines = [
        f"# The NACA 0012 blades of [Smi21] on the viscous lattice (section table {table})",
        "",
        "Written by `scripts/smith_lattice.py`. Perfect mirror at the root, uniform stream: the "
        "ceiling's boundary layer (8 % of the long blade's span, 16 % of the short one's) and "
        'the tunnel\'s walls are not in it. Slopes are of the lift over 0…4°. "5 % below" is '
        "against the line through the rows at 0° and 4°, as in `bench/knee/one-degree/`. The "
        "stall is the last row before the normal force falls by more than 0.05 in half a "
        "degree. The most loaded strip is the one nearest the most lift its section carries "
        'attached; "margin" is from its incidence to the end of its section\'s attached '
        f"range. The strip criterion is `bladehydro.knee`'s rule at its share of "
        f"{bladehydro.KNEE_FRACTION:g}.",
        "",
        "| blade | Re on the mean chord | lift slope per degree: measured / lattice | "
        "measured: 5 % below at ° | measured stall after °, C_L there | lattice C_L there | "
        "most loaded strip: z / span | its lift | share of its section's limit | "
        "its incidence ° | margin ° | lattice's own polar: 5 % below at ° | "
        "strip criterion ° | measured against its line there | two degrees on |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for kind, span_mm, name, re_c in RUNS:
        b = blade(span_mm)
        speed = re_c * NU / MEAN_M
        pol = [
            sections.polar(FoilFamily.SYMMETRIC, TC, re_c * c / MEAN_M, 0.0, table) for c in b.chord
        ]
        am, clm, cnm = measured(name)
        k_meas = (np.interp(4.0, am, clm) - np.interp(0.0, am, clm)) / 4.0
        angles = np.arange(0.0, 26.01, 0.5)
        own = np.array(
            [lattice.solve_viscous([b], {"blade": pol}, speed, a).loads["blade"].cl for a in angles]
        )
        k_lat = (np.interp(4.0, angles, own) - own[0]) / 4.0
        own5 = five_below(angles, own)
        drop = np.flatnonzero(cnm[:-1] - cnm[1:] > 0.05)
        a_st = float(am[drop[0]])
        sol = lattice.solve_viscous([b], {"blade": pol}, speed, a_st)
        ld = sol.loads["blade"]
        limit = np.array([p.cl_limit for p in pol])
        k = int(np.argmax(ld.cl_local / limit))
        end = pol[k].attached_deg[1] if pol[k].attached_deg else pol[k].alpha_break_deg
        lo, hi = (
            lattice.solve_viscous([b], {"blade": pol}, speed, a).loads["blade"] for a in (2.0, 6.0)
        )
        crit = float(
            (
                2.0
                + (bladehydro.KNEE_FRACTION * limit - lo.cl_local)
                / ((hi.cl_local - lo.cl_local) / 4.0)
            ).min()
        )

        lines.append(
            "| "
            + " | ".join(
                [
                    f"{kind}, span {span_mm:.0f} mm",
                    f"{re_c / 1e6:.1f}e6",
                    f"{k_meas:.4f} / {k_lat:.4f}",
                    f"{five_below(am, clm):.1f}",
                    f"{a_st:.1f}, {np.interp(a_st, am, clm):.3f}",
                    f"{ld.cl:.3f}{'' if sol.converged else ' (not converged)'}",
                    f"{b.z_mid[k] / (span_mm * 1e-3):.2f}",
                    f"{ld.cl_local[k]:.2f}",
                    f"{ld.cl_local[k] / limit[k]:.2f}",
                    f"{ld.alpha_eff_deg[k]:.1f}",
                    f"{end - ld.alpha_eff_deg[k]:+.1f}",
                    "beyond 26" if np.isnan(own5) else f"{own5:.1f}",
                    f"{crit:.1f}",
                    against(am, clm, crit),
                    against(am, clm, crit + 2.0),
                ]
            )
            + " |"
        )
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
