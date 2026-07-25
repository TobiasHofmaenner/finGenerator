"""End-to-end: loft -> manifold check -> export (docs/PHYSICS.md §5)."""

import struct

import numpy as np
import pytest
from build123d import Pos, Solid

from fingen.check import check_solid
from fingen.export import to_step, to_stl
from fingen.loft import fin_solid
from fingen.params import FinParams, FoilFamily, FoilParams, GenSettings, OutlineParams


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
    # Flat inner face on the y=0 plane (print-bed face); the skin may
    # undershoot by a fraction of a print layer between tip-lobe stations.
    assert y_min == pytest.approx(0.0, abs=0.15)


def test_center_fin_symmetric():
    fin = FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC))
    report = check_solid(fin_solid(fin), fin)
    assert report.ok, report.issues


def test_cambered_fin_at_top_of_validated_range():
    # camber_ratio's upper bound in params.py is the demonstrated buildable
    # limit — this test pins it: raising the bound requires making this pass.
    fin = FinParams(foil=FoilParams(family=FoilFamily.CAMBERED, camber_ratio=0.05))
    for settings in (GenSettings(n_stations=11, n_foil_points=60), GenSettings()):
        report = check_solid(fin_solid(fin, settings), fin, settings)
        assert report.ok, report.issues


def test_step_roundtrip_preserves_geometry(side_fin, tmp_path):
    from build123d import import_step

    _, part = side_fin
    step = to_step(part, tmp_path / "fin.step")
    assert step.read_text().startswith("ISO-10303-21")
    back = import_step(str(step))
    assert len(back.solids()) == 1
    assert back.volume == pytest.approx(part.volume, rel=1e-3)
    for axis in ("X", "Y", "Z"):
        assert getattr(back.bounding_box().max, axis) == pytest.approx(
            getattr(part.bounding_box().max, axis), abs=0.05)


def test_stl_mesh_volume_matches_solid(side_fin, tmp_path):
    _, part = side_fin
    stl = to_stl(part, tmp_path / "fin.stl")
    data = stl.read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    assert n > 100
    rec = np.frombuffer(data[84:84 + n * 50],
                        dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    tri = rec["v"].reshape(n, 3, 3).astype(np.float64)
    # Signed volume via the divergence theorem over facets.
    vol = abs(float(np.einsum("ij,ij->i", tri[:, 0],
                              np.cross(tri[:, 1], tri[:, 2])).sum()) / 6.0)
    assert vol == pytest.approx(part.volume, rel=0.02)


def test_resolution_only_changes_discretization(side_fin):
    fin, part = side_fin
    for settings in (GenSettings(n_stations=11, n_foil_points=60),
                     GenSettings(n_stations=23, n_foil_points=160),
                     GenSettings(cap_chord=1.5),
                     GenSettings(cap_chord=6.0)):
        other = fin_solid(fin, settings)
        assert other.volume == pytest.approx(part.volume, rel=0.02)
        assert pytest.approx(
            part.bounding_box().max.Z, abs=0.5) == other.bounding_box().max.Z


def test_grooved_fin_is_valid_and_lighter(side_fin):
    from fingen.params import GrooveParams

    fin_plain, part_plain = side_fin
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                    grooves=GrooveParams(count=6))
    part = fin_solid(fin)
    report = check_solid(part, fin)
    assert report.ok, report.issues
    # Grooves remove material — and the checker's analytic volume knows it.
    assert part.volume < part_plain.volume
    removed = part_plain.volume - part.volume
    assert 200.0 < removed < 2000.0, removed
    # Span/planform must be untouched (thinning only, no outline change) —
    # up to the 0.05 mm station-merge shuffle in the smooth tip segment.
    bb, bb_plain = part.bounding_box(), part_plain.bounding_box()
    assert abs(bb.max.Z - bb_plain.max.Z) < 0.05
    assert abs(bb.max.X - bb_plain.max.X) < 0.05


def test_groove_count_zero_is_identical(side_fin):
    from fingen.params import GrooveParams

    _, part_plain = side_fin
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                    grooves=GrooveParams(count=0, depth_ratio=0.5))
    assert abs(fin_solid(fin).volume - part_plain.volume) < 1e-6


def test_checker_detects_broken_inputs():
    fin = FinParams()
    box = Solid.make_box(10, 10, 10)

    two = box + Pos(500, 0, 0) * Solid.make_box(10, 10, 10)
    report = check_solid(two, fin)
    assert not report.ok and "exactly 1 solid" in report.issues[0]

    # A valid solid that is simply not this fin: wrong span, wrong volume.
    report = check_solid(Solid.make_box(110, 10, 300), fin)
    assert not report.ok
    assert any("span extent" in issue for issue in report.issues)

    # Right span, absurd thickness extent.
    report = check_solid(Solid.make_box(110, 200, 115), fin)
    assert not report.ok
    assert any("thickness extent" in issue for issue in report.issues)


def test_level2_offset_fin_is_checked_like_any_other():
    fin = FinParams(outline=OutlineParams(te_dx=(0.0, -8.0, -12.0, -8.0, 0.0, 0.0)))
    settings = GenSettings(n_stations=11, n_foil_points=60)
    report = check_solid(fin_solid(fin, settings), fin, settings)
    assert report.ok, report.issues


def test_mirror_hand_flips_chirality(side_fin):
    from fingen.export import mirror_hand

    _, part = side_fin
    left = mirror_hand(part)
    bb, lb = part.bounding_box(), left.bounding_box()
    # Volume preserved; foil bulge flips from +y to -y; flat face stays y=0.
    assert abs(left.volume - part.volume) < 1e-3 * part.volume
    assert abs(lb.min.Y + bb.max.Y) < 1e-6
    assert abs(lb.max.Y) < 1e-6
    assert len(left.solids()) == 1


def test_split_halves_is_a_mirror_pair():
    from fingen.export import split_halves

    fin = FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC))
    part = fin_solid(fin)
    half_a, half_b = split_halves(part)
    # Each half is one solid with a flat face at the midplane, volumes sum
    # to the whole, and each prints flat (one lives in y>=0, the other y<=0).
    assert len(half_a.solids()) == 1 and len(half_b.solids()) == 1
    assert abs(half_a.volume + half_b.volume - part.volume) < 1e-3 * part.volume
    assert half_a.bounding_box().min.Y > -1e-6
    assert half_b.bounding_box().max.Y < 1e-6
    # Symmetric section: the halves mirror each other in volume too.
    assert abs(half_a.volume - half_b.volume) < 1e-3 * part.volume
