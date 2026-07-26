"""The optimizer: objective correctness, graded penalties, and a seeded
micro-search that must improve on the default fin and yield a buildable solid.

These are fast tests (tier-0 analytic evaluate is milliseconds; the search is
seconds). Exactly one OCCT build is allowed — the buildability check on the
micro-optimization winner.
"""

import json
import time

import pytest

from fingen.check import check_solid
from fingen.loft import fin_solid
from fingen.optimize import (
    RiderSpec,
    default_spider_targets,
    evaluate,
    fin_from_dict,
    interference_factor,
    optimize,
    render_result_card,
    write_result_json,
)
from fingen.params import (
    FinConfig,
    FinParams,
    FoilFamily,
    FoilParams,
    GenSettings,
    OutlineParams,
)
from fingen.sizing import Skill
from fingen.spider import AXES

COARSE = GenSettings(n_stations=11, n_foil_points=60)


def _side_default() -> FinParams:
    return FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))


def test_evaluate_is_fast_and_deterministic():
    rider = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE, config=FinConfig.THRUSTER)
    fin = _side_default()
    r1 = evaluate(fin, rider)  # warm the fleet-normalization cache
    best_ms = float("inf")
    for _ in range(5):
        t0 = time.perf_counter()
        evaluate(fin, rider)
        best_ms = min(best_ms, (time.perf_counter() - t0) * 1000.0)
    assert best_ms < 50.0, f"evaluate took {best_ms:.1f} ms (budget 50 ms)"
    r2 = evaluate(fin, rider)
    assert r1.objective == r2.objective
    assert r1.spider_predicted == r2.spider_predicted
    assert set(r1.spider_predicted) == set(AXES)


def test_penalties_are_graded_and_trigger():
    # Anchor gate: a light rider on a SINGLE (one fin carries everything, so it
    # must be big) — the default side-fin-sized blade is undersized, firing an
    # area/capacity penalty. Penalties are fractional margins, not a cliff.
    single = RiderSpec(weight_kg=45.0, skill=Skill.CRUISER, config=FinConfig.SINGLE)
    res = evaluate(FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC)), single)
    assert not res.feasible
    assert any(k in res.penalties for k in ("area_low", "area_high", "capacity"))
    assert all(v > 0.0 for v in res.penalties.values())
    assert res.objective > 10.0  # penalty dominates the feasible distance scale

    # Structural gate: an absurdly thin section under a heavy aggressive rider
    # overstresses -> stress penalty (bending SF < 1).
    heavy = RiderSpec(weight_kg=95.0, skill=Skill.PRO, config=FinConfig.THRUSTER)
    thin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE,
                                     thickness_ratio=0.04, te_thickness=0.4))
    res2 = evaluate(thin, heavy)
    assert "stress" in res2.penalties and res2.penalties["stress"] > 0.0
    assert res2.margins["stress_sf"] < 1.0


def test_interference_factor_thruster_vs_isolated():
    # A thruster's fin operates in the set's downwash: the measured environment
    # factor is below 1; an isolated single fin runs at 1.
    assert interference_factor(FinConfig.SINGLE, 10.0) == 1.0
    env = interference_factor(FinConfig.THRUSTER, 10.0)
    assert 0.5 < env < 1.0


def test_targets_follow_rider():
    # The documented rider->targets mapping: heavier/more-skilled weight
    # drive+hold; beginners weight forgiveness.
    beginner = default_spider_targets(60.0, Skill.CRUISER)
    pro = default_spider_targets(95.0, Skill.PRO)
    assert pro["hold"] > beginner["hold"]
    assert pro["drive"] > beginner["drive"]
    assert beginner["forgiveness"] > pro["forgiveness"]
    for t in (beginner, pro):
        assert set(t) == set(AXES)
        assert all(0.05 <= v <= 0.95 for v in t.values())


def test_micro_optimization_improves_and_builds():
    rider = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE, config=FinConfig.THRUSTER)
    default_obj = evaluate(_side_default(), rider).objective

    result = optimize(rider, budget_evals=150, seed=0)
    assert result.result.objective < default_obj, (
        f"opt {result.result.objective:.3f} did not beat default {default_obj:.3f}")
    assert result.result.feasible
    assert result.history[-1] <= result.history[0]
    assert 0 < result.stage_boundary < len(result.history)

    # Deterministic under seed.
    again = optimize(rider, budget_evals=150, seed=0)
    assert again.result.objective == result.result.objective
    assert again.fin == result.fin

    # The winner must be a buildable, self-consistent solid (one OCCT build).
    part = fin_solid(result.fin, COARSE)
    report = check_solid(part, result.fin, COARSE)
    assert report.ok, f"winner failed check_solid: {report.issues}"


def test_cli_optimize_parse_round_trip():
    from fingen.cli import _build_parser

    args = _build_parser().parse_args(
        ["optimize", "--weight", "78", "--skill", "pro", "--config", "quad",
         "--material", "paht-cf", "--budget", "250", "--seed", "7", "--out", "o"])
    assert args.command == "optimize"
    assert args.weight == 78.0
    assert args.skill == "pro"
    assert args.config == "quad"
    assert args.material == "paht-cf"
    assert args.budget == 250
    assert args.seed == 7
    assert args.hand == "both"


def test_result_card_and_json_render(tmp_path):
    rider = RiderSpec(weight_kg=72.0, skill=Skill.INTERMEDIATE, config=FinConfig.THRUSTER)
    result = optimize(rider, budget_evals=60, seed=0)

    card = render_result_card(result, tmp_path / "card.png")
    assert card.exists() and card.stat().st_size > 1000

    js = write_result_json(result, tmp_path / "result.json")
    data = json.loads(js.read_text())
    assert set(data["spider_predicted"]) == set(AXES)
    assert set(data["spider_target"]) == set(AXES)
    assert "history" in data["search"] and data["search"]["seed"] == 0
    # The serialized fin round-trips back to the winning params.
    assert fin_from_dict(data["fin"]) == result.fin


def test_rider_speed_and_target_override():
    # speed defaults from skill; an explicit override wins and merges partial
    # spider-target overrides over the derived defaults.
    rider = RiderSpec(weight_kg=70.0, skill=Skill.ADVANCED)
    assert rider.speed == pytest.approx(7.5)
    over = RiderSpec(weight_kg=70.0, skill=Skill.ADVANCED, speed_ms=6.0,
                     spider_targets={"hold": 0.9})
    assert over.speed == pytest.approx(6.0)
    assert over.resolved_targets()["hold"] == pytest.approx(0.9)
    # untouched axes keep their derived values
    assert over.resolved_targets()["drive"] == default_spider_targets(
        70.0, Skill.ADVANCED)["drive"]
    with pytest.raises(ValueError):
        RiderSpec(weight_kg=70.0, spider_targets={"nonsense": 0.5})
    with pytest.raises(ValueError):
        RiderSpec(weight_kg=10.0)


def test_absurd_thin_fin_via_outline_is_infeasible():
    # A tiny, thin fin for a heavy rider stacks anchor + stress penalties;
    # the objective must sit far above any feasible score.
    heavy = RiderSpec(weight_kg=95.0, skill=Skill.PRO, config=FinConfig.THRUSTER)
    tiny = FinParams(outline=OutlineParams(depth=60.0, base=55.0),
                     foil=FoilParams(family=FoilFamily.FLAT_INSIDE,
                                     thickness_ratio=0.045, te_thickness=0.4))
    res = evaluate(tiny, heavy)
    assert not res.feasible
    assert res.objective > 10.0
    assert len(res.penalties) >= 2
