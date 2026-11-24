"""Force history of every row of a polar: means of the last three windows of 150 iterations
and the range inside the last one. A row at the iteration cap is filed with the mean of its
last 150 iterations; this shows whether that number is a settled value or one sample of a swing.

    python3 hist.py <variant dir>      (the directory holding a+NN.N/)
"""
import pathlib
import sys

import numpy as np

base = pathlib.Path(sys.argv[1])
for d in sorted(base.glob("a+*")):
    f = d / "postProcessing/forceCoeffs/0/coefficient.dat"
    hdr = None
    rows = []
    for line in f.read_text().splitlines():
        if line.startswith("#"):
            hdr = line.lstrip("# ").split()
            continue
        rows.append([float(x) for x in line.split()])
    a = np.array(rows)
    icl, icd = hdr.index("Cl"), hdr.index("Cd")
    n = len(a)
    w = 150 if n >= 450 else max(n // 3, 1)
    cl = [a[n - (k + 1) * w:n - k * w, icl].mean() for k in (2, 1, 0)]
    cd = [a[n - (k + 1) * w:n - k * w, icd].mean() for k in (2, 1, 0)]
    last = a[n - w:, icl]
    print(f"{d.name}  it {n:4d}  cl windows {cl[0]:.4f} {cl[1]:.4f} {cl[2]:.4f}"
          f"  range in last {last.min():.4f}..{last.max():.4f}"
          f"  cd windows {cd[0]:.4f} {cd[1]:.4f} {cd[2]:.4f}")
