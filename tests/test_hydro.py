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
