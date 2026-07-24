"""Foil section generation: 2D hydrofoil profiles (docs/PHYSICS.md §4).

NACA 4-digit construction [Jac33, AvD59]: analytic thickness distribution and
two-parabola camber line, thickness applied perpendicular to the camber line.
Families (docs/FIN-PRIMER.md §4): SYMMETRIC (50/50), CAMBERED (m, p explicit),
FLAT_INSIDE (flat face at y=0, full section shape outboard — the half-section
construction of the measured baseline fin [BW04]).

All returned coordinates are in mm. Sections are generated in local chord
coordinates: leading edge at x=0, trailing edge at x=chord, thickness along y.
The flat face of FLAT_INSIDE lies exactly in the y=0 plane at every station,
so the assembled blade has a planar inner face (printable flat on the bed).
"""

from __future__ import annotations

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


def section_points(
    foil: FoilParams,
    chord: float,
    thickness_ratio: float | None = None,
    n_points: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (upper, lower) surface point arrays for one section, in mm.

    Both arrays run leading edge → trailing edge and share the exact leading
    edge point; the trailing edge is truncated to foil.te_thickness and left
    open (the caller closes it with a straight TE segment).

    thickness_ratio overrides foil.thickness_ratio (spanwise schedules).
    """
    if chord <= 0.0:
        raise ValueError(f"chord must be positive, got {chord}")
    t = foil.thickness_ratio if thickness_ratio is None else thickness_ratio
    n = max(n_points // 2, 20)
    x = _cosine_x(n)
    yt = _thickness(x, t)

    if foil.family is FoilFamily.FLAT_INSIDE:
        # Flat face at y=0; the full section thickness goes outboard: the outer
        # surface is the doubled thickness envelope (upper half of a NACA
        # section of parameter 2t), so max total thickness = t·chord [BW04].
        upper = np.column_stack((x, 2.0 * yt))
        lower = np.column_stack((x, np.zeros_like(x)))
    elif foil.family is FoilFamily.CAMBERED and foil.camber_ratio > 0.0:
        yc, dyc = _camber(x, foil.camber_ratio, foil.camber_position)
        theta = np.arctan(dyc)
        upper = np.column_stack((x - yt * np.sin(theta), yc + yt * np.cos(theta)))
        lower = np.column_stack((x + yt * np.sin(theta), yc - yt * np.cos(theta)))
    else:  # SYMMETRIC (or CAMBERED with zero camber)
        upper = np.column_stack((x, yt))
        lower = np.column_stack((x, -yt))

    # Share one exact leading-edge point so the section wire closes cleanly.
    upper[0] = (0.0, 0.0) if foil.family is not FoilFamily.CAMBERED else upper[0]
    lower[0] = upper[0]

    upper *= chord
    lower *= chord

    # Printability: widen the trailing edge to te_thickness with a linear wedge
    # y ± Δ·(x/c)/2 (standard blunt-TE modification), applied only if needed.
    gap = upper[-1, 1] - lower[-1, 1]
    if gap < foil.te_thickness:
        add = 0.5 * (foil.te_thickness - gap)
        upper[:, 1] += add * (upper[:, 0] / chord)
        lower[:, 1] -= add * (lower[:, 0] / chord)

    return upper, lower


def section_properties(upper: np.ndarray, lower: np.ndarray) -> dict[str, float]:
    """Analytic cross-check values: max thickness and its chordwise station."""
    # Interpolate lower onto upper x for a common grid (families share x except
    # CAMBERED, where the perpendicular offset shifts x slightly).
    xs = upper[:, 0]
    lo = np.interp(xs, lower[:, 0], lower[:, 1])
    thick = upper[:, 1] - lo
    i = int(np.argmax(thick))
    return {"max_thickness": float(thick[i]), "x_at_max": float(xs[i])}
