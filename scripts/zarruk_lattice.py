"""The measured hydrofoil of [Zar14] on the viscous lattice: a second measured 3-D polar
for the strip model, beside the tunnel fin [BW04].

    uv run python scripts/zarruk_lattice.py [--table=v1] [--md=bench/zarruk/lattice.md]

The foil: an unswept trapezoid of NACA 0009 sections, span 300 mm from the tunnel
ceiling, chord 120 mm at the root and 60 mm at the tip (bench/zarruk/geometry.md).
Type I has the standard trailing edge (0.2 % of chord), Type II a thick one (1.3 %,
close to the section table's 1 %). Measured lift polars at four Reynolds numbers on
the mean chord are in bench/zarruk/measured/ (digitized, stainless-steel models: the
stiff ones). The foil is smooth and untripped; the paper sees laminar-flow effects up
to Re 0.6e6 and none from 0.8e6.

The lattice has a perfect mirror at the root (the ceiling) and no other wall: the
tunnel is 0.6 m square, the tip 0.3 m from its floor, and the data carry no
correction for that. Each strip reads the symmetric section of t/c 0.09 at its own
Reynolds number.

What is asked of the comparison:
  * the lift slope, at an aspect ratio twice a fin's;
  * where the measured foil stalls, what its most loaded strip is doing: its lift as
    a share of the lift the table's section has at its break (the quantity
    bladehydro.KNEE_FRACTION is a share of), its incidence, and how far that is from
    the end of the section's attached range.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from fingen import lattice, sections
from fingen.params import FoilFamily

MEASURED = Path(__file__).resolve().parent.parent / "bench/zarruk/measured"
NU = 1.14e-6                        # water at 15 °C; only the strips' Reynolds numbers use it
SPAN_MM, ROOT_MM, TIP_MM, MEAN_M = 300.0, 120.0, 60.0, 0.09
SLOPE_DEG = (4.0, 8.0)             # where the digitized rows are clean and the foil on its line
RUNS = (("II", "0.4e6"), ("II", "0.6e6"), ("II", "0.8e6"), ("II", "1.0e6"),
        ("I", "0.4e6"), ("I", "0.6e6"), ("I", "0.8e6"), ("I", "1.0e6"))


def blade() -> lattice.Blade:
    z = np.linspace(0.0, SPAN_MM, 61)
    chord = ROOT_MM + (TIP_MM - ROOT_MM) * z / SPAN_MM
    # unswept about the mid-chord line (the paper's moment reference)
    return lattice.blade_from_planform("blade", z, 0.5 * (ROOT_MM - chord), chord, nz=16, nx=3,
                                       x_ref_mm=0.5 * ROOT_MM)


def measured(kind: str, re_label: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(angle, lift, whether the digitized marker was clean or deblended: quality A or B;
    C is a fragment or a merged cluster, ±0.015 in lift, and most low-angle rows are C)."""
    rows = []
    for line in (MEASURED / f"forces_Type{kind}-SS_Re_{re_label}.csv").read_text().splitlines():
        cells = line.split(",")
        try:
            rows.append((float(cells[0]), float(cells[1]), cells[2].strip() in ("A", "B")))
        except (ValueError, IndexError):
            continue                 # comment, header, or a marker hidden in the figure
    a, cl, good = np.array(sorted(rows)).T
    return a, cl, good.astype(bool)


def slope_per_deg(a: np.ndarray, cl: np.ndarray, use: np.ndarray | None = None) -> float:
    """Slope of the line through the origin over SLOPE_DEG (nan with fewer than three rows)."""
    m = (a >= SLOPE_DEG[0]) & (a <= SLOPE_DEG[1]) & (True if use is None else use)
    return float(np.sum(a[m] * cl[m]) / np.sum(a[m] ** 2)) if m.sum() >= 3 else float("nan")


def stall(a: np.ndarray, cl: np.ndarray) -> tuple[float, float] | None:
    """(angle, lift) of the highest measured lift, if the polar goes on past it."""
    k = int(np.argmax(cl))
    return (float(a[k]), float(cl[k])) if k < len(a) - 1 else None


def main() -> None:
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    table = opt.get("table", "v1")
    b = blade()
    lines = [f"# The hydrofoil of [Zar14] on the viscous lattice (section table {table})", "",
             "Written by `scripts/zarruk_lattice.py`. Perfect mirror at the root, no other wall. "
             "Slopes are of the line through the origin over 4…8° (measured: clean markers only; "
             "the paper gives 4.82 per rad for Type I at Re 1.0e6). The most loaded strip is the "
             "one nearest its section's lift at break; \"margin\" is from its incidence to the end "
             "of its section's attached range.", "",
             "| foil | Re on the mean chord | lift slope per rad: measured / lattice | "
             "measured stall: ° , C_L | lattice C_L there | most loaded strip: z / span | "
             "its lift | share of its section's lift at break | its incidence ° | margin ° | "
             "lattice's own polar: 5 % below its line at ° |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for kind, re_label in RUNS:
        re_c = float(re_label)
        speed = re_c * NU / MEAN_M
        pol = [sections.polar(FoilFamily.SYMMETRIC, 0.09, re_c * c / MEAN_M, 0.0, table)
               for c in b.chord]
        am, clm, good = measured(kind, re_label)
        angles = np.arange(2.0, 16.01, 0.5)
        own = np.array([lattice.solve_viscous([b], {"blade": pol}, speed, a).loads["blade"].cl
                        for a in angles])
        k_lat = slope_per_deg(angles, own)
        below = own < 0.95 * k_lat * angles
        knee = f"{angles[np.argmax(below)]:.1f}" if below.any() else "beyond 16"
        k_meas = slope_per_deg(am, clm, good)
        cells = [f"Type {kind}", re_label,
                 ("–" if np.isnan(k_meas) else f"{np.degrees(k_meas):.2f}")
                 + f" / {np.degrees(k_lat):.2f}"]
        st = stall(am, clm)
        if st is None:
            cells += [f"not reached (to {am[-1]:.1f}°, {clm[-1]:.3f})"] + ["–"] * 6
        else:
            sol = lattice.solve_viscous([b], {"blade": pol}, speed, st[0])
            ld = sol.loads["blade"]
            brk = np.array([float(p.cl_at(p.alpha_break_deg)) for p in pol])
            k = int(np.argmax(ld.cl_local / brk))
            end = pol[k].attached_deg[1] if pol[k].attached_deg else pol[k].alpha_break_deg
            cells += [f"{st[0]:.1f}, {st[1]:.3f}",
                      f"{ld.cl:.3f}{'' if sol.converged else ' (not converged)'}",
                      f"{b.z_mid[k] / (SPAN_MM * 1e-3):.2f}", f"{ld.cl_local[k]:.2f}",
                      f"{ld.cl_local[k] / brk[k]:.2f}", f"{ld.alpha_eff_deg[k]:.1f}",
                      f"{end - ld.alpha_eff_deg[k]:+.1f}"]
        lines.append("| " + " | ".join(cells + [knee]) + " |")
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
