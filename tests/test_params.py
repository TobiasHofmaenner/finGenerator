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
    # ...and clear of the root: the base section must stay full thickness.
    with pytest.raises(ValueError):
        FinParams(outline=OutlineParams(depth=40.0),
                  grooves=GrooveParams(count=1, pitch=40.0, width=40.0,
                                       span_start=0.05))
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
    from fingen.params import GrooveParams

    g = GrooveParams()
    assert args.grooves == g.count
    assert (args.groove_length, args.groove_pitch, args.groove_width) == (
        g.length, g.pitch, g.width)
    assert (args.groove_depth, args.groove_start) == (g.depth_ratio, g.span_start)
    assert args.groove_surface == g.surface.value


def test_cli_groove_args_reach_the_dataclass():
    # depth_ratio and span_start have overlapping float ranges — a swapped
    # keyword in _fin_from_args would validate fine and ship a wrong fin.
    from fingen.cli import _build_parser, _fin_from_args
    from fingen.params import GrooveSurface

    args = _build_parser().parse_args(
        ["make", "x.step", "--family", "symmetric", "--grooves", "3",
         "--groove-length", "40", "--groove-pitch", "8", "--groove-width", "4",
         "--groove-depth", "0.2", "--groove-start", "0.6",
         "--groove-surface", "both"])
    g = _fin_from_args(args).grooves
    assert (g.count, g.length, g.pitch, g.width) == (3, 40.0, 8.0, 4.0)
    assert (g.depth_ratio, g.span_start) == (0.2, 0.6)
    assert g.surface is GrooveSurface.BOTH
