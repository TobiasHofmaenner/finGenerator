"""Spanwise loading of the rectangular wing from each row's saved surface pressure.

    uv run python bench/js37-wing/wing_strips.py <variant dir> <chord mm> <semi-span mm> <speed m/s> [strips]

Reads every row's `a+NN.N/postProcessing/surfaces/*/fin.vtk` (the fin patch's points and faces, the
kinematic pressure at the points, at the row's last iteration: one instant of a swinging row) and
prints, per span strip, the section lift from the pressure alone on the strip's own area
(the force across the stream, the stream being turned by the row's angle in the case's x-y plane)
and the lowest pressure coefficient. The last column is the whole half wing on chord x semi-span.
Friction is not in it. The case sinks the wing 2 mm below its symmetry plane; z is from that plane.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "knee" / "one-degree"))
from strip_loads import read_vtk  # noqa: E402


def main() -> None:
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    run = Path(sys.argv[1])
    chord, span, speed = float(sys.argv[2]) * 1e-3, float(sys.argv[3]) * 1e-3, float(sys.argv[4])
    nb = int(sys.argv[5]) if len(sys.argv) > 5 else 12
    q = 0.5 * speed**2
    dz = span / nb
    mid = (np.arange(nb) + 0.5) / nb
    print("z/semi-span    " + " ".join(f"{m:6.3f}" for m in mid) + "    wing")
    for case in sorted(run.glob("a[+-]*"), key=lambda p: float(p.name[1:])):
        found = sorted(case.glob("postProcessing/surfaces/*/fin.vtk"),
                       key=lambda p: float(p.parent.name))
        if not found:
            continue
        alpha = math.radians(float(case.name[1:]))
        pts, faces, p = read_vtk(found[-1])
        lift = np.zeros(nb)
        cpmin = np.zeros(nb)
        for face in faces:
            v = pts[face]
            area = np.zeros(3)
            for m in range(1, len(face) - 1):
                area += 0.5 * np.cross(v[m] - v[0], v[m + 1] - v[0])
            pm = p[face].mean()
            # outward normal times pressure pushes the wall inward: force = -p n dA
            fx, fy = -pm * area[0], -pm * area[1]
            z = v[:, 2].mean()
            if not 0.0 <= z < span:
                continue
            b = min(int(z / dz), nb - 1)
            lift[b] += fy * math.cos(alpha) - fx * math.sin(alpha)
            cpmin[b] = min(cpmin[b], pm / q)
        # the patch's normals may point either way: the wing at a positive angle lifts toward +y
        cl = lift / (q * chord * dz)
        if cl.sum() < 0 and alpha > 0:
            cl = -cl
        print(f"{case.name} cl      " + " ".join(f"{x:6.3f}" for x in cl) + f"  {cl.mean():6.3f}")
        print(f"{case.name} cp min  " + " ".join(f"{x:6.2f}" for x in cpmin))


if __name__ == "__main__":
    main()
