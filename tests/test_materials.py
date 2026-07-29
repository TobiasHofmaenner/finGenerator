"""Material-card registry, measured-card intake, and flex wiring.

Fast tests only. The measured-card round-trip goes through the REAL
scripts/bench_intake.py serializer (a synthetic staircase sweep + fin), so the
loader is checked against the exact schema bench_intake writes — not a
hand-rolled stand-in. A second hand-written card exercises the schema minimally
and the error paths.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from fingen.flex import flex_report
from fingen.materials import (
    CARDS,
    MaterialCard,
    get_card,
    load_measured_card,
    register_card,
)
from fingen.params import FinParams, FoilFamily, FoilParams

# Load bench_intake the way test_bench_intake does (it lives in scripts/, not
# on the package path) so the round-trip uses its real card serializer.
_SPEC = importlib.util.spec_from_file_location(
    "bench_intake", Path(__file__).resolve().parents[1] / "scripts" / "bench_intake.py")
bench_intake = importlib.util.module_from_spec(_SPEC)
sys.modules["bench_intake"] = bench_intake
_SPEC.loader.exec_module(bench_intake)

LEAD, USTEPS, SPR = 4.0, 16.0, 200.0
STEP_MM = LEAD / (USTEPS * SPR)


@pytest.fixture(autouse=True)
def _restore_registry():
    """Snapshot/restore CARDS so shadowing tests don't leak into others."""
    saved = dict(CARDS)
    try:
        yield
    finally:
        CARDS.clear()
        CARDS.update(saved)


# --------------------------------------------------------------------------- #
# registry lookup + error path
# --------------------------------------------------------------------------- #
def test_registry_lookup_and_error():
    pet = get_card("pet-cf")
    # The pet-cf default is the user's actual filament, Fiberon PET-CF17.
    assert pet.name == "fiberon-pet-cf17"
    assert pet.provenance == "datasheet"
    assert pet.e_mpa == pytest.approx(4744.4)     # ISO 178 bending modulus X-Y
    assert pet.e_z_mpa == pytest.approx(2768.2)   # < e_mpa: layers weaker in Z
    assert pet.e_z_mpa < pet.e_mpa
    assert pet.strength_xy_mpa == pytest.approx(109.3)
    assert pet.density_kg_m3 == pytest.approx(1340.0)
    assert pet.annealed is True
    # get_card("pet-cf") and the explicit product name resolve to one card.
    assert get_card("fiberon-pet-cf17") is pet
    # Bambu PET-CF is retained as a separate comparison entry.
    assert get_card("bambu-pet-cf").e_mpa == pytest.approx(5320.0)

    with pytest.raises(KeyError) as exc:
        get_card("unobtainium")
    # Clean error lists what is available.
    assert "unobtainium" in str(exc.value)
    assert "pet-cf" in str(exc.value)


def test_all_datasheet_cards_are_datasheet_provenance():
    for name in ("pet-cf", "fiberon-pet-cf17", "bambu-pet-cf", "bambu-paht-cf", "pla"):
        assert get_card(name).provenance == "datasheet"


def test_approximated_paht_card():
    # The user's paht-cf is Elegoo PAHT-CF (PA12-CF), an APPROXIMATED card.
    paht = get_card("paht-cf")
    assert paht.provenance == "approximated"
    assert paht.annealed is False               # Elegoo states no anneal
    # Default e_mpa is the CONDITIONED (wet) modulus, below the dry reference.
    assert paht.e_mpa_dry is not None
    assert paht.e_mpa < paht.e_mpa_dry
    assert paht.e_mpa == pytest.approx(paht.e_mpa_dry * 0.85, rel=1e-3)
    assert paht.e_mpa_dry == pytest.approx(5089.0)   # Elegoo published dry X-Y
    # Derivation documents what is Elegoo's vs analog-derived, with uncertainty.
    assert paht.derivation
    assert "ELEGOO" in paht.derivation.upper()
    assert "analog" in paht.derivation.lower()
    # The Bambu analog behind the approximation is a separate comparison card.
    assert get_card("bambu-paht-cf").provenance == "datasheet"
    assert get_card("bambu-paht-cf").e_mpa == pytest.approx(4230.0)


# --------------------------------------------------------------------------- #
# sizing / materials cross-check
# --------------------------------------------------------------------------- #
def test_sizing_allowable_derives_from_card_strength():
    from fingen.sizing import _MATERIAL_ALLOW_MPA, PRINT_KNOCKDOWN_INPLANE, STRUCTURAL_SF

    # The allowable is the card's XY bending strength times the IN-PLANE
    # as-printed knockdown, over the structural SF. In-plane — not the old
    # blanket 0.5 — because the exporter prints the blade FLAT, so its bending
    # tension runs within the layer planes; 0.5 was effectively the material's
    # own Z/XY ratio and double-counted anisotropy on a part oriented to avoid it.
    assert _MATERIAL_ALLOW_MPA["pet-cf"] == pytest.approx(
        get_card("pet-cf").strength_xy_mpa * PRINT_KNOCKDOWN_INPLANE / STRUCTURAL_SF)
    # paht-cf runs on the Elegoo strength wet-derated (x0.85) through that chain.
    conditioned = (get_card("paht-cf").strength_xy_mpa * 0.85
                   * PRINT_KNOCKDOWN_INPLANE / STRUCTURAL_SF)
    assert _MATERIAL_ALLOW_MPA["paht-cf"] == pytest.approx(conditioned, rel=1e-3)
    # The in-plane knockdown must stay well ABOVE the through-layer one, or the
    # flat-print decision has been silently thrown away.
    from fingen.sizing import PRINT_KNOCKDOWN_INTERLAMINAR
    assert PRINT_KNOCKDOWN_INPLANE > 4 * PRINT_KNOCKDOWN_INTERLAMINAR


# --------------------------------------------------------------------------- #
# measured-card JSON round-trip (real bench_intake schema)
# --------------------------------------------------------------------------- #
def _staircase(k: float, d_max: float, n: int = 25):
    up = np.linspace(0.0, d_max, n)
    down = np.linspace(d_max, 0.0, n)[1:]
    disp = np.concatenate([up, down])
    return disp, k * disp


def _write_bench_csv(path: Path, disp_mm, force_n, header: dict) -> Path:
    lines = [f"# {k}: {v}" for k, v in header.items()]
    lines.append("time_s,steps,force_N")
    steps = np.round(np.asarray(disp_mm, float) / STEP_MM).astype(int)
    for i, (si, fi) in enumerate(zip(steps, np.asarray(force_n, float), strict=True)):
        lines.append(f"{float(i):.3f},{int(si)},{fi:.5f}")
    path.write_text("\n".join(lines) + "\n")
    return path


def test_measured_card_roundtrips_through_bench_intake(tmp_path):
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    station = 0.75 * fin.outline.depth
    e_true = 5200.0
    k_true = bench_intake.predicted_stiffness(fin, e_true, station)
    disp, force = _staircase(k_true, d_max=60.0 / k_true)
    header = {"fin_id": "sidefin-petcf-004", "lead_mm": LEAD, "usteps": int(USTEPS),
              "steps_per_rev": int(SPR), "backlash_mm": 0.0, "temp_C": 22.0,
              "station_mm": station, "direction": "toward_face", "material": "pet-cf"}
    csv = _write_bench_csv(tmp_path / "run.csv", disp, force, header)

    # Produce a real bench card JSON via the same code path the rig uses.
    mc = bench_intake.process(csv, fin=fin)
    card_json = tmp_path / "run.card.json"
    card_json.write_text(json.dumps(mc.card, indent=2) + "\n")
    assert mc.card["E_eff_mpa"] == pytest.approx(e_true, rel=0.02)

    measured = load_measured_card(card_json, annealed=False)
    assert isinstance(measured, MaterialCard)
    assert measured.provenance == "measured"
    assert measured.name == "pet-cf"                       # shadows the sizing slot
    assert measured.e_mpa == pytest.approx(mc.card["E_eff_mpa"])
    assert measured.annealed is False                      # as-printed bench blade
    # Strength/density/e_z are inherited from the datasheet card (the bench
    # measures stiffness, not strength).
    base = get_card("pet-cf")
    assert measured.strength_xy_mpa == pytest.approx(base.strength_xy_mpa)
    assert measured.density_kg_m3 == pytest.approx(base.density_kg_m3)
    assert measured.e_z_mpa == pytest.approx(base.e_z_mpa)
    assert "run.csv" in measured.source

    # register_card lets it shadow the datasheet default.
    register_card(measured)
    assert get_card("pet-cf") is measured
    assert get_card("pet-cf").provenance == "measured"


def test_synthetic_bench_json_and_error_paths(tmp_path):
    # Minimal hand-written card in bench_intake's schema.
    good = {"fin_id": "synthetic", "material": "paht-cf", "E_eff_mpa": 3900.0,
            "K_measured_N_per_mm": 41.2, "R2": 0.999, "station_mm": 86.25,
            "provenance": {"source_csv": "/data/synthetic.csv",
                           "model": "tier-0 flex.py point-load inversion"}}
    p = tmp_path / "good.json"
    p.write_text(json.dumps(good))
    card = load_measured_card(p)
    assert card.name == "paht-cf"
    assert card.provenance == "measured"
    assert card.e_mpa == pytest.approx(3900.0)
    assert card.annealed is get_card("paht-cf").annealed  # inherited when unstated
    # A measurement supersedes the dry-split estimate.
    assert card.e_mpa_dry is None
    assert card.derivation == ""

    # K-only card (no E inversion) is a clear error, not a silent bad card.
    no_e = dict(good, E_eff_mpa=None)
    pe = tmp_path / "no_e.json"
    pe.write_text(json.dumps(no_e))
    with pytest.raises(ValueError, match="E_eff_mpa"):
        load_measured_card(pe)

    # Unknown resin has no datasheet card to inherit from.
    unknown = dict(good, material="mystery-resin")
    pu = tmp_path / "unknown.json"
    pu.write_text(json.dumps(unknown))
    with pytest.raises(KeyError):
        load_measured_card(pu)


# --------------------------------------------------------------------------- #
# flex picks up the card E
# --------------------------------------------------------------------------- #
def test_flex_uses_card_modulus_per_material():
    fin = FinParams()
    pet = flex_report(fin, 74.0, 6.4, material="pet-cf")
    paht = flex_report(fin, 74.0, 6.4, material="paht-cf")
    # Different cards, different default modulus, different deflection.
    assert pet.tip_deflection_mm != pytest.approx(paht.tip_deflection_mm)
    # Deflection ∝ 1/E: the ratio tracks the inverse modulus ratio.
    ratio = paht.tip_deflection_mm / pet.tip_deflection_mm
    assert ratio == pytest.approx(
        get_card("pet-cf").e_mpa / get_card("paht-cf").e_mpa, rel=0.02)


def test_flex_default_follows_measured_shadow():
    fin = FinParams()
    before = flex_report(fin, 74.0, 6.4)  # default pet-cf card
    # A stiffer measured card shadowing "pet-cf" must soften the default report.
    shadow = MaterialCard(
        name="pet-cf", e_mpa=2.0 * get_card("pet-cf").e_mpa,
        e_z_mpa=2768.2, strength_xy_mpa=109.3, strength_z_mpa=43.4,
        density_kg_m3=1340.0, source="bench: test", accessed="2026-07-26",
        provenance="measured", annealed=False)
    register_card(shadow)
    after = flex_report(fin, 74.0, 6.4)
    assert after.tip_deflection_mm == pytest.approx(0.5 * before.tip_deflection_mm,
                                                    rel=1e-6)
