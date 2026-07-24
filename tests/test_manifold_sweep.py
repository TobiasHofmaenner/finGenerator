"""Property-based manifold sweep: ANY in-range parameter vector must either be
rejected cleanly (ValueError) or produce a watertight solid that passes the
geometry checker. A companion floor test asserts the generator actually
accepts a healthy share of the space — mass rejection cannot hide behind the
escape hatch — and a deterministic corner sweep pins known-buildable regions."""

import itertools

from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from fingen.check import check_solid
from fingen.loft import fin_solid
from fingen.params import FinParams, FoilFamily, FoilParams, GenSettings, OutlineParams

COARSE = GenSettings(n_stations=11, n_foil_points=60)  # keep OCCT time sane

outline_strategy = st.builds(
    OutlineParams,
    depth=st.floats(40.0, 300.0),
    base=st.floats(40.0, 250.0),
    sweep=st.floats(0.0, 60.0),
    tip_width_ratio=st.floats(0.05, 0.6),
    le_fullness=st.floats(0.0, 1.0),
    te_shape=st.floats(-1.0, 1.0),
)

foil_strategy = st.builds(
    FoilParams,
    family=st.sampled_from(FoilFamily),
    thickness_ratio=st.floats(0.04, 0.15),
    camber_ratio=st.floats(0.0, 0.05),
    camber_position=st.floats(0.2, 0.6),
    te_thickness=st.floats(0.4, 1.2),
)

fin_strategy = st.builds(
    FinParams,
    outline=outline_strategy,
    foil=foil_strategy,
    thickness_tip_factor=st.floats(0.5, 1.2),
)

_outcomes = {"produced": 0, "rejected": 0}


@given(fin_strategy)
@settings(max_examples=25, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_any_valid_params_yield_a_manifold(fin):
    try:
        part = fin_solid(fin, COARSE)
    except ValueError:
        _outcomes["rejected"] += 1
        event("rejected cleanly")
        return
    _outcomes["produced"] += 1
    event("produced a solid")
    report = check_solid(part, fin, COARSE)
    assert report.ok, f"params: {fin}\nissues: {report.issues}"


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
    for fin in corners:
        report = check_solid(fin_solid(fin, COARSE), fin, COARSE)
        assert report.ok, f"corner failed: {fin}\nissues: {report.issues}"
