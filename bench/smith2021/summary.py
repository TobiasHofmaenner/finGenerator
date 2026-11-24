"""One line per measured condition of [Smi21] (measured/*.csv): slope, break, stall, return.

python3 summary.py measured/ > measured-summary.md
"""

import csv
import sys
from pathlib import Path

print(
    "| condition | C_N per degree, 0–4° | C_L 5 % below its line (0°, 4°) at | "
    "highest C_N on the way up, at | stall on the way up (C_N falls by more than 0.05 in half "
    "a degree) after | back on the up-curve (within 0.02) from | C_D at 0° |"
)
print("|---|---|---|---|---|---|---|")
for f in sorted(Path(sys.argv[1]).glob("*.csv")):
    rows = list(csv.DictReader(line for line in f.open() if not line.startswith("#")))
    up = {float(r["alpha_deg"]): r for r in rows if r["sweep"] == "up"}
    dn = {float(r["alpha_deg"]): r for r in rows if r["sweep"] == "down"}
    al = sorted(up)
    cn = {a: float(up[a]["CN"]) for a in al}
    cl = {a: float(up[a]["CL"]) for a in al}
    slope = (cn[4.0] - cn[0.0]) / 4.0
    k = (cl[4.0] - cl[0.0]) / 4.0
    below = [(a, cl[a] / (cl[0.0] + k * a) - 1.0) for a in al if a >= 5.0]
    five = "not reached"
    for (a0, d0), (a1, d1) in zip(below[:-1], below[1:], strict=True):
        if d0 > -0.05 >= d1:
            five = f"{a0 + (a1 - a0) * (-0.05 - d0) / (d1 - d0):.1f}°"
            break
    a_max = max(al, key=lambda a: cn[a])
    drops = [a0 for a0, a1 in zip(al[:-1], al[1:], strict=True) if cn[a0] - cn[a1] > 0.05]
    stall = f"{drops[0]:.1f}°" if drops else "gradual"
    back = [
        a
        for a in sorted(dn, reverse=True)
        if a in cn and a < (drops[0] if drops else a_max) and abs(float(dn[a]["CN"]) - cn[a]) < 0.02
    ]
    ret = f"{back[0]:.1f}°" if back and drops else "–"
    print(
        f"| {f.stem} | {slope:.4f} | {five} | {cn[a_max]:.3f}, {a_max:.1f}° | {stall} | {ret} | "
        f"{float(up[0.0]['CD']):.4f} |"
    )
