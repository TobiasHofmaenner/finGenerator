"""Section-polar feasibility probe (gen-3 model extension): NeuralFoil on fingen's own sections.

    uv run --with neuralfoil python scripts/section_probe.py [--md=out/section-probe.md]

NeuralFoil is a neural surrogate of XFOIL (2-D panel method + integral boundary
layer). It is NOT a project dependency: this probe runs it in a throwaway
overlay to answer one question before any 2-D RANS is spent — do section
polars, pushed through the vortex lattice of scripts/vlm_probe.py, reproduce
the 3-D CFD we already have?

  1. section table for the two foil families over thickness: zero-lift angle,
     slope, cl_max and its angle, the negative-side limit, drag at the toe angle;
  2. fin CL_max = section cl_max / (peak local cl / CL from the lattice), against
     the three isolated CFD polars — no fitted constant;
  3. lattice lift slope corrected by the section slope, against CFD;
  4. side-fin drag at its own incidence in the set (minus the toe), against the
     set CFD of bench/mount.

Two boundary-layer states are run: free transition (n_crit 9, clean tunnel) and
tripped at 5 % chord on both faces (the closest analogue of our fully turbulent
RANS, and of a printed fin in turbulent surf).
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import neuralfoil as nf  # noqa: E402
import vlm_probe as vlm  # noqa: E402

from fingen.foil import section_points  # noqa: E402
from fingen.hydro import RHO_SEAWATER, NU_SEAWATER, zero_lift_alpha_deg  # noqa: E402
from fingen.optimize import fin_from_dict  # noqa: E402
from fingen.outline import metrics  # noqa: E402
from fingen.params import FinParams, FoilFamily, FoilParams  # noqa: E402

ALPHA = np.arange(-14.0, 24.01, 0.5)
STATES = {"free": dict(n_crit=9.0, xtr_upper=1.0, xtr_lower=1.0),
          "tripped": dict(n_crit=9.0, xtr_upper=0.05, xtr_lower=0.05)}


def coords(family: FoilFamily, tc: float, chord_mm: float = 70.0) -> np.ndarray:
    """Selig-ordered unit-chord coordinates of a fingen section (TE upper -> LE -> TE lower)."""
    foil = FoilParams(family=family, thickness_ratio=tc)
    up, lo = section_points(foil, chord_mm, thickness_ratio=tc, n_points=200)
    return np.vstack([up[::-1], lo[1:]]) / chord_mm


def polar(family, tc, re, state="tripped", chord_mm=70.0) -> dict:
    a = nf.get_aero_from_coordinates(coords(family, tc, chord_mm), alpha=ALPHA, Re=re, model_size="xlarge", **STATES[state])
    return {"cl": np.asarray(a["CL"]), "cd": np.asarray(a["CD"]), "conf": np.asarray(a["analysis_confidence"])}


def summarize(p: dict) -> dict:
    cl, cd = p["cl"], p["cd"]
    i0 = int(np.argmin(np.abs(cl)))
    lin = (ALPHA >= ALPHA[i0] - 1.0) & (ALPHA <= ALPHA[i0] + 3.0)
    slope = float(np.polyfit(np.radians(ALPHA[lin]), cl[lin], 1)[0])
    a0 = float(np.interp(0.0, cl[max(i0 - 3, 0):i0 + 4], ALPHA[max(i0 - 3, 0):i0 + 4]))
    pos = ALPHA > a0
    k = int(np.argmax(cl[pos])); kmin = int(np.argmin(cl[~pos]))
    at = lambda al: float(np.interp(al, ALPHA, cd))
    return {"a0": a0, "slope": slope, "cl_max": float(cl[pos][k]), "a_max": float(ALPHA[pos][k]),
            "cl_min": float(cl[~pos][kmin]), "a_min": float(ALPHA[~pos][kmin]),
            "cd_min": float(cd.min()), "a_cdmin": float(ALPHA[int(np.argmin(cd))]),
            "cd_0": at(0.0), "cd_m35": at(-3.5), "cd_a0": at(a0),
            "conf_min": float(p["conf"][(ALPHA > -6) & (ALPHA < 14)].min())}


def _load(path):
    d = json.loads(Path(path).read_text())
    return d["fin"] if "fin" in d else d


def main() -> None:
    L: list[str] = []
    w = L.append
    speed = 8.5
    re_of = lambda chord_mm, v=speed: v * chord_mm * 1e-3 / NU_SEAWATER
    w("# Section-polar probe — NeuralFoil on fingen sections\n")
    w(f"Reynolds number at 8.5 m/s: {re_of(70):.2e} on a 70 mm chord. Angles in the section's own frame: "
      "positive = flow onto the flat (inside) face of a side foil, the direction it is cambered for.\n")

    # 1. section tables --------------------------------------------------------
    for state in ("tripped", "free"):
        w(f"\n## 1{'a' if state == 'tripped' else 'b'}. Section table, boundary layer {state}, Re {re_of(70):.1e}\n")
        w("| family | t/c | α0 ° | thin-airfoil α0 ° (tier-0) | slope /rad | cl_max | at α ° | negative limit cl | at α ° | cd min | at α ° | cd at 0° | cd at −3.5° | confidence |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for fam, tcs in ((FoilFamily.FLAT_INSIDE, (0.05, 0.07, 0.092, 0.099, 0.12, 0.15, 0.18, 0.22)),
                         (FoilFamily.SYMMETRIC, (0.046, 0.066, 0.09, 0.12))):
            for tc in tcs:
                s = summarize(polar(fam, tc, re_of(70), state))
                a0_t0 = zero_lift_alpha_deg(FinParams(foil=FoilParams(family=fam, thickness_ratio=tc)))
                w(f"| {fam.value} | {tc:.3f} | {s['a0']:+.2f} | {a0_t0:+.2f} | {s['slope']:.2f} | {s['cl_max']:.2f} | {s['a_max']:.1f} | "
                  f"{s['cl_min']:.2f} | {s['a_min']:.1f} | {s['cd_min']:.4f} | {s['a_cdmin']:+.1f} | {s['cd_0']:.4f} | {s['cd_m35']:.4f} | {s['conf_min']:.2f} |")

    # 2/3. fins: CL_max and slope through the lattice --------------------------
    fins = {
        "gen-2 side": ("bench/mount/fins/side-shipped-gen2.json", "out/cfd/omar-big-gen2-m2-shipped/verify-polar.json"),
        "gen-1 side": ("bench/mount/fins/side-asridden-gen1.json", "out/cfd/omar-big-asridden/verify-polar.json"),
        "ridden centre": ("bench/mount/fins/centre-ridden-gen1.json", "out/cfd/omar-ridden-centre/verify-polar.json"),
    }
    w("\n## 2. Fin maximum lift with NO fitted constant: section cl_max ÷ lattice peak loading\n")
    w("Section evaluated at the Reynolds number of the chord where the lattice says the loading peaks, at the local thickness there.\n")
    w("| fin | peak local cl / CL (lattice) | at span | local chord mm | local t/c | section cl_max tripped / free | predicted CL_max tripped / free | CFD CL_max | tier-0 gen 2 | pred/CFD tripped / free |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    from fingen.hydro import lift_curve_slope, stall_alpha_deg
    from fingen.outline import planform
    rows_out = {}
    for name, (fp, pp) in fins.items():
        fin = fin_from_dict(_load(fp))
        cfd = json.loads(Path(pp).read_text())["rows"]
        clmax_cfd = max(r["cl"] for r in cfd)
        iso = vlm.isolated(fin)
        z, x_le, chord = planform(fin.outline)
        zpk = iso["peak_z_frac"] * fin.outline.depth
        c_loc = float(np.interp(zpk, z, chord))
        tc_loc = fin.foil.thickness_ratio * (1.0 + (fin.thickness_tip_factor - 1.0) * zpk / fin.outline.depth)
        sec = {st: summarize(polar(fin.foil.family, tc_loc, re_of(c_loc), st, chord_mm=c_loc)) for st in STATES}
        pred = {st: sec[st]["cl_max"] / iso["peak_ratio"] for st in STATES}
        s_t0, ar = lift_curve_slope(fin)
        t0 = s_t0 * math.radians(stall_alpha_deg(ar) - zero_lift_alpha_deg(fin))
        rows_out[name] = (fin, iso, cfd)
        w(f"| {name} | {iso['peak_ratio']:.2f} | {iso['peak_z_frac']:.2f} | {c_loc:.0f} | {tc_loc:.3f} | {sec['tripped']['cl_max']:.2f} / {sec['free']['cl_max']:.2f} | "
          f"{pred['tripped']:.2f} / {pred['free']:.2f} | {clmax_cfd:.2f} | {t0:.2f} | {pred['tripped'] / clmax_cfd:.2f} / {pred['free'] / clmax_cfd:.2f} |")

    w("\n## 3. Lift slope and lift at 0°: inviscid lattice corrected by the section's own slope and zero-lift angle\n")
    w("Correction: the section slope a0 replaces 2π in the finite-wing relation (Helmbold ratio at the fin's full-mirror aspect ratio); lift at 0° uses the section's α0 in place of thin-airfoil theory.\n")
    w("| fin | CLα CFD | lattice inviscid | lattice × section (tripped) | ratio to CFD | CL(0°) CFD | lattice thin-airfoil | lattice with section α0 (tripped) |")
    w("|---|---|---|---|---|---|---|---|")
    for name, (fin, iso, cfd) in rows_out.items():
        s_cfd = (cfd[1]["cl"] - cfd[0]["cl"]) / math.radians(cfd[1]["alpha"] - cfd[0]["alpha"])
        mc = metrics(fin.outline).area / fin.outline.depth
        tc_mean = fin.foil.thickness_ratio * (1.0 + (fin.thickness_tip_factor - 1.0) * 0.4)
        sec = summarize(polar(fin.foil.family, tc_mean, re_of(mc), "tripped", chord_mm=mc))
        ar = 2.0 * fin.outline.depth**2 / metrics(fin.outline).area
        helm = lambda a0: a0 * ar / (a0 / math.pi + math.sqrt(ar**2 + (a0 / math.pi) ** 2))
        corr = helm(sec["slope"]) / helm(2.0 * math.pi)
        s_corr = iso["slope"] * corr
        cl0_corr = -s_corr * math.radians(sec["a0"]) if fin.foil.family is not FoilFamily.SYMMETRIC else 0.0
        w(f"| {name} | {s_cfd:.2f} | {iso['slope']:.2f} | {s_corr:.2f} | {s_corr / s_cfd:.2f} | {cfd[0]['cl']:.3f} | {iso['cl0']:.3f} | {cl0_corr:.3f} |")

    # 4. side-fin drag at the toe angle ---------------------------------------
    w("\n## 4. Side-fin drag going straight: the fin at minus its toe angle\n")
    w("Set CFD per side fin at 0° leeway (bench/mount) against section profile drag at the fin's own incidence, mean chord and mean thickness, × q × area. "
      "The CFD value is 3-D (tip, junction, residual induced drag); read the TREND with incidence first.\n")
    res = json.loads(Path("bench/mount/results.json").read_text())["cases"]
    q = 0.5 * RHO_SEAWATER * speed**2
    w("| blade | toe ° | own incidence ° | set CFD cd | set CFD N | section cd tripped / free | × q·A, N tripped / free | tier-0 gen 3, N |")
    w("|---|---|---|---|---|---|---|---|")
    from fingen import spider
    for blade, fp, cases in (("gen-2 side", "bench/mount/fins/side-shipped-gen2.json", (("toe-2.5", 2.5), ("baseline", 3.5), ("toe-4.5", 4.5))),
                             ("gen-1 side", "bench/mount/fins/side-asridden-gen1.json", (("G1-side-asridden-gen1", 3.5),))):
        fin = fin_from_dict(_load(fp))
        A = metrics(fin.outline).area * 1e-6
        mc = metrics(fin.outline).area / fin.outline.depth
        tc_mean = fin.foil.thickness_ratio * (1.0 + (fin.thickness_tip_factor - 1.0) * 0.4)
        pol = {st: polar(fin.foil.family, tc_mean, re_of(mc), st, chord_mm=mc) for st in STATES}
        for case, toe in cases:
            c = next(r["coeffs"] for r in res[case]["rows"] if r["angle"] == 0.0)["right"]
            cds = {st: float(np.interp(-toe, ALPHA, pol[st]["cd"])) for st in STATES}
            w(f"| {blade} | {toe} | {-toe:+.1f} | {c['cd']:.4f} | {c['cd'] * q * A:.1f} | {cds['tripped']:.4f} / {cds['free']:.4f} | "
              f"{cds['tripped'] * q * A:.1f} / {cds['free'] * q * A:.1f} | {spider.trim_drag_n(fin, speed, toe):.1f} |")
        cd_iso0 = {st: float(np.interp(0.0, ALPHA, pol[st]["cd"])) for st in STATES}
        w(f"| {blade}, isolated at 0° for reference | – | +0.0 | (isolated CFD) | – | {cd_iso0['tripped']:.4f} / {cd_iso0['free']:.4f} | "
          f"{cd_iso0['tripped'] * q * A:.1f} / {cd_iso0['free'] * q * A:.1f} | – |")
    w("\nSection drag polar of the gen-2 side foil (tripped), own incidence → cd, cl:\n")
    fin = fin_from_dict(_load("bench/mount/fins/side-shipped-gen2.json"))
    mc = metrics(fin.outline).area / fin.outline.depth
    tc_mean = fin.foil.thickness_ratio * (1.0 + (fin.thickness_tip_factor - 1.0) * 0.4)
    for st in STATES:
        p = polar(fin.foil.family, tc_mean, re_of(mc), st, chord_mm=mc)
        w(f"- {st}: " + ", ".join(f"{a:+.0f}°: {np.interp(a, ALPHA, p['cd']):.4f} ({np.interp(a, ALPHA, p['cl']):+.2f})" for a in (-8, -6, -4.5, -3.5, -2.5, -1, 0, 2, 4, 8, 12)))

    # 5. cost -------------------------------------------------------------------
    c0 = coords(FoilFamily.FLAT_INSIDE, 0.09)
    nf.get_aero_from_coordinates(c0, alpha=ALPHA, Re=5e5, model_size="xlarge")
    t0 = time.perf_counter()
    for _ in range(20):
        nf.get_aero_from_coordinates(c0, alpha=ALPHA, Re=5e5, model_size="xlarge")
    t_x = (time.perf_counter() - t0) / 20
    t0 = time.perf_counter()
    for _ in range(20):
        nf.get_aero_from_coordinates(c0, alpha=ALPHA, Re=5e5, model_size="medium")
    t_m = (time.perf_counter() - t0) / 20
    w(f"\n## 5. Cost\n\nOne full polar ({len(ALPHA)} angles): {t_x * 1e3:.0f} ms at model size xlarge, {t_m * 1e3:.0f} ms at medium. "
      "As a precomputed table (family × thickness × Reynolds × angle) the in-loop cost is an interpolation.")

    text = "\n".join(L)
    print(text)
    for a in sys.argv[1:]:
        if a.startswith("--md="):
            Path(a.split("=", 1)[1]).write_text(text + "\n")


if __name__ == "__main__":
    main()
