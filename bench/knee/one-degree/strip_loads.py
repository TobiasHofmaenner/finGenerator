"""Strip loads of 3-D polar rows from their saved surface pressure, beside the lattice's strips.

    strip_loads.py extract <fin.json> <variant dir> <run name> <strip-loads.json>
    strip_loads.py table <fin.json> <speed> <run name> <strip-loads.json>

`extract` reads every row's `a+NN.N/postProcessing/surfaces/*/fin.vtk` (legacy ASCII VTK: the fin
patch's points and faces and the kinematic pressure at the points, at the row's last iteration, so
a swinging row is one instant of it) and adds to the JSON, per angle and per lattice strip (the
ten strips of `bladehydro`, by span station): the pressure force across the chord plane over
(q c dz), the lowest pressure coefficient, and the median face size at the nose (first 1 % of
chord). Friction is not in it. The fin's tip is rounded off in the mesh, so the last strip is empty.

`table` prints, from the JSON: each strip's CFD lift over the lattice's (table v1, perfect mirror,
run through its sections' ends), normalised by the same ratio at the lowest angle; and per strip
the first angle at which that falls 5 % short, with the lattice's strip lift there, its share of
the section's limit, the section incidence and the margin to the end of the attached range.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from fingen import bladehydro, lattice
from fingen.optimize import fin_from_dict


def read_vtk(path: Path) -> tuple[np.ndarray, list[np.ndarray], np.ndarray]:
    tok = path.read_text().split()
    i = tok.index("POINTS")
    n = int(tok[i + 1])
    pts = np.array(tok[i + 3:i + 3 + 3 * n], dtype=float).reshape(n, 3)
    i = tok.index("POLYGONS", i)
    m, size = int(tok[i + 1]), int(tok[i + 2])
    raw = np.array(tok[i + 3:i + 3 + size], dtype=int)
    faces, k = [], 0
    for _ in range(m):
        c = raw[k]
        faces.append(raw[k + 1:k + 1 + c])
        k += c + 1
    j = tok.index("POINT_DATA", i)
    while not (tok[j] == "p" and tok[j + 1] == "1"):
        j += 1
    return pts, faces, np.array(tok[j + 4:j + 4 + n], dtype=float)


def _fin(path: str):
    raw = json.loads(Path(path).read_text())
    return fin_from_dict(raw.get("fin", raw))


def extract(fin_path: str, base: Path, run: str, out: Path) -> None:
    fin = _fin(fin_path)
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    z, x_le, chord = lattice.planform(fin.outline)
    edges = np.concatenate([[0.0], np.cumsum(blade.dz)])
    data = json.loads(out.read_text()) if out.exists() else {}
    rows = {}
    for d in sorted(base.glob("a+*")):
        f = next(iter(sorted(d.glob("postProcessing/surfaces/*/fin.vtk"))), None)
        if f is None:
            continue
        pts, faces, p = read_vtk(f)
        cen = np.empty((len(faces), 3))
        av = np.empty((len(faces), 3))
        pf = np.empty(len(faces))
        for k, face in enumerate(faces):
            g = pts[face]
            c = g.mean(axis=0)
            a = np.zeros(3)
            for t in range(len(face)):
                a += 0.5 * np.cross(g[t] - c, g[(t + 1) % len(face)] - c)
            cen[k], av[k], pf[k] = c, a, p[face].mean()
        fy = pf * av[:, 1]
        sgn = 1.0 if fy.sum() > 0 else -1.0
        idx = np.searchsorted(edges, cen[:, 2]) - 1
        x0 = pts[:, 0].min() * 1e3 - x_le.min()
        s = (cen[:, 0] * 1e3 - x0 - np.interp(cen[:, 2] * 1e3, z, x_le)) \
            / np.interp(cen[:, 2] * 1e3, z, chord)
        size = np.sqrt(np.linalg.norm(av, axis=1)) * 1e3
        force, cpmin, nose = [], [], []
        for k in range(len(blade.dz)):
            m = idx == k
            force.append(float(sgn * fy[m].sum()))                 # m^4/s^2, kinematic
            cpmin.append(float(pf[m].min()) if m.any() else None)  # m^2/s^2, kinematic
            mm = m & (s < 0.01)
            nose.append(float(np.median(size[mm])) if mm.any() else None)
        rows[d.name[1:]] = {"iteration": int(f.parent.name), "faces": len(faces),
                            "strip_force_kinematic": force, "lowest_p_kinematic": cpmin,
                            "nose_face_mm": nose}
    data[run] = {"rows": rows}
    out.write_text(json.dumps(data, indent=1))
    print(f"{run}: {len(rows)} rows")


def table(fin_path: str, speed: float, run: str, src: Path) -> None:
    fin = _fin(fin_path)
    blade = lattice.blade_from_fin("blade", fin, nz=bladehydro.NZ, nx=bladehydro.NX)
    pol = lattice.strip_sections(fin, blade, speed, "v1")
    lim = np.array([p.cl_limit for p in pol])
    end = np.array([p.attached_deg[1] if p.attached_deg else p.alpha_break_deg for p in pol])
    q = 0.5 * speed ** 2
    rows = json.loads(src.read_text())[run]["rows"]
    n = len(blade.dz)
    got = []
    for key in sorted(rows, key=float):
        a = float(key)
        if a <= 0:
            continue
        cfd = np.array(rows[key]["strip_force_kinematic"]) / (q * blade.chord * blade.dz)
        ld = lattice.solve_viscous([blade], {"blade": pol}, speed, a,
                                   mirror_strength=1.0).loads["blade"]
        got.append((a, cfd, ld.cl_local.copy(), ld.alpha_eff_deg.copy(),
                    [None if v is None else v / q for v in rows[key]["lowest_p_kinematic"]]))
    nose = rows[sorted(rows, key=float)[0]]["nose_face_mm"]
    radius = 1.1019 * fin.foil.thickness_ratio ** 2 * blade.chord * 1e3

    def row(label: str, vals, fmt: str = "{:6.2f}") -> None:
        print(f"{label:22s}" + " ".join(
            "     –" if v is None or not np.isfinite(v) else fmt.format(v) for v in vals))

    print(f"{run}: symmetric t/c {fin.foil.thickness_ratio}, {speed} m/s")
    row("strip z/depth", blade.z_mid / blade.depth)
    row("chord mm", blade.chord * 1e3, "{:6.1f}")
    row("faces per nose radius", [None if v is None else r / v
                                  for r, v in zip(radius, nose, strict=True)])
    row("section limit", lim)
    row("section end deg", end, "{:6.1f}")
    ref = got[0][1] / got[0][2]
    print(f"CFD strip lift over the lattice's, over the same at {got[0][0]:.0f} deg")
    for a, cfd, lat, _, _ in got:
        row(f"  {a:4.1f}", [(cfd[k] / lat[k]) / ref[k] if ref[k] > 0 else None for k in range(n)])
    print("lowest pressure coefficient")
    for a, _, _, _, cp in got:
        row(f"  {a:4.1f}", cp)
    hit: list[tuple | None] = []
    for k in range(n):
        prev, found = None, None
        for a, cfd, lat, ae, _ in got:
            r = (cfd[k] / lat[k]) / ref[k] if ref[k] > 0 else float("nan")
            if prev is not None and r < 0.95 <= prev[1]:
                t = (prev[1] - 0.95) / (prev[1] - r)
                found = (prev[0] + t * (a - prev[0]), prev[2] + t * (lat[k] - prev[2]),
                         prev[3] + t * (ae[k] - prev[3]))
                break
            prev = (a, r, lat[k], ae[k])
        hit.append(found)
    print("first 5 % short")
    row("  blade angle deg", [h[0] if h else None for h in hit], "{:6.1f}")
    row("  lattice strip lift", [h[1] if h else None for h in hit])
    row("  share of the limit", [h[1] / lim[k] if h else None for k, h in enumerate(hit)])
    row("  incidence deg", [h[2] if h else None for h in hit], "{:6.1f}")
    row("  margin to the end", [end[k] - h[2] if h else None for k, h in enumerate(hit)],
        "{:+6.1f}")


if __name__ == "__main__":
    if len(sys.argv) < 6:
        sys.exit(__doc__)
    if sys.argv[1] == "extract":
        extract(sys.argv[2], Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5]))
    else:
        table(sys.argv[2], float(sys.argv[3]), sys.argv[4], Path(sys.argv[5]))
