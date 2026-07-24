"""Section math against its own analytic definition (docs/PHYSICS.md §4)."""

import numpy as np
import pytest

from fingen.foil import section_points, section_properties
from fingen.params import FoilFamily, FoilParams

CHORD = 100.0


def test_symmetric_thickness_and_position():
    foil = FoilParams(family=FoilFamily.SYMMETRIC, thickness_ratio=0.09, te_thickness=0.4)
    upper, lower = section_points(foil, CHORD)
    props = section_properties(upper, lower)
    # Max thickness = t·c at x/c = 0.30 [Jac33]; the TE wedge adds a little.
    assert props["max_thickness"] == pytest.approx(9.0, rel=0.05)
    assert props["x_at_max"] == pytest.approx(30.0, abs=4.0)
    # Symmetry (before the TE wedge dominates): mid-chord upper == -lower.
    mid = len(upper) // 2
    assert upper[mid, 1] == pytest.approx(-lower[mid, 1], rel=0.05)


def test_flat_inside_has_planar_inner_face():
    foil = FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.09)
    upper, lower = section_points(foil, CHORD)
    assert np.all(lower[:, 1] <= 0.0)
    assert np.min(lower[:, 1]) > -foil.te_thickness  # only the TE wedge dips below 0
    props = section_properties(upper, lower)
    assert props["max_thickness"] == pytest.approx(9.0, rel=0.08)


def test_cambered_mean_line():
    foil = FoilParams(family=FoilFamily.CAMBERED, thickness_ratio=0.08,
                      camber_ratio=0.04, camber_position=0.4)
    upper, lower = section_points(foil, CHORD)
    xs = upper[:, 0]
    lo = np.interp(xs, lower[:, 0], lower[:, 1])
    mean = 0.5 * (upper[:, 1] + lo)
    # Max camber = m·c near x = p·c [Jac33].
    assert np.max(mean) == pytest.approx(4.0, rel=0.1)
    assert xs[int(np.argmax(mean))] == pytest.approx(40.0, abs=8.0)


def test_trailing_edge_truncation():
    foil = FoilParams(family=FoilFamily.SYMMETRIC, te_thickness=0.8)
    upper, lower = section_points(foil, CHORD)
    gap = upper[-1, 1] - lower[-1, 1]
    assert gap == pytest.approx(0.8, abs=1e-9)


def test_shared_leading_edge_point():
    for family in FoilFamily:
        foil = FoilParams(family=family, camber_ratio=0.03)
        upper, lower = section_points(foil, CHORD)
        assert upper[0] == pytest.approx(lower[0], abs=1e-9)


def test_rejects_nonpositive_chord():
    with pytest.raises(ValueError):
        section_points(FoilParams(), 0.0)
