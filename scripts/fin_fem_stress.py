"""Build a fin from slider params, run a CalculiX static solve, and export a
von Mises stress SURFACE for the marketing flow video.

Pipeline (reusing scripts/fem_demo.py's deck writer and load picks):
build the blade solid -> gmsh second-order tets (C3D10) -> CalculiX static
(fixed base, uniform outer-face pressure, mm-N-MPa) -> parse the .frd nodal
stress -> extract the outer triangle surface with nodal von Mises -> save a
plain ``stress-surface.npz`` (points in METRES, triangle faces, von Mises in
MPa). That .npz feeds ``scripts/flow_video.py --fem-surface`` so the render
stays a pyvista-only job with no fingen/OCCT import.

Usage: uv run python scripts/fin_fem_stress.py <workdir> [overrides]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fem_demo as fd  # deck writer, load picks, tool paths, thresholds

from fingen.export import to_step
from fingen.femviz import boundary_faces, parse_frd, read_inp, von_mises
from fingen.loft import fin_solid
from fingen.params import (
    FinParams,
    FoilFamily,
    FoilParams,
    GrooveParams,
    GrooveSurface,
    OutlineParams,
    TabParams,
    TabSystem,
)

CL_MAX = 2.0  # mm; a marketing surface, not a mesh-convergence study


def make_fin(a: argparse.Namespace) -> FinParams:
    grooves = (GrooveParams(count=a.grooves, length=a.groove_length,
                            pitch=a.groove_pitch, width=a.groove_width,
                            depth_ratio=a.groove_depth, span_start=a.groove_start,
                            surface=GrooveSurface.OUTER)
               if a.grooves else GrooveParams(count=0))
    return FinParams(
        outline=OutlineParams(depth=a.depth, base=a.base, sweep=a.sweep,
                              tip_width_ratio=a.tip_width, le_fullness=a.le_fullness,
                              te_shape=a.te_shape),
        foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=a.thickness,
                        camber_ratio=a.camber, camber_position=a.camber_pos,
                        te_thickness=a.te_thickness),
        thickness_tip_factor=a.tip_factor,
        grooves=grooves,
        tabs=TabParams(system=TabSystem.NONE),
    )


def run(cmd: list[str], cwd: Path, name: str) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    (cwd / f"log.{name}").write_text(r.stdout + r.stderr)
    if r.returncode != 0 or "*ERROR" in (r.stdout + r.stderr):
        sys.exit(f"{name} failed (see {cwd}/log.{name}):\n" + (r.stdout + r.stderr)[-1500:])


def solve(workdir: Path, fin: FinParams) -> None:
    step = to_step(fin_solid(fin), workdir / "fin.step")
    (workdir / "fin.geo").write_text(f"""\
SetFactory("OpenCASCADE");
Merge "{step.name}";
Mesh.CharacteristicLengthMax = {CL_MAX};
Mesh.CharacteristicLengthMin = {fd.CL_MIN};
Mesh.CharacteristicLengthFromCurvature = 1;
Mesh.MinimumCirclePoints = 12;
Mesh.ElementOrder = 2;
Mesh.Optimize = 1;
Mesh.SecondOrderLinear = 1;
""")
    inp = workdir / "fin-gmsh.inp"
    run([fd.GMSH, "-3", "-order", "2", "-format", "inp", "-o", str(inp), "fin.geo"],
        workdir, "gmsh")
    mesh = read_inp(inp)
    base = sorted(n for n, xyz in mesh.nodes.items() if xyz[2] < fd.BASE_Z_MM)
    loaded = fd.pick_loaded_faces(mesh)
    if not base or not loaded:
        sys.exit(f"empty set: {len(base)} base nodes, {len(loaded)} loaded faces")
    print(f"mesh: {len(mesh.elements):,} C3D10 / {len(mesh.nodes):,} nodes · "
          f"{len(base)} base · {len(loaded)} loaded faces", flush=True)
    job = fd.write_deck(workdir, mesh, base, loaded)
    run([fd.CCX, "-i", job.stem], workdir, "ccx")


def export_surface(workdir: Path) -> Path:
    """Outer triangle surface -> stress-surface.npz: points & nodal displacement
    in METRES, triangle faces, nodal von Mises in MPa. The displacement lets the
    render flex the blade (points + factor·disp) for the breathing-fin effect."""
    frd = parse_frd(workdir / "job.frd")
    model = read_inp(workdir / "job.inp")
    vm = von_mises(frd.stress)
    idx = {nid: k for k, nid in enumerate(frd.node_ids)}
    tris = np.array([[idx[a], idx[b], idx[c]]
                     for _, _, (a, b, c) in boundary_faces(model)], dtype=np.int64)
    out = workdir / "stress-surface.npz"
    np.savez(out, points=frd.coords * 0.001, faces=tris, vm=vm,
             disp=frd.displacement * 0.001)
    umax = float(np.linalg.norm(frd.displacement, axis=1).max())
    print(f"von Mises: max {vm.max():.2f} MPa · p98 {np.percentile(vm, 98):.2f} · "
          f"max |u| {umax:.2f} mm · {len(tris):,} surface tris -> {out}", flush=True)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workdir", type=Path)
    # Outline / foil sliders (T-FINS hero-fin defaults).
    p.add_argument("--depth", type=float, default=115.0)
    p.add_argument("--base", type=float, default=110.0)
    p.add_argument("--sweep", type=float, default=42.0)
    p.add_argument("--tip-width", type=float, default=0.6, dest="tip_width")
    p.add_argument("--le-fullness", type=float, default=0.57, dest="le_fullness")
    p.add_argument("--te-shape", type=float, default=-0.32, dest="te_shape")
    p.add_argument("--thickness", type=float, default=0.09)
    p.add_argument("--camber", type=float, default=0.0)
    p.add_argument("--camber-pos", type=float, default=0.4, dest="camber_pos")
    p.add_argument("--te-thickness", type=float, default=0.7, dest="te_thickness")
    p.add_argument("--tip-factor", type=float, default=0.85, dest="tip_factor")
    # Grooves.
    p.add_argument("--grooves", type=int, default=3)
    p.add_argument("--groove-length", type=float, default=64.0, dest="groove_length")
    p.add_argument("--groove-pitch", type=float, default=18.5, dest="groove_pitch")
    p.add_argument("--groove-width", type=float, default=7.5, dest="groove_width")
    p.add_argument("--groove-depth", type=float, default=0.29, dest="groove_depth")
    p.add_argument("--groove-start", type=float, default=0.3, dest="groove_start")
    args = p.parse_args()

    t0 = time.time()
    args.workdir.mkdir(parents=True, exist_ok=True)
    solve(args.workdir, make_fin(args))
    export_surface(args.workdir)
    print(f"done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
