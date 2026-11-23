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
    e = r.cl**2 / (math.pi * ar * trefftz_cdi(r.gamma_strip, r.dz, r.z_wake, b.area, 7.0))
    assert 0.99 < e < 1.003


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


# --------------------------------------------------------------------------
# Viscous coupling: every strip follows its section polar (fingen.sections)
# --------------------------------------------------------------------------

def _bw04():
    """The [BW04] water-tunnel fin replica (finGenerator-cfd/scripts/bw04_polar.py)."""
    from fingen.params import OutlineParams

    return FinParams(outline=OutlineParams(depth=120.0, base=100.0, sweep=25.0,
                                           tip_width_ratio=0.45, le_fullness=0.75, te_shape=0.8),
                     foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.09),
                     thickness_tip_factor=1.0)


def test_viscous_polar_reproduces_the_tunnel_drag_in_the_linear_range():
    # Brandner & Walker, digitised Figure 2 (+-0.02 on CD): CD 0.030 / 0.035 /
    # 0.055 / 0.09 at 0 / 4 / 8 / 12 deg, where their stated lift line (0.05 per
    # deg from -3.5 deg) gives CL 0.175 / 0.375 / 0.575 / 0.775. Drag is compared
    # at the tunnel's LIFT: a fin that lifts more at the same angle also drags
    # more, and on the full mirror the model lifts 15 % more than the tunnel
    # (its wall is no perfect mirror). Tier-0's flat-plate cd0 has no notion of
    # what a flat inside face costs at low incidence; the section table does.
    from fingen.bladehydro import BOARD_MIRROR_STRENGTH
    from fingen.lattice import viscous_polar

    angles = [-1.0, 0.0, 4.0, 8.0, 12.0, 14.0]
    for strength, tol in ((BOARD_MIRROR_STRENGTH, 0.004), (1.0, 0.012)):
        rows = viscous_polar(_bw04(), 7.0, angles, mirror_strength=strength)
        assert all(ok for _, _, ok in rows)
        cl = [loads.cl for _, loads, _ in rows]
        cd = [loads.cd for _, loads, _ in rows]
        for cl_meas, cd_meas in ((0.175, 0.030), (0.375, 0.035), (0.575, 0.055), (0.775, 0.090)):
            assert float(np.interp(cl_meas, cl, cd)) == pytest.approx(cd_meas, abs=tol)
    # with the weakened image the lift line is the tunnel's as well
    rows = viscous_polar(_bw04(), 7.0, [0.0, 8.0, 12.0], mirror_strength=BOARD_MIRROR_STRENGTH)
    assert (rows[1][1].cl - rows[0][1].cl) / 8.0 == pytest.approx(0.050, rel=0.08)
    # on the full mirror it keeps the known mirror/wall offset (model high)
    rows = viscous_polar(_bw04(), 7.0, [0.0, 8.0, 12.0])
    assert 0.050 < (rows[1][1].cl - rows[0][1].cl) / 8.0 < 0.066
    assert not rows[2][1].separated.any()                   # no strip at its break at 12 deg


def test_induced_drag_is_read_in_the_far_wake():
    # A planar wake cannot beat the elliptic loading: CL^2 / (pi AR CDi) <= 1. The
    # force sum on swept bound legs reads 10-18 % less drag than that bound allows.
    from fingen.lattice import solve_viscous, strip_sections

    fin = _bw04()
    b = blade_from_fin("blade", fin)
    loads = solve_viscous([b], {"blade": strip_sections(fin, b, 7.0)}, 7.0, 8.0).loads["blade"]
    ar = 2.0 * (float(np.sum(b.dz)) ** 2) / b.area
    assert 0.97 < loads.cl**2 / (math.pi * ar * loads.cd_induced) <= 1.0
    assert loads.cl**2 / (math.pi * ar * loads.cd_induced_near) > 1.08
    assert loads.cd == pytest.approx(loads.cd_induced + loads.cd_profile)


def test_ten_strips_carry_the_fine_lattice_lift():
    # Control points at the middle of each strip's clustering-angle step: the lift
    # of a coarse lattice is the fine lattice's within half a percent.
    fin = _bw04()
    coarse = solve([blade_from_fin("b", fin, nz=10, nx=2)], 7.0, 6.0)["b"].cl
    fine = solve([blade_from_fin("b", fin, nz=40, nx=4)], 7.0, 6.0)["b"].cl
    assert coarse == pytest.approx(fine, rel=0.006)


def test_viscous_lattice_sees_the_flat_inside_face_at_the_toe_angle():
    # bench/foil-family, isolated level-2 RANS at -3.5 deg: 13.4 N for the shipped
    # flat-inside side fin (tier-0 generation 3: ~5 N).
    from fingen.lattice import viscous_polar
    from fingen.outline import metrics

    side = _field_fin("side-shipped-gen2.json")
    camb = dataclasses.replace(side, foil=dataclasses.replace(
        side.foil, family=FoilFamily.CAMBERED, camber_ratio=0.03, camber_position=0.4))
    qs = 0.5 * 1025.0 * 8.5**2 * metrics(side.outline).area * 1e-6
    flat_n = viscous_polar(side, 8.5, [-3.5])[0][1].cd * qs
    camb_n = viscous_polar(camb, 8.5, [-3.5])[0][1].cd * qs
    assert flat_n == pytest.approx(13.4, rel=0.20)
    assert camb_n < 0.5 * flat_n


def test_viscous_and_linear_lattice_agree_where_the_section_is_linear():
    from fingen.lattice import solve_viscous, strip_sections

    fin = _field_fin("centre-ridden-gen1.json")
    b = blade_from_fin("c", fin)
    lin = solve([b], 8.5, 4.0)["c"].cl
    sol = solve_viscous([b], {"c": strip_sections(fin, b, 8.5)}, 8.5, 4.0)
    assert sol.converged and sol.iterations < 40
    assert sol.loads["c"].cl == pytest.approx(lin, rel=0.06)        # section slope ~ 2 pi
    assert sol.loads["c"].cd_profile > 0.008


def test_viscous_set_keeps_the_side_fin_roles():
    from fingen.lattice import solve_viscous, strip_sections

    sp = _thruster()
    blades = set_blades(sp)
    pol = {b.name: strip_sections(sp.center if b.name == "center" else sp.side, b, 8.5)
           for b in blades}
    sol = solve_viscous(blades, pol, 8.5, 5.0)
    assert sol.converged
    right, left, centre = (sol.loads[k] for k in ("right", "left", "center"))
    assert right.cl > left.cl > 0.0 and centre.cl > 0.0
    assert left.alpha_eff_deg.mean() < -3.0 < right.alpha_eff_deg.mean()   # against / with camber
    assert left.cd_profile > 1.5 * right.cd_profile        # the flat face, loaded the wrong way
    with pytest.raises(ValueError):
        solve_viscous(blades, {**pol, "left": pol["left"][:-1]}, 8.5, 5.0)


def test_a_flat_inside_blade_driven_from_its_curved_side_levels_off():
    # bench/phase2b/outside-fin: the shipped gen-2 side alone at negative own incidence,
    # mesh levels 5 and 6. It follows its lift line to -8 deg and levels off at -0.29 to
    # -0.35 from -9 deg; the strips on the table carry it on to -0.51, because the 2-D
    # referee's lift goes on growing behind a flat inside face's lower end. held_below
    # holds a flat-inside strip's lift LOWER_HOLD_DEG past that end: one number, fitted here.
    from fingen.lattice import LOWER_HOLD_DEG, held_below, solve_viscous, strip_sections

    side = _field_fin("side-shipped-gen2.json")
    blade = blade_from_fin("blade", side, nz=10, nx=2)
    pol = strip_sections(side, blade, 8.5, "v1")
    held = held_below(pol)
    assert LOWER_HOLD_DEG == 1.5

    def cl(polars, alpha):
        return solve_viscous([blade], {"blade": polars}, 8.5, alpha).loads["blade"].cl

    simulation = {-8.0: -0.258, -10.0: -0.295, -12.0: -0.310, -16.0: -0.349}
    for alpha, ref in simulation.items():
        assert cl(held, alpha) == pytest.approx(ref, rel=0.10)
    assert cl(pol, -12.0) < 1.3 * simulation[-12.0]              # not held: 40 % too much
    assert cl(pol, -16.0) < 1.4 * simulation[-16.0]
    # up to the lower end and a little past it nothing changes
    for alpha in (-6.0, 0.0, 6.0):
        assert cl(held, alpha) == pytest.approx(cl(pol, alpha), abs=1e-9)
    # only the lift of flat-inside strips is held: drag is the table's, a cambered blade's
    # polars and table v0's (no attached range) come back as they are
    assert all(np.array_equal(h.cd, p.cd) for h, p in zip(held, pol, strict=True))
    cambered = dataclasses.replace(side, foil=dataclasses.replace(
        side.foil, family=FoilFamily.CAMBERED, camber_ratio=0.03, camber_position=0.4))
    pc = strip_sections(cambered, blade, 8.5, "v1")
    assert all(h is p for h, p in zip(held_below(pc), pc, strict=True))
    p0 = strip_sections(side, blade, 8.5, "v0")
    assert all(h is p for h, p in zip(held_below(p0), p0, strict=True))
