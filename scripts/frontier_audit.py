"""Lever audit on a frontier (gen-3 item 0.2): how much can each TASTE quantity
move without giving up the monotone goods, and what moves it?

    uv run python scripts/frontier_audit.py out/frontier-<rider>.json [--floor=2] [--fmax=1.0,1.3] [--md=out.md]

Reads the JSON written by scripts/frontier.py. Defines the "realistic" subset
of the frontier (peak margin >= floor degrees) and a BAND of near-equivalent
goods inside it (F_max between fmax_lo and fmax_hi times F_peak, trim drag at
or below the band's median), then reports for every taste quantity its range
inside the band (max/min), the same per 100 N bin of F_max across the whole
frontier, and the Spearman correlation of each design knob with each taste
quantity inside the band. A lever whose in-band range is small cannot be
offered: moving it would mean trading goods, not taste.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

TASTES = ("yaw_stiffness_nm_rad", "roll_damping_nm_s", "release_proxy")
GOODS = ("drag_trim_n", "drag_peak_n", "ld_work", "ld_peak", "f_max_eff_n", "margin_peak_deg")
KNOBS = ("depth", "base", "sweep", "tip_width_ratio", "le_fullness", "te_shape", "t_c",
         "thickness_tip_factor", "area_mm2", "aspect_ratio")


def _sp(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 6 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    opt = {k: v for k, v in (a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)}
    floor = float(opt.get("floor", 2.0))
    f_lo, f_hi = (float(x) for x in opt.get("fmax", "1.0,1.3").split(","))
    d = json.loads(Path(args[0]).read_text())
    F = np.array(d["frontier"], dtype=float)
    col = {f: i for i, f in enumerate(d["fields"])}
    c = lambda k, A=F: A[:, col[k]]
    r = d["rider"]
    fp, dboard = r["f_peak_n"], r["board_drag_yardstick_n"]
    out: list[str] = []
    w = out.append
    w(f"# Lever audit — {r['preset']}: {r['weight_kg']:.0f} kg {r['skill']}, {r['speed_ms']:.1f} m/s, "
      f"F_peak {fp:.0f} N, board drag ≈ {dboard:.0f} N\n")
    real = c("margin_peak_deg") >= floor
    R = F[real]
    w(f"Frontier {len(F)} designs; realistic subset (margin ≥ {floor:g}°): {len(R)}.\n")

    def ext(A, k):
        v = A[:, col[k]]; v = v[~np.isnan(v)]
        return (float(v.min()), float(v.max())) if len(v) else (float("nan"), float("nan"))

    w("## Goods on the realistic frontier\n")
    w("| quantity | min | max | in rider terms |")
    w("|---|---|---|---|")
    terms = {"drag_trim_n": lambda a, b: f"{(b - a) / dboard * 100:.0f} % of board drag",
             "drag_peak_n": lambda a, b: f"{(b - a) / dboard * 100:.0f} % of board drag",
             "ld_work": lambda a, b: f"×{b / a:.2f}", "ld_peak": lambda a, b: f"×{b / a:.2f}",
             "f_max_eff_n": lambda a, b: f"{a / fp:.2f}–{b / fp:.2f} × F_peak",
             "margin_peak_deg": lambda a, b: f"{b - a:.1f}° span"}
    for k in GOODS:
        a, b = ext(R, k); w(f"| {k} | {a:.2f} | {b:.2f} | {terms[k](a, b)} |")

    band = real & (c("f_max_eff_n") >= f_lo * fp) & (c("f_max_eff_n") <= f_hi * fp)
    if band.sum():
        med = float(np.median(c("drag_trim_n")[band]))
        band &= c("drag_trim_n") <= med
    B = F[band]
    w(f"\n## Band of near-equivalent goods: margin ≥ {floor:g}°, F_max {f_lo:g}–{f_hi:g} × F_peak, "
      f"trim drag ≤ band median — {len(B)} designs\n")
    w("| quantity | band min | band max | ratio | note |")
    w("|---|---|---|---|---|")
    for k in TASTES + ("ld_work", "drag_trim_n", "drag_peak_n"):
        if len(B):
            a, b = ext(B, k)
            note = "taste lever range at ~fixed goods" if k in TASTES else "residual spread of the goods inside the band"
            w(f"| {k} | {a:.3g} | {b:.3g} | ×{b / a:.2f} | {note} |")
    w("\n## Taste spread per 100 N bin of F_max (whole frontier)\n")
    w("| F_max bin | n | yaw stiffness | roll damping | release proxy | trim drag N |")
    w("|---|---|---|---|---|---|")
    fm = c("f_max_eff_n")
    for lo in range(int(np.floor(fm.min() / 100) * 100), int(fm.max()) + 1, 100):
        m = (fm >= lo) & (fm < lo + 100)
        if m.sum() < 5:
            continue
        cells = []
        for k in TASTES + ("drag_trim_n",):
            v = c(k)[m]
            cells.append(f"{v.min():.3g}–{v.max():.3g} (×{v.max() / v.min():.1f})")
        w(f"| {lo}–{lo + 100} | {m.sum()} | " + " | ".join(cells) + " |")
    if len(B) >= 8:
        w("\n## What moves each taste at ~fixed goods (Spearman inside the band)\n")
        w("| knob | yaw stiffness | roll damping | release proxy |")
        w("|---|---|---|---|")
        for k in KNOBS:
            w(f"| {k} | " + " | ".join(f"{_sp(c(t, B), c(k, B)):+.2f}" for t in TASTES) + " |")
        w("\n## Taste-vs-taste inside the band (are they independent levers?)\n")
        w("| | yaw stiffness | roll damping | release proxy |")
        w("|---|---|---|---|")
        for t1 in TASTES:
            w(f"| {t1} | " + " | ".join(f"{_sp(c(t1, B), c(t2, B)):+.2f}" for t2 in TASTES) + " |")
    text = "\n".join(out)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
