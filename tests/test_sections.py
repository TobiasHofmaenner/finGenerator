"""fingen.sections: the shipped section table and its interpolation."""

import math

import numpy as np
import pytest

from fingen import sections
from fingen.params import FinParams, FoilFamily, FoilParams

RE = 5.7e5      # 8.5 m/s on a 70 mm chord


def test_table_ships_with_its_provenance():
    meta = sections.table_meta()
    assert meta["source"] == "neuralfoil" and "tripped" in meta["boundary_layer"]
    assert meta["te_thickness_over_chord"] == pytest.approx(0.01)
    assert "provisional" in meta["status"]


def test_symmetric_sections_are_antisymmetric():
    p = sections.polar(FoilFamily.SYMMETRIC, 0.09, RE)
    for a in (2.0, 5.0, 8.0):
        assert float(p.cl_at(-a)) == pytest.approx(-float(p.cl_at(a)), abs=0.02)
        assert float(p.cd_at(-a)) == pytest.approx(float(p.cd_at(a)), rel=0.15)
    assert abs(p.alpha0_deg) < 0.2
    assert p.slope_per_rad == pytest.approx(2.0 * math.pi, rel=0.06)


def test_flat_inside_section_matches_the_resolved_wall_rans_points():
    # finGenerator-cfd/scripts/section_polar.py, wall resolved, t/c 0.092, Re 5.7e5
    # (docs/MODEL-EXTENSION.md): cl 0.426 / 0.861 / 1.346 at 0 / 4 / 12 deg,
    # cd 0.0423 at -3.5 deg. The table is NeuralFoil; these are its anchors.
    p = sections.polar(FoilFamily.FLAT_INSIDE, 0.092, RE)
    assert float(p.cl_at(0.0)) == pytest.approx(0.426, abs=0.03)
    assert float(p.cl_at(4.0)) == pytest.approx(0.861, abs=0.04)
    assert float(p.cl_at(12.0)) == pytest.approx(1.346, abs=0.06)
    assert float(p.cd_at(-3.5)) == pytest.approx(0.0423, rel=0.08)
    # zero-lift angle: set CFD -3.50 deg, [BW04] tunnel fin -3.5 deg
    assert p.alpha0_deg == pytest.approx(-3.5, abs=0.3)


def test_flat_inside_face_costs_drag_at_the_toe_angle_and_camber_avoids_it():
    flat = sections.polar(FoilFamily.FLAT_INSIDE, 0.092, RE)
    camb = sections.polar(FoilFamily.CAMBERED, 0.092, RE, camber_ratio=0.03)
    assert flat.alpha_cd_min_deg > 0.0                      # low-drag range on the positive side
    assert float(flat.cd_at(-3.5)) > 2.5 * flat.cd_min      # toed in, it runs far outside it
    assert float(camb.cd_at(-3.5)) < 0.4 * float(flat.cd_at(-3.5))
    assert camb.alpha0_deg == pytest.approx(flat.alpha0_deg, abs=0.6)   # trims at the same toe


def test_interpolation_hits_the_nodes_and_is_monotone_between_them():
    t = sections._table()
    k, r = 4, 2                                             # t/c 0.09, Re 4e5
    p = sections.polar(FoilFamily.FLAT_INSIDE, float(t["tc"][k]), float(t["reynolds"][r]))
    assert np.allclose(p.cl, t["flat_inside_cl"][k, r], atol=1e-6)
    assert not p.clipped
    cl0 = [float(sections.polar(FoilFamily.FLAT_INSIDE, tc, RE).cl_at(0.0))
           for tc in (0.05, 0.07, 0.09, 0.11, 0.13)]
    assert cl0 == sorted(cl0)                               # camber grows with thickness
    cd = [sections.polar(FoilFamily.SYMMETRIC, 0.09, re).cd_min for re in (1.5e5, 3e5, 6e5, 1.2e6)]
    assert cd == sorted(cd, reverse=True)                   # friction falls with Reynolds number


def test_out_of_table_requests_are_clamped_and_flagged():
    assert sections.polar(FoilFamily.SYMMETRIC, 0.09, 5.0e4).clipped
    assert sections.polar(FoilFamily.CAMBERED, 0.09, RE, camber_ratio=0.08).clipped
    assert not sections.polar(FoilFamily.CAMBERED, 0.09, RE, camber_ratio=0.03).clipped
    with pytest.raises(ValueError):
        sections.polar(FoilFamily.SYMMETRIC, 0.09, 0.0)


def test_cambered_family_with_zero_camber_is_the_symmetric_section():
    a = sections.polar(FoilFamily.CAMBERED, 0.09, RE, camber_ratio=0.0)
    b = sections.polar(FoilFamily.SYMMETRIC, 0.09, RE)
    assert np.allclose(a.cl, b.cl, atol=1e-9)


def test_thin_sections_break_earlier_than_thick_ones():
    thin = sections.polar(FoilFamily.SYMMETRIC, 0.046, RE)
    thick = sections.polar(FoilFamily.SYMMETRIC, 0.12, RE)
    assert thin.alpha_break_deg < thick.alpha_break_deg - 2.0
    assert thin.cl_break < thick.cl_break


def test_for_station_follows_the_thickness_schedule_and_the_local_chord():
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.10),
                    thickness_tip_factor=0.6)
    root = sections.for_station(fin, 8.5, 110.0, 0.0)
    tip = sections.for_station(fin, 8.5, 30.0, 1.0)
    assert root.thickness_ratio == pytest.approx(0.10)
    assert tip.thickness_ratio == pytest.approx(0.06)
    assert tip.reynolds == pytest.approx(root.reynolds * 30.0 / 110.0, rel=5e-3)  # log-Re key
    assert tip.alpha0_deg > root.alpha0_deg                 # thinner tip, less camber
