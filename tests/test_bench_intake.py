"""Fast tests for scripts/bench_intake.py on synthetic bench sweeps.

Three anchors the task asks for: a known stiffness round-trips through the
fit, rig-compliance subtraction returns the true fin stiffness, and the
tier-0 E inversion recovers a known modulus within 2 %. Plus a light check
that a real fingen-case.json loads and that a relaxation hold is read.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "bench_intake", Path(__file__).resolve().parents[1] / "scripts" / "bench_intake.py")
bench_intake = importlib.util.module_from_spec(_SPEC)
sys.modules["bench_intake"] = bench_intake  # dataclass annotation resolution
_SPEC.loader.exec_module(bench_intake)

from fingen.params import FinParams, FoilFamily, FoilParams  # noqa: E402

LEAD, USTEPS, SPR = 4.0, 16.0, 200.0
STEP_MM = LEAD / (USTEPS * SPR)  # 0.00125 mm / microstep


def _steps(disp_mm: np.ndarray) -> np.ndarray:
    return np.round(disp_mm / STEP_MM).astype(int)


def _write_csv(path: Path, disp_mm, force_n, *, header: dict, times=None) -> Path:
    lines = [f"# {k}: {v}" for k, v in header.items()]
    lines.append("time_s,steps,force_N")
    steps = _steps(np.asarray(disp_mm, dtype=float))
    t = np.arange(len(steps), dtype=float) if times is None else np.asarray(times)
    for ti, si, fi in zip(t, steps, np.asarray(force_n, dtype=float), strict=True):
        lines.append(f"{ti:.3f},{int(si)},{fi:.5f}")
    path.write_text("\n".join(lines) + "\n")
    return path


def _base_header(**extra) -> dict:
    h = {"fin_id": "synthetic", "lead_mm": LEAD, "usteps": int(USTEPS),
         "steps_per_rev": int(SPR), "spool": "NA", "backlash_mm": 0.0,
         "temp_C": 22.0, "station_mm": 86.25, "direction": "toward_face"}
    h.update(extra)
    return h


def _staircase(k_n_per_mm: float, d_max: float = 1.2, n: int = 25):
    """Loading then unloading ramp of an ideal linear spring, force = K·disp."""
    up = np.linspace(0.0, d_max, n)
    down = np.linspace(d_max, 0.0, n)[1:]
    disp = np.concatenate([up, down])
    return disp, k_n_per_mm * disp


def test_known_k_roundtrips(tmp_path):
    k_true = 42.5
    disp, force = _staircase(k_true)
    csv = _write_csv(tmp_path / "a.csv", disp, force, header=_base_header())
    mc = bench_intake.process(csv)
    assert mc.card["K_measured_N_per_mm"] == pytest.approx(k_true, rel=0.01)
    assert mc.card["R2"] > 0.999
    # loading and unloading trace the same line -> negligible hysteresis loop
    assert mc.card["hysteresis_area_mJ"] < 1e-3


def test_compliance_subtraction_correct(tmp_path):
    k_fin, k_rig = 40.0, 220.0  # fin in series with a stiffer rig spring
    d_fin = np.concatenate([np.linspace(0, 1.0, 30), np.linspace(1.0, 0, 30)[1:]])
    force = k_fin * d_fin
    stage = d_fin + force / k_rig  # what the screw actually travels

    cf = np.linspace(0.0, 80.0, 9)
    comp = tmp_path / "compliance.csv"
    comp.write_text("force_N,disp_mm\n"
                    + "\n".join(f"{f:.4f},{f / k_rig:.6f}" for f in cf) + "\n")

    csv = _write_csv(tmp_path / "b.csv", stage, force,
                     header=_base_header(compliance_file="compliance.csv"))
    mc = bench_intake.process(csv)
    # Without subtraction the apparent stiffness would be the series
    # combination k_fin·k_rig/(k_fin+k_rig) ≈ 33.8 N/mm; the correction must
    # recover the fin's own 40 N/mm.
    assert mc.card["K_measured_N_per_mm"] == pytest.approx(k_fin, rel=0.01)


def test_e_inversion_recovers_modulus(tmp_path):
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    station = 0.75 * fin.outline.depth
    e_true = 5200.0
    k_true = bench_intake.predicted_stiffness(fin, e_true, station)

    d_max = 60.0 / k_true  # sweep to ~60 N
    disp, force = _staircase(k_true, d_max=d_max)
    csv = _write_csv(tmp_path / "c.csv", disp, force,
                     header=_base_header(station_mm=station))
    mc = bench_intake.process(csv, fin=fin)
    assert mc.card["E_eff_mpa"] == pytest.approx(e_true, rel=0.02)


def test_backlash_and_relaxation(tmp_path):
    # A hold at constant displacement with an exponential force decay must be
    # read back as a time constant near the injected tau; backlash on the
    # return branch must not corrupt the loading-branch fit.
    k = 35.0
    up = np.linspace(0.0, 1.0, 20)
    tau = 20.0
    thold = np.linspace(0.0, 80.0, 40)
    hold_force = 30.0 + 5.0 * np.exp(-thold / tau)
    down = np.linspace(1.0, 0.0, 20)[1:]
    disp = np.concatenate([up, np.full_like(thold, 1.0), down])
    force = np.concatenate([k * up, hold_force, k * down])
    t = np.arange(len(disp), dtype=float)
    t[len(up):len(up) + len(thold)] = len(up) + thold  # real seconds in the hold

    csv = _write_csv(tmp_path / "d.csv", disp, force,
                     header=_base_header(backlash_mm=0.04), times=t)
    mc = bench_intake.process(csv)
    assert mc.card["K_measured_N_per_mm"] == pytest.approx(k, rel=0.05)
    assert any(abs(x - tau) < 0.2 * tau for x in mc.card["relaxation_tau_s"])


def test_load_fin_params_from_case_json():
    case = (Path(__file__).resolve().parents[1]
            / "bench" / "urans-bw04" / "a16.0" / "fingen-case.json")
    fin = bench_intake.load_fin_params(case)
    assert fin.foil.family is FoilFamily.FLAT_INSIDE
    assert fin.outline.depth == pytest.approx(120.0)
