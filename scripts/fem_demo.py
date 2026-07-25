"""CalculiX static demo on the default fingen side fin — the FSI approval gate.

Pipeline: build the default flat-inside side fin (115 mm depth x 110 mm base,
no tabs), export STEP, mesh with gmsh into second-order tets (C3D10), write a
CalculiX deck in consistent mm-N-MPa units, solve, and render the femviz
inspection panels to out/fem-demo.png + out/fem-demo-stress.png.

Demo case definition:
- *BOUNDARY: every node with z < 0.5 mm (the planar base sits at z = 0)
  fixed in all DOF — selected by coordinate from the mesh, not via gmsh
  physical groups;
- *MATERIAL: isotropic E = 7000 MPa, nu = 0.35 (PET-CF-ish placeholder);
- *DLOAD: uniform 10 kPa (0.01 MPa) pressure on the outer (+y) face.
  Crude outer-face pick, good enough for a demo: exterior faces whose
  outward normal has n_y > 0 AND whose centroid sits at y > 1 mm — this
  skips the flat inner face (normal -y), the base (normal -z) and the
  0.7 mm TE ribbon (centroid y ~ 0.35 mm), at the price of a small sliver
  near the leading edge. 10 kPa x ~7600 mm^2 planform ~ 76 N side load,
  the working-load ballpark.

Sanity: with E = 7 GPa a beam estimate puts the tip deflection for this load
in the 1-8 mm band — micrometers or meters mean a units bug (gmsh meshes the
STEP in mm; ccx is unit-agnostic, so mm-N-MPa in => mm and MPa out).

Usage: uv run python scripts/fem_demo.py <workdir>
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from fingen.export import to_step
from fingen.femviz import CcxModel, boundary_faces, fem_report, read_inp
from fingen.loft import fin_solid
from fingen.params import FinParams, FoilFamily, FoilParams

GMSH = "/usr/bin/gmsh"
CCX = "/usr/bin/ccx"
CL_MAX = 1.8  # characteristic length, mm — ~35k C3D10 for the default fin
CL_MIN = 0.5
E_MPA, NU = 7000.0, 0.35  # PET-CF-ish placeholder
PRESSURE_MPA = 0.010  # 10 kPa demo side load on the outer face
BASE_Z_MM = 0.5  # nodes below this height form the fixed base set
OUTER_Y_MM = 1.0  # loaded-face centroid threshold (documented crude pick)


def _run(cmd: list[str], cwd: Path, name: str) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                            env={**os.environ, "OMP_NUM_THREADS": "8"})
    (cwd / f"log.{name}").write_text(result.stdout + result.stderr)
    if result.returncode != 0 or "*ERROR" in result.stdout + result.stderr:
        tail = (result.stdout + result.stderr).strip().splitlines()[-3:]
        raise RuntimeError(f"{name} failed (see {cwd}/log.{name}): {' | '.join(tail)}")


def mesh_fin(workdir: Path) -> Path:
    """STEP -> gmsh -> ABAQUS-format mesh (C3D10 volume elements)."""
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    step = to_step(fin_solid(fin), workdir / "fin.step")
    (workdir / "fin.geo").write_text(f"""\
SetFactory("OpenCASCADE");
Merge "{step.name}";
Mesh.CharacteristicLengthMax = {CL_MAX};
Mesh.CharacteristicLengthMin = {CL_MIN};
Mesh.CharacteristicLengthFromCurvature = 1;
Mesh.MinimumCirclePoints = 12;
Mesh.ElementOrder = 2;
Mesh.Optimize = 1;
// Straight midside nodes: curved ones fold (negative Jacobian) in the thin
// trailing-edge wedge, and at ~4 mm elements the fidelity loss is nil.
Mesh.SecondOrderLinear = 1;
""")
    inp = workdir / "fin-gmsh.inp"
    _run([GMSH, "-3", "-order", "2", "-format", "inp", "-o", str(inp), "fin.geo"],
         workdir, "gmsh")
    return inp


def pick_loaded_faces(model: CcxModel) -> list[tuple[int, int]]:
    """(element, ccx face number) of the outer-face pressure patch."""
    loaded = []
    for eid, fno, tri in boundary_faces(model):
        a, b, c = (model.nodes[n] for n in tri)
        normal = np.cross(b - a, c - a)  # outward by construction
        if normal[1] > 0.0 and (a[1] + b[1] + c[1]) / 3.0 > OUTER_Y_MM:
            loaded.append((eid, fno))
    return loaded


def write_deck(workdir: Path, model: CcxModel, base: list[int],
               loaded: list[tuple[int, int]]) -> Path:
    """Clean mesh include + the ccx job deck (linear static, mm-N-MPa)."""
    mesh_lines = ["*NODE, NSET=NALL"]
    mesh_lines += [f"{nid}, {x:.9g}, {y:.9g}, {z:.9g}"
                   for nid, (x, y, z) in sorted(model.nodes.items())]
    mesh_lines.append("*ELEMENT, TYPE=C3D10, ELSET=EALL")
    mesh_lines += [f"{eid}, " + ", ".join(map(str, conn))
                   for eid, conn in sorted(model.elements.items())]
    (workdir / "fin-mesh.inp").write_text("\n".join(mesh_lines) + "\n")

    deck = ["** fingen FEM demo — default side fin, mm-N-MPa",
            "*INCLUDE, INPUT=fin-mesh.inp",
            "*NSET, NSET=BASE"]
    deck += [", ".join(map(str, base[i:i + 8])) for i in range(0, len(base), 8)]
    deck += ["*MATERIAL, NAME=PETCF",
             "*ELASTIC",
             f"{E_MPA:g}, {NU:g}",
             "*SOLID SECTION, ELSET=EALL, MATERIAL=PETCF",
             "*BOUNDARY",
             "BASE, 1, 3",
             "*STEP",
             "*STATIC",
             "*DLOAD"]
    deck += [f"{eid}, P{fno}, {PRESSURE_MPA:g}" for eid, fno in sorted(loaded)]
    deck += ["*NODE FILE", "U", "*EL FILE", "S", "*END STEP"]
    job = workdir / "job.inp"
    job.write_text("\n".join(deck) + "\n")
    return job


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    t0 = time.time()
    workdir = Path(sys.argv[1])
    workdir.mkdir(parents=True, exist_ok=True)

    mesh = read_inp(mesh_fin(workdir))
    base = sorted(nid for nid, xyz in mesh.nodes.items() if xyz[2] < BASE_Z_MM)
    loaded = pick_loaded_faces(mesh)
    if not base or not loaded:
        raise RuntimeError(f"empty set: {len(base)} base nodes, "
                           f"{len(loaded)} loaded faces")
    print(f"mesh: {len(mesh.elements):,} C3D10 / {len(mesh.nodes):,} nodes · "
          f"{len(base)} base nodes fixed · {len(loaded)} faces at "
          f"{PRESSURE_MPA * 1e3:g} kPa", flush=True)

    job = write_deck(workdir, mesh, base, loaded)
    _run([CCX, "-i", job.stem], workdir, "ccx")

    repo_out = Path(__file__).resolve().parents[1] / "out"
    report = fem_report(workdir / "job.frd", job, repo_out / "fem-demo.png",
                        repo_out / "fem-demo-stress.png")
    u_max = report["u_max_mm"]
    if not 0.05 < u_max < 50.0:
        raise RuntimeError(f"max |u| = {u_max:.3g} mm is outside any plausible "
                           "band for this load — hunt the units bug (expect "
                           "mm-N-MPa throughout)")
    print(f"max |u| {u_max:.2f} mm · max von Mises {report['vm_max_mpa']:.1f} MPa "
          f"· allowable {report['allow_mpa']:.1f} MPa (pet-cf) "
          f"· SF {report['safety_factor']:.2f}", flush=True)
    print(f"resultant {report['force_n']:.0f} N · drawn exaggeration "
          f"×{report['exaggeration']:g}", flush=True)
    print(f"plots: {report['png']} · {report['stress_png']} "
          f"({time.time() - t0:.0f} s)", flush=True)


if __name__ == "__main__":
    main()
