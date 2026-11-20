# Mesh level 5 — a finer surface for drag going straight (2026-11-20)

Mesh level 5 of `finGenerator-cfd` is level 2 with one more surface refinement: cells of base/160 on the faces and base/320 over the first 3 % of chord and at the trailing edge (level 2: base/80 and base/160), 547 000 cells against 390 000, still wall functions and no layers; at 8.5 m/s the first cell stays in the log layer (y+ 12–162, mean 74). Same driver, speed and blades as the level-2 and level-3 runs beside this folder. Lattice columns: `scripts/lattice_vs_polar.py <this folder> --table=v1`, solved with a perfect mirror as the CFD's symmetry plane is one, with the lattice as corrected on 2026-11-20 (control points, far-wake induced drag) and table v1 with five cambered nodes.

3 % camber on the shipped gen-2 planform (9 734 mm², `plan.json`, `results.json`):

| own incidence ° | level 2: C_L, drag N | level 3: C_L, drag N | level 5: C_L, drag N | lattice, table v1: C_L, drag N | lattice, table v0 N |
|---|---|---|---|---|---|
| −4.5 | −0.089, 8.8 | −0.102, 9.9 | −0.085, 7.0 † | −0.089, 5.5 | 4.9 |
| −3.5 | −0.030, 6.9 | −0.043, 7.7 | −0.019, 5.4 † | −0.025, 4.8 | 4.5 |
| −2.5 | +0.024, 6.0 | – | +0.044, 4.8 | +0.039, 4.6 | 4.4 |
| 0 | +0.166, 5.8 | +0.164, 6.0 | +0.207, 5.6 | +0.200, 5.7 | 5.5 |
| +4 | +0.410, 10.2 | – | +0.461, 11.0 | +0.454, 10.7 | 10.6 |
| +8 | +0.590, 22.3 | – | +0.663, 22.3 † | +0.703, 19.7 | 19.6 |
| going straight (mean of −2.5 and −4.5) | 7.4 | – | **5.9** | 5.1 | 4.7 |

The cambered candidate (4.3 % camber, t/c 0.074–0.083, 10 054 mm², `../mesh-level-5-candidate/`):

| own incidence ° | level 2: C_L, drag N | level 5: C_L, drag N | lattice, table v1: C_L, drag N | lattice, table v0 N |
|---|---|---|---|---|
| −4.5 | −0.006, 12.0 | −0.001, 9.4 † | −0.002, 7.0 | 5.6 |
| −3.5 | +0.054, 9.1 | +0.062, 7.1 | +0.062, 6.0 | 5.1 |
| −2.5 | +0.116, 7.8 | +0.128, 6.0 | +0.125, 5.8 | 5.2 |
| 0 | +0.262, 7.9 | +0.291, 7.3 | +0.283, 7.4 | 7.0 |
| +4 | +0.504, 13.4 | +0.541, 14.0 | +0.532, 13.9 | 13.6 |
| going straight (mean of −2.5 and −4.5) | 9.9 | **7.7** | 6.4 | 5.4 |

The flat-inside foil on the same planform (the shipped gen-2 side fin):

| own incidence ° | level 2: C_L, drag N | level 5: C_L, drag N | lattice, table v1: C_L, drag N | lattice, table v0 N |
|---|---|---|---|---|
| −4.5 | −0.055, 16.1 | −0.070, 15.8 † | −0.083, 17.9 | 17.3 |
| −3.5 | +0.003, 13.4 | −0.014, 13.0 † | −0.015, 15.1 | 14.8 |
| −2.5 | +0.064, 11.2 | +0.048, 10.8 † | +0.051, 12.7 | 12.7 |
| 0 | –, 8.8 | +0.217, 8.2 | +0.212, 10.2 | 9.6 |
| +4 | –, 12.7 | +0.480, 11.8 | +0.480, 13.2 | 12.3 |
| going straight | 13.7 | **13.3** | 15.3 | 15.0 |

† stopped at the 800-iteration cap on its residuals. The forces are steady all the same: within 0.3 % over the last 200 iterations on the flat-inside fin and the candidate, within 1.5 % on the 3 % cambered fin at −4.5° and +8°. These are converged values (an earlier version of this note called them unsettled, from the iteration count alone).

## Reading

- **The excess of the level-2 and level-3 polars below about −3° was the under-resolved nose.** One refinement of the surface removes 1.5–2.6 N at the negative angles and little at 0°.
- **Lift: the lattice is within 0.011 in C_L of level 5 from −4.5° to +4° on the cambered blades** (lower from 0° up). Level 2 is 0.03–0.05 low there.
- **Drag: within 5 % from −2.5° to +4° on the three cambered blades**, now that the lattice reads its induced drag in the far wake (it was 8–9 % low at +4°). At +8° it is 12 % low with 6 % more lift: the CFD has begun to bend, the strip model has not.
- **At −4.5° level 5 reads 1.2–2.4 N more than the model on all three cambered blades.** By the 2-D referee the two thicker ones are inside their attached range there. What level 5's number is made of, and why this is open: `../mesh-level-5-v1-neutral/surface-split.md`. Level 5 is the best 3-D mesh there is for these blades, not a referee for their last 10 %: its friction is a third low and its pressure drag high.
- **The flat inside face does not care about the mesh.** 13.3 N going straight on level 5 against 13.7 N on level 2: its separation is fixed by the corner of the flat face. The lattice reads it 12–15 % high on either table (15.0–15.3 N), and v1's drag level for this family, taken from one section at its minimum, makes 0° worse (10.2 against 8.2 N). The other flat-inside sections of the main plan have not run.
- **So the saving from camber is 5.6–7.4 N per fin by this mesh** (13.3 N against 7.7 and 5.9), where the model says 8.9–10.2 N.

The best fin of the table-v1 searches on the same mesh: `../mesh-level-5-v1-neutral/` (6.1 N going straight).
