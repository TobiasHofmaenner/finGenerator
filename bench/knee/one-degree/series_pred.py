"""Thickness series of symmetric foils on the gen-2 side planform: where each reading puts the blade's knee."""
import dataclasses
import json
from pathlib import Path

import numpy as np
from fingen import bladehydro, lattice
from fingen.optimize import fin_from_dict

base = fin_from_dict(json.loads((Path(__file__).parent / "fin-gen2-planform-sym-tc050.json").read_text())["fin"])
SPEED = 8.5
def strips(tc):
    fin = dataclasses.replace(base, foil=dataclasses.replace(base.foil, thickness_ratio=tc))
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pol = lattice.strip_sections(fin, blade, SPEED, "v1")
    lo, hi = (lattice.solve_viscous([blade], {"blade": pol}, SPEED, a, mirror_strength=1.0).loads["blade"] for a in (2.0, 6.0))
    return fin, blade, pol, lo, hi
_, _, pol09, _, _ = strips(0.09)
lim09 = np.array([p.cl_limit for p in pol09])
print("limit of the t/c 0.09 section per strip", np.round(lim09, 2))
for tc in (0.046, 0.05, 0.055, 0.06, 0.066, 0.07, 0.075, 0.08, 0.09, 0.10):
    fin, blade, pol, lo, hi = strips(tc)
    lim = np.array([p.cl_limit for p in pol]); end = np.array([p.attached_deg[1] for p in pol])
    rate = (hi.cl_local - lo.cl_local) / 4.0
    def reach(target):
        r = 2.0 + (target - lo.cl_local) / rate; k = int(np.argmin(r)); return r[k], k
    h1, k1 = reach(bladehydro.KNEE_FRACTION * lim); h2, k2 = reach(lim); h3, k3 = reach(np.minimum(lim, bladehydro.KNEE_FRACTION * lim09))
    slope = (hi.cl - lo.cl) / 4.0
    # the lattice's own polar run through the ends: 5 % below its line
    own = None
    for a in np.arange(4.0, 18.01, 0.25):
        ld = lattice.solve_viscous([blade], {"blade": pol}, SPEED, float(a), mirror_strength=1.0).loads["blade"]
        if ld.cl < 0.95 * (lo.cl + slope * (a - 2.0)): own = a; break
    print(f"t/c {tc:.3f}: limit {lim.min():.2f}..{lim.max():.2f}, end {end.min():.1f}..{end.max():.1f}° | common share of its own limit {h1:4.1f}° (C_L {lo.cl + slope*(h1-2):.2f}) | "
          f"share one {h2:4.1f}° (C_L {lo.cl + slope*(h2-2):.2f}) | smaller of its end and 0.606 of the t/c 0.09 limit {h3:4.1f}° | lattice's own polar 5 % below at {own}")
