"""How much more of a strip's lift sits at its nose on the blade than on the same strip in two
dimensions ([Pol96]'s induced camber, read off the lattice).

    nose_loading.py <fin.json> [nx]

Inviscid lattice with `nx` chordwise panels on the perfect mirror: the first panel's share of each
strip's circulation, over the same share on a two-dimensional flat plate with `nx` panels, for
the planform alone (no camber). The ratio does not depend on `nx` (8 and 16 agree to 0.01) nor
on the angle.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

from fingen import bladehydro, lattice
from fingen.optimize import fin_from_dict


def nose_ratio(fin, nx: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """(strip stations as a share of the depth, nose loading over the two-dimensional value)."""
    b = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=nx)
    beta = math.radians(4.0)
    d = np.array([math.cos(beta), math.sin(beta), 0.0])

    def influence(points: np.ndarray) -> np.ndarray:
        p = points[:, None, :]
        v = lattice._horseshoe(p, b.A[None], b.B[None], b.ATE[None], b.BTE[None], d)
        m = lattice._MIRROR
        return v + lattice._horseshoe(p, (b.B * m)[None], (b.A * m)[None],
                                      (b.BTE * m)[None], (b.ATE * m)[None], d)

    aic = (influence(b.CP) * b.normal[:, None, :]).sum(-1)
    gamma = np.linalg.solve(aic, -(b.normal @ d))      # the planform alone: no camber term
    # two dimensions: nx lumped vortices at the panels' quarter points, collocation at three
    # quarters
    xv, xc = (np.arange(nx) + 0.25) / nx, (np.arange(nx) + 0.75) / nx
    g2 = np.linalg.solve(1.0 / (2.0 * np.pi * (xc[:, None] - xv[None, :])), np.ones(nx))
    share = []
    for k in range(len(b.z_mid)):
        idx = np.where(b.strip == k)[0]
        g = gamma[idx[np.argsort(b.xq_local[idx])]]           # fore to aft
        share.append(g[0] / g.sum())
    return b.z_mid / b.depth, np.array(share) / (g2[0] / g2.sum())


if __name__ == "__main__":
    raw = json.loads(Path(sys.argv[1]).read_text())
    z, r = nose_ratio(fin_from_dict(raw.get("fin", raw)),
                      int(sys.argv[2]) if len(sys.argv) > 2 else 8)
    print("strip z/depth          " + " ".join(f"{x:6.2f}" for x in z))
    print("nose loading over 2-D  " + " ".join(f"{x:6.2f}" for x in r))
