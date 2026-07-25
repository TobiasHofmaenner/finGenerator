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
from fingen.params import (
    DEFAULT_SETTINGS,
    FinParams,
    FoilFamily,
    GenSettings,
    GrooveSurface,
)


def _thickness_at(fin: FinParams, z: float) -> float:
    """Spanwise t/c schedule: linear blend base → tip [BW04 tip-stall rationale]."""
    frac = z / fin.outline.depth
    t = fin.foil.thickness_ratio
    return t * (1.0 + (fin.thickness_tip_factor - 1.0) * frac)


def _groove_intensity(fin: FinParams, z: float) -> float:
    """Spanwise groove weight at station z: a raised-cosine bump per groove
    (smooth channel walls — no C1 breaks for the spanwise skin to ring on),
    1.0 at a channel center, 0.0 between channels and outside the band."""
    g = fin.grooves
    if not g.count:
        return 0.0
    total = 0.0
    for i in range(g.count):
        zc = g.span_start * fin.outline.depth + i * g.pitch
        u = (z - zc) / (0.5 * g.width)
        if abs(u) < 1.0:
            total += 0.5 * (1.0 + np.cos(np.pi * u))
    return min(total, 1.0)


def _groove_thins(fin: FinParams, z: float, chord: float):
    """(thin_outer, thin_inner) callables for section_points at station z.

    Chordwise window: full depth from the LE (the scalloped leading edge
    visible on the [Els22]/[For24] G-fins), fading out by 85 % of the local
    chord so the TE band keeps printable thickness. Depth semantics:
    depth_ratio · intensity of the local per-side thickness is removed.
    """
    g_z = _groove_intensity(fin, z)
    if g_z < 1e-4:
        return None, None
    grooves = fin.grooves
    x_end = min(grooves.length / chord, 0.85)
    x_ramp = 0.75 * x_end

    def thin(x: np.ndarray) -> np.ndarray:
        window = np.where(
            x <= x_ramp, 1.0,
            np.where(x >= x_end, 0.0,
                     0.5 * (1.0 + np.cos(np.pi * (x - x_ramp) / (x_end - x_ramp)))))
        return 1.0 - grooves.depth_ratio * g_z * window

    if grooves.surface is GrooveSurface.BOTH:
        return thin, thin
    return thin, None


def groove_station_z(fin: FinParams) -> list[float]:
    """Exact spanwise stations a groove band needs: channel edges, quarter
    points and centers, plus the inter-channel gap midpoints that pin the
    full-thickness ridges between grooves."""
    g = fin.grooves
    if not g.count:
        return []
    zs: list[float] = []
    for i in range(g.count):
        zc = g.span_start * fin.outline.depth + i * g.pitch
        zs += [zc - 0.5 * g.width, zc - 0.25 * g.width, zc,
               zc + 0.25 * g.width, zc + 0.5 * g.width]
        if i + 1 < g.count:
            zs.append(zc + 0.5 * g.pitch)
    # Half-pitch margins outside the band: the loft is segmented there (the
    # ruled groove segment needs a full-thickness boundary station on each
    # side that the smooth segments share).
    zs.insert(0, g.span_start * fin.outline.depth - 0.5 * g.pitch)
    zs.append(g.span_start * fin.outline.depth + (g.count - 1) * g.pitch
              + 0.5 * g.pitch)
    return zs


def _section_sketch(fin: FinParams, z: float, x_le: float, chord: float,
                    settings: GenSettings):
    thin_outer, thin_inner = _groove_thins(fin, z, chord)
    upper, lower = section_points(fin.foil, chord, thickness_ratio=_thickness_at(fin, z),
                                  n_points=settings.n_foil_points,
                                  thin_outer=thin_outer, thin_inner=thin_inner)
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
    stations = chord_schedule(fin.outline, settings, tip_chord_min=settings.cap_chord,
                              extra_z=groove_station_z(fin))
    sections = [
        _section_sketch(fin, st.z, st.x_le, st.chord, settings) for st in stations
    ]
    # The tip lobe's dome is horizontally tangent at the apex, so a vertex
    # cap there would be a degenerately flat cone (the OCCT failure mode the
    # sweep found on squat outlines). The last station is solved exactly at
    # cap_chord; its tiny planar face (~3 x 0.3 mm) closes the solid instead.
    try:
        if fin.grooves.count:
            # Segmented loft: ThruSections' global surface fit is unstable
            # against the grooves' short-wavelength thickness alternation
            # (metre-scale skin excursions from a 5 % dip — measured, not
            # hypothetical). The groove band is lofted RULED — linear between
            # stations, overshoot-free by construction, and exact through the
            # injected edge/quarter/center stations — while the base and tip
            # segments keep the smooth fit. Boundary stations are shared, so
            # the fuse joins on identical planar faces.
            g = fin.grooves
            z_lo = g.span_start * fin.outline.depth - 0.5 * g.pitch
            z_hi = (g.span_start * fin.outline.depth + (g.count - 1) * g.pitch
                    + 0.5 * g.pitch)
            i_lo = max((i for i, st in enumerate(stations) if st.z <= z_lo + 0.06),
                       default=0)
            i_hi = min((i for i, st in enumerate(stations) if st.z >= z_hi - 0.06),
                       default=len(stations) - 1)
            solid = loft(sections[i_lo:i_hi + 1], ruled=True)
            if i_lo > 0:
                solid = solid + loft(sections[:i_lo + 1])
            if i_hi < len(stations) - 1:
                solid = solid + loft(sections[i_hi:])
        else:
            solid = loft(sections)
    except StdFail_NotDone as exc:
        raise ValueError(
            f"OCCT could not loft this parameter combination cleanly: {fin}"
        ) from exc
    from fingen.tabs import build_tabs

    tabs = build_tabs(fin, settings)
    if tabs is not None:
        solid = solid + tabs
    return Part() + solid
