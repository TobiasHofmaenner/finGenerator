"""Build the section table shipped with fingen (src/fingen/data/sections_v0.npz).

    uv run --with neuralfoil python scripts/build_section_table.py [--out=PATH]

fingen.sections reads cl, cd and cm of the three foil families from a table, so
the library itself needs nothing but numpy. This script fills that table with
NeuralFoil (a neural surrogate of XFOIL, MIT licence) run in a throwaway
overlay — it is NOT a dependency of the package.

Why NeuralFoil as the base, and what it is checked against
(docs/MODEL-EXTENSION.md): on our own flat-inside section it agrees with
resolved-wall 2-D RANS at the four points run so far (cl 0.43 / 0.86 / 1.35 at
0 / 4 / 12 deg, cd 0.042 at -3.5 deg, Re 5.7e5), and with the zero-lift angle
of the set CFD and of the [BW04] tunnel fin (-3.5 deg). It OVER-reads the
maximum lift of a conventional section (NACA 0012 at Re 7e5: 1.33 at 15 deg
against 1.075 measured, 1.11 resolved-wall RANS), so the stall region of this
table is provisional until the RANS section tables
(finGenerator-cfd/scripts/section_polar.py) are folded in as corrections.

Table layout (all arrays float32, alpha in degrees, Reynolds on a log grid):
  symmetric, flat_inside : [thickness, reynolds, alpha]
  cambered               : [thickness, camber, reynolds, alpha]   (camber at 40 % chord)
Sections are fingen's own (`foil.section_points`) with the trailing edge at 1 %
of chord (0.7 mm on a 70 mm chord). Boundary layer tripped at 5 % chord on
both faces — the closest analogue of a printed fin in turbulent surf and of
our fully turbulent RANS.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import neuralfoil as nf
import numpy as np

from fingen.foil import section_points
from fingen.params import FoilFamily, FoilParams

ALPHA = np.arange(-16.0, 24.01, 0.5)
REYNOLDS = np.array([1.0e5, 2.0e5, 4.0e5, 8.0e5, 1.6e6])
TC = np.array([0.04, 0.05, 0.06, 0.075, 0.09, 0.11, 0.13, 0.16, 0.19, 0.22])
TC_CAMBERED = np.array([0.05, 0.07, 0.09, 0.12, 0.16])
CAMBER = np.array([0.0, 0.01, 0.02, 0.03, 0.04, 0.05])
CAMBER_POSITION = 0.4
CHORD_MM, TE_MM = 70.0, 0.7
TRIP = 0.05


def _coords(foil: FoilParams) -> np.ndarray:
    up, lo = section_points(foil, CHORD_MM, thickness_ratio=foil.thickness_ratio, n_points=200)
    return np.vstack([up[::-1], lo[1:]]) / CHORD_MM


def _polar(foil: FoilParams, re: float) -> np.ndarray:
    a = nf.get_aero_from_coordinates(_coords(foil), alpha=ALPHA, Re=re, model_size="xlarge",
                                     xtr_upper=TRIP, xtr_lower=TRIP)
    return np.stack([np.asarray(a[k], dtype=np.float32) for k in ("CL", "CD", "CM", "analysis_confidence")])


def main() -> None:
    out = Path("src/fingen/data/sections_v0.npz")
    for arg in sys.argv[1:]:
        if arg.startswith("--out="):
            out = Path(arg.split("=", 1)[1])
    data: dict[str, np.ndarray] = {"alpha": ALPHA.astype(np.float32), "reynolds": REYNOLDS.astype(np.float32),
                                   "tc": TC.astype(np.float32), "tc_cambered": TC_CAMBERED.astype(np.float32),
                                   "camber": CAMBER.astype(np.float32)}
    for fam in (FoilFamily.SYMMETRIC, FoilFamily.FLAT_INSIDE):
        block = np.stack([np.stack([_polar(FoilParams(family=fam, thickness_ratio=float(t), te_thickness=TE_MM), float(re))
                                    for re in REYNOLDS]) for t in TC])          # [tc, re, 4, alpha]
        for i, key in enumerate(("cl", "cd", "cm", "conf")):
            data[f"{fam.value}_{key}"] = block[:, :, i, :]
    block = np.stack([np.stack([np.stack([
        _polar(FoilParams(family=FoilFamily.CAMBERED if m > 0 else FoilFamily.SYMMETRIC, thickness_ratio=float(t),
                          camber_ratio=float(m), camber_position=CAMBER_POSITION, te_thickness=TE_MM), float(re))
        for re in REYNOLDS]) for m in CAMBER]) for t in TC_CAMBERED])           # [tc, camber, re, 4, alpha]
    for i, key in enumerate(("cl", "cd", "cm", "conf")):
        data[f"cambered_{key}"] = block[:, :, :, i, :]
    meta = {"version": 0, "source": "neuralfoil", "model_size": "xlarge",
            "neuralfoil_version": __import__("importlib.metadata").metadata.version("neuralfoil"),
            "boundary_layer": f"tripped at {TRIP:g} chord, both faces", "te_thickness_over_chord": TE_MM / CHORD_MM,
            "camber_position": CAMBER_POSITION, "built": datetime.date.today().isoformat(),
            "status": "provisional in the stall region; see scripts/build_section_table.py"}
    data["meta"] = np.array(json.dumps(meta))
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, **data)
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} kB): "
          f"{len(TC)} thicknesses x {len(REYNOLDS)} Re x {len(ALPHA)} angles for symmetric and flat_inside, "
          f"{len(TC_CAMBERED)} x {len(CAMBER)} cambers for cambered")
    k = int(np.argmin(np.abs(TC - 0.09))); r = int(np.argmin(np.abs(REYNOLDS - 4e5)))
    for fam in ("symmetric", "flat_inside"):
        cl, cd = data[f"{fam}_cl"][k, r], data[f"{fam}_cd"][k, r]
        print(f"  {fam} t/c {TC[k]:.2f} Re {REYNOLDS[r]:.0e}: cl(0) {np.interp(0, ALPHA, cl):+.3f}  cl(8) {np.interp(8, ALPHA, cl):.3f}  "
              f"cd(0) {np.interp(0, ALPHA, cd):.4f}  cd(-3.5) {np.interp(-3.5, ALPHA, cd):.4f}  min confidence {data[f'{fam}_conf'][k, r].min():.2f}")


if __name__ == "__main__":
    main()
