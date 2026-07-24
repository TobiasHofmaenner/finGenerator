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


def test_config_requires_matching_fins():
    side = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    FinSetParams(config=FinConfig.TWIN, center=None, side=side)
    with pytest.raises(ValueError):
        FinSetParams(config=FinConfig.THRUSTER, center=None, side=side)
    with pytest.raises(ValueError):
        FinSetParams(config=FinConfig.SINGLE, center=None, side=None)
