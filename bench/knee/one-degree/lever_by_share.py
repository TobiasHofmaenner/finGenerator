"""The tip-width lever by the lattice, read at several shares of the section's limit.

  uv run python bench/knee/one-degree/lever_by_share.py

For the gen-3 side fin (tip 0.60 of the base) and its narrow-tipped twin (tip 0.35): the blade angle
at which the first strip reaches a share of its section's limit, and the difference between the two.
`bladehydro.knee` marks the onset at KNEE_FRACTION; the meshes' strips let go at 0.8 to 0.9.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import strip_loads as sl  # noqa: E402

from fingen import bladehydro, lattice  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
FINS = {"gen3 side": ROOT / "bench/design-points/cfd/fin-sliders.json",
        "tip 0.35": Path(__file__).parent / "fin-gen3-tip035.json"}
ANGLES = np.arange(2.0, 20.01, 0.5)


def shares(fin_path: Path, speed: float = 8.5):
    """Strip positions and, per blade angle, each strip's lift over its section's limit."""
    fin = sl._fin(str(fin_path))
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pol = lattice.strip_sections(fin, blade, speed, "v1")
    lim = np.array([p.cl_limit for p in pol])
    cl = np.array([lattice.solve_viscous([blade], {"blade": pol}, speed, a,
                                         mirror_strength=1.0).loads["blade"].cl_local
                   for a in ANGLES])
    return blade.z_mid / blade.depth, cl / lim


def first(share: np.ndarray, s: float) -> tuple[float, int]:
    """Lowest blade angle at which a strip reaches the share s, and which strip."""
    best = (99.0, -1)
    for k in range(share.shape[1]):
        y = share[:, k]
        i = int(np.argmax(y >= s))
        if y[i] < s or i == 0:
            continue
        a = ANGLES[i - 1] + (s - y[i - 1]) / (y[i] - y[i - 1]) * (ANGLES[i] - ANGLES[i - 1])
        if a < best[0]:
            best = (a, k)
    return best


if __name__ == "__main__":
    data = {n: shares(p) for n, p in FINS.items()}
    print("share   gen-3 side deg (strip z/depth)   tip 0.35 deg (strip z/depth)   lever deg")
    for s in (bladehydro.KNEE_FRACTION, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90):
        (ag, kg), (at, kt) = first(data["gen3 side"][1], s), first(data["tip 0.35"][1], s)
        zg, zt = data["gen3 side"][0][kg], data["tip 0.35"][0][kt]
        print(f"{s:5.3f}   {ag:6.2f} ({zg:.2f})                    {at:6.2f} ({zt:.2f})"
              f"                  {ag - at:5.2f}")
