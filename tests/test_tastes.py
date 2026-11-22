"""Tastes given relative to the balanced fin (GEN3-PLAN 1.7): `optimize_with_tastes`."""

import dataclasses
import json
from pathlib import Path

import pytest

import fingen.optimize as opt
from fingen.optimize import (
    TASTES,
    OptimizationResult,
    RiderSpec,
    evaluate,
    fin_from_dict,
    optimize_with_tastes,
    taste_bands_from_multiples,
    tasted_result_to_dict,
)
from fingen.params import FinConfig, FinParams, FoilFamily, TabSystem
from fingen.sizing import Skill

BENCH = Path(__file__).resolve().parent.parent / "bench"
YAW, ROLL = TASTES


def _rider(**kw) -> RiderSpec:
    return RiderSpec(weight_kg=60.0, skill=Skill.PRO, speed_ms=8.5, config=FinConfig.THRUSTER,
                     material="ppa-cf", tabs=TabSystem("click_tab"), hydro_model="lattice-knee",
                     side_foil="cambered", scoring="frontier", **kw)


def _gen2_cambered() -> FinParams:
    fin = fin_from_dict(json.loads(
        (BENCH / "foil-family/fins/side-shipped-gen2.json").read_text())["fin"])
    return dataclasses.replace(fin, foil=dataclasses.replace(
        fin.foil, family=FoilFamily.CAMBERED, camber_ratio=0.03, camber_position=0.4))


def _smaller(fin: FinParams) -> FinParams:
    return dataclasses.replace(fin, outline=dataclasses.replace(
        fin.outline, depth=fin.outline.depth - 20.0))


def _stub(calls: list, banded_fin: FinParams):
    """`optimize` replaced: the gen-2 planform with camber for a rider without taste bands,
    `banded_fin` for one with; every call is noted."""
    def fake(rider, budget_evals=4000, seed=0, workers=None, progress=None):
        calls.append(rider)
        fin = banded_fin if rider.taste_bands else _gen2_cambered()
        return OptimizationResult(fin=fin, result=evaluate(fin, rider), rider=rider, history=[0.0],
                                  stage_boundary=0, n_evals=budget_evals, seed=seed,
                                  grooves_enabled=False)
    return fake


def test_a_multiple_below_one_is_an_upper_bound_and_above_one_a_lower_bound():
    ref = {YAW: 240.0, ROLL: 0.45}
    bands = taste_bands_from_multiples(ref, {YAW: 0.8, ROLL: 1.25})
    assert bands[YAW][1] == pytest.approx(192.0) and bands[YAW][0] < 1e-3
    assert bands[ROLL][0] == pytest.approx(0.5625) and bands[ROLL][1] > 1e3
    # the bands are what RiderSpec accepts
    assert _rider(taste_bands=bands).taste_bands == bands
    # within two percent of 1 the balanced fin is what is asked for
    assert taste_bands_from_multiples(ref, {YAW: 1.0, ROLL: 0.99}) == {}
    with pytest.raises(ValueError):
        taste_bands_from_multiples(ref, {"pivot": 0.8})
    with pytest.raises(ValueError):
        taste_bands_from_multiples(ref, {YAW: 0.0})


def test_no_taste_asked_is_one_search_and_the_balanced_fin(monkeypatch):
    calls: list = []
    monkeypatch.setattr(opt, "optimize", _stub(calls, _gen2_cambered()))
    out = optimize_with_tastes(_rider(), {YAW: 1.0, ROLL: 1.0}, budget_evals=50)
    assert len(calls) == 1 and calls[0].taste_bands is None
    assert out.tasted is None and out.chosen is out.balanced and out.n_evals == 50
    assert out.bands == {} and all(out.reached.values())
    assert out.reference[YAW] == pytest.approx(out.balanced.result.margins[YAW])
    assert tasted_result_to_dict(out)["tasted"] is None


def test_a_taste_is_held_to_a_band_around_the_balanced_fins_own_value(monkeypatch):
    calls: list = []
    looser = _smaller(_gen2_cambered())
    monkeypatch.setattr(opt, "optimize", _stub(calls, looser))
    out = optimize_with_tastes(_rider(), {YAW: 0.8}, budget_evals=50, seed=3)
    # the balanced fin first, then the same rider with the band its yaw stiffness makes
    assert [c.taste_bands is None for c in calls] == [True, False]
    ref = evaluate(_gen2_cambered(), _rider()).margins
    assert out.reference == {YAW: pytest.approx(ref[YAW]), ROLL: pytest.approx(ref[ROLL])}
    assert set(out.bands) == {YAW} and out.bands[YAW][1] == pytest.approx(0.8 * ref[YAW])
    assert calls[1].taste_bands == out.bands
    assert out.multiples == {YAW: 0.8, ROLL: 1.0}
    assert out.chosen is out.tasted and out.n_evals == 100
    # where the second fin ended, as a multiple of the balanced one, and whether inside
    got = evaluate(looser, calls[1]).margins[YAW] / ref[YAW]
    assert out.achieved[YAW] == pytest.approx(got) and got < 1.0
    assert out.reached[YAW] is (got <= 0.8 * 1.03) and out.reached[ROLL] is True
    # both fins carry their shortfalls in felt steps; the banded one also the taste's
    assert "shortfall_hold" in out.balanced.result.margins
    assert f"shortfall_{YAW}" in out.tasted.result.margins
    data = tasted_result_to_dict(out)
    assert data["tastes"][YAW]["band"][1] == pytest.approx(0.8 * ref[YAW])
    assert data["tastes"][ROLL] == {"multiple": 1.0, "reference": pytest.approx(ref[ROLL]),
                                    "band": None, "achieved_multiple": pytest.approx(
                                        out.achieved[ROLL]), "reached": True}
    json.dumps(data)


def test_a_band_that_is_not_reached_is_reported_not_raised(monkeypatch):
    # asked for 40 % stiffer; the second search comes back with the same fin
    calls: list = []
    monkeypatch.setattr(opt, "optimize", _stub(calls, _gen2_cambered()))
    out = optimize_with_tastes(_rider(), {YAW: 1.4}, budget_evals=50)
    assert out.bands[YAW][0] == pytest.approx(1.4 * out.reference[YAW])
    assert out.achieved[YAW] == pytest.approx(1.0) and out.reached[YAW] is False
    assert out.tasted.result.margins[f"shortfall_{YAW}"] > 0.9      # 0.4 / 1.4 over the step of 0.3


def test_tastes_need_frontier_scoring_and_no_bands_of_the_riders_own():
    with pytest.raises(ValueError, match="frontier"):
        optimize_with_tastes(dataclasses.replace(_rider(), scoring="targets"), {YAW: 0.8})
    with pytest.raises(ValueError, match="not both"):
        optimize_with_tastes(_rider(taste_bands={YAW: (1.0, 200.0)}), {YAW: 0.8})
    with pytest.raises(ValueError, match="unknown"):
        optimize_with_tastes(_rider(), {"pivot": 0.8})


def test_the_two_searches_run_end_to_end_on_a_small_budget():
    out = optimize_with_tastes(_rider(), {YAW: 0.7}, budget_evals=120, seed=0, workers=1)
    assert out.tasted is not None
    assert out.n_evals == out.balanced.n_evals + out.tasted.n_evals
    assert out.bands[YAW][1] == pytest.approx(0.7 * out.reference[YAW])
    assert out.tasted.rider.taste_bands == out.bands and out.balanced.rider.taste_bands is None
    assert out.achieved[YAW] == pytest.approx(
        out.tasted.result.margins[YAW] / out.balanced.result.margins[YAW])
    assert tasted_result_to_dict(out)["tastes"][YAW]["multiple"] == 0.7
