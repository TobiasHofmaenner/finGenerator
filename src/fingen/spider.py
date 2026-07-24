"""The spiderweb: six surfer-language axes summarizing a fin's tradeoffs.

This is the optimizer's future target and the user's mental model. Each axis
is a normalized 0–100 score derived from hidden physics metrics; today they
are backed by the tier-0 analytic model plus two labeled geometry proxies,
and the CFD polar card replaces the backing numbers later WITHOUT changing
the axes (docs/PHYSICS.md §6, the metrics discussion).

Axes and their hidden metrics (at the 7 m/s reference point):
  speed        1 / total drag at trim (friction+form CD0 [Hoe75] + induced)
  drive        L/D at working lift (CL = 0.4)
  hold         maximum side force: slope · α_break [BW04] · q · area
  pivot        1 / yaw stiffness (slope · area · CP arm from the base center)
  release      PROXY: sweep + tip-unloading (elliptic deviation) — replaced
               by the post-peak lift gradient once URANS points exist
  forgiveness  degrees of margin from the working angle to the [BW04] break

Scores are normalized against the reference fleet (template presets swept
through the same formulas), so 50 means "mid-fleet", not an absolute grade.
"""

from __future__ import annotations

import math
from pathlib import Path

from fingen.hydro import RHO_SEAWATER, estimate, lift_curve_slope, stall_alpha_deg
from fingen.outline import metrics, planform
from fingen.params import FinParams, FoilFamily, FoilParams, OutlineParams

AXES = ("speed", "drive", "hold", "pivot", "release", "forgiveness")
REF_SPEED = 7.0
# The working point is a fixed side FORCE, not a fixed CL: a surfer loads the
# fin with the turn's force budget [Knies25], and a big keel delivers it at
# tiny CL (efficiently) while a small blade must work near its break.
WORK_FORCE_N = 120.0
# Normalization is by interpolated rank within the reference fleet — robust
# to outlier templates (a longboard single otherwise crushes every shortboard
# fin to ~0 on the extensive axes).


def _cd0(fin: FinParams, speed: float) -> float:
    """Profile drag: turbulent flat-plate friction with a thickness form
    factor [Hoe75], both sides of the fin."""
    est = estimate(fin, speed, 0.0)
    cf = 0.074 / est.reynolds**0.2
    t = fin.foil.thickness_ratio
    form = 1.0 + 2.0 * t + 60.0 * t**4
    return 2.0 * cf * form


def raw_scores(fin: FinParams, speed: float = REF_SPEED) -> dict[str, float]:
    """Unnormalized physical values per axis (bigger = more of the quality)."""
    m = metrics(fin.outline)
    area_m2 = m.area * 1e-6
    q = 0.5 * RHO_SEAWATER * speed**2
    slope, ar_eff = lift_curve_slope(fin)
    cd0 = _cd0(fin, speed)

    # speed: inverse total drag at trim (α = 1°) in N
    est_trim = estimate(fin, speed, 1.0)
    drag_trim = q * area_m2 * (cd0 + est_trim.cdi)
    # hold: max side force in N (linear to the AR-dependent break)
    a_break = stall_alpha_deg(ar_eff)
    f_max = q * area_m2 * slope * math.radians(a_break)
    # drive: L/D delivering the reference force (capped near the break for
    # fins too small to deliver it at all)
    cl_work = min(WORK_FORCE_N / (q * area_m2),
                  0.95 * slope * math.radians(a_break))
    cdi_work = cl_work**2 / (math.pi * 0.9 * ar_eff)
    ld_work = cl_work / (cd0 + cdi_work)
    # pivot: inverse yaw stiffness — CP arm measured from the base center
    z, x_le, chord = planform(fin.outline)
    import numpy as np

    x_cp = float(np.trapezoid((x_le + 0.25 * chord) * chord, z)
                 / max(np.trapezoid(chord, z), 1e-9))
    arm_m = abs(x_cp - fin.outline.base / 2.0) * 1e-3 + 0.25 * (m.area / fin.outline.depth) * 1e-3
    yaw_stiffness = q * area_m2 * slope * arm_m
    # release (PROXY): raked, tip-unloaded planforms shed load gradually
    release = 0.6 * (m.sweep / 50.0) + 0.4 * min(m.elliptic_deviation / 0.30, 1.0)
    # forgiveness: margin from the working angle to the break
    alpha_work = math.degrees(cl_work / slope)
    margin = a_break - alpha_work

    return {
        "speed": 1.0 / max(drag_trim, 1e-9),
        "drive": ld_work,
        "hold": f_max,
        "pivot": 1.0 / max(yaw_stiffness, 1e-9),
        "release": release,
        "forgiveness": margin,
    }


def reference_fleet() -> dict[str, FinParams]:
    """Template presets spanning the design space — the normalization basis."""
    flat = FoilParams(family=FoilFamily.FLAT_INSIDE)
    return {
        "thruster-side": FinParams(foil=flat),
        "quad-rear": FinParams(outline=OutlineParams(depth=100, base=95, sweep=36,
                                                     tip_width_ratio=0.38), foil=flat),
        "fish-keel": FinParams(outline=OutlineParams(depth=95, base=180, sweep=14,
                                                     tip_width_ratio=0.55,
                                                     le_fullness=0.9, te_shape=0.8),
                               foil=FoilParams(family=FoilFamily.FLAT_INSIDE,
                                               thickness_ratio=0.10)),
        "hi-aspect": FinParams(outline=OutlineParams(depth=130, base=90, sweep=25,
                                                     tip_width_ratio=0.3,
                                                     le_fullness=0.5,
                                                     te_shape=-0.15),
                               foil=FoilParams(family=FoilFamily.FLAT_INSIDE,
                                               thickness_ratio=0.075)),
        "gun-rake": FinParams(outline=OutlineParams(depth=128, base=112, sweep=50,
                                                    tip_width_ratio=0.2,
                                                    le_fullness=0.65,
                                                    te_shape=-0.4),
                              foil=FoilParams(family=FoilFamily.FLAT_INSIDE,
                                              thickness_ratio=0.08)),
        "longboard-single": FinParams(outline=OutlineParams(depth=240, base=160,
                                                            sweep=45,
                                                            tip_width_ratio=0.28,
                                                            le_fullness=0.7,
                                                            te_shape=-0.4),
                                      foil=FoilParams(family=FoilFamily.SYMMETRIC,
                                                      thickness_ratio=0.08)),
    }


def normalized_scores(fin: FinParams, speed: float = REF_SPEED) -> dict[str, float]:
    """0–100 per axis, min–max scaled against the reference fleet (clipped;
    a genuinely out-of-fleet fin can pin at 0 or 100)."""
    fleet = [raw_scores(f, speed) for f in reference_fleet().values()]
    raw = raw_scores(fin, speed)
    import numpy as np

    out = {}
    for axis in AXES:
        values = np.sort([f[axis] for f in fleet])
        ranks = np.linspace(0.0, 100.0, len(values))
        out[axis] = float(np.interp(raw[axis], values, ranks))
    return out


def spider_chart(fins: dict[str, FinParams], out_png: str | Path,
                 speed: float = REF_SPEED) -> Path:
    """Dark-styled radar chart for one or more fins (T-FINS palette)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    bg, text, muted = "#0a0a0a", "#e8e8e8", "#8f8f8f"
    colors = ["#a7e0ea", "#f0a9a9", "#d8c48a", "#9fd8a7"]
    line2 = (1.0, 1.0, 1.0, 0.14)

    angles = np.linspace(0, 2 * np.pi, len(AXES), endpoint=False)
    fig, ax = plt.subplots(figsize=(6.4, 6.4), facecolor=bg,
                           subplot_kw={"projection": "polar"})
    ax.set_facecolor(bg)
    for i, (name, fin) in enumerate(fins.items()):
        scores = normalized_scores(fin, speed)
        values = [scores[a] for a in AXES]
        vals = np.concatenate((values, [values[0]]))
        angs = np.concatenate((angles, [angles[0]]))
        color = colors[i % len(colors)]
        ax.plot(angs, vals, color=color, lw=2, label=name)
        ax.fill(angs, vals, color=color, alpha=0.10)
    ax.set_xticks(angles)
    ax.set_xticklabels([a.upper() for a in AXES], color=text, fontsize=10,
                       family="monospace")
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75])
    ax.set_yticklabels(["25", "50", "75"], color=muted, fontsize=7)
    ax.grid(color=line2, linewidth=0.8)
    ax.spines["polar"].set_color(line2)
    legend = ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.12),
                       facecolor=bg, edgecolor=line2, labelcolor=text,
                       fontsize=9)
    legend.get_frame().set_linewidth(0.8)
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120, facecolor=bg, bbox_inches="tight")
    plt.close(fig)
    return out_png
