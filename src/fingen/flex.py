"""Tier-0 flex model: cantilever bending + rake-induced twist (docs/PHYSICS.md §5b).

The blade is a tapered solid-section cantilever [GT97, Zar14]: Euler-Bernoulli
bending in the lateral (y) direction under a distributed side load, plus strip
torsion about the spanwise axis. Two mechanisms change the local incidence:

- **Rake coupling**: the bending slope θ(z), resolved along a swept elastic
  axis, tilts each streamwise section by Δα = −θ·sinΛ_e — washout on
  swept-back fins [BAH96]. An unswept axis produces exactly zero, matching
  the no-resolvable-twist measurement on the unswept metal foils of [Zar14].
- **Direct torsion**: the local center of pressure (≈ quarter chord) sits
  ahead of the elastic axis (taken as the section-centroid locus — the exact
  shear center of a solid thin section is slightly forward of it, a tier-1
  refinement), so the lift applies a nose-up distributed torque
  m = w·(x_ea − x_c/4), integrated with GJ [BAH96].

All properties are numeric over the station arrays (cumulative trapezoids):
milliseconds per evaluation, embeddable inside an optimizer loop, and the
reference line the CalculiX/FSI tier is compared against. The same solve
yields the Rayleigh wet natural frequency (structural mass + the 2D
flat-plate added mass πρ_w(c/2)² per unit span [BAH96]), a strip-theory
divergence speed (GJ torsional stiffness vs the q·c²·e·a aerodynamic
moment [BAH96]), and the bending-stress margin per station — the groove
band gets its own reported maximum, the tier-0 closure of the
critical-section note in docs/PHYSICS.md §4.

Validity limits: strip torsion constant J = (1/3)∫t³dx holds for SOLID THIN
sections (t/c ≤ 0.15 — the FoilParams ceiling). The pure wetted-span beam
reads consistently STIFF against 3D references — root warping, shear lag
and plate behavior are missing, and they grow with how stubby the blade is —
so bending compliance carries a single calibrated knockdown (see
ROOT_COMPLIANCE_SLOPE); torsion is left uncorrected (no torsional anchor
yet). CALIBRATION NOTE: with no explicit override, E now comes from the
material card — `get_card(material).e_mpa`, the datasheet ISO-178 X-Y bending
modulus (4744 MPa for pet-cf = Polymaker Fiberon PET-CF17 [FibPET26], the
user's filament), which is the correct span-bending stiffness of a flat-printed
blade (fingen.materials explains why flexural-X-Y, and that the datasheet is
the ANNEALED ceiling). Feed the measured effective modulus through `e_mpa`
once the load-cell bench rig supplies it. The 7000 MPa E_PLACEHOLDER_MPA below
is retained only as scripts/bench_intake.py's e_ratio anchor, not the default.

Geometry in mm like the rest of fingen; the solve converts to SI internally.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from fingen.foil import section_points
from fingen.hydro import RHO_SEAWATER, lift_curve_slope
from fingen.loft import _groove_thins, _thickness_at, groove_station_z
from fingen.materials import get_card
from fingen.outline import chord_schedule
from fingen.params import FinParams, GenSettings
from fingen.sizing import _MATERIAL_ALLOW_MPA

# Retained as bench_intake's e_ratio reference anchor only — the live flex
# default now reads get_card(material).e_mpa (see the CALIBRATION NOTE above).
E_PLACEHOLDER_MPA = 7000.0
POISSON = 0.35  # short-CF thermoplastics; G = E / (2(1+ν))
# Printed short-CF blade density [PETCF: 1.29 g/cm³], solid infill assumed.
RHO_PRINT = 1300.0  # kg/m³
# Local center of pressure at the quarter chord (thin-airfoil result; the
# fin's low AR pulls the *total* center aft, but strip torsion wants the
# sectional value) [BAH96].
X_CP_FRAC = 0.25
# 3D ROOT-COMPLIANCE CALIBRATION. Euler-Bernoulli on the wetted span misses
# root warping above the clamp, shear lag and plate behavior — all growing
# with root-chord/span. Bending compliance is scaled by
#     1 + ROOT_COMPLIANCE_SLOPE · (c_root / span),
# one slope calibrated on the two available 3D anchors: the measured [Zar14]
# Type I dimensionless deflection δ' = 0.204 (slender, c/s = 0.4, needs
# ×1.18 over the raw beam) and the CalculiX demo on the default side fin
# (stubby, c/s = 0.96, 1.19 mm at 74 N, needs ×1.51) — both land within a
# few percent with slope 0.55, and the [Zar14] wet frequency follows to −3%.
# A fit through exactly two anchors: treat the tests as regression pins; the
# FEM tier recalibrates per-geometry, the load-cell rig per-material.
ROOT_COMPLIANCE_SLOPE = 0.55
# Station resolution for the FinParams wrapper: beam double-integrals are
# converged well below the model error at 40 stations, still milliseconds.
_N_STATIONS = 40
_N_FOIL_POINTS = 80


@dataclass(frozen=True)
class SectionMech:
    """Numeric mechanical properties of one station's solid section (mm)."""

    area_mm2: float
    i_mm4: float  # bending inertia about the chordwise neutral axis
    j_mm4: float  # torsion constant (strip formula, solid thin section)
    x_c_mm: float  # chordwise area centroid, local (from the LE)
    y_max_mm: float  # extreme-fibre distance from the neutral axis


def section_mech(upper: np.ndarray, lower: np.ndarray) -> SectionMech:
    """Section properties from the actual foil polygon (thin-strip integration).

    Bending inertia about the chordwise neutral axis (the fin bends in y)
    with the neutral-axis offset resolved numerically — flat-inside and
    grooved sections are asymmetric, so ȳ ≠ 0 [GT97]. The torsion constant
    uses the solid-thin-section strip formula J = (1/3)∫t(x)³dx, valid for
    t/c ≤ 0.15 [BAH96, Roa01]; note this is NOT the polar moment, which
    grossly overestimates torsional stiffness of non-circular sections.
    """
    xs = upper[:, 0]
    y_up = upper[:, 1]
    y_lo = np.interp(xs, lower[:, 0], lower[:, 1])
    t = y_up - y_lo
    area = float(np.trapezoid(t, xs))
    x_c = float(np.trapezoid(xs * t, xs) / max(area, 1e-12))
    y_bar = float(np.trapezoid(0.5 * (y_up + y_lo) * t, xs) / max(area, 1e-12))
    i_xx = float(np.trapezoid(((y_up - y_bar) ** 3 - (y_lo - y_bar) ** 3) / 3.0, xs))
    j = float(np.trapezoid(t**3, xs) / 3.0)
    y_max = float(max(np.max(np.abs(y_up - y_bar)), np.max(np.abs(y_lo - y_bar))))
    return SectionMech(area, i_xx, j, x_c, y_max)


@dataclass(frozen=True)
class FlexReport:
    """Tier-0 flex answers for one blade at one operating point.

    twist_deg is the local incidence change Δα(z) (rake coupling + direct
    torsion); negative = washout. lift_knockdown is ΔCL/CL from that
    washout, closed with the hydro lift slope — negative = lift lost.
    stress_groove_mpa is None when the fin has no grooves.
    """

    z_mm: np.ndarray
    deflection_mm: np.ndarray
    twist_deg: np.ndarray
    tip_deflection_mm: float
    tip_twist_deg: float
    lift_knockdown: float  # ΔCL/CL, dimensionless fraction
    f_wet_hz: float  # Rayleigh wet fundamental (added mass included)
    divergence_speed_ms: float  # strip-theory torsional divergence [BAH96]
    i_root_mm4: float  # base-section bending inertia (validation handle)
    stress_root_mpa: float
    stress_max_mpa: float
    z_stress_max_mm: float  # station of the critical bending section
    stress_groove_mpa: float | None
    allow_mpa: float

    @property
    def stress_margin(self) -> float:
        """Allowable / worst-station bending stress (< 1 means overstressed)."""
        return self.allow_mpa / max(self.stress_max_mpa, 1e-12)


def _cumtrapz(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Cumulative trapezoid from x[0], same length as x (starts at 0)."""
    return np.concatenate(([0.0], np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(x))))


def flex_solve(z_mm: np.ndarray, chord_mm: np.ndarray, x_le_mm: np.ndarray,
               sections: Sequence[tuple[np.ndarray, np.ndarray]],
               e_mpa: float, force_n: float, speed: float, lift_slope: float, *,
               nu: float = POISSON,
               load: Callable[[np.ndarray], np.ndarray] | None = None,
               rho_struct: float = RHO_PRINT, rho_fluid: float = RHO_SEAWATER,
               allow_mpa: float = _MATERIAL_ALLOW_MPA["pet-cf"],
               groove_band_mm: tuple[float, float] | None = None) -> FlexReport:
    """Core solve on station arrays (root at z_mm[0], free tip at z_mm[-1]).

    sections are (upper, lower) polygons per station in local mm (the
    section_points convention). load(z_mm) overrides the spanwise shape of
    the lateral load (any positive scale — it is normalized so the total is
    force_n); the default w ∝ c(z) is the uniform-CL assumption. lift_slope
    is the 3D dCL/dα per radian (hydro's DATCOM value) used for the washout
    knockdown and the divergence strip estimate.
    """
    z_mm = np.asarray(z_mm, dtype=float)
    chord_mm = np.asarray(chord_mm, dtype=float)
    x_le_mm = np.asarray(x_le_mm, dtype=float)
    if not (len(z_mm) == len(chord_mm) == len(x_le_mm) == len(sections)):
        raise ValueError("z, chord, x_le and sections must have equal length")
    if len(z_mm) < 5:
        raise ValueError(f"need at least 5 stations, got {len(z_mm)}")
    if np.any(np.diff(z_mm) <= 0.0):
        raise ValueError("z stations must be strictly increasing (root to tip)")
    if force_n <= 0.0 or speed <= 0.0:
        raise ValueError(f"force_n {force_n} and speed {speed} must be positive")

    mech = [section_mech(u, lo) for u, lo in sections]
    z = z_mm * 1e-3
    chord = chord_mm * 1e-3
    span = float(z[-1] - z[0])
    area_m2 = np.array([m.area_mm2 for m in mech]) * 1e-6
    i_m4 = np.array([m.i_mm4 for m in mech]) * 1e-12
    j_m4 = np.array([m.j_mm4 for m in mech]) * 1e-12
    y_max = np.array([m.y_max_mm for m in mech]) * 1e-3
    x_ea = (x_le_mm + np.array([m.x_c_mm for m in mech])) * 1e-3
    x_cp = (x_le_mm + X_CP_FRAC * chord_mm) * 1e-3
    e_pa = e_mpa * 1e6
    # Effective bending stiffness: the 3D root-compliance knockdown (module
    # header) softens the beam; internal actions M, V stay equilibrium-exact.
    root_factor = 1.0 + ROOT_COMPLIANCE_SLOPE * float(chord[0] / span)
    ei = e_pa * i_m4 / root_factor
    gj = e_pa / (2.0 * (1.0 + nu)) * j_m4

    # Distributed lateral load, scaled so the resultant equals force_n.
    shape = np.asarray(load(z_mm), dtype=float) if load is not None else chord
    w = shape * (force_n / float(np.trapezoid(shape, z)))

    # Cantilever internal actions, integrated from the free tip (V, M, T all
    # vanish there by construction) [GT97].
    v = float(np.trapezoid(w, z)) - _cumtrapz(w, z)
    moment = float(np.trapezoid(v, z)) - _cumtrapz(v, z)
    theta = _cumtrapz(moment / ei, z)  # bending slope dδ/dz
    delta = _cumtrapz(theta, z)

    # Rake coupling: local elastic-axis sweep from the centroid locus. An
    # unswept axis gives sinΛ_e = 0 and therefore zero bend-induced twist.
    # The locus is smoothed by a chord-weighted cubic before differentiating:
    # inside the tip lobe the raw locus curls forward (the LE keeps only a
    # small share of the lobe narrowing — a planform-construction detail on
    # millimetre chords carrying no load), and a raw local gradient would let
    # that artifact dominate the reported tip twist through sinΛ_e.
    axis_fit = np.polynomial.Polynomial.fit(z, x_ea, 3, w=chord)
    lambda_e = np.arctan(axis_fit.deriv()(z))
    # Direct torsion: sectional lift at c/4, reacted at the elastic axis;
    # m > 0 (axis aft of the load) is nose-up, i.e. +Δα [BAH96].
    torque = float(np.trapezoid(w * (x_ea - x_cp), z)) - _cumtrapz(w * (x_ea - x_cp), z)
    dalpha = -theta * np.sin(lambda_e) + _cumtrapz(torque / gj, z)

    # Washout-corrected lift knockdown: ΔCL = a·∫Δα·c dz / S against the
    # rigid CL = F/(qS) — both share qS, so the ratio is load-independent
    # only through δ ∝ F; report at this operating point.
    s_ref = float(np.trapezoid(chord, z))
    q = 0.5 * rho_fluid * speed**2
    dcl = lift_slope * float(np.trapezoid(dalpha * chord, z)) / s_ref
    knockdown = dcl / (force_n / (q * s_ref))

    # Rayleigh quotient on the static bending shape: 2U = ∫M²/EI dz,
    # 2T = ω²∫μδ² dz with μ = structural + flat-plate added mass πρ_w(c/2)²
    # per unit span [BAH96] — the added mass dominates thin blades and is
    # what separates f_wet from the in-air tap test.
    mu = rho_struct * area_m2 + rho_fluid * math.pi * chord**2 / 4.0
    omega2 = float(np.trapezoid(moment**2 / ei, z) / np.trapezoid(mu * delta**2, z))
    f_wet = math.sqrt(omega2) / (2.0 * math.pi)

    # Torsional divergence, strip theory with the assumed fundamental mode
    # φ = sin(πz/2s): q_D = ∫GJφ'² / ∫a·c·e·φ² (e = ea−cp arm; c²·(e/c)
    # = c·e). Reduces to the classic (π/2s)²GJ/(c²e'a) uniform result
    # [BAH96]. Sweep is neglected — washout on swept-back fins raises the
    # true divergence speed, so this reads conservative for raked fins.
    psi = np.sin(0.5 * math.pi * (z - z[0]) / span)
    dpsi = 0.5 * math.pi / span * np.cos(0.5 * math.pi * (z - z[0]) / span)
    aero = float(np.trapezoid(lift_slope * chord * (x_ea - x_cp) * psi**2, z))
    if aero > 0.0:
        q_div = float(np.trapezoid(gj * dpsi**2, z)) / aero
        u_div = math.sqrt(2.0 * q_div / rho_fluid)
    else:
        u_div = math.inf  # elastic axis at/ahead of the cp: no divergence

    # Bending stress per station σ = M·y_max/I [GT97]; the critical section
    # of a grooved fin is usually inside the band (nearly the root moment
    # against a disproportionate modulus cut — docs/PHYSICS.md §5b).
    sigma_mpa = moment * y_max / np.maximum(i_m4, 1e-18) / 1e6
    i_max = int(np.argmax(sigma_mpa))
    groove_mpa = None
    if groove_band_mm is not None:
        in_band = (z_mm >= groove_band_mm[0]) & (z_mm <= groove_band_mm[1])
        groove_mpa = float(np.max(sigma_mpa[in_band])) if np.any(in_band) else 0.0

    return FlexReport(
        z_mm=z_mm,
        deflection_mm=delta * 1e3,
        twist_deg=np.degrees(dalpha),
        tip_deflection_mm=float(delta[-1] * 1e3),
        tip_twist_deg=float(math.degrees(dalpha[-1])),
        lift_knockdown=knockdown,
        f_wet_hz=f_wet,
        divergence_speed_ms=u_div,
        i_root_mm4=mech[0].i_mm4,
        stress_root_mpa=float(sigma_mpa[0]),
        stress_max_mpa=float(sigma_mpa[i_max]),
        z_stress_max_mm=float(z_mm[i_max]),
        stress_groove_mpa=groove_mpa,
        allow_mpa=allow_mpa,
    )


def flex_report(fin: FinParams, force_n: float, speed: float,
                material: str = "pet-cf", e_mpa: float | None = None) -> FlexReport:
    """Tier-0 flex of a fingen blade under force_n at boat-speed `speed` [m/s].

    Stations come from the outline's chord schedule with the groove stations
    injected (channel edges/centers), and each station's section reuses the
    loft's spanwise thickness schedule and groove thinning — a grooved fin
    automatically gets its softened band and its groove-band stress check.
    e_mpa overrides the placeholder modulus (see the module CALIBRATION NOTE).
    """
    if material not in _MATERIAL_ALLOW_MPA:
        raise ValueError(f"material {material!r} not in {sorted(_MATERIAL_ALLOW_MPA)}")
    # Default modulus from the datasheet card (in-plane flexural, fingen.materials);
    # an explicit e_mpa (e.g. the bench-measured effective modulus) overrides it.
    e = get_card(material).e_mpa if e_mpa is None else e_mpa
    settings = GenSettings(n_stations=_N_STATIONS, n_foil_points=_N_FOIL_POINTS)
    stations = chord_schedule(fin.outline, settings, tip_chord_min=settings.cap_chord,
                              extra_z=groove_station_z(fin))
    sections = []
    for st in stations:
        thin_outer, thin_inner = _groove_thins(fin, st.z, st.chord)
        sections.append(section_points(fin.foil, st.chord,
                                       thickness_ratio=_thickness_at(fin, st.z),
                                       n_points=settings.n_foil_points,
                                       thin_outer=thin_outer, thin_inner=thin_inner))
    slope, _ = lift_curve_slope(fin)
    band = None
    if fin.grooves.count:
        g = fin.grooves
        z0 = g.span_start * fin.outline.depth - 0.5 * g.width
        band = (z0, z0 + (g.count - 1) * g.pitch + g.width)
    return flex_solve(np.array([st.z for st in stations]),
                      np.array([st.chord for st in stations]),
                      np.array([st.x_le for st in stations]),
                      sections, e, force_n, speed, slope,
                      allow_mpa=_MATERIAL_ALLOW_MPA[material], groove_band_mm=band)
