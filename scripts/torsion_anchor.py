"""Torsional anchor: 3D FEM vs tier-0 Saint-Venant GJ, over a stubbiness sweep.

WHY. flex.py scales BENDING compliance by 1 + ROOT_COMPLIANCE_SLOPE*(c_root/span)
— a slope fitted to two 3D anchors, worth +49% on the 46 kg anchor fin — because
Euler-Bernoulli on the wetted span misses root warping, shear lag and plate
behaviour. TORSION gets no such correction at all: `gj = G * j_strip` is raw
Saint-Venant. This script produces the missing anchor.

THE LOAD CASE IS A PURE COUPLE, and that is the whole trick. Nodal y-forces on a
tip slab are set to F_i = k*(x_i - xbar), so sum(F) is exactly zero while the
z-moment is k*sum((x_i-xbar)^2). Zero resultant means:
  * no bending response to contaminate the twist reading (an offset point load
    would give bend AND twist, and separating them is exactly the error term we
    are trying to measure);
  * the applied torque is the SAME about every axis parallel to z, so there is
    no elastic-axis ambiguity in the reference value.

WHAT IS MEASURED. Per spanwise slab, the section's rigid-body rotation about z
is least-squares fitted from the nodal displacement field:
    phi = sum(x~*uy~ - y~*ux~) / sum(x~^2 + y~^2)          (tildes = mean-removed)
Tier-0's prediction for the same geometry and torque is the Saint-Venant
integral phi_0(z) = T * integral_0^z dz'/(G*J_strip(z')), built from the SAME
station/section machinery flex_report uses, so the two differ only in 3D effects.

The reported anchor is the compliance ratio phi_fem/phi_0 — directly comparable
to the bending anchors' "needs x1.18" / "needs x1.51". Two competing effects
live in it, and their SIGNS are opposite:
  * root warping restraint: a built-in root prevents the section warping out of
    plane, stiffening the blade near the clamp -> ratio < 1;
  * finite width-to-thickness shape error: J_strip = (1/3)*integral t^3 dx
    overestimates the true Saint-Venant constant by ~6-12% over our t/c range
    -> ratio > 1.
Which dominates, and how the balance moves with c_root/span, is the open
question this exists to answer. Nothing here is fed back into flex.py
automatically — the fit is reported for a human to accept.

Usage: uv run python scripts/torsion_anchor.py <workdir> [case ...]
       cases default to the full sweep; name them to run a subset.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from fingen.export import to_step
from fingen.femviz import CcxModel, parse_frd, read_inp
from fingen.flex import POISSON, section_mech
from fingen.foil import section_points
from fingen.loft import _groove_thins, _thickness_at, fin_solid, groove_station_z
from fingen.outline import chord_schedule
from fingen.params import (
    FinParams,
    FoilFamily,
    FoilParams,
    GenSettings,
    OutlineParams,
)

GMSH = "/usr/bin/gmsh"
CCX = "/usr/bin/ccx"
# Element size, mm. Overridable because the anchor ratio is only worth
# believing if it is mesh-converged — a torsion field is carried by the thin
# outer material, exactly where a coarse tet mesh is weakest, so the study has
# to be run at more than one resolution before the number goes anywhere near
# flex.py. TORSION_CL=1.2 scripts/torsion_anchor.py ... to refine.
CL_MAX = float(os.environ.get("TORSION_CL", "1.8"))
CL_MIN = 0.5
E_MPA = 7000.0            # same placeholder as fem_demo; the RATIO is E-independent
TORQUE_NMM = 1000.0       # ~1 deg of tip twist on the default fin: linear, small-angle
BASE_Z_MM = 0.5
# Couple applied above this fraction of span. Overridable for the same reason
# CL_MAX is: the outboard ratio is read below the patch, and "below" has to be
# far enough that Saint-Venant's principle has actually done its work. Moving
# the patch and seeing the read band not move is the check.
TIP_LOAD_FRAC = float(os.environ.get("TORSION_LOAD_FRAC", "0.90"))
READ_LO, READ_HI = 0.06, 0.80   # twist read band (clear of clamp mesh and load patch)
N_SLABS = 26

# Stubbiness sweep. c_root/span is the parameter the BENDING slope is written
# against, so the torsional fit is expressed against the same abscissa; the
# bending anchors sat at 0.40 and 0.96, and real side fins cluster near 0.9.
CASES: dict[str, tuple[float, float]] = {
    # name:        (depth mm, base mm)  ->  c/s
    "veryslender": (260.0, 70.0),    # 0.27
    "slender":     (200.0, 80.0),    # 0.40 — matches the Zar14 bending anchor
    "slender2":    (175.0, 88.0),    # 0.50
    "mid":         (150.0, 95.0),    # 0.63
    "mid2":        (130.0, 102.0),   # 0.78
    "default":     (115.0, 110.0),   # 0.96 — matches the CalculiX bending anchor
    "stubby":      (100.0, 125.0),   # 1.25
    "verystubby":  (85.0, 135.0),    # 1.59
    # Chord held FIXED while span varies, to separate c/s from absolute size:
    # if the boundary layer really scales with chord, these four share one
    # boundary-layer LENGTH and differ only in how much span sits outside it.
    "fixc_a":      (220.0, 110.0),   # 0.50, same chord as `default`
    "fixc_b":      (160.0, 110.0),   # 0.69
    "fixc_c":      (135.0, 110.0),   # 0.81
    "fixc_d":      (95.0, 110.0),    # 1.16
}


def _run(cmd: list[str], cwd: Path, name: str) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                            env={**os.environ, "OMP_NUM_THREADS": "8"})
    (cwd / f"log.{name}").write_text(result.stdout + result.stderr)
    if result.returncode != 0 or "*ERROR" in result.stdout + result.stderr:
        tail = (result.stdout + result.stderr).strip().splitlines()[-3:]
        raise RuntimeError(f"{name} failed (see {cwd}/log.{name}): {' | '.join(tail)}")


def build_fin(depth: float, base: float) -> FinParams:
    """Untabbed flat-inside blade. No grooves and no tabs on purpose: both add
    3D features that would confound the one effect being measured."""
    return FinParams(outline=OutlineParams(depth=depth, base=base),
                     foil=FoilParams(family=FoilFamily.FLAT_INSIDE))


def mesh_fin(fin: FinParams, workdir: Path) -> Path:
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
Mesh.SecondOrderLinear = 1;
""")
    inp = workdir / "fin-gmsh.inp"
    _run([GMSH, "-3", "-order", "2", "-format", "inp", "-o", str(inp), "fin.geo"],
         workdir, "gmsh")
    return inp


def tip_couple(model: CcxModel, torque_nmm: float
               ) -> tuple[list[tuple[int, float]], float]:
    """(node, Fy) pairs forming a pure z-couple on the tip slab, and its z span.

    F_i = k*(x_i - xbar) with k set from the requested torque. sum(F) vanishes
    identically, so the resultant is zero to machine precision rather than to
    whatever a hand-built patch happens to cancel to — the whole point.
    """
    zs = np.array([xyz[2] for xyz in model.nodes.values()])
    z_cut = zs.min() + TIP_LOAD_FRAC * (zs.max() - zs.min())
    ids = [nid for nid, xyz in model.nodes.items() if xyz[2] >= z_cut]
    if len(ids) < 12:
        raise RuntimeError(f"only {len(ids)} tip nodes above z={z_cut:.1f}")
    x = np.array([model.nodes[n][0] for n in ids])
    dx = x - x.mean()
    denom = float(np.sum(dx**2))
    if denom <= 0:
        raise RuntimeError("degenerate tip slab: zero chordwise spread")
    k = torque_nmm / denom
    return [(n, float(k * d)) for n, d in zip(ids, dx)], z_cut


def write_deck(workdir: Path, model: CcxModel, base: list[int],
               loads: list[tuple[int, float]]) -> Path:
    mesh_lines = ["*NODE, NSET=NALL"]
    mesh_lines += [f"{nid}, {x:.9g}, {y:.9g}, {z:.9g}"
                   for nid, (x, y, z) in sorted(model.nodes.items())]
    mesh_lines.append("*ELEMENT, TYPE=C3D10, ELSET=EALL")
    mesh_lines += [f"{eid}, " + ", ".join(map(str, conn))
                   for eid, conn in sorted(model.elements.items())]
    (workdir / "fin-mesh.inp").write_text("\n".join(mesh_lines) + "\n")

    deck = ["** fingen torsional anchor — pure tip couple, mm-N-MPa",
            "*INCLUDE, INPUT=fin-mesh.inp",
            "*NSET, NSET=BASE"]
    deck += [", ".join(map(str, base[i:i + 8])) for i in range(0, len(base), 8)]
    deck += ["*MATERIAL, NAME=ISO",
             "*ELASTIC",
             f"{E_MPA:g}, {POISSON:g}",
             "*SOLID SECTION, ELSET=EALL, MATERIAL=ISO",
             "*BOUNDARY",
             "BASE, 1, 3",
             "*STEP",
             "*STATIC",
             "*CLOAD"]
    deck += [f"{nid}, 2, {fy:.9g}" for nid, fy in sorted(loads)]
    deck += ["*NODE FILE", "U", "*END STEP"]
    job = workdir / "job.inp"
    job.write_text("\n".join(deck) + "\n")
    return job


def phi_profile(coords: np.ndarray, disp: np.ndarray, z_lo: float, z_hi: float
                ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(z, phi_rad, n_nodes) per slab: least-squares rigid rotation about z."""
    edges = np.linspace(z_lo, z_hi, N_SLABS + 1)
    zc, phis, counts = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (coords[:, 2] >= lo) & (coords[:, 2] < hi)
        if m.sum() < 12:
            continue
        x, y = coords[m, 0], coords[m, 1]
        ux, uy = disp[m, 0], disp[m, 1]
        xt, yt = x - x.mean(), y - y.mean()
        uxt, uyt = ux - ux.mean(), uy - uy.mean()
        denom = float(np.sum(xt**2 + yt**2))
        if denom <= 0:
            continue
        zc.append(0.5 * (lo + hi))
        phis.append(float(np.sum(xt * uyt - yt * uxt) / denom))
        counts.append(int(m.sum()))
    return np.array(zc), np.array(phis), np.array(counts)


def tier0_phi(fin: FinParams, z_query: np.ndarray, torque_nmm: float) -> np.ndarray:
    """Saint-Venant twist phi_0(z) = T * cumulative integral of 1/(G*J_strip).

    Uses flex_report's own station/section path so the only difference from
    tier-0 is the 3D solve, not a re-derived section model.
    """
    # 60 stations is the GenSettings ceiling; flex_report itself runs 40, and the
    # J(z) integrand is smooth, so the tier-0 reference is converged well inside
    # the 3D effect being measured.
    settings = GenSettings(n_stations=60, n_foil_points=160)
    stations = chord_schedule(fin.outline, settings, tip_chord_min=settings.cap_chord,
                              extra_z=groove_station_z(fin))
    z, j = [], []
    for st in stations:
        thin_outer, thin_inner = _groove_thins(fin, st.z, st.chord)
        up, lo = section_points(fin.foil, st.chord,
                                thickness_ratio=_thickness_at(fin, st.z),
                                n_points=settings.n_foil_points,
                                thin_outer=thin_outer, thin_inner=thin_inner)
        z.append(st.z)
        j.append(section_mech(up, lo).j_mm4)
    z, j = np.array(z), np.array(j)
    g = E_MPA / (2.0 * (1.0 + POISSON))
    # Integrate 1/(G*J) from the root on a dense grid, then sample.
    zz = np.linspace(z.min(), z.max(), 4000)
    inv_gj = 1.0 / np.maximum(np.interp(zz, z, j) * g, 1e-12)
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (inv_gj[1:] + inv_gj[:-1]) * np.diff(zz))])
    return torque_nmm * np.interp(z_query, zz, cum)


def run_case(name: str, depth: float, base: float, root: Path) -> dict:
    workdir = root / name
    workdir.mkdir(parents=True, exist_ok=True)
    fin = build_fin(depth, base)
    t0 = time.time()

    model = read_inp(mesh_fin(fin, workdir))
    base_ids = sorted(n for n, xyz in model.nodes.items() if xyz[2] < BASE_Z_MM)
    loads, z_cut = tip_couple(model, TORQUE_NMM)
    if not base_ids:
        raise RuntimeError("no base nodes")
    resultant = sum(f for _, f in loads)
    print(f"[{name}] mesh {len(model.elements):,} C3D10 / {len(model.nodes):,} nodes · "
          f"{len(base_ids)} fixed · couple on {len(loads)} nodes above "
          f"z={z_cut:.1f} · resultant {resultant:+.2e} N", flush=True)

    job = write_deck(workdir, model, base_ids, loads)
    _run([CCX, "-i", job.stem], workdir, "ccx")

    frd = parse_frd(workdir / "job.frd")
    coords, disp = frd.coords, frd.displacement
    span = float(coords[:, 2].max() - coords[:, 2].min())
    z, phi_fem, counts = phi_profile(coords, disp,
                                     coords[:, 2].min() + READ_LO * span,
                                     coords[:, 2].min() + READ_HI * span)
    phi_0 = tier0_phi(fin, z, TORQUE_NMM)
    good = phi_0 > 0
    ratio = np.where(good, phi_fem / np.where(good, phi_0, 1.0), np.nan)

    c_over_s = base / depth
    # Headline anchor: the ratio at the top of the read band, i.e. the
    # accumulated compliance over essentially the whole loaded span — the same
    # quantity the bending anchors report ("needs x1.18").
    far = float(ratio[-1])
    print(f"[{name}] c/s {c_over_s:.2f} · tip twist FEM {np.degrees(phi_fem[-1]):.4f} deg "
          f"vs tier-0 {np.degrees(phi_0[-1]):.4f} deg · ANCHOR x{far:.3f} "
          f"({time.time() - t0:.0f} s)", flush=True)
    return {
        "case": name, "depth_mm": depth, "base_mm": base, "c_over_s": c_over_s,
        "torque_nmm": TORQUE_NMM, "n_elements": len(model.elements),
        "resultant_n": resultant,
        "anchor_ratio": far,
        "z_mm": z.tolist(), "z_frac": (z / span).tolist(),
        "phi_fem_deg": np.degrees(phi_fem).tolist(),
        "phi_tier0_deg": np.degrees(phi_0).tolist(),
        "ratio": ratio.tolist(), "slab_nodes": counts.tolist(),
    }


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = Path(sys.argv[1])
    root.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[2:] or list(CASES)
    results = []
    for name in wanted:
        if name not in CASES:
            raise SystemExit(f"unknown case {name!r}; have {sorted(CASES)}")
        results.append(run_case(name, *CASES[name], root))

    out = Path(__file__).resolve().parents[1] / "out" / "torsion-anchor.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"e_mpa": E_MPA, "nu": POISSON,
                               "torque_nmm": TORQUE_NMM,
                               "cases": results}, indent=2) + "\n")
    print(f"\n{'case':10} {'c/s':>6} {'anchor x':>9}")
    for r in results:
        print(f"{r['case']:10} {r['c_over_s']:6.2f} {r['anchor_ratio']:9.3f}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
