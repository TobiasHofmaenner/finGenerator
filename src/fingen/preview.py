"""Visual preview: render a fin to PNG (planform, sections, 3D mesh).

Development/inspection aid — matplotlib lives in the dev extras, so this
module imports it lazily. Styled to match T-FINS-web's dark-instrument look
(near-black canvas, off-white ink, hairlines, single cyan accent — see the
web repo's style.css); the webapp itself renders GLB/three.js instead.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from fingen.foil import section_points
from fingen.loft import _thickness_at, fin_solid
from fingen.outline import chord_schedule, control_points, planform
from fingen.params import DEFAULT_SETTINGS, FinParams, GenSettings

# T-FINS-web palette (style.css :root)
_BG = "#0a0a0a"
_VIEWER_BG = "#000000"
_TEXT = "#e8e8e8"
_MUTED = "#8f8f8f"
_FAINT = "#5e5e5e"
_LINE = (1.0, 1.0, 1.0, 0.08)
_LINE2 = (1.0, 1.0, 1.0, 0.14)
_ACCENT = "#a7e0ea"  # leading edge / primary
_DANGER = "#f0a9a9"  # trailing edge (subdued red)
_ACCENT_GLOW = (167 / 255, 224 / 255, 234 / 255, 0.12)
_SOLID = "#6fa9b5"  # accent, darkened for shaded surfaces

_N_SECTIONS = 6


def _style_axes(ax) -> None:
    ax.set_facecolor(_BG)
    for spine in ax.spines.values():
        spine.set_color(_LINE2)
        spine.set_linewidth(0.8)
    ax.tick_params(colors=_MUTED, labelsize=8)
    ax.xaxis.label.set_color(_MUTED)
    ax.yaxis.label.set_color(_MUTED)
    ax.title.set_color(_TEXT)
    ax.grid(True, color=_LINE, linewidth=0.7)


def render_preview(fin: FinParams, path: str | Path,
                   settings: GenSettings = DEFAULT_SETTINGS, part=None,
                   show_solid: bool = False) -> Path:
    """Write a PNG: outline + control polygons and section profiles; with
    show_solid=True a third panel renders the tessellated solid (off by
    default — the webapp has a live 3D view, and skipping it means no loft
    is needed at all). Returns the written path."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    z, x_le, chord_dense = planform(fin.outline)
    x_te = x_le + chord_dense
    from fingen.loft import groove_station_z

    stations = chord_schedule(fin.outline, settings, tip_chord_min=settings.cap_chord,
                              extra_z=groove_station_z(fin))
    le_ctrl, te_ctrl = control_points(fin.outline)

    n_panels = 3 if show_solid else 2
    fig = plt.figure(figsize=(5 * n_panels, 6), facecolor=_BG)

    ax = fig.add_subplot(1, n_panels, 1)
    _style_axes(ax)
    ax.plot(x_le, z, color=_ACCENT, lw=2, label="LE")
    ax.plot(x_te, z, color=_DANGER, lw=2, label="TE")
    for ctrl, color in ((le_ctrl, _ACCENT), (te_ctrl, _DANGER)):
        ax.plot(ctrl[:, 0], ctrl[:, 1], "o--", color=color, ms=3.5, lw=0.7, alpha=0.35)
    for st in stations:
        ax.plot([st.x_le, st.x_le + st.chord], [st.z, st.z],
                color=_FAINT, lw=0.5, alpha=0.6)
    ax.set_aspect("equal")
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("z (span) [mm]")
    ax.set_title("planform + control polygons")
    legend = ax.legend(facecolor=_BG, edgecolor=_LINE2, labelcolor=_TEXT, fontsize=9)
    legend.get_frame().set_linewidth(0.8)

    ax = fig.add_subplot(1, n_panels, 2)
    _style_axes(ax)
    idx = np.unique(np.linspace(0, len(stations) - 1, _N_SECTIONS).astype(int))
    picks = [stations[i] for i in idx]
    offset = 0.0
    from fingen.loft import _groove_thins

    for st in reversed(picks):
        thin_outer, thin_inner = _groove_thins(fin, st.z, st.chord)
        upper, lower = section_points(fin.foil, st.chord,
                                      thickness_ratio=_thickness_at(fin, st.z),
                                      n_points=settings.n_foil_points,
                                      thin_outer=thin_outer, thin_inner=thin_inner)
        xs = np.concatenate((upper[:, 0], lower[::-1, 0])) + st.x_le
        ys = np.concatenate((upper[:, 1], lower[::-1, 1])) + offset
        ax.plot(xs, ys, color=_TEXT, lw=0.9)
        ax.fill(xs, ys, color=_ACCENT_GLOW)
        ax.annotate(f"z={st.z:.0f}", (st.x_le, offset + 1.0),
                    fontsize=7, color=_MUTED, family="monospace")
        offset += max(st.chord * fin.foil.thickness_ratio * 2.2, 7.0)
    ax.set_aspect("equal")
    ax.set_title("sections (true thickness)")
    ax.set_xlabel("x [mm]")

    if show_solid:
        if part is None:
            part = fin_solid(fin, settings)
        _solid_panel(fig, part)

    fig.tight_layout()
    fig.savefig(path, dpi=110, facecolor=_BG)
    plt.close(fig)
    return path


def _solid_panel(fig, part) -> None:
    import numpy as np

    vertices, faces = part.tessellate(0.3)
    pts = np.array([(v.X, v.Y, v.Z) for v in vertices])
    ax3 = fig.add_subplot(1, 3, 3, projection="3d")
    ax3.set_facecolor(_VIEWER_BG)
    ax3.plot_trisurf(pts[:, 0], pts[:, 1], pts[:, 2], triangles=np.array(faces),
                     color=_SOLID, edgecolor="none", alpha=0.95, shade=True)
    ranges = pts.max(axis=0) - pts.min(axis=0)
    ax3.set_box_aspect(tuple(np.maximum(ranges, 1.0)))
    ax3.set_title("lofted solid", color=_TEXT)
    ax3.view_init(elev=18, azim=-60)
    for axis in (ax3.xaxis, ax3.yaxis, ax3.zaxis):
        axis.set_pane_color((0, 0, 0, 1.0))
        axis.line.set_color(_LINE2)
    ax3.tick_params(colors=_FAINT, labelsize=7)
    ax3.grid(False)
