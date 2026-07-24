"""Planform outline: Bézier leading/trailing edges → chord schedule
(docs/PHYSICS.md §3).

Both edges are degree-5 Bézier curves in the (x, z) plane — x streamwise,
z spanwise — sharing the tip point at (depth·tan(sweep), depth), so the chord
closes to zero at the tip. User parameters generate the control points; the
control polygons stay monotone in z with single-bump x perturbations, so the
variation-diminishing property guarantees fair, oscillation-free edges for any
parameter combination in range [Far02, PT97]. Degree 7 stays in the low-order
band demonstrated adequate for foil-grade curves [Jai17] while giving the
control polygon enough authority near the base to reach full templates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from fingen.params import DEFAULT_SETTINGS, GenSettings, OutlineParams

# Spanwise fractions of the six interior control points (P1..P6 of degree 7).
_CTRL_Z = np.array([0.10, 0.26, 0.44, 0.62, 0.85, 0.94])
# Fullness blends each edge from the straight base→tip chord (fullness 0)
# toward a "boxy" profile whose lower controls hug the vertical through the
# base corner (fullness 1) — commercial templates carry their area this way
# (FCS mean chord ≈ 78% of base [FCS26]; weights tuned so the default fullness
# reproduces the published area, enforced by the anchor test).
_LE_W = np.array([1.45, 1.35, 1.15, 0.85, 0.45, 0.20])
_LE_BOW = 0.05  # small absolute forward bow so zero-sweep fins still gain area
_TE_W = np.array([1.45, 1.35, 1.2, 0.95, 0.0, 0.0])  # overshoot offsets Bézier dilution

_DENSE = 600  # samples per edge for the z → x interpolants


@dataclass(frozen=True)
class Station:
    """One spanwise loft station."""

    z: float
    x_le: float
    chord: float


@dataclass(frozen=True)
class OutlineMetrics:
    """Derived (reported, never input) planform quantities."""

    area: float  # mm²
    aspect_ratio: float  # depth² / area (geometric, one fin, no reflection)
    sweep: float  # recomputed base-LE → tip angle, degrees


def _bezier(ctrl: np.ndarray, u: np.ndarray) -> np.ndarray:
    n = len(ctrl) - 1
    out = np.zeros((len(u), ctrl.shape[1]))
    for i, point in enumerate(ctrl):
        out += math.comb(n, i) * (u**i * (1.0 - u) ** (n - i))[:, None] * point
    return out


def control_points(outline: OutlineParams) -> tuple[np.ndarray, np.ndarray]:
    """Generate (LE, TE) Bézier control points from the outline parameters."""
    d, b = outline.depth, outline.base
    x_tip = d * math.tan(math.radians(outline.sweep))
    tip = np.array([x_tip, d])
    zs = _CTRL_Z * d

    # Leading edge: blend from the straight (0,0)→tip chord toward the
    # vertical through the base LE corner, plus a small absolute forward bow.
    le_line = zs * (x_tip / d)
    f_le = outline.le_fullness
    le_x = le_line * (1.0 - f_le * _LE_W) - f_le * _LE_BOW * b * _LE_W
    le = np.vstack(([0.0, 0.0], np.column_stack((le_x, zs)), tip))

    # Trailing edge: blend from the straight (base,0)→tip chord toward the
    # vertical through the base TE corner (x = base).
    te_line = b + zs * ((x_tip - b) / d)
    f_te = outline.te_fullness
    te_x = te_line + f_te * _TE_W * (b - te_line)
    # Tip-region fullness: pin the control points at 85%/94% depth so the
    # chord near ~85% depth tracks tip_chord_ratio · base, tapering above.
    te_x[4] = le_x[4] + outline.tip_chord_ratio * b
    te_x[5] = le_x[5] + 0.45 * outline.tip_chord_ratio * b
    te = np.vstack(([b, 0.0], np.column_stack((te_x, zs)), tip))
    return le, te


def _edge_interpolants(outline: OutlineParams) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Dense (z, x_le, x_te) samples on a common z grid."""
    le, te = control_points(outline)
    u = np.linspace(0.0, 1.0, _DENSE)
    le_pts, te_pts = _bezier(le, u), _bezier(te, u)
    # z(u) is monotone (control z are monotone), so z → x is well-defined.
    z = np.linspace(0.0, outline.depth, _DENSE)
    x_le = np.interp(z, le_pts[:, 1], le_pts[:, 0])
    x_te = np.interp(z, te_pts[:, 1], te_pts[:, 0])
    return z, x_le, x_te


def chord_schedule(outline: OutlineParams, settings: GenSettings = DEFAULT_SETTINGS,
                   tip_chord_min: float = 3.0) -> list[Station]:
    """Sample loft stations, cosine-clustered toward the tip.

    Stations stop where the chord reaches tip_chord_min; the loft closes the
    remaining tip region with a cap to the shared tip point.

    Raises ValueError if the edges cross (negative chord) anywhere below the
    tip region — geometrically impossible outlines fail fast, before OCCT.
    """
    z, x_le, x_te = _edge_interpolants(outline)
    chord = x_te - x_le

    body = z < 0.98 * outline.depth
    if np.any(chord[body] <= 0.0):
        z_bad = float(z[body][np.argmax(chord[body] <= 0.0)])
        raise ValueError(
            f"outline edges cross at z ≈ {z_bad:.1f} mm (negative chord); "
            "reduce te_fullness/sweep or increase base/tip_chord_ratio")

    # Last station: outermost z where chord ≥ tip_chord_min.
    wide = np.nonzero(chord >= tip_chord_min)[0]
    if len(wide) == 0:
        raise ValueError("tip_chord_min exceeds the maximum chord of this outline")
    z_last = float(z[wide[-1]])

    s = np.sin(0.5 * np.pi * np.linspace(0.0, 1.0, settings.n_stations))
    stations = []
    for zi in z_last * s:
        stations.append(Station(z=float(zi),
                                x_le=float(np.interp(zi, z, x_le)),
                                chord=float(np.interp(zi, z, chord))))
    return stations


def tip_point(outline: OutlineParams) -> tuple[float, float]:
    """The shared LE/TE tip point (x, z)."""
    return (outline.depth * math.tan(math.radians(outline.sweep)), outline.depth)


def metrics(outline: OutlineParams) -> OutlineMetrics:
    """Derived planform quantities for validation against published specs [FCS26]."""
    z, x_le, x_te = _edge_interpolants(outline)
    chord = np.clip(x_te - x_le, 0.0, None)
    area = float(np.trapezoid(chord, z))
    x_tip, d = tip_point(outline)
    return OutlineMetrics(
        area=area,
        aspect_ratio=outline.depth**2 / area,
        sweep=math.degrees(math.atan2(x_tip, d)),
    )
