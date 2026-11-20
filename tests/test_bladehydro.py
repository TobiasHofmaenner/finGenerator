"""The lattice hydro path (RiderSpec.hydro_model = "lattice"): bladehydro + the switch."""

import dataclasses
import json
from pathlib import Path

import pytest

from fingen import bladehydro, spider
from fingen.hydro import RHO_SEAWATER, lift_curve_slope, zero_lift_alpha_deg
from fingen.optimize import RiderSpec, evaluate, fin_from_dict
from fingen.outline import metrics
from fingen.params import FinConfig, FinParams, FoilFamily, TabSystem
from fingen.sizing import Skill

BENCH = Path(__file__).parents[1] / "bench/mount/fins"
SPEED = 8.5


def _fin(name: str) -> FinParams:
    return fin_from_dict(json.loads((BENCH / name).read_text())["fin"])


def _candidate() -> FinParams:
    """bench/cambered-candidate: 4.3 % camber on t/c 0.074, the first camber-free winner."""
    raw = json.loads((BENCH.parents[1]
                      / "cambered-candidate/fins/side-cambered-candidate.json").read_text())
    return fin_from_dict(raw.get("fin", raw))


def _cambered(fin: FinParams) -> FinParams:
    return dataclasses.replace(fin, foil=dataclasses.replace(
        fin.foil, family=FoilFamily.CAMBERED, camber_ratio=0.03, camber_position=0.4))


def _rider(**kw) -> RiderSpec:
    return RiderSpec(weight_kg=60.0, skill=Skill.PRO, speed_ms=SPEED, config=FinConfig.THRUSTER,
                     material="ppa-cf", tabs=TabSystem("click_tab"), **kw)


def test_tier0_stays_the_default_and_unknown_models_are_refused():
    assert _rider().hydro_model == "tier0"
    assert spider.HYDRO_MODELS == ("tier0", "lattice", "lattice-v1", "lattice-knee")
    assert spider.SECTION_TABLE == {"lattice": "v0", "lattice-v1": "v1", "lattice-knee": "v1"}
    assert "lattice-knee" in spider.STRIP_KNEE and set(spider.SECTION_TABLE) >= spider.STRIP_KNEE
    with pytest.raises(ValueError):
        _rider(hydro_model="cfd")
    with pytest.raises(ValueError):
        spider.raw_scores(FinParams(), model="cfd")


def test_lift_curve_carries_the_blade_and_the_board():
    side = _fin("side-shipped-gen2.json")
    slope, a0, x_cp = bladehydro.lift_curve(side, SPEED)
    slope_t0, _ = lift_curve_slope(side)
    # same level as tier-0 (both sit ~8-9 % under a perfect mirror), not the same number
    assert slope == pytest.approx(slope_t0, rel=0.12)
    # zero-lift angle: set CFD and the tunnel fin say -3.5 deg for this section family;
    # the thinner tip of this blade (factor 0.78) takes some camber off
    assert -4.2 < a0 < -2.6
    assert abs(a0) < abs(zero_lift_alpha_deg(side))          # tier-0 reads the root section only
    assert -60.0 < x_cp < 20.0
    centre = _fin("centre-ridden-gen1.json")
    assert abs(bladehydro.lift_curve(centre, SPEED)[1]) < 0.3


def test_trim_drag_reads_the_flat_inside_face_at_its_toe_angle():
    # bench/foil-family and bench/mount: 11.2 / 13.4 / 16.1 N per fin at toe 2.5 / 3.5 /
    # 4.5 deg (perfect mirror), 6.4 N for the cambered twin at zero side force. Tier-0
    # reads ~5 N whatever the toe and cannot tell the two foils apart.
    side = _fin("side-shipped-gen2.json")
    d = [bladehydro.trim_drag_n(side, SPEED, toe) for toe in (2.5, 3.5, 4.5)]
    assert d[0] < d[1] < d[2]
    assert d[1] == pytest.approx(13.4, rel=0.25)
    assert d[2] - d[0] == pytest.approx(16.1 - 11.2, rel=0.35)
    assert bladehydro.trim_drag_n(_cambered(side), SPEED, 3.5) < 0.5 * d[1]
    assert spider.trim_drag_n(side, SPEED, 3.5) < 0.5 * d[1]          # the tier-0 reading


def test_drag_at_force_meets_the_force_or_stops_at_the_cap():
    side = _fin("side-shipped-gen2.json")
    drag, lift = bladehydro.drag_at_force_n(side, SPEED, 150.0, alpha_max_deg=10.0)
    assert lift == pytest.approx(150.0, rel=0.03) and 5.0 < drag < 25.0
    drag_c, lift_c = bladehydro.drag_at_force_n(side, SPEED, 2000.0, alpha_max_deg=6.0)
    qa = 0.5 * RHO_SEAWATER * SPEED**2 * metrics(side.outline).area * 1e-6
    assert lift_c < 2000.0
    assert lift_c == pytest.approx(bladehydro.point(side, SPEED, 6.0)[0].cl * qa)
    assert drag_c > drag


def test_evaluate_under_the_lattice_model_tells_the_two_foils_apart():
    side, twin = _fin("side-shipped-gen2.json"), _cambered(_fin("side-shipped-gen2.json"))
    lat = _rider(hydro_model="lattice")
    flat_l, camb_l = evaluate(side, lat), evaluate(twin, lat)
    flat_0, camb_0 = evaluate(side, _rider()), evaluate(twin, _rider())
    assert set(flat_l.spider_predicted) == set(spider.AXES)
    # tier-0: the two foils are the same fin on speed and drive
    for axis in ("speed", "drive"):
        assert camb_0.spider_predicted[axis] == pytest.approx(flat_0.spider_predicted[axis],
                                                              abs=2.0)
    # lattice: the cambered foil is faster in trim and cruises cleaner
    assert camb_l.spider_predicted["speed"] > flat_l.spider_predicted["speed"] + 30.0
    assert camb_l.spider_predicted["drive"] > flat_l.spider_predicted["drive"] + 20.0
    # structure is untouched by the switch
    for key in ("stress_sf", "tip_deflection_mm", "f_wet_hz"):
        assert flat_l.margins[key] == pytest.approx(flat_0.margins[key], rel=1e-9)


def test_symmetric_centre_reads_similarly_under_both_models():
    centre = _fin("centre-ridden-gen1.json")
    t0 = spider.trim_drag_n(centre, SPEED)
    lat = bladehydro.trim_drag_n(centre, SPEED, 0.0)
    assert lat == pytest.approx(t0, rel=0.35)       # no camber, no toe: little to disagree on
    scores = spider.normalized_scores(centre, SPEED, 60.0, model="lattice")
    assert all(0.0 <= v <= 100.0 for v in scores.values())


def test_section_table_v1_prices_a_thin_cambered_blade_on_the_edge_of_its_range():
    # bench/cambered-candidate: 4.3 % camber on t/c 0.074. Going straight at the 3.5 deg
    # toe it works at -2.5..-4.5 deg; resolved-wall RANS has thin cambered sections leave
    # their attached range between -3.5 and -4.5 deg, table v0 a degree later
    # (docs/MODEL-EXTENSION.md, "The cambered candidate was a second exploit").
    cand = _candidate()
    v0 = bladehydro.trim_drag_n(cand, SPEED, 3.5)
    v1 = bladehydro.trim_drag_n(cand, SPEED, 3.5, "v1")
    assert v0 == pytest.approx(5.4, abs=0.3)
    assert 6.0 < v1 < 9.0
    # the thicker 3 % blade keeps most of its range and moves by under a newton
    twin = _cambered(_fin("side-shipped-gen2.json"))
    assert 0.3 < (bladehydro.trim_drag_n(twin, SPEED, 3.5, "v1")
                  - bladehydro.trim_drag_n(twin, SPEED, 3.5)) < 1.3
    # lift is the same blade: within 0.02 in CL across the working range
    for a in (-3.5, 0.0, 4.0):
        assert bladehydro.point(cand, SPEED, a, "v1")[0].cl == pytest.approx(
            bladehydro.point(cand, SPEED, a)[0].cl, abs=0.02)


def test_evaluate_reads_the_table_its_model_names():
    cand = _candidate()
    e0 = evaluate(cand, _rider(hydro_model="lattice", scoring="frontier"))
    e1 = evaluate(cand, _rider(hydro_model="lattice-v1", scoring="frontier"))
    assert e0.margins["trim_drag_n"] == pytest.approx(bladehydro.trim_drag_n(cand, SPEED, 3.5))
    assert e1.margins["trim_drag_n"] == pytest.approx(
        bladehydro.trim_drag_n(cand, SPEED, 3.5, "v1"))
    assert e1.margins["trim_drag_n"] > e0.margins["trim_drag_n"] + 0.7



def test_knee_sits_on_the_tunnel_fin_and_comes_earlier_on_a_slender_blade():
    # [BW04] tunnel fin (AR 1.5): lift on its line to 12 deg, 6 % below it at 14.
    # KNEE_FRACTION is fitted to put its knee at 12 deg; nothing else is fitted.
    from fingen.params import FoilParams, OutlineParams

    bw04 = FinParams(outline=OutlineParams(depth=120.0, base=100.0, sweep=25.0,
                                           tip_width_ratio=0.45, le_fullness=0.75, te_shape=0.8),
                     foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.09),
                     thickness_tip_factor=1.0)
    a_bw04, cl_bw04 = bladehydro.knee(bw04, 7.0, "v1")
    assert a_bw04 == pytest.approx(12.0, abs=0.4)
    assert cl_bw04 == pytest.approx(0.80, abs=0.05)
    # the shipped gen-2 side (AR 2.0): its level-2 and level-5 polars leave their line
    # between 4 and 8 deg (bench/foil-family, bench/cambered-candidate/mesh-level-5);
    # the aspect-ratio rule holds it to 12
    side = _fin("side-shipped-gen2.json")
    a_side, cl_side = bladehydro.knee(side, SPEED, "v1")
    assert 6.0 < a_side < 9.0
    assert cl_side < cl_bw04
    # a low wide blade keeps its line longer (bench/paddle-probe: 12-16 deg)
    paddle = fin_from_dict(json.loads(
        (BENCH.parents[1] / "paddle-probe/fins/side-paddle-probe.json").read_text()).get("fin", {}))
    assert bladehydro.knee(paddle, SPEED, "v1")[0] > a_bw04 + 2.0


def test_lattice_knee_model_moves_hold_and_nothing_below_the_knee():
    side = _fin("side-shipped-gen2.json")
    v1 = evaluate(side, _rider(hydro_model="lattice-v1", scoring="frontier"))
    kn = evaluate(side, _rider(hydro_model="lattice-knee", scoring="frontier"))
    assert kn.margins["trim_drag_n"] == pytest.approx(v1.margins["trim_drag_n"])
    assert kn.margins["hold_ratio"] < 0.8 * v1.margins["hold_ratio"]
    assert kn.margins["margin_peak_deg"] < v1.margins["margin_peak_deg"] - 3.0


def test_hold_floor_under_the_strip_knee_is_the_gen2_sides_level():
    # Decision D11: where the knee is read off the strips, hold is anchored on fins
    # of known behaviour. The gen-2 side (it holds) defines the floor; the gen-1
    # side that slid is below it. The gate in degrees, set against the 12 deg
    # rule, does not apply there.
    from fingen.optimize import HOLD_ASPIRATION_KNEE, HOLD_FLOOR_KNEE

    knee = _rider(hydro_model="lattice-knee", scoring="frontier", peak_margin_min_deg=2.0)
    gen2 = evaluate(_fin("side-shipped-gen2.json"), knee)
    gen1 = evaluate(_fin("side-asridden-gen1.json"), knee)
    assert HOLD_FLOOR_KNEE <= gen2.margins["hold_ratio"] < HOLD_FLOOR_KNEE + 0.03
    assert "hold_min" not in gen2.penalties and "peak_margin" not in gen2.penalties
    assert gen1.margins["hold_ratio"] < HOLD_FLOOR_KNEE - 0.08
    assert gen1.penalties["hold_min"] > 0.1 and not gen1.feasible
    assert any("below the floor" in issue for issue in gen1.issues)
    assert not any("will slide" in issue for issue in gen2.issues)
    assert knee.resolved_aspirations()["hold"] == HOLD_ASPIRATION_KNEE
    # the rider's own numbers still win, and the other models keep theirs
    own = _rider(hydro_model="lattice-knee", scoring="frontier", hold_min=0.9,
                 aspirations={"hold": 1.0})
    assert "hold_min" in evaluate(_fin("side-shipped-gen2.json"), own).penalties
    assert own.resolved_aspirations()["hold"] == 1.0
    rule = _rider(hydro_model="lattice-v1", scoring="frontier", peak_margin_min_deg=2.0)
    assert rule.resolved_hold_min() is None and rule.resolved_aspirations()["hold"] == 1.15
    assert "peak_margin" in evaluate(_fin("side-shipped-gen2.json"), rule).penalties


def test_lean_angle_given_directly_is_the_skill_levels_own():
    # GEN3-PLAN 1.0: the rider sets lean angle and speed, not a skill label. A lean
    # angle that happens to be a level's own must give exactly that level's fin
    # loads; one between two levels lies between them.
    from fingen.optimize import _P_DESIGN_RAD_S, design_roll_rate_rad_s

    side = _fin("side-shipped-gen2.json")
    by_skill = evaluate(side, _rider(scoring="frontier"))                  # PRO = 55 deg
    direct = dataclasses.replace(_rider(scoring="frontier"), skill=Skill.CRUISER, bank_deg=55.0)
    by_angle = evaluate(side, direct)
    assert direct.bank == 55.0 and _rider().bank == 55.0
    for key in ("hold_ratio", "stress_sf", "stress_sf_roll", "trim_drag_n", "alpha_peak_deg"):
        assert by_angle.margins[key] == pytest.approx(by_skill.margins[key]), key
    for skill, rate in _P_DESIGN_RAD_S.items():
        assert design_roll_rate_rad_s(skill.value) == pytest.approx(rate)
    between = evaluate(side, dataclasses.replace(direct, bank_deg=44.0))
    softer = evaluate(side, dataclasses.replace(direct, bank_deg=40.0))
    holds = [e.margins["hold_ratio"] for e in (softer, between, by_angle)]
    assert holds[0] > holds[1] > holds[2]
    with pytest.raises(ValueError, match="bank_deg"):
        _rider(bank_deg=70.0)
