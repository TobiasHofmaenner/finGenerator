"""Planform outline: Bézier leading/trailing edges + elliptical tip lobe →
chord schedule (docs/PHYSICS.md §3).

Both edges are degree-7 Bézier curves in the (x, z) plane — x streamwise,
z spanwise — meeting at the construction tip point (depth·tan(sweep), depth).
The visible tip is NOT that point: commercial fins end in a rounded lobe, so
the chord schedule applies an elliptical rounding above the span height where
the chord equals the tip width — c(z) is multiplied by √(1−u²), with the lobe
centerline following the outline's own mean line (i.e. the rake direction).
This closes the planform with a round, rake-following tip that is tangent to
the edges below it; the loft ends at the cap chord and closes with that last
section's tiny planar face (a vertex cap on the dome would be a degenerately
flat cone).

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
# TEMPLATE-PRIOR CALIBRATION (level 1): the weight vectors below define how
# the six sliders map onto control polygons. They are calibrated so defaults
# resemble known-rideable commercial templates — an empirical prior, NOT a
# physics statement (the elliptic-deviation metric quantifies the cost: the
# default concave TE sits ~0.08 further from minimum-induced-drag loading
# than a straight TE). The optimizer is not bound by them: le_dx/te_dx
# offsets (level 2) span the full degree-7 Bézier family.
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
# Parabolic sagitta 4t(1-t) at the control fractions: edge curvature is the
# SECOND derivative of the pull profile, so a linearly-increasing pull just
# re-angles a straight line (the observed straight-then-bend TE) — constant
# curvature needs a parabolic pull, i.e. a circular-arc-like cutaway that
# starts curving right at the base and hands over to the tip lobe.
_TE_CONCAVE_W = np.array([0.36, 0.77, 0.99, 0.94, 0.64, 0.29])
_TE_CONCAVE_AMPL = 0.5  # fraction of base at te_shape = -1, weight 1
_LE_LOBE_SHARE = 0.35  # LE's share of the tip lobe's narrowing; the TE absorbs
# the rest — keeps the LE on its own strictly convex Bezier (no depression
# before the top radius) and spreads the TE's concave approach over the lobe

_DENSE = 600  # samples per edge for the z → x interpolants
_DENSITY_CAP = 4.0  # max station-density boost for body stations


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
    elliptic_deviation: float  # RMS distance of c(z) from the same-area
    # elliptic distribution / mean chord — first-order proxy for distance
    # from minimum-induced-drag loading [Pra21]; a VLM number replaces it
    # in the hydro module. Attach this to every shape tweak.


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

    te_line = b + zs * ((x_tip - b) / d)
    convex = max(outline.te_shape, 0.0)
    concave = max(-outline.te_shape, 0.0)
    te_x = (te_line + convex * _TE_CONVEX_W * (b - te_line)
            - concave * _TE_CONCAVE_AMPL * _TE_CONCAVE_W * b)
    # Level-1 guarantee: sliders alone always yield a valid outline — extreme
    # te_shape saturates against the LE polygon instead of crossing it. The
    # saturation is smooth (softplus): a hard max puts a C0 kink in the
    # control polygon that the loft skin amplifies into a local bulge.
    k = 0.04 * b
    gap = te_x - (le_x + 0.12 * b)
    te_x = le_x + 0.12 * b + k * np.logaddexp(0.0, gap / k)
    # Level-2 optimizer offsets, applied after the clamp: full Bézier freedom,
    # backstopped by planform()'s edge-crossing rejection.
    le_x = le_x + np.asarray(outline.le_dx)
    te_x = te_x + np.asarray(outline.te_dx)
    le = np.vstack(([0.0, 0.0], np.column_stack((le_x, zs)), tip))
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
    z, x_le, chord, _ = _planform_ex(outline)
    return z, x_le, chord


def _planform_ex(outline: OutlineParams) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """planform() plus the lobe start height z_w (internal)."""
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
    # The lobe must have real vertical extent: if the raw edges only narrow to
    # the tip width in the last few mm (moderate sweeps), a chord-triggered
    # start squashes the rounding into invisibility — so start no higher than
    # 0.55 lobe-widths below the apex (clamped for squat outlines).
    z_w = min(z_w, max(outline.depth - 1.0 * w, 0.3 * outline.depth))
    u_tip = np.clip((z - z_w) / max(outline.depth - z_w, 1e-9), 0.0, 1.0)
    # Blend the raw (point-converging) chord into a full dome of the
    # lobe-entry width: (1−u²)^0.4 holds width longer than a pure ellipse
    # (√), then still turns with a horizontal tangent (a real radius) at the
    # apex; the smoothstep keeps C1 at lobe entry. Multiplying raw × dome
    # would still taper to a tangent point.
    dome = float(np.interp(z_w, z, chord)) * np.clip(1.0 - u_tip**2, 0.0, None) ** 0.4
    blend = u_tip**2 * (3.0 - 2.0 * u_tip)
    rounded = chord * (1.0 - blend) + dome * blend
    # Asymmetric narrowing: centering the lobe on the mean line drags the LE
    # into a concave dip below the top radius; instead the LE keeps only a
    # small share of the narrowing and the TE absorbs the rest.
    shrink = chord - rounded
    x_le = np.where(z > z_w, x_le + _LE_LOBE_SHARE * shrink, x_le)
    chord = np.where(z > z_w, rounded, chord)
    return z, x_le, chord, z_w


def chord_schedule(outline: OutlineParams, settings: GenSettings = DEFAULT_SETTINGS,
                   tip_chord_min: float = 3.0,
                   extra_z: list[float] | None = None) -> list[Station]:
    """Sample loft stations over the rounded planform.

    Body stations are distributed by chord variation (density ∝ 1 + |dc/dz|,
    capped) — pure end-clustering under-samples wherever the chord changes
    fastest, letting the spanwise B-spline skin oscillate between stations.
    Lobe stations sit at uniform ellipse angles (|dc/dz| diverges at the dome
    apex, so a gradient measure would pile everything into the last mm), and
    the final station is solved exactly at tip_chord_min.

    extra_z injects additional exact stations (groove edges/centers): the
    spanwise skin can only follow thickness features that the station set
    resolves. Values outside (0, z_cut) are dropped; near-duplicates merged.
    """
    z, x_le, chord, z_w = _planform_ex(outline)

    # The cap must stay well inside the tip lobe, or narrow-lobed small fins
    # get truncated below the lobe and lose real span (found by the sweep).
    # 0.45·width keeps the cut on the dome (≤ ~11% of lobe height lost);
    # the 0.8 mm floor keeps OCCT away from degenerate closures.
    w = outline.tip_width_ratio * outline.base
    tip_chord_min = max(0.8, min(tip_chord_min, 0.45 * w))

    if float(np.max(chord)) < tip_chord_min:
        raise ValueError("tip_chord_min exceeds the maximum chord of this outline")

    # Exact cap crossing: in the lobe the chord decreases monotonically, so
    # invert it to find where it reaches tip_chord_min (no grid quantization).
    lobe_mask = z >= z_w
    z_lobe, c_lobe = z[lobe_mask], chord[lobe_mask]
    if c_lobe[-1] < tip_chord_min <= c_lobe[0]:
        z_cut = float(np.interp(-tip_chord_min, -c_lobe, z_lobe))
    else:
        # The chord dips below the printable minimum before the lobe: the
        # planform has a sub-mm waist (a nearly severed tip) — a degenerate
        # design, rejected cleanly rather than silently truncated.
        raise ValueError(
            "planform waist pinches below the printable minimum; reduce the "
            "te_shape cutaway or increase tip_width_ratio/base")

    # Needle-tip guard, aligned with the checker's span-truncation bound: if
    # cutting at the printable minimum loses meaningful span, the tip region
    # is thinner than printable over a real distance — a degenerate design.
    if outline.depth - z_cut > max(1.2, 0.012 * outline.depth):
        raise ValueError(
            f"tip region is thinner than the printable minimum over the last "
            f"{outline.depth - z_cut:.1f} mm of span; increase tip_width_ratio "
            "or soften the te_shape cutaway")

    # Body stations by (capped) chord-variation measure; lobe stations at
    # uniform ellipse angles — |dc/dz| diverges at the dome apex, so a pure
    # gradient measure would pile every station into the last millimetres.
    # Lobe stations scale with the lobe's share of the span — a fixed count
    # starves the body under narrow lobes exactly where the raw outline still
    # converges steeply (found by the corner tests).
    if z_cut > z_w:
        # Proportional to the lobe's share of the span (a squat keel's dome
        # can be most of the fin) — but the body keeps a healthy floor: with
        # too few body stations the base-region skin sags below z=0 on squat
        # fins (found by the corner tests at depth 60).
        share = (z_cut - z_w) / max(z_cut, 1e-9)
        body_floor = max(6, settings.n_stations // 3)
        n_lobe = int(np.clip(round(settings.n_stations * 1.2 * share), 2,
                             max(settings.n_stations - body_floor, 2)))
    else:
        n_lobe = 0
    n_body = max(settings.n_stations - n_lobe, 4)

    zs = np.linspace(0.0, z_w, 400)
    cd = np.interp(zs, z, chord)
    grad = np.abs(np.gradient(cd, zs))
    density = 1.0 + np.minimum(grad / max(float(np.mean(grad)), 1e-9), _DENSITY_CAP)
    mu = np.concatenate(([0.0], np.cumsum(0.5 * (density[1:] + density[:-1]) * np.diff(zs))))
    mu /= mu[-1]
    zi_body = np.interp(np.linspace(0.0, 1.0, n_body), mu, zs)
    zi_body[0], zi_body[-1] = 0.0, z_w

    if n_lobe:
        span = max(outline.depth - z_w, 1e-9)
        theta_cut = math.asin(min((z_cut - z_w) / span, 1.0))
        theta = theta_cut * np.arange(1, n_lobe + 1) / n_lobe
        zi = np.concatenate((zi_body, z_w + span * np.sin(theta)))
    else:
        zi = zi_body

    if extra_z:
        # Stay clear of the exact base (z=0) and cap stations — the merge
        # below keeps the last value of a close pair, and those two must
        # survive exactly.
        keep = [v for v in extra_z if 0.5 < v < z_cut - 0.05]
        zi = np.sort(np.concatenate((zi, np.array(keep, dtype=float))))
        # Merge near-duplicates (keep the later value so the exact cap
        # station survives): sub-0.05 mm station pairs make OCCT's spanwise
        # fit ill-conditioned without adding any resolvable geometry.
        zi = zi[np.append(np.diff(zi) > 0.05, True)]

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
    live = chord > 0.5
    span = float(z[live][-1]) if np.any(live) else outline.depth
    c_ell = (4.0 * area / (np.pi * span)) * np.sqrt(
        np.clip(1.0 - (z / span) ** 2, 0.0, None))
    deviation = float(np.sqrt(np.mean((chord - c_ell) ** 2)) / np.mean(chord[live]))
    return OutlineMetrics(
        area=area,
        aspect_ratio=outline.depth**2 / area,
        sweep=math.degrees(math.atan2(x_tip, d)),
        elliptic_deviation=deviation,
    )
