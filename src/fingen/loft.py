"""Assembly of the 3D fin solid (docs/PHYSICS.md §5).

Foil sections are generated at each outline station with identical point count
and parameterization — sections are compatible by construction, which is the
guard against the classical skinning failure mode (wiggles/control-point
explosion from incompatible section knot vectors) [PT02, PT97]. The solid is
closed by the planar base face at z = 0 and the last station's tiny planar
face at the tip (the station is solved exactly at the cap chord).

Coordinate frame: x streamwise (LE of the base at x = 0), y section thickness
(FLAT_INSIDE fins have their flat face exactly in the y = 0 plane), z spanwise.
"""

from __future__ import annotations

import numpy as np
from build123d import BuildLine, BuildSketch, Line, Part, Plane, Spline, loft, make_face
from OCP.StdFail import StdFail_NotDone

from fingen.foil import section_points
from fingen.outline import chord_schedule
from fingen.params import DEFAULT_SETTINGS, FinParams, FoilFamily, GenSettings


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
            if fin.foil.family is FoilFamily.FLAT_INSIDE:
                # Outer surface spline + straight TE + straight flat face:
                # the inner face is an exact planar strip (print-bed face);
                # the LE corner between them is a real feature of flat foils.
                Spline(*[tuple(p) for p in upper])
                Line(tuple(upper[-1]), tuple(lower[-1]))
                Line(tuple(lower[-1]), tuple(lower[0]))
            else:
                # Two splines sharing the LE vertex. The vertex pins OCCT's
                # station-to-station correspondence at the nose — a single
                # wrap-around spline lets the LE drift in curve parameter as
                # the upper/lower arc ratio changes spanwise, skewing the
                # skin. LE tangency across the vertex is left to the
                # interpolator: with cosine clustering the nose points are
                # ~0.02% chord apart, so the tangent match is near-exact.
                # (Explicit end tangents would guarantee G1 but make the
                # sketch wire non-planar in current build123d.)
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
    # The tip lobe's dome is horizontally tangent at the apex, so a vertex
    # cap there would be a degenerately flat cone (the OCCT failure mode the
    # sweep found on squat outlines). The last station is solved exactly at
    # cap_chord; its tiny planar face (~3 x 0.3 mm) closes the solid instead.
    try:
        solid = loft(sections)
    except StdFail_NotDone as exc:
        raise ValueError(
            f"OCCT could not loft this parameter combination cleanly: {fin}"
        ) from exc
    return Part() + solid
