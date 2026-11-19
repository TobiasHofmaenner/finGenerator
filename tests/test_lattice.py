"""fingen.lattice against textbook wings and against our own CFD (docs/MODEL-EXTENSION.md)."""

import dataclasses
import json
import math
import time
from pathlib import Path

import numpy as np
import pytest

from fingen.hydro import zero_lift_alpha_deg
from fingen.lattice import (
    blade_from_fin,
    blade_from_planform,
    isolated,
    set_blades,
    solve,
    trefftz_cdi,
)
from fingen.optimize import fin_from_dict
from fingen.params import FinConfig, FinParams, FinSetParams, FoilFamily, FoilParams

BENCH = Path(__file__).parents[1] / "bench/mount/fins"


def _field_fin(name: str) -> FinParams:
    return fin_from_dict(json.loads((BENCH / name).read_text())["fin"])


def _rect(ar: float, **kw):
    z = np.linspace(0.0, 100.0, 400)               # semi-span 100 mm, mirrored: full span 200
    return blade_from_planform("w", z, np.zeros_like(z), np.full_like(z, 200.0 / ar), **kw)


@pytest.mark.parametrize("ar, reference", [(2.0, 2.47), (4.0, 3.60), (6.0, 4.20)])
def test_rectangular_wings_match_lifting_surface_theory(ar, reference):
    # Published lifting-surface lift slopes of rectangular wings (per radian).
    # Lifting-LINE theory would give 3.14 / 4.19 / 4.71 — the lattice must sit on
    # the surface-theory values, which is what a low-aspect-ratio fin needs.
    cl = solve([_rect(ar, nz=24, nx=6)], 7.0, 4.0)["w"].cl
    assert cl / math.radians(4.0) == pytest.approx(reference, rel=0.03)


def test_elliptic_planform_has_unit_span_efficiency():
    z = np.linspace(0.0, 100.0, 400)
    chord = 60.0 * np.sqrt(np.clip(1.0 - (z / 100.0) ** 2, 0.0, None))
    b = blade_from_planform("w", z, -0.25 * chord, chord, nz=24, nx=6)   # straight c/4 line
    r = solve([b], 7.0, 4.0)["w"]
    ar = 2.0 * 100.0**2 / float(np.trapezoid(chord, z))
    e = r.cl**2 / (math.pi * ar * trefftz_cdi(r.gamma_strip, r.dz, r.z, b.area, 7.0))
    assert 0.97 < e < 1.04


def test_mirror_is_the_other_half_of_the_wing():
    # A blade of span s on the mirror is half of a wing of span 2s: its slope must
    # equal the AR-4 wing's, and without the mirror it falls to the AR-2 value.
    b = _rect(4.0, nz=24, nx=6)
    on = solve([b], 7.0, 4.0)["w"].cl / math.radians(4.0)
    off = solve([b], 7.0, 4.0, mirror=False)["w"].cl / math.radians(4.0)
    assert on == pytest.approx(3.60, rel=0.03)
    assert off == pytest.approx(2.47, rel=0.06)       # free wing of half the aspect ratio


def test_camber_offset_reproduces_the_section_zero_lift_angle():
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE), thickness_tip_factor=1.0)
    iso = isolated(fin)
    assert iso.cl0 > 0.1                                # a flat-inside blade pulls at zero leeway
    assert iso.alpha0_deg == pytest.approx(zero_lift_alpha_deg(fin), rel=0.03)
    sym = isolated(FinParams())
    assert abs(sym.cl0) < 1e-9 and math.isnan(sym.alpha0_deg) is False


def test_tip_thickness_moves_the_zero_lift_angle_of_a_flat_inside_blade():
    # Tier-0 reads alpha_0 from the ROOT section only (docs/MODEL-REACH.md: the tip
    # factor is invisible to it). On a flat-inside foil a thinner tip is less camber.
    base = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    thin, thick = (isolated(dataclasses.replace(base, thickness_tip_factor=f)) for f in (0.6, 1.2))
    assert thin.alpha0_deg > thick.alpha0_deg           # less negative
    assert abs(thick.cl0 / thin.cl0 - 1.0) > 0.15
    # Incidence loading untouched; the forces carry the induced velocity, so camber
    # leaves a second-order trace (~0.04 %) in the difference quotient.
    assert thin.slope == pytest.approx(thick.slope, rel=2e-3)


def test_outline_shape_moves_the_loading_peak():
    # The hydrodynamic meaning of outline shape: WHERE the blade is loaded. A wide
    # tip unloads the outer span relative to a narrow one.
    base = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    def tip(ratio):
        outline = dataclasses.replace(base.outline, tip_width_ratio=ratio)
        return isolated(dataclasses.replace(base, outline=outline))

    narrow, wide = tip(0.15), tip(0.50)
    assert narrow.peak_ratio > wide.peak_ratio * 1.05
    assert narrow.peak_z_frac >= wide.peak_z_frac


@pytest.mark.parametrize("name, cfd_slope, lo, hi", [
    ("side-shipped-gen2.json", 3.73, 0.95, 1.05),       # verify polar, 0-4 deg
    ("side-asridden-gen1.json", 3.98, 0.95, 1.07),
    ("centre-ridden-gen1.json", 2.89, 1.05, 1.20),      # inviscid over-read of the 4.6 % section
])
def test_isolated_lift_slope_against_cfd(name, cfd_slope, lo, hi):
    assert lo < isolated(_field_fin(name), 8.5, nz=16, nx=4).slope / cfd_slope < hi


def _thruster(toe=3.5, cant=8.0, side_x=-195.0, side_y=118.0) -> FinSetParams:
    return FinSetParams(config=FinConfig.THRUSTER, side=_field_fin("side-shipped-gen2.json"),
                        center=_field_fin("centre-ridden-gen1.json"), toe=toe, cant=cant,
                        side_x=side_x, side_y=side_y)


def test_set_is_mirror_symmetric():
    blades = set_blades(_thruster())
    assert [b.name for b in blades] == ["center", "right", "left"]
    zero = solve(blades, 8.5, 0.0)
    assert zero["right"].cl == pytest.approx(-zero["left"].cl, abs=1e-9)
    assert abs(zero["center"].cl) < 1e-9
    plus, minus = solve(blades, 8.5, 5.0), solve(blades, 8.5, -5.0)
    assert plus["right"].cl == pytest.approx(-minus["left"].cl, rel=1e-9)
    assert plus["center"].cl == pytest.approx(-minus["center"].cl, rel=1e-9)
    assert plus["right"].cl > plus["left"].cl > 0.0     # the blade working WITH its camber leads


def test_set_reproduces_the_cfd_interference_and_its_trend():
    # bench/mount set CFD at 5 deg: centre in the set / centre alone = 0.64 / 0.67 /
    # 0.72 at side offsets 103 / 118 / 133 mm. Tier-0 carries one fixed table value.
    centre = blade_from_fin("c", _field_fin("centre-ridden-gen1.json"), nz=10, nx=2)
    alone = solve([centre], 8.5, 5.0)["c"].cl
    factor = [solve(set_blades(_thruster(side_y=y)), 8.5, 5.0)["center"].cl / alone
              for y in (103.0, 118.0, 133.0)]
    assert factor[0] < factor[1] < factor[2]
    assert 0.58 < factor[1] < 0.72
    assert factor[2] - factor[0] == pytest.approx(0.08, abs=0.04)


def test_zero_net_force_toe_matches_the_set_cfd():
    # Set CFD: the side pair carries no net force at toe 3.65 deg (bench/mount).
    cl = {toe: solve(set_blades(_thruster(toe=toe)), 8.5, 0.0)["right"].cl for toe in (2.5, 4.5)}
    toe0 = 2.5 + 2.0 * cl[2.5] / (cl[2.5] - cl[4.5])
    assert cl[2.5] > 0.0 > cl[4.5]
    assert toe0 == pytest.approx(3.65, abs=0.25)


def test_resolution_is_converged_and_cheap():
    fin = _field_fin("side-shipped-gen2.json")
    coarse, fine = isolated(fin, 8.5, nz=10, nx=2), isolated(fin, 8.5, nz=16, nx=4)
    assert coarse.slope == pytest.approx(fine.slope, rel=0.025)
    assert coarse.peak_ratio == pytest.approx(fine.peak_ratio, rel=0.03)
    b = blade_from_fin("b", fin)                        # default 12 x 3 = 36 panels
    solve([b], 8.5, 4.0)
    t0 = time.perf_counter()
    for _ in range(5):
        solve([b], 8.5, 4.0)
    assert (time.perf_counter() - t0) / 5 < 0.25        # ~3 ms on an idle core; loose for CI


def test_bad_inputs_are_rejected():
    fin = FinParams()
    with pytest.raises(ValueError):
        blade_from_fin("b", fin, hand="up")
    with pytest.raises(ValueError):
        blade_from_fin("b", fin, nz=2)
    with pytest.raises(ValueError):
        solve([], 7.0, 4.0)
    with pytest.raises(ValueError):
        solve([blade_from_fin("b", fin)], 0.0, 4.0)
