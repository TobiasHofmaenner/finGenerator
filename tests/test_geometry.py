"""End-to-end: loft -> manifold check -> export (docs/PHYSICS.md §5)."""

import pytest

from fingen.check import check_solid
from fingen.export import to_step, to_stl
from fingen.loft import fin_solid
from fingen.params import FinParams, FoilFamily, FoilParams, GenSettings


@pytest.fixture(scope="module")
def side_fin():
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    return fin, fin_solid(fin)


def test_side_fin_is_a_valid_manifold(side_fin):
    fin, part = side_fin
    report = check_solid(part, fin)
    assert report.ok, report.issues


def test_side_fin_dimensions(side_fin):
    fin, part = side_fin
    bbox = part.bounding_box()
    z_min, z_max, y_min = bbox.min.Z, bbox.max.Z, bbox.min.Y
    assert z_max == pytest.approx(fin.outline.depth, abs=0.5)
    assert z_min == pytest.approx(0.0, abs=0.5)
    # Flat inner face on the y=0 plane (print-bed face).
    assert y_min == pytest.approx(0.0, abs=0.5)


def test_center_fin_symmetric():
    fin = FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC))
    report = check_solid(fin_solid(fin), fin)
    assert report.ok, report.issues


def test_cambered_fin():
    fin = FinParams(foil=FoilParams(family=FoilFamily.CAMBERED, camber_ratio=0.03))
    report = check_solid(fin_solid(fin), fin)
    assert report.ok, report.issues


def test_step_and_stl_export(side_fin, tmp_path):
    _, part = side_fin
    step = to_step(part, tmp_path / "fin.step")
    assert step.read_text().startswith("ISO-10303-21")
    stl = to_stl(part, tmp_path / "fin.stl")
    assert stl.stat().st_size > 10_000


def test_resolution_only_changes_discretization(side_fin):
    fin, part = side_fin
    coarse = fin_solid(fin, GenSettings(n_stations=11, n_foil_points=60))
    assert coarse.volume == pytest.approx(part.volume, rel=0.02)
