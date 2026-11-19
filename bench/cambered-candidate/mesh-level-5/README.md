# Mesh level 5 — a finer surface as the 3-D referee for drag going straight (2026-11-20)

Mesh level 5 of `finGenerator-cfd` is level 2 with one more surface refinement (cells of base/320 instead of base/160, 547 000 cells against 390 000), still wall functions and no layers; at 8.5 m/s the first cell stays in the log layer (y+ 12–162, mean 74). Same driver, speed and blades as the level-2 and level-3 runs beside this folder. Lattice columns: `scripts/lattice_vs_polar.py <this folder> --table=v1`, solved with a perfect mirror as the CFD's symmetry plane is one.

3 % camber on the shipped gen-2 planform (9 734 mm², `plan.json`, `results.json`):

| own incidence ° | level 2: C_L, drag N | level 3: C_L, drag N | level 5: C_L, drag N | lattice, table v1: C_L, drag N | lattice, table v0 N |
|---|---|---|---|---|---|
| −4.5 | −0.089, 8.8 | −0.102, 9.9 | −0.085, 7.0 † | −0.092, 5.6 | 4.9 |
| −3.5 | −0.030, 6.9 | −0.043, 7.7 | −0.019, 5.4 † | −0.026, 4.9 | 4.5 |
| −2.5 | +0.024, 6.0 | – | +0.044, 4.8 | +0.040, 4.6 | 4.4 |
| 0 | +0.166, 5.8 | +0.164, 6.0 | +0.207, 5.6 | +0.206, 5.6 | 5.4 |
| +4 | +0.410, 10.2 | – | +0.461, 11.0 | +0.467, 10.1 | 9.9 |
| +8 | +0.590, 22.3 | – | +0.663, 22.3 † | +0.723, 18.3 | 18.1 |
| going straight (mean of −2.5 and −4.5) | 7.4 | – | **5.9** | 5.1 | 4.6 |

The cambered candidate (4.3 % camber, t/c 0.074–0.083, 10 054 mm², `../mesh-level-5-candidate/`):

| own incidence ° | level 2: C_L, drag N | level 5: C_L, drag N | lattice, table v1: C_L, drag N | lattice, plain ratio blend N | lattice, table v0 N |
|---|---|---|---|---|---|
| −4.5 | −0.006, 12.0 | −0.001, 9.4 † | −0.003, 7.3 | 10.1 | 5.6 |
| −3.5 | +0.054, 9.1 | +0.062, 7.1 | +0.065, 6.0 | 7.2 | 5.1 |
| −2.5 | +0.116, 7.8 | +0.128, 6.0 | +0.130, 5.7 | 5.7 | 5.2 |
| 0 | +0.262, 7.9 | +0.291, 7.3 | +0.292, 7.1 | 7.0 | 6.7 |
| +4 | +0.504, 13.4 | +0.541, 14.0 | +0.548, 12.9 | 12.9 | 12.5 |
| going straight (mean of −2.5 and −4.5) | 9.9 | **7.7** | 6.5 | 7.9 | 5.4 |

The flat-inside foil on the same planform (the shipped gen-2 side fin):

| own incidence ° | level 2: C_L, drag N | level 5: C_L, drag N | lattice, table v1: C_L, drag N | lattice, table v0 N |
|---|---|---|---|---|
| −4.5 | −0.055, 16.1 | −0.070, 15.8 † | −0.085, 18.0 | 17.3 |
| −3.5 | +0.003, 13.4 | −0.014, 13.0 † | −0.015, 15.1 | 14.8 |
| −2.5 | +0.064, 11.2 | +0.048, 10.8 † | +0.053, 12.6 | 12.6 |
| 0 | –, 8.8 | +0.217, 8.2 | +0.219, 9.9 | 9.4 |
| +4 | –, 12.7 | +0.480, 11.8 | +0.495, 12.4 | 11.5 |
| going straight | 13.7 | **13.3** | 15.3 | 15.0 |

† at the 800-iteration cap: the flow sits at an edge of its attached range, or (flat inside, below 0°) is separated on the inside face, and does not settle.

## Reading

- **The excess of the level-2 and level-3 polars below about −3° was the under-resolved nose.** One refinement of the surface removes 1.5–2.6 N at the negative angles and little at 0°.
- **Lift: lattice and level 5 agree within 0.007 in C_L from −4.5° to +4° on both blades.** Level 2 is 0.03–0.05 low there. (Lattice tables written before 2026-11-20 used the board's weakened mirror against this symmetry plane and read 8 % low themselves; the two offsets cancelled.)
- **Drag: within 3 % at 0°.** At +4° the lattice is 8 % low, most of it its near-field induced drag. At +8° it is 18 % low with 9 % more lift: the CFD has begun to bend, the strip model has not.
- **The flat inside face does not care about the mesh.** 13.3 N going straight on level 5 against 13.7 N on level 2: its separation is fixed by the corner of the flat face. The lattice reads it 12–15 % high on either table (15.0–15.3 N), and v1's drag level for this family, taken from one section at its minimum, makes 0° worse (9.9 against 8.2 N). The other flat-inside sections of the main plan have not run.
- **So the saving from camber is 5.6–7.4 N per fin by this mesh** (13.3 N against 7.7 and 5.9), where the model says 8.8–10.2 N: it is about a newton too kind to these two cambered blades and two newtons too hard on the flat one.
- **Going straight, the candidate costs 7.7 N.** Table v1 reads 6.5 N, the plain blend of RANS / table ratios 7.9 N, table v0 5.4 N. Both blades here have their sections between the two thicknesses the 2-D referee has run (t/c 0.070 and 0.092); v1 moves the lower end of the attached range evenly between them, and these polars say it stays early for longer. Sections at t/c 0.080 are queued.

The best fin of the table-v1 searches is running on the same mesh (`../mesh-level-5-v1-neutral/` when it lands).
