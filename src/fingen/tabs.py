"""Fin mounting tabs (docs/TAB-SYSTEMS.md).

Three proprietary systems, implemented from convergent community measurements
(no official drawings exist; see the doc for sources, confidence and the
patent/trademark situation — generic names are deliberate):

- DUAL_TAB   (FCS-compatible): two 20×14 mm rectangular tabs, 53 mm apart.
- SINGLE_TAB (Futures-compatible): one blade-length tab, angled front face.
- CLICK_TAB  (FCS II-compatible): 45+33 mm tabs, hook notch, side indents.

Tabs extend below the base plane (z < 0) and are fused onto the blade.
Thickness anchor: FLAT_INSIDE fins carry the tab's inner face flush with the
y = 0 flat plane (the whole fin prints flat on the bed, like commercial
flat-foiled fins — boxes have the lateral clearance for it); other families
center the tab on the base section's mid-thickness. TabParams.x_offset /
y_offset slide the set along the base / across the thickness from there. All dimensions carry a
`fit_offset` on thickness — printers vary, boxes are the ground truth; print
the test coupon (`fingen coupon`) before a full fin. v1 simplifications,
documented deliberately: no draft angles, sharp hook-notch root (R2 in the
reference models), no screw groove on the single tab (the grub screw bears
directly on the angled face, as most printed fins do).
"""

from __future__ import annotations

import numpy as np
from build123d import Axis, Box, Part, Plane, Polygon, Pos, extrude

from fingen.foil import section_points
from fingen.params import (
    DEFAULT_SETTINGS,
    FinParams,
    FoilFamily,
    GenSettings,
    TabParams,
    TabSystem,
)

# Nominal (slot-side) dimensions in mm from docs/TAB-SYSTEMS.md.
_DUAL_LEN, _DUAL_DEPTH, _DUAL_THICK, _DUAL_PITCH = 20.0, 14.0, 6.35, 53.0
_DUAL_CORNER = 2.0
_SINGLE_THICK, _SINGLE_DEPTH_SIDE, _SINGLE_MAXLEN = 7.19, 17.5, 110.0
_SINGLE_FRONT_ANGLE = 6.0  # deg, LOW confidence — single community source
_CLICK_FRONT, _CLICK_REAR, _CLICK_GAP, _CLICK_DEPTH, _CLICK_THICK = 45.0, 33.0, 20.0, 14.0, 6.35
_CLICK_SPAN = _CLICK_FRONT + _CLICK_GAP + _CLICK_REAR  # 98.0
_CLICK_TE_RAKE = 20.0  # deg
# Hook notch on the front tab's leading edge: 4 mm tall, 4-8 mm below surface.
_NOTCH_TOP, _NOTCH_BOTTOM, _NOTCH_DEEP = 4.0, 8.0, 4.5
# Retention indents on both faces of the rear tab.
_INDENT_LEN, _INDENT_TALL, _INDENT_TOP, _INDENT_SETBACK = 15.0, 6.0, 3.0, 0.7


def system_depth(tabs: TabParams) -> float:
    """How far the tabs extend below the base plane (0 for NONE)."""
    if tabs.system is TabSystem.NONE:
        return 0.0
    if tabs.tab_depth is not None:
        return tabs.tab_depth
    return {TabSystem.DUAL_TAB: _DUAL_DEPTH,
            TabSystem.SINGLE_TAB: _SINGLE_DEPTH_SIDE,
            TabSystem.CLICK_TAB: _CLICK_DEPTH}[tabs.system]


def tab_span_x(fin: FinParams) -> tuple[float, float] | None:
    """(x_lo, x_hi) chordwise extent the tab set occupies, or None for NONE.

    Used to tell the tab-to-blade junction edges apart from the blade's own
    base outline — both lie in z = 0, only the first is a step."""
    tabs = fin.tabs
    if tabs.system is TabSystem.NONE:
        return None
    base = fin.outline.base
    if tabs.system is TabSystem.SINGLE_TAB:
        length = min(base - 12.0, _SINGLE_MAXLEN)
        x0 = (base - length) / 2.0 + tabs.x_offset
        return x0, x0 + length
    span = (_DUAL_PITCH + _DUAL_LEN if tabs.system is TabSystem.DUAL_TAB
            else _CLICK_SPAN)
    x0 = (base - span) / 2.0 + tabs.x_offset
    return x0, x0 + span


def system_thickness(tabs: TabParams) -> float:
    """Nominal tab thickness as lofted, including the printed fit_offset."""
    if tabs.system is TabSystem.NONE:
        return 0.0
    nominal = {TabSystem.DUAL_TAB: _DUAL_THICK,
               TabSystem.SINGLE_TAB: _SINGLE_THICK,
               TabSystem.CLICK_TAB: _CLICK_THICK}[tabs.system]
    return nominal + tabs.fit_offset


def _base_mid_y(fin: FinParams, settings: GenSettings) -> float:
    """Mid-thickness of the base section — the non-flat-family tab centerline."""
    upper, lower = section_points(fin.foil, fin.outline.base,
                                  n_points=settings.n_foil_points)
    return float((upper[:, 1].max() + lower[:, 1].min()) / 2.0)


def _tab_center_y(fin: FinParams, settings: GenSettings, thick: float) -> float:
    """Tab centerline in y for a tab of the given thickness: flush with the
    flat face on FLAT_INSIDE fins (printability anchor), mid-thickness
    elsewhere; TabParams.y_offset shifts from that anchor. Raises a clean
    ValueError (naming the parameter) when the tab would leave the base
    section's thickness envelope — the checker would refuse that geometry
    anyway, but only after a full loft+fuse and with a message that blames
    the blade instead of y_offset."""
    if fin.foil.family is FoilFamily.FLAT_INSIDE:
        y_c = thick / 2.0 + fin.tabs.y_offset
    else:
        y_c = _base_mid_y(fin, settings) + fin.tabs.y_offset
    upper, lower = section_points(fin.foil, fin.outline.base,
                                  n_points=settings.n_foil_points)
    y_max, y_min = float(upper[:, 1].max()), float(lower[:, 1].min())
    slack = 0.3
    if y_c + thick / 2.0 > y_max + slack or y_c - thick / 2.0 < y_min - slack:
        raise ValueError(
            f"tab (thickness {thick:.2f} mm at y_offset "
            f"{fin.tabs.y_offset:+.1f} mm) leaves the base section envelope "
            f"[{y_min:.2f}, {y_max:.2f}] mm — reduce |y_offset| or thicken "
            "the section")
    return y_c


def _require_engagement(intervals: list[tuple[float, float]], base: float,
                        x_offset: float, label: str) -> None:
    """Each tab must keep enough length engaged under the base footprint to
    fuse structurally — but tabs MAY overhang the base ends: commercial
    click fins align the rear indent with the fin's aft end, and on small
    fins (base < set span) overhang is the only way the set fits at all.
    Engagement floor: half the tab's length, at least 8 mm."""
    for x_lo, x_hi in intervals:
        need = max(0.5 * (x_hi - x_lo), 8.0)
        got = min(x_hi, base) - max(x_lo, 0.0)
        if got < need:
            raise ValueError(
                f"tab x_offset {x_offset:+.1f} mm leaves a {label} tab at "
                f"[{x_lo:.1f}, {x_hi:.1f}] mm with only {max(got, 0.0):.1f} mm "
                f"engaged under the {base:.0f} mm base (needs {need:.1f} mm)")


def _raked_cut(x_face: float, angle_deg: float, side: str) -> Part:
    """Half-space cutter bounded by a raked plane through (x_face, z=0) whose
    BOTTOM edge leads (x decreases with z): x(z) = x_face + z·tan(angle).
    side="front" removes material forward of the plane, "aft" removes aft.
    Built as an exact extruded polygon — no rotation-sign pitfalls."""
    t = float(np.tan(np.radians(angle_deg)))
    z_top, z_bot = 60.0, -60.0
    x_top, x_bot = x_face + z_top * t, x_face + z_bot * t
    far = -300.0 if side == "front" else 300.0
    pts = [(x_top, z_top), (x_bot, z_bot), (x_bot + far, z_bot), (x_top + far, z_top)]
    return Part() + extrude(Plane.XZ * Polygon(*pts, align=None), amount=100.0, both=True)


def build_tabs(fin: FinParams, settings: GenSettings) -> Part | None:
    """Build the tab solid for the fin, or None for TabSystem.NONE.

    Raises ValueError when the fin base is too short for the system's span —
    a clean rejection, consistent with the generator's production contract.
    """
    tabs = fin.tabs
    if tabs.system is TabSystem.NONE:
        return None

    base = fin.outline.base
    depth = system_depth(tabs)

    if tabs.system is TabSystem.DUAL_TAB:
        thick = _DUAL_THICK + tabs.fit_offset
        y_c = _tab_center_y(fin, settings, thick)
        span = _DUAL_PITCH + _DUAL_LEN  # 73 mm outer span
        x0 = (base - span) / 2.0 + tabs.x_offset
        _require_engagement([(x0, x0 + _DUAL_LEN),
                             (x0 + _DUAL_PITCH, x0 + span)],
                            base, tabs.x_offset, "dual-tab")
        solid = None
        for cx in (x0 + _DUAL_LEN / 2.0, x0 + _DUAL_PITCH + _DUAL_LEN / 2.0):
            tab = Pos(cx, y_c, -depth / 2.0) * Box(_DUAL_LEN, thick, depth)
            bottom = tab.edges().filter_by(Axis.Y).group_by(Axis.Z)[0]
            tab = tab.fillet(_DUAL_CORNER, bottom)
            solid = tab if solid is None else solid + tab
        return Part() + solid

    if tabs.system is TabSystem.SINGLE_TAB:
        thick = _SINGLE_THICK + tabs.fit_offset
        y_c = _tab_center_y(fin, settings, thick)
        length = min(base - 12.0, _SINGLE_MAXLEN)
        if length < 50.0:
            raise ValueError(f"single-tab needs a base of at least 62 mm (got {base:.0f} mm)")
        x0 = (base - length) / 2.0 + tabs.x_offset
        _require_engagement([(x0, x0 + length)], base, tabs.x_offset, "single-tab")
        tab = Pos(x0 + length / 2.0, y_c, -depth / 2.0) * Box(length, thick, depth)
        # Angled front face, bottom edge leading: the fin hooks in nose-first.
        tab -= _raked_cut(x0 + depth * 0.06, _SINGLE_FRONT_ANGLE, "front")
        return Part() + tab

    # CLICK_TAB
    thick = _CLICK_THICK + tabs.fit_offset
    y_c = _tab_center_y(fin, settings, thick)
    x0 = (base - _CLICK_SPAN) / 2.0 + tabs.x_offset
    rear_span = (x0 + _CLICK_FRONT + _CLICK_GAP, x0 + _CLICK_SPAN)
    _require_engagement([(x0, x0 + _CLICK_FRONT), rear_span],
                        base, tabs.x_offset, "click-tab")
    front = Pos(x0 + _CLICK_FRONT / 2.0, y_c, -depth / 2.0) * Box(_CLICK_FRONT, thick, depth)
    # Trailing-edge rake (bottom forward) eases the insertion rotation.
    front -= _raked_cut(x0 + _CLICK_FRONT, _CLICK_TE_RAKE, "aft")
    # Hook notch in the leading edge: the material below it is the nose that
    # slides under the plug's internal bar.
    front -= (Pos(x0 + _NOTCH_DEEP / 2.0, y_c, -(_NOTCH_TOP + _NOTCH_BOTTOM) / 2.0)
              * Box(_NOTCH_DEEP, thick + 2.0, _NOTCH_BOTTOM - _NOTCH_TOP))

    rear_x0 = x0 + _CLICK_FRONT + _CLICK_GAP
    rear = Pos(rear_x0 + _CLICK_REAR / 2.0, y_c, -depth / 2.0) * Box(_CLICK_REAR, thick, depth)
    rear -= _raked_cut(rear_x0 + _CLICK_REAR, _CLICK_TE_RAKE, "aft")
    # Spring-barrel indents on BOTH faces of the rear tab.
    if tabs.click_indent_depth > 0.0:
        z_mid = -(_INDENT_TOP + _INDENT_TALL / 2.0)
        for side in (-1.0, 1.0):
            y_face = y_c + side * thick / 2.0
            rear -= (Pos(rear_x0 + _INDENT_SETBACK + _INDENT_LEN / 2.0,
                         y_face - side * tabs.click_indent_depth / 2.0, z_mid)
                     * Box(_INDENT_LEN, tabs.click_indent_depth + 0.2, _INDENT_TALL))
    return Part() + front + rear


def coupon_solid(tabs: TabParams, settings: GenSettings = DEFAULT_SETTINGS) -> Part:
    """Test-fit coupon: a small plate carrying just the tabs — minutes to
    print, so the fit_offset gets dialed against real boxes before a full fin."""
    if tabs.system is TabSystem.NONE:
        raise ValueError("coupon needs a tab system (dual/single/click)")
    from dataclasses import replace

    from fingen.params import FinParams, FoilParams

    # The coupon tests the box interface, not the placement — offsets zeroed.
    tabs = replace(tabs, x_offset=0.0, y_offset=0.0)

    span = {TabSystem.DUAL_TAB: 79.0, TabSystem.SINGLE_TAB: 92.0,
            TabSystem.CLICK_TAB: 104.0}[tabs.system]
    stub = FinParams(outline=type(FinParams().outline)(base=max(span + 8.0, 80.0)),
                     foil=FoilParams(), tabs=tabs)
    tab_part = build_tabs(stub, settings)
    y_mid = _base_mid_y(stub, settings)
    plate = (Pos(stub.outline.base / 2.0, y_mid, 2.5)
             * Box(stub.outline.base, max(12.0, _SINGLE_THICK + 6.0), 5.0))
    return Part() + plate + tab_part
