import pytest

from fingen import FinParams, FinSetParams, FoilParams


def test_defaults_are_valid():
    fin = FinParams()
    assert fin.depth > 0
    FinSetParams(center=fin, side=FinParams(foil=FoilParams(camber_ratio=0.03, flat_inside=True)))


def test_rejects_absurd_dimensions():
    with pytest.raises(ValueError):
        FinParams(depth=5.0)
    with pytest.raises(ValueError):
        FinParams(sweep=80.0)
    with pytest.raises(ValueError):
        FoilParams(thickness_ratio=0.5)


def test_fin_set_needs_a_fin():
    with pytest.raises(ValueError):
        FinSetParams(center=None, side=None)
