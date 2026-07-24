"""Property-based manifold sweep: ANY in-range parameter vector must either be
rejected cleanly (ValueError) or produce a watertight solid that passes the
geometry checker. This is the guarantee the parametric design rests on."""

from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from fingen.check import check_solid
from fingen.loft import fin_solid
from fingen.params import FinParams, FoilFamily, FoilParams, GenSettings, OutlineParams

outline_strategy = st.builds(
    OutlineParams,
    depth=st.floats(40.0, 300.0),
    base=st.floats(40.0, 250.0),
    sweep=st.floats(0.0, 60.0),
    tip_chord_ratio=st.floats(0.05, 0.9),
    le_fullness=st.floats(0.0, 1.0),
    te_fullness=st.floats(0.0, 1.0),
)

foil_strategy = st.builds(
    FoilParams,
    family=st.sampled_from(FoilFamily),
    thickness_ratio=st.floats(0.04, 0.15),
    camber_ratio=st.floats(0.0, 0.12),
    camber_position=st.floats(0.2, 0.6),
    te_thickness=st.floats(0.4, 1.2),
)

fin_strategy = st.builds(
    FinParams,
    outline=outline_strategy,
    foil=foil_strategy,
    thickness_tip_factor=st.floats(0.5, 1.2),
)


@given(fin_strategy)
@settings(max_examples=25, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_any_valid_params_yield_a_manifold(fin):
    coarse = GenSettings(n_stations=11, n_foil_points=60)  # keep OCCT time sane
    try:
        part = fin_solid(fin, coarse)
    except ValueError:
        event("rejected cleanly")  # acceptable; rate visible via
        return  # --hypothesis-show-statistics
    event("produced a solid")
    report = check_solid(part, fin, coarse)
    assert report.ok, f"params: {fin}\nissues: {report.issues}"
