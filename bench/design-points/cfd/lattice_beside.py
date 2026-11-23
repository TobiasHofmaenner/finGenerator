"""The design-point fins in CFD beside the lattice (perfect mirror, as the CFD's symmetry plane): lift, drag in N."""
import json
from pathlib import Path
import numpy as np
from fingen import bladehydro as bh, lattice
from fingen.optimize import fin_from_dict
from fingen.outline import metrics

D = Path("bench/design-points/cfd"); Q = 0.5 * 1025.0 * 8.5**2
for fin_file, runs in (("fin-sliders", ("sliders-L6", "sliders-L5")), ("fin-sliders-tip035", ("tip035-L5",)), ("fin-offsets", ("offsets-L6", "offsets-L5"))):
    fin = fin_from_dict(json.loads((D / f"{fin_file}.json").read_text())["fin"])
    area = metrics(fin.outline).area * 1e-6
    blade = lattice.blade_from_fin("blade", fin, nz=bh.NZ, nx=bh.NX)
    pol = {"blade": lattice.strip_sections(fin, blade, 8.5, "v1")}
    print(f"== {fin_file}: {1e6 * area:.0f} mm2")
    for run in runs:
        rows = next(iter(json.loads((D / f"{run}.json").read_text())["variants"].values()))["rows"]
        print(f"  {run}")
        for r in sorted(rows, key=lambda r: r["alpha"]):
            ld = lattice.solve_viscous([blade], pol, 8.5, r["alpha"], mirror_strength=1.0).loads["blade"]
            print(f"    {r['alpha']:+5.1f}  CL cfd {r['cl']:+.3f} lattice {ld.cl:+.3f}   drag cfd {r['cd'] * Q * area:5.2f} N lattice {ld.cd * Q * area:5.2f} N  ratio {ld.cd / r['cd']:.2f}  it {int(r['iterations'])}")
