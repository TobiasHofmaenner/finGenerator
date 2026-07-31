"""Rank a multistart's seeds, cluster them, and export ranked STLs + a sheet.

WHY CLUSTER AT ALL. A multistart's headline is "the best objective found", which
says nothing about whether that optimum is REAL. Sixteen seeds landing in one
basin is evidence; sixteen landing in sixteen basins means the search is
sampling a plateau and the winner is whichever seed got lucky. Only the second
question tells you how much to trust the number, and it is invisible in a
ledger of scalars — you have to compare the DESIGNS.

DISTANCE. Fins are compared in the optimizer's own slider space, normalized by
each slider's range, so a millimetre of depth and a hundredth of t/c count
according to how much of the search box each spends. Comparing raw parameters
would let `depth` (40-300 mm) drown every other axis.

Two designs are "the same" below CLUSTER_EPS mean normalized distance. That
threshold is a judgement call and is reported alongside the count, because the
cluster count is meaningless without it.

Outputs, into <result-dir>/ranked/:
    01-side.stl / 01-center.stl ... ranked by set objective, 01 = best
    ranked-summary.png          one sheet: every design overlaid + the table
    ranked.json                 the ledger with cluster ids and distances

Usage: uv run python scripts/rank_seeds.py <result-dir> [--top N] [--eps 0.05]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fingen.check import check_solid  # noqa: E402
from fingen.export import to_stl  # noqa: E402
from fingen.loft import fin_solid  # noqa: E402
from fingen.optimize import fin_from_dict  # noqa: E402
from fingen.outline import planform  # noqa: E402
from fingen.params import DEFAULT_SETTINGS, TabParams, TabSystem  # noqa: E402

_BG, _FG, _GRID = "#0b0e11", "#d7dee6", "#243040"
CLUSTER_EPS = 0.05

# The axes a design is compared on, with the span used to normalize each. These
# mirror optimize._SLIDER_BOUNDS; kept explicit so a bounds change shows up as a
# visible edit here rather than silently rescaling every past comparison.
_AXES: tuple[tuple[str, str, float, float], ...] = (
    ("outline", "depth", 40.0, 300.0),
    ("outline", "base", 40.0, 250.0),
    ("outline", "sweep", 0.0, 60.0),
    ("outline", "tip_width_ratio", 0.05, 0.6),
    ("outline", "le_fullness", 0.0, 1.0),
    ("outline", "te_shape", -1.0, 1.0),
    ("foil", "thickness_ratio", 0.04, 0.15),
    ("_root", "thickness_tip_factor", 0.5, 1.2),
)


def _vec(fd: dict) -> np.ndarray:
    out = []
    for group, key, lo, hi in _AXES:
        raw = fd.get(key) if group == "_root" else fd.get(group, {}).get(key)
        out.append(((raw if raw is not None else lo) - lo) / (hi - lo))
    return np.array(out)


def _outline_xy(fin):
    z, x_le, chord = planform(fin.outline)
    return (np.concatenate([x_le, (x_le + chord)[::-1], x_le[:1]]),
            np.concatenate([z, z[::-1], z[:1]]))


def cluster(vecs: list[np.ndarray], eps: float) -> list[int]:
    """Single-link agglomeration: a design joins a cluster if it is within eps
    of ANY member. Single-link (not centroid) because a plateau shows up as a
    chain of near-identical designs, and a centroid rule would split it
    arbitrarily at the ends."""
    ids = [-1] * len(vecs)
    nxt = 0
    for i in range(len(vecs)):
        if ids[i] >= 0:
            continue
        ids[i] = nxt
        stack = [i]
        while stack:
            a = stack.pop()
            for j in range(len(vecs)):
                if ids[j] < 0 and float(np.abs(vecs[a] - vecs[j]).mean()) < eps:
                    ids[j] = nxt
                    stack.append(j)
        nxt += 1
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("result_dir", type=Path)
    ap.add_argument("--top", type=int, default=0, help="export only the best N STLs (0 = all)")
    ap.add_argument("--eps", type=float, default=CLUSTER_EPS)
    ap.add_argument("--no-stl", action="store_true", help="sheet only, skip geometry")
    args = ap.parse_args()

    seeds = sorted((args.result_dir / "seeds").glob("seed-*.json"))
    if not seeds:
        raise SystemExit(f"no seeds under {args.result_dir}/seeds")
    runs = []
    for p in seeds:
        d = json.loads(p.read_text())
        runs.append({"seed": int(p.stem.split("-")[1]), "path": p, "d": d,
                     "obj": d["set"]["objective"], "feasible": d["set"]["feasible"]})
    runs.sort(key=lambda r: (not r["feasible"], r["obj"]))

    vecs = [_vec(r["d"]["fin"]) for r in runs]
    cids = cluster(vecs, args.eps)
    best = vecs[0]
    for r, c, v in zip(runs, cids, vecs, strict=True):
        r["cluster"] = c
        r["dist_to_best"] = float(np.abs(v - best).mean())

    # BASIN COUNT vs EPS. One threshold gives one number and hides how fragile
    # it is: designs 0.086 apart are "different" at eps 0.05 and "the same" at
    # 0.12. Reporting the sweep is the honest form of the answer, and the shape
    # of it is itself diagnostic — a sharp drop means real basins separated by a
    # gap, a gradual slide means a plateau with no basins at all.
    eps_sweep = [(e, len(set(cluster(vecs, e)))) for e in
                 (0.02, 0.03, 0.05, 0.08, 0.12, 0.20)]

    sizes: dict[int, int] = {}
    for c in cids:
        sizes[c] = sizes.get(c, 0) + 1
    # Rank clusters by their best member so cluster 1 is the winning basin.
    order = {c: i + 1 for i, c in enumerate(dict.fromkeys(cids))}
    for r in runs:
        r["basin"] = order[r["cluster"]]
        r["basin_size"] = sizes[r["cluster"]]

    out = args.result_dir / "ranked"
    out.mkdir(parents=True, exist_ok=True)

    # --- ranked STLs ------------------------------------------------------
    export = runs if args.top == 0 else runs[: args.top]
    if not args.no_stl:
        tabs = TabParams(system=TabSystem(runs[0]["d"]["rider"]["tabs"]),
                         fit_offset=-0.2, click_indent_depth=0.0)
        for rank, r in enumerate(export, 1):
            for slot, key in (("side", "fin"), ("center", "center_fin")):
                if not r["d"].get(key):
                    continue
                fin = dataclasses.replace(fin_from_dict(r["d"][key]), tabs=tabs)
                try:
                    part = fin_solid(fin, DEFAULT_SETTINGS)
                    rep = check_solid(part, fin, DEFAULT_SETTINGS)
                    to_stl(part, out / f"{rank:02d}-{slot}.stl")
                    r[f"{slot}_solid"] = "OK" if rep.ok else "check_solid: " + "; ".join(rep.issues)
                except Exception as exc:  # noqa: BLE001 — a bad loft must not kill the sheet
                    r[f"{slot}_solid"] = f"{type(exc).__name__}: {exc}"
            print(f"  {rank:02d}  seed {r['seed']:3d}  obj {r['obj']:.5f}  "
                  f"basin {r['basin']}  {r.get('side_solid', '-')}", flush=True)

    # --- the sheet --------------------------------------------------------
    n_show = min(len(runs), 24)
    fig = plt.figure(figsize=(17, 8.4), facecolor=_BG)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.0, 1.5], wspace=0.28)

    ax = fig.add_subplot(gs[0, 0], facecolor=_BG)
    cmap = plt.get_cmap("turbo")
    nb = max(r["basin"] for r in runs)
    for r in runs[:n_show][::-1]:
        fin = fin_from_dict(r["d"]["fin"])
        x, y = _outline_xy(fin)
        first = r["basin"] not in [q["basin"] for q in runs[: runs.index(r)]]
        ax.plot(x, y, lw=2.2 if r is runs[0] else 0.9,
                color=cmap((r["basin"] - 1) / max(nb - 1, 1)),
                alpha=1.0 if r is runs[0] else 0.55,
                label=f"basin {r['basin']} (n={r['basin_size']})" if first else None)
    ax.set_aspect("equal")
    ax.set_title(f"all {len(runs)} seeds, coloured by basin", color=_FG, fontsize=10)
    ax.set_xlabel("chord [mm]", color=_FG, fontsize=8)
    ax.set_ylabel("span [mm]", color=_FG, fontsize=8)
    ax.legend(facecolor=_BG, edgecolor=_GRID, labelcolor=_FG, fontsize=6.5, loc="best")

    ax2 = fig.add_subplot(gs[0, 1], facecolor=_BG)
    objs = [r["obj"] for r in runs]
    ax2.scatter(range(1, len(runs) + 1), objs,
                c=[cmap((r["basin"] - 1) / max(nb - 1, 1)) for r in runs], s=26)
    ax2.set_xlabel("rank", color=_FG, fontsize=8)
    ax2.set_ylabel("set objective (lower = better)", color=_FG, fontsize=8)
    ax2.set_title("convergence spread", color=_FG, fontsize=10)

    ax3 = fig.add_subplot(gs[0, 2], facecolor=_BG)
    ax3.axis("off")
    hdr = (f"{'#':>3} {'seed':>5} {'objective':>10} {'basin':>6} {'dist':>7} "
           f"{'area':>7} {'SF':>5} {'tab':>5}")
    lines = [f"{runs[0]['d']['rider']['weight_kg']:.0f} kg  "
             f"{runs[0]['d']['rider']['skill']}  {runs[0]['d']['rider']['material']}  "
             f"{runs[0]['d']['rider']['tabs']}", "",
             f"{len(runs)} seeds -> {nb} basins at eps={args.eps}",
             "  basins vs eps: " + "  ".join(f"{e:.2f}:{n}" for e, n in eps_sweep),
             ""]
    lines.append(hdr)
    for rank, r in enumerate(runs[:n_show], 1):
        m = r["d"]["margins"]
        lines.append(f"{rank:>3} {r['seed']:>5} {r['obj']:>10.5f} {r['basin']:>6} "
                     f"{r['dist_to_best']:>7.3f} {m['area_mm2']:>7.0f} "
                     f"{m['stress_sf_roll']:>5.2f} {m['tab_sf']:>5.2f}")
    if len(runs) > n_show:
        lines.append(f"    ... {len(runs) - n_show} more")
    ax3.text(0.0, 1.0, "\n".join(lines), transform=ax3.transAxes, va="top",
             family="monospace", fontsize=8, color=_FG)

    for a in (ax, ax2):
        a.tick_params(colors=_FG, labelsize=7)
        for sp in a.spines.values():
            sp.set_color(_GRID)
        a.grid(color=_GRID, lw=0.5, alpha=0.5)
    fig.suptitle(f"{args.result_dir.name} — multistart, ranked", color=_FG, fontsize=12)
    fig.savefig(out / "ranked-summary.png", dpi=125, facecolor=_BG, bbox_inches="tight")

    (out / "ranked.json").write_text(json.dumps(
        {"eps": args.eps, "n_seeds": len(runs), "n_basins": nb,
         "basins_vs_eps": eps_sweep,
         "runs": [{k: v for k, v in r.items() if k not in ("d", "path")} for r in runs]},
        indent=2, default=str) + "\n")
    print(f"\n{len(runs)} seeds -> {nb} basins at eps={args.eps}")
    print("  basins vs eps: " + "  ".join(f"{e:.2f}->{n}" for e, n in eps_sweep))
    print(f"  largest basin: {max(sizes.values())} seeds")
    print(f"wrote {out}/ranked-summary.png and ranked.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
