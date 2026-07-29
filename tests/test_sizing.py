"""The anchor: absolute requirements and the optimizer's hard gate."""

import pytest

from fingen.params import (
    FinConfig,
    FinParams,
    FoilFamily,
    FoilParams,
    OutlineParams,
    TabParams,
    TabSystem,
)
from fingen.sizing import (
    KT_TAB,
    Skill,
    anchor,
    base_bending_stress_mpa,
    check_anchor,
    required_side_force_n,
    tab_neck_stress_mpa,
)


def test_center_member_carries_a_smaller_share_than_the_dominant():
    """The aft/center fin of a thruster carries LESS load than the dominant
    front (measured Falk split: ~(1 - rear deficit) of it), so sizing it must
    ask for less force. Sizing it against the dominant share while its produced
    force is ALSO downwash-derated would systematically oversize it."""
    from fingen.params import FinConfig
    from fingen.sizing import CONFIG_CENTER_SHARE, CONFIG_DOMINANT_SHARE

    dom = anchor(46.0, Skill.ADVANCED, config=FinConfig.THRUSTER)
    cen = anchor(46.0, Skill.ADVANCED, config=FinConfig.THRUSTER, member="center")

    assert required_side_force_n(cen) < required_side_force_n(dom)
    expected = (CONFIG_CENTER_SHARE[FinConfig.THRUSTER]
                / CONFIG_DOMINANT_SHARE[FinConfig.THRUSTER])
    assert required_side_force_n(cen) / required_side_force_n(dom) == pytest.approx(expected)
    # The smaller share sizes a smaller blade, and the peak load follows too.
    assert cen.area_min_mm2 < dom.area_min_mm2
    assert cen.force_peak_n < dom.force_peak_n

    # Configs with no co-designed center fall back to the dominant share.
    quad_dom = anchor(46.0, Skill.ADVANCED, config=FinConfig.QUAD)
    quad_cen = anchor(46.0, Skill.ADVANCED, config=FinConfig.QUAD, member="center")
    assert quad_cen.force_peak_n == quad_dom.force_peak_n

    with pytest.raises(ValueError):
        anchor(46.0, Skill.ADVANCED, member="nonsense")


def test_anchor_matches_measured_loads():
    # ~85 kg rider system in a hard turn should land near the measured
    # ~300 N per-fin peak [Knies25] (calibration target of the share model).
    sheet = anchor(82.0, Skill.ADVANCED)
    assert 220.0 < sheet.force_peak_n < 420.0
    # Sustained ≈ a third of the peak — the [Knies25] coherence check.
    assert 2.0 < sheet.force_peak_n / sheet.force_work_n < 4.5
    assert sheet.force_work_n < sheet.force_peak_n
    assert sheet.area_min_mm2 < sheet.area_max_mm2


def test_default_fin_feasible_for_mid_rider():
    sheet = anchor(75.0, Skill.INTERMEDIATE, tabs=TabSystem.SINGLE_TAB)
    assert check_anchor(FinParams(), sheet) == []


def test_gate_catches_undersized_fin():
    sheet = anchor(95.0, Skill.PRO)
    tiny = FinParams(outline=OutlineParams(depth=80.0, base=70.0))
    issues = check_anchor(tiny, sheet)
    assert any("area" in i or "side force" in i for i in issues)


def test_gate_catches_weak_section():
    sheet = anchor(95.0, Skill.PRO)
    thin = FinParams(foil=FoilParams(thickness_ratio=0.04, te_thickness=0.4))
    assert any("stress" in i for i in check_anchor(thin, sheet))


def test_peak_stress_envelope_never_loosens_the_root_gate():
    """The gate takes max(root-plane, station-sweep). Neither term dominates —
    the base IS the critical section for roughly half the design space, and
    mid-span for the rest (docs/FEM-BENCH.md) — so the envelope must never read
    BELOW the root-only value it replaced. A regression here would silently pass
    fins the old gate rejected."""
    from fingen.sizing import base_bending_stress_mpa, peak_bending_stress_mpa

    sheet = anchor(82.0, Skill.ADVANCED, tabs=TabSystem.CLICK_TAB)
    shapes = [
        FinParams(),
        FinParams(outline=OutlineParams(depth=140.0, base=110.0)),
        FinParams(outline=OutlineParams(depth=80.0, base=130.0)),   # squat keel
        FinParams(outline=OutlineParams(depth=160.0, base=90.0)),   # upright
        FinParams(foil=FoilParams(thickness_ratio=0.05, te_thickness=0.5)),
        FinParams(foil=FoilParams(thickness_ratio=0.11)),
    ]
    for fin in shapes:
        root = base_bending_stress_mpa(fin, sheet.force_peak_n)
        env = peak_bending_stress_mpa(fin, sheet)
        assert env >= root - 1e-9, f"envelope {env} below root {root} for {fin.outline}"


def test_peak_stress_envelope_catches_the_mid_span_peak():
    """A strongly tapered blade thins faster than its moment falls, so the
    critical station moves inboard. Tier-1 FEM measured this on the anchor fin:
    peak at 53 % of span, 1.44x the root band. The envelope must see it."""
    from fingen.sizing import base_bending_stress_mpa, peak_bending_stress_mpa

    sheet = anchor(82.0, Skill.ADVANCED, tabs=TabSystem.CLICK_TAB)
    tapered = FinParams(outline=OutlineParams(depth=130.0, base=115.0,
                                              tip_width_ratio=0.42,
                                              le_fullness=0.0))
    assert (peak_bending_stress_mpa(tapered, sheet)
            > 1.2 * base_bending_stress_mpa(tapered, sheet.force_peak_n))


def test_peak_stress_envelope_accepts_a_precomputed_span_stress():
    """optimize.evaluate already solves flex; passing its number in must give
    the same answer as letting the envelope solve it again (and skip the cost)."""
    from fingen.flex import flex_report
    from fingen.sizing import peak_bending_stress_mpa

    sheet = anchor(75.0, Skill.INTERMEDIATE, tabs=TabSystem.CLICK_TAB)
    fin = FinParams()
    span = flex_report(fin, sheet.force_peak_n, sheet.design_speed,
                       material=sheet.material).stress_max_mpa
    assert peak_bending_stress_mpa(fin, sheet, span) == pytest.approx(
        peak_bending_stress_mpa(fin, sheet), rel=1e-9)


def test_heavier_rider_needs_more_fin():
    light = anchor(55.0, Skill.INTERMEDIATE)
    heavy = anchor(100.0, Skill.INTERMEDIATE)
    assert heavy.force_peak_n > light.force_peak_n
    assert heavy.area_min_mm2 > light.area_min_mm2


def test_stress_scales_with_thickness():
    fat = FinParams(foil=FoilParams(thickness_ratio=0.12))
    slim = FinParams(foil=FoilParams(thickness_ratio=0.05))
    assert base_bending_stress_mpa(slim, 300.0) > base_bending_stress_mpa(fat, 300.0)


def test_unknown_material_rejected():
    with pytest.raises(ValueError):
        anchor(75.0, material="unobtainium")


def test_required_side_force_pins_the_safety_factor():
    # House pin against a hand-computed literal so the FORCE_SF factor (and the
    # force_work_n build-up it multiplies) cannot silently vanish — dropping it
    # weakens the capacity gate AND inflates every hold score. For a 75 kg
    # intermediate thruster (m_total = 75 + 3 = 78 kg, share = 0.6):
    #   F_req = SUSTAINED_WEIGHT_FRACTION · m_total·g · (share/0.6) · FORCE_SF
    #         = 0.103 · 78 · 9.81 · (0.6/0.6) · 1.3
    #         = 78.81354 · 1.3 = 102.457602 N
    sheet = anchor(75.0, Skill.INTERMEDIATE, 6.4, FinConfig.THRUSTER, "pet-cf")
    assert required_side_force_n(sheet) == pytest.approx(102.457602, rel=1e-6)
    # And it is strictly the working load scaled UP by the factor (guards the
    # factor being dropped or set to 1): F_req = force_work_n · 1.3.
    assert required_side_force_n(sheet) == pytest.approx(sheet.force_work_n * 1.3,
                                                         rel=1e-12)


def test_tab_neck_stress_inactive_for_glass_on():
    # #24: TabSystem.NONE (glass-on) leaves the gate inactive — no stress, no
    # allowable to compare against.
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    assert fin.tabs.system is TabSystem.NONE
    assert tab_neck_stress_mpa(fin, 12.0, 220.0) is None


def test_tab_stress_is_bending_through_the_tabs_own_section():
    # The tabs are the ONLY material crossing z = 0, and every box reaction acts
    # BELOW that cut, so by statics they transmit the WHOLE root moment — in
    # BENDING, through their own section modulus:
    #     S_tab = sum(L) * t_tab^2 / 6,  t_tab = system thickness + fit_offset
    # t_tab is the TAB's thickness, NOT the blade's t/c*base. This replaces a
    # bearing/shear model whose implied section modulus was ~8x too large (it
    # divided a couple FORCE by the blade's fused footprint), reporting SF 4.7
    # where the bending number is 1.4 — so the optimizer never felt the tab.
    m_nm, v_n = 12.0, 220.0
    fin = FinParams(outline=OutlineParams(base=110.0),
                    foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.10),
                    tabs=TabParams(system=TabSystem.DUAL_TAB))
    assert KT_TAB == 2.5  # independent-literal pin on the calibration constant

    t_tab = 6.35 - 0.2                       # _DUAL_THICK + default fit_offset
    s_tab = (20.0 + 20.0) * t_tab**2 / 6.0   # mm^3, both tabs share a neutral axis
    assert s_tab == pytest.approx(252.15, rel=1e-4)
    t_weld = min(0.10 * 110.0, t_tab)        # the weld is only as thick as the thinner
    expected = (2.5 * m_nm / (s_tab * 1e-9) / 1e6
                + v_n / ((20.0 + 20.0) * t_weld * 1e-6) / 1e6)
    assert tab_neck_stress_mpa(fin, m_nm, v_n) == pytest.approx(expected, rel=1e-9)

    # MUTATION GUARD — the retired bearing model. Dividing a couple force by the
    # blade footprint gives a far LOWER stress; the pin above rejects it.
    lever = (2.0 / 3.0) * 14.0 * 1e-3
    old = 2.5 * ((m_nm / 2.0) / lever + v_n / 2.0) / ((20.0 * 1e-3) * 0.011) / 1e6
    assert old < 0.2 * expected

    # MUTATION GUARD — using the BLADE thickness for the tab section. The blade
    # is 11.0 mm here vs the tab's 6.15, and S goes as t^2, so this is ~3.2x
    # optimistic. It is the specific bug that was in the module.
    s_blade = (20.0 + 20.0) * (0.10 * 110.0)**2 / 6.0
    assert 2.5 * m_nm / (s_blade * 1e-9) / 1e6 < 0.4 * expected


def test_tab_section_is_fixed_by_the_BOX_not_the_blade():
    # Consequence the design has to live with: S_tab depends only on the tab
    # SYSTEM, so a fin cannot strengthen its own mounting by getting thicker.
    # Only the root MOMENT can move. (This is why gating tier-0 on the tab makes
    # the search degrade the blade rather than improve the tab.)
    thin = FinParams(outline=OutlineParams(base=110.0),
                     foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.05),
                     tabs=TabParams(system=TabSystem.CLICK_TAB))
    thick = FinParams(outline=OutlineParams(base=110.0),
                      foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.14),
                      tabs=TabParams(system=TabSystem.CLICK_TAB))
    m_nm = 10.0
    # With zero shear the stress is pure bending and must be IDENTICAL.
    assert (tab_neck_stress_mpa(thin, m_nm, 0.0)
            == pytest.approx(tab_neck_stress_mpa(thick, m_nm, 0.0), rel=1e-12))
    # And it scales linearly with the moment.
    assert (tab_neck_stress_mpa(thin, 2 * m_nm, 0.0)
            == pytest.approx(2 * tab_neck_stress_mpa(thin, m_nm, 0.0), rel=1e-12))


def test_futures_single_tab_is_stronger_than_fcs_ii():
    # A real design consequence of the section view: FUTURES puts ONE long
    # 7.19 mm bar where FCS II puts two 6.35 mm ones, so S is ~1.5x larger and
    # the same fin is meaningfully better mounted. Worth knowing when a rider
    # asks which board to buy.
    def s_for(system, base):
        fin = FinParams(outline=OutlineParams(base=base),
                        foil=FoilParams(family=FoilFamily.SYMMETRIC, thickness_ratio=0.09),
                        tabs=TabParams(system=system))
        return tab_neck_stress_mpa(fin, 10.0, 0.0)

    click = s_for(TabSystem.CLICK_TAB, 110.0)
    single = s_for(TabSystem.SINGLE_TAB, 110.0)
    assert single < click                      # lower stress = stronger mount
    assert click / single == pytest.approx(1.5, abs=0.15)
    # SINGLE_TAB's length tracks the base and clamps at 110 mm.
    assert s_for(TabSystem.SINGLE_TAB, 250.0) == pytest.approx(
        s_for(TabSystem.SINGLE_TAB, 122.0), rel=1e-9)


def test_printed_tab_is_critical_where_the_blade_is_not():
    # REALITY ANCHOR, corrected. The retired model put a commercial-shaped
    # dual-tab side fin at tab_sf 3.0 — i.e. printed tabs never fail. They do:
    # snapping flush at the deck is THE known failure mode of a printed fin.
    # The bending model puts the same fin at tab_sf ~0.4 while its BLADE sits at
    # ~3.6, i.e. the tab is roughly an order of magnitude more critical. That
    # ordering — not the absolute number — is the calibration claim here.
    # (Commercial fins survive because they are glass/carbon at 200-400 MPa, not
    # printed pet-cf at 109; at 112 MPa tab stress a composite fin is SF ~2-3.)
    from fingen.flex import flex_report
    from fingen.optimize import _P_DESIGN_RAD_S
    fin = FinParams(outline=OutlineParams(depth=115.0, base=110.0),
                    foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.09),
                    tabs=TabParams(system=TabSystem.DUAL_TAB))
    sheet = anchor(75.0, Skill.INTERMEDIATE, 6.4, FinConfig.THRUSTER, "pet-cf")
    flex = flex_report(fin, sheet.force_peak_n, 6.4, material="pet-cf",
                       p_design_rad_s=_P_DESIGN_RAD_S[Skill.INTERMEDIATE])
    tab_sf = sheet.allow_mpa / tab_neck_stress_mpa(
        fin, flex.root_moment_roll_nm, flex.root_shear_roll_n)
    assert tab_sf < 1.0                        # the tab is the critical section
    assert flex.stress_margin_roll > 3.0       # while the blade is comfortable
    assert flex.stress_margin_roll / tab_sf > 5.0   # by nearly an order of magnitude
