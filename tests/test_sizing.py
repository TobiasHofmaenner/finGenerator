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


def test_tab_neck_stress_dual_pins_kt_and_depth_couple():
    # CORRECTED reaction model (bundle-2 physics pass). The root SIDE-BENDING
    # moment (about the chordwise axis) is reacted PER TAB as a bearing couple
    # over the INSERTION DEPTH (14 mm), NOT over the chordwise tab SPACING — the
    # old 53 mm pitch lever reacted a *yaw* couple against a side-bending moment
    # (wrong free-body, ~3.8× optimistic). Triangular bearing ⇒ effective lever
    # (2/3)·depth; the moment splits equally over the two equal tabs; the shear
    # splits over the two tabs; the fillet factor KT_TAB (2.5) amplifies it.
    # FLAT_INSIDE fin, t/c 0.10, base 110 mm ⇒ base thickness 11.0 mm; two 20 mm
    # necks; per-tab insertion depth 14 mm.
    m_nm, v_n = 12.0, 220.0  # combined-case root moment (N·m) and shear (N)
    fin = FinParams(outline=OutlineParams(base=110.0),
                    foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.10),
                    tabs=TabParams(system=TabSystem.DUAL_TAB))
    assert KT_TAB == 2.5  # independent-literal pin on the calibration constant
    t_base = 0.10 * 110.0 * 1e-3          # 0.011 m
    area = (20.0 * 1e-3) * t_base         # neck length × base thickness, m²
    lever = (2.0 / 3.0) * 14.0 * 1e-3     # triangular-bearing lever over the depth
    r_couple = (m_nm / 2.0) / lever       # moment shared over the two tabs
    r_shear = v_n / 2.0                   # shear split over the two tabs
    expected = 2.5 * (r_couple + r_shear) / area / 1e6
    assert expected == pytest.approx(8.5551948, rel=1e-6)   # hand-computed literal
    assert tab_neck_stress_mpa(fin, m_nm, v_n) == pytest.approx(expected, rel=1e-9)
    # Mutation guard "revert the lever to the 53 mm chordwise spacing" (the
    # original bug): reacting a side-bending moment as a chordwise yaw couple
    # gives a materially lower stress the literal pin above rejects.
    wrong = 2.5 * (m_nm / (53.0 * 1e-3) + r_shear) / area / 1e6
    assert tab_neck_stress_mpa(fin, m_nm, v_n) != pytest.approx(wrong, rel=1e-2)
    assert wrong < 0.6 * expected
    # (Mutation guard "KT_TAB dropped" is covered: `expected` carries the literal
    # 2.5, so a KT_TAB of 1.0 makes the module return expected/2.5 ≠ expected.)


def test_tab_neck_stress_click_asymmetric_necks_shortest_governs():
    # Finding 3: CLICK's asymmetric necks (45 + 33 mm) must let the SHORTEST
    # (33 mm) neck govern through the worst-tab max(). Pins the geometry row AND
    # the max (not min) selection: with an equal per-tab couple+shear reaction,
    # the smaller neck area carries the higher stress. base 100 mm, t/c 0.08 ⇒
    # base thickness 8.0 mm; insertion depth 14 mm.
    m_nm, v_n = 15.0, 180.0
    fin = FinParams(outline=OutlineParams(base=100.0),
                    foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.08),
                    tabs=TabParams(system=TabSystem.CLICK_TAB))
    t_base = 0.08 * 100.0 * 1e-3          # 0.008 m
    lever = (2.0 / 3.0) * 14.0 * 1e-3
    r_couple = (m_nm / 2.0) / lever
    r_shear = v_n / 2.0
    s45 = 2.5 * (r_couple + r_shear) / ((45.0 * 1e-3) * t_base) / 1e6
    s33 = 2.5 * (r_couple + r_shear) / ((33.0 * 1e-3) * t_base) / 1e6
    assert s33 > s45                                       # shorter neck ⇒ higher stress
    assert s33 == pytest.approx(8.4618506, rel=1e-6)      # hand literal (33 mm governs)
    got = tab_neck_stress_mpa(fin, m_nm, v_n)
    assert got == pytest.approx(s33, rel=1e-9)            # max() picks the 33 mm neck
    # A max→min selection flip (or a corrupted CLICK geometry row) would return
    # the 45 mm-neck stress instead — a different, lower value this pin rejects.
    assert got != pytest.approx(s45, rel=1e-3)


def test_tab_neck_stress_single_tracks_base_length_and_clamps():
    # Finding 3: SINGLE_TAB carries one neck whose chordwise length = min(base −
    # 12, 110) mm; the side-bending moment reacts over the Futures 3/4" box depth
    # (17.5 mm) with n_tabs = 1 (no split, no shear division). base 120 ⇒ length
    # 108 mm; symmetric fin, t/c 0.09 ⇒ base thickness 10.8 mm.
    m_nm, v_n = 20.0, 150.0
    fin = FinParams(outline=OutlineParams(base=120.0),
                    foil=FoilParams(family=FoilFamily.SYMMETRIC, thickness_ratio=0.09),
                    tabs=TabParams(system=TabSystem.SINGLE_TAB))
    length_mm = min(120.0 - 12.0, 110.0)                  # 108
    assert length_mm == 108.0
    t_base = 0.09 * 120.0 * 1e-3                           # 0.0108 m
    lever = (2.0 / 3.0) * 17.5 * 1e-3                      # single-tab box depth
    area = (length_mm * 1e-3) * t_base
    expected = 2.5 * (m_nm / lever + v_n) / area / 1e6     # one tab: no split
    assert expected == pytest.approx(3.9958113, rel=1e-6)
    assert tab_neck_stress_mpa(fin, m_nm, v_n) == pytest.approx(expected, rel=1e-9)
    # The length clamps at 110 mm for a very wide base (min(base − 12, 110)).
    wide = FinParams(outline=OutlineParams(base=250.0),
                     foil=FoilParams(family=FoilFamily.SYMMETRIC, thickness_ratio=0.09),
                     tabs=TabParams(system=TabSystem.SINGLE_TAB))
    t_base_w = 0.09 * 250.0 * 1e-3
    area_w = (110.0 * 1e-3) * t_base_w
    exp_w = 2.5 * (m_nm / lever + v_n) / area_w / 1e6
    assert tab_neck_stress_mpa(wide, m_nm, v_n) == pytest.approx(exp_w, rel=1e-9)


def test_tab_gate_sanity_anchor_commercial_dual_fin():
    # CALIBRATION ANCHOR (Finding 1). A commercial-like dual-tab side fin
    # (115 mm depth × 110 mm base, t/c 0.09, pet-cf) at the 75 kg intermediate
    # working load must clear the tab gate with healthy margin — production
    # FCS-style fins at that load do not routinely snap tabs. The corrected
    # couple-over-depth model returns tab_sf ≈ 3.0 here (NOT ≪ 1), so the model
    # is well-calibrated at the reality anchor and the gate keeps the standard
    # SF ≥ 1 threshold the blade-bending gate uses — no tier-0 confidence-factor
    # relaxation needed (it would have been documented here otherwise). The gate
    # still DISCRIMINATES: a thin t/c-0.05 dual under a heavy pro drops below 1.
    from fingen.flex import flex_report
    from fingen.optimize import _P_DESIGN_RAD_S
    fin = FinParams(outline=OutlineParams(depth=115.0, base=110.0),
                    foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.09),
                    tabs=TabParams(system=TabSystem.DUAL_TAB))
    sheet = anchor(75.0, Skill.INTERMEDIATE, 6.4, FinConfig.THRUSTER, "pet-cf")
    flex = flex_report(fin, sheet.force_peak_n, 6.4, material="pet-cf",
                       p_design_rad_s=_P_DESIGN_RAD_S[Skill.INTERMEDIATE])
    stress = tab_neck_stress_mpa(fin, flex.root_moment_roll_nm, flex.root_shear_roll_n)
    tab_sf = sheet.allow_mpa / stress
    assert tab_sf == pytest.approx(3.002, rel=2e-3)  # comfortably above the SF≥1 gate
    assert tab_sf > 2.5
