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
    DECODE_PENALTY,
    RiderSpec,
    default_spider_targets,
    evaluate,
    fin_from_dict,
    interference_factor,
    optimize,
    render_result_card,
    result_to_dict,
    write_result_json,
)
from fingen.params import (
    FinConfig,
    FinParams,
    FoilFamily,
    FoilParams,
    GenSettings,
    OutlineParams,
    TabParams,
    TabSystem,
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

    # Budget 400: the seven-axis objective (the stability/roll axis was added on
    # top of the original six) makes the tuned template start a harder point to
    # beat, so the micro-search needs a few hundred evals — not the old 150 — to
    # clear it; at 400 it improves by a clear margin and still builds one solid.
    result = optimize(rider, budget_evals=400, seed=0)
    assert result.result.objective < default_obj, (
        f"opt {result.result.objective:.3f} did not beat default {default_obj:.3f}")
    assert result.result.feasible
    assert result.history[-1] <= result.history[0]
    assert 0 < result.stage_boundary < len(result.history)

    # Deterministic under seed.
    again = optimize(rider, budget_evals=400, seed=0)
    assert again.result.objective == result.result.objective
    assert again.fin == result.fin

    # The winner must be a buildable, self-consistent solid (one OCCT build).
    part = fin_solid(result.fin, COARSE)
    report = check_solid(part, result.fin, COARSE)
    assert report.ok, f"winner failed check_solid: {report.issues}"


def test_rider_tab_system_gates_the_base_chord():
    """The rider's BOARD mounting system must reach the gates: FCS II tabs span
    98 mm, so a blade with too short a base cannot mount. Without this the
    optimizer happily ships an unmountable fin (it did)."""
    from fingen.params import TabSystem

    short_base = FinParams(
        outline=OutlineParams(depth=124.0, base=99.0, sweep=29.0),
        foil=FoilParams(family=FoilFamily.FLAT_INSIDE))

    glass = RiderSpec(weight_kg=46.0, skill=Skill.ADVANCED, config=FinConfig.THRUSTER)
    fcs2 = RiderSpec(weight_kg=46.0, skill=Skill.ADVANCED, config=FinConfig.THRUSTER,
                     tabs=TabSystem.CLICK_TAB)

    assert "base_min" not in evaluate(short_base, glass).penalties
    res = evaluate(short_base, fcs2).penalties
    assert res["base_min"] > 0.0  # graded fractional margin, not a cliff

    # And the search must then DESIGN a mountable blade.
    result = optimize(fcs2, budget_evals=400, seed=0)
    assert result.fin.tabs.system is TabSystem.CLICK_TAB
    assert result.fin.outline.base >= 104.0, result.fin.outline.base
    assert result.center is not None and result.center.tabs.system is TabSystem.CLICK_TAB
    assert result.center.outline.base >= 104.0, result.center.outline.base


def test_thruster_center_is_designed_not_the_template_default():
    """A thruster rider gets a CO-DESIGNED symmetric center, not the stock
    _default_center() (an adult 115x110 blade) — the whole point of the set
    stage. The center is scored as the aft member (Falk downwash), so its
    reported env_factor must be below 1."""
    rider = RiderSpec(weight_kg=46.0, skill=Skill.ADVANCED, config=FinConfig.THRUSTER)
    result = optimize(rider, budget_evals=400, seed=0)

    assert result.center is not None and result.center_result is not None
    # Symmetric 50/50 section: a center fin works both ways off the stringer.
    assert result.center.foil.family is FoilFamily.SYMMETRIC
    # Not the template default blade.
    default_center = FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC))
    assert result.center.outline != default_center.outline
    # Scored in the set's downwash, not as an isolated fin.
    assert 0.5 < result.center_result.margins["env_factor"] < 1.0
    # The set is assembled and ready for placement/export.
    assert result.fin_set is not None
    assert result.fin_set.center is result.center
    assert result.fin_set.side is result.fin

    # Deterministic under seed, like the side path.
    again = optimize(rider, budget_evals=400, seed=0)
    assert again.center == result.center


def test_center_design_respects_the_eval_budget():
    """The center search is carved OUT of budget_evals, not spent on top of it:
    a co-designed thruster must not silently cost 1.5x the requested budget.
    (CMA spends whole generations, so allow one population of slack.)"""
    rider = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE, config=FinConfig.THRUSTER)
    result = optimize(rider, budget_evals=300, seed=0)
    assert result.n_evals <= 300 * 1.15, f"budget blown: {result.n_evals} for 300"


def test_non_center_configs_are_unchanged():
    """Only center-design configs (thruster) grow a center; single/twin/quad
    keep the single-blade contract exactly as before."""
    for config in (FinConfig.SINGLE, FinConfig.TWIN, FinConfig.QUAD):
        rider = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE, config=config)
        result = optimize(rider, budget_evals=150, seed=0)
        assert result.center is None
        assert result.center_result is None
        assert result.fin_set is None
        assert "center_fin" not in result_to_dict(result)


def test_set_report_carries_penalties_and_feasibility():
    """The reported set objective must be penalty-INCLUSIVE (like every other
    reported objective) so an infeasible member can never read as a healthy
    set, and feasibility must be surfaced explicitly."""
    rider = RiderSpec(weight_kg=46.0, skill=Skill.ADVANCED, config=FinConfig.THRUSTER)
    d = result_to_dict(optimize(rider, budget_evals=300, seed=0))

    assert {"objective", "distance", "feasible"} <= set(d["set"])
    # Penalty-inclusive: never below the pure spider blend.
    assert d["set"]["objective"] >= d["set"]["distance"] - 1e-9
    assert d["set"]["feasible"] == (d["feasible"] and d["center"]["feasible"])
    assert "center_fin" in d


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


def test_formerly_crashing_seeds_now_complete():
    # Review finding: chord_schedule ValueErrors beyond _decode aborted the
    # whole search (75kg/thruster/seed 8 crashed deterministically).
    rider = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE,
                      config=FinConfig.THRUSTER)
    result = optimize(rider, budget_evals=300, seed=8)
    assert result.result.objective < DECODE_PENALTY


def test_winner_is_a_plausible_fin():
    # Review finding: pancakes (base 3.5x depth) and 165mm-deep "side fins"
    # shipped as feasible. The practical corridor must keep winners saleable.
    rider = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE,
                      config=FinConfig.THRUSTER)
    result = optimize(rider, budget_evals=250, seed=0)
    out = result.fin.outline
    assert out.depth <= 150.0, out.depth          # corridor 90-140 + slack
    assert out.depth >= 80.0, out.depth
    from fingen.outline import metrics
    ar = metrics(out).aspect_ratio
    assert 0.95 <= ar <= 2.8, ar                   # no pancakes, no needles


def test_dominant_blade_carries_no_rear_deficit():
    # Review finding: the measured rear-fin deficit was applied to the front
    # blade the optimizer builds. env is 1.0 for the dominant blade now.
    rider = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE,
                      config=FinConfig.THRUSTER)
    res = evaluate(FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE)),
                   rider)
    assert res.margins["env_factor"] == 1.0


def test_roll_metrics_reported_but_not_in_objective(monkeypatch):
    # The roll REPORT MARGINS stay report-only. evaluate() surfaces the blade's
    # damping/inertia/tau/agility and the set-level damping on margins via
    # opt.roll_report/opt.roll_set_report; those numbers must NOT feed the
    # objective. (This is DISTINCT from the stability spider axis, which enters
    # the objective through spider.raw_scores -> spider.roll_report — a separate
    # import path this patch deliberately does not touch; the stability axis is
    # pinned separately in test_stability_axis_*.) A deeper blade must read more
    # roll damping and less agility, and the thruster set damps more than the
    # lone blade.
    import dataclasses

    import fingen.optimize as opt

    rider = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE,
                      config=FinConfig.THRUSTER)
    side = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    res = evaluate(side, rider)
    for key in ("roll_damping_nm_s", "roll_inertia_kgm2", "roll_tau_ms",
                "roll_agility", "roll_set_damping_nm_s"):
        assert key in res.margins and res.margins[key] > 0.0
    # Set (center + side pair) damps more than the single dominant blade.
    assert res.margins["roll_set_damping_nm_s"] > res.margins["roll_damping_nm_s"]
    deep = FinParams(outline=OutlineParams(depth=135, base=95, sweep=33,
                                           tip_width_ratio=0.35),
                     foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    res_deep = evaluate(deep, rider)
    assert res_deep.margins["roll_damping_nm_s"] > res.margins["roll_damping_nm_s"]
    assert res_deep.margins["roll_agility"] < res.margins["roll_agility"]

    # The report-must-not-leak pin. Patch the roll reports evaluate() consumes
    # for its MARGINS (opt.roll_report/opt.roll_set_report) so the damping/inertia
    # they hand back are scaled by a huge factor. If any of those REPORT numbers
    # leaked into the objective, that ×137 swing would move the scored outputs.
    # They must stay BITWISE identical while the roll MARGINS move by exactly the
    # injected factor. (The stability axis rides spider.roll_report, untouched
    # here, so the objective legitimately still depends on roll through THAT path
    # — see test_stability_axis_in_objective.)
    K = 137.0
    real_report = opt.roll_report
    real_set = opt.roll_set_report

    def scaled_report(*a, **k):
        rep = real_report(*a, **k)
        return dataclasses.replace(rep, l_p=rep.l_p * K,
                                   added_inertia_kgm2=rep.added_inertia_kgm2 * K)

    def scaled_set(*a, **k):
        rep = real_set(*a, **k)
        return dataclasses.replace(
            rep, roll_damping_nm_s=rep.roll_damping_nm_s * K,
            added_inertia_kgm2=rep.added_inertia_kgm2 * K)

    monkeypatch.setattr(opt, "roll_report", scaled_report)
    monkeypatch.setattr(opt, "roll_set_report", scaled_set)
    patched = evaluate(side, rider)

    # Scored outputs: byte-for-byte identical (roll never enters them).
    assert patched.objective == res.objective
    assert patched.distance == res.distance
    assert patched.penalty == res.penalty
    assert patched.spider_predicted == res.spider_predicted
    # Report-only margins: moved by exactly the injected factor (proves the
    # patched reports really are the ones evaluate() read).
    assert patched.margins["roll_damping_nm_s"] == pytest.approx(
        K * res.margins["roll_damping_nm_s"])
    assert patched.margins["roll_inertia_kgm2"] == pytest.approx(
        K * res.margins["roll_inertia_kgm2"])
    assert patched.margins["roll_set_damping_nm_s"] == pytest.approx(
        K * res.margins["roll_set_damping_nm_s"])


def test_washout_actually_reaches_the_score(monkeypatch):
    # Review finding: dropping the washout multiplication would survive the
    # suite. Pin: a larger flex knockdown must lower hold/drive.
    import fingen.optimize as opt

    rider = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE,
                      config=FinConfig.THRUSTER)
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    base = evaluate(fin, rider).spider_predicted

    real = opt.flex_report

    def soft(*a, **k):
        rep = real(*a, **k)
        object.__setattr__(rep, "lift_knockdown", -0.5)
        return rep

    monkeypatch.setattr(opt, "flex_report", soft)
    softer = evaluate(fin, rider).spider_predicted
    assert softer["hold"] < base["hold"]
    assert softer["drive"] < base["drive"]


def test_hold_is_requirement_relative_not_fleet_ranked(monkeypatch):
    # The light-rider fix: hold measures side-force headroom over F_req
    # (spider.hold_score), not Newtons ranked against the adult reference fleet.
    # Two pins: (1) a 45 kg rider's adequately-sized fin clears the old
    # fleet-rank hold ceiling (~35, which made its hold target structurally
    # unreachable); (2) inflating F_req alone LOWERS hold — impossible for a
    # fleet-ranked axis, which never sees F_req.
    import fingen.optimize as opt

    rider = RiderSpec(weight_kg=45.0, skill=Skill.ADVANCED, config=FinConfig.THRUSTER)
    fin = FinParams(outline=OutlineParams(depth=130.0, base=118.0, sweep=22.0,
                                          tip_width_ratio=0.30, le_fullness=0.07,
                                          te_shape=-0.34),
                    foil=FoilParams(family=FoilFamily.FLAT_INSIDE,
                                    thickness_ratio=0.14))
    res = evaluate(fin, rider)
    assert res.margins["capacity_n"] > res.margins["capacity_req_n"]  # has headroom
    assert res.spider_predicted["hold"] > 52.0  # clears the old ~35 fleet ceiling

    real = opt.required_side_force_n

    def inflated(sheet):
        return real(sheet) * 4.0

    monkeypatch.setattr(opt, "required_side_force_n", inflated)
    harder = evaluate(fin, rider)
    assert harder.spider_predicted["hold"] < res.spider_predicted["hold"] - 10.0


def test_stage_b_decode_applies_offsets():
    # Review finding: a no-op stage B passed every test. Pin the decode:
    # nonzero offset entries must reach the FinParams, bounded vs the
    # DECODED base (the 0.3*base coupling).
    import numpy as np

    import fingen.optimize as opt

    x = np.full(opt._N_SLIDERS + 12, 0.5)
    x[opt._N_SLIDERS] = 0.9         # first le_dx entry, well off center
    fin = opt._decode(x, FinConfig.THRUSTER, use_offsets=True,
                      use_grooves=False)
    assert abs(fin.outline.le_dx[0]) > 1.0
    assert abs(fin.outline.le_dx[0]) <= 0.3 * fin.outline.base + 1e-6


def test_objective_guard_covers_evaluate(monkeypatch):
    # The first guard patch silently no-opped (str.replace mismatch) and its
    # test passed by trajectory luck. This one cannot be dodged: evaluate()
    # itself raises, and the search must still complete.
    import fingen.optimize as opt

    real_evaluate = opt.evaluate
    calls = {"n": 0}

    def sometimes_raises(fin, rider, **kwargs):
        calls["n"] += 1
        if calls["n"] % 3 == 0:
            raise ValueError("synthetic deep-rejection")
        return real_evaluate(fin, rider, **kwargs)

    monkeypatch.setattr(opt, "evaluate", sometimes_raises)
    rider = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE,
                      config=FinConfig.THRUSTER)
    result = optimize(rider, budget_evals=60, seed=3)
    assert result.result.objective < DECODE_PENALTY


def test_evaluate_scores_track_rider_weight_not_wref():
    # Review finding: evaluate()'s raw_scores call must pass rider.weight_kg —
    # substituting the W_REF default (spider.raw_scores(fin, speed)) passed the
    # entire suite. The drive/forgiveness working point is a fixed side FORCE that
    # scales with rider mass (spider.work_force_n), so on the IDENTICAL fin at a
    # FIXED speed a lighter rider loads a smaller work force -> smaller cl_work,
    # which gives (a) a smaller working angle and thus a LARGER stall margin
    # (higher forgiveness), and (b) operation further below the induced-drag rise
    # and thus a HIGHER L/D-at-load (higher drive). Both predicted axes must be
    # strictly greater for the 45 kg rider than the 95 kg rider.
    import fingen.optimize as opt
    from fingen import spider

    fin = FinParams(outline=OutlineParams(depth=128.0, base=101.0, sweep=33.0,
                                          tip_width_ratio=0.35),
                    foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    light = RiderSpec(weight_kg=45.0, skill=Skill.INTERMEDIATE,
                      config=FinConfig.THRUSTER, speed_ms=6.4)
    heavy = RiderSpec(weight_kg=95.0, skill=Skill.INTERMEDIATE,
                      config=FinConfig.THRUSTER, speed_ms=6.4)
    res_l = evaluate(fin, light).spider_predicted
    res_h = evaluate(fin, heavy).spider_predicted
    assert res_l["forgiveness"] > res_h["forgiveness"]
    assert res_l["drive"] > res_h["drive"]

    # Magnitude pin. Substituting the W_REF default would REVERSE both directions
    # above (the 77.5 kg work force stalls this fin, flooring the light rider),
    # but pin it independently anyway: forgiveness carries no washout, so
    # evaluate's predicted forgiveness for the 45 kg rider must equal the
    # fleet-normalized rank of spider.raw_scores(fin, 6.4, 45.0)['forgiveness']
    # against the 45 kg fleet — computed here directly WITH the weight. Under the
    # W_REF default this reads ~0 (the floored margin) instead of ~59.
    raw45 = spider.raw_scores(fin, 6.4, 45.0)
    expected_forgiveness = opt._normalize(
        raw45, opt._fleet_raw(6.4, 45.0))["forgiveness"]
    assert expected_forgiveness > 55.0          # the real value, not the ~0 floor
    assert res_l["forgiveness"] == pytest.approx(expected_forgiveness)


def test_stability_axis_in_objective():
    # (A) The stability (roll) axis is SCORED, not report-only: moving only its
    # target changes the weighted quadratic distance. Mutation guard "stability
    # axis dropped from distance" (or from AXES): the objective would then be
    # indifferent to the stability target.
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    low = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE, config=FinConfig.THRUSTER,
                    spider_targets={"stability": 0.10})
    high = RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE, config=FinConfig.THRUSTER,
                     spider_targets={"stability": 0.90})
    r_low = evaluate(fin, low)
    r_high = evaluate(fin, high)
    assert "stability" in r_low.spider_predicted
    assert 0.0 <= r_low.spider_predicted["stability"] <= 100.0
    # Same fin, same everything but the stability target -> different distance.
    assert r_low.distance != pytest.approx(r_high.distance)
    assert r_low.objective != pytest.approx(r_high.objective)


def test_stability_target_varies_with_skill_and_weight():
    # Mutation guard "stability target map returning constant" AND the Finding-2
    # middle-tier permutation: the INTERMEDIATE↔ADVANCED base swap (0.55↔0.45)
    # survived the old test because its only skill check was CRUISER vs PRO and
    # its heavy/light pair shared — and thus cancelled — the INTERMEDIATE base.
    # Pin STRICT MONOTONICITY across ALL FOUR skill bases at W_REF (77.5 kg, where
    # the weight term is exactly 0) to hand-computed literals carried through the
    # damping/clip pipeline  0.5 + 0.72·(base − 0.5), clipped to [0.12, 0.85]:
    #   CRUISER 0.70 → 0.644   INTERMEDIATE 0.55 → 0.536
    #   ADVANCED 0.45 → 0.464  PRO 0.35 → 0.392
    st = {sk: default_spider_targets(77.5, sk)["stability"]
          for sk in (Skill.CRUISER, Skill.INTERMEDIATE, Skill.ADVANCED, Skill.PRO)}
    assert st[Skill.CRUISER] == pytest.approx(0.644, rel=1e-9)
    assert st[Skill.INTERMEDIATE] == pytest.approx(0.536, rel=1e-9)
    assert st[Skill.ADVANCED] == pytest.approx(0.464, rel=1e-9)
    assert st[Skill.PRO] == pytest.approx(0.392, rel=1e-9)
    # Strict monotone CRUISER > INTERMEDIATE > ADVANCED > PRO — an INTERMEDIATE↔
    # ADVANCED base swap breaks both the middle literals and this ordering.
    assert (st[Skill.CRUISER] > st[Skill.INTERMEDIATE] > st[Skill.ADVANCED]
            > st[Skill.PRO])
    # The named anchor the finding calls out, pinned on its own line, through the
    # full damping/clip pipeline.
    assert default_spider_targets(77.5, Skill.ADVANCED)["stability"] == pytest.approx(
        0.464, rel=1e-9)
    # Weight: at fixed skill a heavier rider wants more damping (control-torque
    # scaling) — the original directional check, retained.
    light = default_spider_targets(45.0, Skill.INTERMEDIATE)["stability"]
    heavy = default_spider_targets(110.0, Skill.INTERMEDIATE)["stability"]
    assert heavy > light + 0.10


def test_p_design_map_varies_by_skill():
    # (B) Mutation guard "p_design map collapsed to one value": the four skill
    # tiers carry four distinct roll rates, pinned to independent literals.
    from fingen.optimize import _P_DESIGN_RAD_S
    vals = [_P_DESIGN_RAD_S[s] for s in
            (Skill.CRUISER, Skill.INTERMEDIATE, Skill.ADVANCED, Skill.PRO)]
    assert vals == [2.5, 4.0, 6.0, 8.0]
    assert len(set(vals)) == 4


def test_roll_augmented_stress_gate_uses_worse_case():
    # (B) evaluate() reports BOTH stress margins and gates on the WORSE. A deep
    # blade under a hard PRO roll rate overstresses more in the combined case, so
    # the roll SF is the smaller one and it drives the penalty.
    deep = FinParams(outline=OutlineParams(depth=140, base=95, sweep=33,
                                           tip_width_ratio=0.35),
                     foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    rider = RiderSpec(weight_kg=95.0, skill=Skill.PRO, config=FinConfig.THRUSTER)
    r = evaluate(deep, rider)
    assert "stress_sf" in r.margins and "stress_sf_roll" in r.margins
    assert r.margins["stress_sf_roll"] < r.margins["stress_sf"]  # roll adds tip load
    worst = min(r.margins["stress_sf"], r.margins["stress_sf_roll"])
    assert worst < 1.0  # this blade is overstressed
    # Mutation guard "gate uses steady only": the penalty must come from the
    # WORSE (roll) margin, not the steady one.
    assert r.penalties["stress"] == pytest.approx(1.0 - worst)
    assert r.penalties["stress"] != pytest.approx(1.0 - r.margins["stress_sf"])


def test_tab_sf_gate_active_inactive_and_grades():
    # (C) Glass-on blade (TabSystem.NONE, what the optimizer decodes today):
    # gate inactive, tab_sf = inf, no penalty.
    import math as _m
    rider = RiderSpec(weight_kg=80.0, skill=Skill.ADVANCED, config=FinConfig.THRUSTER)
    glass = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    r = evaluate(glass, rider)
    assert r.margins["tab_sf"] == _m.inf
    assert "tab_sf" not in r.penalties
    # The SAME blade with tabs activates the gate (finite, positive SF).
    tabbed = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                       tabs=TabParams(system=TabSystem.DUAL_TAB))
    rt = evaluate(tabbed, rider)
    assert _m.isfinite(rt.margins["tab_sf"]) and rt.margins["tab_sf"] > 0.0
    assert "tab_sf" not in rt.penalties  # a normal side fin's tabs are fine
    # A small-base thin dual-tab under a heavy pro trips the gate -> graded penalty.
    trip = FinParams(outline=OutlineParams(depth=135, base=70, sweep=33,
                                           tip_width_ratio=0.35),
                     foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.05),
                     tabs=TabParams(system=TabSystem.DUAL_TAB))
    rp = evaluate(trip, RiderSpec(weight_kg=105.0, skill=Skill.PRO,
                                  config=FinConfig.THRUSTER))
    assert rp.margins["tab_sf"] < 1.0
    assert rp.penalties["tab_sf"] == pytest.approx(1.0 - rp.margins["tab_sf"])


def test_normalize_stable_at_tied_fleet_values():
    # Landscape finding: tied fleet breakpoints made ranks flip 0<->40 under
    # sub-ULP jitter. Ranks at a tie must sit at the tie-group mean, stably.

    import fingen.optimize as opt
    from fingen import spider

    tied = 0.6
    fleet = tuple(
        tuple({ax: (tied if i < 4 else 5.0 + i) for ax in spider.AXES}.items())
        for i in range(6))
    a = opt._normalize({ax: tied for ax in spider.AXES}, fleet)
    b = opt._normalize({ax: tied + 1e-12 for ax in spider.AXES}, fleet)
    c = opt._normalize({ax: tied - 1e-12 for ax in spider.AXES}, fleet)
    for ax in spider.AXES:
        assert abs(a[ax] - 30.0) < 1.0     # mean rank of the 4-way tie
        assert abs(a[ax] - b[ax]) < 0.5
        assert abs(a[ax] - c[ax]) < 0.5
