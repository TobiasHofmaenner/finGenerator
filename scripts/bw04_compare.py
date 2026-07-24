"""Quantitative comparison: our polar vs Brandner & Walker's measurements.

Reference data provenance (paper fetched 2026-07-24, Wayback):
- Linear range: constructed from the paper's STATED slope (0.05/deg) and
  zero-lift incidence (-3.5 deg, Re-invariant) — more precise than reading
  the figure.
- Knee/high-alpha CL and all CD: digitized by eye from Figure 2 (Re >= 4e5
  curves, which collapse); uncertainty ~+/-0.03 CL, +/-0.02 CD.

Usage: uv run python scripts/bw04_compare.py <polar.json> <out.png>
"""

from __future__ import annotations

import json
import sys

import numpy as np

MEAS_SLOPE_PER_DEG = 0.05
MEAS_ALPHA_ZL = -3.5
# Digitized Figure 2 (alpha, CL) beyond the linear range and (alpha, CD):
MEAS_CL_HIGH = [(12, 0.775), (14, 0.82), (16, 0.89), (18, 0.96),
                (20, 1.02), (22, 1.07), (24, 1.10)]
MEAS_CD = [(0, 0.030), (4, 0.035), (8, 0.055), (12, 0.09),
           (16, 0.16), (20, 0.25), (24, 0.38)]


def main() -> None:
    with open(sys.argv[1]) as fh:
        rows = json.load(fh)
    a = np.array([r["alpha"] for r in rows])
    cl = np.array([r["cl"] for r in rows])
    cd = np.array([r["cd"] for r in rows])

    lin = a <= 8.0
    slope_deg = float(np.polyfit(a[lin], cl[lin], 1)[0])
    alpha_zl = float(-np.polyfit(a[lin], cl[lin], 1)[1] / slope_deg)
    meas_lin = MEAS_SLOPE_PER_DEG * (a[lin] - MEAS_ALPHA_ZL)
    mean_dcl = float(np.mean(np.abs(cl[lin] - meas_lin)))
    cd0 = float(cd[0])

    print(f"slope: {slope_deg:.4f}/° vs measured 0.0500/° "
          f"({(slope_deg / MEAS_SLOPE_PER_DEG - 1) * 100:+.1f}%)")
    print(f"zero-lift: {alpha_zl:+.2f}° vs measured -3.5°  "
          f"(Δ {abs(alpha_zl - MEAS_ALPHA_ZL):.2f}°)")
    print(f"mean |ΔCL| over linear range: {mean_dcl:.3f}")
    print(f"CD(0): {cd0:.4f} vs measured ≈0.030 (±0.02 digitizing)")
    gates = {
        "slope_15pct": abs(slope_deg / MEAS_SLOPE_PER_DEG - 1) < 0.15,
        "alpha_zl_1deg": abs(alpha_zl - MEAS_ALPHA_ZL) < 1.0,
        "mean_dcl_005": mean_dcl < 0.05,
        "cd0_band": abs(cd0 - 0.030) < 0.02,
    }
    print("GATES: " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}"
                                for k, v in gates.items()))

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    BG, TXT, MUT, ACC, DNG = "#0a0a0a", "#e8e8e8", "#8f8f8f", "#a7e0ea", "#f0a9a9"
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6), facecolor=BG)
    for ax in (ax1, ax2):
        ax.set_facecolor(BG)
        for sp in ax.spines.values():
            sp.set_color((1, 1, 1, 0.14))
        ax.tick_params(colors=MUT, labelsize=8)
        ax.grid(color=(1, 1, 1, 0.08), lw=0.7)
    th = np.linspace(-4, 12, 10)
    ax1.plot(th, MEAS_SLOPE_PER_DEG * (th - MEAS_ALPHA_ZL), "--", color=MUT,
             lw=1.2, label="measured slope & α₀ [BW04]")
    mh = np.array(MEAS_CL_HIGH)
    ax1.errorbar(mh[:, 0], mh[:, 1], yerr=0.03, fmt="s", color=TXT, ms=4,
                 lw=0, elinewidth=1, capsize=2, label="digitized Fig. 2")
    ax1.plot(a, cl, "o-", color=ACC, lw=2, ms=4, label="our CFD bench")
    ax1.set_xlabel("α [°]", color=MUT)
    ax1.set_ylabel("CL", color=MUT)
    ax1.set_title("lift: CFD vs measurement", color=TXT, fontsize=10)
    ax1.legend(facecolor=BG, edgecolor=(1, 1, 1, 0.14), labelcolor=TXT,
                     fontsize=8)
    md = np.array(MEAS_CD)
    ax2.errorbar(md[:, 0], md[:, 1], yerr=0.02, fmt="s", color=TXT, ms=4,
                 lw=0, elinewidth=1, capsize=2, label="digitized Fig. 2")
    ax2.plot(a, cd, "o-", color=DNG, lw=2, ms=4, label="our CFD bench")
    ax2.set_xlabel("α [°]", color=MUT)
    ax2.set_ylabel("CD", color=MUT)
    ax2.set_title("drag: CFD vs measurement", color=TXT, fontsize=10)
    ax2.legend(facecolor=BG, edgecolor=(1, 1, 1, 0.14), labelcolor=TXT,
               fontsize=8)
    fig.tight_layout()
    fig.savefig(sys.argv[2], dpi=120, facecolor=BG)
    print(f"plot: {sys.argv[2]}")


if __name__ == "__main__":
    main()
