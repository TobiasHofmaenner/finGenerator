"""Outline math and the FCS validation anchor (docs/PHYSICS.md §3)."""

import pytest

from fingen.outline import chord_schedule, metrics, tip_point
from fingen.params import GenSettings, OutlineParams


def test_base_station_matches_parameters():
    outline = OutlineParams()
    stations = chord_schedule(outline)
    assert stations[0].z == 0.0
    assert stations[0].x_le == pytest.approx(0.0, abs=1e-6)
    assert stations[0].chord == pytest.approx(outline.base, rel=1e-6)


def test_chord_positive_and_reaches_tip_region():
    outline = OutlineParams()
    stations = chord_schedule(outline, tip_chord_min=3.0)
    assert all(st.chord > 0 for st in stations)
    assert stations[-1].chord == pytest.approx(3.0, rel=0.1)
    assert stations[-1].z < outline.depth <= tip_point(outline)[1]


def test_default_template_lands_in_commercial_band():
    # A medium thruster side fin [FCS26]: base 110, depth 115, published area
    # ~9825 mm2. Our default (concave-TE, rounded-tip) template must land in a
    # commercial-plausible band; exact calibration against a traced template
    # is tracked as a TODO.
    m = metrics(OutlineParams())
    assert 6500.0 < m.area < 10500.0
    assert m.sweep == pytest.approx(42.0, abs=0.01)
    assert m.aspect_ratio == pytest.approx(115.0**2 / m.area, rel=1e-9)


def test_sweep_recompute_matches_input():
    m = metrics(OutlineParams(sweep=33.0))
    assert m.sweep == pytest.approx(33.0, abs=0.01)


def test_te_shape_moves_area_the_documented_direction():
    concave = metrics(OutlineParams(te_shape=-1.0)).area
    straight = metrics(OutlineParams(te_shape=0.0)).area
    convex = metrics(OutlineParams(te_shape=1.0)).area
    assert concave < straight < convex


def test_resolution_does_not_change_the_design():
    import numpy as np

    outline = OutlineParams()
    coarse = chord_schedule(outline, GenSettings(n_stations=9))
    fine = chord_schedule(outline, GenSettings(n_stations=31))
    assert coarse[-1].z == pytest.approx(fine[-1].z, rel=1e-6)
    # Every coarse station must lie ON the fine schedule's curve, not merely
    # share endpoints — this is what pins "resolution only" for the outline.
    fz = np.array([s.z for s in fine])
    fc = np.array([s.chord for s in fine])
    fx = np.array([s.x_le for s in fine])
    for st in coarse:
        assert st.chord == pytest.approx(float(np.interp(st.z, fz, fc)), rel=0.002)
        assert st.x_le == pytest.approx(float(np.interp(st.z, fz, fx)), abs=0.1)
