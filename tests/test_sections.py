"""fingen.sections: the shipped section table and its interpolation."""

import json
import math
from pathlib import Path

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
    # a request AT the table's edge is inside it (the grids are stored in single precision)
    assert not sections.polar(FoilFamily.CAMBERED, 0.05, RE, 0.03, table="v1").clipped
    assert sections.polar(FoilFamily.CAMBERED, 0.049, RE, 0.03, table="v1").clipped
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


def _referee_sections():
    """Every section of the record table v1 is built on (bench/section-tables/rerun-held):
    (name, family, t/c, camber, Re, angles / lift / drag of the rows inside its attached
    range, the bracket of its lower end or None, the bracket of its upper end). A row is past
    an end when it did not settle (a bounded cycle about a steady mean counts as settled) or
    has more than four times the section's lowest drag: the builder's own reading."""
    path = Path(__file__).resolve().parent.parent / "bench/section-tables/rerun-held/results.json"
    out = []
    for name, sec in json.loads(path.read_text())["sections"].items():
        spec = sec["spec"]
        rows = sorted(sec["rows"], key=lambda r: r["alpha"])
        a, cl, cd = (np.array([r[k] for r in rows]) for k in ("alpha", "cl", "cd"))
        settled = np.array([bool(r.get("settled", True)) or bool(r.get("cycle")) for r in rows])
        ok = settled & (cd <= 4.0 * cd[settled].min())
        lo = hi = int(np.argmin(np.where(ok, cd, np.inf)))
        while lo > 0 and ok[lo - 1]:
            lo -= 1
        while hi < len(a) - 1 and ok[hi + 1]:
            hi += 1
        out.append((name, FoilFamily(spec["family"]), spec["thickness_ratio"],
                    spec.get("camber_ratio", 0.0), spec["re"], a[lo:hi + 1], cl[lo:hi + 1],
                    cd[lo:hi + 1], (a[lo - 1], a[lo]) if lo > 0 else None, (a[hi], a[hi + 1])))
    return out


def test_v1_is_the_referee_at_its_sections():
    # Table v1 is v0 moved onto the resolved-wall RANS sections. At each of them it has to
    # BE the referee, read the way the model reads it: lift and drag of every row inside the
    # attached range, and both ends inside the quarter or half degree the referee brackets
    # them in. (As built on 2026-11-22: lift within 0.0013, drag within 1.4 %.)
    secs = _referee_sections()
    assert len(secs) == 39
    assert {fam for _, fam, *_ in secs} == set(FoilFamily)
    for name, fam, tc, camber, re, a, cl, cd, lower, upper in secs:
        p = sections.polar(fam, tc, re, camber, table="v1")
        assert not p.clipped, name
        assert np.abs(p.cl_at(a) - cl).max() < 0.005, name
        assert np.abs(p.cd_at(a) / cd - 1.0).max() < 0.03, name
        assert upper[0] <= p.attached_deg[1] <= upper[1], name
        if lower is not None:        # a symmetric section is run on one side only
            assert lower[0] <= p.attached_deg[0] <= lower[1], name


def test_v1_reads_what_the_referee_found_at_the_edges_of_the_range():
    # What the record says and v0 does not (docs/MODEL-EXTENSION.md):
    # a thin cambered section keeps its attached range going straight. 3 % camber on
    # t/c 0.07 at Re 5.7e5 is attached from -6.0 to +10.0 deg; the first referee had it
    # separated at -4.5, on an outline the mesher had cut short at the nose.
    thin = sections.polar(FoilFamily.CAMBERED, 0.07, RE, 0.03, table="v1")
    assert thin.attached_deg == pytest.approx((-6.125, 10.125), abs=0.01)
    assert float(thin.cd_at(-4.5)) < 1.2 * thin.cd_min
    assert float(thin.cd_at(0.0)) == pytest.approx(0.0122, rel=0.03)
    # past its upper end the section has let go: lift falls, drag is several times the lowest
    assert float(thin.cl_at(11.5)) < float(thin.cl_at(10.0)) - 0.2
    assert float(thin.cd_at(11.5)) > 4.0 * thin.cd_min
    # a flat inside face costs drag below about zero incidence and ends just under -4.75 deg
    # at every thickness from 0.05 to 0.12; v0 has no such end
    flat = sections.polar(FoilFamily.FLAT_INSIDE, 0.092, RE, table="v1")
    assert flat.attached_deg[0] == pytest.approx(-4.875, abs=0.01)
    assert float(flat.cd_at(-3.5)) == pytest.approx(0.0354, rel=0.03)      # 2.4 x its lowest
    assert float(flat.cd_at(-3.5)) > 2.2 * flat.cd_min
    assert float(flat.cl_at(10.0)) == pytest.approx(1.44, abs=0.02)
    # the upper end of the thin sections climbs steeply with thickness (3 % camber:
    # 6.6, 7.6, 10.1, 11.6, 13.1 deg at t/c 0.05, 0.06, 0.07, 0.075, 0.08)
    ends = [sections.polar(FoilFamily.CAMBERED, tc, RE, 0.03, table="v1").attached_deg[1]
            for tc in (0.05, 0.06, 0.07, 0.075, 0.08)]
    assert ends == pytest.approx([6.625, 7.625, 10.125, 11.625, 13.125], abs=0.01)


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


def test_cl_limit_is_the_highest_attached_lift_not_the_lift_where_the_slope_falls():
    """A lift curve that rounds over before its end: the break by slope sits inside the
    range and reads less lift than the section carries; the limit is the top."""
    a = np.arange(-4.0, 14.01, 0.25)
    # straight to 8 deg, a top of 0.9 at 10 deg, and it lets go there
    cl = np.where(a <= 8.0, 0.1 * a, 0.8 + 0.1 * (a - 8.0) - 0.025 * (a - 8.0) ** 2)
    cl = np.where(a > 10.0, 0.6, cl)
    kw = dict(family=FoilFamily.CAMBERED, thickness_ratio=0.07, camber_ratio=0.03, reynolds=5.7e5,
              alpha_deg=a, cl=cl, cd=0.01 + 0.0002 * a**2, cm=np.zeros_like(a), clipped=False)
    p = sections.SectionPolar(**kw, attached_deg=(-4.0, 10.0))
    assert p.cl_limit == pytest.approx(0.9)
    assert p.alpha_break_deg < 10.0
    assert p.cl_break < p.cl_limit
    # a table without a range (the plain layout): the lift at the break, as before
    plain = sections.SectionPolar(**kw)
    assert plain.cl_limit == plain.cl_break
