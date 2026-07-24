"""Mounting-tab geometry (docs/TAB-SYSTEMS.md)."""

import pytest
from build123d import Box, Pos

from fingen.check import check_solid
from fingen.loft import fin_solid
from fingen.params import FinParams, GenSettings, OutlineParams, TabParams, TabSystem
from fingen.tabs import build_tabs, coupon_solid, system_depth

COARSE = GenSettings(n_stations=11, n_foil_points=60)


def _fin(system, **tab_kw):
    return FinParams(tabs=TabParams(system=system, **tab_kw))


@pytest.mark.parametrize("system,depth", [
    (TabSystem.DUAL_TAB, 14.0),
    (TabSystem.SINGLE_TAB, 17.5),
    (TabSystem.CLICK_TAB, 14.0),
])
def test_tabbed_fin_builds_checks_and_reaches_depth(system, depth):
    fin = _fin(system)
    part = fin_solid(fin, COARSE)
    report = check_solid(part, fin, COARSE)
    assert report.ok, report.issues
    assert pytest.approx(-depth, abs=0.05) == part.bounding_box().min.Z
    assert system_depth(fin.tabs) == depth


def test_none_means_flat_base():
    fin = FinParams()
    assert build_tabs(fin, COARSE) is None
    assert pytest.approx(0.0, abs=0.2) == fin_solid(fin, COARSE).bounding_box().min.Z


def test_dual_tab_geometry():
    tabs = build_tabs(_fin(TabSystem.DUAL_TAB), COARSE)
    slab = tabs & (Pos(55, 0, -7) * Box(400, 100, 1))
    assert len(slab.solids()) == 2  # two separate tabs
    bb = tabs.bounding_box()
    assert pytest.approx(73.0, abs=0.1) == bb.max.X - bb.min.X  # 53 pitch + 20 tab


def test_single_tab_front_hooks_forward():
    tabs = build_tabs(_fin(TabSystem.SINGLE_TAB), COARSE)
    top = tabs & (Pos(55, 0, -0.5) * Box(400, 100, 1))
    bot = tabs & (Pos(55, 0, -17.0) * Box(400, 100, 1))
    assert bot.bounding_box().min.X < top.bounding_box().min.X  # bottom edge leads


def test_click_tab_trailing_rake_and_notch():
    tabs = build_tabs(_fin(TabSystem.CLICK_TAB), COARSE)
    top = tabs & (Pos(55, 0, -0.5) * Box(400, 100, 1))
    bot = tabs & (Pos(55, 0, -13.5) * Box(400, 100, 1))
    assert bot.bounding_box().max.X < top.bounding_box().max.X  # raked TE
    # Hook notch: a slab through 4-8 mm below surface is shorter at the front.
    notch = tabs & (Pos(55, 0, -6) * Box(400, 100, 1))
    assert notch.bounding_box().min.X > top.bounding_box().min.X


def test_fit_offset_changes_thickness():
    loose = build_tabs(_fin(TabSystem.SINGLE_TAB, fit_offset=-0.4), COARSE)
    tight = build_tabs(_fin(TabSystem.SINGLE_TAB, fit_offset=0.2), COARSE)
    def dy(p):
        return p.bounding_box().max.Y - p.bounding_box().min.Y

    assert dy(tight) - dy(loose) == pytest.approx(0.6, abs=0.05)


def test_small_base_rejected_cleanly():
    fin = FinParams(outline=OutlineParams(depth=90.0, base=70.0),
                    tabs=TabParams(system=TabSystem.DUAL_TAB))
    with pytest.raises(ValueError):
        fin_solid(fin, COARSE)


def test_coupons_build():
    for system in (TabSystem.DUAL_TAB, TabSystem.SINGLE_TAB, TabSystem.CLICK_TAB):
        part = coupon_solid(TabParams(system=system))
        assert len(part.solids()) == 1
        assert part.volume > 4000
    with pytest.raises(ValueError):
        coupon_solid(TabParams())
