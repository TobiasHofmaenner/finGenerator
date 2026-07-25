"""Property-based manifold sweep of the PRODUCTION CONTRACT: for any in-range
parameter vector the pipeline must (a) produce a solid that passes the
checker, (b) reject it with a clean ValueError, or (c) produce a solid the
checker refuses — which the CLI/API translate into refusal to export. What
must never happen: an unexplained crash, or a corrupt solid escaping
unchecked. A floor test asserts most of the space actually builds (mass
rejection/refusal cannot hide), and a deterministic corner sweep pins the
healthy template space where refusal is NOT acceptable."""

import itertools

import pytest
from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from fingen.check import check_solid
from fingen.loft import fin_solid
from fingen.params import (
    FinParams,
    FoilFamily,
    FoilParams,
    GenSettings,
    GrooveParams,
    GrooveSurface,
    OutlineParams,
    TabParams,
    TabSystem,
)

# OCCT-heavy: local only, excluded from GitHub CI. The xdist group keeps the
# whole file on one worker so the floor test sees the sweep's counters.
pytestmark = [pytest.mark.heavy, pytest.mark.xdist_group("manifold-sweep")]

COARSE = GenSettings(n_stations=15, n_foil_points=60)  # default stations — test
# what users actually get; reduced section points keep OCCT time sane

_dx = st.tuples(*[st.floats(-10.0, 10.0)] * 6)  # level-2 offsets, ±10 mm safe for base >= 40

outline_strategy = st.builds(
    OutlineParams,
    depth=st.floats(40.0, 300.0),
    base=st.floats(40.0, 250.0),
    sweep=st.floats(0.0, 60.0),
    tip_width_ratio=st.floats(0.05, 0.6),
    le_fullness=st.floats(0.0, 1.0),
    te_shape=st.floats(-1.0, 1.0),
    le_dx=_dx,
    te_dx=_dx,
)

foil_strategy = st.builds(
    FoilParams,
    family=st.sampled_from(FoilFamily),
    thickness_ratio=st.floats(0.04, 0.15),
    camber_ratio=st.floats(0.0, 0.05),
    camber_position=st.floats(0.2, 0.6),
    te_thickness=st.floats(0.4, 1.2),
)

tab_strategy = st.builds(
    TabParams,
    system=st.sampled_from(TabSystem),
    fit_offset=st.floats(-0.6, 0.4),
    tab_depth=st.one_of(st.none(), st.floats(8.0, 20.0)),
    click_indent_depth=st.floats(0.0, 1.5),
    x_offset=st.floats(-40.0, 40.0),
    y_offset=st.floats(-3.0, 3.0),
)

@st.composite
def groove_strategy(draw):
    # width <= pitch is an intra-GrooveParams constraint; draw pitch first.
    pitch = draw(st.floats(2.0, 40.0))
    return GrooveParams(
        count=draw(st.integers(0, 12)),
        length=draw(st.floats(5.0, 200.0)),
        pitch=pitch,
        width=draw(st.floats(1.0, pitch)),
        depth_ratio=draw(st.floats(0.05, 0.6)),
        span_start=draw(st.floats(0.05, 0.85)),
        surface=draw(st.sampled_from(GrooveSurface)),
    )


# Components, not a built FinParams: FinParams.__post_init__ enforces
# cross-field constraints (groove band vs depth, groove surface vs foil
# family) with ValueError — under the production contract those are CLEAN
# REJECTIONS, so construction must happen inside the test's try block, not
# during strategy generation.
fin_components = st.fixed_dictionaries({
    "outline": outline_strategy,
    "foil": foil_strategy,
    "thickness_tip_factor": st.floats(0.5, 1.2),
    "tabs": tab_strategy,
    "grooves": groove_strategy(),
})

_outcomes = {"produced": 0, "rejected": 0, "invalid": 0}


@given(fin_components)
@settings(max_examples=25, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_any_valid_params_yield_a_manifold(components):
    try:
        fin = FinParams(**components)
    except ValueError:
        # Cross-field parameter validation (groove band vs depth, groove
        # surface vs family) — the front door, not the escape hatch. Counted
        # apart so the acceptance floor keeps measuring what it always did:
        # of the vectors that pass validation, most must build.
        _outcomes["invalid"] += 1
        event("invalid parameter vector")
        return
    try:
        part = fin_solid(fin, COARSE)
    except ValueError:
        _outcomes["rejected"] += 1
        event("rejected cleanly")
        return
    report = check_solid(part, fin, COARSE)
    if report.ok:
        _outcomes["produced"] += 1
        event("produced a checked solid")
    else:
        # The checker refusing an adversarial corner IS the system working:
        # the CLI/API gate exports on report.ok. Corner cases where refusal
        # would be wrong are pinned by test_known_buildable_corners.
        _outcomes["rejected"] += 1
        event("checker refused")


def test_acceptance_floor():
    """Runs after the sweep (file order): the escape hatch must not swallow
    the space. The floor is a mass-rejection alarm, deliberately below the
    true acceptance rate: hypothesis replays stored past counterexamples
    first, and those are exactly the degenerate shapes that now reject
    cleanly, biasing the sample. Healthy-space buildability is pinned
    deterministically by test_known_buildable_corners below."""
    total = _outcomes["produced"] + _outcomes["rejected"]
    assert total > 0, "sweep did not run"
    assert _outcomes["produced"] >= 0.45 * total, _outcomes


def test_known_buildable_corners():
    """Deterministic pins: single-parameter extremes off the default fin must
    build and pass checks (clean rejection is NOT acceptable here)."""
    corners = [FinParams()]
    for field, lo, hi in [("depth", 60.0, 250.0), ("base", 60.0, 200.0),
                          ("sweep", 0.0, 50.0), ("tip_width_ratio", 0.08, 0.5),
                          ("le_fullness", 0.0, 1.0), ("te_shape", -1.0, 1.0)]:
        for value in (lo, hi):
            corners.append(FinParams(outline=OutlineParams(**{field: value})))
    for family, thickness in itertools.product(
            (FoilFamily.SYMMETRIC, FoilFamily.FLAT_INSIDE), (0.06, 0.12)):
        corners.append(FinParams(foil=FoilParams(family=family,
                                                 thickness_ratio=thickness)))
    for system in (TabSystem.DUAL_TAB, TabSystem.SINGLE_TAB, TabSystem.CLICK_TAB):
        corners.append(FinParams(tabs=TabParams(system=system)))
    for fin in corners:
        report = check_solid(fin_solid(fin, COARSE), fin, COARSE)
        assert report.ok, f"corner failed: {fin}\nissues: {report.issues}"
