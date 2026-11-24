"""The force curves of [Smi21] read out of the paper's own vector figures.

    pdftocairo -svg -f N -l N paper.pdf pN.svg      for N = 11, 13, 14, 15
                                                    (the paper is not in the repository)
    python3 -I extract_curves.py <dir with p11.svg p13.svg p14.svg p15.svg> measured/

Figures 10 and 12-15 of Smith, Brandner, Pearce, Venning, Moreau & Clarke (2021), J. Fluids and
Structures 102:103225, are vector graphics: every condition is one polyline whose vertices are
the measured points, in half-degree steps up through stall and back down. The axes are calibrated
on the figures' own grid lines, so a value is as exact as the PDF's coordinates (0.01 pt: 1e-4 in
C_N, 0.002 deg). Coefficients as in the paper: body axes, on mean chord (0.1 m) x span;
C_N normal to the chord, C_A along it (positive aft), C_P the pitching moment about mid-chord
on mean chord^2 x span. Written per condition: alpha, C_N, C_A, C_P, the sweep (up / down), and
the lift and drag they give (C_L = C_N cos a - C_A sin a, C_D = C_N sin a + C_A cos a).
A polyline leaves out a point that lies on the line between its neighbours; those are put back
on that line and marked in `on_line` (N, A, P: which of the three).
"""

from __future__ import annotations

import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

NS = "{http://www.w3.org/2000/svg}"


def _mat(t):
    m = re.match(r"matrix\(([^)]*)\)", t or "")
    return (
        tuple(float(v) for v in re.split(r"[ ,]+", m.group(1).strip())) if m else (1, 0, 0, 1, 0, 0)
    )


def _mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _attr(el, key):
    v = el.get(key)
    if v:
        return v
    m = re.search(r"(?:^|;)\s*" + key + r":([^;]+)", el.get("style", ""))
    return m.group(1).strip() if m else ""


def polylines(svg: Path) -> list[tuple[list[tuple[float, float]], str]]:
    """Every stroked path made of straight segments only, in page coordinates, with its colour."""
    out = []

    def walk(el, m):
        m = _mul(m, _mat(el.get("transform")))
        if el.tag == NS + "path":
            toks = re.findall(r"[MLHVCZ]|-?\d+\.?\d*(?:e-?\d+)?", el.get("d", ""))
            pts, i, kinds, cmd = [], 0, Counter(), None
            while i < len(toks):
                if toks[i] in "MLHVCZ":
                    cmd = toks[i]
                    kinds[cmd] += 1
                    i += 1
                elif cmd in "ML":
                    x, y = float(toks[i]), float(toks[i + 1])
                    i += 2
                    pts.append((m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]))
                else:
                    i += 1
            if kinds["C"] == 0 and kinds["M"] == 1 and len(pts) >= 25:
                out.append((pts, _attr(el, "stroke")))
        for ch in el:
            if ch.tag != NS + "defs":
                walk(ch, m)

    walk(ET.parse(svg).getroot(), (1, 0, 0, 1, 0, 0))
    return out


def _dark(colour: str) -> float:
    return sum(float(v) for v in re.findall(r"[\d.]+", colour))


class Panel:
    """A plot panel: x of two angles, y of two values, and the frame the curves lie in."""

    def __init__(self, xa, ya, frame):
        (self.x0, self.a0), (self.x1, self.a1) = xa
        (self.y0, self.v0), (self.y1, self.v1) = ya
        self.frame = frame  # (xmin, xmax, ymin, ymax) in page points

    def curves(self, lines, top, bottom):
        """The polylines of one set of curves, by colour, darkest first: [(alpha, value), ...]
        in drawing order. A set is told from its neighbours (the same curves staggered, another
        quantity) by where its highest point lies (`top`, a range of page y) and by nothing of it
        lying below `bottom`. Vertices outside the frame (some conditions were measured beyond
        the plotted range) are left out; a condition drawn as two paths, up and down, is joined."""
        xmin, xmax, ymin, ymax = self.frame
        found: dict[str, list] = {}
        for pts, colour in lines:
            inside = [
                (x, y)
                for x, y in pts
                if xmin - 0.5 <= x <= xmax + 0.5 and ymin - 0.5 <= y <= ymax + 0.5
            ]
            if len(inside) < 25:
                continue
            ys = [y for _, y in inside]
            if not (top[0] <= min(ys) <= top[1] and max(ys) <= bottom):
                continue
            data = [
                (
                    self.a0 + (x - self.x0) * (self.a1 - self.a0) / (self.x1 - self.x0),
                    self.v0 + (y - self.y0) * (self.v1 - self.v0) / (self.y1 - self.y0),
                )
                for x, y in inside
            ]
            found.setdefault(colour, []).extend(data)
        return [found[c] for c in sorted(found, key=_dark)]


def _sweeps(curve):
    """Index by (sweep, half-degree step). A point belongs to the sweep it is reached in:
    up while the angle rises, down while it falls."""
    out = {}
    for i, (a, v) in enumerate(curve):
        prev = curve[i - 1][0] if i else curve[1][0] - 2 * (curve[1][0] - a)
        out[
            (
                "up"
                if a >= prev - 1e-6
                and not (i and abs(a - prev) < 1e-6 and ("up", round(a * 2)) in out)
                else "down",
                round(a * 2),
            )
        ] = v
    return out


def _filled(series: dict, keys: list[int]) -> tuple[dict, set]:
    """A figure's polyline leaves out a point that lies on the straight line between its
    neighbours. Put those back by that line; say which."""
    have = sorted(series)
    out, added = dict(series), set()
    for k in keys:
        if k in series:
            continue
        lo = max((h for h in have if h < k), default=None)
        hi = min((h for h in have if h > k), default=None)
        if lo is not None and hi is not None and hi - lo <= 4:
            out[k] = series[lo] + (series[hi] - series[lo]) * (k - lo) / (hi - lo)
            added.add(k)
    return out, added


def write(path: Path, header: str, cn, ca, cp) -> None:
    rows = []
    for sweep in ("up", "down"):
        n, a, p = ({k: v for (sw, k), v in _sweeps(c).items() if sw == sweep} for c in (cn, ca, cp))
        keys = sorted(set(n) | set(a) | set(p), reverse=sweep == "down")
        (n, fn), (a, fa), (p, fp) = (_filled(series, keys) for series in (n, a, p))
        for k in keys:
            if k not in n or k not in a or k not in p:
                continue
            al = k / 2.0
            r = math.radians(al)
            cl = n[k] * math.cos(r) - a[k] * math.sin(r)
            cd = n[k] * math.sin(r) + a[k] * math.cos(r)
            on_line = "".join(t for t, f in (("N", fn), ("A", fa), ("P", fp)) if k in f)
            rows.append(
                f"{al:.1f},{sweep},{n[k]:.4f},{a[k]:.4f},{p[k]:.4f},{cl:.4f},{cd:.4f},{on_line}"
            )
    path.write_text(header + "alpha_deg,sweep,CN,CA,CP,CL,CD,on_line\n" + "\n".join(rows) + "\n")


HEAD = (
    "# From the vector figures of Smith, Brandner, Pearce, Venning, Moreau & Clarke (2021),\n"
    "# J. Fluids and Structures 102:103225, {fig}. NACA 0012 trapezoid, root 120 mm, tip 80 mm,\n"
    "# span {b} mm, hung from the tunnel ceiling; ceiling boundary layer {db} of the span;\n"
    "# Re {re} on the mean chord (0.1 m). Body axes, on mean chord x span; CL and CD derived\n"
    "# (extract_curves.py).\n"
)


def main() -> None:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    # Fig. 10 (page 11): the long blade in the natural layer (8 % of span), by Reynolds number.
    lines = polylines(src / "p11.svg")
    top = Panel(
        ((204.32, 0.0), (338.12, 25.0)),
        ((215.23, 0.0), (64.44, 1.8)),
        (177.57, 364.88, 56.06, 231.99),
    )
    mid_a = Panel(
        ((204.40, 0.0), (338.57, 25.0)),
        ((320.15, 0.0), (268.11, 0.4)),
        (177.57, 365.39, 242.10, 359.18),
    )
    mid_p = Panel(
        ((204.40, 0.0), (338.57, 25.0)),
        ((320.15, 0.0), (268.11, 0.2)),
        (177.57, 365.39, 242.10, 359.18),
    )
    cn = top.curves(lines, (120.0, 160.0), 232.0)  # not the staggered copies above, nor C_N' below
    ca = mid_a.curves(lines, (305.0, 322.0), 352.0)
    cp = mid_p.curves(lines, (245.0, 280.0), 331.0)
    for rey, n, a, p in zip(("1.2e6", "1.0e6", "0.8e6", "0.6e6", "0.4e6"), cn, ca, cp, strict=True):
        write(
            dst / f"long-b240-db0.08-Re{rey}.csv",
            HEAD.format(fig="Fig. 10", b=240, db="8 %", re=rey),
            n,
            a,
            p,
        )
    # Figs. 12-15 (pages 13-15): both blades at Re 1.0e6 against the depth of immersion.
    lines13, lines14, lines15 = (polylines(src / f"p{n}.svg") for n in (13, 14, 15))
    f12 = Panel(
        ((204.54, 0.0), (339.06, 25.0)),
        ((202.99, 0.0), (58.75, 2.7)),
        (177.64, 365.96, 58.75, 235.04),
    )
    f13 = Panel(
        ((209.02, 0.0), (365.96, 25.0)),
        ((511.78, 0.0), (367.54, 2.7)),
        (177.63, 365.96, 367.54, 543.83),
    )
    f14a = Panel(
        ((204.24, 0.0), (338.01, 25.0)),
        ((135.28, 0.0), (68.57, 0.4)),
        (177.49, 364.76, 56.07, 172.80),
    )
    f14p = Panel(
        ((204.24, 0.0), (338.01, 25.0)),
        ((151.95, 0.0), (68.57, 0.25)),
        (177.49, 364.76, 56.07, 172.80),
    )
    f15a = Panel(
        ((208.70, 0.0), (364.76, 25.0)),
        ((136.88, 0.0), (65.05, 0.4)),
        (177.49, 364.76, 56.07, 172.80),
    )
    f15p = Panel(
        ((208.70, 0.0), (364.76, 25.0)),
        ((154.84, 0.0), (65.05, 0.25)),
        (177.49, 364.76, 56.07, 172.80),
    )
    short = ("0.90", "0.81", "0.70", "0.59", "0.47", "0.35", "0.28", "0.27", "0.16")
    long_ = ("0.45", "0.40", "0.35", "0.30", "0.23", "0.17", "0.14", "0.13", "0.08")
    for tag, b, names, cn, ca, cp, figs in (
        (
            "short-b120",
            120,
            short,
            f12.curves(lines13, (146.0, 154.0), 209.5),
            f14a.curves(lines14, (124.0, 135.0), 173.0),
            f14p.curves(lines14, (68.0, 84.0), 173.0),
            "Figs. 12, 14",
        ),
        (
            "long-b240",
            240,
            long_,
            f13.curves(lines13, (455.0, 472.0), 520.5),
            f15a.curves(lines15, (123.0, 135.0), 173.0),
            f15p.curves(lines15, (60.0, 76.0), 173.0),
            "Figs. 13, 15",
        ),
    ):
        for db, n, a, p in zip(names, cn, ca, cp, strict=True):
            write(
                dst / f"{tag}-Re1.0e6-db{db}.csv",
                HEAD.format(fig=figs, b=b, db=f"{float(db) * 100:.0f} %", re="1.0e6"),
                n,
                a,
                p,
            )
    print(len(list(dst.glob("*.csv"))), "files")


if __name__ == "__main__":
    main()
