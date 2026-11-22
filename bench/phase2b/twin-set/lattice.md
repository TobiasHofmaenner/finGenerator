# A twin set through the lattice, beside its set CFD

Written by `scripts/twin_set_lattice.py`. Fin 14790 mm² (flat_inside, t/c 0.1), toe 2°, cant 4°, ±165 mm off the centreline, 7 m/s, CFD mesh level 5. Lattice with a perfect mirror.

| leeway ° | fin | lift: linear lattice | viscous lattice | set CFD | drag: viscous lattice | set CFD |
|---|---|---|---|---|---|---|
| 0 | right | +0.066 | +0.065 | +0.054 | 0.0314 | 0.0292 |
| 0 | left | -0.066 | -0.065 | -0.053 | 0.0314 | 0.0292 |
| 2 | right | +0.126 | +0.125 | +0.106 | 0.0297 | 0.0255 |
| 2 | left | -0.007 | -0.004 | -0.004 | 0.0358 | 0.0356 |
| 4 | right | +0.187 | +0.187 | +0.165 | 0.0305 | 0.0254 |
| 4 | left | +0.054 | +0.057 | +0.051 | 0.0425 | 0.0452 |
| 6 | right | +0.249 | +0.250 | +0.229 | 0.0343 | 0.0298 |
| 6 | left | +0.115 | +0.108 | +0.107 | 0.0539 | 0.0596 |
| 8 | right | +0.314 | +0.313 | +0.299 | 0.0404 | 0.0384 |
| 8 | left | +0.178 | +0.175 | +0.149 | 0.0664 | 0.0769 |
| 12 | right | +0.450 | +0.449 | +0.449 | 0.0613 | 0.0681 |
| 12 | left | +0.310 | +0.306 | +0.226 | 0.1012 | 0.1177 |

| leeway ° | share of the loaded fin: linear lattice | viscous lattice | set CFD |
|---|---|---|---|
| 0 | nan | nan | 244.03 |
| 2 | 1.06 | 1.03 | 1.04 |
| 4 | 0.78 | 0.77 | 0.77 |
| 6 | 0.68 | 0.70 | 0.68 |
| 8 | 0.64 | 0.64 | 0.67 |
| 12 | 0.59 | 0.59 | 0.66 |

Going straight, a fin of this pair carries no side force at 4.12° of toe (linear lattice).

| toe ° | share of the loaded fin at leeway 2° | 4° | 6° | 8° | 12° |
|---|---|---|---|---|---|
| 0 | 1.57 | 1.04 | 0.86 | 0.77 | 0.69 |
| 2 | 1.06 | 0.78 | 0.68 | 0.64 | 0.59 |
| 4 | 0.53 | 0.51 | 0.50 | 0.50 | 0.50 |
