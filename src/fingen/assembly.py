r"""Fin-set assembly: place per-slot blades into one 3D scene (docs/PHYSICS.md §2b).

A single blade solid (fingen.loft.fin_solid) is built in its own frame with the
base on z = 0. Toe and cant are *placement* transforms applied here, and one
right-hand blade serves both sides: the left hand is `export.mirror_hand` of the
right (build/CHECK the right blade, mirror last). This module never re-lofts a
blade to change hand or angle.

Assembly frame (== each blade's own frame — no remapping, which is the whole
point of reusing fin_solid output directly):

    +x  aft, toward the tail     (LE at local x=0, TE at +x)
    +y  toward the RIGHT rail     (outboard for the right fin; the canonical
                                   right-hand blade's foil bulges toward +y,
                                   flat/inboard face on y=0 — see export.py)
    +z  up, out of the board       (blades hang in z ≥ 0; board plane = z=0)

Origin = the center-fin base center. The right fin sits at +side_y, the left at
−side_y; thruster/quad front fins sit FORWARD of the origin, so side_x < 0.

Sign conventions — TOP VIEW (looking down −z onto the board bottom), nose up:

                          nose (forward, −x)
                                 ^
                                 |
              LE\               |               /LE      LE = leading edge
                 \   RIGHT fin  |  LEFT fin    /         both leading edges
                  \  (+side_y)  |  (−side_y)  /          rotate IN toward the
              TE   \            |            /   TE      stringer = toe-IN.
        outboard <--\           |           /--> outboard
             (+y rail)                       (−y rail)
                                 |
                        tail (aft, +x), center fin on the stringer (toe=cant=0)

    toe  = rotation about the vertical z axis. NOSE-IN (leading edge toward the
           stringer) is POSITIVE toe. Right fin: +toe about +z. Left fin gets
           the opposite sign (−toe about +z) so it toes in symmetrically.
    cant = outward lean about the longitudinal x axis: the TIP leans toward the
           near rail (right fin tip → +y, left fin tip → −y). Right fin: −cant
           about +x; left fin: +cant about +x — again opposite signs, same
           magnitude.

Cant and the z ≥ 0 convention: a canted blade's root must stay on the board
plane, so cant rotates about the x-parallel line through the blade's OWN base
centerline (the base face center, recentered to the origin) BEFORE the outboard
translation — never about the global x axis after translating to side_y (the
classic bug: that lifts the whole root by side_y·sin(cant), centimetres off the
board). Rotating about the base centerline leaves only the finite base-thickness
tilt (≤ ~1 mm at 8°), so bbox.min.Z ≈ 0 for every blade.
"""

from __future__ import annotations

from pathlib import Path

from build123d import Axis, Box, Compound, Part, Pos

from fingen.export import mirror_hand, to_step, to_stl
from fingen.loft import fin_solid
from fingen.params import DEFAULT_SETTINGS, FinConfig, FinSetParams, GenSettings

# Pairwise solid-intersection volume (mm³) above which two slots are declared
# overlapping. A hair over zero: disjoint blades share nothing, and any real
# interpenetration is many mm³ (see _validate_no_overlap).
_OVERLAP_TOL = 1.0


def _base_plane_center(part: Part):
    """Center of the blade's base cross-section just above z = 0.

    The naive lowest-face pick grabs a tab bottom on tabbed fins (tabs
    extend below the base plane), pivoting the placement ~6 mm off; and
    the z=0 planar faces themselves are partitioned by tab footprints,
    shifting their area centroid. A thin slice at z = 0.5 mm sees the
    pure blade section — identical for tabbed and tabless variants of
    the same blade — and its volume centroid is the section's area
    centroid."""
    slab = Pos(0.0, 0.0, 0.5) * Box(4000.0, 4000.0, 0.2)
    section = part & slab
    return section.center()


def place_fin(part: Part, *, toe_deg: float, cant_deg: float, x: float, y: float,
              hand: str) -> Part:
    """Place one blade: mirror (left hand), toe, cant, then translate to (x, y).

    hand is "right" (build orientation, foil bulge → +y) or "left" (mirror
    image). Left/right take opposite toe and cant signs from the same
    magnitudes. See the module docstring for the frame and sign sketch.

    The pivot for both rotations is the blade's base-face center: it is moved to
    the origin first, so toe is about the vertical line through the base center
    and cant about the base centerline — keeping the root on z ≈ 0 — and (x, y)
    is then the absolute position of that base center in the assembly frame.
    """
    if hand not in ("right", "left"):
        raise ValueError(f"hand must be 'right' or 'left', got {hand!r}")
    if hand == "left":
        part = mirror_hand(part)
    sgn = 1.0 if hand == "right" else -1.0

    base = _base_plane_center(part)
    part = Pos(-base.X, -base.Y, 0.0) * part  # base center → origin
    part = part.rotate(Axis.Z, sgn * toe_deg)  # toe: about vertical, nose-in +
    part = part.rotate(Axis.X, -sgn * cant_deg)  # cant: outward tip lean
    part = Pos(x, y, 0.0) * part  # to the slot
    return Part() + part


def _bbox_overlap(ba, bb, margin: float = 1e-6) -> bool:
    """Cheap AABB pre-filter on precomputed bounding boxes: disjoint boxes
    cannot share volume, so the expensive boolean is skipped for a
    well-spaced set (the normal path)."""

    def gap(lo1, hi1, lo2, hi2) -> bool:  # do 1-D intervals [lo,hi] stay apart?
        return hi1 + margin < lo2 or hi2 + margin < lo1

    return not (gap(ba.min.X, ba.max.X, bb.min.X, bb.max.X)
                or gap(ba.min.Y, ba.max.Y, bb.min.Y, bb.max.Y)
                or gap(ba.min.Z, ba.max.Z, bb.min.Z, bb.max.Z))


def _validate_no_overlap(placed: list[tuple[str, Part]]) -> None:
    """Reject a set whose blades interpenetrate (e.g. side_y too small): the
    minimum safe spacing depends on blade thickness/toe/cant, so it is checked
    on the placed solids rather than by a scalar bound. Raises ValueError."""
    boxes = [p.bounding_box() for _, p in placed]  # one OCCT eval per blade
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            (ni, pi), (nj, pj) = placed[i], placed[j]
            if not _bbox_overlap(boxes[i], boxes[j]):
                continue
            inter = pi & pj
            vol = inter.volume if inter is not None else 0.0
            if vol > _OVERLAP_TOL:
                raise ValueError(
                    f"fin slots '{ni}' and '{nj}' interpenetrate "
                    f"(intersection {vol:.0f} mm³): increase side_y/rear_y "
                    "spacing (or reduce toe/cant)")


def fin_set(set_params: FinSetParams,
            settings: GenSettings = DEFAULT_SETTINGS) -> list[tuple[str, Part]]:
    """Build and place every blade of the set. Returns [(slot_name, Part), …].

    Each unique blade (center, side) is lofted once; the opposite hand is a
    mirror, and every blade is placed per config. The center/rear-center fin is
    symmetric and rides the stringer, so it is placed with toe = cant = 0.
    Raises ValueError if any two placed blades overlap.
    """
    cfg = set_params.config
    # Lazy lofts: FinSetParams populates both slots for every config, but
    # e.g. SINGLE never places the side blade — don't pay for solids the
    # config discards (this path sits in optimizer/CFD-prep loops).
    _cache: dict[str, Part] = {}

    def center() -> Part:
        if "center" not in _cache:
            _cache["center"] = fin_solid(set_params.center, settings)
        return _cache["center"]

    def side() -> Part:
        if "side" not in _cache:
            _cache["side"] = fin_solid(set_params.side, settings)
        return _cache["side"]

    sx, sy = set_params.side_x, set_params.side_y
    toe, cant = set_params.toe, set_params.cant

    placed: list[tuple[str, Part]] = []
    if cfg is FinConfig.SINGLE:
        placed.append(("center",
                       place_fin(center(), toe_deg=0.0, cant_deg=0.0, x=0.0,
                                 y=0.0, hand="right")))
    elif cfg is FinConfig.TWIN:
        placed += _side_pair(side(), "", toe, cant, sx, sy)
    elif cfg in (FinConfig.THRUSTER, FinConfig.TWO_PLUS_ONE):
        placed.append(("center",
                       place_fin(center(), toe_deg=0.0, cant_deg=0.0, x=0.0,
                                 y=0.0, hand="right")))
        placed += _side_pair(side(), "", toe, cant, sx, sy)
    elif cfg is FinConfig.QUAD:
        placed += _side_pair(side(), "front_", toe, cant, sx, sy)
        placed += _side_pair(side(), "rear_", set_params.rear_toe,
                             set_params.rear_cant, set_params.rear_x,
                             set_params.rear_y)
    else:  # pragma: no cover - enum is exhaustive above
        raise ValueError(f"unhandled config {cfg}")

    _validate_no_overlap(placed)
    return placed


def _side_pair(side: Part, prefix: str, toe: float, cant: float,
               x: float, y: float) -> list[tuple[str, Part]]:
    """Right (+y) and left (−y) placements of the same side blade."""
    return [
        (f"{prefix}right",
         place_fin(side, toe_deg=toe, cant_deg=cant, x=x, y=y, hand="right")),
        (f"{prefix}left",
         place_fin(side, toe_deg=toe, cant_deg=cant, x=x, y=-y, hand="left")),
    ]


def _scene(set_params: FinSetParams, settings: GenSettings) -> Compound:
    """All placed blades as one Compound labelled 'fins' — snappyHexMesh treats
    the multi-solid surface as a single patch."""
    blades = fin_set(set_params, settings)
    return Compound(label="fins", children=[p for _, p in blades])


def assembly_stl(set_params: FinSetParams, path: str | Path,
                 settings: GenSettings = DEFAULT_SETTINGS) -> Path:
    """Write one STL of the whole placed set (multi-fin CFD surface 'fins')."""
    return to_stl(_scene(set_params, settings), path)


def assembly_step(set_params: FinSetParams, path: str | Path,
                  settings: GenSettings = DEFAULT_SETTINGS) -> Path:
    """Write the whole placed set to a STEP file for CAD."""
    return to_step(_scene(set_params, settings), path)


# --- preview -----------------------------------------------------------------

# House style (bg from the brief; cyan primary / orange accent).
_BG = "#0b0e11"
_INK = "#e8e8e8"
_MUTED = "#8f8f8f"
_CYAN = "#a7e0ea"
_ORANGE = "#f0a86a"
_CENTER = "#6fa9b5"


def _slice_segments(part: Part, z: float, deflection: float = 0.5):
    """(N, 2, 2) array of x-y line segments where the tessellated blade crosses
    the horizontal plane at height z — the top-view cross-section outline."""
    import numpy as np

    verts, faces = part.tessellate(deflection)
    pts = np.array([(v.X, v.Y, v.Z) for v in verts])
    segs = []
    for tri in faces:
        q = pts[list(tri)]
        zc = q[:, 2] - z
        cross = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if zc[a] * zc[b] < 0.0:
                t = zc[a] / (zc[a] - zc[b])
                cross.append(q[a] + t * (q[b] - q[a]))
        if len(cross) == 2:
            segs.append([cross[0][:2], cross[1][:2]])
    return np.array(segs) if segs else np.empty((0, 2, 2))


def preview_set(set_params: FinSetParams, path: str | Path,
                settings: GenSettings = DEFAULT_SETTINGS, z: float = 5.0) -> Path:
    """Top-view (x-y) PNG: each blade's z-section outline, toe annotations and a
    config label, in the dark house style. Returns the written path."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blades = fin_set(set_params, settings)

    fig, ax = plt.subplots(figsize=(6.5, 6.5), facecolor=_BG)
    ax.set_facecolor(_BG)
    for name, part in blades:
        segs = _slice_segments(part, z)
        color = _CENTER if "center" in name else _CYAN
        if len(segs):
            ax.add_collection(LineCollection(segs, colors=color, linewidths=1.4))
        # Toe annotation at the blade's base-face center (x-y).
        base = _base_plane_center(part)
        is_rear = "rear" in name
        toe = set_params.rear_toe if is_rear else set_params.toe
        signed = 0.0 if "center" in name else (toe if "right" in name else -toe)
        ax.annotate(f"{name}\ntoe {signed:+.1f}°" if "center" not in name
                    else f"{name}\ntoe 0°",
                    (base.X, base.Y), color=_ORANGE, fontsize=8,
                    ha="center", va="center", family="monospace")

    ax.axvline(0.0, color=_MUTED, lw=0.6, ls="--", alpha=0.5)  # stringer
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.margins(0.15)
    ax.invert_xaxis()  # +x aft → tail to the left, nose to the right
    ax.set_xlabel("x aft →  [mm]", color=_MUTED)
    ax.set_ylabel("y outboard (right rail +) [mm]", color=_MUTED)
    ax.set_title(f"{set_params.config.value} set — top view "
                 f"(section z={z:.0f} mm)", color=_INK)
    for spine in ax.spines.values():
        spine.set_color("#2a2f36")
    ax.tick_params(colors=_MUTED, labelsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110, facecolor=_BG)
    plt.close(fig)
    return path
