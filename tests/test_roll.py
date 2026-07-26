"""Tier-0 roll dynamics (fingen.roll): closed-form quadrature, span/chord
scalings, set-level composition, and the deep-vs-shallow depth-pricing pin.

The roll integrals are smooth low-order polynomials in z, so the numeric
quadrature is checked straight against the exact rectangular-planform results;
the scaling and depth pins are the product-relevant behaviour the module exists
to give the optimizer.
"""

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from fingen.hydro import RHO_SEAWATER, lift_curve_slope
from fingen.params import (
    FinConfig,
    FinParams,
    FinSetParams,
    FoilFamily,
    FoilParams,
    OutlineParams,
)
from fingen.roll import (
    roll_report,
    roll_set_report,
    roll_solve,
)

_SPEC = importlib.util.spec_from_file_location(
    "roll_validation", Path(__file__).resolve().parents[1] / "scripts" / "roll_validation.py")
roll_validation = importlib.util.module_from_spec(_SPEC)
sys.modules["roll_validation"] = roll_validation
_SPEC.loader.exec_module(roll_validation)

A_SECTION = 2.0 * math.pi  # thin-section 2D lift slope, for the analytic checks
SPEED = 6.4
# The audit-calibrated finite-span factor, written as an INDEPENDENT literal (not
# imported from roll.KAPPA_FS): a mutated constant moves only the module side of
# the pin. Provenance: 0.93 rolling relief × 0.78 viscous knockdown ≈ 0.73
# (bench/roll-validation/AUDIT-ADDENDUM.md); planform-specific, provisional.
KAPPA_LITERAL = 0.73


def _rect(chord_mm: float, span_mm: float, n: int = 200):
    """Rectangular strip arrays (constant chord, root→tip). A rectangle's
    geometric AR is span/chord, so its reflected AR_full = 2·span/chord."""
    z = np.linspace(0.0, span_mm, n)
    return z, np.full(n, chord_mm)


def test_closed_form_quadrature():
    # Rectangular planform about z0 = 0: ∫c·z² dz = c·s³/3 exactly, and the roll
    # added inertia ρ·∫(πc²/4)·z² dz = ρ·π·c²·s³/12. Verify the quadrature to
    # 0.1 %.
    c, s = 0.085, 0.115  # m
    z, chord = _rect(c * 1e3, s * 1e3)
    rep = roll_solve(z, chord, A_SECTION, SPEED)
    assert rep.moment_arm_int_m4 == pytest.approx(c * s**3 / 3.0, rel=1e-3)
    assert rep.added_inertia_kgm2 == pytest.approx(
        RHO_SEAWATER * math.pi * c**2 * s**3 / 12.0, rel=1e-3)
    # Drag (z³) form: ∫c·z³ dz = c·s⁴/4.
    assert rep.drag_arm_int_m5 == pytest.approx(c * s**4 / 4.0, rel=1e-3)
    # 1.1 is the documented flat-plate normal-force coefficient (roll.FLAT_PLATE_CD).
    # Written as a LITERAL here on purpose: importing the module constant would
    # make this pin self-confirming (a mutated Cd would move both sides together
    # and still pass). Duplicating it lets the pin catch a changed constant.
    assert rep.drag_damping_kgm2 == pytest.approx(
        0.5 * RHO_SEAWATER * 1.1 * c * s**4 / 4.0, rel=1e-3)
    # Finite-span calibration: kappa_fs is the audit-calibrated CONSTANT 0.73
    # (not AR-dependent); ar_full = 2·s/c is still reported as provenance context.
    ar_full = 2.0 * (s / c)  # reflected AR of the rectangle (reported only)
    assert rep.ar_full == pytest.approx(ar_full, rel=1e-3)
    assert rep.kappa_fs == pytest.approx(KAPPA_LITERAL, rel=1e-9)
    # UNCORRECTED backbone: the strip integral is still −q·a/U·c·s³/3 (the
    # geometric quadrature the module exists to carry), exposed as l_p_strip.
    q = 0.5 * RHO_SEAWATER * SPEED**2
    assert rep.l_p_strip == pytest.approx(-q * A_SECTION / SPEED * c * s**3 / 3.0, rel=1e-3)
    # CORRECTED L_p is that strip value times kappa (a damping moment, negative).
    assert rep.l_p < 0.0
    assert rep.l_p == pytest.approx(KAPPA_LITERAL * rep.l_p_strip, rel=1e-9)
    assert rep.roll_damping_nm_s == pytest.approx(
        KAPPA_LITERAL * q * A_SECTION / SPEED * c * s**3 / 3.0, rel=1e-3)
    # Dimensionless damping of a rectangular blade is kappa·(−a/3) (bare −a/3).
    assert rep.clp == pytest.approx(KAPPA_LITERAL * (-A_SECTION / 3.0), rel=1e-3)


def test_kappa_fs_is_calibration_constant():
    # (a) The finite-span factor pin. kappa_fs is the audit-calibrated CONSTANT
    # 0.73 — planform-INdependent as applied (the physics of WHICH constant is
    # planform-specific, but the code applies one number), so it must read 0.73 for
    # every planform while ar_full still reports the reflected AR 2·(s/c). Mutation
    # guard: a mutated KAPPA_FS moves rep.kappa_fs off the independent literal 0.73;
    # a resurrected AR-dependent A/(A+4) would make kappa_fs VARY with AR here (it
    # must not) and land at 0.33/0.43/0.56 instead of a flat 0.73.
    kappas = []
    for c_mm, s_mm in ((100.0, 100.0), (80.0, 120.0), (60.0, 150.0)):
        z, chord = _rect(c_mm, s_mm)
        rep = roll_solve(z, chord, A_SECTION, SPEED)
        assert rep.ar_full == pytest.approx(2.0 * (s_mm / c_mm), rel=1e-3)
        assert rep.kappa_fs == pytest.approx(KAPPA_LITERAL, rel=1e-9)  # flat 0.73
        kappas.append(rep.kappa_fs)
    assert max(kappas) - min(kappas) == pytest.approx(0.0, abs=1e-12)  # AR-invariant


def test_corrected_clp_rectangular_literal():
    # (b) Corrected fin-norm Clp of a rectangular blade against a hand-computed
    # literal. Bare strip Clp = −a/3; corrected = kappa·(−a/3) with kappa = 0.73,
    # so Clp = 0.73·(−2π/3) = 0.73·(−2.0943951) = −1.52891.
    c, s = 0.085, 0.115  # m
    z, chord = _rect(c * 1e3, s * 1e3)
    rep = roll_solve(z, chord, A_SECTION, SPEED)
    assert rep.clp == pytest.approx(KAPPA_LITERAL * (-A_SECTION / 3.0), rel=1e-3)
    assert rep.clp == pytest.approx(-1.52891, rel=2e-3)  # independent numeric literal


def test_l_p_strip_over_l_p_is_inverse_kappa():
    # (c) Auditability contract: the reported l_p is exactly kappa_fs·l_p_strip,
    # so l_p_strip / l_p == 1/kappa_fs — for ANY planform (rect and a real taper).
    # Mutation guard: applying 1/kappa (inverted) makes this ratio come out as
    # kappa, not 1/kappa; not applying kappa at all makes l_p == l_p_strip so the
    # ratio is 1 ≠ 1/kappa. Both fail here.
    z, chord = _rect(90.0, 150.0)
    rect = roll_solve(z, chord, A_SECTION, SPEED)
    real = roll_report(FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE)), SPEED)
    for rep in (rect, real):
        assert 0.0 < rep.kappa_fs < 1.0
        assert rep.l_p == pytest.approx(rep.kappa_fs * rep.l_p_strip, rel=1e-12)
        assert rep.l_p_strip / rep.l_p == pytest.approx(1.0 / rep.kappa_fs, rel=1e-12)


def test_span_and_chord_scalings():
    # Damping arm integral ∫c·z² dz ∝ s³ at fixed chord (double span → ×8) and
    # ∝ c at fixed span; added inertia ∝ c² at fixed span.
    base = roll_solve(*_rect(80.0, 100.0), A_SECTION, SPEED)
    long_span = roll_solve(*_rect(80.0, 200.0), A_SECTION, SPEED)
    fat_chord = roll_solve(*_rect(160.0, 100.0), A_SECTION, SPEED)

    assert long_span.moment_arm_int_m4 == pytest.approx(
        8.0 * base.moment_arm_int_m4, rel=1e-3)
    # The ×8 span scaling is a property of the strip backbone, pinned on the
    # UNCORRECTED l_p_strip. kappa_fs is a constant, so the corrected roll_damping
    # scales ×8 too — but l_p_strip is the backbone the module exists to carry.
    assert abs(long_span.l_p_strip) == pytest.approx(8.0 * abs(base.l_p_strip), rel=1e-3)
    assert long_span.kappa_fs == pytest.approx(base.kappa_fs, rel=1e-12)  # AR-invariant
    assert fat_chord.moment_arm_int_m4 == pytest.approx(
        2.0 * base.moment_arm_int_m4, rel=1e-3)
    assert fat_chord.added_inertia_kgm2 == pytest.approx(
        4.0 * base.added_inertia_kgm2, rel=1e-3)


def test_deep_vs_shallow_prices_depth():
    # THE product pin: two SAME-AREA blades — deep-narrow vs shallow-wide — the
    # deep one must show substantially more roll damping AND added inertia. At
    # fixed area S = c·s the damping ∫c·z² dz ∝ S·s² and the inertia ∝ S·s, so
    # depth is what a roll-aware objective would pay for.
    deep = roll_solve(*_rect(50.0, 196.0), A_SECTION, SPEED)   # c 50, s 196 mm
    shallow = roll_solve(*_rect(100.0, 98.0), A_SECTION, SPEED)  # c 100, s 98 mm
    # equal area (both 9800 mm²), span exactly doubled
    assert pytest.approx(0.050 * 0.196) == 0.100 * 0.098
    # span doubled ⇒ strip damping ×4 (s²), inertia ×2 (s). The ×4 is a backbone
    # scaling, pinned on the UNCORRECTED l_p_strip; kappa_fs is a constant, so the
    # corrected damping scales ×4 as well (the factor cancels in the ratio).
    assert abs(deep.l_p_strip) == pytest.approx(4.0 * abs(shallow.l_p_strip), rel=1e-3)
    assert deep.added_inertia_kgm2 == pytest.approx(2.0 * shallow.added_inertia_kgm2, rel=1e-3)
    assert deep.kappa_fs == pytest.approx(shallow.kappa_fs, rel=1e-12)  # AR-invariant
    assert deep.roll_damping_nm_s == pytest.approx(4.0 * shallow.roll_damping_nm_s, rel=1e-3)
    assert deep.roll_damping_nm_s > 2.0 * shallow.roll_damping_nm_s  # depth pays


def test_center_fin_is_pure_sweep():
    # y = cant = 0: all damping is the sweep mechanism, no heave.
    z, chord = _rect(90.0, 120.0)
    rep = roll_solve(z, chord, A_SECTION, SPEED)
    assert rep.heave_damping_nm_s == pytest.approx(0.0, abs=1e-12)
    assert rep.sweep_damping_nm_s == pytest.approx(rep.roll_damping_nm_s, rel=1e-9)


def test_roll_axis_offset_raises_effective_arm():
    # z0 > 0 lifts the whole blade further from the axis (z_eff = z + z0), so the
    # arm integral and damping both grow monotonically with z0.
    z, chord = _rect(90.0, 120.0)
    r0 = roll_solve(z, chord, A_SECTION, SPEED, z0_mm=0.0)
    r50 = roll_solve(z, chord, A_SECTION, SPEED, z0_mm=50.0)
    assert r50.moment_arm_int_m4 > r0.moment_arm_int_m4
    assert r50.roll_damping_nm_s > r0.roll_damping_nm_s


def test_roll_axis_offset_magnitude_pins_z0():
    # Monotonicity alone leaves the z0 mm→m conversion unpinned (feeding z0 in
    # millimetres would still grow the arm). Pin the MAGNITUDE against an
    # INDEPENDENT closed form: for a rectangular blade with no cant the arm is
    # ℓ(z) = z + z0, so ∫₀ˢ c·(z + z0)² dz = c·((s + z0)³ − z0³)/3. The literal
    # z0 = 0.050 m (from z0_mm = 50) makes a 1000× unit slip fail.
    c, s = 0.090, 0.120  # m
    z0_mm = 50.0
    z, chord = _rect(c * 1e3, s * 1e3)
    rep = roll_solve(z, chord, A_SECTION, SPEED, z0_mm=z0_mm)
    z0 = z0_mm * 1e-3  # 0.050 m — the conversion under test
    expected = c * ((s + z0) ** 3 - z0**3) / 3.0
    assert rep.moment_arm_int_m4 == pytest.approx(expected, rel=1e-3)


def test_cant_trades_sweep_for_heave():
    # A side blade at a lateral offset. Cant tilts the lift normal: the SWEEP
    # contribution (∝ cosγ, plus the shallower canted depth) must fall
    # monotonically with cant, while the heave contribution (∝ sinγ) rises from
    # zero — the set-geometry sign/monotonicity pin.
    z, chord = _rect(90.0, 120.0)
    kw = dict(y_offset_mm=118.0)
    sweeps, heaves = [], []
    for cant in (0.0, 4.0, 8.0, 12.0):
        rep = roll_solve(z, chord, A_SECTION, SPEED, cant_deg=cant, **kw)
        sweeps.append(rep.sweep_damping_nm_s)
        heaves.append(rep.heave_damping_nm_s)
    assert heaves[0] == pytest.approx(0.0, abs=1e-12)
    assert all(a > b for a, b in zip(sweeps, sweeps[1:], strict=False))  # sweep ↓
    assert all(a < b for a, b in zip(heaves, heaves[1:], strict=False))  # heave ↑


def test_heave_contribution_magnitude_pins_offset_and_units():
    # The offset (y_f) contribution to the heave mechanism is otherwise only
    # checked for monotonicity/sign — a dropped y_f or an mm→m slip survives.
    # Pin the heave-damping MAGNITUDE against an INDEPENDENT closed form derived
    # from the physics (NOT from roll.py helpers). roll.py's heave arm is
    # ℓ_h(z) = Y(z)·sinγ with the lateral offset Y(z) = y_f + z·sinγ, and
    # heave_damp = q·a/U · ∫₀ˢ c·ℓ_h² dz. With ℓ_h² = sin²γ·(y_f + z·sinγ)² and
    #     ∫₀ˢ (y_f + z·sinγ)² dz = y_f²·s + y_f·sinγ·s² + sin²γ·s³/3,
    # heave_damp = kappa·q·a/U · c·sin²γ·(y_f²·s + y_f·sinγ·s² + sin²γ·s³/3),
    # where kappa = 0.73 is the audit-calibrated finite-span constant (the heave
    # diagonal is a lift-loading term, so it carries kappa like l_p). Here the
    # y_f² term dominates, so dropping y_f or slipping mm→m moves the expectation
    # by ~100–1000×, far outside the quadrature tolerance.
    c, s = 0.090, 0.120  # m (chord, span)
    y_off_mm, cant = 118.0, 8.0  # offset > 0 and cant > 0, as required
    z, chord = _rect(c * 1e3, s * 1e3)
    rep = roll_solve(z, chord, A_SECTION, SPEED,
                     y_offset_mm=y_off_mm, cant_deg=cant)
    y_f = y_off_mm * 1e-3  # 0.118 m — the mm→m conversion under test
    sg = math.sin(math.radians(cant))
    q = 0.5 * RHO_SEAWATER * SPEED**2
    lateral_sq_int = y_f**2 * s + y_f * sg * s**2 + sg**2 * s**3 / 3.0
    expected_heave = KAPPA_LITERAL * q * A_SECTION / SPEED * c * sg**2 * lateral_sq_int
    assert rep.heave_damping_nm_s == pytest.approx(expected_heave, rel=1e-3)
    # The offset term genuinely dominates the heave (guards against a pin that a
    # dropped y_f could still satisfy): y_f²·s ≫ sin²γ·s³/3.
    assert y_f**2 * s > 100.0 * (sg**2 * s**3 / 3.0)


def test_set_side_blades_add_to_center():
    # A thruster's side pair rides at a lateral offset and adds roll damping on
    # top of the center fin: the set total must exceed the center-only value.
    sp = FinSetParams(config=FinConfig.THRUSTER)
    rep = roll_set_report(sp, SPEED)
    assert set(rep.per_slot) == {"center", "right", "left"}
    center_only = rep.per_slot["center"].roll_damping_nm_s
    assert rep.roll_damping_nm_s > center_only
    # Right and left contribute identically (mirror-symmetric roll arm).
    assert rep.per_slot["right"].roll_damping_nm_s == pytest.approx(
        rep.per_slot["left"].roll_damping_nm_s, rel=1e-9)
    # Totals sum the slots; τ and agility come off the totals.
    assert rep.roll_damping_nm_s == pytest.approx(
        sum(r.roll_damping_nm_s for r in rep.per_slot.values()), rel=1e-12)
    assert rep.agility_proxy == pytest.approx(1.0 / rep.roll_damping_nm_s, rel=1e-9)
    assert rep.tau_ms > 0.0


def test_set_configs_enumerate_expected_slots():
    for cfg, slots in (
        (FinConfig.SINGLE, {"center"}),
        (FinConfig.TWIN, {"right", "left"}),
        (FinConfig.QUAD, {"front_right", "front_left", "rear_right", "rear_left"}),
    ):
        rep = roll_set_report(FinSetParams(config=cfg), SPEED)
        assert set(rep.per_slot) == slots


def test_wrapper_and_agility_ordering():
    # A deep single vs a shallow side blade through the FinParams wrapper: the
    # deeper blade damps harder and is therefore LESS agile (lower proxy).
    deep = FinParams(outline=OutlineParams(depth=240, base=160, sweep=45,
                                           tip_width_ratio=0.28),
                     foil=FoilParams(family=FoilFamily.SYMMETRIC))
    shallow = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    rd = roll_report(deep, SPEED)
    rs = roll_report(shallow, SPEED)
    assert rd.roll_damping_nm_s > rs.roll_damping_nm_s
    assert rd.agility_proxy < rs.agility_proxy
    assert rd.tau_ms > 0.0 and rd.lift_slope == pytest.approx(lift_curve_slope(deep)[0])


def test_input_validation():
    z, chord = _rect(90.0, 120.0)
    with pytest.raises(ValueError):
        roll_solve(z, chord[:-1], A_SECTION, SPEED)  # length mismatch
    with pytest.raises(ValueError):
        roll_solve(z[:3], chord[:3], A_SECTION, SPEED)  # too few stations
    with pytest.raises(ValueError):
        roll_solve(z[::-1], chord, A_SECTION, SPEED)  # not increasing
    with pytest.raises(ValueError):
        roll_solve(z, chord, A_SECTION, 0.0)  # zero speed


def test_roll_validation_case_writes(tmp_path):
    # CFD-prep smoke: the twisted-inflow case renders — the sheared inlet
    # uy(z) = ω·z and the roll-moment forces FO are in place, the fin STL is
    # exported. (The EPYC solves it; here we only prove the dictionaries write.)
    from fingen.params import GenSettings

    coarse = GenSettings(n_stations=11, n_foil_points=60)
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    case = roll_validation.write_roll_case(fin, 6.4, 3.0, tmp_path / "w3", settings=coarse)
    for rel in ("system/controlDict", "system/blockMeshDict", "0/U",
                "constant/triSurface/fin.stl"):
        assert (case / rel).exists(), rel
    u = (case / "0/U").read_text()
    assert "codedFixedValue" in u and "3*cf[i].z()" in u  # uy(z) = 3·z twist
    control = (case / "system/controlDict").read_text()
    assert "rollMoment" in control and "type            forces;" in control
    # Baseline ω = 0 renders too (uniform inlet through the same coded path).
    base = roll_validation.write_roll_case(fin, 6.4, 0.0, tmp_path / "w0", settings=coarse)
    assert "0*cf[i].z()" in (base / "0/U").read_text()
