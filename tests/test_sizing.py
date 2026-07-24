"""The anchor: absolute requirements and the optimizer's hard gate."""

import pytest

from fingen.params import FinParams, FoilParams, OutlineParams, TabSystem
from fingen.sizing import Skill, anchor, base_bending_stress_mpa, check_anchor


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
