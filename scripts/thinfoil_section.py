"""Thin-foil low-Re section polar — the free-run thin-foil exploit, HYDRO half.

Exploit adjudication #17 (thin-foil), CFD half. The reproducible free-run
exploit (out/freerun-dossiers.md "THIN FOIL"; winner out/freerun-95kg-pro-free-b2
.json) drives t/c to the 0.045 floor riding the static stress gate: profile drag
cd0 = 2*cf*(1+2t+60t^4) (spider._cd0, Hoerner) drops monotonically with t, so
speed/drive/hold all climb. tier-0 hands the section SECTION_SLOPE = 2*pi and the
Hoerner cd0 with NO Reynolds/thickness caveat — but the winner's section (flat-
inside, t/c 0.0446, sharp LE) is thinner than the SK81/Zarruk validated band.

CFD question: does a 0.045 t/c sharp-LE section keep its 2pi-class lift slope and
Hoerner cd0 at the fin Reynolds number (2-7e5), or does it separate early / carry
a drag penalty tier-0 misses?

Machinery: the validated SK81-style EXTRUDED-SECTION slab (scripts/sk81_naca0012
.py) — a constant section extruded into a quasi-2D slab with symmetryPlane z
faces, incidence set by the rotated inlet vector + freestream lateral patches,
one snappy mesh built at alpha=0 and copied to every angle. Run at the winner's
ACTUAL section (flat-inside, t/c 0.0446, mean chord) and its mean-chord Re at
8.5 m/s (the 95 kg pro speed). Two turbulence tiers on ONE shared resolved-wall
mesh (cell-center y+ ~1 prism layers):

  * TRANSITION (primary): kOmegaSSTLM (gamma-Re_theta), inlet Tu 1 % — the
    validated transition tier (bench/bw04-polar-transition, T3A). This is the
    tier that can SHOW laminar / early LE separation on a thin sharp nose.
  * FULLY-TURBULENT (bracket): kOmegaSST, inlet Tu 5 % — the SK81 tier
    convention. The needle finding (cd0 +24 % at low Re vs the transitional
    measurement, commit 2454f01) is this tier's known cd0 overshoot; carrying
    it here brackets the pessimistic drag side for this thinner section.

Compares CFD lift slope vs tier-0 SECTION_SLOPE=2pi, CFD cd0 vs tier-0 Hoerner
cd0, and the knee/stall onset over 0-10 deg / 2 deg (the winner works at
alpha ~7.1 deg — inside the sweep). Verdict: does the thin-foil exploit's HYDRO
claim survive (its structural half stays with the user's rig)?

Usage: uv run python scripts/thinfoil_section.py <workdir> [procs]

Resume-safe: a (angle, model) whose forceCoeffs exists is reparsed; the first
meshed case donates its polyMesh to the rest.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from fingen.foil import section_points
from fingen.params import FoilFamily, FoilParams

FOAM_BASHRC = "/usr/lib/openfoam/openfoam2512/etc/bashrc"

# ---- the thin-foil winner's ACTUAL section + operating point ----------------
# out/freerun-95kg-pro-free-b2.json: flat-inside, t/c 0.0446, camber 0.
FOIL = FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.044639453285725224,
                  camber_ratio=0.0, camber_position=0.4, te_thickness=0.7)
TC = FOIL.thickness_ratio
# planform: area 8776.585 mm^2, depth 113.610 mm -> mean chord = area/depth.
CHORD = (8776.585263826284 / 113.61019226088422) * 1e-3  # m, mean chord ~77.3 mm
SPAN = 0.02  # slab extrusion depth (z extent), m
SPEED = 8.5  # m/s, 95 kg pro rider speed
NU = 1.05e-6  # seawater kinematic viscosity (fingen.hydro.NU_SEAWATER)
RHO = 1025.0  # seawater density (fingen.hydro.RHO_SEAWATER)
RE = SPEED * CHORD / NU  # mean-chord Reynolds number (~6.3e5, in the fin band)
ANGLES = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]
MODELS = ("lm", "ft")  # kOmegaSSTLM (transition) + kOmegaSST (fully turbulent)

# domain (SK81 convention: -4c..+8c streamwise, +/-4c lateral) scaled to chord
X0, X1 = -4.0 * CHORD, 8.0 * CHORD
Y0, Y1 = -4.0 * CHORD, 4.0 * CHORD
CELL = CHORD / 12.0  # background cell; z gets round(SPAN/CELL) cells
END_TIME = 2000
MAX_SURF_LEVEL = 5

# resolved-wall prism stack (cell-center y+ ~1), mirrors fingen.cfd.case level 4
_U_TAU = SPEED * math.sqrt(0.0576 * RE**-0.2 / 2.0)
FIRST_LAYER = 2.0 * NU / _U_TAU
_SURF_CELL = CELL / 2**MAX_SURF_LEVEL
N_LAYERS = max(int(math.log(0.4 * _SURF_CELL / FIRST_LAYER) / math.log(1.2)) + 2, 10)

# tier-0 references
SECTION_SLOPE = 2.0 * math.pi  # a0 per rad (hydro.SECTION_SLOPE)
_CF = 0.074 / RE**0.2
CD0_HOERNER = 2.0 * _CF * (1.0 + 2.0 * TC + 60.0 * TC**4)  # spider._cd0 form

_BG, _TEXT, _MUTED = "#0b0e11", "#e8e8e8", "#8f8f8f"
_GRID = (1.0, 1.0, 1.0, 0.13)


def _jsonable(o):
    """json.dumps default: unwrap numpy scalars (np.bool_/np.float64) to Python."""
    if hasattr(o, "item"):
        return o.item()
    return str(o)


def _model_props(model: str) -> dict:
    """Turbulence inputs per tier."""
    if model == "lm":
        tu, rasmodel, transition = 0.01, "kOmegaSSTLM", True
    else:
        tu, rasmodel, transition = 0.05, "kOmegaSST", False
    k_in = 1.5 * (SPEED * tu) ** 2
    omega_in = math.sqrt(k_in) / (0.09**0.25 * 0.1 * CHORD)
    tu_pct = tu * 100.0
    if tu_pct <= 1.3:
        re_theta = 1173.51 - 589.428 * tu_pct + 0.2196 / tu_pct**2
    else:
        re_theta = 331.50 * (tu_pct - 0.5658) ** -0.671
    return {"tu": tu, "rasmodel": rasmodel, "transition": transition,
            "k_in": k_in, "omega_in": omega_in, "re_theta": re_theta}


def write_foil_stl(path: Path) -> None:
    """Extruded flat-inside section slab, meters, overhanging both z faces 2 mm so
    the symmetryPlane cuts the solid interior (the root-leak fix, sk81/case)."""
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

    upper, lower = section_points(FOIL, CHORD * 1e3)  # mm frame; lower is flat (y=0)
    with BuildSketch(Plane.XY) as sk:
        with BuildLine():
            Spline(*[tuple(p) for p in upper])            # LE -> TE (curved upper)
            Line(tuple(upper[-1]), tuple(lower[-1]))      # blunt TE
            Line(tuple(lower[-1]), tuple(lower[0]))       # flat inner face -> LE
        make_face()
    part = extrude(sk.sketch, amount=SPAN * 1e3 + 4.0)
    part = Pos(0.0, 0.0, -0.002) * scale(part, 0.001)
    path.parent.mkdir(parents=True, exist_ok=True)
    export_stl(part, str(path), tolerance=1e-5, angular_tolerance=0.1)


def write_case(case: Path, alpha_deg: float, model: str) -> None:
    """Full case dicts (no STL) for one (angle, model)."""
    mp = _model_props(model)
    for sub in ("0", "constant/triSurface", "system"):
        (case / sub).mkdir(parents=True, exist_ok=True)
    a = math.radians(alpha_deg)
    ux, uy = SPEED * math.cos(a), SPEED * math.sin(a)
    vel = f"({ux:.6g} {uy:.6g} 0)"
    nx, ny, nz = (round((X1 - X0) / CELL), round((Y1 - Y0) / CELL),
                  max(round(SPAN / CELL), 2))
    loc = (X1 - 0.1 * CHORD + 0.37 * CELL, 0.5 * Y0 + 0.37 * CELL, 0.5 * SPAN + 0.37 * CELL)
    k_in, omega_in, re_theta = mp["k_in"], mp["omega_in"], mp["re_theta"]
    # fin/foil wall BCs mirror fingen.cfd.case: transition resolves k to 0 at the
    # wall; fully-turbulent uses the k wall function.
    k_wall = ("type fixedValue; value uniform 0;" if mp["transition"]
              else f"type kqRWallFunction; value uniform {k_in:g};")
    div_extra = ("    div(phi,gammaInt)  bounded Gauss upwind;\n"
                 "    div(phi,ReThetat)  bounded Gauss upwind;\n"
                 if mp["transition"] else "")
    solver_extra = "|gammaInt|ReThetat" if mp["transition"] else ""
    u_relax = "0.8" if mp["transition"] else "0.9"

    files = {
        "system/controlDict": f"""FoamFile {{ version 2.0; format ascii; class dictionary; object controlDict; }}
application     simpleFoam;
startFrom       latestTime;
stopAt          endTime;
endTime         {END_TIME};
deltaT          1;
writeControl    timeStep;
writeInterval   500;
purgeWrite      1;
writeFormat     binary;
runTimeModifiable yes;
functions
{{
    forceCoeffs
    {{
        type            forceCoeffs;
        libs            (forces);
        writeControl    timeStep;
        writeInterval   1;
        patches         (foil);
        rho             rhoInf;
        rhoInf          {RHO:g};
        liftDir         ({-math.sin(a):.6g} {math.cos(a):.6g} 0);
        dragDir         ({math.cos(a):.6g} {math.sin(a):.6g} 0);
        CofR            ({0.25 * CHORD:g} 0 {0.5 * SPAN:g});
        pitchAxis       (0 0 1);
        magUInf         {SPEED:g};
        lRef            {CHORD:g};
        Aref            {CHORD * SPAN:g};
    }}
    yPlus {{ type yPlus; libs (fieldFunctionObjects); writeControl onEnd; }}
}}
""",
        "system/fvSchemes": f"""FoamFile {{ version 2.0; format ascii; class dictionary; object fvSchemes; }}
ddtSchemes      {{ default steadyState; }}
gradSchemes     {{ default cellLimited Gauss linear 1; }}
divSchemes
{{
    default                     none;
    div(phi,U)                  bounded Gauss linearUpwind grad(U);
    div(phi,k)                  bounded Gauss upwind;
    div(phi,omega)              bounded Gauss upwind;
{div_extra}    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}}
laplacianSchemes {{ default Gauss linear corrected; }}
interpolationSchemes {{ default linear; }}
snGradSchemes   {{ default corrected; }}
wallDist        {{ method meshWave; }}
""",
        "system/fvSolution": f"""FoamFile {{ version 2.0; format ascii; class dictionary; object fvSolution; }}
solvers
{{
    p      {{ solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0.01; }}
    "(U|k|omega{solver_extra})" {{ solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0.1; }}
}}
SIMPLE
{{
    consistent      yes;
    nNonOrthogonalCorrectors 0;
    residualControl {{ p 1e-4; U 1e-5; "(k|omega{solver_extra})" 1e-5; }}
}}
relaxationFactors {{ equations {{ U {u_relax}; ".*" 0.7; }} }}
""",
        "system/blockMeshDict": f"""FoamFile {{ version 2.0; format ascii; class dictionary; object blockMeshDict; }}
scale 1;
vertices
(
    ({X0:g} {Y0:g} 0) ({X1:g} {Y0:g} 0) ({X1:g} {Y1:g} 0) ({X0:g} {Y1:g} 0)
    ({X0:g} {Y0:g} {SPAN:g}) ({X1:g} {Y0:g} {SPAN:g})
    ({X1:g} {Y1:g} {SPAN:g}) ({X0:g} {Y1:g} {SPAN:g})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1) );
boundary
(
    inlet    {{ type patch; faces ((0 4 7 3)); }}
    outlet   {{ type patch; faces ((1 2 6 5)); }}
    farfield {{ type patch; faces ((0 1 5 4) (3 7 6 2)); }}
    backSym  {{ type symmetryPlane; faces ((0 3 2 1)); }}
    frontSym {{ type symmetryPlane; faces ((4 5 6 7)); }}
);
""",
        "system/snappyHexMeshDict": f"""FoamFile {{ version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }}
castellatedMesh true;
snap            true;
addLayers       true;
geometry {{ foil.stl {{ type triSurfaceMesh; name foil; }} }}
castellatedMeshControls
{{
    maxLocalCells   2000000;
    maxGlobalCells  10000000;
    minRefinementCells 10;
    nCellsBetweenLevels 3;
    features        ( {{ file "foil.eMesh"; level {MAX_SURF_LEVEL}; }} );
    refinementSurfaces {{ foil {{ level (4 {MAX_SURF_LEVEL}); }} }}
    refinementRegions {{ foil {{ mode distance; levels (({0.3 * CHORD:g} 2)); }} }}
    resolveFeatureAngle 30;
    locationInMesh ({loc[0]:.6g} {loc[1]:.6g} {loc[2]:.6g});
    allowFreeStandingZoneFaces true;
}}
snapControls
{{
    nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5;
    nFeatureSnapIter 10; implicitFeatureSnap false; explicitFeatureSnap true;
    multiRegionFeatureSnap false;
}}
addLayersControls
{{
    relativeSizes false;
    layers {{ foil {{ nSurfaceLayers {N_LAYERS}; }} }}
    expansionRatio 1.2; firstLayerThickness {FIRST_LAYER:.6g};
    minThickness {FIRST_LAYER / 4.0:.6g};
    nGrow 0; featureAngle 60; nRelaxIter 3; nSmoothSurfaceNormals 1;
    nSmoothNormals 3; nSmoothThickness 10; maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3; minMedialAxisAngle 90; nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}
meshQualityControls
{{
    maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4; maxConcave 80;
    minVol 1e-14; minTetQuality 1e-16; minArea -1; minTwist 0.02;
    minDeterminant 0.001; minFaceWeight 0.05; minVolRatio 0.01; minTriangleTwist -1;
    nSmoothScale 4; errorReduction 0.75;
}}
writeFlags (scalarLevels);
mergeTolerance 1e-6;
""",
        "system/surfaceFeatureExtractDict": """FoamFile { version 2.0; format ascii; class dictionary; object surfaceFeatureExtractDict; }
foil.stl { extractionMethod extractFromSurface; includedAngle 150; }
""",
        "constant/transportProperties": f"""FoamFile {{ version 2.0; format ascii; class dictionary; object transportProperties; }}
transportModel  Newtonian;
nu              {NU:g};
""",
        "constant/turbulenceProperties": f"""FoamFile {{ version 2.0; format ascii; class dictionary; object turbulenceProperties; }}
simulationType  RAS;
RAS {{ RASModel {mp["rasmodel"]}; turbulence on; printCoeffs on; }}
""",
        "0/U": f"""FoamFile {{ version 2.0; format ascii; class volVectorField; object U; }}
dimensions [0 1 -1 0 0 0 0];
internalField uniform {vel};
boundaryField
{{
    inlet    {{ type fixedValue; value uniform {vel}; }}
    outlet   {{ type inletOutlet; inletValue uniform (0 0 0); value uniform {vel}; }}
    farfield {{ type freestreamVelocity; freestreamValue uniform {vel}; }}
    backSym  {{ type symmetryPlane; }}
    frontSym {{ type symmetryPlane; }}
    foil     {{ type noSlip; }}
}}
""",
        "0/p": """FoamFile { version 2.0; format ascii; class volScalarField; object p; }
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet    { type zeroGradient; }
    outlet   { type fixedValue; value uniform 0; }
    farfield { type freestreamPressure; freestreamValue uniform 0; }
    backSym  { type symmetryPlane; }
    frontSym { type symmetryPlane; }
    foil     { type zeroGradient; }
}
""",
        "0/k": f"""FoamFile {{ version 2.0; format ascii; class volScalarField; object k; }}
dimensions [0 2 -2 0 0 0 0];
internalField uniform {k_in:g};
boundaryField
{{
    inlet    {{ type fixedValue; value uniform {k_in:g}; }}
    outlet   {{ type zeroGradient; }}
    farfield {{ type inletOutlet; inletValue uniform {k_in:g}; value uniform {k_in:g}; }}
    backSym  {{ type symmetryPlane; }}
    frontSym {{ type symmetryPlane; }}
    foil     {{ {k_wall} }}
}}
""",
        "0/omega": f"""FoamFile {{ version 2.0; format ascii; class volScalarField; object omega; }}
dimensions [0 0 -1 0 0 0 0];
internalField uniform {omega_in:g};
boundaryField
{{
    inlet    {{ type fixedValue; value uniform {omega_in:g}; }}
    outlet   {{ type zeroGradient; }}
    farfield {{ type inletOutlet; inletValue uniform {omega_in:g}; value uniform {omega_in:g}; }}
    backSym  {{ type symmetryPlane; }}
    frontSym {{ type symmetryPlane; }}
    foil     {{ type omegaWallFunction; value uniform {omega_in:g}; }}
}}
""",
        "0/nut": """FoamFile { version 2.0; format ascii; class volScalarField; object nut; }
dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet    { type calculated; value uniform 0; }
    outlet   { type calculated; value uniform 0; }
    farfield { type calculated; value uniform 0; }
    backSym  { type symmetryPlane; }
    frontSym { type symmetryPlane; }
    foil     { type nutkWallFunction; value uniform 0; }
}
""",
    }
    if mp["transition"]:
        for name, val in (("gammaInt", 1.0), ("ReThetat", re_theta)):
            files[f"0/{name}"] = f"""FoamFile {{ version 2.0; format ascii; class volScalarField; object {name}; }}
dimensions [0 0 0 0 0 0 0];
internalField uniform {val:g};
boundaryField
{{
    inlet    {{ type fixedValue; value uniform {val:g}; }}
    outlet   {{ type zeroGradient; }}
    farfield {{ type inletOutlet; inletValue uniform {val:g}; value uniform {val:g}; }}
    backSym  {{ type symmetryPlane; }}
    frontSym {{ type symmetryPlane; }}
    foil     {{ type zeroGradient; }}
}}
"""
    for rel, content in files.items():
        (case / rel).write_text(content)


def _foam(case: Path, step: str) -> None:
    tool = "simpleFoam" if step.startswith("mpirun") else step.split()[0]
    r = subprocess.run(["bash", "-c", f"source {FOAM_BASHRC} && cd {case} && {step}"],
                       capture_output=True, text=True)
    (case / f"log.{tool}").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        tail = r.stderr.splitlines()[-1] if r.stderr else "?"
        raise RuntimeError(f"{tool} failed (see {case}/log.{tool}): {tail}")


def solve(case: Path, procs: int) -> None:
    if procs > 1:
        (case / "system/decomposeParDict").write_text(
            "FoamFile { version 2.0; format ascii; class dictionary; "
            "object decomposeParDict; }\n"
            f"numberOfSubdomains {procs};\nmethod scotch;\n")
        if not (case / "processor0").exists():
            _foam(case, "decomposePar -force")
        _foam(case, f"mpirun --allow-run-as-root --oversubscribe -np {procs} "
                    "simpleFoam -parallel")
        _foam(case, "reconstructPar -latestTime")
    else:
        _foam(case, "simpleFoam")


def coefficients(case: Path, tail_fraction: float = 0.2) -> dict:
    root = case / "postProcessing/forceCoeffs"
    header, rows = [], {}
    for tdir in sorted((d for d in root.iterdir() if d.is_dir()),
                       key=lambda d: float(d.name)):
        dat = tdir / "coefficient.dat"
        if not dat.exists():
            continue
        for line in dat.read_text().splitlines():
            if line.startswith("#"):
                header = line.replace("#", "").split()
                continue
            vals = [float(v) for v in line.split()]
            rows[vals[0]] = vals
    times = sorted(rows)
    tail = [rows[t] for t in times[int(len(times) * (1.0 - tail_fraction)):]]
    avg = [sum(col) / len(tail) for col in zip(*tail, strict=True)]
    out = dict(zip(header, avg, strict=False))
    return {"cl": out.get("Cl", float("nan")), "cd": out.get("Cd", float("nan")),
            "cm": out.get("CmPitch", float("nan")), "iters": times[-1]}


def yplus(case: Path) -> tuple[float, float] | None:
    dats = sorted((case / "postProcessing/yPlus").rglob("yPlus.dat"))
    if not dats:
        return None
    mn = mx = None
    for line in dats[-1].read_text().splitlines():
        p = line.split()
        if not line.startswith("#") and len(p) > 3 and p[1] == "foil":
            mn, mx = float(p[2]), float(p[3])
    return (mn, mx) if mn is not None else None


def mesh_cells(case: Path) -> int | None:
    log = case / "log.snappyHexMesh"
    if not log.exists():
        return None
    import re
    nums = re.findall(r"cells:\s*(\d+)", log.read_text())
    return int(nums[-1]) if nums else None


def main() -> None:
    workdir = Path(sys.argv[1])
    procs = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    workdir.mkdir(parents=True, exist_ok=True)

    print(f"THIN-FOIL section polar: flat-inside t/c {TC:.4f}  chord {CHORD*1e3:.1f} mm"
          f"  U {SPEED} m/s  Re {RE:,.0f}", flush=True)
    print(f"tier-0: SECTION_SLOPE 2pi = {SECTION_SLOPE:.3f}/rad ({math.radians(1)*SECTION_SLOPE:.4f}/deg)"
          f"  Hoerner cd0 {CD0_HOERNER:.4f}", flush=True)
    print(f"resolved wall: {N_LAYERS} layers, first {FIRST_LAYER:.2e} m; "
          f"angles {ANGLES}; models {MODELS}; procs {procs}", flush=True)

    mesh_src, mcells, yp0 = None, None, None
    results = {m: [] for m in MODELS}
    for model in MODELS:
        for alpha in ANGLES:
            case = workdir / f"a{alpha:04.1f}-{model}"
            t0 = time.time()
            done = (case / "postProcessing/forceCoeffs").exists()
            if not done:
                write_case(case, alpha, model)
                if mesh_src is None:
                    write_foil_stl(case / "constant/triSurface/foil.stl")
                    try:
                        for step in ("surfaceFeatureExtract", "blockMesh",
                                     "snappyHexMesh -overwrite"):
                            _foam(case, step)
                        mesh_src = case
                        mcells = mesh_cells(case)
                    except RuntimeError as exc:
                        print(f"  MESH FAILED: {exc}", flush=True)
                        raise
                else:
                    shutil.rmtree(case / "constant/polyMesh", ignore_errors=True)
                    shutil.copytree(mesh_src / "constant/polyMesh",
                                    case / "constant/polyMesh")
                try:
                    solve(case, procs)
                except RuntimeError as exc:
                    print(f"  a{alpha} {model}: solve FAILED: {exc}", flush=True)
            try:
                c = coefficients(case)
            except (FileNotFoundError, ValueError, IndexError):
                c = {"cl": float("nan"), "cd": float("nan"), "cm": float("nan"),
                     "iters": float("nan")}
            yp = yplus(case)
            if yp0 is None and yp is not None:
                yp0 = yp
            row = {"alpha": alpha, **c, "yplus": yp, "wall_s": round(time.time() - t0, 1)}
            results[model].append(row)
            (workdir / "section-polar-cases.json").write_text(json.dumps(results, indent=2, default=_jsonable))
            print(f"  {model} a{alpha:4.1f}: CL {c['cl']:7.4f}  CD {c['cd']:7.4f}  "
                  f"CM {c['cm']:7.4f}  y+ {yp}  ({row['wall_s']:.0f}s)", flush=True)

    analysis = _analyse(results, mcells, yp0)
    (workdir / "section-polar.json").write_text(json.dumps(analysis, indent=2, default=_jsonable))
    _report(analysis)
    try:
        _plot(workdir / "section-polar.png", results, analysis)
        print("wrote section-polar.png", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"plot skipped: {exc}", flush=True)


def _fit_slope(rows: list[dict], amax: float) -> tuple[float, float]:
    a = np.array([r["alpha"] for r in rows])
    cl = np.array([r["cl"] for r in rows])
    m = (a <= amax) & np.isfinite(cl)
    if m.sum() < 2:
        return float("nan"), float("nan")
    fit = np.polyfit(np.radians(a[m]), cl[m], 1)
    return float(fit[0]), float(fit[1])


def _cd0_from_polar(rows: list[dict], amax: float = 4.0) -> float:
    """Zero-lift profile drag: intercept of a CD = cd0 + k*CL^2 fit over the
    attached low-alpha points. Fairer than CD(alpha=0) for a flat-inside section
    (which carries CL0>0, so its true drag bucket floor sits at alpha<0)."""
    cl = np.array([r["cl"] for r in rows if r["alpha"] <= amax and math.isfinite(r["cl"])
                   and math.isfinite(r["cd"])])
    cd = np.array([r["cd"] for r in rows if r["alpha"] <= amax and math.isfinite(r["cl"])
                   and math.isfinite(r["cd"])])
    if len(cl) < 2:
        return float("nan")
    return float(np.polyfit(cl**2, cd, 1)[1])  # intercept at CL=0


def _knee(rows: list[dict]) -> dict:
    """Departure-from-linear knee: first angle where CL falls >8 % below the
    0-4 deg linear extrapolation, else CL_max angle within range."""
    a = np.array([r["alpha"] for r in rows])
    cl = np.array([r["cl"] for r in rows])
    ok = np.isfinite(cl)
    slope, icpt = _fit_slope(rows, 4.0)
    knee = None
    for i in range(len(a)):
        if not ok[i] or a[i] <= 4.0:
            continue
        lin = slope * math.radians(a[i]) + icpt
        if lin > 0 and cl[i] < 0.92 * lin:
            knee = float(a[i])
            break
    i_max = int(np.argmax(np.where(ok, cl, -np.inf)))
    return {"knee_deg": knee, "cl_max": float(cl[i_max]), "cl_max_alpha": float(a[i_max]),
            "attached_through_range": knee is None}


def _analyse(results: dict, mcells: int | None, yp0) -> dict:
    out = {
        "generated": time.strftime("%Y-%m-%d"),
        "section": "flat-inside (thin-foil free-run winner, 95kg pro free-b2)",
        "tc": TC, "chord_m": CHORD, "speed_ms": SPEED, "Re_meanchord": RE,
        "mesh_cells": mcells, "yplus_alpha0": yp0, "n_layers": N_LAYERS,
        "first_layer_m": FIRST_LAYER, "angles": ANGLES,
        "tier0": {"section_slope_rad": SECTION_SLOPE,
                  "section_slope_deg": math.radians(1) * SECTION_SLOPE,
                  "cd0_hoerner": CD0_HOERNER, "cf": _CF},
        "models": {},
    }
    for model, rows in results.items():
        s6, _ = _fit_slope(rows, 6.0)
        s8, _ = _fit_slope(rows, 8.0)
        cd0 = next((r["cd"] for r in rows if r["alpha"] == 0.0), float("nan"))
        cds = [r["cd"] for r in rows if math.isfinite(r["cd"])]
        cd_min = min(cds) if cds else float("nan")
        cd0_polar = _cd0_from_polar(rows)
        knee = _knee(rows)
        out["models"][model] = {
            "rasmodel": "kOmegaSSTLM" if model == "lm" else "kOmegaSST",
            "tier": "transition (gamma-Re_theta, Tu 1%)" if model == "lm"
                    else "fully-turbulent (Tu 5%)",
            "slope_0_6_rad": s6, "slope_0_8_rad": s8,
            "slope_dev_vs_2pi_pct": (s6 - SECTION_SLOPE) / SECTION_SLOPE * 100.0,
            "cd0_at_alpha0": cd0, "cd_min": cd_min,
            "cd0_from_polar": cd0_polar,
            "cd0_polar_ratio_vs_hoerner": (cd0_polar / CD0_HOERNER
                                           if math.isfinite(cd0_polar) else None),
            "cd0_alpha0_ratio_vs_hoerner": (cd0 / CD0_HOERNER
                                            if math.isfinite(cd0) else None),
            **knee, "rows": rows,
        }
    # verdict on the PRIMARY (transition) tier
    lm = out["models"]["lm"]
    slope_keeps_2pi = abs(lm["slope_dev_vs_2pi_pct"]) <= 20.0
    early_separation = (lm["knee_deg"] is not None and lm["knee_deg"] <= 8.0)
    r_polar = lm["cd0_polar_ratio_vs_hoerner"]
    drag_penalty = r_polar is not None and r_polar > 1.15
    out["verdict"] = {
        "slope_keeps_2pi_within20pct": bool(slope_keeps_2pi),
        "early_separation_knee_le8deg": bool(early_separation),
        "cd0_penalty_over_hoerner_gt15pct": bool(drag_penalty),
        "cd0_polar_ratio_vs_hoerner": r_polar,
        "alpha_work_deg": 7.108,
        "hydro_claim_survives": bool(slope_keeps_2pi and not early_separation
                                     and not drag_penalty),
        "needle_context": ("needle finding (commit 2454f01): fully-turbulent CFD "
                           "overshoots cd0 by +24% vs the transitional measurement "
                           "at low Re — the 'ft' tier here is that pessimistic drag "
                           "bracket; 'lm' (transition) is the fair low-Re cd0."),
    }
    return out


def _report(a: dict) -> None:
    print("\n=== thin-foil section polar — verdict ===", flush=True)
    print(f"tier-0: slope 2pi={SECTION_SLOPE:.3f}/rad  Hoerner cd0={CD0_HOERNER:.4f}",
          flush=True)
    for model in ("lm", "ft"):
        m = a["models"][model]
        rp = m["cd0_polar_ratio_vs_hoerner"]
        print(f"[{m['tier']}] slope(0-6) {m['slope_0_6_rad']:.3f}/rad "
              f"({m['slope_dev_vs_2pi_pct']:+.1f}% vs 2pi)  cd0_polar "
              f"{m['cd0_from_polar']:.4f} (x{rp:.2f} Hoerner)  cd0@a0 "
              f"{m['cd0_at_alpha0']:.4f}  knee {m['knee_deg']}  "
              f"CLmax {m['cl_max']:.3f}@{m['cl_max_alpha']:.0f}", flush=True)
    v = a["verdict"]
    print(f"HYDRO claim survives: {v['hydro_claim_survives']}  "
          f"(2pi slope kept {v['slope_keeps_2pi_within20pct']}, early-sep "
          f"{v['early_separation_knee_le8deg']}, cd0-penalty "
          f"{v['cd0_penalty_over_hoerner_gt15pct']})", flush=True)


def _plot(out_png: Path, results: dict, analysis: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    c_lm, c_ft, c_t0 = "#7fd4e0", "#f2a154", "#8ce39a"
    fig, ax = plt.subplots(1, 3, figsize=(15, 5), facecolor=_BG)
    for x in ax:
        x.set_facecolor(_BG)
        for s in x.spines.values():
            s.set_color(_GRID)
        x.tick_params(colors=_MUTED, labelsize=8)
        x.grid(True, color=_GRID, lw=0.6)

    aa = np.linspace(0, max(ANGLES), 60)
    ax[0].plot(aa, math.radians(1) * SECTION_SLOPE * aa, "--", color=c_t0, lw=1.6,
               label=f"tier-0 2pi ({math.radians(1)*SECTION_SLOPE:.4f}/deg)")
    for model, col, lab in (("lm", c_lm, "CFD transition (gamma-Re_theta)"),
                            ("ft", c_ft, "CFD fully-turbulent")):
        r = results[model]
        a = [x["alpha"] for x in r]
        cl = [x["cl"] for x in r]
        cd = [x["cd"] for x in r]
        ax[0].plot(a, cl, "o-", color=col, lw=1.7, ms=6, label=lab)
        ax[1].plot(cd, cl, "o-", color=col, lw=1.7, ms=6, label=lab)
        ax[2].plot(a, cd, "o-", color=col, lw=1.7, ms=6, label=lab)
    ax[1].axvline(CD0_HOERNER, color=c_t0, ls=":", lw=1.4, label="tier-0 Hoerner cd0")
    ax[2].axhline(CD0_HOERNER, color=c_t0, ls=":", lw=1.4, label="tier-0 Hoerner cd0")
    ax[2].axvline(7.108, color=_MUTED, ls="-.", lw=1.0, label="winner alpha_work 7.1")
    ax[0].set_xlabel("alpha [deg]", color=_TEXT); ax[0].set_ylabel("CL", color=_TEXT)
    ax[0].set_title("Lift curve vs tier-0 2pi", color=_TEXT)
    ax[1].set_xlabel("CD", color=_TEXT); ax[1].set_ylabel("CL", color=_TEXT)
    ax[1].set_title("Drag polar", color=_TEXT)
    ax[2].set_xlabel("alpha [deg]", color=_TEXT); ax[2].set_ylabel("CD", color=_TEXT)
    ax[2].set_title("Profile drag vs Hoerner cd0", color=_TEXT)
    for x in ax:
        x.legend(fontsize=7, facecolor=_BG, edgecolor=_GRID, labelcolor=_TEXT)
    fig.suptitle(f"THIN-FOIL section (flat-inside t/c {TC:.3f}) — section polar at "
                 f"fin Re {RE:,.0f} (U {SPEED} m/s)", color=_TEXT, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_png, dpi=130, facecolor=_BG)
    plt.close(fig)


if __name__ == "__main__":
    main()
