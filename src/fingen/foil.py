"""Foil section generation: 2D hydrofoil profiles (docs/PHYSICS.md §4).

NACA 4-digit construction [Jac33, AvD59]: analytic thickness distribution and
two-parabola camber line, thickness applied perpendicular to the camber line.
Families (docs/FIN-PRIMER.md §4): SYMMETRIC (50/50), CAMBERED (m, p explicit),
FLAT_INSIDE (flat face at y=0, full section shape outboard — the half-section
construction of the measured baseline fin [BW04]).

Both surfaces are resampled onto a fixed arc-length parameterization before
being returned. This is what makes sections genuinely compatible across loft
stations [PT02]: the raw perpendicular camber assembly produces non-monotone,
station-dependent point spacing near the leading edge (at higher camber the
first cosine points fold slightly past the LE), which OCCT's section matching
turns into silent spanwise distortion. Arc-length fractions are geometry-
independent, so index i means "the same place on the surface" at every station.

All returned coordinates are in mm. Sections are generated in local chord
coordinates: leading edge at x=0, trailing edge at x=chord, thickness along y.
The flat face of FLAT_INSIDE lies exactly in the y=0 plane at every station —
including the trailing-edge printability wedge, which for this family is
applied entirely to the outer surface — so the assembled blade has a truly
planar inner face (printable flat on the bed).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from fingen.params import FoilFamily, FoilParams

# NACA thickness polynomial coefficients [Jac33]. The -0.1015 x^4 term leaves
# the analytic trailing edge slightly open; the printability truncation below
# widens it to te_thickness regardless.
_C = (0.29690, -0.12600, -0.35160, 0.28430, -0.10150)


def _cosine_x(n: int) -> np.ndarray:
    """Chordwise stations clustered at the leading edge, x ∈ [0, 1]."""
    theta = np.linspace(0.0, np.pi, n)
    return 0.5 * (1.0 - np.cos(theta))


def _thickness(x: np.ndarray, t: float) -> np.ndarray:
    """Per-side NACA thickness envelope y_t(x); max y_t = t/2 (total = t) [Jac33]."""
    return 5.0 * t * (_C[0] * np.sqrt(x) + _C[1] * x + _C[2] * x**2
                      + _C[3] * x**3 + _C[4] * x**4)


def _camber(x: np.ndarray, m: float, p: float) -> tuple[np.ndarray, np.ndarray]:
    """NACA camber line y_c(x) and slope dy_c/dx [Jac33]."""
    y = np.where(x < p,
                 (m / p**2) * (2.0 * p * x - x**2),
                 (m / (1.0 - p) ** 2) * ((1.0 - 2.0 * p) + 2.0 * p * x - x**2))
    dy = np.where(x < p,
                  (2.0 * m / p**2) * (p - x),
                  (2.0 * m / (1.0 - p) ** 2) * (p - x))
    return y, dy


def _resample_by_arclength(pts: np.ndarray, n: int) -> np.ndarray:
    """Resample a surface polyline at fixed arc-length fractions (cosine
    spacing: dense at both ends, where the LE and TE curvature lives)."""
    seg = np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1))
    s = np.concatenate(([0.0], np.cumsum(seg)))
    fractions = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, n)))
    si = fractions * s[-1]
    out = np.column_stack((np.interp(si, s, pts[:, 0]), np.interp(si, s, pts[:, 1])))
    out[0], out[-1] = pts[0], pts[-1]
    return out


def section_points(
    foil: FoilParams,
    chord: float,
    thickness_ratio: float | None = None,
    n_points: int = 100,
    thin_outer: Callable[[np.ndarray], np.ndarray] | None = None,
    thin_inner: Callable[[np.ndarray], np.ndarray] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (upper, lower) surface point arrays for one section, in mm.

    Both arrays run leading edge → trailing edge, share the exact leading edge
    point, and are arc-length parameterized (see module docstring). The
    trailing edge is truncated to foil.te_thickness and left open (the caller
    closes it with a straight TE segment).

    thickness_ratio overrides foil.thickness_ratio (spanwise schedules).
    thin_outer/thin_inner scale the per-side thickness distribution as a
    function of normalized chordwise position — the hook for spanwise
    thinning grooves [Els22]. Thinning acts on the thickness envelope (about
    the camber line), so cambered sections groove cleanly too.
    """
    if chord <= 0.0:
        raise ValueError(f"chord must be positive, got {chord}")
    t = foil.thickness_ratio if thickness_ratio is None else thickness_ratio
    n = max(n_points // 2, 20)
    x = _cosine_x(n)
    yt = _thickness(x, t)
    yt_u = yt * thin_outer(x) if thin_outer is not None else yt
    yt_l = yt * thin_inner(x) if thin_inner is not None else yt

    if foil.family is FoilFamily.FLAT_INSIDE:
        # Flat face at y=0; the full section thickness goes outboard: the outer
        # surface is the doubled thickness envelope (upper half of a NACA
        # section of parameter 2t), so max total thickness = t·chord [BW04].
        upper = np.column_stack((x, 2.0 * yt_u))
        lower = np.column_stack((x, np.zeros_like(x)))
    elif foil.family is FoilFamily.CAMBERED and foil.camber_ratio > 0.0:
        yc, dyc = _camber(x, foil.camber_ratio, foil.camber_position)
        theta = np.arctan(dyc)
        upper = np.column_stack((x - yt_u * np.sin(theta), yc + yt_u * np.cos(theta)))
        lower = np.column_stack((x + yt_l * np.sin(theta), yc - yt_l * np.cos(theta)))
        lower[0] = upper[0]  # exact shared LE point
    else:  # SYMMETRIC (or CAMBERED with zero camber)
        upper = np.column_stack((x, yt_u))
        lower = np.column_stack((x, -yt_l))

    upper *= chord
    lower *= chord

    # Printability: widen the trailing edge to te_thickness with a linear wedge
    # (standard blunt-TE modification), applied only if needed. FLAT_INSIDE
    # takes the whole wedge on the outer surface so the flat face stays a
    # true plane; other families split it symmetrically.
    gap = upper[-1, 1] - lower[-1, 1]
    if gap < foil.te_thickness:
        add = foil.te_thickness - gap
        if foil.family is FoilFamily.FLAT_INSIDE:
            upper[:, 1] += add * (upper[:, 0] / chord)
        else:
            upper[:, 1] += 0.5 * add * (upper[:, 0] / chord)
            lower[:, 1] -= 0.5 * add * (lower[:, 0] / chord)

    return _resample_by_arclength(upper, n), _resample_by_arclength(lower, n)


def le_tangent(foil: FoilParams) -> tuple[float, float]:
    """Unit tangent of the section curve at the leading edge, pointing into the
    upper surface. For a round-nosed section this is the chord-normal rotated
    by the camber-line slope at x=0 (θ₀ = atan(2m/p)); both surface splines are
    built with this exact tangent, which pins G1 continuity at the LE vertex.
    """
    if foil.family is FoilFamily.CAMBERED and foil.camber_ratio > 0.0:
        theta0 = float(np.arctan(2.0 * foil.camber_ratio / foil.camber_position))
        return (-float(np.sin(theta0)), float(np.cos(theta0)))
    return (0.0, 1.0)


def section_properties(upper: np.ndarray, lower: np.ndarray) -> dict[str, float]:
    """Analytic cross-check values: max thickness and its chordwise station."""
    # Interpolate lower onto upper x for a common grid (families share x except
    # CAMBERED, where the perpendicular offset shifts x slightly).
    xs = upper[:, 0]
    lo = np.interp(xs, lower[:, 0], lower[:, 1])
    thick = upper[:, 1] - lo
    i = int(np.argmax(thick))
    return {"max_thickness": float(thick[i]), "x_at_max": float(xs[i])}
