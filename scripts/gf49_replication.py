"""GF49 replication — twisted-inflow C_lp of a rectangular NACA 0012 wing.

Validation task #19 (the roll-method MEASURED pin). Goodman & Fisher NACA
Report 968 / TN 1835 [GF49] measured the damping-in-roll derivative C_lp of
UNTAPERED (rectangular, taper 1) NACA 0012 wings in ROLLING FLOW (a rotated
airstream about a fixed wing — physically identical to our twisted inflow
uy(z)=omega*z). Their unswept wing 4 (full-wing AR 2.61) reads
C_lp(C_L=0) ~= -0.22 /rad (full-wing normalization). This script reproduces
that number with the frozen level-2 bench and states a PASS/FAIL on whether the
twisted-inflow method recovers the MEASURED rolling derivative within ~15 %.

Method (see out/roll-clp-anchors.md, bench/roll-validation/{VERDICT,AUDIT-ADDENDUM}.md):

  * We model the HALF-wing (semi-span) against the board symmetryPlane exactly
    as every fin case does, compute the half-wing roll moment M_x^half about the
    root x-axis, and DOUBLE it for the full-wing comparison. The full-wing rolling
    derivative is  dM_x^full/domega = 2 * dM_x^half/domega.

  * C_lp is the STANDARD aircraft derivative (GF49 convention), semi-span-based:
        C_l  = M_x^full / (q * S_full * b)
        C_lp = C_l / (p*b/2V) = 2V * (dM_x^full/domega) / (q * S_full * b^2)
    with S_full = c*b the FULL-wing area, b = 2*s the FULL span (s = semi-span),
    q = 1/2 rho V^2.  (The classic x2/x4 trap: b, not b/2; S_full, not S_half.)
    For a rectangular wing this reduces to strip C_lp = -a0/6 (a0=2pi -> -1.047).

  * The symmetryPlane board solves the SYMMETRIC-MIRROR problem (alpha=omega*|z|),
    which the audit (AUDIT-ADDENDUM.md) shows sits ~+20 % above TRUE ANTISYMMETRIC
    rolling (alpha=omega*z): converged lifting-line gives the tapered fin 0.268
    (sym-mirror) vs 0.223 (antisym), ratio 0.223/0.268 = 0.832. GF49 measured true
    antisymmetric rolling, so we report BOTH the raw sym-mirror CFD C_lp and the
    antisym-corrected value (x0.832) and compare the latter to -0.22.

Geometry: a constant NACA 0012 section (t/c 0.12, 0.4 mm blunt TE) extruded
spanwise into a rectangular half-wing of chord c and semi-span s = 1.305*c (so
the reflected full wing has AR_full = 2s/c = 2.61, matching wing 4). Chord picked
for Re ~= 1e6 at the 6.4 m/s roll-bench speed (GF49 tested Re 1-2e6; C_lp at
C_L=0 is a lift-slope quantity the report notes is ~Re-independent, so the Re gap
is immaterial for the anchor). Root sunk 2 mm below the board plane (symmetry
cuts the solid — the root-leak fix); the square wing tip sits free inside the
domain.

Reuses the HEAD case-writer machinery (fingen.cfd.case.write_case, the frozen
level-2 recipe) for the domain/mesh/solver, then overwrites the STL with the
rectangular wing, overwrites 0/U with the roll-shear inflow, and injects the
roll-moment forces FO — exactly the roll_validation.py pattern. The twist uses
exprFixedValue (runtime-parsed, libfiniteVolume): the codedFixedValue path
cannot compile on the runtime-only OpenFOAM here and the root dynamicCode
security check blocks it regardless (bench/roll-validation/VERDICT.md).

Usage: uv run python scripts/gf49_replication.py <workdir> [procs]

One mesh is built at omega=0 and copied to every other omega. Resume-safe: an
omega whose rollMoment output exists is reparsed, not resolved.
"""

from __future__ import annotations

import json
import math
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from fingen.cfd.case import CaseSpec, run_case, write_case
from fingen.foil import section_points
from fingen.hydro import NU_SEAWATER, RHO_SEAWATER, lift_curve_slope
from fingen.params import FinParams, FoilFamily, FoilParams, OutlineParams

# ---- GF49 wing 4 target + our operating point -------------------------------
SPEED = 6.4  # m/s — the tier-0 / roll-bench operating point
TARGET_RE = 1.0e6  # GF49 tested Re 1-2e6; C_lp(C_L=0) ~Re-independent
CHORD_M = round(TARGET_RE * NU_SEAWATER / SPEED, 4)  # 0.164 m -> Re ~= 1.0e6
HALF_AR = 1.305  # wing 4 full-wing AR 2.61 -> half-wing (semi-span) AR 1.305
SEMISPAN_M = HALF_AR * CHORD_M  # s; reflected AR_full = 2s/c = 2.61
OMEGAS = (0.0, 1.0, 2.0)  # {0, low, mid}; helix pb/2V = omega*b/2V up to ~0.067
#                            (GF49 tested |pb/2V| up to 0.066 — omega=2 sits there)

# NACA 0012 section (t/c 0.12, 0.4 mm blunt-TE truncation = 0.2 % chord).
FOIL = FoilParams(family=FoilFamily.SYMMETRIC, thickness_ratio=0.12, te_thickness=0.4)

MESH_LEVEL = 2  # frozen level-2 polar recipe (docs/CFD-BENCH.md)
END_TIME = 800  # runTime cap; residualControl stops earlier if it trips

# GF49 / theory anchors (full-wing C_lp per rad, unswept AR 2.61 = wing 4).
GF49_MEASURED = -0.22  # digitized Rep 968 Fig 5-6 (C_L=0)
A0 = 2.0 * math.pi  # 2-D section slope
CLP_STRIP_2D = -A0 / 6.0  # -1.047; pure strip theory, rectangular wing
AR_FULL = 2.61
# Toll & Queijo lifting-line [TQ48] eq.27, unswept: C_lp = -(a0/8)*A/(A+4)
CLP_LL_TQ = -(A0 / 8.0) * AR_FULL / (AR_FULL + 4.0)
# Sym-mirror -> antisym factor from the audit's converged-LL numbers (0.223/0.268).
ANTISYM_FACTOR = 0.223 / 0.268  # 0.832
ROLLING_RELIEF = 0.93  # antisymmetric rolling relief (LL vs strip), roll.KAPPA_FS provenance


def _jsonable(o):
    """json.dumps default: unwrap numpy scalars (np.bool_/np.float64) to Python."""
    if hasattr(o, "item"):
        return o.item()
    return str(o)


def rect_wing_stl(path: Path) -> None:
    """Rectangular NACA 0012 half-wing STL, in meters.

    Constant section extruded spanwise (+z) from the board to the tip; the root
    overhangs 2 mm below z=0 so the board symmetryPlane cuts the solid (the
    root-leak fix, fingen.cfd.case); the square tip cap sits free at z = s inside
    the domain. Chord along +x (LE at x=0), thickness along y.
    """
    from build123d import (
        BuildLine,
        BuildSketch,
        Line,
        Plane,
        Pos,
        Spline,
        export_stl,
        extrude,
        make_face,
        scale,
    )

    upper, lower = section_points(FOIL, CHORD_M * 1e3)  # mm frame
    with BuildSketch(Plane.XY) as sk:
        with BuildLine():
            Spline(*[tuple(p) for p in upper])           # LE -> TE (upper)
            Line(tuple(upper[-1]), tuple(lower[-1]))     # blunt TE
            Spline(*[tuple(p) for p in lower[::-1]])     # TE -> LE (lower)
        make_face()
    # Extrude to the tip + 2 mm root overhang; scale mm->m; sink 2 mm.
    part = extrude(sk.sketch, amount=SEMISPAN_M * 1e3 + 2.0)
    part = Pos(0.0, 0.0, -0.002) * scale(part, 0.001)
    path.parent.mkdir(parents=True, exist_ok=True)
    export_stl(part, str(path), tolerance=1e-5, angular_tolerance=0.1)


def twisted_U(ux: float, omega: float) -> str:
    """0/U with exprFixedValue carrying uy(z) = omega*z (roll shear) on the inlet
    AND the top/side farfield (the all-boundary shear fix — a freestream farfield
    would relax uy toward 0). exprFixedValue is runtime-parsed (no wmake, no
    dynamicCode security block); pos().z() is the mesh height above the board."""
    u = f"{ux:.6g}"
    w = f"{omega:.6g}"
    expr = f'"vector({u}, {w}*pos().z(), 0)"'

    def twist() -> str:
        return (f"type            exprFixedValue;\n"
                f"        value           uniform ({u} 0 0);\n"
                f"        valueExpr       {expr};")

    return f"""FoamFile {{ version 2.0; format ascii; class volVectorField; object U; }}
dimensions [0 1 -1 0 0 0 0];
internalField uniform ({u} 0 0);
boundaryField
{{
    inlet
    {{
        {twist()}
    }}
    outlet   {{ type inletOutlet; inletValue uniform (0 0 0); value uniform ({u} 0 0); }}
    board    {{ type symmetryPlane; }}
    farfield
    {{
        {twist()}
    }}
    fin      {{ type noSlip; }}
}}
"""


def roll_moment_fo() -> str:
    """`forces` FO reporting force+moment about the root x-axis (CofR at origin,
    on the board plane). moment.dat's total-x column is the roll moment M_x."""
    return f"""    rollMoment
    {{
        type            forces;
        libs            (forces);
        writeControl    timeStep;
        writeInterval   1;
        patches         (fin);
        rho             rhoInf;
        rhoInf          {RHO_SEAWATER};
        CofR            (0 0 0);
    }}
"""


def scaffold_fin() -> FinParams:
    """A valid FinParams whose outline base=chord, depth=semi-span sizes the
    write_case domain to the rectangular wing. Its lofted solid is DISCARDED
    (overwritten by the rectangular STL); only base/depth drive the box."""
    return FinParams(
        outline=OutlineParams(depth=round(SEMISPAN_M * 1e3, 3),
                              base=round(CHORD_M * 1e3, 3)),
        foil=FoilParams(family=FoilFamily.SYMMETRIC, thickness_ratio=0.12,
                        te_thickness=0.4),
    )


def parse_mx(case: Path, tail_fraction: float = 0.2) -> dict | None:
    """Tail-averaged total roll moment M_x [N.m] from the rollMoment forces FO.

    moment.dat rows are `Time (tot_x tot_y tot_z) (pres...) (visc...)`; after
    stripping parentheses the total roll moment is the first component."""
    dats = sorted(case.glob("postProcessing/rollMoment/*/moment.dat"))
    if not dats:
        dats = sorted(case.glob("postProcessing/rollMoment/*/force.dat"))  # fallback
        if not dats:
            return None
    rows = []
    for line in dats[-1].read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        vals = [float(v) for v in line.replace("(", " ").replace(")", " ").split()]
        rows.append(vals)  # [Time, tot_x, tot_y, tot_z, pres_x, ...]
    if not rows:
        return None
    tail = rows[int(len(rows) * (1.0 - tail_fraction)):]
    mx = [r[1] for r in tail]
    return {"mx": float(np.mean(mx)), "mx_last": float(rows[-1][1]),
            "std": float(np.std(mx)), "iters": float(rows[-1][0]), "n_tail": len(tail)}


def write_omega_case(case: Path, omega: float) -> None:
    """write_case scaffold + rectangular STL + roll-shear U + roll-moment FO."""
    write_case(CaseSpec(fin=scaffold_fin(), speed=SPEED, leeway_deg=0.0,
                        mesh_level=MESH_LEVEL, end_time=END_TIME), case)
    rect_wing_stl(case / "constant/triSurface/fin.stl")
    (case / "0/U").write_text(twisted_U(SPEED, omega))
    ctrl = (case / "system/controlDict").read_text()
    ctrl = ctrl.replace("functions\n{\n", "functions\n{\n" + roll_moment_fo(), 1)
    (case / "system/controlDict").write_text(ctrl)


def clp_from_slope(slope_half: float) -> float:
    """Full-wing standard C_lp from the HALF-wing slope dM_x^half/domega [N.m.s].
    dM_x^full/domega = 2*slope_half; C_lp = 2V*(dM_x^full/domega)/(q*S_full*b^2)."""
    b = 2.0 * SEMISPAN_M
    s_full = CHORD_M * b
    q = 0.5 * RHO_SEAWATER * SPEED**2
    dmx_full = 2.0 * slope_half
    return 2.0 * SPEED * dmx_full / (q * s_full * b**2)


def main() -> None:
    workdir = Path(sys.argv[1])
    procs = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    workdir.mkdir(parents=True, exist_ok=True)

    re_c = SPEED * CHORD_M / NU_SEAWATER
    b = 2.0 * SEMISPAN_M
    ar_full_actual = b**2 / (CHORD_M * b)
    # 3-D (Helmbold) strip reference at the CFD symmetry-plane reflector (k~2 =>
    # ar_eff = AR_full): C_lp = -a_3D/6.
    a3d = 2.0 * math.pi * ar_full_actual / (2.0 + math.sqrt(ar_full_actual**2 + 4.0))
    clp_strip_3d = -a3d / 6.0

    print(f"GF49 replication: rectangular NACA 0012, chord {CHORD_M*1e3:.1f} mm, "
          f"semi-span {SEMISPAN_M*1e3:.1f} mm", flush=True)
    print(f"  Re_c {re_c:,.0f} (target {TARGET_RE:,.0f})  AR_full {ar_full_actual:.3f} "
          f"(wing 4 = 2.61)  speed {SPEED} m/s", flush=True)
    print(f"  omega {list(OMEGAS)} rad/s  helix pb/2V "
          f"{[round(w*b/(2*SPEED), 4) for w in OMEGAS]}  (GF49 max 0.066)", flush=True)
    print(f"  anchors: measured {GF49_MEASURED:+.3f}  LL(TQ48) {CLP_LL_TQ:+.3f}  "
          f"strip-2D {CLP_STRIP_2D:+.3f}  strip-3D {clp_strip_3d:+.3f}", flush=True)
    print(f"  fidelity: level {MESH_LEVEL}, end_time {END_TIME}, procs {procs}", flush=True)

    rows, mesh_src, mesh_cells = [], None, None
    for omega in OMEGAS:
        case = workdir / f"w{omega:04.1f}"
        t0 = time.time()
        parsed = parse_mx(case)
        if parsed is None:
            write_omega_case(case, omega)
            if mesh_src is not None:
                shutil.rmtree(case / "constant/polyMesh", ignore_errors=True)
                shutil.copytree(mesh_src / "constant/polyMesh",
                                case / "constant/polyMesh")
            try:
                run_case(case, procs=procs, mesh=(mesh_src is None))
            except Exception as exc:  # noqa: BLE001
                print(f"  omega {omega}: run FAILED: {exc}", flush=True)
            parsed = parse_mx(case)
        if mesh_src is None and (case / "constant/polyMesh").exists():
            mesh_src = case
            log = case / "log.snappyHexMesh"
            if log.exists():
                import re as _re
                nums = _re.findall(r"cells:\s*(\d+)", log.read_text())
                mesh_cells = int(nums[-1]) if nums else None
        mx = parsed["mx"] if parsed else float("nan")
        row = {"omega": omega, "M_x_half": mx,
               "M_x_last": parsed["mx_last"] if parsed else float("nan"),
               "tail_std": parsed["std"] if parsed else float("nan"),
               "iters": parsed["iters"] if parsed else float("nan"),
               "wall_s": round(time.time() - t0, 1)}
        rows.append(row)
        (workdir / "gf49-cases.json").write_text(json.dumps(rows, indent=2, default=_jsonable))
        print(f"  omega {omega:4.1f}: M_x^half {mx:+.5f} N.m  "
              f"(tail_std {row['tail_std']:.2e}, {row['iters']:.0f} it, "
              f"{row['wall_s']:.0f}s)", flush=True)

    # ---- derivative + C_lp --------------------------------------------------
    w = np.array([r["omega"] for r in rows])
    mx = np.array([r["M_x_half"] for r in rows])
    ok = np.isfinite(mx)
    slope_lsq = float(np.polyfit(w[ok], mx[ok], 1)[0]) if ok.sum() >= 2 else float("nan")
    # near-zero secant (0 -> first non-zero omega): the L_p-relevant derivative
    nz = [i for i in range(len(w)) if w[i] > 0 and ok[i]]
    i0 = int(np.where(w == 0.0)[0][0]) if (w == 0.0).any() else None
    secant_nz = ((mx[nz[0]] - mx[i0]) / (w[nz[0]] - w[i0])
                 if (nz and i0 is not None) else float("nan"))

    clp_sym_lsq = clp_from_slope(slope_lsq)
    clp_sym_nz = clp_from_slope(secant_nz)
    clp_anti_lsq = clp_sym_lsq * ANTISYM_FACTOR
    clp_anti_nz = clp_sym_nz * ANTISYM_FACTOR

    # PASS/FAIL: antisym-corrected CFD (near-zero derivative) vs measured, <15 %.
    err_nz = (clp_anti_nz - GF49_MEASURED) / abs(GF49_MEASURED) * 100.0
    err_lsq = (clp_anti_lsq - GF49_MEASURED) / abs(GF49_MEASURED) * 100.0
    passed = bool(abs(err_nz) <= 15.0)

    # Viscous-knockdown decomposition (the tiebreaker RERUN-VERDICT.md item 3
    # asked for): how far below the INVISCID lifting line does each land?
    knock_cfd = clp_anti_nz / CLP_LL_TQ          # CFD/LL (antisym) — RANS knockdown
    knock_meas = GF49_MEASURED / CLP_LL_TQ       # measured/LL — the TRUE knockdown
    kappa_cfd = ROLLING_RELIEF * knock_cfd       # RANS-implied kappa
    kappa_meas = ROLLING_RELIEF * knock_meas     # measurement-implied kappa

    result = {
        "generated": time.strftime("%Y-%m-%d"),
        "wing": "GF49 Rep 968 / TN 1835 wing 4 — untapered NACA 0012, AR 2.61, unswept",
        "setup": {
            "speed_ms": SPEED, "chord_m": CHORD_M, "semispan_m": SEMISPAN_M,
            "Re_c": re_c, "AR_full": ar_full_actual, "mesh_level": MESH_LEVEL,
            "end_time": END_TIME, "procs": procs, "mesh_cells": mesh_cells,
            "foil": "NACA 0012 (t/c 0.12, 0.4 mm blunt TE)",
            "omegas": list(OMEGAS),
            "helix_pb2V": [w_ * b / (2 * SPEED) for w_ in OMEGAS],
            "board_bc": "symmetryPlane (symmetric-mirror problem)",
            "inflow_bc": "exprFixedValue uy(z)=omega*pos().z() on inlet+farfield",
        },
        "cases": rows,
        "mesh_cells": mesh_cells,
        "derivative_half_Nms": {"lsq": slope_lsq, "near_zero_secant": secant_nz},
        "normalization": ("C_lp = 2V*(dMx_full/domega)/(q*S_full*b^2), "
                          "dMx_full=2*dMx_half, S_full=c*b, b=2s (GF49 convention)"),
        "clp_cfd": {
            "sym_mirror_lsq": clp_sym_lsq, "sym_mirror_near_zero": clp_sym_nz,
            "antisym_corrected_lsq": clp_anti_lsq,
            "antisym_corrected_near_zero": clp_anti_nz,
            "antisym_factor": ANTISYM_FACTOR,
            "antisym_note": ("symmetryPlane solves the symmetric-mirror problem "
                             "(alpha=omega*|z|); x0.832 = audit LL 0.223/0.268 "
                             "maps it to true antisymmetric rolling"),
        },
        "anchors": {
            "measured_GF49": GF49_MEASURED, "LL_TollQueijo": CLP_LL_TQ,
            "strip_2D": CLP_STRIP_2D, "strip_3D_helmbold": clp_strip_3d,
        },
        "viscous_knockdown": {
            "note": ("how far below the inviscid lifting line (antisym LL=%.3f) each "
                     "lands; knockdown = value/LL" % CLP_LL_TQ),
            "cfd_over_LL_antisym": knock_cfd,
            "measured_over_LL_antisym": knock_meas,
            "rolling_relief": ROLLING_RELIEF,
            "kappa_implied_by_cfd": kappa_cfd,
            "kappa_implied_by_measured": kappa_meas,
        },
        "verdict": {
            "compare": "antisym-corrected CFD (near-zero derivative) vs measured -0.22",
            "clp_cfd_antisym_near_zero": clp_anti_nz,
            "pct_error_near_zero": err_nz, "pct_error_lsq": err_lsq,
            "reproduces_within_15pct": passed,
            "outcome": ("REPRODUCES the measurement" if passed
                        else f"OVER-PREDICTS the measurement by {abs(err_nz):.0f}%"),
            "kappa_fs_implication": (
                "PASS/reproduce -> the RANS captures the full viscous knockdown the "
                "GF49 measurement shows; kappa~0.73 (rolling relief 0.93 x measured "
                "viscous 0.78) stands." if passed else
                "FAIL/over-predict -> the wall-function RANS lands near the inviscid "
                "lifting line (CFD/LL=%.2f) and MISSES most of the viscous/lifting-"
                "surface knockdown the GF49 measurement shows (measured/LL=%.2f). "
                "This CONFIRMS RERUN-VERDICT.md hedge 2: the fixed-rig's implied "
                "kappa~0.90 (from the RANS's own weak knockdown ~0.97) is a wall-"
                "function artifact; the independent GF49 MEASUREMENT is the truth, so "
                "roll.KAPPA_FS should stay ~0.73-0.78 (measurement-implied kappa=%.2f), "
                "NOT be raised to 0.90. The wall-function hedge is real." % (
                    knock_cfd, knock_meas, kappa_meas)),
        },
    }
    (workdir / "gf49-replication.json").write_text(
        json.dumps(result, indent=2, default=_jsonable))

    print("\n=== C_lp (full-wing, per rad) ===", flush=True)
    print(f"  strip 2-D (-a0/6)          {CLP_STRIP_2D:+.3f}", flush=True)
    print(f"  strip 3-D (-a3D/6, k=2)    {clp_strip_3d:+.3f}", flush=True)
    print(f"  LL Toll-Queijo [TQ48]      {CLP_LL_TQ:+.3f}", flush=True)
    print(f"  measured [GF49] wing 4     {GF49_MEASURED:+.3f}", flush=True)
    print(f"  CFD sym-mirror  (nz/lsq)   {clp_sym_nz:+.3f} / {clp_sym_lsq:+.3f}", flush=True)
    print(f"  CFD antisym-corr (nz/lsq)  {clp_anti_nz:+.3f} / {clp_anti_lsq:+.3f}", flush=True)
    print(f"  error vs measured (nz)     {err_nz:+.1f}%   "
          f"=> {'PASS (reproduces)' if passed else 'FAIL (over-predicts)'} (<15%)", flush=True)
    print(f"  viscous knockdown: CFD/LL {knock_cfd:.2f}  measured/LL {knock_meas:.2f}"
          f"  => kappa CFD {kappa_cfd:.2f} / measured {kappa_meas:.2f}", flush=True)

    try:
        _plot(workdir / "gf49-replication.png", w, mx, slope_lsq, clp_sym_nz,
              clp_anti_nz, clp_strip_3d)
        print("wrote gf49-replication.png", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"plot skipped: {exc}", flush=True)


def _plot(out_png, w, mx, slope_lsq, clp_sym_nz, clp_anti_nz, clp_strip_3d):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    bg, text, muted = "#0b0e11", "#e8e8e8", "#8f8f8f"
    grid = (1, 1, 1, 0.13)
    c_cfd, c_meas, c_ll, c_strip = "#7fd4e0", "#8ce39a", "#f2c14e", "#f2a154"
    ok = np.isfinite(mx)
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 5.0), facecolor=bg)
    for a in ax:
        a.set_facecolor(bg)
        for s in a.spines.values():
            s.set_color(grid)
        a.tick_params(colors=muted, labelsize=8)
        a.grid(True, color=grid, lw=0.6)

    # left: M_x^half vs omega + LSQ line
    ww = np.linspace(0, w[ok].max(), 50)
    icpt = float(np.polyfit(w[ok], mx[ok], 1)[1])
    ax[0].plot(ww, slope_lsq * ww + icpt, "--", color=c_strip, lw=1.5,
               label=f"LSQ slope {slope_lsq:+.3f} N.m.s")
    ax[0].plot(w[ok], mx[ok], "o-", color=c_cfd, lw=1.8, ms=7,
               label="CFD M_x^half (roll moment)")
    ax[0].set_xlabel("omega [rad/s]", color=text)
    ax[0].set_ylabel("M_x^half [N.m]", color=text)
    ax[0].set_title("Half-wing roll moment vs roll shear", color=text)
    ax[0].legend(fontsize=8, facecolor=bg, edgecolor=grid, labelcolor=text)

    # right: C_lp comparison bars
    labels = ["strip 3-D", "LL TQ48", "measured\nGF49", "CFD\nsym-mirror",
              "CFD\nantisym-corr"]
    vals = [clp_strip_3d, CLP_LL_TQ, GF49_MEASURED, clp_sym_nz, clp_anti_nz]
    cols = [c_strip, c_ll, c_meas, "#5aa9b8", c_cfd]
    ax[1].bar(labels, vals, color=cols, edgecolor=grid)
    ax[1].axhline(GF49_MEASURED, color=c_meas, ls=":", lw=1.2)
    for i, v in enumerate(vals):
        ax[1].text(i, v - 0.02, f"{v:.3f}", ha="center", va="top",
                   color=text, fontsize=8)
    ax[1].set_ylabel("C_lp (full-wing, per rad)", color=text)
    ax[1].set_title("Damping-in-roll derivative — CFD vs measured vs theory",
                    color=text)

    fig.suptitle("GF49 replication — rectangular NACA 0012, AR_full 2.61, "
                 "twisted-inflow RANS (level 2)", color=text, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_png, dpi=140, facecolor=bg)
    plt.close(fig)


if __name__ == "__main__":
    main()
