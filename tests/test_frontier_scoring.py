"""Frontier scoring: goods in physical units, one-sided (RiderSpec.scoring = "frontier")."""

import dataclasses
import json
from pathlib import Path

import pytest

from fingen.optimize import (
    DEFAULT_ASPIRATIONS,
    FRONTIER_RHO,
    PENALTY_WEIGHT,
    RiderSpec,
    board_drag_n,
    evaluate,
    fin_from_dict,
    frontier_achievement,
)
from fingen.params import FinConfig, FoilFamily, TabSystem
from fingen.sizing import Skill

BENCH = Path(__file__).parents[1] / "bench/mount/fins"


def _rider(**kw) -> RiderSpec:
    return RiderSpec(weight_kg=60.0, skill=Skill.PRO, speed_ms=8.5, config=FinConfig.THRUSTER,
                     material="ppa-cf", tabs=TabSystem("click_tab"), **kw)


def _goods(**kw) -> dict:
    d = board_drag_n(60.0)
    g = {"trim_drag_n": 0.04 * d, "work_drag_n": 0.05 * d, "hold": 1.15}
    return {**g, **kw}


TASTES = {"yaw_stiffness_nm_rad": 300.0, "roll_damping_nm_s": 0.45}


def test_targets_stay_the_default_and_bad_specs_are_refused():
    assert _rider().scoring == "targets"
    assert _rider().resolved_aspirations() == DEFAULT_ASPIRATIONS
    assert _rider(aspirations={"hold": 1.4}).resolved_aspirations()["hold"] == 1.4
    for bad in ({"scoring": "pareto"}, {"aspirations": {"speed": 1.0}},
                {"taste_bands": {"release": (0.1, 0.2)}},
                {"taste_bands": {"roll_damping_nm_s": (0.5, 0.2)}}):
        with pytest.raises(ValueError):
            _rider(**bad)


def test_board_drag_yardstick():
    assert board_drag_n(60.0) == pytest.approx(63.0 * 9.81 / 5.0)


def test_at_the_aspiration_point_every_shortfall_is_zero():
    value, d = frontier_achievement(_goods(), TASTES, _rider(scoring="frontier"))
    assert value == pytest.approx(0.0, abs=1e-12)
    assert all(abs(v) < 1e-12 for v in d.values())


def test_every_good_is_one_sided_overshoot_is_rewarded_never_taxed():
    # The defect of the two-sided spider distance: beating a target cost as much
    # as missing it. Here each good, improved alone from the aspiration point and
    # then improved again, must keep lowering the objective.
    r = _rider(scoring="frontier")
    base, _ = frontier_achievement(_goods(), TASTES, r)
    d = board_drag_n(60.0)
    for key, better, best in (("trim_drag_n", 0.03 * d, 0.02 * d),
                              ("work_drag_n", 0.04 * d, 0.03 * d),
                              ("hold", 1.35, 1.6)):
        v1, _ = frontier_achievement(_goods(**{key: better}), TASTES, r)
        v2, _ = frontier_achievement(_goods(**{key: best}), TASTES, r)
        assert v2 < v1 < base, key


def test_the_worst_served_good_leads_and_steps_are_noticeable_differences():
    r = _rider(scoring="frontier")
    d = board_drag_n(60.0)
    step = 0.05 * d / 2.0                                   # 5 % of board drag, shared by the pair
    value, short = frontier_achievement(_goods(trim_drag_n=0.04 * d + 2.0 * step, hold=1.35),
                                        TASTES, r)
    assert short["trim_drag"] == pytest.approx(2.0)         # two steps short
    assert short["hold"] == pytest.approx(-1.0)             # one step (20 % of peak force) past
    assert value == pytest.approx(2.0 + FRONTIER_RHO * (2.0 - 1.0))
    # a centre fin carries the set's drag step alone
    _, short_c = frontier_achievement(_goods(trim_drag_n=0.04 * d + 2.0 * step), TASTES, r,
                                      rear_member=True)
    assert short_c["trim_drag"] == pytest.approx(1.0)


def test_taste_bands_are_free_inside_and_cost_outside():
    r = _rider(scoring="frontier", taste_bands={"roll_damping_nm_s": (0.40, 0.50)})
    inside, _ = frontier_achievement(_goods(), TASTES, r)
    outside, d = frontier_achievement(_goods(), {**TASTES, "roll_damping_nm_s": 0.65}, r)
    assert inside == pytest.approx(0.0, abs=1e-12)
    assert d["roll_damping_nm_s"] == pytest.approx((0.65 - 0.50) / 0.50 / 0.30)
    assert outside == pytest.approx(d["roll_damping_nm_s"])


def test_evaluate_reports_the_goods_and_scores_a_cleaner_foil_better():
    side = fin_from_dict(json.loads((BENCH / "side-shipped-gen2.json").read_text())["fin"])
    twin = dataclasses.replace(side, foil=dataclasses.replace(
        side.foil, family=FoilFamily.CAMBERED, camber_ratio=0.03, camber_position=0.4))
    r = _rider(scoring="frontier", hydro_model="lattice")
    flat, camb = evaluate(side, r), evaluate(twin, r)
    for e in (flat, camb):
        for key in ("trim_drag_n", "work_drag_n", "hold_ratio", "margin_peak_deg",
                    "shortfall_trim_drag", "shortfall_hold"):
            assert key in e.margins
        assert e.objective == pytest.approx(e.distance + PENALTY_WEIGHT * e.penalty)
    # the flat inside face is three steps short on trim drag; the cambered twin is not
    assert flat.margins["shortfall_trim_drag"] > 2.5
    assert camb.margins["shortfall_trim_drag"] < 0.5
    assert camb.objective < flat.objective
    # the goods are reported under the default scoring too, without driving it
    plain = evaluate(side, _rider(hydro_model="lattice"))
    assert plain.margins["trim_drag_n"] == pytest.approx(flat.margins["trim_drag_n"])
    assert not any(k.startswith("shortfall_") for k in plain.margins)


def test_the_reserve_is_one_good_counted_once():
    # Hold (F_max / F_peak) and the peak margin in degrees are the same reserve:
    # margin = (alpha_break - alpha_zero) * (1 - 1 / hold). The first cut scored
    # both; the double credit opened a second valley at the largest fin the
    # sliders can draw, and six searches of six ended in it where the lean fin
    # scored better under the same rule (docs/MODEL-EXTENSION.md). The margin is
    # reported and gated, never an aspiration.
    assert "margin_deg" not in DEFAULT_ASPIRATIONS
    with pytest.raises(ValueError):
        _rider(aspirations={"margin_deg": 4.0})
    r = _rider(scoring="frontier")
    _, d = frontier_achievement(_goods(), TASTES, r)
    assert set(d) == {"trim_drag", "work_drag", "hold"}
    # the two ends of the measured line, in steps (lean 9 996 mm2, oversized 15 433 mm2)
    board = board_drag_n(60.0)
    step = 0.05 * board / 2.0
    lean, _ = frontier_achievement(
        _goods(trim_drag_n=0.04 * board + 0.05 * step, work_drag_n=0.05 * board + 0.05 * step,
               hold=1.14), TASTES, r)
    oversized, _ = frontier_achievement(
        _goods(trim_drag_n=0.04 * board + 0.54 * step, work_drag_n=0.05 * board + 0.61 * step,
               hold=1.62), TASTES, r)
    assert lean < oversized - 0.3


def test_the_margin_and_the_hold_ratio_move_together():
    side = fin_from_dict(json.loads((BENCH / "side-shipped-gen2.json").read_text())["fin"])
    r = _rider(scoring="frontier", hydro_model="lattice")
    rows = []
    for scale in (0.9, 1.0, 1.1, 1.25):
        o = side.outline
        fin = dataclasses.replace(side, outline=dataclasses.replace(o, depth=o.depth * scale))
        m = evaluate(fin, r).margins
        rows.append((m["hold_ratio"], m["margin_peak_deg"]))
    holds, margins = zip(*rows, strict=True)
    assert list(holds) == sorted(holds) and list(margins) == sorted(margins)
    # below one the fin cannot make the turn at any angle: the margin is negative exactly there
    assert all((h < 1.0) == (g < 0.0) for h, g in rows)
