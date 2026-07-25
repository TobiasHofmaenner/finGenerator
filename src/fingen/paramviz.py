"""Parameter explainer SVGs for the web UI: white-on-black pictograms, one per
slider, drawn from the real fingen geometry (planform()/section_points()) so
they always depict the actual shape family.

Usage: uv run python -m fingen.paramviz <outdir> [--png]
(--png adds PNG twins for quick visual review; the site uses the SVGs.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from fingen.foil import section_points
from fingen.params import FoilFamily, FoilParams, OutlineParams

_BG = "#000000"
_MAIN = "#ffffff"
_DIM = "#9a9a9a"
_FAINT = "#565656"
_LW = 2.0


def _fig():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(3.2, 3.2), facecolor=_BG)
    ax.set_facecolor(_BG)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def _outline_xy(**kw):
    from fingen.outline import planform

    z, x_le, chord = planform(OutlineParams(**kw))
    live = chord > 0.3
    x = np.concatenate((x_le[live], (x_le + chord)[live][::-1]))
    y = np.concatenate((z[live], z[live][::-1]))
    return x, y


def _draw_outline(ax, color=_MAIN, lw=_LW, ls="-", **kw):
    x, y = _outline_xy(**kw)
    ax.plot(x, y, color=color, lw=lw, ls=ls)


def _arrow(ax, p0, p1, label, color=_MAIN, offset=(0, 0)):
    ax.annotate("", xy=p1, xytext=p0, annotation_clip=False,
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.6))
    mid = ((p0[0] + p1[0]) / 2 + offset[0], (p0[1] + p1[1]) / 2 + offset[1])
    ax.text(*mid, label, color=color, fontsize=11, ha="center", va="center",
            family="monospace")


def _save(fig, outdir: Path, name: str, png: bool):
    fig.savefig(outdir / f"{name}.svg", facecolor=_BG, bbox_inches="tight",
                pad_inches=0.08)
    if png:
        fig.savefig(outdir / f"{name}.png", facecolor=_BG, bbox_inches="tight",
                    pad_inches=0.08, dpi=110)
    import matplotlib.pyplot as plt

    plt.close(fig)


_YX = 2.2  # vertical exaggeration for section pictograms (legibility)


def _section_xy(foil: FoilParams, chord=100.0):
    upper, lower = section_points(foil, chord, n_points=120)
    x = np.concatenate((upper[:, 0], lower[::-1, 0]))
    y = np.concatenate((upper[:, 1], lower[::-1, 1])) * _YX
    return x, y


PARAM_HELP = {
    "depth": "Span from board to tip. More depth = more hold and leverage.",
    "base": "Chord length at the board. More base = more drive and stiffness.",
    "sweep": "Rake: how far the tip trails the base. More sweep = drawn-out turns, more hold.",
    "tip_width": "Width of the rounded tip lobe. Wider = more tip area and hold, sturdier print.",
    "le_fullness": "How far the leading edge bows forward, carrying area low on the fin.",
    "te_shape": "Trailing edge: \u22121 concave cutaway (release) \u2026 +1 convex keel (drive).",
    "thickness": "Section thickness over chord. Thicker = stiffer, gentler stall, more drag.",
    "camber": "Section curvature: pre-aims lift toward the turn (side fins).",
    "camber_pos": "Chordwise position of maximum camber.",
    "tip_factor": "Tip thickness relative to base. Below 1 thins the tip, softening tip stall.",
    "foil_family": "Symmetric 50/50 for center fins, flat inside for sides, cambered between.",
    "tabs": "Mounting: dual (FCS-compatible), single (Futures), click (FCS II), or none.",
    "tab_fit": "Print-fit tweak of tab thickness. Print a test coupon, adjust in 0.1 mm steps.",
    "tab_x": "Slide the tab set fore/aft. Tabs may overhang the base ends "
             "(commercial click fins do); each keeps ≥ half its length engaged.",
    "tab_y": "Shift tabs across the fin thickness. Flat fins anchor the tabs "
             "flush with the flat side, so fin and tabs print flat on the bed.",
    "grooves": "Thinning grooves on the upper fin: +11% lift-to-drag at hard "
               "turn angles, softer tip flex (Wollongong studies). 0 = smooth fin.",
    "groove_length": "How far each groove runs back from the leading edge.",
    "groove_pitch": "Spanwise spacing between groove centers.",
    "groove_width": "Width of each groove channel (≤ pitch).",
    "groove_depth": "Fraction of local thickness removed at a groove center. "
                    "Deeper = more effect, softer fin.",
    "groove_start": "Where the groove band begins, as a fraction of depth.",
    "groove_surface": "Outer face only (G1, prints flat) or both faces (G2).",
}


def generate_all(outdir: str | Path, png: bool = False) -> list[Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "params-help.json").write_text(
        json.dumps(PARAM_HELP, indent=2, ensure_ascii=False) + "\n")
    default = OutlineParams()

    # depth: vertical extent
    fig, ax = _fig()
    _draw_outline(ax)
    ax.set_xlim(-52, default.base * 1.1)
    _arrow(ax, (-24, 0), (-24, default.depth), "")
    ax.text(-34, default.depth / 2, "depth", color=_MAIN, fontsize=11,
            ha="center", va="center", family="monospace", rotation=90)
    _save(fig, outdir, "depth", png)

    # base: chord at the board
    fig, ax = _fig()
    _draw_outline(ax)
    ax.set_ylim(-34, default.depth * 1.08)
    _arrow(ax, (0, -14), (default.base, -14), "")
    ax.text(default.base / 2, -27, "base", color=_MAIN, fontsize=11,
            ha="center", family="monospace")
    _save(fig, outdir, "base", png)

    # sweep: rake angle to the tip
    fig, ax = _fig()
    _draw_outline(ax, color=_DIM, lw=1.4)
    x_tip = default.depth * np.tan(np.radians(default.sweep))
    ax.plot([0, 0], [0, default.depth], color=_FAINT, lw=1.2, ls="--")
    ax.plot([0, x_tip], [0, default.depth], color=_MAIN, lw=1.6)
    theta = np.linspace(np.pi / 2, np.pi / 2 - np.radians(default.sweep), 40)
    ax.plot(45 * np.cos(theta), 45 * np.sin(theta), color=_MAIN, lw=1.2)
    ax.text(22, 52, "sweep", color=_MAIN, fontsize=11, family="monospace")
    _save(fig, outdir, "sweep", png)

    # tip width: lobe width comparison
    fig, ax = _fig()
    _draw_outline(ax, color=_FAINT, lw=1.4, ls="--", tip_width_ratio=0.12)
    _draw_outline(ax, tip_width_ratio=0.5)
    ax.text(default.base * 0.72, default.depth * 1.06, "tip width",
            color=_MAIN, fontsize=11, family="monospace", ha="center")
    _save(fig, outdir, "tip_width", png)

    # le fullness
    fig, ax = _fig()
    _draw_outline(ax, color=_FAINT, lw=1.4, ls="--", le_fullness=0.05)
    _draw_outline(ax, le_fullness=0.95)
    ax.text(6, default.depth * 0.55, "LE\nfullness", color=_MAIN, fontsize=11,
            family="monospace", ha="center")
    _save(fig, outdir, "le_fullness", png)

    # te shape: concave / straight / convex
    fig, ax = _fig()
    _draw_outline(ax, color=_FAINT, lw=1.2, ls="--", te_shape=0.9)
    _draw_outline(ax, color=_DIM, lw=1.2, te_shape=0.0)
    _draw_outline(ax, te_shape=-0.9)
    ax.text(default.base * 1.02, default.depth * 0.45, "TE shape\n-1 … +1",
            color=_MAIN, fontsize=10, family="monospace")
    _save(fig, outdir, "te_shape", png)

    # thickness (t/c)
    fig, ax = _fig()
    foil = FoilParams(family=FoilFamily.SYMMETRIC, thickness_ratio=0.12)
    x, y = _section_xy(foil)
    ax.plot(x, y, color=_MAIN, lw=_LW)
    ax.fill(x, y, color=_MAIN, alpha=0.08)
    _arrow(ax, (30, -6.2 * _YX), (30, 6.2 * _YX), "", color=_MAIN)
    ax.text(30, 8.0 * _YX, "thickness", color=_MAIN, fontsize=11, ha="center",
            family="monospace")
    _save(fig, outdir, "thickness", png)

    # camber + camber position
    cam = FoilParams(family=FoilFamily.CAMBERED, thickness_ratio=0.08,
                     camber_ratio=0.05, camber_position=0.4)
    for name, note in (("camber", "camber"), ("camber_pos", "position")):
        fig, ax = _fig()
        x, y = _section_xy(cam)
        ax.plot(x, y, color=_MAIN, lw=_LW)
        ax.plot([0, 100], [0, 0], color=_FAINT, lw=1.0, ls="--")
        upper, lower = section_points(cam, 100.0, n_points=120)
        lo = np.interp(upper[:, 0], lower[:, 0], lower[:, 1])
        mean = 0.5 * (upper[:, 1] + lo) * _YX
        ax.plot(upper[:, 0], mean, color=_DIM, lw=1.2, ls=":")
        i = int(np.argmax(mean))
        if name == "camber":
            ax.set_ylim(None, mean[i] + 20)
            _arrow(ax, (upper[i, 0], 0), (upper[i, 0], mean[i]), "")
            ax.text(upper[i, 0], mean[i] + 6.5, note, color=_MAIN, fontsize=11,
                    ha="center", family="monospace")
        else:
            ax.set_ylim(-16, None)
            _arrow(ax, (0, -8), (upper[i, 0], -8), "")
            ax.text(upper[i, 0] / 2, -14, note, color=_MAIN, fontsize=11,
                    ha="center", family="monospace")
        _save(fig, outdir, name, png)

    # tip thickness factor: base vs tip section
    fig, ax = _fig()
    xb, yb = _section_xy(FoilParams(thickness_ratio=0.1))
    ax.plot(xb, yb, color=_DIM, lw=1.4)
    xt, yt = _section_xy(FoilParams(thickness_ratio=0.07), chord=45.0)
    ax.plot(xt + 20, yt + 30, color=_MAIN, lw=_LW)
    ax.text(50, 44, "tip factor", color=_MAIN, fontsize=11, ha="center",
            family="monospace")
    ax.text(50, -16, "base", color=_FAINT, fontsize=9, ha="center",
            family="monospace")
    _save(fig, outdir, "tip_factor", png)

    # foil family: three sections
    fig, ax = _fig()
    fams = [(FoilFamily.SYMMETRIC, "symmetric 50/50", 44),
            (FoilFamily.FLAT_INSIDE, "flat inside", 0),
            (FoilFamily.CAMBERED, "cambered", -44)]
    for fam, label, dy in fams:
        foil = FoilParams(family=fam, thickness_ratio=0.1,
                          camber_ratio=0.04 if fam is FoilFamily.CAMBERED else 0.0)
        x, y = _section_xy(foil)
        ax.plot(x, y + dy, color=_MAIN, lw=1.6)
        ax.text(104, dy, label, color=_DIM, fontsize=9, va="center",
                family="monospace")
    ax.set_xlim(-6, 190)
    _save(fig, outdir, "foil_family", png)

    # grooves: planform with the thinned band + dimension arrows
    from fingen.params import FinParams, GrooveParams
    fig, ax = _fig()
    _draw_outline(ax, color=_DIM, lw=1.4)
    fin = FinParams(grooves=GrooveParams(count=6))
    g = fin.grooves
    d = default.depth
    from fingen.outline import planform
    zpl, x_le_pl, chord_pl = planform(default)
    for i in range(g.count):
        zc = g.span_start * d + i * g.pitch
        x0 = float(np.interp(zc, zpl, x_le_pl))
        run = min(g.length, 0.55 * float(np.interp(zc, zpl, chord_pl)))
        ax.plot([x0 + 2, x0 + 2 + run], [zc, zc], color=_MAIN, lw=2.6,
                solid_capstyle="round", alpha=0.9)
    z0 = g.span_start * d
    _arrow(ax, (default.base * 1.02, z0), (default.base * 1.02, z0 + 5 * g.pitch), "")
    ax.text(default.base * 1.08, z0 + 2.5 * g.pitch, "pitch × n", color=_MAIN,
            fontsize=9, family="monospace", rotation=90, va="center")
    ax.text(30, z0 - 12, "grooves", color=_MAIN, fontsize=11, family="monospace")
    _save(fig, outdir, "grooves", png)

    # groove depth: full vs thinned section overlay
    fig, ax = _fig()
    x, y = _section_xy(FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.1))
    ax.plot(x, y, color=_DIM, lw=1.4)
    thin = lambda xs: 1.0 - 0.5 * np.where(  # noqa: E731
        xs <= 0.45, 1.0, np.where(xs >= 0.6, 0.0,
                                  0.5 * (1 + np.cos(np.pi * (xs - 0.45) / 0.15))))
    upper, lower = section_points(
        FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.1), 100.0,
        n_points=120, thin_outer=thin)
    ax.plot(upper[:, 0], upper[:, 1] * _YX, color=_MAIN, lw=_LW)
    i = int(np.argmax(y))
    y_thin = float(np.interp(x[i], upper[:, 0], upper[:, 1])) * _YX
    ax.plot([x[i], x[i]], [y_thin, y[i]], color=_MAIN, lw=1.2)
    ax.plot([x[i] - 3, x[i] + 3], [y[i], y[i]], color=_MAIN, lw=1.2)
    ax.plot([x[i] - 3, x[i] + 3], [y_thin, y_thin], color=_MAIN, lw=1.2)
    ax.text(x[i], y[i] + 7, "groove depth", color=_MAIN, fontsize=11,
            ha="center", family="monospace")
    _save(fig, outdir, "groove_depth", png)

    # tab x: outline with tabs below the base + chordwise arrow
    fig, ax = _fig()
    _draw_outline(ax, color=_DIM, lw=1.4)
    for cx in (28.5, 81.5):  # dual-tab centers on the default 110 base
        ax.fill([cx - 10, cx + 10, cx + 10, cx - 10], [0, 0, -14, -14],
                color=_MAIN, alpha=0.85)
    _arrow(ax, (55, -24), (80, -24), "")
    ax.text(67, -34, "tab x", color=_MAIN, fontsize=11, ha="center",
            family="monospace")
    ax.set_ylim(-40, None)
    _save(fig, outdir, "tab_x", png)

    # tab y: base section with the tab crossing the thickness + y arrow
    fig, ax = _fig()
    x, y = _section_xy(FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.1))
    ax.plot(x, y, color=_DIM, lw=1.4)
    ax.plot([0, 100], [0, 0], color=_DIM, lw=1.4)
    ax.fill([22, 42, 42, 22], [0, 0, 22, 22], color=_MAIN, alpha=0.75)
    _arrow(ax, (52, 2), (52, 22), "")
    ax.text(56, 12, "tab y", color=_MAIN, fontsize=11, family="monospace",
            va="center")
    ax.text(2, -12, "flat side = print bed", color=_DIM, fontsize=8,
            family="monospace")
    ax.set_ylim(-18, None)
    _save(fig, outdir, "tab_y", png)

    return sorted(outdir.glob("*.svg"))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out/paramviz"
    written = generate_all(out, png="--png" in sys.argv)
    print("\n".join(str(p) for p in written))
