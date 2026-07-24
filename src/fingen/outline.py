"""Planform outline: Bézier leading/trailing edges + elliptical tip lobe →
chord schedule (docs/PHYSICS.md §3).

Both edges are degree-7 Bézier curves in the (x, z) plane — x streamwise,
z spanwise — meeting at the construction tip point (depth·tan(sweep), depth).
The visible tip is NOT that point: commercial fins end in a rounded lobe, so
the chord schedule applies an elliptical rounding above the span height where
the chord equals the tip width — c(z) is multiplied by √(1−u²), with the lobe
centerline following the outline's own mean line (i.e. the rake direction).
This closes the planform with a round, rake-following tip that is tangent to
the edges below it, and shrinks the loft's closing cap to a sub-mm hole.

Control polygons stay monotone in z with single-bump x perturbations, so the
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
_CTRL_Z = np.array([0.10, 0.26, 0.44, 0.62, 0.80, 0.92])
# le_fullness blends the LE from the straight base→tip chord toward the
# vertical through the base corner (plus a small absolute forward bow), which
# is how commercial templates carry area low on the fin [FCS26].
_LE_W = np.array([1.45, 1.35, 1.15, 0.85, 0.45, 0.20])
_LE_BOW = 0.05  # absolute forward bow so zero-sweep fins still gain area
# te_shape > 0 blends the TE toward the vertical through the base TE corner
# (convex, keel-like); te_shape < 0 pulls it toward the LE (concave cutaway,
# the common commercial look) with the cut biased to the mid-upper span, where
# real templates carve away area under the overhanging tip.
_TE_CONVEX_W = np.array([1.45, 1.35, 1.2, 0.95, 0.55, 0.2])
_TE_CONCAVE_W = np.array([0.1, 0.3, 0.5, 0.6, 0.5, 0.3])
_TE_CONCAVE_AMPL = 0.35  # fraction of base at te_shape = -1, weight 1

_DENSE = 600  # samples per edge for the z → x interpolants
_DENSITY_CAP = 6.0  # max station-density boost, keeps the tip from hogging all


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

    le_line = zs * (x_tip / d)
    f_le = outline.le_fullness
    le_x = le_line * (1.0 - f_le * _LE_W) - f_le * _LE_BOW * b * _LE_W
    le = np.vstack(([0.0, 0.0], np.column_stack((le_x, zs)), tip))

    te_line = b + zs * ((x_tip - b) / d)
    convex = max(outline.te_shape, 0.0)
    concave = max(-outline.te_shape, 0.0)
    te_x = (te_line + convex * _TE_CONVEX_W * (b - te_line)
            - concave * _TE_CONCAVE_AMPL * _TE_CONCAVE_W * b)
    te = np.vstack(([b, 0.0], np.column_stack((te_x, zs)), tip))
    return le, te


def _edge_interpolants(outline: OutlineParams) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Dense (z, x_le, x_te) samples on a common z grid, before tip rounding."""
    le, te = control_points(outline)
    u = np.linspace(0.0, 1.0, _DENSE)
    le_pts, te_pts = _bezier(le, u), _bezier(te, u)
    # z(u) is monotone (control z are monotone), so z → x is well-defined.
    z = np.linspace(0.0, outline.depth, _DENSE)
    x_le = np.interp(z, le_pts[:, 1], le_pts[:, 0])
    x_te = np.interp(z, te_pts[:, 1], te_pts[:, 0])
    return z, x_le, x_te


def planform(outline: OutlineParams) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Dense (z, x_le, chord) of the FINAL planform, tip rounding applied.

    Raises ValueError if the edges cross (negative chord) below the tip
    region — geometrically impossible outlines fail fast, before OCCT.
    """
    z, x_le, x_te = _edge_interpolants(outline)
    chord = x_te - x_le

    body = z < 0.9 * outline.depth
    if np.any(chord[body] <= 0.0):
        z_bad = float(z[body][np.argmax(chord[body] <= 0.0)])
        raise ValueError(
            f"outline edges cross at z ≈ {z_bad:.1f} mm (negative chord); "
            "raise te_shape/base or reduce sweep")

    # Elliptical tip lobe: above z_w (where the chord reaches the tip width)
    # scale the chord by √(1−u²). C1 at z_w, vertical tangent at the apex —
    # a round tip whose centerline keeps following the outline's mean line.
    w = outline.tip_width_ratio * outline.base
    wide = np.nonzero(chord >= w)[0]
    z_w = float(z[wide[-1]]) if len(wide) else 0.0
    center = x_le + 0.5 * chord
    u_tip = np.clip((z - z_w) / max(outline.depth - z_w, 1e-9), 0.0, 1.0)
    rounded = chord * np.sqrt(np.clip(1.0 - u_tip**2, 0.0, None))
    chord = np.where(z > z_w, rounded, chord)
    x_le = np.where(z > z_w, center - 0.5 * chord, x_le)
    return z, x_le, chord


def chord_schedule(outline: OutlineParams, settings: GenSettings = DEFAULT_SETTINGS,
                   tip_chord_min: float = 3.0) -> list[Station]:
    """Sample loft stations over the rounded planform.

    Stations are distributed by chord variation (density ∝ 1 + |dc/dz|/mean,
    capped) — pure end-clustering under-samples wherever the chord changes
    fastest, letting the spanwise B-spline skin oscillate between stations.
    They stop where the chord reaches tip_chord_min; the loft closes the
    remaining sub-mm tip with a vertex cap.
    """
    z, x_le, chord = planform(outline)

    wide = np.nonzero(chord >= tip_chord_min)[0]
    if len(wide) == 0:
        raise ValueError("tip_chord_min exceeds the maximum chord of this outline")
    z_last = float(z[wide[-1]])

    zs = np.linspace(0.0, z_last, 400)
    cd = np.interp(zs, z, chord)
    grad = np.abs(np.gradient(cd, zs))
    density = 1.0 + np.minimum(grad / max(float(np.mean(grad)), 1e-9), _DENSITY_CAP)
    mu = np.concatenate(([0.0], np.cumsum(0.5 * (density[1:] + density[:-1]) * np.diff(zs))))
    mu /= mu[-1]
    zi = np.interp(np.linspace(0.0, 1.0, settings.n_stations), mu, zs)
    zi[0], zi[-1] = 0.0, z_last

    return [Station(z=float(v),
                    x_le=float(np.interp(v, z, x_le)),
                    chord=float(np.interp(v, z, chord))) for v in zi]


def tip_point(outline: OutlineParams) -> tuple[float, float]:
    """The construction tip point (x, z) — the lobe centerline's endpoint."""
    return (outline.depth * math.tan(math.radians(outline.sweep)), outline.depth)


def metrics(outline: OutlineParams) -> OutlineMetrics:
    """Derived planform quantities (tip rounding included)."""
    z, _, chord = planform(outline)
    area = float(np.trapezoid(chord, z))
    x_tip, d = tip_point(outline)
    return OutlineMetrics(
        area=area,
        aspect_ratio=outline.depth**2 / area,
        sweep=math.degrees(math.atan2(x_tip, d)),
    )
