import pytest

from fingen import (
    FinConfig,
    FinParams,
    FinSetParams,
    FoilFamily,
    FoilParams,
    GenSettings,
    OutlineParams,
)


def test_defaults_are_valid():
    fin = FinParams()
    assert fin.outline.depth > 0
    FinSetParams()


def test_rejects_out_of_range_values():
    with pytest.raises(ValueError):
        OutlineParams(depth=5.0)
    with pytest.raises(ValueError):
        OutlineParams(sweep=80.0)
    with pytest.raises(ValueError):
        OutlineParams(le_fullness=1.5)
    with pytest.raises(ValueError):
        FoilParams(thickness_ratio=0.5)
    with pytest.raises(ValueError):
        FoilParams(te_thickness=0.1)
    with pytest.raises(ValueError):
        FinParams(thickness_tip_factor=0.1)
    with pytest.raises(ValueError):
        GenSettings(n_stations=3)


def test_groove_validation():
    from fingen.params import GrooveParams, GrooveSurface

    GrooveParams(count=6)  # [Els22] G1-style defaults are valid
    with pytest.raises(ValueError):
        GrooveParams(count=13)
    with pytest.raises(ValueError):
        GrooveParams(count=2, width=8.0, pitch=6.0)  # width > pitch
    with pytest.raises(ValueError):
        GrooveParams(count=2, depth_ratio=0.8)
    # Band must stay below 90 % of depth.
    with pytest.raises(ValueError):
        FinParams(grooves=GrooveParams(count=12, pitch=10.0, span_start=0.4))
    # Flat-inside foils only groove the outer face (inner face = print bed).
    with pytest.raises(ValueError):
        FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                  grooves=GrooveParams(count=2, surface=GrooveSurface.BOTH))
    FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC),
              grooves=GrooveParams(count=2, surface=GrooveSurface.BOTH))


def test_config_requires_matching_fins():
    side = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    FinSetParams(config=FinConfig.TWIN, center=None, side=side)
    with pytest.raises(ValueError):
        FinSetParams(config=FinConfig.THRUSTER, center=None, side=side)
    with pytest.raises(ValueError):
        FinSetParams(config=FinConfig.SINGLE, center=None, side=None)


def test_cli_defaults_match_dataclass_defaults():
    # The CLI derives its defaults from the dataclasses; this pins it (the
    # duplicated-literal version drifted: CLI sweep 33 vs params 42).
    from fingen.cli import _build_parser

    args = _build_parser().parse_args(["make", "out.step"])
    out = OutlineParams()
    assert (args.depth, args.base, args.sweep) == (out.depth, out.base, out.sweep)
    assert args.tip_width == out.tip_width_ratio
    assert args.te_shape == out.te_shape
    assert args.le_fullness == out.le_fullness
