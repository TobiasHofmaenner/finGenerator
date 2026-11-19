# Mesh level 5 — a finer surface as the 3-D referee for drag going straight (2026-11-20)

Mesh level 5 of `finGenerator-cfd` is level 2 with one more surface refinement (cells of base/320 instead of base/160, 547 000 cells against 390 000), still wall functions and no layers; at 8.5 m/s the first cell stays in the log layer (y+ 12–162, mean 74). Same driver, speed and blades as the level-2 and level-3 runs beside this folder.

3 % camber on the shipped gen-2 planform (9 734 mm²):

| own incidence ° | level 2: C_L, drag N | level 3: C_L, drag N | level 5: C_L, drag N | lattice, table v0 N | lattice, RANS sections N |
|---|---|---|---|---|---|
| −4.5 | −0.089, 8.8 | −0.102, 9.9 | −0.085, 7.0 † | 4.9 | 6.3 |
| −3.5 | −0.030, 6.9 | −0.043, 7.7 | −0.020, 5.4 † | 4.5 | 4.9 |
| 0 | +0.166, 5.8 | +0.164, 6.0 | +0.207, 5.6 | 5.4 | 5.6 |
| +4 | +0.410, 10.2 | – | +0.461, 11.0 | 9.9 | 10.1 |

† at the 800-iteration cap: the flow sits at the edge of its attached range and does not settle.

One refinement of the surface removes 1.5–1.8 N at the negative angles and nothing at 0°. The excess of the level-2 and level-3 polars below about −3° was the under-resolved nose. What is left between level 5 and the lattice with referee sections is 0.5–0.7 N, on runs that do not settle. At +4° level 5 carries 12 % more lift than level 2; at equal lift its drag matches the lattice.

`results.json` is a snapshot; the candidate, the flat-inside fin and the −2.5° and +8° rows of this blade are still running.
