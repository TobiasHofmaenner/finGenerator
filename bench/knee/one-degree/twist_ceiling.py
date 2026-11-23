"""What-if: what a load-dependent twist could add to the force at the knee.

    twist_ceiling.py <fin.json> <speed>

The strip knee is reached when ONE strip is at KNEE_FRACTION of its section's limit; the others
still have room. First the gain from a tip that twists off by 2, 4 and 8 deg under the load
(`washout_gain`). Then the ceiling: the twist that brings every strip to that share at the same
angle, found with the lattice (table v1, board mirror; the root strip and the two tip strips
are left free), and the force at that point against the rigid knee's (`ceiling`). Whether a
structure can produce such a twist, and what the flow does on a blade twisted so, is not
looked at here.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

from fingen import bladehydro, lattice
from fingen.optimize import fin_from_dict


def ceiling(fin, speed: float, free_tip: int = 2, passes: int = 40) -> dict:
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pol = {"blade": lattice.strip_sections(fin, blade, speed, "v1")}
    lim = np.array([p.cl_limit for p in pol["blade"]])
    qa = bladehydro._q_area(fin, speed)
    a_rigid, cl_rigid = bladehydro.knee(fin, speed, "v1")
    n = len(lim)
    use = (np.arange(n) < n - free_tip) & (np.arange(n) > 0)

    def solve(alpha: float, twist_deg: np.ndarray):
        t = np.radians(twist_deg)[blade.strip]
        nrm = blade.normal.copy()
        nrm[:, 0] = blade.normal[:, 0] * np.cos(t) + blade.normal[:, 1] * np.sin(t)
        nrm[:, 1] = -blade.normal[:, 0] * np.sin(t) + blade.normal[:, 1] * np.cos(t)
        b = dataclasses.replace(blade, normal=nrm)
        return lattice.solve_viscous([b], pol, speed, alpha,
                                     mirror_strength=bladehydro.BOARD_MIRROR_STRENGTH).loads["blade"]

    target = bladehydro.KNEE_FRACTION * lim
    twist = np.zeros(n)
    alpha = a_rigid
    ref = 1                                            # the second strip keeps the blade's angle
    for _ in range(passes):
        ld = solve(alpha, twist)
        err = (target - ld.cl_local) / 0.08          # degrees, at roughly 0.08 of lift per degree
        twist[use] += 0.5 * err[use]
        twist[0] = 0.0                                 # the root strip is left as it is
        twist[~use] = twist[use][-1]                   # the tip strips follow the last one set
        twist -= twist[ref]
        twist[0] = 0.0
        alpha += 0.5 * err[ref]
    ld = solve(alpha, twist)
    return {"rigid": (a_rigid, cl_rigid * qa), "even": (alpha, ld.cl * qa), "twist": twist,
            "z": blade.z_mid / blade.depth, "share": ld.cl_local / lim}


def washout_gain(fin, speed: float, tip_deg: float) -> tuple[float, float, float, float]:
    """(rigid knee deg, N, knee deg, N) with a twist that grows with the blade's force, zero at
    the root and `tip_deg` off at the tip at the rigid knee's force, as (z/depth) squared."""
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pol = {"blade": lattice.strip_sections(fin, blade, speed, "v1")}
    lim = np.array([p.cl_limit for p in pol["blade"]])
    qa = bladehydro._q_area(fin, speed)
    zf = blade.z_mid / blade.depth

    def solve(alpha: float, twist_deg: np.ndarray):
        t = np.radians(twist_deg)[blade.strip]
        nrm = blade.normal.copy()
        nrm[:, 0] = blade.normal[:, 0] * np.cos(t) + blade.normal[:, 1] * np.sin(t)
        nrm[:, 1] = -blade.normal[:, 0] * np.sin(t) + blade.normal[:, 1] * np.cos(t)
        b = dataclasses.replace(blade, normal=nrm)
        return lattice.solve_viscous([b], pol, speed, alpha,
                                     mirror_strength=bladehydro.BOARD_MIRROR_STRENGTH).loads["blade"]

    def knee(lo, hi) -> tuple[float, float]:
        rate = (hi.cl_local - lo.cl_local) / 4.0
        reach = np.where(rate > 1e-6, 2.0 + (bladehydro.KNEE_FRACTION * lim - lo.cl_local)
                         / np.maximum(rate, 1e-6), np.inf)
        a = float(reach.min())
        return a, (lo.cl + (hi.cl - lo.cl) / 4.0 * (a - 2.0)) * qa

    rigid = [solve(a, np.zeros(len(lim))) for a in (2.0, 6.0)]
    a0, f0 = knee(*rigid)
    flexed = []
    for a, r in zip((2.0, 6.0), rigid, strict=True):
        force, ld = r.cl * qa, r
        for _ in range(3):
            ld = solve(a, -tip_deg * zf ** 2 * force / f0)
            force = ld.cl * qa
        flexed.append(ld)
    return (a0, f0, *knee(*flexed))


if __name__ == "__main__":
    raw = json.loads(Path(sys.argv[1]).read_text())
    for tip in (2.0, 4.0, 8.0):
        a0, f0, a1, f1 = washout_gain(fin_from_dict(raw.get("fin", raw)), float(sys.argv[2]), tip)
        print(f"tip twisting off {tip:.0f} deg at the rigid knee's force ({f0:.0f} N): "
              f"knee {a1:.1f} deg, {f1:.0f} N ({100 * (f1 / f0 - 1):+.1f} %)")
    out = ceiling(fin_from_dict(raw.get("fin", raw)), float(sys.argv[2]))
    (ar, fr), (ae, fe) = out["rigid"], out["even"]
    print(f"rigid knee {ar:.1f} deg, {fr:.0f} N;  every strip at the share together: {ae:.1f} deg, "
          f"{fe:.0f} N ({100 * (fe / fr - 1):+.0f} %)")
    print("strip z/depth      " + " ".join(f"{x:6.2f}" for x in out["z"]))
    print("twist needed, deg  " + " ".join(f"{x:+6.1f}" for x in out["twist"]))
    print("share of the limit " + " ".join(f"{x:6.2f}" for x in out["share"]))
