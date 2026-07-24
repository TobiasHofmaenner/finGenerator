"""Visual preview: render a fin to PNG (planform, sections, 3D mesh).

Development/inspection aid — matplotlib lives in the dev extras, so this
module imports it lazily. The webapp will render GLB/three.js instead.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from fingen.foil import section_points
from fingen.loft import _thickness_at, fin_solid
from fingen.outline import chord_schedule, control_points, planform
from fingen.params import DEFAULT_SETTINGS, FinParams, GenSettings


def render_preview(fin: FinParams, path: str | Path,
                   settings: GenSettings = DEFAULT_SETTINGS, part=None) -> Path:
    """Write a three-panel PNG: outline + control polygon, section profiles,
    and the tessellated solid. Returns the written path."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    z, x_le, chord_dense = planform(fin.outline)
    x_te = x_le + chord_dense
    stations = chord_schedule(fin.outline, settings, tip_chord_min=settings.cap_chord)
    le_ctrl, te_ctrl = control_points(fin.outline)

    fig = plt.figure(figsize=(15, 6))

    ax = fig.add_subplot(1, 3, 1)
    ax.plot(x_le, z, "b-", lw=2, label="LE")
    ax.plot(x_te, z, "r-", lw=2, label="TE")
    for ctrl, color in ((le_ctrl, "b"), (te_ctrl, "r")):
        ax.plot(ctrl[:, 0], ctrl[:, 1], f"{color}o--", ms=4, lw=0.7, alpha=0.4)
    for st in stations:
        ax.plot([st.x_le, st.x_le + st.chord], [st.z, st.z], "k-", lw=0.5, alpha=0.5)
    ax.set_aspect("equal")
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("z (span) [mm]")
    ax.set_title("planform + control polygons")
    ax.legend()

    ax = fig.add_subplot(1, 3, 2)
    picks = [stations[0], stations[len(stations) // 2], stations[-1]]
    offset = 0.0
    for st in reversed(picks):
        upper, lower = section_points(fin.foil, st.chord,
                                      thickness_ratio=_thickness_at(fin, st.z),
                                      n_points=settings.n_foil_points)
        xs = np.concatenate((upper[:, 0], lower[::-1, 0])) + st.x_le
        ys = np.concatenate((upper[:, 1], lower[::-1, 1])) + offset
        ax.plot(xs, ys, "k-", lw=1)
        ax.fill(xs, ys, alpha=0.15)
        ax.annotate(f"z={st.z:.0f}", (st.x_le, offset), fontsize=8)
        offset += max(st.chord * fin.foil.thickness_ratio * 2.5, 8.0)
    ax.set_aspect("equal")
    ax.set_title("sections (true thickness)")
    ax.set_xlabel("x [mm]")

    if part is None:
        part = fin_solid(fin, settings)
    vertices, faces = part.tessellate(0.3)
    pts = np.array([(v.X, v.Y, v.Z) for v in vertices])
    ax3 = fig.add_subplot(1, 3, 3, projection="3d")
    ax3.plot_trisurf(pts[:, 0], pts[:, 1], pts[:, 2], triangles=np.array(faces),
                     color="tab:cyan", edgecolor="none", alpha=0.9, shade=True)
    ranges = pts.max(axis=0) - pts.min(axis=0)
    ax3.set_box_aspect(tuple(np.maximum(ranges, 1.0)))
    ax3.set_title("lofted solid")
    ax3.view_init(elev=18, azim=-60)

    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
