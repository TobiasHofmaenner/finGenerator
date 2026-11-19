"""The cambered side foil as a searched family (RiderSpec.side_foil = "cambered")."""

import numpy as np
import pytest

from fingen.optimize import (
    _N_GROOVES,
    _N_OFFSETS,
    _N_SLIDERS,
    RiderSpec,
    _decode,
    _x0_sliders,
    optimize,
    searches_camber,
)
from fingen.params import FinConfig, FoilFamily, TabSystem
from fingen.sizing import Skill


def _rider(**kw) -> RiderSpec:
    return RiderSpec(weight_kg=60.0, skill=Skill.PRO, speed_ms=8.5, config=FinConfig.THRUSTER,
                     material="ppa-cf", tabs=TabSystem("click_tab"), **kw)


def test_flat_inside_stays_the_default_and_unknown_foils_are_refused():
    assert _rider().side_foil == "flat_inside"
    assert not searches_camber(_rider())
    with pytest.raises(ValueError):
        _rider(side_foil="80/20")


def test_only_the_side_blade_of_a_set_carries_the_camber_gene():
    r = _rider(side_foil="cambered")
    assert searches_camber(r)
    assert not searches_camber(r, FoilFamily.SYMMETRIC)             # the centre of the set
    single = RiderSpec(weight_kg=75.0, config=FinConfig.SINGLE, side_foil="cambered")
    assert not searches_camber(single)


@pytest.mark.parametrize("use_offsets, use_grooves", [(False, False), (True, False), (True, True)])
def test_camber_gene_rides_after_every_other_gene(use_offsets, use_grooves):
    n = _N_SLIDERS + (_N_OFFSETS if use_offsets else 0) + (_N_GROOVES if use_grooves else 0)
    x = np.array(_x0_sliders(FinConfig.THRUSTER) + [0.5] * (n - _N_SLIDERS) + [0.8])
    plain = _decode(x[:n], FinConfig.THRUSTER, use_offsets=use_offsets, use_grooves=use_grooves)
    camb = _decode(x, FinConfig.THRUSTER, use_offsets=use_offsets, use_grooves=use_grooves,
                   camber=True)
    assert plain.foil.family is FoilFamily.FLAT_INSIDE and plain.foil.camber_ratio == 0.0
    assert camb.foil.family is FoilFamily.CAMBERED
    assert camb.foil.camber_ratio == pytest.approx(0.8 * 0.05)
    assert camb.foil.camber_position == pytest.approx(0.4)
    assert camb.outline == plain.outline and camb.grooves == plain.grooves
    assert camb.foil.thickness_ratio == plain.foil.thickness_ratio


def test_search_returns_a_cambered_side_and_a_symmetric_centre():
    res = optimize(_rider(side_foil="cambered"), budget_evals=360, seed=0, workers=1)
    assert res.fin.foil.family is FoilFamily.CAMBERED
    assert 0.0 <= res.fin.foil.camber_ratio <= 0.05
    assert res.center is not None and res.center.foil.family is FoilFamily.SYMMETRIC
    flat = optimize(_rider(), budget_evals=360, seed=0, workers=1)
    assert flat.fin.foil.family is FoilFamily.FLAT_INSIDE           # the default path is untouched
