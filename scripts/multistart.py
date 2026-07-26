"""Multistart convergence study for the fingen optimizer.

Usage:
    uv run python scripts/multistart.py <out_prefix> [n_starts=20] [budget=3000] [seed=0]

The question this answers, in the user's words: with more compute per run and
many different starting points spread across the parameter grid, do all restarts
converge to one global minimum, or do we get distinct local solutions?

For two riders — 75 kg INTERMEDIATE thruster (the well-conditioned case) and
95 kg PRO thruster (the antagonistic-target case, whose derived spider wishes
demand hold+drive+speed at once) — the study:

  1. STARTS  Latin-hypercube samples `n_starts` points in the level-1 slider
     cube [0,1]^8 (seeded, reproducible). Start #0 is the template default
     encoding, so the *old* behavior (optimize with no x0) is literally one of
     the restarts — and, run with the base seed, an exact reproduction of it.
  2. RUNS    fires the SAME two-stage `optimize()` from each start with real
     `budget` compute per restart (via the new backward-compatible `x0` param),
     parallelized across processes. Restart i uses seed = base_seed + i, so the
     stochastic search is independent per start while staying reproducible.
  3. CLUSTER groups the finals into basins by single-link agglomerative
     clustering on euclidean distance in the normalized slider space
     (threshold 0.10 — see `_CLUSTER_THRESHOLD`).
  4. CENTROID answers "is the average of the parameters a viable fin?" — the
     global and per-basin slider centroids are decoded and evaluated, and each
     slider is tagged consensus / split / flat.
  5. VIZ     renders per rider: a curated dark-style sheet (`<slug>.png`; arrow
     cloud, objective ladder, basin gallery, verdict) plus the full corner atlas
     (`<slug>-corner.png`; all 28 pairwise + 8 diagonal slider projections). The
     parameter centroid is a white star on both. A per-rider JSON with every
     restart's final and the centroid analysis sits next to the PNGs.

Tier-0 analytic evaluate; winners are verified by CFD on demand.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.stats import qmc

from fingen.optimize import (
    _N_SLIDERS,
    _SLIDER_BOUNDS,
    RiderSpec,
    _decode,
    _x0_sliders,
    evaluate,
    fin_from_dict,
    fin_to_dict,
    optimize,
)
from fingen.outline import metrics, planform
from fingen.params import FinConfig, FinParams
from fingen.sizing import Skill

# --- house palette (near-black bg, cyan primary, orange accent) --------------
_BG = "#0b0e11"
_PANEL = "#12171c"
_CYAN = "#7fd4e0"
_ORANGE = "#f2a154"
_INK = "#e8edf0"
_MUTED = "#8a97a0"
_GREY = "#3a4650"
_WHITE = "#ffffff"  # the global "consensus" centroid marker (average fin)
_GRID = (1.0, 1.0, 1.0, 0.12)

# Categorical basin palette (validated on the dark surface, dataviz skill).
# Cyan is the house primary; orange is reserved for the global-best marker, so
# it is deliberately absent here. Green<->red is the only adjacent CVD-warn
# pair, covered by the direct basin labels present on every panel.
_BASIN_COLORS = ["#7fd4e0", "#d55181", "#9085e9", "#199e70", "#e66767", "#c98500"]

# --- study config ------------------------------------------------------------
# The two rider profiles: the well-conditioned mid case and the antagonistic
# heavy/aggressive case whose flattened landscape is the multimodality suspect.
RIDERS: tuple[tuple[str, str, RiderSpec], ...] = (
    ("75kg-intermediate", "75 kg intermediate · thruster",
     RiderSpec(weight_kg=75.0, skill=Skill.INTERMEDIATE, config=FinConfig.THRUSTER)),
    ("95kg-pro", "95 kg pro · thruster",
     RiderSpec(weight_kg=95.0, skill=Skill.PRO, config=FinConfig.THRUSTER)),
)

# Basins are single-link agglomerative clusters on euclidean distance in the
# normalized slider space — but only over the sliders the objective actually
# IDENTIFIES. Empirically the optimum is a FLAT valley: tip_width_ratio,
# le_fullness and thickness_tip_factor roam most of their range at essentially
# constant objective (see the per-slider IQR). Left in, those unidentified
# directions inflate intra-basin distance past any small threshold and fragment
# one physical basin into dozens of numeric-noise "clusters" — exactly what the
# study must NOT call multimodality. So a slider with a normalized IQR above
# `_IQR_FLAT` (robust to a lone distinct basin) is dropped from the distance,
# and clustering runs on the load-bearing remainder. On that subspace the
# cluster count is stable across a wide threshold plateau (75 kg -> 1 for
# t in [0.15, 0.30]; 95 kg -> 2 for t in [0.12, 0.30]); 0.20 sits in both.
_CLUSTER_THRESHOLD = 0.20
_IQR_FLAT = 0.15
# A final within 5% of the global best counts as "reached the global basin".
_NEAR_FRAC = 0.05
# A slider this close to 0 or 1 is cornered against its bound.
_CORNER_EPS = 0.02

_SLIDER_NAMES = tuple(name for name, _lo, _hi in _SLIDER_BOUNDS)
# The eight decoded-geometry fields, in report order (matches the task list).
_GEOM_KEYS = ("depth", "base", "sweep", "tipw", "le_full", "te_shape",
              "t_c", "tip_factor")


# --- encode / decode helpers -------------------------------------------------


def encode_sliders(fin: FinParams) -> list[float]:
    """Back-project a fin's level-1 params to the normalized [0,1]^8 slider box
    (the inverse of `_decode`'s slider block; mirrors `_x0_sliders`)."""
    o, f = fin.outline, fin.foil
    src = {
        "depth": o.depth, "base": o.base, "sweep": o.sweep,
        "tip_width_ratio": o.tip_width_ratio, "le_fullness": o.le_fullness,
        "te_shape": o.te_shape, "thickness_ratio": f.thickness_ratio,
        "thickness_tip_factor": fin.thickness_tip_factor,
    }
    return [(src[name] - lo) / (hi - lo) for name, lo, hi in _SLIDER_BOUNDS]


def geom_of(fin: FinParams) -> dict[str, float]:
    """The eight decoded-geometry numbers the study reports and plots."""
    o = fin.outline
    return {
        "depth": o.depth, "base": o.base, "sweep": o.sweep,
        "tipw": o.tip_width_ratio, "le_full": o.le_fullness, "te_shape": o.te_shape,
        "t_c": fin.foil.thickness_ratio, "tip_factor": fin.thickness_tip_factor,
    }


def start_geom(x: list[float], config: FinConfig) -> dict[str, float] | None:
    """Geometry a start vector decodes to (level-1 only), for the arrow cloud.
    None if the (rare) raw start is undecodable — then we draw no start dot."""
    try:
        return geom_of(_decode(np.asarray(x, dtype=float), config,
                               use_offsets=False, use_grooves=False))
    except ValueError:
        return None


def make_starts(n_starts: int, config: FinConfig, seed: int) -> list[list[float]]:
    """`n_starts` starts in [0,1]^8: #0 the template default, the rest a seeded
    Latin-hypercube sample (reproducible for a given seed)."""
    template = _x0_sliders(config)
    if n_starts <= 1:
        return [template]
    sampler = qmc.LatinHypercube(d=_N_SLIDERS, seed=seed)
    lhs = sampler.random(n_starts - 1)
    return [template] + [list(row) for row in lhs]


# --- one restart (runs in a worker process) ----------------------------------


def _run_start(task: tuple) -> dict:
    """Run `optimize` from one start. Pure-python/numpy evaluate, fork-safe.
    Returns plain JSON-able types so nothing exotic crosses the process pool."""
    idx, rider, x0, budget, seed = task
    try:
        opt = optimize(rider, budget_evals=budget, seed=seed, x0=x0)
        fin = opt.fin
        r = opt.result
        sliders = encode_sliders(fin)
        cornered = [name for name, v in zip(_SLIDER_NAMES, sliders, strict=True)
                    if v <= _CORNER_EPS or v >= 1.0 - _CORNER_EPS]
        # Level-1-only objective: the fin the averaged sliders can reconstruct
        # (no stage-B Bezier offsets/grooves). This is the fair baseline the
        # centroid — also level-1 only — is compared against.
        try:
            fin_l1 = _decode(np.asarray(sliders, dtype=float), rider.config,
                             use_offsets=False, use_grooves=False)
            obj_l1 = float(evaluate(fin_l1, rider).objective)
        except ValueError:
            obj_l1 = None
        return {
            "idx": idx,
            "start": [float(v) for v in x0],
            "seed": seed,
            "final_sliders": [float(v) for v in sliders],
            "geom": geom_of(fin),
            "aspect_ratio": float(metrics(fin.outline).aspect_ratio),
            "area_mm2": float(metrics(fin.outline).area),
            "objective": float(r.objective),
            "objective_l1": obj_l1,
            "distance": float(r.distance),
            "penalty": float(r.penalty),
            "feasible": bool(r.feasible),
            "penalties": {k: float(v) for k, v in r.penalties.items()},
            "grooves": int(fin.grooves.count),
            "cornered_sliders": cornered,
            "n_evals": int(opt.n_evals),
            "fin": fin_to_dict(fin),
            "error": None,
        }
    except Exception as exc:  # a crashed restart is data, not a study failure
        return {"idx": idx, "start": [float(v) for v in x0], "seed": seed,
                "error": f"{type(exc).__name__}: {exc}"}


# --- clustering into basins --------------------------------------------------


def flat_directions(x: np.ndarray) -> tuple[list[int], np.ndarray]:
    """Sliders the objective leaves unidentified: normalized IQR > `_IQR_FLAT`.
    IQR (not std) so a single distinct basin can't push a tight slider over the
    line. Returns (flat indices, per-slider IQR)."""
    q25, q75 = np.percentile(x, [25, 75], axis=0)
    iqr = q75 - q25
    return [i for i in range(x.shape[1]) if iqr[i] > _IQR_FLAT], iqr


def cluster_basins(records: list[dict]
                   ) -> tuple[list[dict], list[float], list[int], list[float]]:
    """Single-link agglomerative clustering of the finals in the normalized
    slider space, restricted to the objective-IDENTIFIED sliders (the flat
    directions are dropped — see `_CLUSTER_THRESHOLD`). Basins are ranked by
    best (lowest) objective so basin 1 is the global basin. Annotates each valid
    record in place with `basin_rank`; returns the basin summaries, the sorted
    merge distances, the flat-slider indices, and the per-slider IQR."""
    valid = [r for r in records if r.get("error") is None]
    x = np.array([r["final_sliders"] for r in valid], dtype=float)

    flat_idx, iqr = flat_directions(x)
    ident_idx = [i for i in range(_N_SLIDERS) if i not in flat_idx] or list(range(_N_SLIDERS))
    xi = x[:, ident_idx]

    merges: list[float] = []
    if len(valid) == 1:
        labels = np.array([1])
    else:
        z = linkage(xi, method="single", metric="euclidean")
        merges = sorted(float(d) for d in z[:, 2])
        labels = fcluster(z, t=_CLUSTER_THRESHOLD, criterion="distance")

    groups: dict[int, list[dict]] = {}
    for rec, lab in zip(valid, labels, strict=True):
        groups.setdefault(int(lab), []).append(rec)

    # Rank basins by their best objective (global basin first).
    ordered = sorted(groups.values(), key=lambda g: min(r["objective"] for r in g))
    basins: list[dict] = []
    for rank, group in enumerate(ordered, start=1):
        rep = min(group, key=lambda r: r["objective"])
        for rec in group:
            rec["basin_rank"] = rank
        n_feas = sum(1 for r in group if r["feasible"])
        basins.append({
            "rank": rank,
            "count": len(group),
            "best_obj": rep["objective"],
            "worst_obj": max(r["objective"] for r in group),
            "representative_idx": rep["idx"],
            "geom": rep["geom"],
            "aspect_ratio": rep["aspect_ratio"],
            "feasible_count": n_feas,
            "members": sorted(r["idx"] for r in group),
            "cornered": rep["cornered_sliders"],
        })
    return basins, merges, flat_idx, [float(v) for v in iqr]


def verdict(records: list[dict], basins: list[dict]) -> dict:
    """Headline convergence metrics for the sheet footer and the JSON."""
    valid = [r for r in records if r.get("error") is None]
    objs = [r["objective"] for r in valid]
    best, worst = min(objs), max(objs)
    within = sum(1 for o in objs if o <= best * (1.0 + _NEAR_FRAC))
    template = next((r for r in records if r["idx"] == 0), None)
    template_rank = template.get("basin_rank") if template and not template.get("error") else None
    return {
        "n_basins": len(basins),
        "n_valid": len(valid),
        "n_crashed": sum(1 for r in records if r.get("error") is not None),
        "n_infeasible": sum(1 for r in valid if not r["feasible"]),
        "global_best": best,
        "worst": worst,
        "spread": worst - best,
        "frac_within_5pct": within / len(valid) if valid else 0.0,
        "n_within_5pct": within,
        "template_basin_rank": template_rank,
        "template_found_global": template_rank == 1,
        "total_evals": sum(r["n_evals"] for r in valid),
    }


# --- "is the average fin viable?" (centroid analysis) ------------------------
# A slider counts as consensus when the runs agree tightly; split when its
# per-basin means separate (the average lands between modes where neither lives);
# flat when it roams within a basin at ~constant objective (unidentified).
_SPLIT_SEP = 0.20


def _decode_eval(sliders: np.ndarray, rider: RiderSpec) -> dict:
    """Decode a level-1 slider vector and score it. A centroid can be
    undecodable (planform) or crash the flex tip check (chord_schedule); both
    mean 'not a viable fin' rather than a study failure."""
    out: dict = {"sliders": [float(v) for v in sliders]}
    try:
        fin = _decode(np.asarray(sliders, dtype=float), rider.config,
                      use_offsets=False, use_grooves=False)
        r = evaluate(fin, rider)
        out.update({
            "decodable": True, "objective": float(r.objective),
            "distance": float(r.distance), "penalty": float(r.penalty),
            "feasible": bool(r.feasible),
            "penalties": {k: float(v) for k, v in r.penalties.items()},
            "geom": geom_of(fin), "aspect_ratio": float(metrics(fin.outline).aspect_ratio),
            "viable": bool(r.feasible), "fin": fin_to_dict(fin),
        })
    except ValueError as exc:
        out.update({"decodable": False, "viable": False, "objective": None,
                    "feasible": False, "error": str(exc)})
    return out


def centroid_analysis(rider: RiderSpec, records: list[dict], basins: list[dict],
                      flat_names: list[str]) -> dict:
    """Answer 'is the average of the parameters a viable fin?' empirically: the
    global centroid, each basin's centroid, and a per-slider consensus/split/flat
    classification."""
    valid = [r for r in records if r.get("error") is None]
    x = np.array([r["final_sliders"] for r in valid], dtype=float)

    glob = _decode_eval(x.mean(axis=0), rider)
    best = min(r["objective"] for r in valid)              # offset-included winners
    worst = max(r["objective"] for r in valid)
    l1 = [r["objective_l1"] for r in valid if r.get("objective_l1") is not None]
    best_l1 = min(l1) if l1 else None                      # fair level-1 baseline
    if glob["objective"] is not None:
        glob["vs_best_pct"] = 100.0 * (glob["objective"] - best) / best if best else 0.0
        glob["vs_worst_pct"] = 100.0 * (glob["objective"] - worst) / worst if worst else 0.0
        if best_l1:
            glob["vs_best_l1_pct"] = 100.0 * (glob["objective"] - best_l1) / best_l1
    glob["best_l1"] = best_l1

    per_basin = []
    for b in basins:
        mem_recs = [r for r in valid if r["basin_rank"] == b["rank"]]
        mem = np.array([r["final_sliders"] for r in mem_recs])
        c = _decode_eval(mem.mean(axis=0), rider)
        b_l1 = [r["objective_l1"] for r in mem_recs if r.get("objective_l1") is not None]
        best_basin_l1 = min(b_l1) if b_l1 else None
        c["rank"] = b["rank"]
        c["basin_best"] = b["best_obj"]          # offset-included
        c["basin_best_l1"] = best_basin_l1       # fair level-1 baseline
        # Jitter-averaging: does the averaged fin beat the basin's best single
        # LEVEL-1 fin (like-for-like, since the centroid carries no offsets)?
        c["beats_basin_best"] = bool(c["objective"] is not None and best_basin_l1 is not None
                                     and c["objective"] <= best_basin_l1)
        per_basin.append(c)

    params = []
    for i, name in enumerate(_SLIDER_NAMES):
        means = [float(np.mean([r["final_sliders"][i] for r in valid
                                if r["basin_rank"] == b["rank"]])) for b in basins]
        sep = (max(means) - min(means)) if len(means) > 1 else 0.0
        cls = "flat" if name in flat_names else ("split" if sep > _SPLIT_SEP else "consensus")
        params.append({"slider": name, "std": float(x[:, i].std()),
                       "basin_means": means, "separation": sep, "class": cls})
    return {"global": glob, "per_basin": per_basin, "params": params}


# --- plotting ----------------------------------------------------------------


def _outline_xy(fin: FinParams) -> tuple[np.ndarray, np.ndarray]:
    z, x_le, chord = planform(fin.outline)
    live = chord > 0.3
    x = np.concatenate((x_le[live], (x_le + chord)[live][::-1]))
    y = np.concatenate((z[live], z[live][::-1]))
    return x, y


def _basin_color(rank: int | None) -> str:
    if rank is None:
        return _GREY
    return _BASIN_COLORS[(rank - 1) % len(_BASIN_COLORS)]


def _style_axes(ax, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_facecolor(_PANEL)
    ax.set_xlabel(xlabel, color=_MUTED, fontsize=9)
    ax.set_ylabel(ylabel, color=_MUTED, fontsize=9)
    ax.set_title(title, color=_INK, fontsize=10, family="monospace")
    ax.tick_params(colors=_MUTED, labelsize=7)
    ax.grid(color=_GRID, lw=0.6)
    for s in ax.spines.values():
        s.set_color("#2a333b")


def draw_cloud(ax, records, starts_geom, config, global_idx, xk, yk,
               xl, yl, centroid_geom=None) -> None:
    """Arrow cloud on one 2D geometry projection: grey start dot -> colored
    final dot (color = basin), the global best circled in orange, and the global
    parameter centroid (average fin) as a white star."""
    for rec in records:
        if rec.get("error") is not None:
            continue
        fg = rec["geom"]
        color = _basin_color(rec.get("basin_rank"))
        sg = starts_geom[rec["idx"]]
        if sg is not None:
            ax.annotate("", xy=(fg[xk], fg[yk]), xytext=(sg[xk], sg[yk]),
                        arrowprops=dict(arrowstyle="-|>", color=color, alpha=0.45,
                                        lw=0.9, shrinkA=2, shrinkB=3))
            ax.scatter([sg[xk]], [sg[yk]], s=14, c=_GREY, zorder=3,
                       edgecolors="none")
        ax.scatter([fg[xk]], [fg[yk]], s=44, c=color, zorder=4,
                   edgecolors=_BG, linewidths=0.6)
    gb = records[global_idx]["geom"]
    ax.scatter([gb[xk]], [gb[yk]], s=210, facecolors="none", edgecolors=_ORANGE,
               linewidths=2.2, zorder=5)
    if centroid_geom is not None:
        ax.scatter([centroid_geom[xk]], [centroid_geom[yk]], s=150, marker="*",
                   c=_WHITE, zorder=6, edgecolors=_BG, linewidths=0.6)
    _style_axes(ax, xl, yl, f"{xl} vs {yl}")


def draw_ladder(ax, records, global_best) -> None:
    """Sorted bar of final objectives, colored by basin, with an orange line at
    global best +5%. A flat run of equal bars = one basin; steps = multimodality."""
    valid = [r for r in records if r.get("error") is None]
    valid = sorted(valid, key=lambda r: r["objective"])
    objs = [r["objective"] for r in valid]
    colors = [_basin_color(r.get("basin_rank")) for r in valid]
    xs = np.arange(len(valid))
    ax.set_facecolor(_PANEL)
    ax.bar(xs, objs, color=colors, edgecolor=_BG, linewidth=0.6, width=0.82,
           zorder=3)
    thr = global_best * (1.0 + _NEAR_FRAC)
    ax.axhline(thr, color=_ORANGE, lw=1.4, ls="--", zorder=4)
    ax.text(0.15, thr, f"global best +5% = {thr:.3f}", color=_ORANGE, fontsize=8.5,
            family="monospace", va="bottom", ha="left", zorder=5,
            bbox=dict(boxstyle="round,pad=0.2", fc=_PANEL, ec="none", alpha=0.75))
    if max(objs) > 0 and min(objs) > 0 and max(objs) / min(objs) > 25.0:
        ax.set_yscale("log")
    ax.set_xlim(-0.7, len(valid) - 0.3)
    ax.set_xlabel("restart (sorted by final objective)", color=_MUTED, fontsize=9)
    ax.set_ylabel("final objective", color=_MUTED, fontsize=9)
    ax.set_title("objective ladder — one basin reads as one flat step",
                 color=_INK, fontsize=10, family="monospace")
    ax.tick_params(colors=_MUTED, labelsize=7)
    ax.grid(color=_GRID, lw=0.6, axis="y")
    for s in ax.spines.values():
        s.set_color("#2a333b")


def draw_gallery(ax, records, basins, n_valid, centroid=None) -> None:
    """Outline overlay of each basin representative on one mm scale. If a single
    basin dominates, it visually reads as one outline with a big call-out. When
    the global centroid (average fin) is viable, its outline is overlaid in white."""
    ax.set_facecolor(_PANEL)
    dominant = basins[0]["count"] >= 0.75 * n_valid if basins else False
    for basin in basins:
        rep = next(r for r in records if r["idx"] == basin["representative_idx"])
        fin = fin_from_dict(rep["fin"])
        x, y = _outline_xy(fin)
        color = _basin_color(basin["rank"])
        lw = 3.0 if (dominant and basin["rank"] == 1) else 2.1
        ax.plot(x, y, color=color, lw=lw,
                label=f"basin {basin['rank']}: {basin['count']}/{n_valid} runs")
        ax.fill(x, y, color=color, alpha=0.10)
    if centroid is not None and centroid.get("viable") and "fin" in centroid:
        cx, cy = _outline_xy(fin_from_dict(centroid["fin"]))
        ax.plot(cx, cy, color=_WHITE, lw=1.6, ls="--",
                label=f"consensus fin (obj {centroid['objective']:.3f})")
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_title("basin gallery — representative outlines (same mm scale)",
                 color=_INK, fontsize=10, family="monospace")
    ax.tick_params(colors=_MUTED, labelsize=6)
    for s in ax.spines.values():
        s.set_color("#2a333b")
    ax.legend(loc="lower right", facecolor=_PANEL, edgecolor=_GRID,
              labelcolor=_INK, fontsize=8)
    if dominant:
        ax.text(0.5, 0.96, f"{basins[0]['count']}/{n_valid} converge here",
                color=_CYAN, fontsize=13, family="monospace", ha="center",
                va="top", transform=ax.transAxes, weight="bold")


def draw_panel(ax, rider_label, records, basins, vd, merges, centroid=None) -> None:
    """Monospace ledger: verdict, per-basin geometry, consensus fin, anomalies."""
    ax.set_facecolor(_PANEL)
    ax.axis("off")
    n = vd["n_valid"]
    multimodal = vd["n_basins"] > 1
    head_color = _ORANGE if multimodal else _CYAN
    lines: list[tuple[str, str]] = []
    tag = "MULTIMODAL" if multimodal else "UNIMODAL"
    lines.append((f"{tag}: {vd['n_basins']} basin(s) over {n} restarts", head_color))
    lines.append((f"global best {vd['global_best']:.3f}  worst {vd['worst']:.3f}"
                  f"  spread {vd['spread']:.3f}", _MUTED))
    lines.append((f"within 5% of best: {vd['n_within_5pct']}/{n}"
                  f" ({100.0 * vd['frac_within_5pct']:.0f}%)", _MUTED))
    tfate = ("global basin" if vd["template_found_global"]
             else f"basin {vd['template_basin_rank']}")
    lines.append((f"template start #0 -> {tfate}",
                  _CYAN if vd["template_found_global"] else _ORANGE))
    lines.append(("", _INK))
    lines.append((f"{'basin':<6}{'n':>4}{'obj':>8}{'depth':>7}{'base':>6}"
                  f"{'sweep':>6}{'t/c':>6}{'AR':>6}", _MUTED))
    for b in basins:
        g = b["geom"]
        lines.append((f"{b['rank']:<6}{b['count']:>4}{b['best_obj']:>8.3f}"
                      f"{g['depth']:>7.0f}{g['base']:>6.0f}{g['sweep']:>6.0f}"
                      f"{g['t_c']:>6.3f}{b['aspect_ratio']:>6.2f}",
                      _basin_color(b["rank"])))
    if centroid is not None:
        gc = centroid["global"]
        if gc.get("objective") is None:
            lines.append(("consensus fin (all-run avg): UNDECODABLE", _ORANGE))
        else:
            state = "FEASIBLE" if gc["feasible"] else "INFEASIBLE"
            lines.append((f"consensus fin (all-run avg): obj {gc['objective']:.3f}"
                          f" {state}  ({gc['vs_best_pct']:+.0f}% vs best)",
                          _WHITE if gc["viable"] else _ORANGE))
    lines.append(("", _INK))
    flat = ", ".join(vd["flat_sliders"]) or "none"
    lines.append((f"flat/unidentified sliders: {flat}", _ORANGE if vd["flat_sliders"] else _MUTED))
    lines.append((f"clustered on: {', '.join(vd['ident_sliders'])}", _MUTED))
    lines.append(("", _INK))
    lines.append(("anomalies", _MUTED))
    lines.append((f"  crashed {vd['n_crashed']}   infeasible finals "
                  f"{vd['n_infeasible']}", _MUTED))
    gap = "n/a"
    if merges:
        below = [d for d in merges if d < _CLUSTER_THRESHOLD]
        above = [d for d in merges if d >= _CLUSTER_THRESHOLD]
        if below and above:
            gap = f"{max(below):.3f} | {min(above):.3f}"
    lines.append((f"  merge dist around thr {_CLUSTER_THRESHOLD}: {gap}", _MUTED))
    for b in basins:
        if b["cornered"]:
            lines.append((f"  basin {b['rank']} corners: "
                          f"{','.join(b['cornered'])}", _basin_color(b["rank"])))
    y = 0.99
    for text, color in lines:
        ax.text(0.0, y, text, color=color, fontsize=8.2, family="monospace",
                va="top", transform=ax.transAxes)
        y -= 0.045
    ax.set_title(rider_label, color=_INK, fontsize=11, family="monospace",
                 loc="left")


def render_corner(out_png: Path, rider_label: str, records, basins, vd,
                  n_starts, budget, seed, centroid=None) -> None:
    """Full corner atlas: lower-triangle grid of all 28 pairwise projections of
    the 8 normalized level-1 sliders, plus a per-slider start->final slope chart
    on the diagonal. Grey start dot -> basin-colored final dot in every panel,
    global best circled orange, the parameter centroid (average fin) a white
    star. The complete companion to the main sheet's three curated projections."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    valid = [r for r in records if r.get("error") is None]
    global_idx = basins[0]["representative_idx"]
    gb = records[global_idx]
    n = _N_SLIDERS
    names = _SLIDER_NAMES
    cs = centroid["global"]["sliders"] if centroid else None

    fig = plt.figure(figsize=(2.85 * n, 2.9 * n), facecolor=_BG)
    fig.text(0.5, 0.985, "T-FINS multistart — full corner atlas", color=_INK,
             fontsize=26, family="monospace", ha="center", weight="bold")
    fig.text(0.5, 0.973,
             f"{rider_label}   ·   all 28 pairwise + 8 diagonal slider projections"
             f"   ·   normalized [0,1] axes   ·   {n_starts} starts   ·   "
             f"budget {budget}   ·   seed {seed}",
             color=_MUTED, fontsize=14, family="monospace", ha="center")

    gs = fig.add_gridspec(n, n, left=0.055, right=0.995, top=0.955, bottom=0.045,
                          hspace=0.12, wspace=0.12)
    for r in range(n):
        for c in range(r + 1):
            ax = fig.add_subplot(gs[r, c])
            ax.set_facecolor(_PANEL)
            if c == r:  # diagonal: per-slider start -> final slope chart
                for rec in valid:
                    color = _basin_color(rec.get("basin_rank"))
                    s, f = rec["start"][r], rec["final_sliders"][r]
                    ax.plot([0.0, 1.0], [s, f], color=color, lw=0.8, alpha=0.5, zorder=3)
                    ax.scatter([0.0], [s], s=8, c=_GREY, zorder=4, edgecolors="none")
                    ax.scatter([1.0], [f], s=14, c=color, zorder=5, edgecolors=_BG,
                               linewidths=0.4)
                ax.scatter([1.0], [gb["final_sliders"][r]], s=80, facecolors="none",
                           edgecolors=_ORANGE, linewidths=1.6, zorder=6)
                if cs is not None:
                    ax.scatter([1.0], [cs[r]], s=90, marker="*", c=_WHITE, zorder=7,
                               edgecolors=_BG, linewidths=0.4)
                ax.set_xlim(-0.3, 1.3)
                ax.set_xticks([0.0, 1.0])
                if r == n - 1:
                    ax.set_xticklabels(["start", "final"], fontsize=6, color=_MUTED)
                else:
                    ax.set_xticklabels([])
            else:  # off-diagonal: slider c (x) vs slider r (y), start -> final
                for rec in valid:
                    color = _basin_color(rec.get("basin_rank"))
                    sx, sy = rec["start"][c], rec["start"][r]
                    fx, fy = rec["final_sliders"][c], rec["final_sliders"][r]
                    ax.annotate("", xy=(fx, fy), xytext=(sx, sy),
                                arrowprops=dict(arrowstyle="-|>", color=color,
                                                alpha=0.38, lw=0.6, shrinkA=1, shrinkB=1.5))
                    ax.scatter([sx], [sy], s=7, c=_GREY, zorder=3, edgecolors="none")
                    ax.scatter([fx], [fy], s=15, c=color, zorder=4, edgecolors=_BG,
                               linewidths=0.4)
                ax.scatter([gb["final_sliders"][c]], [gb["final_sliders"][r]], s=90,
                           facecolors="none", edgecolors=_ORANGE, linewidths=1.6, zorder=5)
                if cs is not None:
                    ax.scatter([cs[c]], [cs[r]], s=95, marker="*", c=_WHITE, zorder=6,
                               edgecolors=_BG, linewidths=0.4)
                ax.set_xlim(-0.05, 1.05)
                ax.set_xticks([0.0, 0.5, 1.0])
                ax.set_xticklabels(["0", "", "1"] if r == n - 1 else [], fontsize=6)
            ax.set_ylim(-0.05, 1.05)
            ax.set_yticks([0.0, 0.5, 1.0])
            ax.set_yticklabels(["0", "", "1"] if c == 0 else [], fontsize=6)
            ax.tick_params(colors=_MUTED, labelsize=6, length=2)
            ax.grid(color=_GRID, lw=0.4)
            for sp in ax.spines.values():
                sp.set_color("#2a333b")
            if r == n - 1:
                ax.set_xlabel(names[c], color=_INK, fontsize=10, family="monospace")
            if c == 0:
                ax.set_ylabel(names[r], color=_INK, fontsize=10, family="monospace")

    # Legend + reading guide in the empty upper-right triangle.
    ax_i = fig.add_subplot(gs[0:4, 4:8])
    ax_i.axis("off")
    tag = "UNIMODAL" if vd["n_basins"] == 1 else f"MULTIMODAL — {vd['n_basins']} basins"
    guide = [
        (tag, _CYAN if vd["n_basins"] == 1 else _ORANGE, 15),
        ("", _INK, 6),
        ("grey dot = start   arrow -> colored dot = final", _MUTED, 12),
        ("color = basin      orange ring = global best", _MUTED, 12),
        ("white star = parameter centroid (average fin)", _WHITE, 12),
        ("diagonal = that slider's start->final migration", _MUTED, 12),
        ("", _INK, 6),
    ]
    y = 0.98
    for text, color, fs in guide:
        ax_i.text(0.0, y, text, color=color, fontsize=fs, family="monospace",
                  va="top", transform=ax_i.transAxes)
        y -= 0.05 if text else 0.026
    for b in basins:
        ax_i.text(0.0, y, "  ■", color=_basin_color(b["rank"]), fontsize=13,
                  family="monospace", va="top", transform=ax_i.transAxes)
        ax_i.text(0.07, y, f" basin {b['rank']}: {b['count']}/{vd['n_valid']} runs  "
                  f"obj {b['best_obj']:.3f}", color=_INK, fontsize=12,
                  family="monospace", va="top", transform=ax_i.transAxes)
        y -= 0.045
    y -= 0.02
    if centroid is not None:
        gc = centroid["global"]
        cls = {"consensus": [], "split": [], "flat": []}
        for p in centroid["params"]:
            cls[p["class"]].append(p["slider"])
        if gc.get("objective") is None:
            ax_i.text(0.0, y, "consensus fin (average): UNDECODABLE", color=_ORANGE,
                      fontsize=12, family="monospace", va="top", transform=ax_i.transAxes)
        else:
            state = "feasible" if gc["feasible"] else "INFEASIBLE"
            ax_i.text(0.0, y, f"consensus fin (average): obj {gc['objective']:.3f} "
                      f"{state} ({gc['vs_best_pct']:+.0f}% vs best)",
                      color=_WHITE if gc["viable"] else _ORANGE, fontsize=12,
                      family="monospace", va="top", transform=ax_i.transAxes)
        y -= 0.05
        for label, key, col in (("consensus", "consensus", _CYAN),
                                ("split/bimodal", "split", _ORANGE),
                                ("flat/free", "flat", _MUTED)):
            ax_i.text(0.0, y, f"  {label}: {', '.join(cls[key]) or 'none'}",
                      color=col, fontsize=11, family="monospace", va="top",
                      transform=ax_i.transAxes)
            y -= 0.042

    fig.savefig(out_png, dpi=100, facecolor=_BG)
    plt.close(fig)


def render_sheet(out_png: Path, rider_label: str, records, basins, vd, merges,
                 config, n_starts, budget, seed, wall_s, centroid=None) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    starts_geom = {r["idx"]: start_geom(r["start"], config) for r in records}
    global_idx = basins[0]["representative_idx"]
    n_valid = vd["n_valid"]
    cgeom = centroid["global"].get("geom") if centroid else None

    fig = plt.figure(figsize=(18.0, 15.5), facecolor=_BG)
    fig.text(0.5, 0.982, "T-FINS optimizer — multistart convergence study",
             color=_INK, fontsize=22, family="monospace", ha="center", weight="bold")
    fig.text(0.5, 0.962,
             f"{rider_label}   ·   {n_starts} starts (LHS + template)   ·   "
             f"budget {budget} evals/restart   ·   base seed {seed}",
             color=_MUTED, fontsize=13, family="monospace", ha="center")

    gs = fig.add_gridspec(3, 6, left=0.05, right=0.975, top=0.93, bottom=0.05,
                          hspace=0.30, wspace=0.55,
                          height_ratios=[1.05, 0.72, 1.15])
    projections = (("depth", "sweep", "depth (mm)", "sweep (deg)"),
                   ("base", "t_c", "base (mm)", "t/c"),
                   ("tipw", "le_full", "tip width ratio", "le fullness"))
    for i, (xk, yk, xl, yl) in enumerate(projections):
        draw_cloud(fig.add_subplot(gs[0, 2 * i:2 * i + 2]), records, starts_geom,
                   config, global_idx, xk, yk, xl, yl, cgeom)
    draw_ladder(fig.add_subplot(gs[1, 0:6]), records, vd["global_best"])
    draw_gallery(fig.add_subplot(gs[2, 0:3]), records, basins, n_valid,
                 centroid["global"] if centroid else None)
    draw_panel(fig.add_subplot(gs[2, 3:6]), rider_label, records, basins, vd,
               merges, centroid)

    unimodal = vd["n_basins"] == 1
    if unimodal:
        verdict_line = "VERDICT: UNIMODAL — all restarts reach one global basin"
    else:
        verdict_line = f"VERDICT: MULTIMODAL — {vd['n_basins']} distinct basins"
    fig.text(0.5, 0.016,
             f"total evals {vd['total_evals']:,}   ·   wall {wall_s:.0f} s   ·   "
             f"{verdict_line}",
             color=_INK if unimodal else _ORANGE, fontsize=13,
             family="monospace", ha="center", weight="bold")
    fig.savefig(out_png, dpi=115, facecolor=_BG)
    plt.close(fig)


# --- driver ------------------------------------------------------------------


def study_rider(slug: str, label: str, rider: RiderSpec, out_prefix: Path,
                n_starts: int, budget: int, seed: int) -> dict:
    starts = make_starts(n_starts, rider.config, seed)
    tasks = [(i, rider, x0, budget, seed + i) for i, x0 in enumerate(starts)]

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(_run_start, tasks))
    wall_s = time.time() - t0
    records.sort(key=lambda r: r["idx"])

    basins, merges, flat_idx, iqr = cluster_basins(records)
    vd = verdict(records, basins)
    vd["flat_sliders"] = [_SLIDER_NAMES[i] for i in flat_idx]
    vd["ident_sliders"] = [n for i, n in enumerate(_SLIDER_NAMES) if i not in flat_idx]
    vd["slider_iqr"] = {n: iqr[i] for i, n in enumerate(_SLIDER_NAMES)}
    centroid = centroid_analysis(rider, records, basins, vd["flat_sliders"])

    png = out_prefix.with_name(f"{out_prefix.name}-{slug}.png")
    render_sheet(png, label, records, basins, vd, merges, rider.config,
                 n_starts, budget, seed, wall_s, centroid)
    corner = out_prefix.with_name(f"{out_prefix.name}-{slug}-corner.png")
    render_corner(corner, label, records, basins, vd, n_starts, budget, seed,
                  centroid)

    payload = {
        "rider": {"weight_kg": rider.weight_kg, "skill": rider.skill.name,
                  "config": rider.config.value, "material": rider.material,
                  "speed_ms": rider.speed},
        "study": {"n_starts": n_starts, "budget": budget, "seed": seed,
                  "cluster_threshold": _CLUSTER_THRESHOLD, "iqr_flat": _IQR_FLAT,
                  "clustered_on": vd["ident_sliders"],
                  "flat_sliders": vd["flat_sliders"], "wall_s": wall_s},
        "verdict": vd,
        "merge_distances": merges,
        "basins": basins,
        "centroid": centroid,
        "restarts": records,
    }
    js = out_prefix.with_name(f"{out_prefix.name}-{slug}.json")
    js.write_text(json.dumps(payload, indent=2) + "\n")

    tag = "UNIMODAL" if vd["n_basins"] == 1 else f"MULTIMODAL ({vd['n_basins']})"
    print(f"[{slug}] {tag}  best {vd['global_best']:.3f}  worst {vd['worst']:.3f}"
          f"  spread {vd['spread']:.3f}  within5% {vd['n_within_5pct']}/{vd['n_valid']}"
          f"  template->basin {vd['template_basin_rank']}"
          f"  crashed {vd['n_crashed']}  {wall_s:.0f}s", flush=True)
    print(f"    flat/unidentified sliders (roam free at ~const obj): "
          f"{', '.join(vd['flat_sliders']) or 'none'}"
          f"   |   clustered on: {', '.join(vd['ident_sliders'])}", flush=True)
    for b in basins:
        g = b["geom"]
        cstr = f"  corners {','.join(b['cornered'])}" if b["cornered"] else ""
        print(f"    basin {b['rank']}: {b['count']}/{vd['n_valid']} runs  "
              f"obj {b['best_obj']:.3f}  depth {g['depth']:.0f} base {g['base']:.0f} "
              f"sweep {g['sweep']:.0f} t/c {g['t_c']:.3f} AR {b['aspect_ratio']:.2f}"
              f"  feas {b['feasible_count']}/{b['count']}{cstr}", flush=True)
    gc = centroid["global"]
    cls = {k: [p["slider"] for p in centroid["params"] if p["class"] == k]
           for k in ("consensus", "split", "flat")}
    if gc.get("objective") is None:
        print("    consensus fin (all-run average): UNDECODABLE", flush=True)
    else:
        print(f"    consensus fin (all-run average): obj {gc['objective']:.3f} "
              f"{'FEASIBLE' if gc['feasible'] else 'INFEASIBLE'} "
              f"({gc['vs_best_pct']:+.0f}% vs best, "
              f"{gc.get('vs_best_l1_pct', 0.0):+.0f}% vs best level-1)  "
              f"depth {gc['geom']['depth']:.0f} base {gc['geom']['base']:.0f} "
              f"t/c {gc['geom']['t_c']:.3f}", flush=True)
    print(f"    params  consensus: {', '.join(cls['consensus']) or 'none'}  |  "
          f"split: {', '.join(cls['split']) or 'none'}  |  "
          f"flat: {', '.join(cls['flat']) or 'none'}", flush=True)
    for pb in centroid["per_basin"]:
        if pb.get("objective") is not None and pb.get("basin_best_l1") is not None:
            print(f"    basin {pb['rank']} centroid: obj {pb['objective']:.3f}  "
                  f"vs basin best level-1 {pb['basin_best_l1']:.3f}  "
                  f"beats {pb['beats_basin_best']}", flush=True)
    print(f"    wrote {png} , {corner} , {js}", flush=True)
    return payload


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out_prefix = Path(sys.argv[1])
    n_starts = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    print(f"multistart: {n_starts} starts x {budget} evals x {len(RIDERS)} riders,"
          f" base seed {seed}", flush=True)
    for slug, label, rider in RIDERS:
        study_rider(slug, label, rider, out_prefix, n_starts, budget, seed)


if __name__ == "__main__":
    main()
