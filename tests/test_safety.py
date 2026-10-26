"""Third-party injury constraints (fingen.safety).

Regression pins on the two metrics, their calibration against the commercial
template fleet, and the property that makes them an interlock rather than
advice: the optimizer's soft gate and the exporter's hard gate read the same
functions and agree on every outline.
"""
import numpy as np
import pytest

from fingen.optimize import RiderSpec, evaluate
from fingen.params import FinConfig, FinParams, FoilFamily, FoilParams, OutlineParams, TabSystem
from fingen.safety import (
    HOOK_MAX_MM,
    TIP_RADIUS_MIN_MM,
    hook_depth,
    safety_issues,
    safety_penalties,
    tip_radius,
)
from fingen.sizing import Skill, anchor, check_anchor
from fingen.spider import reference_fleet

# The first hook the optimizer produced: Omar's small-wave side blade
# (60 kg PRO thruster, ppa-cf). The tip point sits at depth*tan(sweep) = 74.9 mm
# while the le_dx offsets park the 80 % and 92 % span control points at 97.7 and
# 107.2 mm, so the leading edge has to swing forward to reach the tip.
HOOKED = OutlineParams(
    depth=121.8539, base=133.2646, sweep=31.5873, tip_width_ratio=0.3278,
    le_fullness=0.0259, te_shape=-0.1746,
    le_dx=(34.3718, 10.5531, -22.1236, 8.2737, 38.513, 38.6452),
    te_dx=(-14.0203, -2.7524, -15.6127, 20.9058, 37.276, 25.3026))


def test_every_commercial_template_is_allowed():
    """The line is 'no worse than the commercial baseline'. If a threshold ever
    moves so that a template is forbidden, the constraint has stopped meaning
    that — which is why this is pinned per template with the measured values."""
    for name, fin in reference_fleet().items():
        assert hook_depth(fin.outline) <= HOOK_MAX_MM, name
        assert tip_radius(fin.outline) >= TIP_RADIUS_MIN_MM, name
        assert safety_issues(fin.outline) == [], name


def test_threshold_margins_against_the_fleet():
    """The pointiest template (hi-aspect, 9.03 mm) keeps a ~1 mm margin, and the
    largest template 'hook' (fish-keel, 0.69 mm, a tip-rounding effect) stays
    below the 1 mm line. Guards against tightening past the baseline."""
    fleet = reference_fleet()
    assert tip_radius(fleet["hi-aspect"].outline) == pytest.approx(9.03, abs=0.05)
    assert max(hook_depth(f.outline) for f in fleet.values()) == pytest.approx(0.69, abs=0.05)


def test_the_hook_that_started_this_is_caught():
    assert hook_depth(HOOKED) == pytest.approx(10.9, abs=0.2)
    assert "forward_hook" in safety_penalties(HOOKED)
    assert any("hooks forward" in i for i in safety_issues(HOOKED))


def test_monotone_rake_has_no_hook():
    assert hook_depth(OutlineParams()) == 0.0


def test_forward_base_bulge_is_not_a_hook():
    """le_fullness bows the LE forward low on the span. That pocket closes
    against the board — it is how commercial templates carry area low, not a
    catch — so measurement starts only once the edge first moves aft."""
    assert hook_depth(OutlineParams(le_fullness=1.0)) <= HOOK_MAX_MM


def test_sharp_tip_is_caught():
    pointy = OutlineParams(tip_width_ratio=0.05)
    assert tip_radius(pointy) < TIP_RADIUS_MIN_MM
    assert "tip_radius" in safety_penalties(pointy)
    assert any("tip radius" in i for i in safety_issues(pointy))


def test_optimizer_treats_a_hook_as_infeasible():
    rider = RiderSpec(weight_kg=60.0, skill=Skill.PRO, config=FinConfig.THRUSTER,
                      material="ppa-cf", tabs=TabSystem.CLICK_TAB)
    fin = FinParams(outline=HOOKED, foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    r = evaluate(fin, rider)
    assert not r.feasible
    assert r.penalties.get("forward_hook", 0.0) > 0.0


def test_exporter_gate_refuses_a_hook():
    """check_anchor is what the export script refuses on."""
    sheet = anchor(60.0, Skill.PRO, design_speed=8.5, config=FinConfig.THRUSTER,
                   material="ppa-cf", tabs=TabSystem.CLICK_TAB)
    fin = FinParams(outline=HOOKED, foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    assert any("hooks forward" in i for i in check_anchor(fin, sheet))


def test_soft_and_hard_gates_agree_on_every_outline():
    """ONE quantity, two walls. evaluate()'s penalties and check_anchor()'s
    issues must forbid exactly the same outlines, or the optimizer ships fins
    the exporter then refuses (which has happened before with the stress gate)."""
    rng = np.random.default_rng(7)
    checked = 0
    for _ in range(400):
        base = rng.uniform(80, 180)
        try:
            o = OutlineParams(depth=rng.uniform(80, 200), base=base, sweep=rng.uniform(0, 55),
                              tip_width_ratio=rng.uniform(0.05, 0.6),
                              le_fullness=rng.uniform(0, 1), te_shape=rng.uniform(-1, 1),
                              le_dx=tuple(rng.uniform(-0.25 * base, 0.25 * base, 6)),
                              te_dx=tuple(rng.uniform(-0.25 * base, 0.25 * base, 6)))
            pen, iss = safety_penalties(o), safety_issues(o)
        except ValueError:
            continue
        assert bool(pen) == bool(iss)
        assert ("forward_hook" in pen) == any("hooks forward" in i for i in iss)
        assert ("tip_radius" in pen) == any("tip radius" in i for i in iss)
        checked += 1
    assert checked > 200
