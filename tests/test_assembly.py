"""Fin-set assembly: placement transforms + multi-blade scene (docs/PHYSICS.md §2b)."""

import struct

import numpy as np
import pytest
from build123d import Axis

from fingen.assembly import assembly_stl, fin_set, place_fin, preview_set
from fingen.loft import fin_solid
from fingen.params import (
    FinConfig,
    FinParams,
    FinSetParams,
    FoilFamily,
    FoilParams,
    GenSettings,
)

COARSE = GenSettings(n_stations=11, n_foil_points=60)


@pytest.fixture(scope="module")
def side_blade():
    return fin_solid(FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE)), COARSE)


@pytest.fixture(scope="module")
def thruster():
    return fin_set(FinSetParams(config=FinConfig.THRUSTER), COARSE)


def _base_axis_deg(part):
    """In-plane angle of the base-face principal axis (rotation-covariant chord
    direction marker) — used to read back a placed blade's toe."""
    base = part.faces().sort_by(Axis.Z)[0]
    vs = np.array([(v.X, v.Y) for v in base.vertices()])
    vs = vs - vs.mean(axis=0)
    _, _, vt = np.linalg.svd(vs, full_matrices=False)
    return np.degrees(np.arctan2(vt[0, 1], vt[0, 0]))


def test_thruster_three_solids_with_mirrored_sides(thruster):
    names = [n for n, _ in thruster]
    assert names == ["center", "right", "left"]
    blades = dict(thruster)
    for _, p in thruster:
        assert len(p.solids()) == 1
    rb, lb = blades["right"].bounding_box(), blades["left"].bounding_box()
    # The side pair is a mirror image across the stringer (y = 0): the right
    # blade's y-extent is the left's negated.
    hi_lo, lo_hi = rb.max.Y + lb.min.Y, rb.min.Y + lb.max.Y
    assert hi_lo == pytest.approx(0.0, abs=1e-3)
    assert lo_hi == pytest.approx(0.0, abs=1e-3)
    assert rb.min.Y > 0.0 and lb.max.Y < 0.0  # sides on opposite rails


def test_toe_is_realized(side_blade):
    # Compare each hand's placed base axis to its own zero-toe reference: the
    # right fin rotates +toe about +z (nose-in), the left the opposite sign.
    for toe in (3.0, 5.0):
        r0 = _base_axis_deg(place_fin(side_blade, toe_deg=0.0, cant_deg=0.0,
                                      x=0.0, y=120.0, hand="right"))
        rt = _base_axis_deg(place_fin(side_blade, toe_deg=toe, cant_deg=0.0,
                                      x=0.0, y=120.0, hand="right"))
        l0 = _base_axis_deg(place_fin(side_blade, toe_deg=0.0, cant_deg=0.0,
                                      x=0.0, y=-120.0, hand="left"))
        lt = _base_axis_deg(place_fin(side_blade, toe_deg=toe, cant_deg=0.0,
                                      x=0.0, y=-120.0, hand="left"))
        assert rt - r0 == pytest.approx(toe, abs=0.2)
        assert lt - l0 == pytest.approx(-toe, abs=0.2)


def test_cant_keeps_root_on_board_plane(thruster):
    # Every blade's root sits on z = 0: cant pivots about the base centerline,
    # so only the finite base-thickness tilt (< ~1 mm at 8°) remains — NOT the
    # side_y·sin(cant) ≈ 16 mm a global-axis cant would lift the root by.
    for name, p in thruster:
        bb = p.bounding_box()
        z_min, z_max = bb.min.Z, bb.max.Z
        assert z_min == pytest.approx(0.0, abs=1.2), name
        assert z_max > 100.0  # blade hangs up into z > 0


def test_center_fin_has_no_toe_or_cant(thruster):
    center = dict(thruster)["center"]
    z_min = center.bounding_box().min.Z
    assert z_min == pytest.approx(0.0, abs=0.05)  # symmetric, flat on board
    assert _base_axis_deg(center) == pytest.approx(0.0, abs=0.5)


def test_quad_makes_four_and_single_makes_one():
    quad = fin_set(FinSetParams(config=FinConfig.QUAD), COARSE)
    assert [n for n, _ in quad] == ["front_right", "front_left",
                                    "rear_right", "rear_left"]
    single = fin_set(FinSetParams(config=FinConfig.SINGLE), COARSE)
    assert [n for n, _ in single] == ["center"]


def test_assembly_stl_is_nonempty_multi_solid(thruster, tmp_path):
    stl = assembly_stl(FinSetParams(config=FinConfig.THRUSTER),
                       tmp_path / "fins.stl", COARSE)
    assert stl.exists()
    data = stl.read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    # Three lofted blades → a plausible (large) triangle count, one file.
    assert n > 1000
    assert stl.stat().st_size == 84 + n * 50


def test_overlapping_sides_are_rejected():
    # side_y far too small → the two side blades interpenetrate; caught on the
    # placed solids (not a scalar bound), with a clean ValueError.
    with pytest.raises(ValueError, match="interpenetrate"):
        fin_set(FinSetParams(config=FinConfig.THRUSTER, side_y=3.0), COARSE)


def test_place_fin_rejects_bad_hand(side_blade):
    with pytest.raises(ValueError, match="hand"):
        place_fin(side_blade, toe_deg=0.0, cant_deg=0.0, x=0.0, y=0.0, hand="port")


def test_preview_set_renders_png(tmp_path):
    png = preview_set(FinSetParams(config=FinConfig.SINGLE), tmp_path / "set.png",
                      COARSE)
    assert png.exists()
    assert png.stat().st_size > 15_000
