"""Tier-0 hydrodynamic model (docs/PHYSICS.md §6): fast analytic estimates.

Lift-curve slope via DATCOM §4.1.3.2 [DAT78] with the board modeled as a
partial reflection plane [Hem28, Hoe75]; induced drag via lifting-line
[Pra21, Osw33]; stall margin against the measured fin stall band [BW04].
These are the instant numbers behind the web UI and the reference line every
CFD result gets compared against — seconds vs hours, honest about being a
first-order model.

SI units here (m, m/s, N), converting from the geometry's mm internally.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from fingen.outline import metrics, planform
from fingen.params import FinParams

RHO_SEAWATER = 1025.0  # kg/m³
NU_SEAWATER = 1.05e-6  # m²/s

# Board-as-end-plate effectiveness: AR_eff = k · AR_geometric. A full mirror
# doubles AR; the board is finite/curved/moving, so k < 2 [Hem28, Hoe75].
REFLECTION_FACTOR = 1.7
# Measured lift-curve break of the reference fin: α ≈ 12–14° [BW04].
STALL_ALPHA_DEG = 12.0
SPAN_EFFICIENCY = 0.90  # e for fin-like tapered planforms (CFD will calibrate)
SECTION_SLOPE = 2.0 * math.pi  # a0 per radian; thin sections at fin Re [SK81]


@dataclass(frozen=True)
class HydroEstimate:
    """First-order performance numbers for one fin at one operating point."""

    aspect_ratio_eff: float
    lift_slope: float  # dCL/dα per radian [DAT78]
    cl: float  # at the given leeway angle
    lift_n: float  # side force, N
    cdi: float  # induced drag coefficient
    drag_induced_n: float
    stall_margin_deg: float  # distance to the [BW04] lift-curve break
    reynolds: float  # at mean chord


def half_chord_sweep(fin: FinParams) -> float:
    """Half-chord-line sweep angle in radians (DATCOM's Λ_c/2)."""
    z, x_le, chord = planform(fin.outline)
    live = chord > 1.0
    x_half = x_le[live] + 0.5 * chord[live]
    dz = z[live][-1] - z[live][0]
    return math.atan2(float(x_half[-1] - x_half[0]), float(dz))


def lift_curve_slope(fin: FinParams) -> tuple[float, float]:
    """(CLα per radian, effective AR) — DATCOM §4.1.3.2, incompressible
    [DAT78]. Reduces to Helmbold at Λ=0 [And17] and to πAR/2 as AR→0 [Jon46].
    """
    m = metrics(fin.outline)
    ar_eff = REFLECTION_FACTOR * m.aspect_ratio
    kappa = SECTION_SLOPE / (2.0 * math.pi)
    tan_l = math.tan(half_chord_sweep(fin))
    slope = (2.0 * math.pi * ar_eff
             / (2.0 + math.sqrt((ar_eff / kappa) ** 2 * (1.0 + tan_l**2) + 4.0)))
    return slope, ar_eff


def estimate(fin: FinParams, speed: float, leeway_deg: float) -> HydroEstimate:
    """Point estimate at board speed [m/s] and leeway (angle of attack) [deg]."""
    m = metrics(fin.outline)
    area_m2 = m.area * 1e-6
    mean_chord_m = (m.area / fin.outline.depth) * 1e-3
    slope, ar_eff = lift_curve_slope(fin)
    alpha = math.radians(leeway_deg)
    cl = slope * alpha
    q = 0.5 * RHO_SEAWATER * speed**2
    cdi = cl**2 / (math.pi * SPAN_EFFICIENCY * ar_eff)
    return HydroEstimate(
        aspect_ratio_eff=ar_eff,
        lift_slope=slope,
        cl=cl,
        lift_n=q * area_m2 * cl,
        cdi=cdi,
        drag_induced_n=q * area_m2 * cdi,
        stall_margin_deg=STALL_ALPHA_DEG - leeway_deg,
        reynolds=speed * mean_chord_m / NU_SEAWATER,
    )
