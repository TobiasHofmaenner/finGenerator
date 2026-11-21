"""fingen.sections: the shipped section table and its interpolation."""

import json
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


def test_both_tables_ship_and_v1_names_what_it_was_fitted_on():
    assert sections.TABLES == ("v0", "v1")
    meta = sections.table_meta("v1")
    assert meta["version"] == 1 and "RANS" in meta["source"]
    assert "camb3-tc070-re570k" in meta["fits"]["cambered"]["nodes"]
    assert sections.table_meta()["version"] == 0                 # v0 stays the default
    with pytest.raises(ValueError):
        sections.polar(FoilFamily.SYMMETRIC, 0.09, RE, table="v2")


def test_v1_ends_a_thin_cambered_sections_range_where_the_rans_does():
    # bench/section-tables/thin-cambered, 3 % camber, Re 5.7e5, resolved wall:
    # t/c 0.070 attached at -3.5 deg (cd 0.0139), separated at -4.5 (0.032, 2.5 x the
    # minimum) and past its knee at +10; t/c 0.092 attached from -6 to +10 deg.
    thin0 = sections.polar(FoilFamily.CAMBERED, 0.07, RE, 0.03)
    thin1 = sections.polar(FoilFamily.CAMBERED, 0.07, RE, 0.03, table="v1")
    thick1 = sections.polar(FoilFamily.CAMBERED, 0.092, RE, 0.03, table="v1")
    assert float(thin0.cd_at(-4.5)) < 1.35 * thin0.cd_min        # v0: still inside
    assert float(thin1.cd_at(-4.5)) > 1.8 * thin1.cd_min         # v1: out, as in RANS
    assert float(thin1.cd_at(-3.5)) < 1.35 * thin1.cd_min
    assert float(thick1.cd_at(-4.5)) < 1.25 * thick1.cd_min
    assert float(thin1.cd_at(0.0)) == pytest.approx(0.0128, rel=0.05)
    assert float(thin1.cl_at(8.0)) == pytest.approx(1.126, abs=0.03)
    assert float(thick1.cl_at(10.0)) == pytest.approx(1.287, abs=0.03)
    # the knee is a maximum: lift falls within 4 deg past it
    assert float(thin1.cl_at(13.0)) < float(thin1.cl_at(8.5))


def test_v1_keeps_the_flat_inside_anchors():
    p = sections.polar(FoilFamily.FLAT_INSIDE, 0.092, RE, table="v1")
    assert float(p.cl_at(0.0)) == pytest.approx(0.426, abs=0.02)
    assert float(p.cl_at(4.0)) == pytest.approx(0.861, abs=0.02)
    assert float(p.cl_at(10.0)) == pytest.approx(1.361, abs=0.03)
    assert float(p.cd_at(-3.5)) == pytest.approx(0.0423, rel=0.05)
    assert float(p.cd_at(4.0)) == pytest.approx(0.0177, rel=0.06)   # v0 reads 0.0138 here
    assert float(sections.polar(FoilFamily.FLAT_INSIDE, 0.092, RE).cd_at(4.0)) < 0.015


def test_aligned_layout_keeps_one_cliff_between_two_nodes(tmp_path, monkeypatch):
    # Two nodes whose attached ranges end at -4 and -6 deg, the drag stepping from 0.01 to
    # 0.05 behind the end. Halfway between them the range ends at -5 deg in ONE step; read
    # point by point it would end in two half steps, at -4 and at -6.
    s_marks = np.array([-1.1, -1.0, 0.0, 1.0, 1.1])
    s = np.unique(np.concatenate([s_marks[0] - np.arange(0.5, 16.1, 0.5) / 10.0,
                                  np.linspace(-1.1, 1.1, 45),
                                  s_marks[-1] + np.arange(0.5, 18.1, 0.5) / 10.0]))
    marks = np.array([[-4.2, -4.0, 0.0, 9.0, 9.2], [-6.2, -6.0, 0.0, 11.0, 11.2]])
    cd = np.where(np.abs(s) <= 1.0, 0.01, 0.05)
    block = lambda v: np.repeat(np.asarray(v, dtype=float)[:, None], 2, axis=1)  # noqa: E731
    meta = {"layout": "aligned", "deg_per_s": 10.0, "alpha_range": [-16.0, 24.0], "version": 1}
    np.savez(tmp_path / "sections_v1.npz", s=s, s_marks=s_marks, tc=np.array([0.06, 0.08]),
             tc_cambered=np.array([0.06, 0.08]), camber=np.array([0.0, 0.05]),
             reynolds=np.array([1e5, 1e6]), symmetric_marks=block(marks),
             symmetric_slope=block([0.10, 0.10]), symmetric_alpha0=block([0.0, 0.0]),
             symmetric_rem=block(np.zeros((2, len(s)))), symmetric_cd=block(np.stack([cd, cd])),
             symmetric_cm=block(np.zeros((2, len(s)))), meta=np.array(json.dumps(meta)))
    assert sections.polar(FoilFamily.SYMMETRIC, 0.09, RE).attached_deg is None    # plain layout
    monkeypatch.setattr(sections, "_DATA", tmp_path)
    sections._table.cache_clear()
    sections._polar.cache_clear()
    try:
        p = sections.polar(FoilFamily.SYMMETRIC, 0.07, RE, table="v1")
        assert p.attached_deg == pytest.approx((-5.0, 10.0))
        assert p.alpha_deg[0] == -16.0 and p.alpha_deg[-1] == 24.0
        assert [float(p.cd_at(x)) for x in (-4.1, -4.9)] == pytest.approx([0.01, 0.01])
        assert [float(p.cd_at(x)) for x in (-5.3, -6.5)] == pytest.approx([0.05, 0.05])
        assert float(p.cl_at(3.0)) == pytest.approx(0.30)
    finally:
        sections._table.cache_clear()
        sections._polar.cache_clear()


def test_linear_range_is_found_from_the_peak_down():
    # below the lower end the lift is not monotonic: the linear range must not be looked up there
    a = np.arange(-16.0, 24.1, 0.5)
    cl = 0.1 * (a + 2.0)
    cl = np.where(a < -4.0, cl + 0.25, np.where(a > 10.0, 1.2 - 0.02 * (a - 10.0), cl))
    p = sections.SectionPolar(family=FoilFamily.CAMBERED, thickness_ratio=0.07, camber_ratio=0.03,
                              reynolds=RE, alpha_deg=a, cl=cl, cd=np.full_like(a, 0.01),
                              cm=np.zeros_like(a), clipped=False)
    assert p.alpha0_deg == pytest.approx(-2.0, abs=1e-9)
    assert p.slope_per_rad == pytest.approx(math.degrees(0.1))
    assert p.alpha_break_deg == pytest.approx(10.5)       # the first sample past the peak


def test_linear_range_of_an_aligned_polar_is_looked_for_inside_its_attached_range():
    # a thin section at low Reynolds number: it lets go at 3 deg and reaches twice that
    # lift again, stalled, by 16 deg. The line and the break are the attached range's.
    a = np.arange(-16.0, 24.1, 0.25)
    cl = np.where(np.abs(a) <= 3.0, 0.1 * a, np.sign(a) * (0.2 + 0.03 * (np.abs(a) - 3.0)))
    kw = dict(family=FoilFamily.SYMMETRIC, thickness_ratio=0.046, camber_ratio=0.0, reynolds=RE,
              alpha_deg=a, cl=cl, cd=np.full_like(a, 0.01), cm=np.zeros_like(a), clipped=False)
    plain = sections.SectionPolar(**kw)
    aligned = sections.SectionPolar(**kw, attached_deg=(-3.0, 3.0))
    assert aligned.slope_per_rad == pytest.approx(math.degrees(0.1))
    assert aligned.alpha_break_deg == pytest.approx(3.0)      # the end, with the lift held there
    assert aligned.cl_break == pytest.approx(0.3)
    assert plain.slope_per_rad < 0.5 * aligned.slope_per_rad  # read off the stalled branch
