"""Build section table v1: table v0 moved onto the resolved-wall RANS sections.

    uv run python scripts/build_section_table_v1.py [--out=DIR/sections_v1.npz] [--report=PATH.md]

Table v0 (NeuralFoil, tripped; scripts/build_section_table.py) has the right
shapes and the wrong ends. Against resolved-wall 2-D RANS
(bench/section-tables/) its attached range is half a degree to two degrees too
wide at both ends for cambered sections, its lift slope 3–4 % high, its drag
level 4–12 % low, and below the lower end it ramps up over a degree where the
referee has a cliff a quarter to half a degree wide. The RANS sections are too
few and too coarse in angle to be a table themselves. v1 is therefore v0
WARPED: for every node of the grid

    cd_v1(a) = level * cd_v0(w(a))
    cl_v1(a) = slope * (line_v0(a - d_alpha0) + remainder_v0(w(a)))
    cm_v1(a) = cm_v0(w(a))

where w is a piecewise-linear map of the angle through four marks (MARKS): the
centre of the low-drag range stays, v0's two ends move onto where the referee
has them, and so does the foot of the cliff below the lower end. `remainder`
is what v0's lift does besides its straight line (the roll-off at the knee,
the kink of a flat inside face) — carried along with the marks. Eight numbers
per section do it (FITTED): the two ends, the cliff's width, the drag level
inside the range and the one below the cliff, the lift-slope ratio, the
zero-lift shift, and a retention factor on the remainder above the centre (v0
sheds lift gradually toward its knee; the RANS sections hold their line almost
to the stall).

Those eight are measured at every finished RANS section (`features`, the same
definition on both sources: the lower end is where cd passes 1.5 x its minimum
below the minimum, the foot of the cliff where it passes 2.5 x, the upper end
where it passes 3 x above it) and carried to the rest of the grid per foil
family (`fit_family`, `corrections`):

  * The two ENDS are fitted as the referee has them, not as their distance
    from v0: a plane in thickness and camber misses the referee's upper ends
    by 0.2 deg rms and their distance from v0 by 0.6 (v0's ends are irregular,
    the referee's are not).
  * Each quantity is a least-squares plane over (t/c, camber) plus what each
    section still misses, spread to its neighbourhood by inverse-square
    distance. At a measured section v1 is therefore that section.
  * Reynolds number is kept apart: its trend is read where a section was run at
    more than one, and applied on top. Outside the measured Reynolds numbers
    the ends stay where they were last measured (the referee moves them
    0.1–0.2 deg per octave; v0 0.5–0.7).
  * Outside the sections' box in (t/c, camber) the SHIFT of the box's edge is
    kept, so v0's trend in thickness and camber carries on from the last
    measured section. A family with no finished section keeps v0 unchanged.

v1 ships on finer grids than v0: t/c in steps of 0.005, camber in steps of
0.5 %, Reynolds number in half octaves (so the referee's 5.7e5 is on the
grid), angles in quarter degrees between -10 and +14. They are filled from v0
by interpolation WITH THE MARKS ALIGNED (`aligned_blend`). The library
interpolates plainly between neighbouring nodes; on v0's grid (t/c 0.07 and
0.09 are neighbours, their lower ends two degrees apart) that turns one cliff
into two half-height steps, and a search then parks on a grid node. On the
fine grid neighbours differ by half a degree.

The report reads the finished table THROUGH THE LIBRARY (`sections.polar`), the
way the model reads it, and adds for every node the ends a table built without
that node predicts: how well the table is known between its nodes. The meta
block records sections, planes, remainders, trends and the box.

Rows that did not settle within the iteration cap are used to locate an end
(they say the flow has separated) and for the drag level BELOW the cliff,
never for the level inside the range. Above the upper end v1 keeps v0's
post-stall drag, moved with the end: nothing here referees it.

What the warp does not carry (bench/section-tables/README.md): inside the
range the referee's drag rises with lift earlier than v0's (v1 reads 6–14 %
low at +4…+6 deg), and it stays flat right up to the cliff where v0 creeps up
(v1 reads 9–19 % high in the last half degree before the lower end).
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
V0_PATH = REPO / "src/fingen/data/sections_v0.npz"
BENCH = REPO / "bench/section-tables"
RANS_FILES = ("results.json", "thin-cambered/results.json", "third-batch/results.json")
K_LOWER, K_UPPER = 1.5, 3.0
K_OUT = 2.5                         # below the lower end: the drag at which the face is out
LIN_RANGE = (0.0, 5.0)              # lift line fitted here: inside every section's attached range
STALL_RAMP_DEG = 2.0
# v1's grids (v0: 10 thicknesses, 5 cambered thicknesses, 6 cambers)
TC_FINE = np.concatenate([np.arange(0.040, 0.1301, 0.005), [0.16, 0.19, 0.22]])
TC_CAMBERED_FINE = np.concatenate([np.arange(0.050, 0.1201, 0.005), [0.16]])
CAMBER_FINE = np.arange(0.0, 0.0501, 0.005)
# v1's Reynolds numbers: half octaves (v0: octaves, 1e5 … 1.6e6)
RE_FINE = 1e5 * 2.0 ** (0.5 * np.arange(9))
# v1's angles: v0's half degrees, and quarter degrees where the referee has rows
# that close (a cliff a quarter degree wide does not fit between half degrees)
ALPHA_QUARTER = (-10.0, 14.0)
# What is fitted over the referee's sections: the two ends of the attached range as
# the referee has them, and five numbers that say how v0 differs inside the range.
ENDS = ("lower", "upper")
OFFSETS = ("step", "log_level", "log_level_below", "slope", "d_alpha0", "retention")
FITTED = ENDS + OFFSETS
NEUTRAL = {"d_lower": 0.0, "d_lower_out": 0.0, "d_upper": 0.0, "log_level": 0.0,
           "log_level_below": 0.0, "slope": 1.0, "d_alpha0": 0.0, "retention": 1.0}
MARKS = ("lower_out", "lower", "centre", "upper")    # the angles a warp maps onto each other
BELOW_SPAN_DEG = 3.0                # rows this far below the lower end set the level there
BELOW_RAMP_DEG = 1.0                # the level changes over this much below the lower end
# One step of the referee's spacing in t/c and camber: the unit in which a section's
# distance from a table entry is counted when its remainder is spread.
NODE_REACH = np.array([0.02, 0.015])


def _crossing(a: np.ndarray, y: np.ndarray, k0: int, step: int, limit: float) -> float:
    """Angle where y first passes `limit` walking from index k0 in direction `step`
    (linear between samples); the last sample if it never does."""
    k = k0
    while 0 <= k + step < len(a):
        if y[k + step] >= limit:
            f = (limit - y[k]) / (y[k + step] - y[k])
            return float(a[k] + f * (a[k + step] - a[k]))
        k += step
    return float(a[k])


def features(a: np.ndarray, cl: np.ndarray, cd: np.ndarray) -> dict:
    """Centre and both ends of the low-drag range, lift line of the working range.
    `lower` is where the drag starts up below the minimum (K_LOWER x the minimum),
    `lower_out` where the face is out (K_OUT x): between the two lies the cliff, a
    quarter to half a degree wide in the referee's polars and a degree in v0's."""
    inner = np.nonzero((a >= -8.0) & (a <= 8.0))[0]
    k_min = int(inner[np.argmin(cd[inner])])
    lin = (a >= LIN_RANGE[0]) & (a <= LIN_RANGE[1])
    slope, icpt = np.polyfit(a[lin], cl[lin], 1)
    return {"centre": float(a[k_min]), "cd_min": float(cd[k_min]),
            "lower": _crossing(a, cd, k_min, -1, K_LOWER * cd[k_min]),
            "lower_out": _crossing(a, cd, k_min, -1, K_OUT * cd[k_min]),
            "out_reached": bool(cd[:k_min + 1].max() >= K_OUT * cd[k_min]),
            "upper": _crossing(a, cd, k_min, +1, K_UPPER * cd[k_min]),
            "slope": float(slope), "alpha0": float(-icpt / slope)}


def marks(f: dict, shift: dict | None = None) -> np.ndarray:
    """The four angles of MARKS, in ascending order and at least a little apart
    (`shift`: the corrections d_lower_out, d_lower, d_upper added first)."""
    d = shift or {}
    centre = f["centre"]
    lower = min(f["lower"] + d.get("d_lower", 0.0), centre - 0.5)
    upper = max(f["upper"] + d.get("d_upper", 0.0), centre + 0.5)
    lower_out = min(f["lower_out"] + d.get("d_lower_out", 0.0), lower - 0.05)
    return np.array([lower_out, lower, centre, upper])


def warp(a: np.ndarray, target: np.ndarray, source: np.ndarray) -> np.ndarray:
    """Source angle that the target angle `a` reads from. `target` and `source` are
    the MARKS of the two polars: they map onto each other, linearly in between,
    with unit slope outside the outermost two."""
    return np.where(a < target[0], source[0] + (a - target[0]),
                    np.where(a > target[-1], source[-1] + (a - target[-1]),
                             np.interp(a, target, source)))


def aligned_blend(a: np.ndarray, pol_a: tuple, pol_b: tuple, w: float) -> tuple:
    """Polar a fraction `w` of the way from `pol_a` to `pol_b` (each (cl, cd, cm) on
    `a`), interpolated WITH THE ENDS ALIGNED: the two ends and the centre of the
    low-drag range are interpolated first, each neighbour is warped onto them,
    and only then are the curves blended. A plain blend of two polars whose
    ranges end at different angles turns one cliff into two half-height steps."""
    if w <= 0.0:
        return pol_a
    if w >= 1.0:
        return pol_b
    fa, fb = features(a, pol_a[0], pol_a[1]), features(a, pol_b[0], pol_b[1])
    mix = lambda k: (1.0 - w) * fa[k] + w * fb[k]  # noqa: E731
    target = (1.0 - w) * marks(fa) + w * marks(fb)
    cl = mix("slope") * (a - mix("alpha0"))
    cd, cm = np.zeros_like(a), np.zeros_like(a)
    for weight, pol, f in ((1.0 - w, pol_a, fa), (w, pol_b, fb)):
        src = warp(a, target, marks(f))
        remainder = pol[0] - f["slope"] * (a - f["alpha0"])
        cl = cl + weight * np.interp(src, a, remainder)
        cd = cd + weight * np.interp(src, a, pol[1])
        cm = cm + weight * np.interp(src, a, pol[2])
    return cl, cd, cm


def apply(a: np.ndarray, cl: np.ndarray, cd: np.ndarray, cm: np.ndarray, corr: dict,
          out: np.ndarray | None = None):
    """One v0 polar (on the angles `a`) -> v1 on the angles `out` (default: `a`),
    given its corrections."""
    out = a if out is None else out
    f = features(a, cl, cd)
    target = marks(f, corr)
    w = warp(out, target, marks(f))
    line, rem = lift_parts(a, cl, f, w, corr, out)
    # retention holds between the centre and the upper end; over the next
    # STALL_RAMP_DEG it gives way to v0's full loss, so the knee is a maximum
    upper = target[3]
    past = np.clip((out - upper) / STALL_RAMP_DEG, 0.0, 1.0)
    keep = np.where(out > f["centre"], corr["retention"] + (1.0 - corr["retention"]) * past, 1.0)
    cl1 = corr["slope"] * (line + keep * rem)
    # drag level: one value inside the range, another below the lower end (a flat
    # inside face is right there in v0 and 20 % low inside). The change is made over
    # the first degree BELOW the cliff, so the cliff stays where the warp put it.
    t = np.clip((out - (target[0] - BELOW_RAMP_DEG)) / BELOW_RAMP_DEG, 0.0, 1.0)
    level = np.exp(corr["log_level_below"] + t * (corr["log_level"] - corr["log_level_below"]))
    return cl1, level * np.interp(w, a, cd), np.interp(w, a, cm)


def lift_parts(a, cl, f: dict, w, corr: dict, out=None):
    """(v0's lift line at the shifted zero-lift angle, v0's remainder read at the
    warped angle) on the angles `out` — v1's lift before the slope ratio and the
    retention factor."""
    out = a if out is None else out
    remainder = cl - f["slope"] * (a - f["alpha0"])
    return f["slope"] * (out - f["alpha0"] - corr["d_alpha0"]), np.interp(w, a, remainder)


class TableV0:
    def __init__(self) -> None:
        with np.load(V0_PATH) as raw:
            self.t = {k: np.asarray(raw[k], dtype=float) for k in raw.files if k != "meta"}
            self.meta = json.loads(str(raw["meta"]))
        self.log_re = np.log10(self.t["reynolds"])

    @staticmethod
    def _bracket(grid, x):
        x = min(max(x, float(grid[0])), float(grid[-1]))
        i = int(min(np.searchsorted(grid, x, side="right") - 1, len(grid) - 2))
        return i, float((x - grid[i]) / (grid[i + 1] - grid[i]))

    def polar(self, family: str, tc: float, camber: float, re: float):
        """v0 at any thickness, camber and Reynolds number, interpolated with the ends
        aligned in all three (its ends move 0.5-0.7 deg per octave of Reynolds number)."""
        t = self.t
        a = t["alpha"]
        i_re, w_re = self._bracket(self.log_re, np.log10(re))

        def at_re(block: str, idx: tuple) -> tuple:
            lo, hi = (tuple(t[f"{block}_{k}"][idx + (j,)] for k in ("cl", "cd", "cm"))
                      for j in (i_re, i_re + 1))
            return aligned_blend(a, lo, hi, w_re)

        if family == "cambered" and camber > 0.0:
            i, wt = self._bracket(t["tc_cambered"], tc)
            m, wc = self._bracket(t["camber"], camber)
            rows = [aligned_blend(a, at_re("cambered", (i, mm)), at_re("cambered", (i + 1, mm)), wt)
                    for mm in (m, m + 1)]
            return (a, *aligned_blend(a, rows[0], rows[1], wc))
        family = "symmetric" if family == "cambered" else family
        i, wt = self._bracket(t["tc"], tc)
        return (a, *aligned_blend(a, at_re(family, (i,)), at_re(family, (i + 1,)), wt))


def load_nodes(v0) -> list[dict]:
    nodes = []
    for rel in RANS_FILES:
        path = BENCH / rel
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        cap = int(data["plan"].get("end_time", 4000))
        for name, sec in data["sections"].items():
            spec, rows = sec["spec"], sorted(sec.get("rows", []), key=lambda r: r["alpha"])
            wall = spec.get("wall", data["plan"].get("wall"))
            if len(rows) < len(spec["angles"]) or wall == "wf":
                continue
            a = np.array([r["alpha"] for r in rows])
            cl = np.array([r["cl"] for r in rows])
            cd = np.array([r["cd"] for r in rows])
            settled = np.array([r.get("iters", 0) < cap for r in rows])
            camber = float(spec.get("camber_ratio") or 0.0)
            fam, tc, re = spec["family"], float(spec["thickness_ratio"]), float(spec["re"])
            a0, cl0, cd0, cm0 = v0.polar(fam, tc, camber, re)
            fr, f0 = features(a, cl, cd), features(a0, cl0, cd0)
            # the cliff's width; where the referee's rows end before the face is out,
            # v0's own is kept
            step = (fr["lower"] - fr["lower_out"] if fr["out_reached"]
                    else f0["lower"] - f0["lower_out"])
            corr = {"d_lower": fr["lower"] - f0["lower"], "d_upper": fr["upper"] - f0["upper"],
                    "d_lower_out": fr["lower"] - step - f0["lower_out"], "step": step,
                    "log_level": 0.0, "log_level_below": 0.0, "slope": fr["slope"] / f0["slope"],
                    "d_alpha0": fr["alpha0"] - f0["alpha0"], "retention": 1.0}
            # lift retention toward the knee: v0 sheds lift gradually over several
            # degrees, the RANS sections hold their line almost to the stall. Scale
            # v0's remainder on the settled rows of the upper half of the range.
            w = warp(a0, marks(f0, corr), marks(f0))
            line, rem = lift_parts(a0, cl0, f0, w, corr)
            upper_half = settled & (a > 0.5 * (f0["centre"] + fr["upper"])) & (a < fr["upper"])
            if upper_half.any():
                r = np.interp(a[upper_half], a0, rem)
                gap = cl[upper_half] / corr["slope"] - np.interp(a[upper_half], a0, line)
                if float(r @ r) > 1e-6:
                    corr["retention"] = float(np.clip((r @ gap) / (r @ r), 0.2, 1.5))
            # drag level: RANS over the warped v0 on the settled rows inside the range
            _, cd_w, _ = apply(a0, cl0, cd0, cm0, corr)
            inside = settled & (a > fr["lower"] + 0.5) & (a < fr["upper"] - 0.5)
            corr["log_level"] = float(np.median(np.log(
                cd[inside] / np.interp(a[inside], a0, cd_w))))
            # ... and below the lower end, from the rows within BELOW_SPAN_DEG of it.
            # These have not settled (the face has separated); for a flat inside
            # face they agree with v0 and with the 3-D polars all the same.
            foot = fr["lower"] - step
            below = (a < foot - 0.5) & (a > foot - 0.5 - BELOW_SPAN_DEG)
            corr["log_level_below"] = corr["log_level"]
            if below.any():
                corr["log_level_below"] = float(np.clip(np.median(np.log(
                    cd[below] / np.interp(a[below], a0, cd_w))), np.log(0.6), np.log(1.5)))
            nodes.append({"name": name, "family": fam, "tc": tc, "camber": camber, "re": re,
                          "alpha": a, "cl": cl, "cd": cd, "settled": settled,
                          "rans": fr, "v0": f0, "corr": corr})
    return nodes


def _spread(points, values, x: np.ndarray) -> float:
    """Inverse-square-distance mean of `values` given at `points` ((t/c, camber),
    distances counted in NODE_REACH); exactly a point's own value at that point."""
    if len(points) == 0:
        return 0.0
    d2 = (((np.asarray(points) - x) / NODE_REACH) ** 2).sum(axis=1)
    if (d2 < 1e-12).any():
        return float(np.asarray(values)[int(np.argmin(d2))])
    w = 1.0 / d2
    return float(w @ np.asarray(values) / w.sum())


def fit_family(nodes: list[dict]) -> dict:
    """What the referee says about one foil family, as functions of the section.

    Per quantity (FITTED): its Reynolds-number trend, read at the SITES — a site is
    one (t/c, camber) — that were run at more than one Reynolds number; every site
    brought to the reference Reynolds number with that trend; a least-squares plane
    over (t/c, camber) in the directions the sites span; and what each site still
    misses, spread to its neighbourhood (`_spread`). At a node the result is that
    node's own value — v1 reproduces the referee where it has been asked."""
    key_of = [(round(n["tc"], 6), round(n["camber"], 6)) for n in nodes]
    sites = sorted(set(key_of))
    member = [np.array([k for k, key in enumerate(key_of) if key == s]) for s in sites]
    log_re = np.log10([n["re"] for n in nodes])
    levels, counts = np.unique(np.round(log_re, 4), return_counts=True)
    ref = float(levels[np.argmax(counts)])            # the Reynolds number most nodes ran at
    xy = np.array(sites)
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    used = [j for j in range(2) if hi[j] - lo[j] > 1e-9]
    while len(used) + 1 > len(sites):                 # fewer sites than terms: drop the last
        used.pop()
    design = np.column_stack([np.ones(len(sites))] + [xy[:, j] - xy[:, j].mean() for j in used])
    trend_sites = [s for s, m in zip(sites, member, strict=True) if np.ptp(log_re[m]) > 1e-6]
    planes, left, trends, resid = {}, {}, {}, {}
    for key in FITTED:
        y = np.array([n["rans"][key] if key in ENDS else n["corr"][key] for n in nodes])
        trends[key] = [float(np.polyfit(log_re[m], y[m], 1)[0])
                       for m in member if np.ptp(log_re[m]) > 1e-6]
        at_ref = np.array([float(np.mean(y[m] - _spread(trend_sites, trends[key], xy[k])
                                         * (log_re[m] - ref))) for k, m in enumerate(member)])
        coef, *_ = np.linalg.lstsq(design, at_ref, rcond=None)
        planes[key] = coef.tolist()
        left[key] = (at_ref - design @ coef).tolist()
        resid[key] = float(np.abs(design @ coef - at_ref).max())
    return {"lo": lo.tolist(), "hi": hi.tolist(), "mean": xy.mean(axis=0).tolist(), "used": used,
            "sites": [list(s) for s in sites], "planes": planes, "left": left,
            "max_residual": resid, "nodes": [n["name"] for n in nodes],
            "log_re_ref": ref, "log_re_range": [float(log_re.min()), float(log_re.max())],
            "trend_sites": [list(s) for s in trend_sites], "trends": trends}


def fitted(fit: dict, key: str, tc: float, camber: float, re: float) -> float:
    """One fitted quantity at a section. Outside the sites' box in (t/c, camber) it is
    held at the box's edge; outside the measured Reynolds numbers its trend stops."""
    x = np.clip(np.array([tc, camber]), fit["lo"], fit["hi"])
    row = np.array([1.0] + [x[j] - fit["mean"][j] for j in fit["used"]])
    d_re = float(np.clip(np.log10(re), *fit["log_re_range"])) - fit["log_re_ref"]
    return float(row @ np.array(fit["planes"][key]) + _spread(fit["sites"], fit["left"][key], x)
                 + _spread(fit["trend_sites"], fit["trends"][key], x) * d_re)


def corrections(fit: dict | None, v0: TableV0, family: str, tc: float, camber: float,
                re: float) -> dict:
    """The seven numbers `apply` moves one v0 polar with.

    The two ends are the referee's OWN ends (a plane in thickness and camber fits
    them twice as well as it fits their distance from v0, whose ends are
    irregular); the shift is what brings v0's ends there. Outside the box in
    (t/c, camber) the shift of the box's edge is kept, so v0's trend in thickness
    and camber carries on from the last measured section. In Reynolds number the
    ends themselves are kept outside the measured range: the referee has them move
    0.1-0.2 deg per octave where v0 moves them 0.5-0.7."""
    if fit is None:
        return dict(NEUTRAL)
    tc_c, camber_c = np.clip(np.array([tc, camber]), fit["lo"], fit["hi"])
    a, cl, cd, _ = v0.polar(family, float(tc_c), float(camber_c), re)
    f0 = features(a, cl, cd)
    out = {key: fitted(fit, key, tc, camber, re) for key in OFFSETS}
    lower = fitted(fit, "lower", tc, camber, re)
    out["d_lower"] = lower - f0["lower"]
    out["d_lower_out"] = lower - max(out["step"], 0.05) - f0["lower_out"]
    out["d_upper"] = fitted(fit, "upper", tc, camber, re) - f0["upper"]
    return out


def build(v0: TableV0, fits: dict) -> dict:
    """v1 on grids fine enough that the library's plain interpolation between
    neighbouring nodes has little left to smear: the ends of the attached range
    move about 1 deg per 0.01 of t/c, so 0.005 steps leave half a degree; in
    Reynolds number half octaves, with the referee's own (the most common one of
    the nodes is 5.7e5 = 4e5 x sqrt 2) on the grid."""
    a = np.unique(np.concatenate([v0.t["alpha"], np.arange(ALPHA_QUARTER[0],
                                                           ALPHA_QUARTER[1] + 1e-9, 0.25)]))
    out = {"alpha": a, "reynolds": RE_FINE, "tc": TC_FINE, "tc_cambered": TC_CAMBERED_FINE,
           "camber": CAMBER_FINE}
    for fam in ("symmetric", "flat_inside"):
        block = np.empty((3, len(TC_FINE), len(RE_FINE), len(a)))
        for i, tc in enumerate(TC_FINE):
            for r, re in enumerate(RE_FINE):
                corr = corrections(fits.get(fam), v0, fam, float(tc), 0.0, float(re))
                block[:, i, r] = apply(*v0.polar(fam, float(tc), 0.0, float(re)), corr, a)
        for k, key in enumerate(("cl", "cd", "cm")):
            out[f"{fam}_{key}"] = block[k]
    block = np.empty((3, len(TC_CAMBERED_FINE), len(CAMBER_FINE), len(RE_FINE), len(a)))
    for i, tc in enumerate(TC_CAMBERED_FINE):
        for m, camber in enumerate(CAMBER_FINE):
            for r, re in enumerate(RE_FINE):
                # The camber-free row of the cambered block belongs to the cambered
                # family here: it takes the shift of the least cambered section
                # measured, like every other row outside the box. Left as v0 (as the
                # symmetric family is until it has sections of its own) it sat two
                # degrees of knee above the 0.5 % row next to it, and a search found
                # the seam.
                corr = corrections(fits.get("cambered"), v0, "cambered", float(tc),
                                   float(camber), float(re))
                block[:, i, m, r] = apply(*v0.polar("cambered", float(tc), float(camber),
                                                    float(re)), corr, a)
    for k, key in enumerate(("cl", "cd", "cm")):
        out[f"cambered_{key}"] = block[k]
    return {k: np.asarray(v, dtype=np.float32) for k, v in out.items()}


def shipped(path: Path, node: dict) -> tuple:
    """The node's section as fingen reads it from the table at `path` — the library's
    own lookup, so the report tests what the model is given and not this script's
    formula."""
    from fingen import sections
    from fingen.params import FoilFamily

    if path.parent != sections._DATA:
        sections._DATA = path.parent
        sections._table.cache_clear()
        sections._polar.cache_clear()
    pol = sections.polar(FoilFamily(node["family"]), node["tc"], node["re"], node["camber"], "v1")
    return pol.alpha_deg, pol.cl, pol.cd


def left_out(nodes: list[dict], k: int, v0: TableV0) -> dict:
    """Ends of node k predicted from all the other nodes of its family."""
    n = nodes[k]
    others = [m for j, m in enumerate(nodes) if j != k and m["family"] == n["family"]]
    if not others:
        return {"lower": float("nan"), "upper": float("nan")}
    corr = corrections(fit_family(others), v0, n["family"], n["tc"], n["camber"], n["re"])
    a0, cl0, cd0, cm0 = v0.polar(n["family"], n["tc"], n["camber"], n["re"])
    cl1, cd1, _ = apply(a0, cl0, cd0, cm0, corr)
    return features(a0, cl1, cd1)


def report(nodes: list[dict], fits: dict, v0: TableV0, path: Path) -> str:
    lines = ["# Section table v1 at the referee's nodes", "",
             "v1 is read here the way fingen reads it (`sections.polar` on the shipped file). "
             "\"Left out\" is the end predicted for a node by a table built without it: "
             "how well the table is known between its nodes.", "",
             "| section | lower end °: RANS / v0 / v1 / left out | "
             "upper end °: RANS / v0 / v1 / left out | "
             "drag level v1 / v0 | lift slope v1 / v0 | lift retention | "
             "cd v1 / RANS over the settled rows: "
             "min … max | largest cl difference |", "|---|---|---|---|---|---|---|---|"]
    miss = {"lower": [], "upper": []}
    for k, n in enumerate(nodes):
        corr = corrections(fits.get(n["family"]), v0, n["family"], n["tc"], n["camber"], n["re"])
        a1, cl1, cd1 = shipped(path, n)
        f1, loo = features(a1, cl1, cd1), left_out(nodes, k, v0)
        ok = n["settled"]
        ratio = np.interp(n["alpha"][ok], a1, cd1) / n["cd"][ok]
        dcl = np.abs(np.interp(n["alpha"][ok], a1, cl1) - n["cl"][ok]).max()
        for end in miss:
            miss[end].append((n["family"], loo[end] - n["rans"][end]))
        lines.append(f"| {n['name']} | {n['rans']['lower']:+.2f} / {n['v0']['lower']:+.2f} / "
                     f"{f1['lower']:+.2f} / {loo['lower']:+.2f} | {n['rans']['upper']:+.2f} / "
                     f"{n['v0']['upper']:+.2f} / {f1['upper']:+.2f} / {loo['upper']:+.2f} | "
                     f"{np.exp(corr['log_level']):.3f} | {corr['slope']:.3f} | "
                     f"{corr['retention']:.2f} | "
                     f"{ratio.min():.2f} … {ratio.max():.2f} | {dcl:.3f} |")
    for fam, fit in fits.items():
        span = [("t/c", "camber")[j] for j in fit["used"]] or "a constant"
        re_lo, re_hi = (10.0 ** v for v in fit["log_re_range"])
        lines += ["", f"{fam}: {len(fit['nodes'])} nodes at {len(fit['sites'])} sections, "
                      f"Reynolds number {re_lo:.2g} … {re_hi:.2g} "
                      f"({len(fit['trend_sites'])} section(s) at more than one); "
                      f"plane over {span}; "
                      f"the plane alone misses a section by at most "
                      + ", ".join(f"{k} {v:.3f}" for k, v in fit["max_residual"].items())
                      + " (spread back in around each section)."]
        if fit["trend_sites"]:
            lines += ["  Per octave of Reynolds number (mean over those sections): "
                      + ", ".join(f"{k} {np.mean(v) * np.log10(2.0):+.3f}"
                                  for k, v in fit["trends"].items()) + "."]
        for end, rows in miss.items():
            d = np.array([v for f, v in rows if f == fam and np.isfinite(v)])
            if len(d):
                lines += [f"  Left out, {end} end: rms {np.sqrt((d ** 2).mean()):.2f} deg, "
                          f"largest {np.abs(d).max():.2f} deg over {len(d)} nodes."]
    return "\n".join(lines)


def main() -> None:
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    out_path = Path(opt.get("out", REPO / "src/fingen/data/sections_v1.npz")).resolve()
    if out_path.name != "sections_v1.npz":
        raise SystemExit("--out must be named sections_v1.npz (the report reads it through fingen)")
    v0 = TableV0()
    nodes = load_nodes(v0)
    fits = {fam: fit_family([n for n in nodes if n["family"] == fam])
            for fam in sorted({n["family"] for n in nodes})}
    data = build(v0, fits)
    meta = {**v0.meta, "version": 1, "built": datetime.date.today().isoformat(),
            "source": "table v0 (neuralfoil) warped onto resolved-wall 2-D RANS sections",
            "method": "scripts/build_section_table_v1.py", "fits": fits,
            # fingen.sections reads a camber-free cambered foil from the cambered block
            "cambered_zero_row": "own",
            "status": "provisional: families without a finished RANS section are v0 unchanged; "
                      "outside the sections' box in (t/c, camber) v0's trend carries on from the "
                      "box's edge; outside the measured Reynolds numbers the ends of the attached "
                      "range are kept (see fits)"}
    data["meta"] = np.array(json.dumps(meta))
    np.savez_compressed(out_path, **data)
    text = report(nodes, fits, v0, out_path)
    print(text)
    print(f"\nwrote {out_path} ({out_path.stat().st_size / 1e3:.0f} kB)")
    if "report" in opt:
        Path(opt["report"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
