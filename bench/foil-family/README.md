# Foil-family test — flat inside face vs conventional camber (isolated CFD, 2026-11-19)

Question: a flat-inside side fin runs at minus its toe angle going straight. Is the drag it pays there a property of the flat inside face, and does a conventionally cambered section avoid it? Same planform (Omar's shipped gen-2 side, 9734 mm², t/c 0.092), two sections: the flat-inside original and `FoilFamily.CAMBERED` 3 % camber at 40 % chord. Isolated fin on the symmetry plane, 8.5 m/s, level-2 RANS, driver `finGenerator-cfd/scripts/polar_angles.py`, plan and raw results beside this file. Flat-inside 0…16° rows are the earlier verify polar (`out/cfd/omar-big-gen2-m2-shipped`). Raw cases on the EPYC: `~/bench-results/foil-family`.

| α ° | flat CL | flat CD | flat drag N | cambered CL | cambered CD | cambered drag N | Δ N |
|---|---|---|---|---|---|---|---|
| -4.5 | -0.055 | 0.0448 | 16.1 | -0.089 | 0.0244 | 8.8 | -7.4 |
| -3.5 | +0.003 | 0.0371 | 13.4 | -0.030 | 0.0193 | 6.9 | -6.4 |
| -2.5 | +0.064 | 0.0311 | 11.2 | +0.024 | 0.0167 | 6.0 | -5.2 |
| +0.0 | +0.228 | 0.0244 | 8.8 | +0.166 | 0.0162 | 5.8 | -2.9 |
| +4.0 | +0.488 | 0.0353 | 12.7 | +0.410 | 0.0283 | 10.2 | -2.5 |
| +8.0 | +0.679 | 0.0688 | 24.8 | +0.590 | 0.0620 | 22.3 | -2.5 |
| +12.0 | +0.800 | 0.1201 | 43.3 | +0.710 | 0.1143 | 41.2 | -2.1 |
| +16.0 | +0.829 | 0.1846 | 66.5 | +0.715 | 0.1832 | 66.0 | -0.5 |

Zero-lift angle: flat -3.57°, cambered -2.94°. Lift slope (fit −4.5…4°): 3.68 vs 3.36 per rad. Maximum lift in the polar: 0.829 vs 0.715 (RANS values past the knee are lower bounds, see docs/CFD-BENCH.md).

The isolated flat-inside fin at −2.5 / −3.5 / −4.5° reproduces the side fin's drag in the full set at toe 2.5 / 3.5 / 4.5° (bench/mount) to the first decimal, so the penalty belongs to the foil, not to set interference:

| own incidence ° | isolated flat-inside, N | same fin in the set, N |
|---|---|---|
| -2.5 | 11.2 | 11.2 |
| -3.5 | 13.4 | 13.3 |
| -4.5 | 16.1 | 16.1 |

## Drag at EQUAL side force (interpolated in the polars), per fin

| CL | side force N | flat-inside N | cambered N | Δ |
|---|---|---|---|---|
| 0.0 | 0 | 13.5 | 6.4 | -7.1 N (-52 %) |
| 0.1 | 36 | 10.7 | 5.9 | -4.8 N (-45 %) |
| 0.2 | 72 | 9.2 | 6.4 | -2.8 N (-30 %) |
| 0.3 | 108 | 9.9 | 8.2 | -1.6 N (-17 %) |
| 0.4 | 144 | 11.4 | 10.0 | -1.4 N (-12 %) |
| 0.5 | 180 | 13.5 | 16.3 | +2.8 N (+21 %) |
| 0.6 | 216 | 19.8 | 24.0 | +4.2 N (+21 %) |
| 0.7 | 252 | 28.0 | 39.6 | +11.6 N (+41 %) |

## Reading

- Going straight, the cambered section halves the side fin's drag: 13.4 → 6.4 N at zero side force. For the pair that is ≈ 14 N of the set's ≈ 31 N, about a tenth of a 60 kg rider's total board drag.
- It stays ahead up to about 150 N of side force per fin (CL ≈ 0.45), then the flat-inside foil is better: +21 % drag for the cambered one at CL 0.5–0.6, +41 % at 0.7, and 14 % less maximum lift.
- So the inside-face shape is a genuine trade: speed in trim and light turns against drive and hold in hard ones. Camber between 2 % and the flat foil's equivalent 4.6 % is the dial; 3.5 % would match the flat foil's zero-lift angle.
- NeuralFoil had predicted the direction and the size of the trim-drag gap (15.2 vs 4.5 N per fin) but the wrong sign for maximum lift (it had the cambered section higher).
