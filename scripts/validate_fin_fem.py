"""Tier-1 STRUCTURAL validation of an optimizer winner: tier-0 beam vs 3D FEM.

Reads a result JSON, rebuilds each designed blade, meshes it, solves a linear
static CalculiX case at the DESIGN PEAK LOAD, and prints tier-0's predictions
beside the FEM's. This is the structural half of the adjudication pipeline
(task #17); the CFD half is scripts/submit_cfd_validation.py, which needs the
cluster LAN.

WHY IT MATTERS FOR THE CURRENT WINNER. flex.py's bending compliance carries an
empirical 3D knockdown, 1 + ROOT_COMPLIANCE_SLOPE*(c_root/span), fitted to
exactly TWO anchors at c/s 0.40 and 0.96. The 46 kg ppa-cf winner sits at
c/s 1.055 — outside both — and is pinned on tip_deflection_max_frac = 0.15, the
limit past which the linear model that produced every structural number it
reports is out of validity. So the design sits at the corner of an
extrapolated calibration AND a validity edge. That is precisely the fin worth
solving in 3D before printing.

WHAT IS AND IS NOT COMPARABLE:
  * TIP DEFLECTION is the clean comparison — it is what ROOT_COMPLIANCE_SLOPE
    was calibrated on, and the FEM uses the same E and nu, so a discrepancy is
    the structural model, not the material.
  * PEAK STRESS is NOT like-for-like. Tier-0 reports beam bending stress on the
    extreme fibre; the FEM's von Mises includes the clamp singularity at the
    fixed base, which is a boundary-condition artifact that mesh refinement
    makes WORSE, not better. The script therefore reports von Mises both
    overall and excluding a root band, and treats only the latter as meaningful.
  * The base is fixed at the BLADE ROOT PLANE, not at the box interface, so the
    tab is not resolved here. That is task #24.

Usage: uv run python scripts/validate_fin_fem.py <result.json> <workdir> [blade ...]
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fem_demo as fd  # tool paths, mesh recipe, deck writer

from fingen.export import to_step
from fingen.femviz import boundary_faces, parse_frd, read_inp, von_mises
from fingen.flex import flex_report
from fingen.loft import fin_solid
from fingen.materials import get_card
from fingen.optimize import fin_from_dict
from fingen.params import FinConfig, TabSystem
from fingen.sizing import Skill, anchor

# Element size, mm: finer than fem_demo's 1.8, since this is a validation. gmsh
# occasionally fails on one geometry at one size and succeeds at a neighbour
# (seen at 1.3 on the torsion study, 1.4 on a small-wave blade), so the size is
# overridable: FEM_CL=1.2 scripts/validate_fin_fem.py ...
CL_MAX = float(os.environ.get("FEM_CL", "1.4"))
# Minimum size must resolve the thinnest gap between faces. A wide, thin blade
# (base 133 mm at t/c 0.063) has a trailing-edge zone under 1 mm thick that
# reaches far enough forward for fem_demo's 0.5 mm floor to let the upper and
# lower surface meshes overlap ("Invalid boundary mesh (overlapping facets)").
CL_MIN = float(os.environ.get("FEM_CL_MIN", str(fd.CL_MIN)))
ROOT_EXCLUDE_FRAC = 0.06   # ignore von Mises within this span fraction of the clamp


def mesh_blade(fin, workdir: Path) -> Path:
    step = to_step(fin_solid(fin), workdir / "fin.step")
    (workdir / "fin.geo").write_text(
        f'SetFactory("OpenCASCADE");\nMerge "{step.name}";\n'
        f"Mesh.CharacteristicLengthMax = {CL_MAX};\n"
        f"Mesh.CharacteristicLengthMin = {CL_MIN};\n"
        "Mesh.CharacteristicLengthFromCurvature = 1;\nMesh.MinimumCirclePoints = 12;\n"
        "Mesh.ElementOrder = 2;\nMesh.Optimize = 1;\nMesh.SecondOrderLinear = 1;\n")
    inp = workdir / "fin-gmsh.inp"
    fd._run([fd.GMSH, "-3", "-order", "2", "-format", "inp", "-o", str(inp), "fin.geo"],
            workdir, "gmsh")
    return inp


def solve(fin, force_n: float, e_mpa: float, nu: float, workdir: Path) -> dict:
    """Linear static at `force_n` spread over the outer face. Returns FEM scalars."""
    model = read_inp(mesh_blade(fin, workdir))
    base = sorted(n for n, xyz in model.nodes.items() if xyz[2] < fd.BASE_Z_MM)
    loaded = fd.pick_loaded_faces(model)
    if not base or not loaded:
        raise RuntimeError(f"empty set: {len(base)} base, {len(loaded)} loaded")

    # Scale pressure so the RESULTANT equals the design load: the tier-0 number
    # is a force, and comparing deflections under different totals is comparing
    # nothing. Area from the actual loaded triangles, not the planform.
    area = 0.0
    for eid, _fno, tri in boundary_faces(model):
        a, b, c = (model.nodes[n] for n in tri)
        area += 0.5 * float(np.linalg.norm(np.cross(b - a, c - a)))
    loaded_ids = {(e, f) for e, f in loaded}
    area = 0.0
    for eid, fno, tri in boundary_faces(model):
        if (eid, fno) in loaded_ids:
            a, b, c = (model.nodes[n] for n in tri)
            area += 0.5 * float(np.linalg.norm(np.cross(b - a, c - a)))
    pressure = force_n / area  # MPa (N/mm^2)

    fd.E_MPA, fd.NU, fd.PRESSURE_MPA = e_mpa, nu, pressure
    job = fd.write_deck(workdir, model, base, loaded)
    fd._run([fd.CCX, "-i", job.stem], workdir, "ccx")

    frd = parse_frd(workdir / "job.frd")
    u = frd.displacement
    vm = von_mises(frd.stress)
    z = frd.coords[:, 2]
    span = float(z.max() - z.min())
    tip = z >= z.min() + 0.97 * span
    clear = z >= z.min() + ROOT_EXCLUDE_FRAC * span
    return {
        "n_elements": len(model.elements), "loaded_area_mm2": area,
        "pressure_mpa": pressure, "resultant_n": pressure * area,
        "tip_defl_mm": float(np.abs(u[tip, 1]).mean()),
        "u_max_mm": float(np.abs(u).max()),
        "vm_max_mpa": float(vm.max()),
        # A single degenerate tet extrapolates garbage to its nodes: one run put a
        # 144 N centre blade at 7516 MPa while its deflection was a normal 3.0 mm.
        # The 99.9th percentile of nodes clear of the clamp is the reported peak;
        # the raw max is kept only to flag when it disagrees.
        "vm_max_clear_mpa": float(np.percentile(vm[clear], 99.9)),
        "vm_rawmax_clear_mpa": float(vm[clear].max()),
        "span_mm": span,
    }


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    result = json.loads(Path(sys.argv[1]).read_text())
    root = Path(sys.argv[2]); root.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[3:] or ["side", "center"]

    r = result["rider"]
    card = get_card(r["material"])
    # EACH BLADE AT ITS OWN DESIGN LOAD. This used to build one sheet (the
    # dominant member's) and load the centre with the SIDE blade's peak force —
    # 33% too high on a 60 kg Pro thruster (317.7 N vs the centre's 238.3 N) — so
    # a centre the search had legitimately kept inside tip_deflection_max_frac
    # read 20% here. FEM-vs-tier-0 ratios were still like-for-like (both sides
    # used the same wrong force), but the absolute SF and deflection were not.
    def sheet_for(member: str):
        return anchor(r["weight_kg"], Skill[r["skill"]], design_speed=r["speed_ms"],
                      config=FinConfig(r["config"]), material=r["material"],
                      tabs=TabSystem(r["tabs"]), member=member)
    sheets = {"side": sheet_for("dominant"), "center": sheet_for("center")}
    blades = {"side": result["fin"], "center": result.get("center_fin")}

    for name in wanted:
        raw = blades.get(name)
        if raw is None:
            print(f"[{name}] not in this result — skipping", flush=True); continue
        fin = fin_from_dict(raw)
        t0 = time.time()
        sheet = sheets[name]
        t0r = flex_report(fin, sheet.force_peak_n, r["speed_ms"], material=r["material"])
        fem = solve(fin, sheet.force_peak_n, card.e_mpa, card.nu, root / name)

        cs = fin.outline.base / fin.outline.depth
        print(f"\n=== {name}: c/s {cs:.3f} · {fem['n_elements']:,} C3D10 · "
              f"{sheet.force_peak_n:.1f} N over {fem['loaded_area_mm2']:.0f} mm2 "
              f"({fem['pressure_mpa']*1e3:.2f} kPa) · {time.time()-t0:.0f}s")
        d0, d1 = t0r.tip_deflection_mm, fem["tip_defl_mm"]
        print(f"  {'tip deflection mm':24} tier-0 {d0:8.3f}   FEM {d1:8.3f}   "
              f"FEM/tier-0 {d1/d0:5.3f}")
        print(f"  {'tip defl % span':24} tier-0 {100*d0/fem['span_mm']:8.2f}   "
              f"FEM {100*d1/fem['span_mm']:8.2f}")
        s0 = t0r.stress_max_mpa
        p999, rawc = fem["vm_max_clear_mpa"], fem["vm_rawmax_clear_mpa"]
        flag = "   <- raw max is a mesh artifact" if rawc > 2.0 * p999 else ""
        print(f"  {'peak stress MPa':24} tier-0 {s0:8.2f}   FEM {p999:8.2f} "
              f"(p99.9 clear of clamp)   raw max {rawc:.1f}{flag}")
        print(f"  {'safety factor':24} tier-0 {t0r.allow_mpa/s0:8.3f}   "
              f"FEM {t0r.allow_mpa/fem['vm_max_clear_mpa']:8.3f}   "
              f"(allowable {t0r.allow_mpa:.2f} MPa)")


if __name__ == "__main__":
    main()
