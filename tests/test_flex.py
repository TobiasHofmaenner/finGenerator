"""Tier-0 flex model against the [Zar14] measurements and the CalculiX tier.

The money anchor is the Zarruk Type I stainless hydrofoil
(bench/zarruk/geometry.md): measured dimensionless tip deflection
δ' = δ·E·I/(F·s³) = 0.204, independent of α and Re — a pure test of the
structural model with the hydrodynamics divided out. The CalculiX demo
(scripts/fem_demo.py: 1.19 mm at a 74 N resultant) pins the stubby end.
Both anchors calibrate the root-compliance slope in fingen.flex — treat
these tests as regression pins on that calibration.
"""

import numpy as np
import pytest

from fingen.flex import flex_report, flex_solve, section_mech
from fingen.foil import section_points
from fingen.params import FinParams, FoilFamily, FoilParams, GrooveParams

# [Zar14] Type I geometry and Table 2 properties (bench/zarruk/geometry.md).
SPAN = 300.0  # mm
C_ROOT, C_TIP = 120.0, 60.0  # mm, taper ratio 0.5
E_STEEL = 193000.0  # MPa, 316L
I_TABLE = 5956.0  # mm⁴, their base-section bending inertia
DELTA_PRIME = 0.204  # measured δ', Type I SS mean (Fig. 18)
F_WET = 62.0  # Hz, Type I SS first mode in water
FORCE = 600.0  # N — arbitrary: δ' and f_wet are load-independent

FEM_TIP_MM = 1.19  # CalculiX demo max |u| on the default side fin
FEM_FORCE_N = 74.0  # its pressure-patch resultant


def _zarruk_arrays(n: int = 61):
    """Type I as station arrays: trapezoid, NACA0009 sections, unswept
    elastic axis (x_le chosen so the centroid locus is exactly vertical)."""
    z = np.linspace(0.0, SPAN, n)
    chord = C_ROOT + (C_TIP - C_ROOT) * z / SPAN
    foil = FoilParams(family=FoilFamily.SYMMETRIC, thickness_ratio=0.09,
                      te_thickness=0.4)  # thinnest printable TE ≈ their 0.2%c
    sections = [section_points(foil, c, n_points=120) for c in chord]
    frac = section_mech(*sections[0]).x_c_mm / chord[0]
    return z, chord, -frac * chord, sections


def _load_c43(z_mm: np.ndarray) -> np.ndarray:
    """Linear spanwise loading with centroid at 0.43·span — where our CFD of
    this foil puts the lift centroid (Schrenk-like, between the trapezoid's
    0.444 and the elliptic 0.424)."""
    return 1.0 - 0.5917 * (z_mm / SPAN)


def _zarruk_report(n: int = 61):
    z, chord, x_le, sections = _zarruk_arrays(n)
    # lift_slope ≈ Helmbold at the root-mirrored AR 6.67 (only the knockdown
    # and divergence numbers use it); tunnel water is fresh (ρ = 1000).
    return flex_solve(z, chord, x_le, sections, E_STEEL, FORCE, 6.7, 4.7,
                      load=_load_c43, rho_struct=7900.0, rho_fluid=1000.0)


def test_zarruk_dimensionless_deflection():
    rep = _zarruk_report()
    # Numeric section integration must reproduce their tabulated base
    # inertia (the +2% residual is the printable-TE wedge and quadrature).
    assert rep.i_root_mm4 == pytest.approx(I_TABLE, rel=0.10)
    d_prime = (rep.tip_deflection_mm * 1e-3) * (E_STEEL * 1e6) \
        * (rep.i_root_mm4 * 1e-12) / (FORCE * (SPAN * 1e-3) ** 3)
    # Measured 0.204, α- and Re-independent. The raw wetted-span beam gives
    # 0.164 (their clamp sits above the tunnel-ceiling plane, so the real
    # cantilever is softer); the calibrated root-compliance factor lands −2%.
    assert d_prime == pytest.approx(DELTA_PRIME, rel=0.15)
    # Same solve, same shape: Rayleigh + flat-plate added mass must hit the
    # measured in-water first mode (structural-only would be ~100 Hz).
    assert rep.f_wet_hz == pytest.approx(F_WET, rel=0.15)


def test_unswept_axis_no_twist():
    # Their metal foils showed no resolvable twist [Zar14 p.15]. With the
    # elastic axis exactly vertical the rake coupling is identically zero;
    # what remains is the small nose-up direct-torsion term — same sign as
    # the +0.6° they measured on CFRP00, the first blade soft enough to read.
    rep = _zarruk_report()
    assert 0.0 <= rep.tip_twist_deg < 0.15


def test_raked_fin_washes_out():
    # Default fin, 33° sweep, +y load: bending along the raked elastic axis
    # must dominate the nose-up torsion term — net twist NEGATIVE (washout),
    # and the washout must cost lift (knockdown fraction < 0).
    rep = flex_report(FinParams(), 74.0, 6.4)
    assert rep.tip_twist_deg < -0.1
    assert rep.lift_knockdown < 0.0


def test_fem_cross_check():
    # CalculiX C3D10 demo on this exact blade: 1.19 mm max |u| at 74 N
    # (uniform outer-face pressure ⇒ w ∝ c, our default load). The RAW
    # wetted-span beam reads ~1.5× too stiff for this stubby blade (root
    # warping/shear lag grow with c_root/span); the calibrated compliance
    # slope centers it — expect the beam slightly SOFT here (+1%), slightly
    # stiff on slender blades (Zarruk −2%).
    side = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    rep = flex_report(side, FEM_FORCE_N, 6.4, e_mpa=7000.0)
    assert rep.tip_deflection_mm == pytest.approx(FEM_TIP_MM, rel=0.25)


def test_default_fin_screening_bands():
    # Sanity corridor, not a measurement. The default blade is short, solid
    # and thick (bench stiffness ~60 N/mm) — its wet first mode sits near
    # 100 Hz, far above flexy commercial fins (~3.6 N/mm, O(10 Hz) [Krz24]);
    # the added-mass-loaded band 40–200 Hz flags unit bugs either way.
    # Divergence must clear the tow-in envelope top (15 m/s) with margin.
    rep = flex_report(FinParams(), 74.0, 6.4)
    assert 40.0 < rep.f_wet_hz < 200.0
    assert rep.divergence_speed_ms > 15.0
    assert rep.stress_margin > 1.0  # working load far below the allowable


def test_grooves_soften_and_relocate_critical_section():
    # [Els22/For24] bench result: the grooved blade is measurably softer.
    plain = flex_report(FinParams(), 74.0, 6.4)
    grooved_fin = FinParams(grooves=GrooveParams(count=6))
    grooved = flex_report(grooved_fin, 74.0, 6.4)
    assert grooved.tip_deflection_mm / plain.tip_deflection_mm > 1.05
    # The tier-0 groove-band stress check (closes the PHYSICS.md §4 TODO):
    # the critical bending station must fall INSIDE the band — near-root
    # moment against a section modulus cut that goes as thickness squared.
    g = grooved_fin.grooves
    band_lo = g.span_start * grooved_fin.outline.depth - 0.5 * g.width
    band_hi = band_lo + (g.count - 1) * g.pitch + g.width
    assert band_lo <= grooved.z_stress_max_mm <= band_hi
    assert grooved.stress_groove_mpa == pytest.approx(grooved.stress_max_mpa)
    assert grooved.stress_groove_mpa > grooved.stress_root_mpa
    assert plain.stress_groove_mpa is None


def test_wrapper_material_and_modulus_paths():
    fin = FinParams()
    soft = flex_report(fin, 74.0, 6.4, e_mpa=3500.0)
    stiff = flex_report(fin, 74.0, 6.4, e_mpa=7000.0)
    # Deflection is linear in compliance; the placeholder default is 7000.
    assert soft.tip_deflection_mm == pytest.approx(2.0 * stiff.tip_deflection_mm)
    assert flex_report(fin, 74.0, 6.4).tip_deflection_mm == \
        pytest.approx(stiff.tip_deflection_mm)
    paht = flex_report(fin, 74.0, 6.4, material="paht-cf")
    assert paht.allow_mpa == pytest.approx(125.0 * 0.5 / 2.0)
    with pytest.raises(ValueError):
        flex_report(fin, 74.0, 6.4, material="unobtainium")
    with pytest.raises(ValueError):
        flex_report(fin, -5.0, 6.4)
