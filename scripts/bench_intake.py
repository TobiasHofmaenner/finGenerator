"""Physical stiffness-bench intake — CSV in, material card + QC plot out.

The load-cell rig (docs/BENCH-PROTOCOL.md) pushes a clamped blade with a
known force at a known spanwise station and logs (time, steps, force). This
script turns one such sweep into the number tier-0 flex is missing: the
effective printed modulus `E_eff`, the anchor that replaces flex.py's
`E_PLACEHOLDER_MPA = 7000 MPa` placeholder.

Pipeline:
  1. parse the header block + rows;
  2. steps -> displacement mm  (steps · lead / (steps_per_rev · microstep));
  3. subtract rig series compliance (interpolated from the rigid-post CSV
     named in the header) and close the ball-nut backlash dead-band;
  4. fit the linear stiffness K (N/mm) with R^2 over the loading branch;
  5. hysteresis loop area (dissipation) + relaxation time constants on any
     constant-displacement holds;
  6. with --fin-json, invert the SAME tier-0 beam flex.py uses — driven by
     the bench's point load at the contact station instead of the
     distributed hydro load — for the E that reproduces the measured K.

Outputs `<csv>.card.json` (material card + provenance) and `<csv>.qc.png`
(dark-style force-vs-displacement, both branches, fit line, residuals).

Usage:
  uv run python scripts/bench_intake.py <csv> [--fin-json <fingen-case.json>]
      [--material pet-cf|paht-cf] [--out <card.json>] [--plot <png>]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.optimize import brentq, curve_fit

from fingen.flex import (
    _N_FOIL_POINTS,
    _N_STATIONS,
    E_PLACEHOLDER_MPA,
    flex_solve,
)
from fingen.foil import section_points
from fingen.hydro import lift_curve_slope
from fingen.loft import _groove_thins, _thickness_at, groove_station_z
from fingen.outline import chord_schedule
from fingen.params import (
    FinParams,
    FoilFamily,
    FoilParams,
    GenSettings,
    GrooveParams,
    GrooveSurface,
    OutlineParams,
)
from fingen.sizing import _MATERIAL_ALLOW_MPA

# Loading-branch fit window as a fraction of peak force: the toe below f_lo
# is contact seating (tip bedding into the foil), the shoulder above f_hi is
# where a soft blade starts to roll off the linear line. The stiffness lives
# in the middle.
_FIT_LO, _FIT_HI = 0.15, 0.85
# A hold = a run of samples whose displacement varies by less than this (mm)
# over at least _HOLD_MIN_S seconds — the relaxation segments of Test C.
_HOLD_BAND_MM = 0.01
_HOLD_MIN_S = 15.0


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #
@dataclass
class BenchRun:
    """One parsed bench sweep: header metadata + the raw (t, steps, F) rows."""

    header: dict[str, str]
    time_s: np.ndarray
    steps: np.ndarray
    force_n: np.ndarray
    source: Path

    def h_float(self, key: str, default: float | None = None) -> float:
        if key not in self.header:
            if default is None:
                raise KeyError(f"{self.source.name}: missing required header '{key}'")
            return default
        return float(self.header[key])


def parse_bench_csv(path: str | Path) -> BenchRun:
    """Header lines are `# key: value`; the first non-# line is the column
    header (time_s,steps,force_N in any order), the rest are data rows."""
    path = Path(path)
    header: dict[str, str] = {}
    cols: list[str] | None = None
    rows: list[list[float]] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            body = line.lstrip("#").strip()
            # strip inline comments (`value   # note`) from the value side
            if ":" in body:
                key, val = body.split(":", 1)
                header[key.strip()] = val.split("#", 1)[0].strip()
            continue
        if cols is None:
            cols = [c.strip() for c in line.split(",")]
            continue
        rows.append([float(v) for v in line.split(",")])
    if cols is None or not rows:
        raise ValueError(f"{path.name}: no data rows found")
    table = np.asarray(rows, dtype=float)
    idx = {name: cols.index(name) for name in ("time_s", "steps", "force_N")}
    return BenchRun(header=header, time_s=table[:, idx["time_s"]],
                    steps=table[:, idx["steps"]], force_n=table[:, idx["force_N"]],
                    source=path)


def load_compliance(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Rigid-post calibration CSV -> (force_N, disp_mm), sorted by force."""
    path = Path(path)
    cols: list[str] | None = None
    rows: list[list[float]] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if cols is None:
            cols = [c.strip() for c in line.split(",")]
            continue
        rows.append([float(v) for v in line.split(",")])
    if cols is None or not rows:
        raise ValueError(f"{path.name}: no compliance rows")
    table = np.asarray(rows, dtype=float)
    f = table[:, cols.index("force_N")]
    d = table[:, cols.index("disp_mm")]
    order = np.argsort(f)
    return f[order], d[order]


# --------------------------------------------------------------------------- #
# corrections + fits
# --------------------------------------------------------------------------- #
def steps_to_mm(steps: np.ndarray, lead_mm: float, usteps: float,
                steps_per_rev: float) -> np.ndarray:
    """Commanded stage travel from the step count."""
    return steps * lead_mm / (steps_per_rev * usteps)


@dataclass
class Corrected:
    """Displacement after compliance + backlash removal, split into branches."""

    disp_mm: np.ndarray  # fin displacement, rig compliance removed
    stage_mm: np.ndarray  # commanded actuator travel (constant during a hold)
    force_n: np.ndarray  # magnitude (both push directions come out positive)
    time_s: np.ndarray
    peak_idx: int  # last sample of the loading branch
    load_mask: np.ndarray  # loading-branch selector


def correct(run: BenchRun) -> Corrected:
    """Convert steps->mm, remove series compliance and the backlash dead-band.

    Backlash: at the reversal the ball nut crosses its dead-band before the
    tip re-engages, so the returning (unloading) branch is offset by
    `backlash_mm` in commanded travel. Adding it back overlays the two
    branches at zero force, exactly as the load-free reversal measured it.
    Rig compliance is a series spring: at any force the frame + cell have
    stretched `disp_rig(force)`, which is subtracted at the matching force.
    """
    lead = run.h_float("lead_mm")
    usteps = run.h_float("usteps")
    spr = run.h_float("steps_per_rev")
    backlash = run.h_float("backlash_mm", 0.0)

    stage = steps_to_mm(run.steps, lead, usteps, spr)
    force = np.abs(run.force_n)
    stage = np.abs(stage - stage[0])  # zero the origin, sign-agnostic

    peak_idx = int(np.argmax(stage))
    load_mask = np.zeros(stage.shape, dtype=bool)
    load_mask[: peak_idx + 1] = True
    stage = stage.copy()
    stage[~load_mask] += backlash  # close the dead-band on the return branch

    comp_file = run.header.get("compliance_file")
    if comp_file:
        cpath = (run.source.parent / comp_file)
        cf, cd = load_compliance(cpath)
        disp_rig = np.interp(force, cf, cd)
        disp = stage - disp_rig
    else:
        disp = stage
    return Corrected(disp_mm=disp, stage_mm=stage, force_n=force,
                     time_s=run.time_s, peak_idx=peak_idx, load_mask=load_mask)


def fit_stiffness(disp_mm: np.ndarray, force_n: np.ndarray,
                  mask: np.ndarray) -> tuple[float, float, float]:
    """Linear K (N/mm), intercept (N), R^2 over the central loading band."""
    d, f = disp_mm[mask], force_n[mask]
    peak = float(f.max())
    window = (f >= _FIT_LO * peak) & (f <= _FIT_HI * peak)
    if window.sum() < 3:
        window = np.ones(f.shape, dtype=bool)
    d, f = d[window], f[window]
    slope, intercept = np.polyfit(d, f, 1)
    pred = slope * d + intercept
    ss_res = float(np.sum((f - pred) ** 2))
    ss_tot = float(np.sum((f - f.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(slope), float(intercept), r2


def hysteresis_area(disp_mm: np.ndarray, force_n: np.ndarray,
                    peak_idx: int) -> float:
    """Enclosed loading/unloading loop area (mJ = N·mm), shoelace on the
    ordered loop — the energy dissipated per cycle."""
    if peak_idx >= len(disp_mm) - 1:
        return 0.0  # no return branch recorded
    x = disp_mm
    y = force_n
    area = 0.0
    n = len(x)
    for i in range(n):
        j = (i + 1) % n
        area += x[i] * y[j] - x[j] * y[i]
    return abs(area) * 0.5


def _hold_segments(corr: Corrected) -> list[tuple[int, int]]:
    """Index ranges where the actuator is held (Test C relaxation windows).

    Keyed on the commanded stage position, not the compliance-corrected
    displacement: during a load-relaxation hold the stage is fixed but the
    fin creeps forward as the decaying force lets the rig spring recover
    (disp_mm drifts by ΔF/K_rig), which would otherwise split one hold.
    """
    segments: list[tuple[int, int]] = []
    i = 0
    n = len(corr.stage_mm)
    while i < n:
        j = i
        while (j + 1 < n
               and abs(corr.stage_mm[j + 1] - corr.stage_mm[i]) <= _HOLD_BAND_MM):
            j += 1
        if j > i and corr.time_s[j] - corr.time_s[i] >= _HOLD_MIN_S:
            segments.append((i, j))
            i = j + 1
        else:
            i += 1
    return segments


def relaxation_taus(corr: Corrected) -> list[float]:
    """Fit F(t)=F_inf + A·exp(-t/tau) on each hold; return the taus (s)."""
    taus: list[float] = []
    for i, j in _hold_segments(corr):
        t = corr.time_s[i : j + 1] - corr.time_s[i]
        f = corr.force_n[i : j + 1]
        span = float(f[0] - f[-1])
        if abs(span) < 1e-6:
            continue

        def model(tt, f_inf, amp, tau):
            return f_inf + amp * np.exp(-tt / tau)

        try:
            p0 = (float(f[-1]), span, max(t[-1] / 3.0, 1.0))
            popt, _ = curve_fit(model, t, f, p0=p0, maxfev=10000)
        except (RuntimeError, ValueError):
            continue
        tau = float(popt[2])
        if 0.0 < tau < 10.0 * (t[-1] + 1.0):
            taus.append(tau)
    return taus


# --------------------------------------------------------------------------- #
# tier-0 inversion (E from measured K)
# --------------------------------------------------------------------------- #
def _fin_stations(fin: FinParams, station_mm: float):
    settings = GenSettings(n_stations=_N_STATIONS, n_foil_points=_N_FOIL_POINTS)
    extra = list(groove_station_z(fin)) + [float(station_mm)]
    stations = chord_schedule(fin.outline, settings,
                              tip_chord_min=settings.cap_chord, extra_z=extra)
    z = np.array([st.z for st in stations])
    chord = np.array([st.chord for st in stations])
    x_le = np.array([st.x_le for st in stations])
    sections = []
    for st in stations:
        thin_outer, thin_inner = _groove_thins(fin, st.z, st.chord)
        sections.append(section_points(fin.foil, st.chord,
                                       thickness_ratio=_thickness_at(fin, st.z),
                                       n_points=settings.n_foil_points,
                                       thin_outer=thin_outer, thin_inner=thin_inner))
    zc = int(np.argmin(np.abs(z - station_mm)))
    band = None
    if fin.grooves.count:
        g = fin.grooves
        z0 = g.span_start * fin.outline.depth - 0.5 * g.width
        band = (z0, z0 + (g.count - 1) * g.pitch + g.width)
    return z, chord, x_le, sections, zc, band


def predicted_stiffness(fin: FinParams, e_mpa: float, station_mm: float,
                        material: str = "pet-cf", force_n: float = 50.0) -> float:
    """Tier-0 point-load stiffness (N/mm) at the contact station.

    The bench applies a point load at `station_mm` and reads displacement
    there; this drives flex.py's own beam with that point load (a unit hat at
    the contact node, flex_solve normalizes it to force_n) and returns
    force_n / deflection. Bending deflection is exactly linear in 1/E, so any
    force_n cancels and the inversion is well-posed.
    """
    z, chord, x_le, sections, zc, band = _fin_stations(fin, station_mm)
    slope, _ = lift_curve_slope(fin)

    def point_load(zq: np.ndarray) -> np.ndarray:
        hat = np.zeros_like(zq)
        hat[zc] = 1.0
        return hat

    rep = flex_solve(z, chord, x_le, sections, e_mpa, force_n, 6.4, slope,
                     load=point_load, allow_mpa=_MATERIAL_ALLOW_MPA[material],
                     groove_band_mm=band)
    return force_n / float(rep.deflection_mm[zc])


def invert_modulus(fin: FinParams, k_measured: float, station_mm: float,
                   material: str = "pet-cf") -> float:
    """E (MPa) whose tier-0 point-load stiffness matches the measured K."""

    def residual(e_mpa: float) -> float:
        return predicted_stiffness(fin, e_mpa, station_mm, material) - k_measured

    return float(brentq(residual, 100.0, 60000.0, xtol=1e-3, rtol=1e-8))


# --------------------------------------------------------------------------- #
# fin-params JSON loader
# --------------------------------------------------------------------------- #
def _sub(cls, data: dict | None, drop: tuple[str, ...] = ()):
    """Build a frozen params dataclass from a JSON sub-dict, ignoring
    non-field keys (fingen-case.json carries speed/leeway_deg too)."""
    if data is None:
        return cls()
    fields = {f for f in cls.__dataclass_fields__ if f not in drop}
    kwargs = {k: v for k, v in data.items() if k in fields}
    return cls(**kwargs)


def load_fin_params(source: str | Path | dict) -> FinParams:
    """FinParams from a fingen-case.json-style dict or file (enums by value)."""
    data = source if isinstance(source, dict) else json.loads(Path(source).read_text())
    outline = _sub(OutlineParams, data.get("outline"))
    foil_d = dict(data.get("foil") or {})
    if "family" in foil_d:
        foil_d["family"] = FoilFamily(foil_d["family"])
    foil = _sub(FoilParams, foil_d)
    grv_d = dict(data.get("grooves") or {})
    if "surface" in grv_d:
        grv_d["surface"] = GrooveSurface(grv_d["surface"])
    grooves = _sub(GrooveParams, grv_d)
    kwargs = {"outline": outline, "foil": foil, "grooves": grooves}
    if "thickness_tip_factor" in data:
        kwargs["thickness_tip_factor"] = data["thickness_tip_factor"]
    return FinParams(**kwargs)


# --------------------------------------------------------------------------- #
# processing + card
# --------------------------------------------------------------------------- #
@dataclass
class MaterialCard:
    card: dict = field(default_factory=dict)
    corr: Corrected | None = None
    fit: tuple[float, float, float] = (0.0, 0.0, 0.0)


def process(csv_path: str | Path, fin: FinParams | None = None,
            material: str | None = None) -> MaterialCard:
    """Full intake of one sweep -> material card (+ the corrected series)."""
    run = parse_bench_csv(csv_path)
    corr = correct(run)
    k_meas, intercept, r2 = fit_stiffness(corr.disp_mm, corr.force_n, corr.load_mask)
    material = material or run.header.get("material", "pet-cf")
    station_mm = run.h_float("station_mm", float("nan"))

    card: dict = {
        "fin_id": run.header.get("fin_id", run.source.stem),
        "K_measured_N_per_mm": round(k_meas, 4),
        "R2": round(r2, 5),
        "fit_intercept_N": round(intercept, 4),
        "hysteresis_area_mJ": round(
            hysteresis_area(corr.disp_mm, corr.force_n, corr.peak_idx), 4),
        "relaxation_tau_s": [round(t, 3) for t in relaxation_taus(corr)],
        "temp_C": run.h_float("temp_C", float("nan")),
        "station_mm": station_mm,
        "direction": run.header.get("direction", "unknown"),
        "material": material,
        "E_eff_mpa": None,
        "provenance": {
            "source_csv": str(Path(csv_path).resolve()),
            "lead_mm": run.h_float("lead_mm"),
            "usteps": run.h_float("usteps"),
            "steps_per_rev": run.h_float("steps_per_rev"),
            "backlash_mm": run.h_float("backlash_mm", 0.0),
            "compliance_file": run.header.get("compliance_file"),
            "fin_params": run.header.get("fin_params") or run.header.get("step_ref"),
            "n_samples": int(len(run.steps)),
            "e_placeholder_mpa": E_PLACEHOLDER_MPA,
            "model": "tier-0 flex.py point-load inversion",
        },
    }
    if fin is not None:
        e_eff = invert_modulus(fin, k_meas, station_mm, material)
        card["E_eff_mpa"] = round(e_eff, 1)
        card["provenance"]["e_ratio_vs_placeholder"] = round(e_eff / E_PLACEHOLDER_MPA, 3)
    return MaterialCard(card=card, corr=corr, fit=(k_meas, intercept, r2))


# --------------------------------------------------------------------------- #
# QC plot (dark style, matching femviz)
# --------------------------------------------------------------------------- #
_BG = "#0b0e11"
_TEXT = "#e8e8e8"
_MUTED = "#8f8f8f"
_GRID = (1.0, 1.0, 1.0, 0.14)
_CYAN = "#7fd4e0"
_ORANGE = "#f2a154"
_LOAD = "#e58b8b"


def make_qc_plot(mc: MaterialCard, out_png: str | Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    corr = mc.corr
    k, intercept, r2 = mc.fit
    load = corr.load_mask
    unload = ~load
    fig, (ax, rx) = plt.subplots(
        2, 1, figsize=(7.2, 7.6), facecolor=_BG, height_ratios=[3, 1],
        layout="constrained")

    ax.set_facecolor(_BG)
    ax.plot(corr.disp_mm[load], corr.force_n[load], "o-", ms=3, lw=1.0,
            color=_CYAN, label="loading")
    if unload.any():
        ax.plot(corr.disp_mm[unload], corr.force_n[unload], "o-", ms=3, lw=1.0,
                color=_ORANGE, label="unloading")
    dline = np.array([corr.disp_mm[load].min(), corr.disp_mm[load].max()])
    ax.plot(dline, k * dline + intercept, "--", lw=1.4, color=_LOAD,
            label=f"fit K = {k:.2f} N/mm  (R² {r2:.4f})")
    card = mc.card
    txt = f"{card['fin_id']}  ·  station {card['station_mm']:.1f} mm  ·  {card['direction']}"
    if card["E_eff_mpa"] is not None:
        txt += f"\nE_eff = {card['E_eff_mpa']:.0f} MPa  (placeholder {E_PLACEHOLDER_MPA:.0f})"
    ax.set_title(txt, color=_TEXT, fontsize=10, loc="left")
    ax.set_ylabel("force [N]", color=_MUTED)

    # residuals of the fit over the loading branch
    d, f = corr.disp_mm[load], corr.force_n[load]
    rx.set_facecolor(_BG)
    rx.axhline(0.0, color=_MUTED, lw=0.8)
    rx.plot(d, f - (k * d + intercept), "o", ms=3, color=_CYAN)
    rx.set_ylabel("resid [N]", color=_MUTED)
    rx.set_xlabel("fin displacement [mm]  (rig compliance + backlash removed)",
                  color=_MUTED)

    for a in (ax, rx):
        for spine in a.spines.values():
            spine.set_color(_GRID)
        a.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
        a.tick_params(colors=_MUTED, labelsize=8)
    ax.legend(facecolor=_BG, edgecolor=_GRID, labelcolor=_TEXT, fontsize=8)
    out_png = Path(out_png)
    fig.savefig(out_png, dpi=150, facecolor=_BG)
    plt.close(fig)
    return out_png


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Physical bench intake -> material card")
    ap.add_argument("csv", help="bench sweep CSV (see docs/BENCH-PROTOCOL.md)")
    ap.add_argument("--fin-json", help="fingen-case.json-style params for E inversion")
    ap.add_argument("--material", default=None, choices=sorted(_MATERIAL_ALLOW_MPA))
    ap.add_argument("--out", help="material-card JSON path (default <csv>.card.json)")
    ap.add_argument("--plot", help="QC PNG path (default <csv>.qc.png)")
    ap.add_argument("--no-plot", action="store_true", help="skip the QC plot")
    args = ap.parse_args(argv)

    fin = load_fin_params(args.fin_json) if args.fin_json else None
    mc = process(args.csv, fin=fin, material=args.material)

    csv = Path(args.csv)
    out = Path(args.out) if args.out else csv.with_suffix(".card.json")
    out.write_text(json.dumps(mc.card, indent=2) + "\n")

    plot_note = ""
    if not args.no_plot:
        png = Path(args.plot) if args.plot else csv.with_suffix(".qc.png")
        make_qc_plot(mc, png)
        plot_note = f" · plot {png}"

    c = mc.card
    e_note = f" · E_eff {c['E_eff_mpa']:.0f} MPa" if c["E_eff_mpa"] is not None else ""
    print(f"K {c['K_measured_N_per_mm']:.2f} N/mm (R² {c['R2']:.4f}){e_note} · "
          f"hyst {c['hysteresis_area_mJ']:.2f} mJ · card {out}{plot_note}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
