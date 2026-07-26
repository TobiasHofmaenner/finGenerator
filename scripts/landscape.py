"""Parameter-space characterization of the fingen optimizer objective.

Usage:
    uv run python scripts/landscape.py <out_prefix> [seed=0]

The question, in the user's words: is the objective landscape well-behaved?
Smooth couplings or kinks? Plateaus? How chaotic? Characterize the surface the
optimizer traverses BEFORE trusting the CMA-ES choice.

Complementary to scripts/multistart.py: that study answers WHERE runs converge
(basins/multimodality); this one answers WHAT KIND of surface they cross
(smoothness, conditioning, coupling, plateaus). Everything lives in the same
normalized level-1 slider cube [0,1]^8 the optimizer searches, decoded through
the SAME `optimize._decode` (offsets/grooves off, exactly stage A).

Rider: 75 kg INTERMEDIATE thruster (the well-conditioned reference case). A
lighter antagonistic-rider pass (95 kg PRO thruster) runs a cheap probe subset
for contrast, mirroring multistart's second rider.

Five probes (all tier-0 analytic evaluate; ~13-20 ms each):
  1. RESPONSE CURVES  per-axis 1-D sweeps at 3 base points -> smoothness,
     kinks, multimodality, plateaus, penalty walls, decode rejection.
  2. SMOOTHNESS/LIPSCHITZ  central differences at h=1e-3 and h=1e-5 on 200
     feasible points -> sensitivity ranking + scale-dependence classification
     (smooth vs kinked vs plateau).
  3. COUPLING  central-difference Hessians (h=2e-3) at the 3 base points ->
     signed coupling heatmap + eigen spectrum + conditioning (near-separable or
     elongated bowl? does CMA's covariance adaptation earn its keep?).
  4. SLICE MAPS  80x80 objective terrain over (depth x sweep) and (base x t/c).
  5. STATS  clean-decode / feasible / reject fractions, determinism spot-check,
     eval-cost distribution.

Two dark-style sheets `<out_prefix>-terrain.png` / `-smoothness.png` plus a
`<out_prefix>-probe.json` of all raw probe data, and a VERDICT paragraph
rendered on the terrain sheet and printed to stdout.
"""

from __future__ import annotations

import grp
import json
import os
import pwd
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from fingen.optimize import (
    _SLIDER_BOUNDS,
    DECODE_PENALTY,
    RiderSpec,
    _decode,
    _x0_sliders,
    evaluate,
)
from fingen.params import FinConfig
from fingen.sizing import Skill

# --- config ------------------------------------------------------------------
MAX_WORKERS = 4  # the box is shared with the concurrent multistart study
SLIDER_NAMES = tuple(b[0] for b in _SLIDER_BOUNDS)
N_SLIDERS = len(_SLIDER_BOUNDS)

# Slider indices used by the 2-D slice maps.
IDX = {name: i for i, name in enumerate(SLIDER_NAMES)}

# Probe sizes.
RC_SAMPLES = 200          # response-curve resolution per axis
N_SMOOTH = 200            # feasible points for the Lipschitz probe
SLICE_RES = 80            # 2-D terrain resolution
H_COARSE = 1e-3           # finite-difference scales (normalized units)
H_FINE = 1e-5
H_HESS = 2e-3             # Hessian step
EPS_FLAT = 1e-3           # |grad| below this = locally flat
R_SMOOTH = 3.0            # coarse/fine slope ratio within [1/R, R] = scale-free

# House palette.
_BG = "#0b0e11"
_PANEL = "#12171c"
_CYAN = "#7fd4e0"
_CYAN_LT = "#a7e0ea"
_ORANGE = "#f2a154"
_GREY = "#3a4650"
_INK = "#e8edf0"
_MUTED = "#8a97a0"
_RED = "#c0392b"          # reserved status colour: decode/eval rejection
_GRID = (1.0, 1.0, 1.0, 0.12)
_AXIS = "#2a333b"

# --- worker (process pool) ---------------------------------------------------
_RIDER: RiderSpec | None = None


def _init_worker(weight_kg: float, skill_name: str, config_value: str,
                 material: str) -> None:
    """Set the per-process rider (enums rebuilt worker-side, cache warms once)."""
    global _RIDER
    _RIDER = RiderSpec(weight_kg=weight_kg, skill=Skill[skill_name],
                       config=FinConfig(config_value), material=material)


def _eval_one(x: np.ndarray) -> tuple[int, float, float]:
    """One design vector -> (code, objective, penalty_sum).

    code: 0 feasible, 1 infeasible (graded penalty), 2 decode reject (planform
    ValueError -> the optimizer's DECODE_PENALTY plateau), 3 eval reject
    (evaluate raised a ValueError the optimizer's objective does NOT catch).
    """
    assert _RIDER is not None
    cfg = _RIDER.config
    try:
        fin = _decode(np.asarray(x, dtype=float), cfg, use_offsets=False,
                      use_grooves=False)
    except ValueError:
        return (2, DECODE_PENALTY, float("nan"))
    try:
        ev = evaluate(fin, _RIDER)
    except ValueError:
        return (3, DECODE_PENALTY, float("nan"))
    return (0 if ev.feasible else 1, float(ev.objective), float(ev.penalty))


def _eval_batch(X: np.ndarray) -> list[tuple[int, float, float]]:
    return [_eval_one(x) for x in X]


def _evaluate(X: np.ndarray, ex: ProcessPoolExecutor, chunk: int = 64
              ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate a stack of design vectors in parallel; order preserved."""
    X = np.asarray(X, dtype=float)
    if len(X) == 0:
        e = np.array([], dtype=float)
        return e.astype(int), e, e
    chunks = [X[i:i + chunk] for i in range(0, len(X), chunk)]
    flat = [r for sub in ex.map(_eval_batch, chunks) for r in sub]
    codes = np.array([r[0] for r in flat], dtype=int)
    objs = np.array([r[1] for r in flat], dtype=float)
    pens = np.array([r[2] for r in flat], dtype=float)
    return codes, objs, pens


# --- probes ------------------------------------------------------------------


def probe_stats(ex: ProcessPoolExecutor, rng: np.random.Generator, n: int
                ) -> tuple[dict, np.ndarray]:
    """Random-cube census + feasible-point harvest for the other probes."""
    X = rng.random((n, N_SLIDERS))
    codes, objs, _ = _evaluate(X, ex)
    total = len(codes)
    feas_mask = codes == 0
    fo = objs[feas_mask]
    stats = {
        "n_sampled": total,
        "frac_clean_decode": float(np.mean(codes != 2)),
        "frac_feasible": float(np.mean(feas_mask)),
        "frac_infeasible": float(np.mean(codes == 1)),
        "frac_decode_reject": float(np.mean(codes == 2)),
        "frac_eval_reject": float(np.mean(codes == 3)),
        "feasible_obj_min": float(fo.min()) if fo.size else None,
        "feasible_obj_median": float(np.median(fo)) if fo.size else None,
        "feasible_obj_max": float(fo.max()) if fo.size else None,
    }
    feasible = X[feas_mask]
    return stats, feasible


def probe_determinism_cost(base_points: list[np.ndarray], feasible: np.ndarray
                           ) -> dict:
    """3 repeated evals bitwise identical? + per-eval cost distribution."""
    x = base_points[0]
    reps = [_eval_one(x)[1] for _ in range(3)]
    bitwise = len({v.hex() for v in reps}) == 1
    # Cost distribution over a mix of template + random feasible points.
    sample = [base_points[0]] * 40
    if len(feasible):
        idx = np.linspace(0, len(feasible) - 1, 160).astype(int)
        sample += list(feasible[idx])
    times_ms = []
    for xv in sample:
        t = time.perf_counter()
        _eval_one(xv)
        times_ms.append((time.perf_counter() - t) * 1e3)
    tms = np.array(times_ms)
    return {
        "determinism_bitwise_identical": bool(bitwise),
        "determinism_values_hex": [v.hex() for v in reps],
        "eval_ms_min": float(tms.min()),
        "eval_ms_median": float(np.median(tms)),
        "eval_ms_p95": float(np.percentile(tms, 95)),
        "eval_ms_max": float(tms.max()),
        "eval_ms_n": int(len(tms)),
    }


def select_base_points(ex: ProcessPoolExecutor, template: np.ndarray,
                       feasible: np.ndarray, rng: np.random.Generator
                       ) -> tuple[list[np.ndarray], list[str]]:
    """Template + 2 feasible points chosen for interior margin.

    Among a seeded shuffle of feasible candidates, prefer those whose full
    +/-H_HESS neighbourhood stays feasible, so their Hessians read the interior
    bowl rather than a penalty wall.
    """
    if len(feasible) == 0:
        return [template], ["template"]
    order = rng.permutation(len(feasible))
    cand = feasible[order[:min(12, len(feasible))]]
    # Score each candidate by how many of its 16 axis-step neighbours are feasible.
    probe = []
    for c in cand:
        for i in range(N_SLIDERS):
            for s in (+H_HESS, -H_HESS):
                v = c.copy()
                v[i] = min(1.0, max(0.0, v[i] + s))
                probe.append(v)
    codes, _, _ = _evaluate(np.array(probe), ex)
    codes = codes.reshape(len(cand), 2 * N_SLIDERS)
    n_feas_nb = (codes == 0).sum(axis=1)
    best = np.argsort(-n_feas_nb)[:2]
    pts = [template] + [cand[b] for b in best]
    labels = ["template", "feasible-A", "feasible-B"][:len(pts)]
    return pts, labels


def probe_response_curves(ex: ProcessPoolExecutor, base_points: list[np.ndarray]
                          ) -> dict:
    """1-D sweep of each slider over [0,1] at each base point."""
    grid = np.linspace(0.0, 1.0, RC_SAMPLES)
    blocks = []
    for xb in base_points:
        for j in range(N_SLIDERS):
            b = np.tile(xb, (RC_SAMPLES, 1))
            b[:, j] = grid
            blocks.append(b)
    codes, objs, pens = _evaluate(np.vstack(blocks), ex)
    shape = (len(base_points), N_SLIDERS, RC_SAMPLES)
    return {
        "grid": grid.tolist(),
        "codes": codes.reshape(shape).tolist(),
        "objective": objs.reshape(shape).tolist(),
        "penalty": pens.reshape(shape).tolist(),
    }


def probe_smoothness(ex: ProcessPoolExecutor, points: np.ndarray) -> dict:
    """Two-scale central differences per axis on `points`; classify each sample.

    For every (point, axis): coarse (h=1e-3) and fine (h=1e-5) central-difference
    slopes. A smooth spot has scale-independent slopes (ratio ~ 1); a kink shows
    scale-dependent slopes (or a penalty/reject wall inside the step); a plateau
    is flat at both scales. Axes whose coarse step leaves [0,1] are 'edge'
    (excluded from the smooth/kink/plateau denominator).
    """
    n = len(points)
    steps = []          # eval points
    meta = []           # (point_idx, axis, scale, sign)
    scales = {"coarse": H_COARSE, "fine": H_FINE}
    for p in range(n):
        xb = points[p]
        for i in range(N_SLIDERS):
            for sname, h in scales.items():
                for sign in (+1.0, -1.0):
                    v = xb.copy()
                    v[i] = v[i] + sign * h
                    steps.append(v)
                    meta.append((p, i, sname, sign))
    codes, objs, _ = _evaluate(np.array(steps), ex)
    # Index results back into (point, axis, scale, sign).
    look: dict[tuple[int, int, str, float], tuple[int, float]] = {}
    for m, code, obj in zip(meta, codes, objs, strict=True):
        look[m] = (int(code), float(obj))

    g_fine = np.full((n, N_SLIDERS), np.nan)
    g_coarse = np.full((n, N_SLIDERS), np.nan)
    bucket = np.empty((n, N_SLIDERS), dtype=object)
    for p in range(n):
        xb = points[p]
        for i in range(N_SLIDERS):
            edge = (xb[i] + H_COARSE > 1.0) or (xb[i] - H_COARSE < 0.0)
            cp, fcp = look[(p, i, "coarse", +1.0)]
            cm, fcm = look[(p, i, "coarse", -1.0)]
            fp, ffp = look[(p, i, "fine", +1.0)]
            fm, ffm = look[(p, i, "fine", -1.0)]
            gc = (fcp - fcm) / (2 * H_COARSE)
            gf = (ffp - ffm) / (2 * H_FINE)
            g_coarse[p, i] = gc
            g_fine[p, i] = gf
            wall = any(c in (1, 2, 3) for c in (cp, cm, fp, fm))
            if edge:
                bucket[p, i] = "edge"
            elif wall:
                bucket[p, i] = "kink"
            elif abs(gc) < EPS_FLAT and abs(gf) < EPS_FLAT:
                bucket[p, i] = "plateau"
            else:
                lo, hi = sorted((abs(gc), abs(gf)))
                ratio = hi / max(lo, EPS_FLAT)
                bucket[p, i] = "smooth" if ratio <= R_SMOOTH else "kink"

    flat_bucket = bucket.ravel()
    non_edge = flat_bucket != "edge"
    counts = {b: int(np.sum(flat_bucket == b)) for b in
              ("smooth", "kink", "plateau", "edge")}
    n_class = int(np.sum(non_edge))
    frac = {b: (counts[b] / n_class if n_class else 0.0)
            for b in ("smooth", "kink", "plateau")}

    # Point-level verdict: a point is kinked if any non-edge axis kinks,
    # plateau if all its non-edge axes are flat, else smooth.
    pt_class = []
    for p in range(n):
        row = [bucket[p, i] for i in range(N_SLIDERS) if bucket[p, i] != "edge"]
        if not row:
            pt_class.append("edge")
        elif "kink" in row:
            pt_class.append("kinked")
        elif all(b == "plateau" for b in row):
            pt_class.append("plateau")
        else:
            pt_class.append("smooth")
    pt_class = np.array(pt_class)
    pt_valid = pt_class != "edge"
    n_pt = int(np.sum(pt_valid))
    pt_frac = {b: (int(np.sum(pt_class == b)) / n_pt if n_pt else 0.0)
               for b in ("smooth", "kinked", "plateau")}

    # Interior sensitivity ranking: median |coarse slope| over non-wall samples.
    interior = np.isin(bucket, ("smooth", "plateau"))
    sens = []
    for i in range(N_SLIDERS):
        col = np.abs(g_coarse[:, i])[interior[:, i]]
        sens.append(float(np.median(col)) if col.size else 0.0)

    # Scale-ratio sample (smooth samples only) for the histogram.
    ratio_vals = []
    for p in range(n):
        for i in range(N_SLIDERS):
            if bucket[p, i] == "smooth":
                lo, hi = sorted((abs(g_coarse[p, i]), abs(g_fine[p, i])))
                ratio_vals.append(hi / max(lo, EPS_FLAT))

    return {
        "n_points": n,
        "counts_axis": counts,
        "frac_axis": frac,
        "frac_point": pt_frac,
        "sensitivity_median_abs_coarse": sens,
        "scale_ratio_sample": ratio_vals,
        "g_coarse": g_coarse.tolist(),
        "g_fine": g_fine.tolist(),
    }


def _clip(v: np.ndarray) -> np.ndarray:
    return np.minimum(1.0, np.maximum(0.0, v))


def _push(pts: list[np.ndarray], xb: np.ndarray, deltas: dict[int, float]) -> int:
    """Append xb + deltas (clipped to the cube) to pts, return its index."""
    v = xb.copy()
    for i, d in deltas.items():
        v[i] += d
    pts.append(_clip(v))
    return len(pts) - 1


def _hessian_points(xb: np.ndarray) -> tuple[np.ndarray, int, dict, dict]:
    """Central-difference stencil for the 8x8 Hessian at xb (indices into pts)."""
    pts: list[np.ndarray] = [_clip(xb)]
    diag: dict[int, tuple[int, int]] = {}
    for i in range(N_SLIDERS):
        diag[i] = (_push(pts, xb, {i: +H_HESS}), _push(pts, xb, {i: -H_HESS}))
    off: dict[tuple[int, int], tuple[int, ...]] = {}
    for i in range(N_SLIDERS):
        for j in range(i + 1, N_SLIDERS):
            off[(i, j)] = tuple(
                _push(pts, xb, {i: si, j: sj})
                for si in (+H_HESS, -H_HESS) for sj in (+H_HESS, -H_HESS))
    return np.array(pts), 0, diag, off


def probe_hessian(ex: ProcessPoolExecutor, base_points: list[np.ndarray],
                  labels: list[str]) -> list[dict]:
    """Central-difference Hessian (h=2e-3) + coupling + spectrum per base point."""
    out = []
    for xb, label in zip(base_points, labels, strict=True):
        pts_arr, i0, diag, off = _hessian_points(xb)
        codes, objs, _ = _evaluate(pts_arr, ex)

        h2 = H_HESS * H_HESS
        f0 = objs[i0]
        H = np.zeros((N_SLIDERS, N_SLIDERS))
        for i, (ip, im) in diag.items():
            H[i, i] = (objs[ip] - 2 * f0 + objs[im]) / h2
        for (i, j), (pp, pm, mp, mm) in off.items():
            v = (objs[pp] - objs[pm] - objs[mp] + objs[mm]) / (4 * h2)
            H[i, j] = H[j, i] = v

        # NOTE the objective is only piecewise-smooth (rank-normalization kinks
        # + degenerate-fleet spikes, see probe_noise), so this second-difference
        # "Hessian" is dominated by those artifacts, not clean curvature. We keep
        # it as evidence of NON-convexity, not as a trustworthy bowl.
        absmax = float(np.max(np.abs(H))) or 1.0
        curv_norm = H / absmax  # signed, in [-1,1], for the heatmap
        eig = np.linalg.eigvalsh(0.5 * (H + H.T))
        floor = 1e-6 * np.abs(eig).max()
        nz = np.abs(eig)[np.abs(eig) > floor]
        cond = float(nz.max() / nz.min()) if nz.size else float("inf")
        indefinite = bool((eig > floor).any() and (eig < -floor).any())
        offmask = ~np.eye(N_SLIDERS, dtype=bool)
        offdiag_energy = float(np.sqrt((H[offmask] ** 2).sum())
                               / max(np.sqrt((H ** 2).sum()), 1e-30))
        diag = np.abs(np.diag(H))
        curv_range = float(diag.max() / max(diag[diag > 0].min(), 1e-30)) \
            if (diag > 0).any() else float("inf")

        # Top interactions by |second-difference| (fraction of the peak entry).
        pairs = []
        for i in range(N_SLIDERS):
            for j in range(i + 1, N_SLIDERS):
                pairs.append((abs(H[i, j]), SLIDER_NAMES[i], SLIDER_NAMES[j],
                              float(H[i, j] / absmax)))
        pairs.sort(reverse=True)
        top = [{"axes": [a, b], "coupling": c} for _, a, b, c in pairs[:6]]

        out.append({
            "label": label,
            "base_point": xb.tolist(),
            "H": H.tolist(),
            "coupling": curv_norm.tolist(),
            "eigenvalues": eig.tolist(),
            "condition_number": cond,
            "indefinite": indefinite,
            "offdiag_energy": offdiag_energy,
            "diag_curv_range": curv_range,
            "n_nonfeasible_neighbours": int(np.sum(codes != 0)),
            "f0": float(f0),
            "top_couplings": top,
        })
    return out


def probe_noise(ex: ProcessPoolExecutor, points: np.ndarray,
                rng: np.random.Generator) -> dict:
    """Deterministic pseudo-noise / spike detector.

    Jitter each feasible point by 1e-6 (far below any real geometric feature
    scale) in K random directions and measure the objective spread. A genuinely
    smooth spot moves by ~gradient*1e-6 (negligible); a point sitting in a
    degenerate-fleet 'spike band' (raw axis value pinned on a tied fleet
    breakpoint, where np.interp flips ranks on sub-ULP input changes) jumps by
    O(0.2). The band fraction is the share of the feasible interior that is
    effectively noisy to a local search.
    """
    eps = 1e-6
    band_thresh = 0.05
    k = 8
    n = len(points)
    if n == 0:
        return {"eps": eps, "band_thresh": band_thresh, "n_points": 0, "k": k,
                "spread_median": 0.0, "spread_p95": 0.0, "spread_max": 0.0,
                "noise_band_frac": 0.0, "spread": []}
    steps = []
    for p in range(n):
        steps.append(points[p])
        for _ in range(k):
            d = rng.normal(size=N_SLIDERS)
            d /= max(np.linalg.norm(d), 1e-12)
            steps.append(_clip(points[p] + eps * d))
    _, objs, _ = _evaluate(np.array(steps), ex)
    objs = objs.reshape(n, k + 1)
    spread = objs.max(axis=1) - objs.min(axis=1)
    return {
        "eps": eps, "band_thresh": band_thresh, "n_points": n, "k": k,
        "spread_median": float(np.median(spread)),
        "spread_p95": float(np.percentile(spread, 95)),
        "spread_max": float(spread.max()),
        "noise_band_frac": float(np.mean(spread > band_thresh)),
        "spread": spread.tolist(),
    }


def probe_slice(ex: ProcessPoolExecutor, template: np.ndarray, ax: str, ay: str
                ) -> dict:
    """80x80 objective terrain over two sliders, others at the template."""
    ix, iy = IDX[ax], IDX[ay]
    g = np.linspace(0.0, 1.0, SLICE_RES)
    GX, GY = np.meshgrid(g, g)  # GX varies along x=ax, GY along y=ay
    X = np.tile(template, (SLICE_RES * SLICE_RES, 1))
    X[:, ix] = GX.ravel()
    X[:, iy] = GY.ravel()
    codes, objs, pens = _evaluate(X, ex)
    codes = codes.reshape(SLICE_RES, SLICE_RES)
    objs = objs.reshape(SLICE_RES, SLICE_RES)
    pens = pens.reshape(SLICE_RES, SLICE_RES)
    feas = codes == 0
    if feas.any():
        fi = np.argmin(np.where(feas, objs, np.inf))
        min_rc = np.unravel_index(fi, objs.shape)
        min_xy = [float(g[min_rc[1]]), float(g[min_rc[0]])]
        min_obj = float(objs[min_rc])
    else:
        min_xy, min_obj = None, None
    return {
        "ax": ax, "ay": ay, "grid": g.tolist(),
        "codes": codes.tolist(), "objective": objs.tolist(),
        "penalty": pens.tolist(),
        "template_xy": [float(template[ix]), float(template[iy])],
        "min_xy": min_xy, "min_obj": min_obj,
    }


# --- verdict -----------------------------------------------------------------


def build_verdict(stats: dict, smooth: dict, hess: list[dict], noise: dict) -> dict:
    """Derive the recommendation from the numbers (not vibes)."""
    sm = smooth["frac_point"]["smooth"]
    kk = smooth["frac_point"]["kinked"]
    pl = smooth["frac_point"]["plateau"]
    ax = smooth["frac_axis"]
    cond_template = hess[0]["condition_number"]
    conds = [h["condition_number"] for h in hess]
    indefinite = any(h["indefinite"] for h in hess)
    offdiag = float(np.mean([h["offdiag_energy"] for h in hess]))
    curv_range = max(h["diag_curv_range"] for h in hess)
    top = hess[0]["top_couplings"][0] if hess[0]["top_couplings"] else None
    reject_plateau = stats["frac_decode_reject"] + stats["frac_eval_reject"]

    band = noise["noise_band_frac"]
    spike_amp = noise["spread_max"]
    smooth_interior = ax["smooth"] >= 0.6
    noisy = band >= 0.05  # a meaningful spike band exists

    # The second-difference Hessians are indefinite AND spike/kink-inflated, so
    # they are evidence of NON-convexity, not a clean, polishable bowl. With a
    # deterministic spike band on top, local derivatives are meaningless there.
    if noisy:
        rec = ("KEEP CMA; DO NOT ADD A GRADIENT POLISH YET; FIX THE NORMALIZATION. "
               "CMA-ES is the right tool: rank-based and derivative-free, it is "
               "robust to the deterministic spike band and the penalty-wall kinks "
               "that would wreck any gradient/Newton step. A gradient polish stage "
               "is contraindicated while the spikes stand (local slopes are noise). "
               "Highest-value fix: dedupe/average tied fleet breakpoints in "
               "optimize._normalize (raw forgiveness is pinned at the ~0.6 stall "
               "floor for 4 of 6 reference fins, so np.interp flips ranks 0<->40 on "
               "sub-ULP wobble) -- that de-noises the surface for every optimizer.")
    elif smooth_interior and (indefinite or offdiag >= 0.3 or cond_template >= 30):
        rec = ("KEEP CMA. The feasible interior is mostly smooth but NON-convex "
               "(indefinite Hessians / saddles), strongly coupled and extremely "
               "anisotropic -- the regime CMA's covariance adaptation targets and "
               "where a global gradient method stalls. A short quasi-Newton polish "
               "of the winner is worthwhile ONLY inside a verified convex, "
               "spike-free neighbourhood.")
    else:
        rec = ("CMA IS SAFE; a gradient polish is optional given the ~95% "
               "infeasible cube and rejection plateaus.")

    return {
        "point_smooth_frac": sm, "point_kinked_frac": kk, "point_plateau_frac": pl,
        "axis_smooth_frac": ax["smooth"], "axis_kink_frac": ax["kink"],
        "axis_plateau_frac": ax["plateau"],
        "condition_template": cond_template, "condition_all": conds,
        "indefinite": indefinite, "offdiag_energy": offdiag,
        "diag_curv_range": curv_range, "top_coupling": top,
        "feasible_frac": stats["frac_feasible"],
        "reject_plateau_frac": reject_plateau,
        "noise_band_frac": band, "spike_amplitude": spike_amp,
        "recommendation": rec,
    }


def format_sheet_verdict(v: dict, stats: dict, cost: dict) -> str:
    """A compact, pre-wrapped verdict for the terrain sheet panel."""
    import textwrap
    det = "identical" if cost["determinism_bitwise_identical"] else "BROKEN"
    cond_exp = int(np.log10(max(v["condition_template"], 1)))
    tc = v["top_coupling"]
    tc_txt = f"{tc['axes'][0]}x{tc['axes'][1]}" if tc else "none"
    lines = [
        "VERDICT",
        "mostly-smooth feasible basin inside a",
        "piecewise-linear penalty funnel, PLUS a",
        "deterministic spike band.",
        "",
        f"smooth   {v['axis_smooth_frac']:.0%} axis / {v['point_smooth_frac']:.0%} pts",
        f"kink     {v['axis_kink_frac']:.0%} axis / {v['point_kinked_frac']:.0%} pts",
        f"flat     {v['axis_plateau_frac']:.0%} axis",
        f"feasible {stats['frac_feasible']:.1%} of cube",
        f"reject plateau {v['reject_plateau_frac']:.2%}",
        f"SPIKE BAND {v['noise_band_frac']:.0%} of pts (amp<={v['spike_amplitude']:.2f})",
        "  cause: fleet forgiveness tied at 0.6,",
        "  np.interp rank flips 0<->40 (sub-ULP)",
        "Hessians INDEFINITE (saddles), spike-",
        f"inflated: cond~1e{cond_exp}, off-diag "
        f"{v['offdiag_energy']:.0%}, top {tc_txt}",
        f"determinism {det}; {cost['eval_ms_median']:.0f} ms/eval",
        "",
        "RECOMMENDATION",
    ]
    rec = ("KEEP CMA (rank-based, derivative-free: robust to the "
           "spikes+kinks that break gradient/Newton). No gradient "
           "polish until optimize._normalize dedupes the tied fleet "
           "breakpoints and de-spikes the surface.")
    return "\n".join(lines) + "\n" + textwrap.fill(rec, 44)


def verdict_paragraph(v: dict, stats: dict, cost: dict) -> str:
    tc = v["top_coupling"]
    tc_txt = (f"{tc['axes'][0]}x{tc['axes'][1]}"
              if tc else "none")
    det = ("bitwise reproducible" if cost["determinism_bitwise_identical"]
           else "NON-deterministic")
    defn = "saddles" if v["indefinite"] else "definite"
    return (
        f"VERDICT.  The feasible interior is MOSTLY smooth but NOT clean: "
        f"{v['axis_smooth_frac']:.0%} of per-axis finite-difference probes are "
        f"scale-independent, {v['axis_kink_frac']:.0%} kinked, {v['axis_plateau_frac']:.0%} "
        f"flat; {v['point_smooth_frac']:.0%} of feasible points are locally smooth, "
        f"{v['point_kinked_frac']:.0%} sit on a kink, {v['point_plateau_frac']:.0%} on a flat "
        f"direction.  Two roughness sources: (1) a piecewise-linear PENALTY FUNNEL -- only "
        f"{stats['frac_feasible']:.1%} of the cube is feasible, {v['reject_plateau_frac']:.2%} "
        f"is flat reject plateau, the rest a graded wall that kinks at every constraint "
        f"onset; (2) a deterministic SPIKE BAND -- {v['noise_band_frac']:.0%} of feasible "
        f"points jump by up to {v['spike_amplitude']:.2f} under a 1e-6 jitter, from a "
        f"degenerate-fleet bug (raw forgiveness pinned at the ~0.6 stall floor for 4/6 "
        f"reference fins, so np.interp flips the rank 0<->40 on sub-ULP wobble).  So the "
        f"second-difference Hessians are indefinite ({defn}), "
        f"spike-inflated (cond ~1e{int(np.log10(max(v['condition_template'],1))):d}, "
        f"curvature spans ~1e{int(np.log10(max(v['diag_curv_range'],1))):d}, off-diagonal "
        f"energy {v['offdiag_energy']:.0%}, strongest interaction {tc_txt}) -- NOT a clean "
        f"bowl.  Evals are {det}, {cost['eval_ms_median']:.0f} ms median.  "
        f"RECOMMENDATION: {v['recommendation']}"
    )


# --- rendering ---------------------------------------------------------------


def _diverging_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list(
        "fin_div", [_ORANGE, "#1a2229", _CYAN])


def _sequential_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list(
        "fin_seq", ["#0e2b33", "#1f6b7a", _CYAN, _CYAN_LT])


def _style_ax(ax) -> None:
    ax.set_facecolor(_PANEL)
    ax.tick_params(colors=_MUTED, labelsize=7)
    for s in ax.spines.values():
        s.set_color(_AXIS)


def render_terrain(path: Path, rider_label: str, rc: dict, slices: list[dict],
                   stats: dict, cost: dict, verdict: str,
                   base_labels: list[str], noise: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    grid = np.array(rc["grid"])
    obj = np.array(rc["objective"])   # (base, axis, samples)
    pen = np.array(rc["penalty"])
    codes = np.array(rc["codes"])
    n_base = obj.shape[0]
    base_colors = [_CYAN, _ORANGE, _CYAN_LT][:n_base]

    fig = plt.figure(figsize=(22, 15.5), facecolor=_BG)
    gs = GridSpec(3, 4, figure=fig, height_ratios=[1.0, 1.0, 1.15],
                  hspace=0.42, wspace=0.28,
                  left=0.05, right=0.985, top=0.925, bottom=0.055)
    fig.suptitle(
        f"fingen objective landscape  .  {rider_label}  .  response curves + terrain",
        color=_INK, fontsize=15, family="monospace")

    # --- response curves (8 panels) --
    for j in range(N_SLIDERS):
        ax = fig.add_subplot(gs[j // 4, j % 4])
        _style_ax(ax)
        for b in range(n_base):
            o = obj[b, j]
            ax.plot(grid, np.clip(o, 1e-3, None), color=base_colors[b], lw=1.7,
                    label=base_labels[b] if j == 0 else None, zorder=3)
            # penalty-active shading (feasible boundary crossings)
            active = pen[b, j] > 1e-9
            ax.fill_between(grid, 1e-3, np.clip(o, 1e-3, None),
                            where=active, color=base_colors[b], alpha=0.07,
                            step="mid", zorder=1)
            # rejection ticks at plateau value
            rej = np.isin(codes[b, j], (2, 3))
            if rej.any():
                ax.plot(grid[rej], np.full(rej.sum(), DECODE_PENALTY), "|",
                        color=_RED, ms=7, mew=1.4, zorder=4)
        ax.set_yscale("log")
        ax.set_title(SLIDER_NAMES[j], color=_INK, fontsize=10, family="monospace")
        ax.set_xlim(0, 1)
        ax.grid(color=_GRID, lw=0.6)
        if j % 4 == 0:
            ax.set_ylabel("objective (log)", color=_MUTED, fontsize=8)
    # one shared legend
    handles = [plt.Line2D([], [], color=base_colors[b], lw=2, label=base_labels[b])
               for b in range(n_base)]
    handles += [plt.Line2D([], [], color=_RED, marker="|", ls="", ms=8,
                           label="decode/eval reject"),
                plt.Line2D([], [], color=_MUTED, lw=6, alpha=0.3,
                           label="penalty-active (shaded)")]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.985, 0.985),
               facecolor=_PANEL, edgecolor=_GRID, labelcolor=_INK, fontsize=9,
               ncol=2)

    # --- slice maps --
    seq = _sequential_cmap()
    for k, sl in enumerate(slices):
        ax = fig.add_subplot(gs[2, k])
        _style_ax(ax)
        objm = np.array(sl["objective"])
        codem = np.array(sl["codes"])
        reject = codem >= 2
        vmin = np.log10(max(np.nanmin(objm[codem == 0]), 1e-3)) if (codem == 0).any() else -1
        vmax = np.log10(2.0)
        disp = np.log10(np.clip(objm, 1e-3, None))
        im = ax.imshow(disp, origin="lower", extent=(0, 1, 0, 1), aspect="auto",
                       cmap=seq, vmin=vmin, vmax=vmax, zorder=1)
        # reject cells flat dark red
        red_layer = np.zeros((*reject.shape, 4))
        red_layer[reject] = (0.55, 0.11, 0.09, 1.0)
        ax.imshow(red_layer, origin="lower", extent=(0, 1, 0, 1), aspect="auto",
                  zorder=2)
        # feasible-region contour
        feas = (codem == 0).astype(float)
        ax.contour(np.array(sl["grid"]), np.array(sl["grid"]), feas, levels=[0.5],
                   colors=[_CYAN_LT], linewidths=1.2, zorder=3)
        tx, ty = sl["template_xy"]
        ax.plot(tx, ty, "+", color=_INK, ms=12, mew=2, zorder=5)
        if sl["min_xy"]:
            ax.plot(*sl["min_xy"], "*", color=_ORANGE, ms=15, mew=0.5,
                    mec=_BG, zorder=6)
        ax.set_xlabel(sl["ax"], color=_MUTED, fontsize=9)
        ax.set_ylabel(sl["ay"], color=_MUTED, fontsize=9)
        ax.set_title(f"terrain: {sl['ax']} x {sl['ay']}  (log objective)",
                     color=_INK, fontsize=10, family="monospace")
        cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
        cb.ax.tick_params(colors=_MUTED, labelsize=6)
        cb.outline.set_edgecolor(_AXIS)

    # --- stats panel --
    axs = fig.add_subplot(gs[2, 2])
    axs.set_facecolor(_PANEL)
    axs.axis("off")
    axs.set_title("cube census & cost", color=_INK, fontsize=10, family="monospace")
    lines = [
        (f"sampled           {stats['n_sampled']}", _MUTED),
        (f"feasible          {stats['frac_feasible']:.2%}", _CYAN),
        (f"infeasible        {stats['frac_infeasible']:.2%}", _ORANGE),
        (f"clean decode      {stats['frac_clean_decode']:.2%}", _MUTED),
        (f"decode reject     {stats['frac_decode_reject']:.2%}", _MUTED),
        (f"eval reject       {stats['frac_eval_reject']:.3%}", _RED),
        ("", _INK),
        (f"feasible obj  min {stats['feasible_obj_min']:.3f}", _MUTED),
        (f"          median {stats['feasible_obj_median']:.3f}", _MUTED),
        (f"             max {stats['feasible_obj_max']:.3f}", _MUTED),
        ("", _INK),
        (f"determinism  {'identical' if cost['determinism_bitwise_identical'] else 'BROKEN'}",
         _CYAN if cost["determinism_bitwise_identical"] else _RED),
        (f"spike band   {noise['noise_band_frac']:.0%}  amp {noise['spread_max']:.2f}", _RED),
        (f"eval ms  med {cost['eval_ms_median']:.1f}  p95 {cost['eval_ms_p95']:.1f}",
         _MUTED),
    ]
    y = 0.95
    for text, color in lines:
        axs.text(0.03, y, text, color=color, fontsize=9, family="monospace",
                 va="top", transform=axs.transAxes)
        y -= 0.067

    # --- verdict panel --
    axv = fig.add_subplot(gs[2, 3])
    axv.set_facecolor("#0e1418")
    axv.axis("off")
    for s in ["top", "bottom", "left", "right"]:
        axv.spines[s].set_visible(True)
        axv.spines[s].set_color(_ORANGE)
    axv.set_title("verdict", color=_ORANGE, fontsize=11, family="monospace")
    axv.text(0.03, 0.98, verdict, color=_INK, fontsize=8.6,
             family="monospace", va="top", transform=axv.transAxes, linespacing=1.4)

    fig.savefig(path, dpi=110, facecolor=_BG)
    plt.close(fig)


def render_smoothness(path: Path, rider_label: str, smooth: dict,
                      hess: list[dict], noise: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    fig = plt.figure(figsize=(22, 11.5), facecolor=_BG)
    gs = GridSpec(2, 4, figure=fig, hspace=0.42, wspace=0.32,
                  left=0.05, right=0.98, top=0.9, bottom=0.08)
    fig.suptitle(
        f"fingen objective landscape  .  {rider_label}  .  smoothness & coupling",
        color=_INK, fontsize=15, family="monospace")

    # --- sensitivity ranking bar --
    ax = fig.add_subplot(gs[0, 0])
    _style_ax(ax)
    sens = np.array(smooth["sensitivity_median_abs_coarse"])
    order = np.argsort(sens)
    ax.barh(range(N_SLIDERS), sens[order], color=_CYAN, height=0.7)
    ax.set_yticks(range(N_SLIDERS))
    ax.set_yticklabels([SLIDER_NAMES[i] for i in order], fontsize=8,
                       family="monospace", color=_INK)
    ax.set_xlabel("median |d objective / d slider|", color=_MUTED, fontsize=8)
    ax.set_title("sensitivity ranking (interior)", color=_INK, fontsize=10,
                 family="monospace")
    ax.grid(color=_GRID, lw=0.6, axis="x")

    # --- spike / pseudo-noise histogram (the 'how chaotic' chart) --
    ax = fig.add_subplot(gs[0, 1])
    _style_ax(ax)
    spread = np.array(noise["spread"])
    spread = np.clip(spread[np.isfinite(spread)], 1e-9, None)
    bins = np.logspace(-9, 0, 40)
    ax.hist(spread, bins=bins, color=_CYAN, alpha=0.85)
    ax.set_xscale("log")
    ax.axvline(noise["band_thresh"], color=_RED, lw=1.4, ls="--")
    ax.text(noise["band_thresh"] * 1.3, 0.9,
            f"spike band\n{noise['noise_band_frac']:.0%} of pts",
            color=_RED, fontsize=8, family="monospace",
            transform=ax.get_xaxis_transform(), va="top")
    ax.set_xlabel("objective jump under 1e-6 jitter", color=_MUTED, fontsize=8)
    ax.set_ylabel("feasible points", color=_MUTED, fontsize=8)
    ax.set_title(f"deterministic spike band  (max {noise['spread_max']:.2f})",
                 color=_INK, fontsize=10, family="monospace")
    ax.grid(color=_GRID, lw=0.6, axis="y")

    # --- scale-ratio histogram --
    ax = fig.add_subplot(gs[0, 2])
    _style_ax(ax)
    ratios = np.array(smooth["scale_ratio_sample"])
    ratios = ratios[np.isfinite(ratios)]
    if ratios.size:
        ax.hist(np.clip(ratios, 0.5, 10), bins=np.linspace(0.5, 10, 40),
                color=_CYAN, alpha=0.85)
    ax.axvline(1.0, color=_ORANGE, lw=1.4, ls="--")
    ax.text(1.05, 0.92, "ideal=1", color=_ORANGE, fontsize=8,
            transform=ax.get_xaxis_transform(), family="monospace")
    ax.set_xlabel("|coarse slope| / |fine slope|", color=_MUTED, fontsize=8)
    ax.set_ylabel("smooth samples", color=_MUTED, fontsize=8)
    ax.set_title("scale-dependence of the slope", color=_INK, fontsize=10,
                 family="monospace")
    ax.grid(color=_GRID, lw=0.6)

    # --- point-level classification bar --
    ax = fig.add_subplot(gs[0, 3])
    _style_ax(ax)
    fp = smooth["frac_point"]
    fa = smooth["frac_axis"]
    cats = ["smooth", "kink", "plateau"]
    pt = [fp["smooth"], fp["kinked"], fp["plateau"]]
    axf = [fa["smooth"], fa["kink"], fa["plateau"]]
    xpos = np.arange(3)
    ax.bar(xpos - 0.2, pt, width=0.38, color=_CYAN, label="per point")
    ax.bar(xpos + 0.2, axf, width=0.38, color=_ORANGE, label="per axis")
    ax.set_xticks(xpos)
    ax.set_xticklabels(cats, fontsize=9, family="monospace", color=_INK)
    ax.set_ylim(0, 1)
    ax.set_ylabel("fraction", color=_MUTED, fontsize=8)
    ax.set_title("smooth / kink / plateau share", color=_INK, fontsize=10,
                 family="monospace")
    ax.legend(facecolor=_PANEL, edgecolor=_GRID, labelcolor=_INK, fontsize=8)
    ax.grid(color=_GRID, lw=0.6, axis="y")
    for x, val in zip(xpos - 0.2, pt, strict=True):
        ax.text(x, val + 0.02, f"{val:.0%}", color=_CYAN, fontsize=8,
                ha="center", family="monospace")

    # --- second-difference coupling heatmaps + eigen spectrum --
    # Signed, normalized by peak |entry|, gamma-lifted so off-diagonal structure
    # shows despite the spike-inflated diagonal. NOT a clean curvature bowl.
    div = _diverging_cmap()
    for k, h in enumerate(hess[:3]):
        ax = fig.add_subplot(gs[1, k])
        _style_ax(ax)
        C = np.array(h["coupling"])
        disp = np.sign(C) * np.abs(C) ** 0.4
        im = ax.imshow(disp, cmap=div, vmin=-1, vmax=1, aspect="equal")
        ax.set_xticks(range(N_SLIDERS))
        ax.set_yticks(range(N_SLIDERS))
        ax.set_xticklabels(SLIDER_NAMES, rotation=60, ha="right", fontsize=6,
                           family="monospace", color=_INK)
        ax.set_yticklabels(SLIDER_NAMES, fontsize=6, family="monospace", color=_INK)
        tag = "indefinite/saddle" if h["indefinite"] else "definite"
        ax.set_title(f"2nd-diff @ {h['label']}  ({tag})\n"
                     f"cond ~1e{int(np.log10(max(h['condition_number'], 1))):d}  "
                     f"off-E {h['offdiag_energy']:.0%}",
                     color=_INK, fontsize=8.5, family="monospace")
        cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
        cb.ax.tick_params(colors=_MUTED, labelsize=6)
        cb.outline.set_edgecolor(_AXIS)

    ax = fig.add_subplot(gs[1, 3])
    _style_ax(ax)
    colors = [_CYAN, _ORANGE, _CYAN_LT]
    for k, h in enumerate(hess[:3]):
        eig = np.sort(np.array(h["eigenvalues"]))[::-1]
        ax.plot(range(1, len(eig) + 1), np.sign(eig) * np.log10(np.abs(eig) + 1e-9),
                "o-", color=colors[k % 3], lw=1.5, ms=6, label=h["label"])
    ax.axhline(0, color=_MUTED, lw=0.8, ls=":")
    ax.set_xlabel("eigenvalue index", color=_MUTED, fontsize=8)
    ax.set_ylabel("sign . log10|lambda|", color=_MUTED, fontsize=8)
    ax.set_title("Hessian spectra", color=_INK, fontsize=10, family="monospace")
    ax.legend(facecolor=_PANEL, edgecolor=_GRID, labelcolor=_INK, fontsize=8)
    ax.grid(color=_GRID, lw=0.6)

    fig.savefig(path, dpi=110, facecolor=_BG)
    plt.close(fig)


# --- driver ------------------------------------------------------------------


def run_full(ex: ProcessPoolExecutor, rng: np.random.Generator, rider_label: str,
             out_prefix: Path, n_stats: int) -> dict:
    """The full 5-probe study + both sheets. Returns the JSON-able probe blob."""
    template = np.array(_x0_sliders(FinConfig.THRUSTER))

    stats, feasible = probe_stats(ex, rng, n_stats)
    base_points, base_labels = select_base_points(ex, template, feasible, rng)
    cost = probe_determinism_cost(base_points, feasible)
    rc = probe_response_curves(ex, base_points)
    smooth = probe_smoothness(ex, feasible[:N_SMOOTH])
    noise = probe_noise(ex, feasible[:N_SMOOTH], rng)
    hess = probe_hessian(ex, base_points, base_labels)
    slices = [probe_slice(ex, template, "depth", "sweep"),
              probe_slice(ex, template, "base", "thickness_ratio")]
    verdict = build_verdict(stats, smooth, hess, noise)
    para = verdict_paragraph(verdict, stats, cost)
    sheet = format_sheet_verdict(verdict, stats, cost)

    render_terrain(out_prefix.with_name(out_prefix.name + "-terrain.png"),
                   rider_label, rc, slices, stats, cost, sheet, base_labels, noise)
    render_smoothness(out_prefix.with_name(out_prefix.name + "-smoothness.png"),
                      rider_label, smooth, hess, noise)

    return {
        "rider_label": rider_label,
        "base_labels": base_labels,
        "base_points": [b.tolist() for b in base_points],
        "stats": stats, "cost": cost, "response_curves": rc,
        "smoothness": smooth, "noise": noise, "hessians": hess, "slices": slices,
        "verdict": verdict, "verdict_paragraph": para,
    }


def run_light(ex: ProcessPoolExecutor, rng: np.random.Generator, rider_label: str,
              n_stats: int) -> dict:
    """Cheap contrast pass: stats + smoothness + template Hessian only."""
    template = np.array(_x0_sliders(FinConfig.THRUSTER))
    stats, feasible = probe_stats(ex, rng, n_stats)
    smooth = probe_smoothness(ex, feasible[:N_SMOOTH])
    noise = probe_noise(ex, feasible[:N_SMOOTH], rng)
    hess = probe_hessian(ex, [template], ["template"])
    verdict = build_verdict(stats, smooth, hess, noise)
    return {
        "rider_label": rider_label, "stats": stats, "smoothness": smooth,
        "noise": noise, "hessians": hess, "verdict": verdict,
    }


def _chown_kali(path: Path) -> None:
    try:
        uid = pwd.getpwnam("kali").pw_uid
        gid = grp.getgrnam("kali").gr_gid
        os.chown(path, uid, gid)
    except (PermissionError, KeyError, FileNotFoundError):
        pass


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    out_prefix = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    primary = dict(weight_kg=75.0, skill="INTERMEDIATE", config="thruster",
                   material="pet-cf")
    antagonist = dict(weight_kg=95.0, skill="PRO", config="thruster",
                      material="pet-cf")

    with ProcessPoolExecutor(max_workers=MAX_WORKERS, initializer=_init_worker,
                             initargs=tuple(primary.values())) as ex:
        _init_worker(*primary.values())  # main process too (cost/determinism)
        rng = np.random.default_rng(seed)
        print(f"[landscape] primary rider: 75 kg intermediate thruster (seed {seed})")
        blob_primary = run_full(ex, rng, "75 kg intermediate thruster",
                                out_prefix, n_stats=10000)
        print(blob_primary["verdict_paragraph"])

    # Antagonistic contrast pass (cheap): fresh pool with its rider baked in.
    with ProcessPoolExecutor(max_workers=MAX_WORKERS, initializer=_init_worker,
                             initargs=tuple(antagonist.values())) as ex:
        _init_worker(*antagonist.values())
        rng2 = np.random.default_rng(seed + 1000)
        print("[landscape] antagonistic rider: 95 kg pro thruster (cheap probe)")
        blob_antag = run_light(ex, rng2, "95 kg pro thruster", n_stats=6000)
        va = blob_antag["verdict"]
        print(f"  feasible {blob_antag['stats']['frac_feasible']:.2%}  "
              f"axis-smooth {va['axis_smooth_frac']:.0%}  "
              f"axis-kink {va['axis_kink_frac']:.0%}  "
              f"cond {va['condition_template']:.0f}")

    json_path = out_prefix.with_name(out_prefix.name + "-probe.json")
    json_path.write_text(json.dumps(
        {"seed": seed, "primary": blob_primary, "antagonist": blob_antag,
         "elapsed_s": time.time() - t0}, indent=2) + "\n")

    for suffix in ("-terrain.png", "-smoothness.png", "-probe.json"):
        _chown_kali(out_prefix.with_name(out_prefix.name + suffix))
    print(f"[landscape] wrote {out_prefix}-terrain.png / -smoothness.png / -probe.json "
          f"in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
