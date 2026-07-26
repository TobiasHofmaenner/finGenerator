"""Before/after visualization packet for the freshly-fixed optimizer.

Usage:
    uv run python scripts/before_after.py <out_png> [budget] [seed]
    (defaults: budget 600 evals/rider, seed 0)

Four rider profiles chosen for variety (weight x skill x config). For each:

  BEFORE  the default TEMPLATE blade the optimizer starts stage A from — the
          same FinParams `optimize._x0_sliders` implies: `family_for_config`
          for the config, every other parameter at its dataclass default —
          scored with `evaluate()`.
  AFTER   `optimize(rider, budget, seed)`: the search winner and its evaluation.

Renders ONE combined dark-style sheet (~2200x2800), one row per rider, three
panels: an outline overlay (before grey / after cyan), a spider radar
(before / after / target), and a monospace numbers panel. Also drops a per-rider
result JSON next to the PNG (`<stem>-<n>.json`) via `write_result_json` for the
CFD verification stage (scripts/verify_candidate.py).

The predictions are tier-0 analytic; winners are verified by CFD on demand.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

from fingen import spider
from fingen.optimize import (
    RiderSpec,
    evaluate,
    family_for_config,
    optimize,
    write_result_json,
)
from fingen.outline import metrics, planform
from fingen.params import FinConfig, FinParams, FoilParams
from fingen.sizing import Skill

# House palette (near-black bg, cyan primary, orange accent) + a dim grey for
# the "before" template so the eye reads it as the faded baseline.
_BG = "#0b0e11"
_PANEL = "#12171c"
_CYAN = "#7fd4e0"
_CYAN_LT = "#a7e0ea"
_ORANGE = "#f2a154"
_INK = "#e8edf0"
_MUTED = "#8a97a0"
_GREY = "#3a4650"
_GRID = (1.0, 1.0, 1.0, 0.12)

# Four riders spanning the design space: light/casual, mid, heavy/aggressive,
# and a single-fin config for contrast (deeper blade, symmetric foil family).
RIDERS: tuple[tuple[str, RiderSpec], ...] = (
    ("60 kg cruiser · thruster",
     RiderSpec(weight_kg=60.0, skill=Skill.CRUISER, config=FinConfig.THRUSTER)),
    ("75 kg intermediate · thruster",
     RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE, config=FinConfig.THRUSTER)),
    ("95 kg pro · thruster",
     RiderSpec(weight_kg=95.0, skill=Skill.PRO, config=FinConfig.THRUSTER)),
    ("82 kg advanced · single",
     RiderSpec(weight_kg=82.0, skill=Skill.ADVANCED, config=FinConfig.SINGLE)),
)


def default_fin(config: FinConfig) -> FinParams:
    """The BEFORE blade: the template default with only the config's foil family
    set — exactly the fin `optimize._x0_sliders` back-projects for stage A."""
    return FinParams(foil=FoilParams(family=family_for_config(config)))


# --- outline overlay ---------------------------------------------------------


def _outline_xy(fin: FinParams) -> tuple[np.ndarray, np.ndarray]:
    """Closed planform polygon (x streamwise, y spanwise) — the drawing path
    used by optimize._draw_outline / paramviz."""
    z, x_le, chord = planform(fin.outline)
    live = chord > 0.3
    x = np.concatenate((x_le[live], (x_le + chord)[live][::-1]))
    y = np.concatenate((z[live], z[live][::-1]))
    return x, y


def _draw_grooves(ax, fin: FinParams, color: str) -> None:
    if not fin.grooves.count:
        return
    z, x_le, chord = planform(fin.outline)
    g = fin.grooves
    for i in range(g.count):
        zc = g.span_start * fin.outline.depth + i * g.pitch
        x0 = float(np.interp(zc, z, x_le))
        run = min(g.length, 0.55 * float(np.interp(zc, z, chord)))
        ax.plot([x0 + 2, x0 + 2 + run], [zc, zc], color=color, lw=1.6,
                solid_capstyle="round", alpha=0.9)


def draw_outline_overlay(ax, label: str, before: FinParams, after: FinParams) -> None:
    """Before (dim grey, subtle fill) under after (cyan, light fill), one mm
    scale (equal aspect) so the two shapes are directly comparable."""
    ax.set_facecolor(_PANEL)
    xb, yb = _outline_xy(before)
    xa, ya = _outline_xy(after)
    ax.fill(xb, yb, color=_GREY, alpha=0.22)
    ax.plot(xb, yb, color=_GREY, lw=1.8, label="before (template)")
    ax.fill(xa, ya, color=_CYAN, alpha=0.15)
    ax.plot(xa, ya, color=_CYAN, lw=2.3, label="after (optimized)")
    _draw_grooves(ax, after, _ORANGE)
    ax.set_aspect("equal")
    ax.invert_yaxis()  # base at top, tip hanging down (mounted-under-board view)
    ob, oa = before.outline, after.outline
    ax.text(0.03, 0.13, f"before {ob.depth:.0f} x {ob.base:.0f} mm", color=_GREY,
            fontsize=8, family="monospace", transform=ax.transAxes, va="bottom")
    ax.text(0.03, 0.05, f"after  {oa.depth:.0f} x {oa.base:.0f} mm", color=_CYAN,
            fontsize=8, family="monospace", transform=ax.transAxes, va="bottom")
    ax.set_title(label, color=_INK, fontsize=11, family="monospace", pad=8)
    ax.tick_params(colors=_MUTED, labelsize=6)
    for s in ax.spines.values():
        s.set_color("#2a333b")
    ax.legend(loc="lower right", facecolor=_PANEL, edgecolor=_GRID,
              labelcolor=_INK, fontsize=7)


# --- spider radar ------------------------------------------------------------


def draw_radar(ax, before_res, after_res) -> None:
    """Six-axis radar: target (dashed orange), before (grey, light fill), after
    (cyan, fill). Everything is already 0..100 (spider_target is targets x100)."""
    axes = spider.AXES
    ang = np.linspace(0.0, 2.0 * np.pi, len(axes), endpoint=False)
    ang_c = np.concatenate((ang, ang[:1]))
    tgt = np.array([after_res.spider_target[a] for a in axes])
    bef = np.array([before_res.spider_predicted[a] for a in axes])
    aft = np.array([after_res.spider_predicted[a] for a in axes])

    t = np.concatenate((tgt, tgt[:1]))
    ax.plot(ang_c, t, color=_ORANGE, lw=1.8, ls="--", label="target")
    b = np.concatenate((bef, bef[:1]))
    ax.fill(ang_c, b, color=_GREY, alpha=0.30)
    ax.plot(ang_c, b, color=_GREY, lw=1.6, label="before")
    a = np.concatenate((aft, aft[:1]))
    ax.fill(ang_c, a, color=_CYAN, alpha=0.16)
    ax.plot(ang_c, a, color=_CYAN, lw=2.0, label="after")

    ax.set_xticks(ang)
    # HOLD* is requirement-relative (headroom over F_req), not fleet-ranked like
    # the other five axes (spider.hold_score).
    ax.set_xticklabels([(name.upper() + "*" if name == "hold" else name.upper())
                        for name in axes], color=_INK, fontsize=7,
                       family="monospace")
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75])
    ax.set_yticklabels(["25", "50", "75"], color=_MUTED, fontsize=6)
    ax.grid(color=_GRID, lw=0.8)
    ax.set_facecolor(_BG)
    ax.spines["polar"].set_color(_GRID)
    ax.legend(loc="upper right", bbox_to_anchor=(1.30, 1.07), facecolor=_PANEL,
              edgecolor=_GRID, labelcolor=_INK, fontsize=7)
    ax.text(0.5, -0.11, "* hold = requirement-relative (f_max / F_req)",
            color=_MUTED, fontsize=6, family="monospace", ha="center",
            va="top", transform=ax.transAxes)


# --- numbers panel -----------------------------------------------------------


def draw_numbers(ax, before_res, after_res, before: FinParams, after: FinParams,
                 opt) -> None:
    """Monospace ledger: objective before->after, feasibility, per-axis
    predicted-vs-target, geometry deltas, after-margins, penalties."""
    ax.set_facecolor(_PANEL)
    ax.axis("off")
    ob, oa = before.outline, after.outline
    fb, fa = before.foil, after.foil
    mb, ma = metrics(ob), metrics(oa)
    obj_b, obj_a = before_res.objective, after_res.objective
    impr = 100.0 * (obj_b - obj_a) / obj_b if obj_b else 0.0

    lines: list[tuple[str, str]] = []
    lines.append((f"objective  {obj_b:.3f} -> {obj_a:.3f}  ({impr:+.1f}%)",
                  _CYAN if obj_a <= obj_b else _ORANGE))
    bf = "yes" if before_res.feasible else "NO"
    af = "yes" if after_res.feasible else "NO"
    lines.append((f"feasible   before {bf}   after {af}   evals {opt.n_evals}",
                  _MUTED))
    lines.append(("", _INK))
    lines.append((f"{'axis':<12s}{'before':>8s}{'after':>8s}{'target':>8s}", _MUTED))
    for a in spider.AXES:
        lines.append((f"{a:<12s}{before_res.spider_predicted[a]:>8.1f}"
                      f"{after_res.spider_predicted[a]:>8.1f}"
                      f"{after_res.spider_target[a]:>8.1f}", _INK))
    lines.append(("", _INK))
    lines.append((f"{'geometry':<12s}{'before':>8s}{'after':>8s}{'Δ':>8s}", _MUTED))
    lines.append((f"{'depth mm':<12s}{ob.depth:>8.0f}{oa.depth:>8.0f}"
                  f"{oa.depth - ob.depth:>+8.0f}", _INK))
    lines.append((f"{'base mm':<12s}{ob.base:>8.0f}{oa.base:>8.0f}"
                  f"{oa.base - ob.base:>+8.0f}", _INK))
    lines.append((f"{'sweep deg':<12s}{ob.sweep:>8.0f}{oa.sweep:>8.0f}"
                  f"{oa.sweep - ob.sweep:>+8.0f}", _INK))
    lines.append((f"{'t/c':<12s}{fb.thickness_ratio:>8.3f}{fa.thickness_ratio:>8.3f}"
                  f"{fa.thickness_ratio - fb.thickness_ratio:>+8.3f}", _INK))
    lines.append((f"{'AR':<12s}{mb.aspect_ratio:>8.2f}{ma.aspect_ratio:>8.2f}"
                  f"{ma.aspect_ratio - mb.aspect_ratio:>+8.2f}", _INK))
    lines.append((f"{'area mm2':<12s}{mb.area:>8.0f}{ma.area:>8.0f}"
                  f"{ma.area - mb.area:>+8.0f}", _INK))
    lines.append(("", _INK))
    mg = after_res.margins
    lines.append((f"after margins: stress SF {mg['stress_sf']:.2f}  "
                  f"f_wet {mg['f_wet_hz']:.0f} Hz", _MUTED))
    lines.append((f"  tip defl {mg['tip_deflection_mm']:.2f} mm  "
                  f"washout {mg['washout_pct']:+.1f}%  "
                  f"work {mg['alpha_work_deg']:.1f}deg", _MUTED))
    if after.grooves.count:
        lines.append((f"  grooves {after.grooves.count} @ depth "
                      f"{after.grooves.depth_ratio:.2f}", _MUTED))
    pen = after_res.penalties
    pstr = " ".join(f"{k} {v:.2f}" for k, v in pen.items()) if pen else "none"
    lines.append((f"penalties (after): {pstr}", _ORANGE if pen else _MUTED))

    y = 0.99
    for text, color in lines:
        ax.text(0.0, y, text, color=color, fontsize=8.2, family="monospace",
                va="top", transform=ax.transAxes)
        y -= 0.0445


# --- sheet -------------------------------------------------------------------


def render_sheet(out_png: Path, budget: int, seed: int, rows: list) -> None:
    """One combined portrait sheet, one row per rider (outline / radar / numbers)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(16.9, 21.5), facecolor=_BG)  # ~2197 x 2795 @ dpi 130
    fig.text(0.5, 0.988, "T-FINS optimizer — before / after", color=_INK,
             fontsize=24, family="monospace", ha="center", weight="bold")
    fig.text(0.5, 0.971,
             f"default template blade  ->  optimized winner   ·   "
             f"budget {budget} evals/rider   ·   seed {seed}",
             color=_MUTED, fontsize=13, family="monospace", ha="center")

    gs = fig.add_gridspec(len(rows), 3, left=0.045, right=0.985, top=0.93,
                          bottom=0.028, hspace=0.30, wspace=0.24,
                          width_ratios=[1.0, 1.0, 1.28])
    for i, (_label, _rider, before_fin, before_res, opt) in enumerate(rows):
        draw_outline_overlay(fig.add_subplot(gs[i, 0]), _label, before_fin, opt.fin)
        draw_radar(fig.add_subplot(gs[i, 1], projection="polar"), before_res, opt.result)
        draw_numbers(fig.add_subplot(gs[i, 2]), before_res, opt.result,
                     before_fin, opt.fin, opt)

    fig.text(0.5, 0.010, "tier-0 predictions; winners verified by CFD on demand",
             color=_MUTED, fontsize=12, family="monospace", ha="center", style="italic")
    fig.savefig(out_png, dpi=130, facecolor=_BG)
    plt.close(fig)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out_png = Path(sys.argv[1])
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    out_png.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for n, (label, rider) in enumerate(RIDERS, start=1):
        before_fin = default_fin(rider.config)
        before_res = evaluate(before_fin, rider)
        t0 = time.time()
        opt = optimize(rider, budget_evals=budget, seed=seed)
        dt = time.time() - t0
        json_path = out_png.with_name(f"{out_png.stem}-{n}.json")
        write_result_json(opt, json_path)
        flag = "" if opt.result.feasible else "  ** INFEASIBLE **"
        impr = (100.0 * (before_res.objective - opt.result.objective)
                / before_res.objective if before_res.objective else 0.0)
        print(f"[{n}] {label}: obj {before_res.objective:.3f} -> "
              f"{opt.result.objective:.3f} ({impr:+.1f}%)  "
              f"depth {before_fin.outline.depth:.0f}->{opt.fin.outline.depth:.0f} "
              f"base {before_fin.outline.base:.0f}->{opt.fin.outline.base:.0f} "
              f"AR {metrics(opt.fin.outline).aspect_ratio:.2f}  "
              f"grooves {opt.fin.grooves.count}  {dt:.0f}s{flag}", flush=True)
        if opt.result.penalties:
            print(f"    penalties: {opt.result.penalties}", flush=True)
        rows.append((label, rider, before_fin, before_res, opt))

    render_sheet(out_png, budget, seed, rows)
    print(f"wrote {out_png}", flush=True)


if __name__ == "__main__":
    main()
