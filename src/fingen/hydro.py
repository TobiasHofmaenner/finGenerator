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
# Measured lift-curve break of the AR≈3 reference fin: α ≈ 12–14° [BW04].
STALL_ALPHA_DEG = 12.0


def stall_alpha_deg(ar_eff: float) -> float:
    """Break angle vs effective AR: low-AR planforms break much later
    (vortex lift [Pol66, Tra23]; delta-wing data reach 25-35°). Heuristic
    anchored at the AR-3 measurement [BW04], pending CFD calibration."""
    return min(STALL_ALPHA_DEG + 8.0 * max(0.0, 2.5 - ar_eff), 30.0)
SPAN_EFFICIENCY = 0.90  # e for fin-like tapered planforms (CFD will calibrate)
SECTION_SLOPE = 2.0 * math.pi  # a0 per radian; thin sections at fin Re [SK81]

# --- Post-knee stall-drag term (task #22) ---------------------------------
# The constant-efficiency induced-drag quadratic C_Di = C_L²/(π·e·AR) has NO
# separation/stall-drag term, so tier-0 badly UNDER-predicts drag once the
# section loads past ~0.7·C_L,max: the 2026 transition-tier CFD shows C_D
# running 1.3–4.5× the quadratic above C_L ≈ 0.7 (needle 1.3–3×, thin-foil
# section 1.8–4.5×) [bench/freerun-needle/adjudication.md verdict (b);
# bench/freerun-thinfoil/section-polar.md §"task #22"]. Above a knee at
# C_L,knee = KNEE_FRACTION·C_L,max we add a quadratic rise
#     ΔC_D,stall = K_STALL·max(0, C_L − C_L,knee)²
# which is C1-continuous at the knee by construction (value AND slope → 0 as
# C_L → C_L,knee⁺), so it grafts smoothly onto the attached polar.
KNEE_FRACTION = 0.7  # stall-drag onset at 0.7·C_L,max, per the CFD verdicts
# ── K_STALL derivation (fit ONCE; do not re-derive) ──────────────────────
# Least-squares through the knee against the needle transition-CFD polar
# (bench/freerun-needle/needle-polar.json), the 5 supra-knee points α = 8–16°
# (the 1.3–3× divergence). For each point the residual over the attached model
#   r_i = C_D,cfd,i − (CD0_CAL·cd0_Hoerner + C_L,cfd,i²/(π·e·AR_eff))
# is regressed with no intercept on x_i = max(0, C_L,cfd,i − C_L,knee)²:
#   K_STALL = Σ(r_i·x_i) / Σ(x_i²) = 0.580
# using the needle's documented tier-0 constants (adjudication.md): the k=1.7
# optimizer-basis slope 3.670/rad, AR_eff = 1.7·2.66 = 4.522, break 12°,
# Hoerner cd0 0.01334, e = 0.90 → C_L,max = 0.7686, C_L,knee = 0.538.
# Fit residuals (new model / CFD): α8 1.17, α10 1.25, α12 1.25, α14 1.05,
# α16 0.75 (α16 is capped/unconverged deep stall — a CFD lower bound, so the
# −25% there is expected). All fit points land inside ±30%.
# Cross-checks (same K, full-model/CFD ratio): bw04 fin (AR_geo 1.51,
# AR_eff 2.6) over-predicts ~1.5–1.7× at its near-stall α=8 point — needle-K is
# mildly strong for a gentler mid-AR stall, but scoring caps C_L,work at
# 0.95·C_L,max so the term adds only ~1×cd0 of drag; zarruk NACA0009 hydrofoil
# (AR 3.33 semi-span / ~6.7 mirrored, AR_eff ≥ 3.3) UNDER-predicts (ratio
# 0.30–0.61 at α 8–10°, Re 0.6e6) — needle-K is conservative for that hard
# stall. The needle calibration thus sits centrally between the two bracketing
# benches. NOTE (FINDING 1): all three benches sit at AR_eff ≥ 2.5, where the
# `stall_cl_knee` angle cap (min(stall_alpha_deg, 12°)) is INERT — so the cap
# leaves every bench residual UNCHANGED and needs no AR-dependent K. Zarruk's
# under-prediction is orthogonal to the cap (its supra-knee C_L sit below even
# the 12° knee, and it truly breaks near 10.5°): the model is conservative
# there, never over-predicting, which is the direction the cap protects.
K_STALL = 0.580  # ΔC_D per (C_L − C_L,knee)²; see derivation above


def stall_cl_knee(slope: float, ar_eff: float) -> float:
    """C_L at the stall-DRAG knee: KNEE_FRACTION·slope·α_knee, with the knee
    ANGLE α_knee CAPPED at the measured AR-3 base break STALL_ALPHA_DEG (12°).

    DRAG knee ≠ LIFT break (task #22, FINDING 1). The lift break extends at low
    AR — vortex lift keeps a delta-wing planform generating lift to 25–35°
    (`stall_alpha_deg`), and that late break is real, so the lift/hold/
    forgiveness side keeps using the extended angle untouched. But vortex lift
    is HIGH-drag: the separation-drag rise cannot start LATER than the base
    angle merely because the foil keeps lifting. Pinning the drag knee to the
    un-extended 12° base lets a low-AR blade keep its late lift break while
    paying stall drag from the standard knee. The Zarruk NACA0009 bench
    confirms the direction — a genuinely hard-stalling foil UNDER-predicts its
    excess drag, never over-predicts, so a LATER drag knee is unphysical.

    Above AR_eff 2.5 the cap is inert (stall_alpha_deg == 12 there), so every
    validated bench point (needle 4.52, bw04 2.6, Zarruk ≥3.3) is unchanged; it
    bites ONLY the sub-2.5-AR_eff planforms the uncapped knee handed a windfall
    (the AR-1.1 pancake attractor)."""
    knee_alpha_deg = min(stall_alpha_deg(ar_eff), STALL_ALPHA_DEG)
    return KNEE_FRACTION * slope * math.radians(knee_alpha_deg)


def stall_drag_cd(cl: float, slope: float, ar_eff: float) -> float:
    """Post-knee separation-drag coefficient ΔC_D = K_STALL·max(0, C_L−C_L,knee)²
    (task #22). Zero below the knee; C1-continuous across it (value and slope
    both vanish at the knee). Adds ON TOP of profile + induced drag."""
    excess = cl - stall_cl_knee(slope, ar_eff)
    return K_STALL * excess * excess if excess > 0.0 else 0.0


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
    a_break = stall_alpha_deg(ar_eff)
    return HydroEstimate(
        aspect_ratio_eff=ar_eff,
        lift_slope=slope,
        cl=cl,
        lift_n=q * area_m2 * cl,
        cdi=cdi,
        drag_induced_n=q * area_m2 * cdi,
        stall_margin_deg=a_break - leeway_deg,
        reynolds=speed * mean_chord_m / NU_SEAWATER,
    )
