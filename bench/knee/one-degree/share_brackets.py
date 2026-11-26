"""Between which shares of its section's limit a fin's strips let go, bracketed by its own rows.

  uv run python bench/knee/one-degree/share_brackets.py <fin.json> <speed m/s> <run> \
      [strip-loads.json]

For the last row with every strip within 5 % of the lattice (normalised at the first row) and the
first row with one strip more than 5 % short, the lattice's share of the section limit at the most
loaded strip and at each strip that is short in the second row. No interpolation between rows: the
fin lets go somewhere between the two, so each strip's share at let-go lies between its two values.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import strip_loads as sl  # noqa: E402

from fingen import bladehydro, lattice  # noqa: E402


def brackets(fin_path: str, speed: float, run: str, src: Path) -> None:
    fin = sl._fin(fin_path)
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pol = lattice.strip_sections(fin, blade, speed, "v1")
    lim = np.array([p.cl_limit for p in pol])
    q = 0.5 * speed ** 2
    rows = json.loads(src.read_text())[run]["rows"]
    z = blade.z_mid / blade.depth
    got = []
    for key in sorted(rows, key=float):
        a = float(key)
        if a <= 0:
            continue
        cfd = np.array(rows[key]["strip_force_kinematic"]) / (q * blade.chord * blade.dz)
        lat = lattice.solve_viscous([blade], {"blade": pol}, speed, a,
                                    mirror_strength=1.0).loads["blade"].cl_local.copy()
        got.append((a, cfd / lat, lat / lim))
    ref = got[0][1]
    inner = z < 0.95  # the two tip strips ride the tip vortex and read above the lattice
    held = None
    for a, r, share in got:
        ratio = r / ref
        short = (ratio < 0.95) & inner
        if not short.any():
            held = (a, ratio, share)
            continue
        if held is None:
            print(f"{run}: short already at its second row ({a:g} deg)")
            return
        k = int(np.argmax(np.where(inner, held[2], -1.0)))
        print(f"{run}: every strip within 5 % at {held[0]:g} deg, short at {a:g} deg")
        print(f"  most loaded strip z/depth {z[k]:.2f}: share {held[2][k]:.3f} held, "
              f"{share[k]:.3f} at the next row (CFD over lattice there {ratio[k]:.2f})")
        for j in np.flatnonzero(short):
            print(f"  strip z/depth {z[j]:.2f}: share {held[2][j]:.3f} held, {share[j]:.3f} short"
                  f" (CFD over lattice {ratio[j]:.2f})")
        return
    print(f"{run}: no strip short up to {got[-1][0]:g} deg")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    brackets(sys.argv[1], float(sys.argv[2]), sys.argv[3],
             Path(sys.argv[4]) if len(sys.argv) > 4 else Path(__file__).parent / "strip-loads.json")
