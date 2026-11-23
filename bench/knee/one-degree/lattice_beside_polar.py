"""A blade's 3-D polar beside the lattice on table v1 run THROUGH its sections' ends (perfect mirror).
usage: lattice_beside_polar.py <fin.json> <speed> <results.json> <variant> [t/c override]"""
import dataclasses, json, sys
import numpy as np
from fingen import bladehydro, lattice
from fingen.optimize import fin_from_dict

raw = json.load(open(sys.argv[1])); fin = fin_from_dict(raw.get("fin", raw)); speed = float(sys.argv[2])
if len(sys.argv) > 5:
    fin = dataclasses.replace(fin, foil=dataclasses.replace(fin.foil, thickness_ratio=float(sys.argv[5])))
data = json.load(open(sys.argv[3]))
rows = data["variants"][sys.argv[4]]["rows"] if "variants" in data else data
rows = sorted(rows, key=lambda r: r["alpha"])
blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
pol = lattice.strip_sections(fin, blade, speed, "v1")
lim = np.array([p.cl_limit for p in pol])
a = np.array([r["alpha"] for r in rows]); cl = np.array([r["cl"] for r in rows])
m = (a >= 0) & (a <= 4.01)
if m.sum() < 2: m = (a >= 0) & (a <= 6.01)
s, c0 = np.polyfit(a[m], cl[m], 1)
lat = {}
for x in (2.0, 4.0):
    lat[x] = lattice.solve_viscous([blade], {"blade": pol}, speed, x, mirror_strength=1.0).loads["blade"].cl
sl = (lat[4.0] - lat[2.0]) / 2.0; l0 = lat[2.0] - 2.0 * sl
print(f"t/c {fin.foil.thickness_ratio:.3f} {fin.foil.family.value}  limit per strip {lim.min():.2f}..{lim.max():.2f}")
print(" alpha | CFD cl, vs its line | lattice cl, vs its line | lattice/CFD | top strip share, a_eff | conv")
for r in rows:
    x = r["alpha"]
    if x <= 0: continue
    sol = lattice.solve_viscous([blade], {"blade": pol}, speed, x, mirror_strength=1.0); ld = sol.loads["blade"]
    k = int(np.argmax(ld.cl_local / lim))
    print(f" {x:5.1f} | {r['cl']:.4f} {100*(r['cl']/(s*x+c0)-1):+6.1f} % | {ld.cl:.4f} {100*(ld.cl/(sl*x+l0)-1):+6.1f} % | {100*(ld.cl/r['cl']-1):+5.1f} % | {ld.cl_local[k]/lim[k]:.2f} {ld.alpha_eff_deg[k]:5.1f} | {sol.converged}")
