"""Tier-0 hydro model against its own theoretical limits (docs/PHYSICS.md §6)."""

import math

import pytest

import fingen.hydro as hydro
from fingen.hydro import estimate, lift_curve_slope
from fingen.params import FinParams


def _helmbold(ar, a0=2 * math.pi):
    return a0 / (math.sqrt(1 + (a0 / (math.pi * ar)) ** 2) + a0 / (math.pi * ar))


def test_datcom_matches_helmbold_at_zero_sweep(monkeypatch):
    # With sweep forced to zero, DATCOM must land near Helmbold [And17].
    fin = FinParams()
    monkeypatch.setattr(hydro, "half_chord_sweep", lambda f: 0.0)
    slope, ar_eff = lift_curve_slope(fin)
    assert slope == pytest.approx(_helmbold(ar_eff), rel=0.02)


def test_slender_limit(monkeypatch):
    # As AR -> 0 the slope must approach pi*AR/2 [Jon46].
    fin = FinParams()
    monkeypatch.setattr(hydro, "REFLECTION_FACTOR", 0.05)  # force tiny AR_eff
    monkeypatch.setattr(hydro, "half_chord_sweep", lambda f: 0.0)
    slope, ar_eff = lift_curve_slope(fin)
    assert slope == pytest.approx(math.pi * ar_eff / 2.0, rel=0.05)


def test_sweep_reduces_lift_slope(monkeypatch):
    fin = FinParams()
    swept, _ = lift_curve_slope(fin)
    monkeypatch.setattr(hydro, "half_chord_sweep", lambda f: 0.0)
    unswept, _ = lift_curve_slope(fin)
    assert swept < unswept


def test_point_estimate_magnitudes():
    # Default side fin at 7 m/s and 6 deg leeway: side force should land in
    # the tens-to-~200 N band consistent with measured per-fin loads of
    # ~300 N at higher effective angles [Knies25].
    est = estimate(FinParams(), speed=7.0, leeway_deg=6.0)
    assert 50.0 < est.lift_n < 300.0
    assert 0.3 < est.cl < 1.0
    assert est.stall_margin_deg == pytest.approx(6.0)
    assert 3e5 < est.reynolds < 8e5
    assert est.drag_induced_n < est.lift_n / 4.0


def test_camber_credit_stops_at_the_validated_thickness():
    # Generation 3, defect 3 (docs/MODEL-REACH.md): on a FLAT_INSIDE foil camber
    # is t/2, and alpha_0 was converted 1:1 into max lift at ANY thickness
    # (model CL_max 0.89 at t/c 0.05 -> 1.36 at 0.22) although the camber term
    # was validated at t/c 0.092 / 0.099 only. Beyond CAMBER_CREDIT_TC the break
    # drops degree for degree: the usable angle (break - alpha_0) keeps growing
    # up to 0.10 and is flat above it. Symmetric foils are never shifted.
    from fingen.hydro import (CAMBER_CREDIT_TC, break_alpha_deg, camber_break_shift_deg,
                              stall_alpha_deg, zero_lift_alpha_deg)
    from fingen.params import FoilFamily, FoilParams

    def side(tc):
        return FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=tc))

    _, ar_eff = lift_curve_slope(side(0.10))

    def usable(f):
        return break_alpha_deg(f, ar_eff) - zero_lift_alpha_deg(f)

    assert CAMBER_CREDIT_TC == 0.10
    assert camber_break_shift_deg(side(0.07)) == 0.0
    assert camber_break_shift_deg(side(0.10)) == pytest.approx(0.0, abs=1e-12)
    assert break_alpha_deg(side(0.07), ar_eff) == stall_alpha_deg(ar_eff)
    assert usable(side(0.07)) < usable(side(0.10))
    assert usable(side(0.16)) == pytest.approx(usable(side(0.10)), abs=1e-9)
    assert usable(side(0.22)) == pytest.approx(usable(side(0.10)), abs=1e-9)
    assert camber_break_shift_deg(side(0.22)) > 4.0
    assert camber_break_shift_deg(FinParams()) == 0.0
    sym_thick = FinParams(foil=FoilParams(thickness_ratio=0.20))
    assert camber_break_shift_deg(sym_thick) == 0.0
