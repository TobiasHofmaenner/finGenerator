"""Visualization packet for a designed SET (side + centre) from a result JSON.

Three panels, dark sheet, one file:

  1. PLANFORM   both blades overlaid at true scale, side (cyan) and centre
                (orange), with the base plane and the tab footprints drawn —
                the tab span is what carries the root moment, so it belongs in
                any picture used to judge a set.
  2. SPIDER     each blade's predicted character against its own target. The
                centre gets DIFFERENT targets from the side (optimize
                ._CENTER_TARGET_OVERRIDES), so plotting one target ring for
                both would misrepresent the centre.
  3. NUMBERS    the margins that decide whether it can be built, with the
                binding one called out. A set that scores well on character and
                fails a structural gate is not a better set.

Usage: uv run python scripts/set_viz.py <result.json> [out.png]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dataclasses  # noqa: E402

from fingen import spider  # noqa: E402
from fingen.optimize import fin_from_dict  # noqa: E402
from fingen.outline import planform  # noqa: E402
from fingen.params import TabParams, TabSystem  # noqa: E402
from fingen.tabs import system_depth, tab_span_x  # noqa: E402

_BG, _FG, _GRID = "#0b0e11", "#d7dee6", "#243040"
_SIDE, _CENTER, _TGT = "#38bdf8", "#fb923c", "#a3a3a3"


def _outline_xy(fin) -> tuple[np.ndarray, np.ndarray]:
    """Closed LE->tip->TE loop in mm, y = span."""
    z, x_le, chord = planform(fin.outline)
    x = np.concatenate([x_le, (x_le + chord)[::-1], x_le[:1]])
    y = np.concatenate([z, z[::-1], z[:1]])
    return x, y


def draw_planform(ax, side, center) -> None:
    for fin, colour, label in ((side, _SIDE, "side"), (center, _CENTER, "centre")):
        if fin is None:
            continue
        x, y = _outline_xy(fin)
        ax.plot(x, y, color=colour, lw=1.8, label=label)
        ax.fill(x, y, color=colour, alpha=0.10)
        # tab footprint: the section that actually carries the root moment
        span = tab_span_x(fin)
        if span is not None:
            depth = system_depth(fin.tabs)
            x0, x1 = span
            ax.add_patch(plt.Rectangle((x0, -depth), x1 - x0, depth,
                                       facecolor=colour, alpha=0.30,
                                       edgecolor=colour, lw=1.0))
    ax.axhline(0.0, color=_FG, lw=0.9, ls="--", alpha=0.6)
    ax.text(0.02, 0.02, "base plane (z=0); boxes = tab footprint",
            transform=ax.transAxes, color=_FG, fontsize=7, alpha=0.7)
    ax.set_aspect("equal")
    ax.set_xlabel("chord [mm]", color=_FG, fontsize=8)
    ax.set_ylabel("span [mm]", color=_FG, fontsize=8)
    ax.set_title("planform (true scale)", color=_FG, fontsize=10)
    ax.legend(facecolor=_BG, edgecolor=_GRID, labelcolor=_FG, fontsize=8)


def draw_radar(ax, predicted: dict, target: dict, colour: str, title: str) -> None:
    axes = spider.AXES
    ang = np.linspace(0, 2 * np.pi, len(axes), endpoint=False)
    ang = np.concatenate([ang, ang[:1]])
    pv = np.array([predicted[a] for a in axes])
    tv = np.array([target[a] for a in axes])
    pv = np.concatenate([pv, pv[:1]])
    tv = np.concatenate([tv, tv[:1]])
    ax.plot(ang, tv, color=_TGT, lw=1.3, ls="--", label="target")
    ax.plot(ang, pv, color=colour, lw=2.0, label="predicted")
    ax.fill(ang, pv, color=colour, alpha=0.18)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels(axes, color=_FG, fontsize=7)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", ""], color=_FG, fontsize=6)
    ax.set_title(title, color=_FG, fontsize=10, pad=14)
    ax.grid(color=_GRID, lw=0.6)
    ax.legend(facecolor=_BG, edgecolor=_GRID, labelcolor=_FG,
              fontsize=7, loc="upper right", bbox_to_anchor=(1.25, 1.12))


def draw_numbers(ax, d: dict) -> None:
    ax.axis("off")
    r = d["rider"]
    sm, cm = d["margins"], (d.get("center") or {}).get("margins", {})
    gate = r.get("stress_sf_min", 1.0)
    sd = sm["tip_deflection_mm"] / d["fin"]["outline"]["depth"] * 100.0
    cd = ((cm["tip_deflection_mm"] / d["center_fin"]["outline"]["depth"] * 100.0)
          if cm else float("nan"))
    lines = [
        f"{r['weight_kg']:.0f} kg  {r['skill']}  {r['config']}  "
        f"{r['material']}  {r['tabs']}",
        f"design speed {r['speed_ms']:.2f} m/s      set objective "
        f"{d['set']['objective']:.4f}",
        "",
        f"{'':<22}{'SIDE':>10}{'CENTRE':>10}",
        f"{'area  [mm2]':<22}{sm['area_mm2']:>10.0f}"
        f"{cm.get('area_mm2', float('nan')):>10.0f}",
        f"{'tip deflection [mm]':<22}{sm['tip_deflection_mm']:>10.1f}"
        f"{cm.get('tip_deflection_mm', float('nan')):>10.1f}",
        f"{'   .. % of span':<22}{sd:>10.1f}{cd:>10.1f}",
        f"{'washout [%]':<22}{sm['washout_pct']:>10.2f}"
        f"{cm.get('washout_pct', float('nan')):>10.2f}",
        "",
        f"{'blade SF (steady)':<22}{sm['stress_sf']:>10.2f}"
        f"{cm.get('stress_sf', float('nan')):>10.2f}   gate {gate:.2f}",
        f"{'blade SF (roll)':<22}{sm['stress_sf_roll']:>10.2f}"
        f"{cm.get('stress_sf_roll', float('nan')):>10.2f}",
        f"{'TAB SF':<22}{sm['tab_sf']:>10.2f}"
        f"{cm.get('tab_sf', float('nan')):>10.2f}   "
        f"gate {r.get('tab_sf_min') if r.get('tab_sf_min') else 'OFF'}",
    ]
    # GATED vs REPORTED. A margin below 1.0 on an axis the rider deliberately
    # left ungated (tab_sf_min=None) is an OPEN QUESTION for tier-1, not a
    # verdict — an earlier version printed "not printable as-is" and "all gated
    # margins satisfied" in the same panel, which is both contradictory and
    # overclaims what tier-0 knows.
    gated = [("blade SF", sm["stress_sf_roll"])]
    if cm:
        gated.append(("centre blade SF", cm["stress_sf_roll"]))
    reported = []
    if r.get("tab_sf_min") is None:
        reported.append(("tab SF", min([sm["tab_sf"]] + ([cm["tab_sf"]] if cm else []))))
    else:
        gated.append(("tab SF", min([sm["tab_sf"]] + ([cm["tab_sf"]] if cm else []))))

    failed = [(n, v) for n, v in gated if v < 1.0]
    if failed:
        n, v = min(failed, key=lambda t: t[1])
        lines += ["", f"!! GATE FAILED: {n} {v:.2f} — below unity.",
                  "   Not printable as-is."]
    elif d["set"].get("feasible"):
        lines += ["", "all GATED margins satisfied"]
    for n, v in reported:
        if v < 1.0:
            lines += ["", f"?  {n} {v:.2f} (REPORTED, gate off) — tier-0's tab",
                      "   model is crude here; tier-1 adjudicates. On the 95 kg",
                      "   FCS1 blade it read 2.5-4.8x pessimistic."]
    # A linear Euler-Bernoulli solve produced every row above. Past ~10% of span
    # (where tier-1 measured a 3.7% stress shift) it is out of validity, and
    # nothing in the gate chain checked this until tip_deflection_max_frac.
    if max(sd, 0.0 if cd != cd else cd) > 15.0:
        lines += ["", f"!! tip deflection {max(sd, cd):.0f}% of span — the flex",
                  "   model is LINEAR and is outside its validity here.",
                  "   Treat washout/stress above as unreliable."]
    ax.text(0.0, 1.0, "\n".join(lines), transform=ax.transAxes, va="top",
            family="monospace", fontsize=8.5,
            color="#fca5a5" if failed else _FG)


def main() -> int:
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".png")
    d = json.loads(src.read_text())
    # The optimizer designs BLADES; tabs are attached at export time, so the
    # stored fin carries TabSystem.NONE. Re-attach the rider's system here or
    # the panel silently omits the section that carries the root moment.
    tabs = TabParams(system=TabSystem(d["rider"]["tabs"]), fit_offset=-0.2)
    side = dataclasses.replace(fin_from_dict(d["fin"]), tabs=tabs)
    center = (dataclasses.replace(fin_from_dict(d["center_fin"]), tabs=tabs)
              if d.get("center_fin") else None)

    fig = plt.figure(figsize=(15.5, 5.6), facecolor=_BG)
    gs = fig.add_gridspec(1, 4, width_ratios=[1.15, 1.0, 1.0, 1.05], wspace=0.42)
    ax0 = fig.add_subplot(gs[0, 0], facecolor=_BG)
    draw_planform(ax0, side, center)
    ax1 = fig.add_subplot(gs[0, 1], projection="polar", facecolor=_BG)
    draw_radar(ax1, d["spider_predicted"], d["spider_target"], _SIDE, "side")
    if center is not None:
        ax2 = fig.add_subplot(gs[0, 2], projection="polar", facecolor=_BG)
        # The centre is scored against its OWN targets, not the side's.
        draw_radar(ax2, d["center"]["spider_predicted"],
                   d["center"].get("spider_target", d["spider_target"]),
                   _CENTER, "centre")
    ax3 = fig.add_subplot(gs[0, 3], facecolor=_BG)
    draw_numbers(ax3, d)

    for ax in (ax0,):
        ax.tick_params(colors=_FG, labelsize=7)
        for sp in ax.spines.values():
            sp.set_color(_GRID)
        ax.grid(color=_GRID, lw=0.5, alpha=0.5)
    fig.suptitle(src.stem, color=_FG, fontsize=11, y=0.98)
    fig.savefig(out, dpi=130, facecolor=_BG, bbox_inches="tight")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
