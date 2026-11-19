"""Board-edge experiment (gen-3 decision D9.5): how good a mirror is a real board?

    uv run python scripts/board_edge_probe.py [--md=out/board-edge-probe.md]

Every number we compute — tier-0, the lattice, all our CFD — assumes the board
is an infinite wall (CFD: a symmetry plane; tier-0: softened to an effective
aspect-ratio factor 1.7 instead of 2.0 by a literature guess). A real board is
a finite plate, and beyond its rail the water has a free surface. At surfing
speeds the Froude number on the fin chord is ~8, where a free surface does not
reflect pressure, it RELEASES it (potential = 0 on the surface).

Model, inviscid and linear, in the lattice of scripts/vlm_probe.py:
  * the fin's vortices get an ANTI-symmetric image in z = 0, which puts the
    pressure-release condition on the whole plane;
  * the wetted board footprint is a lattice of vortex rings in that plane
    (a doublet sheet: it leaves the potential zero outside itself) whose
    strengths are solved so no water crosses the footprint.
Limits that check the implementation: no footprint at all = a fin piercing a
free surface (lower bound); a very large footprint must return the
infinite-wall result.

One blade at a time, untoed and uncanted, on a rectangular footprint whose grid
has a line along the blade's root chord (the root vortex lies in the plane and
has to run along panel edges). Legs trail along the board axis.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import vlm_probe as vlm  # noqa: E402

from fingen.hydro import RHO_SEAWATER  # noqa: E402
from fingen.optimize import fin_from_dict  # noqa: E402

FLIP = np.array([1.0, 1.0, -1.0])
XHAT = np.array([1.0, 0.0, 0.0])


def _fill(lines: list[float], h: float) -> np.ndarray:
    """Grid containing every value of `lines`, each interval split into cells of about h."""
    lines = sorted(set(round(v, 9) for v in lines))
    out = [np.array([lines[0]])]
    for a, b in zip(lines, lines[1:]):
        n = max(int(round((b - a) / h)), 1)
        out.append(np.linspace(a, b, n + 1)[1:])
    return np.concatenate(out)


def _grow(start: float, end: float, h0: float, ratio: float) -> np.ndarray:
    """Points from start toward end (either direction), first step h0, growing by ratio."""
    sgn = 1.0 if end > start else -1.0
    pts, h, x = [], h0, start
    while abs(end - x) > 1.6 * h:
        x += sgn * h
        pts.append(x)
        h *= ratio
    pts.append(end)
    return np.array(pts)


def footprint(x0: float, x1: float, half_width: float, x_lines, y_fin: float, h: float,
              ratio: float = 1.3, core_margin: float = 0.03):
    """Vortex-ring grid on z = 0 (m): fine cells of size h in a core around the blade root
    (grid lines exactly on every x in x_lines and on y = y_fin), growing geometrically out to
    the footprint edges. The blade's root vortices lie IN this plane, so they must run along
    ring edges and start at ring corners, or the junction converges only at first order."""
    xa, xb = max(min(x_lines) - core_margin, x0), min(max(x_lines) + core_margin, x1)
    xc = _fill([xa, *[v for v in x_lines if xa < v < xb], xb], h)
    x = np.concatenate([_grow(xa, x0, h, ratio)[::-1], xc, _grow(xb, x1, h, ratio)]) if x0 < xa or x1 > xb else xc
    if x0 >= xa:
        x = np.concatenate([xc, _grow(xb, x1, h, ratio)]) if x1 > xb else xc
    elif x1 <= xb:
        x = np.concatenate([_grow(xa, x0, h, ratio)[::-1], xc])
    ya, yb = max(y_fin - core_margin, -half_width), min(y_fin + core_margin, half_width)
    yc = _fill([ya, y_fin, yb], h)
    parts = [yc]
    if -half_width < ya:
        parts.insert(0, _grow(ya, -half_width, h, ratio)[::-1])
    if half_width > yb:
        parts.append(_grow(yb, half_width, h, ratio))
    y = np.concatenate(parts)
    x, y = np.unique(np.round(x, 9)), np.unique(np.round(y, 9))
    X, Y = np.meshgrid(x, y, indexing="ij")
    Z = np.zeros_like(X)
    pt = lambda xs, ys: np.stack([X[xs, ys], Y[xs, ys], Z[xs, ys]], -1).reshape(-1, 3)
    lo, hi = slice(None, -1), slice(1, None)
    c1, c2, c3, c4 = pt(lo, lo), pt(hi, lo), pt(hi, hi), pt(lo, hi)
    return c1, c2, c3, c4, 0.25 * (c1 + c2 + c3 + c4)


def root_lines(blade: vlm.Blade) -> list[float]:
    """x positions (m) where the blade's root vortices start and where its root chord ends."""
    root = blade.strip == 0
    return sorted({*np.round(blade.A[root][:, 0], 9), *np.round(blade.ATE[root][:, 0], 9)})


def _rings(P, c1, c2, c3, c4, chunk=400):
    """Velocity at P (N,3) of unit vortex rings (M of them): (N, M, 3), chunked over P."""
    out = np.empty((len(P), len(c1), 3))
    for i in range(0, len(P), chunk):
        p = P[i:i + chunk, None, :]
        out[i:i + chunk] = (vlm._seg(p, c1[None], c2[None]) + vlm._seg(p, c2[None], c3[None])
                            + vlm._seg(p, c3[None], c4[None]) + vlm._seg(p, c4[None], c1[None]))
    return out


def lift_slope(blade: vlm.Blade, speed: float, mode: str, plate=None, beta_deg: float = 4.0) -> float:
    """CL per radian of one symmetric blade. mode: 'wall' (+image), 'surface' (anti-image),
    'board' (anti-image + footprint rings)."""
    A, B, ATE, BTE, CP, N = blade.A, blade.B, blade.ATE, blade.BTE, blade.CP, blade.normal
    beta = math.radians(beta_deg)
    Vinf = speed * np.array([math.cos(beta), math.sin(beta), 0.0])
    sign = 1.0 if mode == "wall" else -1.0

    def fin_inf(P, chunk=400):
        out = np.empty((len(P), len(A), 3))
        for i in range(0, len(P), chunk):
            p = P[i:i + chunk, None, :]
            out[i:i + chunk] = (vlm._horseshoe(p, A[None], B[None], ATE[None], BTE[None], XHAT)
                                + sign * vlm._horseshoe(p, (B * FLIP)[None], (A * FLIP)[None],
                                                        (BTE * FLIP)[None], (ATE * FLIP)[None], XHAT))
        return out

    nf = len(A)
    a_ff = (fin_inf(CP) * N[:, None, :]).sum(-1)
    rhs_f = -(N @ Vinf)
    mid = 0.5 * (A + B)
    if mode == "board":
        c1, c2, c3, c4, pc = plate
        a_fp = (_rings(CP, c1, c2, c3, c4) * N[:, None, :]).sum(-1)          # rings -> fin CPs
        a_pf = fin_inf(pc)[:, :, 2]                                           # fin -> plate w
        a_pp = _rings(pc, c1, c2, c3, c4)[:, :, 2]
        M = np.block([[a_ff, a_fp], [a_pf, a_pp]])
        sol = np.linalg.solve(M, np.concatenate([rhs_f, np.zeros(len(pc))]))
        g, mu = sol[:nf], sol[nf:]
        v_ind = (fin_inf(mid) * g[None, :, None]).sum(1) + (_rings(mid, c1, c2, c3, c4) * mu[None, :, None]).sum(1)
    else:
        g = np.linalg.solve(a_ff, rhs_f)
        v_ind = (fin_inf(mid) * g[None, :, None]).sum(1)
    F = RHO_SEAWATER * g[:, None] * np.cross(Vinf + v_ind, B - A)
    lift = F @ np.array([-math.sin(beta), math.cos(beta), 0.0])
    return float(lift.sum()) / (0.5 * RHO_SEAWATER * speed**2 * blade.area) / beta


def _load(path):
    d = json.loads(Path(path).read_text())
    return d["fin"] if "fin" in d else d


def main() -> None:
    L: list[str] = []
    w = L.append
    speed = 8.5
    cen = fin_from_dict(_load("bench/mount/fins/centre-ridden-gen1.json"))
    side = fin_from_dict(_load("bench/mount/fins/side-shipped-gen2.json"))
    mk = lambda fin, y_mm: vlm.blade_from_planform(
        "b", *__import__("fingen.outline", fromlist=["planform"]).planform(fin.outline), alpha0_deg=0.0,
        x_ref_mm=fin.outline.base / 2.0, area_mm2=__import__("fingen.outline", fromlist=["metrics"]).metrics(fin.outline).area,
        nz=14, nx=3, xy_mm=(0.0, y_mm))
    w("# Board-edge experiment — the board as a finite plate under a free surface\n")
    w("Lift slope of one blade, untoed and uncanted, relative to the infinite wall that all our CFD and the lattice assume. "
      "Tier-0's effective-aspect-ratio factor 1.7 (against a perfect 2.0) is worth −9 % on the same scale.\n")

    def board(bl, y_mm, hw, xa, xb, h):
        return footprint(-xa * 1e-3, xb * 1e-3, hw * 1e-3, root_lines(bl), y_mm * 1e-3, h)

    def extrap(bl, y_mm, hw, xa, xb, hs=(0.008, 0.006, 0.0045)):
        """Slopes at three core cell sizes and the h -> 0 extrapolation (least-squares line in h)."""
        vals = [lift_slope(bl, speed, "board", board(bl, y_mm, hw, xa, xb, h)) for h in hs]
        c = np.polyfit(np.array(hs), np.array(vals), 1)
        return vals, float(c[1])

    # --- implementation checks
    w("## 1. Checks (centre fin on the centreline)\n")
    b = mk(cen, 0.0)
    wall = lift_slope(b, speed, "wall")
    surf = lift_slope(b, speed, "surface")
    w(f"Infinite wall: CLα {wall:.3f}. No board, free surface only: {surf:.3f} ({(surf / wall - 1) * 100:+.0f} %).\n")
    w("Grid convergence, footprint half-width 190 mm, 500 mm ahead and 150 mm behind the fin:\n")
    w("| core cell mm | rings | CLα | vs wall |")
    w("|---|---|---|---|")
    for h in (0.012, 0.008, 0.006, 0.0045):
        pl = board(b, 0.0, 190, 500, 150, h)
        sl = lift_slope(b, speed, "board", pl)
        w(f"| {h * 1e3:.1f} | {len(pl[0])} | {sl:.3f} | {(sl / wall - 1) * 100:+.1f} % |")
    vals, ex = extrap(b, 0.0, 190, 500, 150)
    w(f"| → 0 (extrapolated) | – | {ex:.3f} | {(ex / wall - 1) * 100:+.1f} % |")
    w("\nA growing footprint must return the infinite wall (extrapolated to zero cell size):\n")
    w("| footprint half-width × (ahead + behind), mm | CLα | vs wall |")
    w("|---|---|---|")
    for hw, xa, xb in ((190, 500, 150), (400, 600, 400), (800, 1000, 800), (1600, 2000, 1600)):
        t0 = time.perf_counter()
        vals, ex = extrap(b, 0.0, hw, xa, xb)
        w(f"| {hw} × ({xa} + {xb}) | {ex:.3f} | {(ex / wall - 1) * 100:+.1f} % ({time.perf_counter() - t0:.0f} s) |")

    # --- the question: centre vs side on a realistic tail
    w("\n## 2. A realistic tail (all values extrapolated to zero cell size)\n")
    w("Side fin 118 mm off the stringer; 500 mm of wetted board ahead of the fin; the tail edge 150 mm behind the fin's base centre.\n")
    w("| blade | tail half-width mm | rail outboard of the fin mm | CLα wall | CLα finite board + free surface | change |")
    w("|---|---|---|---|---|---|")
    for name, fin, y in (("centre fin", cen, 0.0), ("side fin", side, 118.0)):
        bl = mk(fin, y)
        wl = lift_slope(bl, speed, "wall")
        for hw in (160, 190, 230):
            vals, ex = extrap(bl, y, hw, 500, 150)
            w(f"| {name} | {hw} | {hw - abs(y):.0f} | {wl:.3f} | {ex:.3f} | {(ex / wl - 1) * 100:+.1f} % |")
    w("\nDistance from the fin's base centre to the tail edge behind it (tail half-width 190 mm):\n")
    w("| blade | board behind the fin mm | change vs wall |")
    w("|---|---|---|")
    for name, fin, y in (("centre fin", cen, 0.0), ("side fin", side, 118.0)):
        bl = mk(fin, y)
        wl = lift_slope(bl, speed, "wall")
        for xb in (90, 150, 250, 350):
            vals, ex = extrap(bl, y, 190, 500, xb)
            w(f"| {name} | {xb} | {(ex / wl - 1) * 100:+.1f} % |")
    w("\nWetted length ahead of the fin (tail half-width 190 mm, 150 mm behind):\n")
    w("| blade | wetted length ahead mm | change vs wall |")
    w("|---|---|---|")
    for name, fin, y in (("centre fin", cen, 0.0), ("side fin", side, 118.0)):
        bl = mk(fin, y)
        wl = lift_slope(bl, speed, "wall")
        for xa in (200, 500, 900):
            vals, ex = extrap(bl, y, 190, xa, 150)
            w(f"| {name} | {xa} | {(ex / wl - 1) * 100:+.1f} % |")

    text = "\n".join(L)
    print(text)
    for a in sys.argv[1:]:
        if a.startswith("--md="):
            Path(a.split("=", 1)[1]).write_text(text + "\n")


if __name__ == "__main__":
    main()
