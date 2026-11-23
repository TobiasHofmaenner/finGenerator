"""The nose of the fin surface the mesher was given: a cut at a span station, the facets around the leading edge.
usage: stl_nose.py <binary fin.stl> <t/c> <z in mm ...>  (STL in metres or mm; detected)"""
import struct, sys
import numpy as np
raw = open(sys.argv[1], "rb").read()
n = struct.unpack("<I", raw[80:84])[0]
tri = np.frombuffer(raw, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n, offset=84)["v"].astype(float)
scale = 1000.0 if tri[:, :, 2].max() < 5 else 1.0
tri = tri * scale
tc = float(sys.argv[2])
print(f"{n} triangles; extents mm x {tri[:,:,0].min():.2f}..{tri[:,:,0].max():.2f} y {tri[:,:,1].min():.2f}..{tri[:,:,1].max():.2f} z {tri[:,:,2].min():.2f}..{tri[:,:,2].max():.2f}")
for zs in sys.argv[3:]:
    z0 = float(zs)
    pts = []
    for t in tri:
        d = t[:, 2] - z0
        if d.min() > 0 or d.max() < 0:
            continue
        seg = []
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            da, db = a[2] - z0, b[2] - z0
            if da * db < 0:
                s = da / (da - db); seg.append(a + s * (b - a))
        if len(seg) == 2:
            pts.append(seg)
    pts = np.array(pts)                       # (m, 2, 3)
    allp = pts.reshape(-1, 3)
    xle, xte = allp[:, 0].min(), allp[:, 0].max()
    c = xte - xle
    r = 1.1019 * tc ** 2 * c
    # unique points around the nose, ordered by angle about a point one radius behind the leading edge
    ile = np.argmin(allp[:, 0]); yle = allp[ile, 1]
    near = allp[allp[:, 0] < xle + 0.03 * c]
    key = np.round(near[:, :2] * 1e5).astype(int)
    _, idx = np.unique(key, axis=0, return_index=True)
    q = near[idx]
    ang = np.arctan2(q[:, 1] - yle, q[:, 0] - (xle + r))
    ang = np.where(ang < 0, ang + 2 * np.pi, ang)         # 0..2pi, the nose at pi
    q = q[np.argsort(ang)]
    seglen = np.linalg.norm(np.diff(q[:, :2], axis=0), axis=1)
    dirs = np.diff(q[:, :2], axis=0); dirs /= np.linalg.norm(dirs, axis=1)[:, None]
    turn = np.degrees(np.arccos(np.clip((dirs[:-1] * dirs[1:]).sum(1), -1, 1)))
    xs = (q[:, 0] - xle) / c
    print(f"\nz {z0:.1f} mm: chord {c:.2f} mm, nose radius {r:.3f} mm, {len(q)} facet corners in the first 3 % of chord, {np.sum(xs < 0.005)} in the first 0.5 %")
    print("  corners (x/c in %, y mm):", " ".join(f"({100*x:.3f},{y - yle:+.3f})" for x, y in zip(xs, q[:, 1]) if x < 0.012))
    k = np.where(xs[1:-1] < 0.012)[0]
    print("  segment lengths mm near the nose:", " ".join(f"{v:.3f}" for v in seglen[:-1][xs[1:-1] < 0.012]))
    print("  turning angles deg at those corners:", " ".join(f"{v:.0f}" for v in turn[k]))
    # shape error against the NACA thickness form (sharp-TE form; the blunt edge changes little at the nose)
    def yt(x):
        return 5 * tc * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
    m = (xs > 0) & (xs < 0.03)
    err = np.abs(np.abs(q[m, 1] - yle) - yt(xs[m]) * c)
    print(f"  corners against the NACA form (first 3 %): largest offset {err.max()*1e3:.1f} um; half-thickness at 1 % chord: surface {np.interp(0.01, xs[q[:,1]>yle][np.argsort(xs[q[:,1]>yle])], (q[q[:,1]>yle,1]-yle)[np.argsort(xs[q[:,1]>yle])]):.3f} mm, form {yt(0.01)*c:.3f} mm")
