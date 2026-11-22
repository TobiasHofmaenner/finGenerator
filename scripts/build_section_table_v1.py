"""Build section table v1: table v0 moved onto the resolved-wall RANS sections.

    uv run python scripts/build_section_table_v1.py [--out=DIR/sections_v1.npz] [--report=PATH.md]
                                                    [--sections=rerun-held]

Table v0 (NeuralFoil, tripped; scripts/build_section_table.py) covers every
section fingen can draw; the referee (resolved-wall 2-D RANS on the exact
outline, bench/section-tables/rerun and bench/section-tables/nose) covers a few
dozen. Where the two overlap v0 has the wrong shape at both ends of the
attached range: its drag creeps up over the last two degrees and it has no end,
where the referee stays low up to a break a quarter degree wide and is
separated behind it. Its ends are also up to a degree off, its lift slope 3–4 %
high and its drag level a few percent off. v1 is v0 put right at the referee's
sections and carried in between:

    cd_v1(a) = F(s) * cd_v0(w(a))
    cl_v1(a) = slope * (line_v0(a - d_alpha0) + keep * remainder_v0(w(a))) + H(s)
    cm_v1(a) = cm_v0(w(a))

`w` maps the angle piecewise linearly through five marks (MARKS): the foot of
the lower cliff, the lower end, the centre of the low-drag range, the upper
end, the foot of the upper cliff. The centre stays, v0's ends move onto the
referee's. `s` is the same position counted between the marks (-1 at the lower
end, 0 at the centre, +1 at the upper end): the coordinate in which two
sections are compared. `remainder` is what v0's lift does besides its straight
line. F and H are what the referee's rows still differ by after the move: a
drag ratio and a lift difference at 121 places inside the range. The lift
difference is kept in units of the lift the line gains between the centre and
that end, so a section with a shorter range gets a proportionally smaller one.
Behind either end the referee's rows are kept as STEPS from the value at the
end, every quarter degree for three degrees (drag behind over drag at the end;
lift behind less lift at the end, in the same unit); further out v0's shape
carries on from the last of them. At the end itself the drag is the last row's.

Per section the referee therefore gives (FITTED): the two ends, the width of
either cliff, a drag level, a lift-slope ratio, a zero-lift shift, a retention
factor on v0's roll-off, the two residual curves, and the steps of drag and
lift behind either end. Each is carried to the rest of the grid per foil family
(`fit_family`, `fitted`). The symmetric sections are the cambered family's
camber-free row (fingen.foil draws one outline for both): the two share a fit
(FIT_OF), and a symmetric section is built from its upper half and mirrored.

  * a least-squares plane over (t/c, camber) plus what each section still
    misses, carried between the sections straight from one to the next
    (`_spread`). At a measured section v1 is therefore that section, row for
    row inside its range.
  * The two ENDS are fitted as the referee has them, not as their distance
    from v0 (v0's ends are irregular, the referee's are not).
  * Reynolds number is kept apart, piecewise linear in its logarithm between
    the Reynolds numbers that were run: the slope of each stretch is read at the
    sections run at both of its ends and spread like everything else. Outside
    the Reynolds numbers run, the values of the last one are kept.
  * Outside the sections' box in (t/c, camber) an end is the box edge's, moved
    by what v0's end does between the edge and the section at the reference
    Reynolds number: v0's trend in thickness and camber carries on from the
    last measured section, the trend in Reynolds number is the referee's
    everywhere (`corrections`). A family with no finished section keeps v0
    unchanged.
  * No section has less drag behind an end than at it. Where the fit says so
    (a step carried far in Reynolds number from the sections it was read at)
    the node is built without a step; the scan counts those nodes.

How an end is read. A marched section (the rerun) says where it lets go: a row
is past an end when it did not settle within the iteration cap or has more
than PAST_FACTOR times the section's lowest drag — the rule its march stopped
by. The end is put halfway between the last row inside and the first row past
it, the cliff's foot on that first row. A section run on a fixed list of angles
(the flat-inside one, first recipe), and v0 itself, have no such rows: there
the lower end is where the drag passes K_LOWER times its minimum, the foot
where it passes K_OUT, the upper end where it passes K_UPPER (`features`).

Rows past an end did not settle: steady RANS has no answer for a separated
section, only a mean of something unsteady. They are used for where the end
is, and for drag and lift in the three degrees behind it, never inside the
range.

A row the record marks `cycle` counts as settled. It failed the stopping rule
by swinging about a mean that holds to four digits (a flat inside face at
-2.5 deg on the held stream, shedding from its corner), its neighbours on both
sides settle, and its mean lies on the curve through them. Read as unsettled
it would end the flat-inside range at -1 deg, two rows short of where the
section lets go.

v1 is stored in the ALIGNED layout (fingen.sections): every polar on the
coordinate s, its marks beside it. The library interpolates marks and curves
between neighbouring nodes at equal s, so a section between two nodes has one
cliff at an interpolated angle. Stored on a common grid of angles and
interpolated point by point, the same section had two half-height steps at its
neighbours' angles — in thickness, in camber and in Reynolds number at once —
and the referee's quarter-degree cliff read as a ramp a degree wide.

The report reads the finished table THROUGH THE LIBRARY (`sections.polar`), the
way the model reads it, and adds for every section the ends a table built
without it predicts: how well the table is known between its sections. The
meta block records sections, planes, remainders and Reynolds-number slopes.
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
# The referee's sections: (file under bench/section-tables, families read from it). The
# rerun is on the converged recipe (bench/section-tables/nose). A family read from an
# earlier file is not read again from a later one: the flat-inside family keeps its one
# section from the first recipe only until the rerun has it.
RANS_FILES = (("rerun/results.json", None), ("results.json", ("flat_inside",)))
K_LOWER, K_UPPER = 1.5, 3.0         # ends by drag, where no row says the flow let go (v0)
K_OUT = 2.5                         # ... and the foot of the lower cliff
PAST_FACTOR = 4.0                   # a referee row with this many times its lowest drag: past
CLIFF_MIN_DEG = 0.05                # marks are kept at least this far apart
LIN_RANGE = (0.0, 5.0)              # lift line fitted here: inside every section's attached range
STALL_RAMP_DEG = 2.0
# Behind either cliff's foot the referee's rows are kept at these distances (deg): drag as a
# step from the drag at the end, lift as a step from the lift there. Further out v0's shape
# carries on from the last of them.
BEHIND = np.arange(0.0, 3.01, 0.25)
# v1's grids (v0: 10 thicknesses, 5 cambered thicknesses, 6 cambers). The referee's own
# thicknesses are on them, so a measured section is a node and not a blend of two.
TC_FINE = np.unique(np.round(np.concatenate([np.arange(0.040, 0.1301, 0.005),
                                             [0.15, 0.16, 0.19, 0.22], [0.046, 0.066, 0.092]]), 4))
TC_CAMBERED_FINE = np.unique(np.round(np.concatenate([np.arange(0.050, 0.1201, 0.005),
                                                      [0.135, 0.15, 0.16], [0.066, 0.092]]), 4))
CAMBER_FINE = np.arange(0.0, 0.0501, 0.005)
# v1's Reynolds numbers: half octaves (v0: octaves, 1e5 … 1.6e6), moved onto the referee's own
RE_HALF_OCTAVES = 1e5 * 2.0 ** (0.5 * np.arange(9))
# The aligned layout. Marks sit at S_MARKS for every section; outside them the coordinate
# runs in degrees (DEG_PER_S per unit). KNOTS: where the residual curves are kept.
MARKS = ("lower_out", "lower", "centre", "upper", "upper_out")
S_MARKS = np.array([-1.1, -1.0, 0.0, 1.0, 1.1])
DEG_PER_S = 10.0
# (closer in the outer fifth of the range, where the referee's rows are half a degree apart)
KNOTS = np.unique(np.round(np.concatenate([np.linspace(-0.8, 0.8, 81), np.linspace(0.8, 1.0, 21),
                                           np.linspace(-1.0, -0.8, 21)]), 6))
S_GRID = np.unique(np.round(np.concatenate([
    S_MARKS[0] - np.arange(0.5, 16.01, 0.5) / DEG_PER_S, S_MARKS[0] - BEHIND / DEG_PER_S,
    np.linspace(-1.1, -1.0, 5), KNOTS, np.linspace(1.0, 1.1, 5),
    S_MARKS[-1] + BEHIND / DEG_PER_S, S_MARKS[-1] + np.arange(0.5, 18.01, 0.5) / DEG_PER_S]), 6))
ALPHA_RANGE = (-16.0, 24.0)         # every polar the library hands out spans these angles
# What is fitted over the referee's sections: the two ends of the attached range as
# the referee has them, and what else says how v0 differs.
ENDS = ("lower", "upper")
OFFSETS = ("step", "step_up", "log_level", "log_step_below", "log_step_above", "slope",
           "d_alpha0", "retention", "lift_step_below", "lift_step_above", "g", "h")
FITTED = ENDS + OFFSETS
# (a step of None: v0's own, at the factor of the end it lies behind)
NEUTRAL = {"d_lower": 0.0, "d_lower_out": 0.0, "d_upper": 0.0, "d_upper_out": 0.0,
           "log_level": 0.0, "log_step_below": None, "log_step_above": None, "slope": 1.0,
           "d_alpha0": 0.0, "retention": 1.0, "lift_step_below": np.zeros(len(BEHIND)),
           "lift_step_above": np.zeros(len(BEHIND)),
           "g": np.zeros(len(KNOTS)), "h": np.zeros(len(KNOTS))}
# The symmetric sections are the cambered family's camber-free row (fingen.foil draws the
# same outline for both): one fit for the two, and one polar for the two at zero camber.
FIT_OF = {"symmetric": "cambered", "cambered": "cambered", "flat_inside": "flat_inside"}
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


def features(a: np.ndarray, cl: np.ndarray, cd: np.ndarray, ok: np.ndarray | None = None) -> dict:
    """Marks of a polar read off its drag, and the lift line of the working range.
    `lower` is where the drag starts up below the minimum (K_LOWER x the minimum),
    `lower_out` where the face is out (K_OUT x), `upper` where it passes K_UPPER x
    above the minimum; `upper_out` follows it directly (a polar read this way has
    no cliff there). `ok` marks the rows the minimum is looked for and the lift
    line fitted on (the referee's settled rows; a thin symmetric section has left
    its line before LIN_RANGE ends)."""
    inner = np.nonzero((a >= -8.0) & (a <= 8.0) & (True if ok is None else ok))[0]
    k_min = int(inner[np.argmin(cd[inner])])
    lin = (a >= LIN_RANGE[0]) & (a <= LIN_RANGE[1])
    if ok is not None:
        lin &= ok & (cd < K_LOWER * cd[k_min])
    slope, icpt = np.polyfit(a[lin], cl[lin], 1)
    upper = _crossing(a, cd, k_min, +1, K_UPPER * cd[k_min])
    return {"centre": float(a[k_min]), "cd_min": float(cd[k_min]),
            "lower": _crossing(a, cd, k_min, -1, K_LOWER * cd[k_min]),
            "lower_out": _crossing(a, cd, k_min, -1, K_OUT * cd[k_min]),
            "out_reached": bool(cd[:k_min + 1].max() >= K_OUT * cd[k_min]),
            "upper": upper, "upper_out": upper + CLIFF_MIN_DEG,
            "slope": float(slope), "alpha0": float(-icpt / slope)}


def marched_ends(a: np.ndarray, cd: np.ndarray, settled: np.ndarray) -> dict:
    """Where a marched referee section lets go, at either end: the rows inside its
    attached range (walking out from the lowest drag until the first row that did
    not settle or has more than PAST_FACTOR times that drag), the end halfway
    between the last row inside and the first past it, the cliff's foot on that
    first row. An end the rows do not reach is missing from the result."""
    inner = np.nonzero((a >= -8.0) & (a <= 8.0) & settled)[0]
    k_min = int(inner[np.argmin(cd[inner])])
    past = ~settled | (cd > PAST_FACTOR * cd[k_min])
    lo = hi = k_min
    while lo > 0 and not past[lo - 1]:
        lo -= 1
    while hi < len(a) - 1 and not past[hi + 1]:
        hi += 1
    inside = np.zeros(len(a), dtype=bool)
    inside[lo:hi + 1] = True
    out = {"inside": inside}
    if lo > 0:
        out["lower"], out["lower_out"] = float(0.5 * (a[lo] + a[lo - 1])), float(a[lo - 1])
    if hi < len(a) - 1:
        out["upper"], out["upper_out"] = float(0.5 * (a[hi] + a[hi + 1])), float(a[hi + 1])
    return out


def marks(f: dict, shift: dict | None = None) -> np.ndarray:
    """The five angles of MARKS, in ascending order and at least a little apart
    (`shift`: the corrections d_lower_out, d_lower, d_upper, d_upper_out added first)."""
    d = shift or {}
    centre = f["centre"]
    lower = min(f["lower"] + d.get("d_lower", 0.0), centre - 0.5)
    upper = max(f["upper"] + d.get("d_upper", 0.0), centre + 0.5)
    lower_out = min(f["lower_out"] + d.get("d_lower_out", 0.0), lower - CLIFF_MIN_DEG)
    upper_out = max(f["upper_out"] + d.get("d_upper_out", 0.0), upper + CLIFF_MIN_DEG)
    return np.array([lower_out, lower, centre, upper, upper_out])


def warp(a: np.ndarray, target: np.ndarray, source: np.ndarray) -> np.ndarray:
    """Source angle that the target angle `a` reads from. `target` and `source` are
    the MARKS of the two polars: they map onto each other, linearly in between,
    with unit slope outside the outermost two."""
    return np.where(a < target[0], source[0] + (a - target[0]),
                    np.where(a > target[-1], source[-1] + (a - target[-1]),
                             np.interp(a, target, source)))


def s_of(a: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Position of the angles `a` between the marks `m` (fingen.sections._alpha_of_s,
    the other way round)."""
    return np.where(a < m[0], S_MARKS[0] + (a - m[0]) / DEG_PER_S,
                    np.where(a > m[-1], S_MARKS[-1] + (a - m[-1]) / DEG_PER_S,
                             np.interp(a, m, S_MARKS)))


def alpha_of(s: np.ndarray, m: np.ndarray) -> np.ndarray:
    from fingen.sections import _alpha_of_s
    return _alpha_of_s(s, m, S_MARKS, DEG_PER_S)


def aligned_blend(a: np.ndarray, pol_a: tuple, pol_b: tuple, w: float) -> tuple:
    """Polar a fraction `w` of the way from `pol_a` to `pol_b` (each (cl, cd, cm) on
    `a`), interpolated WITH THE ENDS ALIGNED: the marks are interpolated first, each
    neighbour is warped onto them, and only then are the curves blended. A plain
    blend of two polars whose ranges end at different angles turns one cliff into
    two half-height steps."""
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
    # STALL_RAMP_DEG it gives way to v0's full loss
    past = np.clip((out - target[3]) / STALL_RAMP_DEG, 0.0, 1.0)
    keep = np.where(out > f["centre"], corr["retention"] + (1.0 - corr["retention"]) * past, 1.0)
    # the residuals: the curves inside the range, one value at either cliff's foot and
    # behind it. Across a cliff they run from the one to the other.
    s = s_of(out, target)
    xs = np.concatenate([(S_MARKS[0] - BEHIND / DEG_PER_S)[::-1], KNOTS,
                         S_MARKS[-1] + BEHIND / DEG_PER_S])
    inside = corr["log_level"] + corr["g"]
    below, above = behind_levels(a, cd, f, corr, inside)
    log_f = np.interp(s, xs, np.concatenate([below[::-1], inside, above]))
    span = lift_span(target, corr["slope"] * f["slope"])
    h = corr["h"] * lift_scale(target, corr["slope"] * f["slope"])
    d_cl = np.interp(s, xs, np.concatenate([(h[0] + corr["lift_step_below"] * span[0])[::-1], h,
                                            h[-1] + corr["lift_step_above"] * span[1]]))
    return (corr["slope"] * (line + keep * rem) + d_cl, np.exp(log_f) * np.interp(w, a, cd),
            np.interp(w, a, cm))


def lift_span(target: np.ndarray, slope: float) -> tuple[float, float]:
    """The lift the line gains from the centre to the lower end and to the upper end: the
    unit the lift residual is kept in. A residual kept as a lift difference and carried
    to a section with half the range takes twice its share of the lift there (a soft
    stall of 0.1 became a lift that falls inside the range)."""
    return slope * (target[2] - target[1]), slope * (target[3] - target[2])


def lift_scale(target: np.ndarray, slope: float) -> np.ndarray:
    below, above = lift_span(target, slope)
    return np.where(KNOTS < 0.0, below, above)


def own_step(a: np.ndarray, cd: np.ndarray, f: dict) -> tuple[np.ndarray, np.ndarray]:
    """log of v0's own drag at the distances BEHIND either cliff's foot over its drag
    at that end."""
    m = marks(f)
    return (np.log(np.interp(m[0] - BEHIND, a, cd) / np.interp(m[1], a, cd)),
            np.log(np.interp(m[4] + BEHIND, a, cd) / np.interp(m[3], a, cd)))


def behind_levels(a: np.ndarray, cd: np.ndarray, f: dict, corr: dict,
                  inside: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """log drag factor at the distances BEHIND either cliff's foot. The referee gives
    the STEP there: drag behind the end over drag at the end (`log_step_*`). The
    factor follows from the factor at the end and v0's own step. (Kept as a factor
    on v0 and carried to another section, the drag behind an end came out below the
    drag in front of it at every seventh node of the table.)"""
    out = []
    for k, key, own in zip((0, -1), ("log_step_below", "log_step_above"), own_step(a, cd, f),
                           strict=True):
        step = corr[key]
        out.append(np.full(len(BEHIND), float(inside[k])) if step is None
                   else float(inside[k]) + np.asarray(step) - own)
    return out[0], out[1]


def lift_parts(a, cl, f: dict, w, corr: dict, out=None):
    """(v0's lift line at the shifted zero-lift angle, v0's remainder read at the
    warped angle) on the angles `out` — v1's lift before the slope ratio, the
    retention factor and the residual."""
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
            rows = [aligned_blend(a, at_re("cambered", (i, mm)), at_re("cambered", (i + 1, mm)),
                                  wt) for mm in (m, m + 1)]
            return (a, *aligned_blend(a, rows[0], rows[1], wc))
        family = "symmetric" if family == "cambered" else family
        i, wt = self._bracket(t["tc"], tc)
        return (a, *aligned_blend(a, at_re(family, (i,)), at_re(family, (i + 1,)), wt))


def load_nodes(v0) -> list[dict]:
    nodes = []
    for rel, families in RANS_FILES:
        path = BENCH / rel
        if not path.exists():
            continue
        have = {n["family"] for n in nodes}
        data = json.loads(path.read_text())
        cap = int(data["plan"].get("end_time", 4000))
        for name, sec in data["sections"].items():
            spec, rows = sec["spec"], sorted(sec.get("rows", []), key=lambda r: r["alpha"])
            wall = spec.get("wall", data["plan"].get("wall"))
            # a marched section says itself when it is complete; a fixed list is when all
            # its rows are in
            complete = sec.get("complete", len(rows) >= len(spec["angles"]))
            if (not complete or wall == "wf" or spec["family"] in have
                    or (families and spec["family"] not in families)):
                continue
            if spec["family"] == "symmetric":     # run at positive angles: the rest is its mirror
                rows = sorted(rows + [{**r, "alpha": -r["alpha"], "cl": -r["cl"]} for r in rows
                                      if r["alpha"] > 0.0], key=lambda r: r["alpha"])
            a = np.array([r["alpha"] for r in rows])
            cl = np.array([r["cl"] for r in rows])
            cd = np.array([r["cd"] for r in rows])
            settled = np.array([bool(r.get("cycle")) or r.get("settled", r.get("iters", 0) < cap)
                                for r in rows])
            camber = float(spec.get("camber_ratio") or 0.0)
            fam, tc, re = spec["family"], float(spec["thickness_ratio"]), float(spec["re"])
            a0, cl0, cd0, cm0 = v0.polar(fam, tc, camber, re)
            fr, f0 = features(a, cl, cd, settled), features(a0, cl0, cd0)
            if spec.get("march"):
                ends = marched_ends(a, cd, settled)
                inside = ends.pop("inside")
                fr.update(ends)
                reached = ("lower" in ends, "upper" in ends)
            else:
                # the cliff's width: where the rows end before the face is out, v0's own
                if not fr["out_reached"]:
                    fr["lower_out"] = fr["lower"] - (f0["lower"] - f0["lower_out"])
                inside = settled & (a >= fr["lower"]) & (a <= fr["upper"])
                reached = (True, True)
            corr = dict(NEUTRAL)
            corr.update({"d_lower": fr["lower"] - f0["lower"],
                         "d_upper": fr["upper"] - f0["upper"],
                         "d_lower_out": fr["lower_out"] - f0["lower_out"],
                         "d_upper_out": fr["upper_out"] - f0["upper_out"],
                         "step": fr["lower"] - fr["lower_out"],
                         "step_up": fr["upper_out"] - fr["upper"],
                         "slope": fr["slope"] / f0["slope"],
                         "d_alpha0": fr["alpha0"] - f0["alpha0"]})
            target = marks(f0, corr)
            # lift retention toward the knee: v0 sheds lift gradually over several
            # degrees, the referee holds its line longer. Scale v0's remainder on the
            # rows of the upper half of the range.
            w = warp(a0, target, marks(f0))
            line, rem = lift_parts(a0, cl0, f0, w, corr)
            upper_half = inside & (a > 0.5 * (f0["centre"] + fr["upper"]))
            if upper_half.any():
                r = np.interp(a[upper_half], a0, rem)
                gap = cl[upper_half] / corr["slope"] - np.interp(a[upper_half], a0, line)
                if float(r @ r) > 1e-6:
                    corr["retention"] = float(np.clip((r @ gap) / (r @ r), 0.2, 1.5))
            # what is left after the move, at the rows: drag ratio and lift difference
            cl_w, cd_w, _ = apply(a0, cl0, cd0, cm0, corr, a)
            log_ratio, d_cl, s = np.log(cd / cd_w), cl - cl_w, s_of(a, target)
            # the level: the middle half of the range (the rows crowd toward the ends)
            core = inside & (np.abs(s) <= 0.5)
            corr["log_level"] = float(np.median(log_ratio[core if core.any() else inside]))
            # At an end itself (between the last row inside and the first past it) the
            # drag is the last row's: nothing says it rises before the flow lets go.
            rows_in = np.nonzero(inside)[0]
            s_in, ratio_in = s[inside], log_ratio[inside]
            for mark, k in ((1, rows_in[0]), (3, rows_in[-1])):
                if reached[mark // 3] and abs(a[k] - target[mark]) > 1e-9:
                    at_mark = float(np.interp(warp(target[mark], target, marks(f0)), a0, cd0))
                    s_in = np.append(s_in, S_MARKS[mark])
                    ratio_in = np.append(ratio_in, np.log(cd[k] / at_mark))
            order = np.argsort(s_in)
            corr["g"] = np.interp(KNOTS, s_in[order], ratio_in[order] - corr["log_level"])
            h = np.interp(KNOTS, s[inside], d_cl[inside])
            slope1 = corr["slope"] * f0["slope"]
            corr["h"] = h / lift_scale(target, slope1)
            # Behind either end: the rows within three degrees of the cliff's foot. They did
            # not settle; they say how much drag and lift a separated section has, roughly.
            # Kept as steps from the value at the end (`behind_levels`, `lift_span`).
            foot_lo, foot_hi = target[0], target[-1]
            for side, k, dist, own, span in zip(
                    ("below", "above"), (0, -1), (foot_lo - a, a - foot_hi),
                    own_step(a0, cd0, f0), lift_span(target, slope1), strict=True):
                behind = (dist > -1e-9) & (dist < BEHIND[-1] + 1e-9) & ~inside
                at_end = corr["log_level"] + float(corr["g"][k])
                if behind.any():
                    by = np.argsort(dist[behind])
                    d = dist[behind][by]
                    level = np.interp(BEHIND, d, log_ratio[behind][by])
                    corr[f"log_step_{side}"] = level - at_end + own
                    corr[f"lift_step_{side}"] = (np.interp(BEHIND, d, d_cl[behind][by])
                                                 - h[k]) / span
                else:
                    corr[f"log_step_{side}"] = own
                    corr[f"lift_step_{side}"] = np.zeros(len(BEHIND))
            nodes.append({"name": name, "family": fam, "tc": tc, "camber": camber, "re": re,
                          "alpha": a, "cl": cl, "cd": cd, "settled": settled, "inside": inside,
                          "reached": reached, "rans": fr, "v0": f0, "corr": corr})
    return nodes


def _spread(points, values, x: np.ndarray) -> np.ndarray:
    """`values` (one row per point) given at `points` ((t/c, camber), distances counted
    in NODE_REACH), carried to `x`: a weight on the distance to every point, the weights
    summing to zero, plus a constant. Exactly a point's own row at that point, straight
    from one point to the next along a line of them, and level far from all of them.

    (An inverse-distance mean, used before, is level AROUND every point: between two
    neighbouring sections it drew a step, and beside a section where the plane has a
    slope a bump. Leaving one section out at a time, the two predict its ends equally
    well.)"""
    at = np.asarray(points, dtype=float) / NODE_REACH
    values = np.asarray(values, dtype=float).reshape(len(at), -1)
    n = len(at)
    if n == 1:
        return values[0]
    dist = np.linalg.norm(at[:, None] - at[None], axis=2)
    system = np.block([[dist, np.ones((n, 1))], [np.ones((1, n)), np.zeros((1, 1))]])
    weights = np.linalg.solve(system, np.vstack([values, np.zeros((1, values.shape[1]))]))
    reach = np.linalg.norm(at - np.asarray(x, dtype=float) / NODE_REACH, axis=1)
    return reach @ weights[:n] + weights[n]


def _re_shift(stretches: list[dict], breaks: list[float], x: np.ndarray, log_re: float,
              ref: float) -> np.ndarray | float:
    """What a quantity changes by between the reference Reynolds number and `log_re`
    at the section `x`: its slope in every stretch between two Reynolds numbers that
    were run (spread over the sections run at both), summed from the one to the other.
    Outside the Reynolds numbers run there is no further change."""
    if not breaks:
        return 0.0
    at = float(np.clip(log_re, breaks[0], breaks[-1]))
    total = 0.0
    for (b0, b1), st in zip(zip(breaks[:-1], breaks[1:], strict=True), stretches, strict=True):
        lo, hi = max(min(ref, at), b0), min(max(ref, at), b1)
        if hi > lo and st["sites"]:
            sign = 1.0 if at > ref else -1.0
            total = total + sign * (hi - lo) * _spread(st["sites"], st["slopes"], x)
    return total


def fit_family(nodes: list[dict]) -> dict:
    """What the referee says about one foil family, as functions of the section.

    Per quantity (FITTED; the residual curves are fitted knot by knot): its change
    with Reynolds number, read at the SITES — a site is one (t/c, camber) — that
    were run at more than one; every site brought to the reference Reynolds number
    with it; a least-squares plane over (t/c, camber) in the directions the sites
    span; and what each site still misses, spread to its neighbourhood (`_spread`).
    At a node the result is that node's own value — v1 reproduces the referee where
    it has been asked."""
    key_of = [(round(n["tc"], 6), round(n["camber"], 6)) for n in nodes]
    sites = sorted(set(key_of))
    member = [np.array([k for k, key in enumerate(key_of) if key == s]) for s in sites]
    log_re = np.round(np.log10([n["re"] for n in nodes]), 4)
    levels, counts = np.unique(log_re, return_counts=True)
    ref = float(levels[np.argmax(counts)])            # the Reynolds number most nodes ran at
    xy = np.array(sites)
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    used = [j for j in range(2) if hi[j] - lo[j] > 1e-9]
    while len(used) + 1 > len(sites):                 # fewer sites than terms: drop the last
        used.pop()
    design = np.column_stack([np.ones(len(sites))] + [xy[:, j] - xy[:, j].mean() for j in used])
    multi = [k for k, m in enumerate(member) if np.ptp(log_re[m]) > 1e-6]
    breaks = sorted({float(v) for k in multi for v in log_re[member[k]]})
    planes, left, slopes, resid = {}, {}, {}, {}
    for key in FITTED:
        y = np.array([np.atleast_1d(n["rans"][key] if key in ENDS else n["corr"][key])
                      for n in nodes], dtype=float)
        # a stretch between two Reynolds numbers: the sites with a node at or beyond both
        stretches = []
        for b0, b1 in zip(breaks[:-1], breaks[1:], strict=True):
            st = {"sites": [], "slopes": []}
            for k in multi:
                m = member[k][np.argsort(log_re[member[k]])]
                if log_re[m[0]] <= b0 + 1e-9 and log_re[m[-1]] >= b1 - 1e-9:
                    at = [np.array([np.interp(b, log_re[m], y[m, j]) for j in range(y.shape[1])])
                          for b in (b0, b1)]
                    st["sites"].append(list(sites[k]))
                    st["slopes"].append(((at[1] - at[0]) / (b1 - b0)).tolist())
            stretches.append(st)
        slopes[key] = stretches
        at_ref = np.array([np.mean([y[i] - _re_shift(stretches, breaks, xy[k],
                                                     float(log_re[i]), ref) for i in m], axis=0)
                           for k, m in enumerate(member)])
        coef, *_ = np.linalg.lstsq(design, at_ref, rcond=None)
        planes[key] = coef.tolist()
        left[key] = (at_ref - design @ coef).tolist()
        resid[key] = float(np.abs(design @ coef - at_ref).max())
    return {"lo": lo.tolist(), "hi": hi.tolist(), "mean": xy.mean(axis=0).tolist(), "used": used,
            "sites": [list(s) for s in sites], "planes": planes, "left": left,
            "max_residual": resid, "nodes": [n["name"] for n in nodes],
            "log_re_ref": ref, "re_breaks": breaks, "re_slopes": slopes,
            "log_re_range": [float(log_re.min()), float(log_re.max())]}


def fitted(fit: dict, key: str, tc: float, camber: float, re: float):
    """One fitted quantity at a section (a number, or the curve at KNOTS). Outside the
    sites' box in (t/c, camber) it is held at the box's edge; outside the Reynolds
    numbers run it is held at the last one."""
    x = np.clip(np.array([tc, camber]), fit["lo"], fit["hi"])
    row = np.array([1.0] + [x[j] - fit["mean"][j] for j in fit["used"]])
    v = (row @ np.asarray(fit["planes"][key], dtype=float)
         + _spread(fit["sites"], fit["left"][key], x)
         + _re_shift(fit["re_slopes"][key], fit["re_breaks"], x, float(np.log10(re)),
                     fit["log_re_ref"]))
    v = np.atleast_1d(v)
    return float(v[0]) if v.size == 1 else v


def corrections(fit: dict | None, v0: TableV0, family: str, tc: float, camber: float,
                re: float) -> dict:
    """What `apply` moves one v0 polar with.

    The two ends are the referee's OWN ends (a plane in thickness and camber fits
    them better than it fits their distance from v0, whose ends are irregular);
    the shift is what brings v0's ends there. Outside the box in (t/c, camber) the
    end of the box's edge is carried on by what v0's end does between the edge and
    the section AT THE REFERENCE REYNOLDS NUMBER; how an end moves with Reynolds
    number is the referee's everywhere. (v0's own ends move with Reynolds number in
    either direction, depending on the section: a thin symmetric one's upper end,
    read off its drag, comes IN by a degree per octave. Carried on at every Reynolds
    number separately, that gave a t/c 0.04 section 5.4 deg of range at Re 2.8e5 and
    2.4 deg at 1.6e6.) In Reynolds number the ends themselves are kept outside the
    range that was run."""
    if fit is None:
        return dict(NEUTRAL)
    a, cl, cd, _ = v0.polar(family, tc, camber, re)
    f0 = features(a, cl, cd)
    out = {key: fitted(fit, key, tc, camber, re) for key in OFFSETS}
    lower, upper = ends_at(fit, v0, family, tc, camber, re)
    for key in ("log_step_below", "log_step_above"):
        out[key] = np.maximum(out[key], 0.0)        # no less drag behind an end than at it
    out["d_lower"] = lower - f0["lower"]
    out["d_lower_out"] = lower - max(out["step"], CLIFF_MIN_DEG) - f0["lower_out"]
    out["d_upper"] = upper - f0["upper"]
    out["d_upper_out"] = upper + max(out["step_up"], CLIFF_MIN_DEG) - f0["upper_out"]
    return out


def ends_at(fit: dict, v0: TableV0, family: str, tc: float, camber: float,
            re: float) -> tuple[float, float]:
    """The two ends of a section's attached range as a fit has them (see `corrections`)."""
    lower, upper = (fitted(fit, key, tc, camber, re) for key in ENDS)
    tc_c, camber_c = (float(v) for v in np.clip(np.array([tc, camber]), fit["lo"], fit["hi"]))
    if abs(tc_c - tc) > 1e-9 or abs(camber_c - camber) > 1e-9:
        re_ref = 10.0 ** fit["log_re_ref"]
        here, edge = (features(*v0.polar(family, t, c, re_ref)[:3])
                      for t, c in ((tc, camber), (tc_c, camber_c)))
        lower += here["lower"] - edge["lower"]
        upper += here["upper"] - edge["upper"]
    return lower, upper


def re_grid(nodes: list[dict]) -> np.ndarray:
    """Half octaves, with the referee's own Reynolds numbers in place of the half
    octave next to them (5.7e5 for 5.66e5) or added (9.7e5): a measured section is
    then a node of the table."""
    grid = list(RE_HALF_OCTAVES)
    for re in sorted({n["re"] for n in nodes}):
        k = int(np.argmin(np.abs(np.log(np.array(grid) / re))))
        if abs(np.log(grid[k] / re)) < 0.03:
            grid[k] = re
        else:
            grid.append(re)
    return np.array(sorted(grid))


def build(v0: TableV0, fits: dict, reynolds: np.ndarray) -> dict:
    """v1 in the aligned layout: per node its five marks, the lift line (slope and
    zero-lift angle), and on S_GRID what the lift does besides that line, the drag
    and the moment."""
    out = {"s": S_GRID, "s_marks": S_MARKS, "reynolds": reynolds, "tc": TC_FINE,
           "tc_cambered": TC_CAMBERED_FINE, "camber": CAMBER_FINE}

    def node(fam: str, tc: float, camber: float, re: float) -> tuple:
        corr = corrections(fits.get(FIT_OF[fam]), v0, fam, tc, camber, re)
        a, cl, cd, cm = v0.polar(fam, tc, camber, re)
        f = features(a, cl, cd)
        m = marks(f, corr)
        alpha = alpha_of(S_GRID, m)
        cl1, cd1, cm1 = apply(a, cl, cd, cm, corr, alpha)
        slope, alpha0 = corr["slope"] * f["slope"], f["alpha0"] + corr["d_alpha0"]
        if fam == "symmetric" or camber == 0.0 and fam == "cambered":
            return mirrored(m, slope, cl1, cd1, cm1)
        return m, slope, alpha0, cl1 - slope * (alpha - alpha0), cd1, cm1

    def store(key: str, shape: tuple, cells: list) -> None:
        for k, (name, tail) in enumerate((("marks", (len(MARKS),)), ("slope", ()), ("alpha0", ()),
                                          ("rem", (len(S_GRID),)), ("cd", (len(S_GRID),)),
                                          ("cm", (len(S_GRID),)))):
            out[f"{key}_{name}"] = np.array([c[k] for c in cells]).reshape(shape + tail)

    for fam in ("symmetric", "flat_inside"):
        store(fam, (len(TC_FINE), len(reynolds)),
              [node(fam, float(tc), 0.0, float(re)) for tc in TC_FINE for re in reynolds])
    # The camber-free row of the cambered block is the symmetric section of that
    # thickness, from the same fit as the rows beside it (FIT_OF): no seam for a search
    # to find between no camber and a little. (Left as v0 while the cambered rows were
    # moved, it once sat two degrees of knee above the 0.5 % row next to it.)
    store("cambered", (len(TC_CAMBERED_FINE), len(CAMBER_FINE), len(reynolds)),
          [node("cambered", float(tc), float(camber), float(re))
           for tc in TC_CAMBERED_FINE for camber in CAMBER_FINE for re in reynolds])
    return {k: np.asarray(v, dtype=np.float32) for k, v in out.items()}


def mirrored(m: np.ndarray, slope: float, cl: np.ndarray, cd: np.ndarray,
             cm: np.ndarray) -> tuple:
    """A symmetric section's node from its upper half (centre to upper end and behind
    it): the lower half is the mirror image. Marks, lift line (through zero), lift
    remainder, drag, moment — as `build` stores a node."""
    marks_sym = np.array([-m[4], -m[3], 0.0, m[3], m[4]])
    alpha = alpha_of(S_GRID, marks_sym)
    up = S_GRID >= 0.0
    rem_up = (cl - slope * alpha)[up]
    rem_up = rem_up - rem_up[0]                       # no lift at no incidence
    at, sign = np.abs(S_GRID), np.sign(S_GRID)
    return (marks_sym, slope, 0.0, sign * np.interp(at, S_GRID[up], rem_up),
            np.interp(at, S_GRID[up], cd[up]), sign * np.interp(at, S_GRID[up], cm[up]))


def shipped(path: Path, node: dict):
    """The node's section as fingen reads it from the table at `path` — the library's
    own lookup, so the report tests what the model is given and not this script's
    formula."""
    from fingen import sections
    from fingen.params import FoilFamily

    if path.parent != sections._DATA:
        sections._DATA = path.parent
        sections._table.cache_clear()
        sections._polar.cache_clear()
    return sections.polar(FoilFamily(node["family"]), node["tc"], node["re"], node["camber"], "v1")


def left_out(nodes: list[dict], k: int, v0: TableV0) -> dict:
    """Ends of node k predicted from the other SECTIONS of its family: every node of its
    own section (the same t/c and camber at another Reynolds number) is left out with
    it, and the ends are found the way the table finds them (`ends_at`)."""
    n = nodes[k]
    others = [m for m in nodes if FIT_OF[m["family"]] == FIT_OF[n["family"]]
              and (abs(m["tc"] - n["tc"]) > 1e-9 or abs(m["camber"] - n["camber"]) > 1e-9)]
    if not others:
        return {"lower": float("nan"), "upper": float("nan")}
    lower, upper = ends_at(fit_family(others), v0, n["family"], n["tc"], n["camber"], n["re"])
    return {"lower": lower, "upper": upper}


def report(nodes: list[dict], fits: dict, v0: TableV0, path: Path) -> str:
    lines = ["# Section table v1 at the referee's sections", "",
             "v1 is read here the way fingen reads it (`sections.polar` on the shipped file). An "
             "end is halfway between the referee's last row inside the attached range and its "
             "first row past it (a bracket of a quarter degree where the march bisected); v0's is "
             "where its drag passes 1.5 times (lower) and 3 times (upper) its minimum. \"Left "
             "out\" is the end predicted for a section by a table built without it (at any "
             "Reynolds number): how well the table is known between its sections. The break "
             "is the model's (`SectionPolar.alpha_break_deg`: the lift slope has fallen below "
             "30 % of the line's).", "",
             "| section | lower end °: referee / v0 / v1 / left out | "
             "upper end °: referee / v0 / v1 / left out | "
             "drag level v1 / v0 | lift slope v1 / v0 | "
             "inside the range: c_d v1 / referee, min … max | largest c_l difference | "
             "break °, c_l there: v0 / v1 | referee's highest settled c_l (at °) |",
             "|---|---|---|---|---|---|---|---|---|"]
    miss = {"lower": [], "upper": []}
    from fingen import sections
    from fingen.params import FoilFamily
    # v0 as the library reads it, before `shipped` points the library at the new file
    v0_read = [sections.polar(FoilFamily(n["family"]), n["tc"], n["re"], n["camber"], "v0")
               for n in nodes]
    for k, n in enumerate(nodes):
        corr = corrections(fits.get(FIT_OF[n["family"]]), v0, n["family"], n["tc"], n["camber"],
                           n["re"])
        p1, p0 = shipped(path, n), v0_read[k]
        loo = left_out(nodes, k, v0)
        ok = n["inside"] & n["settled"]
        ratio = p1.cd_at(n["alpha"][ok]) / n["cd"][ok]
        dcl = np.abs(p1.cl_at(n["alpha"][ok]) - n["cl"][ok]).max()
        top = int(np.argmax(np.where(ok, n["cl"], -np.inf)))
        cells = []
        for j, end in enumerate(ENDS):
            if n["reached"][j]:
                miss[end].append((FIT_OF[n["family"]], loo[end] - n["rans"][end]))
            cells.append(f"{n['rans'][end]:+.2f}{'' if n['reached'][j] else ' (not reached)'} / "
                         f"{n['v0'][end]:+.2f} / {p1.attached_deg[j]:+.2f} / {loo[end]:+.2f}")
        lines.append(f"| {n['name']} | {cells[0]} | {cells[1]} | "
                     f"{np.exp(corr['log_level']):.3f} | {corr['slope']:.3f} | "
                     f"{ratio.min():.3f} … {ratio.max():.3f} | {dcl:.4f} | "
                     f"{p0.alpha_break_deg:.2f}, {p0.cl_break:.3f} / {p1.alpha_break_deg:.2f}, "
                     f"{p1.cl_break:.3f} | {n['cl'][top]:.3f} ({n['alpha'][top]:+.2f}) |")
    for fam, fit in fits.items():
        span = [("t/c", "camber")[j] for j in fit["used"]] or "a constant"
        re_lo, re_hi = (10.0 ** v for v in fit["log_re_range"])
        scalar = {k: v for k, v in fit["max_residual"].items() if k not in ("g", "h")}
        lines += ["", f"{fam}: {len(fit['nodes'])} nodes at {len(fit['sites'])} sections, "
                      f"Reynolds number {re_lo:.2g} … {re_hi:.2g}; plane over {span}; "
                      f"the plane alone misses a section by at most "
                      + ", ".join(f"{k} {v:.3f}" for k, v in scalar.items())
                      + " (spread back in around each section)."]
        stretches = zip(fit["re_breaks"][:-1], fit["re_breaks"][1:], strict=True)
        for (b0, b1), lo_st, up_st in zip(stretches, fit["re_slopes"]["lower"],
                                          fit["re_slopes"]["upper"], strict=True):
            if lo_st["sites"]:
                octave = np.log10(2.0)
                lines += [f"  Reynolds number {10 ** b0:.2g} … {10 ** b1:.2g} "
                          f"({len(lo_st['sites'])} section(s)): per octave the lower end moves "
                          f"{np.mean(lo_st['slopes']) * octave:+.2f}°, the upper end "
                          f"{np.mean(up_st['slopes']) * octave:+.2f}°."]
        for end, rows in miss.items():
            d = np.array([v for f, v in rows if f == fam and np.isfinite(v)])
            if len(d):
                lines += [f"  Left out, {end} end: rms {np.sqrt((d ** 2).mean()):.2f} deg, "
                          f"largest {np.abs(d).max():.2f} deg over {len(d)} nodes."]
    return "\n".join(lines)


def scan(path: Path) -> list[str]:
    """Every node of the table at `path`, read through the library and looked at for what
    a polar must not do: drag that is not positive, lift that falls inside the attached
    range, a range shorter than three degrees, a break outside the range, a lift line off
    any section's. Says how many nodes do, and the worst of each kind."""
    from fingen import sections
    from fingen.params import FoilFamily

    if path.parent != sections._DATA:
        sections._DATA = path.parent
    sections._table.cache_clear()
    sections._polar.cache_clear()
    t = sections._table("v1")
    grid = [(FoilFamily(fam), float(tc), 0.0, float(re), t[f"{fam}_marks"][i, k])
            for fam in ("symmetric", "flat_inside") for i, tc in enumerate(t["tc"])
            for k, re in enumerate(t["reynolds"])]
    grid += [(FoilFamily.CAMBERED, float(tc), float(c), float(re), t["cambered_marks"][i, j, k])
             for i, tc in enumerate(t["tc_cambered"]) for j, c in enumerate(t["camber"])
             for k, re in enumerate(t["reynolds"])]
    found: dict[str, list] = {}

    def note(kind: str, size: float | None, where: str) -> None:
        found.setdefault(kind, []).append((size, where))

    for fam, tc, camber, re, m in grid:
        pol = sections.polar(fam, tc, re, camber, "v1")
        where = f"{fam.value} t/c {tc:.3f} camber {100 * camber:.1f} % Re {re:.3g}"
        lo, hi = pol.attached_deg
        inside = (pol.alpha_deg >= lo) & (pol.alpha_deg <= hi)
        if pol.cd.min() <= 0.0:
            note("drag not positive", float(-pol.cd.min()), where)
        upper_half = inside & (pol.alpha_deg >= pol.alpha_cd_min_deg)
        peak = float(pol.cl[upper_half].max())
        drop = 1.0 - float(pol.cl[upper_half][-1]) / peak
        if drop > 0.02:      # the referee's own sections: 0.7 % at most
            note("lift at the upper end below its peak inside the range (share of the peak)",
                 drop, where)
        for name, end, foot in (("lower", m[1], m[0]), ("upper", m[3], m[4])):
            step = float(pol.cd_at(foot) / pol.cd_at(end))
            if step < 1.001:
                note(f"no drag step at the {name} end (the fit gave less drag behind it than "
                     "at it, or the same; the node is built with the same)", None, where)
        if hi - lo < 3.0:
            note("attached range shorter than 3 deg (length)", 3.0 - (hi - lo), where)
        peak = float(pol.cd[inside].max() / pol.cd_min)
        if peak > 1.5 * PAST_FACTOR:
            note("drag inside the range over 6 x its minimum (ratio)", peak, where)
        if not lo - 0.5 <= pol.alpha_break_deg <= hi + 2.5:
            note("break outside the attached range (deg past its upper end)",
                 abs(pol.alpha_break_deg - hi), where)
        if not 4.5 <= pol.slope_per_rad <= 7.5:
            note("lift slope outside 4.5 … 7.5 per rad", abs(pol.slope_per_rad - 6.0), where)
    lines = ["", f"Scan of all {len(grid)} nodes of the table: "
                 + ("nothing found." if not found else "")]
    for kind, rows in found.items():
        if rows[0][0] is None:
            lines.append(f"  {kind}: {len(rows)} nodes.")
            continue
        size, where = max(rows)
        lines.append(f"  {kind}: {len(rows)} nodes, worst {size:.3g} at {where}.")
    return lines


def _plain(obj):
    """Arrays as lists, all the way down (the meta block is JSON)."""
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj.tolist() if isinstance(obj, np.ndarray) else obj


def main() -> None:
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    if "sections" in opt:           # the referee's sections from another record, e.g. rerun-held
        global RANS_FILES
        RANS_FILES = ((f"{opt['sections']}/results.json", None),) + RANS_FILES[1:]
    out_path = Path(opt.get("out", REPO / "src/fingen/data/sections_v1.npz")).resolve()
    if out_path.name != "sections_v1.npz":
        raise SystemExit("--out must be named sections_v1.npz (the report reads it through fingen)")
    v0 = TableV0()
    nodes = load_nodes(v0)
    fits = {fit: fit_family([n for n in nodes if FIT_OF[n["family"]] == fit])
            for fit in sorted({FIT_OF[n["family"]] for n in nodes})}
    data = build(v0, fits, re_grid(nodes))
    meta = {**v0.meta, "version": 1, "built": datetime.date.today().isoformat(),
            "source": "table v0 (neuralfoil) moved onto resolved-wall 2-D RANS sections",
            "method": "scripts/build_section_table_v1.py", "fits": _plain(fits),
            "layout": "aligned", "deg_per_s": DEG_PER_S, "alpha_range": list(ALPHA_RANGE),
            "marks": list(MARKS),
            # fingen.sections reads a camber-free cambered foil from the cambered block
            "cambered_zero_row": "own",
            "status": "provisional: families without a finished RANS section are v0 unchanged; "
                      "outside the sections' box in (t/c, camber) v0's trend carries on from the "
                      "box's edge; outside the Reynolds numbers run the values of the last one "
                      "are kept (see fits)"}
    data["meta"] = np.array(json.dumps(meta))
    np.savez_compressed(out_path, **data)
    text = report(nodes, fits, v0, out_path) + "\n" + "\n".join(scan(out_path))
    print(text)
    print(f"\nwrote {out_path} ({out_path.stat().st_size / 1e3:.0f} kB)")
    if "report" in opt:
        Path(opt["report"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
