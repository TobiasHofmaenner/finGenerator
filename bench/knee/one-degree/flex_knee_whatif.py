"""What-if, not a result: how far the strip knee moves if each strip takes the incidence
change the flex model gives it under the blade's own load (`flex.flex_report(...).twist_deg`:
rake coupling plus torsion; negative = the tip twists off).

    flex_knee_whatif.py <fin.json> <speed> [material]

The rigid knee is `bladehydro.knee` (table v1, board mirror). The flexed one turns each strip's
panels by its incidence change at the force the blade makes at 2 and at 6 deg (three passes
each) and reads the knee off the two solves as before. Nothing here has been checked against a
simulation of a flexed blade; the twist itself has only a sign check ([Zar14]).
"""

from __future__ import annotations

import dataclasses
import json
import math
import sys
from pathlib import Path

import numpy as np

from fingen import bladehydro, flex, lattice
from fingen.optimize import fin_from_dict


def knees(fin, speed: float, material: str = "ppa-cf") -> dict:
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pol = {"blade": lattice.strip_sections(fin, blade, speed, "v1")}
    lim = np.array([p.cl_limit for p in pol["blade"]])
    qa = bladehydro._q_area(fin, speed)

    def solve(alpha: float, twist_deg: np.ndarray | None):
        b = blade
        if twist_deg is not None:
            t = np.radians(twist_deg)[blade.strip]
            n = blade.normal.copy()
            n[:, 0] = blade.normal[:, 0] * np.cos(t) + blade.normal[:, 1] * np.sin(t)
            n[:, 1] = -blade.normal[:, 0] * np.sin(t) + blade.normal[:, 1] * np.cos(t)
            b = dataclasses.replace(blade, normal=n)
        return lattice.solve_viscous([b], pol, speed, alpha,
                                     mirror_strength=bladehydro.BOARD_MIRROR_STRENGTH).loads["blade"]

    def twist_at(force: float) -> np.ndarray:
        r = flex.flex_report(fin, force, speed, material=material)
        return np.interp(blade.z_mid * 1e3, np.asarray(r.z_mm), np.asarray(r.twist_deg))

    def knee(lo, hi) -> tuple[float, float, int]:
        rate = (hi.cl_local - lo.cl_local) / 4.0
        reach = np.where(rate > 1e-6, 2.0 + (bladehydro.KNEE_FRACTION * lim - lo.cl_local)
                         / np.maximum(rate, 1e-6), np.inf)
        k = int(np.argmin(reach))
        a = float(reach[k])
        return a, lo.cl + (hi.cl - lo.cl) / 4.0 * (a - 2.0), k

    rigid = [solve(a, None) for a in (2.0, 6.0)]
    flexed = []
    for a, r in zip((2.0, 6.0), rigid, strict=True):
        force, ld = r.cl * qa, r
        for _ in range(3):
            ld = solve(a, twist_at(force))
            force = ld.cl * qa
        flexed.append(ld)
    ar, clr, kr = knee(*rigid)
    af, clf, kf = knee(*flexed)
    tw = twist_at(clf * qa)
    return {"rigid": (ar, clr * qa, blade.z_mid[kr] / blade.depth),
            "flexed": (af, clf * qa, blade.z_mid[kf] / blade.depth),
            "twist_at_knee_deg": tw, "z": blade.z_mid / blade.depth}


if __name__ == "__main__":
    raw = json.loads(Path(sys.argv[1]).read_text())
    fin = fin_from_dict(raw.get("fin", raw))
    out = knees(fin, float(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "ppa-cf")
    for key in ("rigid", "flexed"):
        a, f, z = out[key]
        print(f"{key:7s} knee at {a:5.2f} deg, {f:5.0f} N, first strip at z/depth {z:.2f}")
    print("incidence change per strip at the flexed knee's force, deg (root to tip): "
          + " ".join(f"{math.degrees(math.radians(x)):+.2f}" for x in out["twist_at_knee_deg"]))
