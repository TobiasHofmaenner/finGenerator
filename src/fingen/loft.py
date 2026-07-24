"""Assembly of the 3D fin solid (docs/PHYSICS.md §5).

Foil sections are generated at each outline station with identical point count
and parameterization — sections are compatible by construction, which is the
guard against the classical skinning failure mode (wiggles/control-point
explosion from incompatible section knot vectors) [PT02, PT97]. The solid is
closed by the planar base face at z = 0 and a cap lofted to the shared tip
point.

Coordinate frame: x streamwise (LE of the base at x = 0), y section thickness
(FLAT_INSIDE fins have their flat face exactly in the y = 0 plane), z spanwise.
"""

from __future__ import annotations

import numpy as np
from build123d import BuildLine, BuildSketch, Line, Part, Plane, Spline, Vertex, loft, make_face
from OCP.StdFail import StdFail_NotDone

from fingen.foil import section_points
from fingen.outline import chord_schedule, tip_point
from fingen.params import DEFAULT_SETTINGS, FinParams, GenSettings


def _thickness_at(fin: FinParams, z: float) -> float:
    """Spanwise t/c schedule: linear blend base → tip [BW04 tip-stall rationale]."""
    frac = z / fin.outline.depth
    t = fin.foil.thickness_ratio
    return t * (1.0 + (fin.thickness_tip_factor - 1.0) * frac)


def _section_sketch(fin: FinParams, z: float, x_le: float, chord: float,
                    settings: GenSettings):
    upper, lower = section_points(fin.foil, chord, thickness_ratio=_thickness_at(fin, z),
                                  n_points=settings.n_foil_points)
    upper = upper + np.array([x_le, 0.0])
    lower = lower + np.array([x_le, 0.0])
    with BuildSketch(Plane.XY.offset(z)) as sk:
        with BuildLine():
            Spline(*[tuple(p) for p in upper])
            Line(tuple(upper[-1]), tuple(lower[-1]))
            Spline(*[tuple(p) for p in lower[::-1]])
        make_face()
    return sk.sketch


def fin_solid(fin: FinParams, settings: GenSettings = DEFAULT_SETTINGS) -> Part:
    """Build the solid for a single fin blade; base plane at z = 0.

    Raises ValueError (from the outline) for parameter combinations whose
    edges cross — callers get a clean rejection before any OCCT work.
    """
    stations = chord_schedule(fin.outline, settings, tip_chord_min=settings.cap_chord)
    sections = [
        _section_sketch(fin, st.z, st.x_le, st.chord, settings) for st in stations
    ]
    x_tip, depth = tip_point(fin.outline)
    try:
        solid = loft([*sections, Vertex(x_tip, 0.0, depth)])
    except StdFail_NotDone as exc:
        raise ValueError(
            f"OCCT could not loft this parameter combination cleanly: {fin}"
        ) from exc
    return Part() + solid
