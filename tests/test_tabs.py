"""Mounting-tab geometry (docs/TAB-SYSTEMS.md)."""

import pytest
from build123d import Box, Pos

from fingen.check import check_solid
from fingen.loft import fin_solid
from fingen.params import (
    FinParams,
    FoilFamily,
    FoilParams,
    GenSettings,
    OutlineParams,
    TabParams,
    TabSystem,
)
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
    # base 70 with dual tabs is LEGAL under the engagement rule (1.5 mm
    # overhang per end, 18.5 mm engaged — real grom fins do this); a base
    # where a tab cannot reach its engagement floor still rejects cleanly.
    fin = FinParams(outline=OutlineParams(depth=90.0, base=70.0),
                    tabs=TabParams(system=TabSystem.DUAL_TAB))
    fin_solid(fin, COARSE)  # builds
    tiny = FinParams(outline=OutlineParams(depth=90.0, base=45.0),
                     tabs=TabParams(system=TabSystem.DUAL_TAB))
    # (the y-envelope guard fires first here — a 6.15 mm tab can't fit a
    # ±2.1 mm section; either way: clean rejection, never a corrupt build)
    with pytest.raises(ValueError):
        fin_solid(tiny, COARSE)


def test_coupons_build():
    for system in (TabSystem.DUAL_TAB, TabSystem.SINGLE_TAB, TabSystem.CLICK_TAB):
        part = coupon_solid(TabParams(system=system))
        assert len(part.solids()) == 1
        assert part.volume > 4000
    with pytest.raises(ValueError):
        coupon_solid(TabParams())


def test_flat_fin_tabs_flush_with_flat_side():
    # FLAT_INSIDE anchors the tab's inner face at y=0: fin + tabs print
    # flat on the bed together. Symmetric fins keep the centered anchor.
    flat = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                     tabs=TabParams(system=TabSystem.DUAL_TAB))
    part = build_tabs(flat, COARSE)
    assert abs(part.bounding_box().min.Y) < 1e-6
    sym = FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC),
                    tabs=TabParams(system=TabSystem.DUAL_TAB))
    part = build_tabs(sym, COARSE)
    assert part.bounding_box().min.Y < -2.0  # centered: crosses the midline


def test_tab_offsets_move_the_set():
    base = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                     tabs=TabParams(system=TabSystem.DUAL_TAB))
    moved = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                      tabs=TabParams(system=TabSystem.DUAL_TAB,
                                     x_offset=8.0, y_offset=1.5))
    bb0 = build_tabs(base, COARSE).bounding_box()
    bb1 = build_tabs(moved, COARSE).bounding_box()
    assert abs((bb1.min.X - bb0.min.X) - 8.0) < 1e-6
    assert abs((bb1.min.Y - bb0.min.Y) - 1.5) < 1e-6


def test_flat_fin_with_tabs_is_one_checked_solid():
    # The anchor change altered the union topology: pin it at whole-fin
    # level for the common side-fin case.
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                    tabs=TabParams(system=TabSystem.DUAL_TAB))
    part = fin_solid(fin, COARSE)
    report = check_solid(part, fin, COARSE)
    assert report.ok, report.issues
    assert part.bounding_box().min.Y > -1e-6  # nothing below the flat plane


def test_symmetric_y_offset_sign():
    # A sign flip in the y_offset application must not survive the suite.
    lo = FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC),
                   tabs=TabParams(system=TabSystem.DUAL_TAB, y_offset=-1.5))
    hi = FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC),
                   tabs=TabParams(system=TabSystem.DUAL_TAB, y_offset=1.5))
    shift = (build_tabs(hi, COARSE).bounding_box().min.Y
             - build_tabs(lo, COARSE).bounding_box().min.Y)
    assert shift == pytest.approx(3.0)


def test_tab_leaving_section_envelope_rejected():
    # Thin blade + full positive y travel: clean ValueError naming the
    # parameter, not a post-loft checker refusal.
    fin = FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC,
                                    thickness_ratio=0.04),
                    tabs=TabParams(system=TabSystem.DUAL_TAB, y_offset=3.0))
    with pytest.raises(ValueError, match="envelope"):
        build_tabs(fin, COARSE)


def test_tab_overhang_allowed_but_engagement_required():
    # Commercial-style: rear tab overhangs the aft base corner — legal.
    over = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                     tabs=TabParams(system=TabSystem.CLICK_TAB, x_offset=8.0))
    bb = build_tabs(over, COARSE).bounding_box()
    overhang = bb.max.X - over.outline.base
    assert overhang > 0  # genuinely past the aft base corner
    # But an unengaged tab is refused, naming the shortfall.
    off = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                    tabs=TabParams(system=TabSystem.DUAL_TAB, x_offset=35.0))
    with pytest.raises(ValueError, match="engaged"):
        build_tabs(off, COARSE)


def test_click_tabs_fit_small_base_via_overhang():
    # base 96 < click span 98: impossible under the old containment rule,
    # normal on commercial small fins. Whole-fin build + check must pass.
    fin = FinParams(outline=OutlineParams(base=96.0),
                    foil=FoilParams(family=FoilFamily.FLAT_INSIDE),
                    tabs=TabParams(system=TabSystem.CLICK_TAB))
    part = fin_solid(fin, COARSE)
    report = check_solid(part, fin, COARSE)
    assert report.ok, report.issues
