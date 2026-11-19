"""Build section table v1: table v0 moved onto the resolved-wall RANS sections.

    uv run python scripts/build_section_table_v1.py [--out=PATH] [--report=PATH.md]

Table v0 (NeuralFoil, tripped; scripts/build_section_table.py) has the right
shapes and the wrong ends. Against resolved-wall 2-D RANS
(bench/section-tables/) its attached range is a degree or more too wide at
both ends for thin cambered sections, its lift slope 4–5 % high and its drag
level 5–10 % low. The RANS sections are too few and too coarse in angle to be
a table themselves. v1 is therefore v0 WARPED: for every node of the v0 grid

    cd_v1(a) = level * cd_v0(w(a))
    cl_v1(a) = slope * (line_v0(a - d_alpha0) + remainder_v0(w(a)))
    cm_v1(a) = cm_v0(w(a))

where w is a piecewise-linear map of the angle that leaves the centre of the
low-drag range in place and moves v0's two ends onto where the referee has
them, and `remainder` is what v0's lift does besides its straight line (the
roll-off at the knee, the kink of a flat inside face) — carried along with
the ends. Seven numbers per section do the correction: the shift of the lower
end, the shift of the upper end, the drag level inside the range and the one
below its lower end, the lift-slope ratio, the zero-lift shift, and a
retention factor on the remainder above the centre (v0 sheds lift gradually
toward its knee; the RANS sections hold their line almost to the stall).

Those seven are measured at every finished RANS section (`features`, the same
definition on both sources: the lower end is where cd passes 1.5 x its
minimum below the minimum, the upper end where it passes 3 x above it) and
carried to the rest of the grid by a least-squares plane in thickness, camber
and log Reynolds number per foil family, using only the directions the nodes
actually span and held constant outside their bounding box. A family with no
finished section keeps v0 unchanged. The meta block records nodes, planes,
residuals and the box, so a reader of the table can see what is measured and
what is carried.

Rows that did not settle within the iteration cap are used to locate an end
(they say the flow has separated) and for the drag level BELOW the lower end,
never for the level inside the range. Above the upper end v1 keeps v0's
post-stall drag, moved with the end: nothing here referees it.
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
LIN_RANGE = (0.0, 5.0)              # lift line fitted here: inside every section's attached range
STALL_RAMP_DEG = 2.0
CORRECTIONS = ("d_lower", "d_upper", "log_level", "log_level_below", "slope", "d_alpha0",
               "retention")
NEUTRAL = {"d_lower": 0.0, "d_upper": 0.0, "log_level": 0.0, "log_level_below": 0.0,
           "slope": 1.0, "d_alpha0": 0.0, "retention": 1.0}
BELOW_SPAN_DEG = 3.0                # rows this far below the lower end set the level there


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
    """Centre and both ends of the low-drag range, lift line of the working range."""
    inner = np.nonzero((a >= -8.0) & (a <= 8.0))[0]
    k_min = int(inner[np.argmin(cd[inner])])
    lin = (a >= LIN_RANGE[0]) & (a <= LIN_RANGE[1])
    slope, icpt = np.polyfit(a[lin], cl[lin], 1)
    return {"centre": float(a[k_min]), "cd_min": float(cd[k_min]),
            "lower": _crossing(a, cd, k_min, -1, K_LOWER * cd[k_min]),
            "upper": _crossing(a, cd, k_min, +1, K_UPPER * cd[k_min]),
            "slope": float(slope), "alpha0": float(-icpt / slope)}


def warp(a: np.ndarray, centre: float, lower_v0: float, upper_v0: float,
         lower_v1: float, upper_v1: float) -> np.ndarray:
    """v0 angle that the v1 angle `a` reads from: centre fixed, ends moved, unit
    slope outside them."""
    lower_v1 = min(lower_v1, centre - 0.5)
    upper_v1 = max(upper_v1, centre + 0.5)
    lo = (lower_v0 - centre) / (lower_v1 - centre)
    hi = (upper_v0 - centre) / (upper_v1 - centre)
    return np.where(a < lower_v1, lower_v0 + (a - lower_v1),
                    np.where(a > upper_v1, upper_v0 + (a - upper_v1),
                             np.where(a < centre, centre + lo * (a - centre),
                                      centre + hi * (a - centre))))


def apply(a: np.ndarray, cl: np.ndarray, cd: np.ndarray, cm: np.ndarray, corr: dict):
    """One v0 polar -> v1, given its corrections."""
    f = features(a, cl, cd)
    w = warp(a, f["centre"], f["lower"], f["upper"],
             f["lower"] + corr["d_lower"], f["upper"] + corr["d_upper"])
    line, rem = lift_parts(a, cl, f, w, corr)
    # retention holds between the centre and the upper end; over the next
    # STALL_RAMP_DEG it gives way to v0's full loss, so the knee is a maximum
    upper = max(f["upper"] + corr["d_upper"], f["centre"] + 0.5)
    past = np.clip((a - upper) / STALL_RAMP_DEG, 0.0, 1.0)
    keep = np.where(a > f["centre"], corr["retention"] + (1.0 - corr["retention"]) * past, 1.0)
    cl1 = corr["slope"] * (line + keep * rem)
    # drag level: one value inside the range, another below the lower end (a flat
    # inside face is right there in v0 and 20 % low inside), blended across the end
    lower = min(f["lower"] + corr["d_lower"], f["centre"] - 0.5)
    t = np.clip((a - (lower - 1.0)) / 1.5, 0.0, 1.0)
    level = np.exp(corr["log_level_below"] + t * (corr["log_level"] - corr["log_level_below"]))
    return cl1, level * np.interp(w, a, cd), np.interp(w, a, cm)


def lift_parts(a, cl, f: dict, w, corr: dict):
    """(v0's lift line at the shifted zero-lift angle, v0's remainder read at the
    warped angle) — v1's lift before the slope ratio and the retention factor."""
    remainder = cl - f["slope"] * (a - f["alpha0"])
    return f["slope"] * (a - f["alpha0"] - corr["d_alpha0"]), np.interp(w, a, remainder)


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
        t = self.t
        if family == "cambered" and camber > 0.0:
            br = [self._bracket(t["tc_cambered"], tc), self._bracket(t["camber"], camber)]
        else:
            br = [self._bracket(t["tc"], tc)]
            family = "symmetric" if family == "cambered" else family
        br.append(self._bracket(self.log_re, np.log10(re)))
        out = []
        for key in ("cl", "cd", "cm"):
            arr = t[f"{family}_{key}"]
            for i, wgt in br:
                arr = (1.0 - wgt) * arr[i] + wgt * arr[i + 1]
            out.append(arr)
        return t["alpha"], *out


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
            corr = {"d_lower": fr["lower"] - f0["lower"], "d_upper": fr["upper"] - f0["upper"],
                    "log_level": 0.0, "log_level_below": 0.0, "slope": fr["slope"] / f0["slope"],
                    "d_alpha0": fr["alpha0"] - f0["alpha0"], "retention": 1.0}
            # lift retention toward the knee: v0 sheds lift gradually over several
            # degrees, the RANS sections hold their line almost to the stall. Scale
            # v0's remainder on the settled rows of the upper half of the range.
            w = warp(a0, f0["centre"], f0["lower"], f0["upper"], fr["lower"], fr["upper"])
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
            below = (a < fr["lower"] - 0.5) & (a > fr["lower"] - 0.5 - BELOW_SPAN_DEG)
            corr["log_level_below"] = corr["log_level"]
            if below.any():
                corr["log_level_below"] = float(np.clip(np.median(np.log(
                    cd[below] / np.interp(a[below], a0, cd_w))), np.log(0.6), np.log(1.5)))
            nodes.append({"name": name, "family": fam, "tc": tc, "camber": camber, "re": re,
                          "alpha": a, "cl": cl, "cd": cd, "settled": settled,
                          "rans": fr, "v0": f0, "corr": corr})
    return nodes


def fit_family(nodes: list[dict]) -> dict:
    """Least-squares plane of each correction over (t/c, camber, log Re), using only
    the directions the nodes span; evaluation is clamped to their bounding box."""
    x = np.array([[n["tc"], n["camber"], np.log10(n["re"])] for n in nodes])
    lo, hi = x.min(axis=0), x.max(axis=0)
    used = [j for j in range(3) if hi[j] - lo[j] > 1e-9]
    while len(used) + 1 > len(nodes):                 # fewer nodes than terms: drop the last
        used.pop()
    design = np.column_stack([np.ones(len(nodes))] + [x[:, j] - x[:, j].mean() for j in used])
    planes, resid = {}, {}
    for key in CORRECTIONS:
        y = np.array([n["corr"][key] for n in nodes])
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        planes[key] = coef.tolist()
        resid[key] = float(np.abs(design @ coef - y).max())
    return {"lo": lo.tolist(), "hi": hi.tolist(), "mean": x.mean(axis=0).tolist(), "used": used,
            "planes": planes, "max_residual": resid, "nodes": [n["name"] for n in nodes]}


def corrections(fit: dict | None, tc: float, camber: float, re: float) -> dict:
    if fit is None:
        return dict(NEUTRAL)
    x = np.clip(np.array([tc, camber, np.log10(re)]), fit["lo"], fit["hi"])
    row = np.array([1.0] + [x[j] - fit["mean"][j] for j in fit["used"]])
    return {key: float(row @ np.array(fit["planes"][key])) for key in CORRECTIONS}


def build(v0, fits: dict) -> dict:
    t = v0.t
    a = t["alpha"]
    out = {k: t[k].astype(np.float32) for k in ("alpha", "reynolds", "tc", "tc_cambered", "camber")}
    for fam in ("symmetric", "flat_inside"):
        block = {k: np.empty_like(t[f"{fam}_{k}"]) for k in ("cl", "cd", "cm")}
        for i, tc in enumerate(t["tc"]):
            for r, re in enumerate(t["reynolds"]):
                corr = corrections(fits.get(fam), float(tc), 0.0, float(re))
                cl, cd, cm = apply(a, t[f"{fam}_cl"][i, r], t[f"{fam}_cd"][i, r],
                                   t[f"{fam}_cm"][i, r], corr)
                block["cl"][i, r], block["cd"][i, r], block["cm"][i, r] = cl, cd, cm
        for k, arr in block.items():
            out[f"{fam}_{k}"] = arr.astype(np.float32)
        out[f"{fam}_conf"] = t[f"{fam}_conf"].astype(np.float32)
    block = {k: np.empty_like(t[f"cambered_{k}"]) for k in ("cl", "cd", "cm")}
    for i, tc in enumerate(t["tc_cambered"]):
        for m, camber in enumerate(t["camber"]):
            for r, re in enumerate(t["reynolds"]):
                corr = corrections(fits.get("cambered"), float(tc), float(camber), float(re))
                cl, cd, cm = apply(a, t["cambered_cl"][i, m, r], t["cambered_cd"][i, m, r],
                                   t["cambered_cm"][i, m, r], corr)
                block["cl"][i, m, r], block["cd"][i, m, r], block["cm"][i, m, r] = cl, cd, cm
    for k, arr in block.items():
        out[f"cambered_{k}"] = arr.astype(np.float32)
    out["cambered_conf"] = t["cambered_conf"].astype(np.float32)
    return out


def report(nodes: list[dict], fits: dict, v0) -> str:
    lines = ["# Section table v1 at the referee's nodes", "",
             "| section | lower end °: RANS / v0 / v1 | upper end °: RANS / v0 / v1 | "
             "drag level v1 / v0 | lift slope v1 / v0 | lift retention | "
             "cd v1 / RANS over the settled rows: "
             "min … max | largest cl difference |", "|---|---|---|---|---|---|---|---|"]
    for n in nodes:
        a0, cl0, cd0, cm0 = v0.polar(n["family"], n["tc"], n["camber"], n["re"])
        corr = corrections(fits.get(n["family"]), n["tc"], n["camber"], n["re"])
        cl1, cd1, _ = apply(a0, cl0, cd0, cm0, corr)
        f1 = features(a0, cl1, cd1)
        ok = n["settled"]
        ratio = np.interp(n["alpha"][ok], a0, cd1) / n["cd"][ok]
        dcl = np.abs(np.interp(n["alpha"][ok], a0, cl1) - n["cl"][ok]).max()
        lines.append(f"| {n['name']} | {n['rans']['lower']:+.2f} / {n['v0']['lower']:+.2f} / "
                     f"{f1['lower']:+.2f} | {n['rans']['upper']:+.2f} / {n['v0']['upper']:+.2f} / "
                     f"{f1['upper']:+.2f} | {np.exp(corr['log_level']):.3f} | "
                     f"{corr['slope']:.3f} | "
                     f"{corr['retention']:.2f} | "
                     f"{ratio.min():.2f} … {ratio.max():.2f} | {dcl:.3f} |")
    for fam, fit in fits.items():
        lines += ["", f"{fam}: {len(fit['nodes'])} nodes, plane over "
                      f"{[('t/c', 'camber', 'log Re')[j] for j in fit['used']] or 'a constant'}; "
                      f"largest residual " + ", ".join(f"{k} {v:.3f}" for k, v in
                                                       fit["max_residual"].items())]
    return "\n".join(lines)


def main() -> None:
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    out_path = Path(opt.get("out", REPO / "src/fingen/data/sections_v1.npz"))
    v0 = TableV0()
    nodes = load_nodes(v0)
    fits = {fam: fit_family([n for n in nodes if n["family"] == fam])
            for fam in sorted({n["family"] for n in nodes})}
    data = build(v0, fits)
    meta = {**v0.meta, "version": 1, "built": datetime.date.today().isoformat(),
            "source": "table v0 (neuralfoil) warped onto resolved-wall 2-D RANS sections",
            "method": "scripts/build_section_table_v1.py", "fits": fits,
            "status": "provisional: families without a finished RANS section are v0 unchanged; "
                      "corrections are held constant outside the nodes' box (see fits)"}
    data["meta"] = np.array(json.dumps(meta))
    np.savez_compressed(out_path, **data)
    text = report(nodes, fits, v0)
    print(text)
    print(f"\nwrote {out_path} ({out_path.stat().st_size / 1e3:.0f} kB)")
    if "report" in opt:
        Path(opt["report"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
