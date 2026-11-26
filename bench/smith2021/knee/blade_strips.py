"""Spanwise loading of a ceiling-hung trapezoid from zarruk_knee's foilSurf surface (kinematic p at points).

python3 -I blade_strips.py <run dir> <root chord m> <tip chord m> <span m> <speed m/s> [bins]
"""
import sys
from pathlib import Path

import numpy as np


def read(path):
    toks = path.read_text().split("\n")
    i = next(k for k, l in enumerate(toks) if l.startswith("POINTS"))
    n = int(toks[i].split()[1])
    j = next(k for k, l in enumerate(toks) if l.startswith("POLYGONS"))
    pts = np.array(" ".join(toks[i + 1:j]).split(), dtype=float).reshape(n, 3)
    npoly = int(toks[j].split()[1])
    k = next(m for m, l in enumerate(toks) if l.startswith("POINT_DATA"))
    flat = np.array(" ".join(toks[j + 1:k]).split(), dtype=int)
    polys, m = [], 0
    for _ in range(npoly):
        polys.append(flat[m + 1:m + 1 + flat[m]]); m += 1 + flat[m]
    f = next(m for m, l in enumerate(toks) if m > k and l.startswith("p "))
    p = np.array(" ".join(toks[f + 1:]).split()[:n], dtype=float)
    return pts, polys, p


def main():
    run = Path(sys.argv[1]); root, tip, span, speed = map(float, sys.argv[2:6])
    nb = int(sys.argv[6]) if len(sys.argv) > 6 else 10
    q = 0.5 * speed**2
    edges = np.linspace(0.0, -span, nb + 1)
    mid = 0.5 * (edges[:-1] + edges[1:])
    chord = root + (root - tip) / span * mid
    print("z/span        " + " ".join(f"{-m / span:6.2f}" for m in mid) + "   total CL")
    for case in sorted(run.glob("a+*")):
        d = case / "postProcessing/foilSurf"
        if not d.exists():
            continue
        t = sorted(d.iterdir(), key=lambda x: float(x.name))[-1]
        pts, polys, p = read(t / "foil.vtk")
        fy = np.zeros(nb); cpmin = np.zeros(nb); tot = 0.0
        for poly in polys:
            v = pts[poly]; c = v.mean(axis=0); pm = p[poly].mean()
            a = np.zeros(3)
            for m in range(1, len(poly) - 1):
                a += 0.5 * np.cross(v[m] - v[0], v[m + 1] - v[0])
            f = -pm * a[1]
            tot += f
            b = int(np.clip((c[2] - 0.0) / (-span) * nb, 0, nb - 1)) if c[2] <= 0 else -1
            if b >= 0:
                fy[b] += f
                cpmin[b] = min(cpmin[b], pm / q)
        dz = span / nb
        cl = fy / (q * chord * dz)
        sign = np.sign(tot) or 1.0
        print(f"{case.name} cl    " + " ".join(f"{sign * x:6.3f}" for x in cl)
              + f"   {sign * tot / (q * span * 0.5 * (root + tip)):.4f}")
        print(f"{case.name} cpmin " + " ".join(f"{x:6.2f}" for x in cpmin))


main()
