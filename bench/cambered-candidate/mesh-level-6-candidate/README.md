# The cambered candidate one mesh level finer (2026-11-22)

Question: on the section table rebuilt from the converged referee the lattice has this fin (4.3 % camber, t/c 0.074–0.083, 10 054 mm²) at 5.0 N from −2.5° to −4.5° of own incidence, where it works going straight. Mesh level 5 has 6.0, 7.1 and 9.4 N there (`../mesh-level-5-candidate/`). The fin, or the mesh's nose?

The same driver, speed (8.5 m/s), angles and inlet as the level-5 polar, on mesh level 6 of `finGenerator-cfd`: level 2 with two more surface refinements, 1 035 476 cells, wall functions, no layers, mean wall y⁺ 45–47. Cells on the nose and what they are against this fin's nose radius at the base (0.74 mm on a base of 123 mm; outboard the chord shrinks and the cells do not):

| mesh level | nose cells mm | cells per nose radius at the base |
|---|---|---|
| 2 | 0.77 | 1.0 |
| 5 | 0.39 | 1.9 |
| 6 | 0.19 | 3.9 |

C_L and drag in N; lattice: `uv run python scripts/lattice_vs_polar.py bench/cambered-candidate/mesh-level-6-candidate --table=v1` (section table of 2026-11-22).

| own incidence ° | level 2 | level 5 | level 6 | lattice |
|---|---|---|---|---|
| −4.5 | −0.006, 12.0 | −0.001, 9.4 † | −0.001, 7.9 | +0.002, 5.0 |
| −3.5 | +0.054, 9.1 | +0.062, 7.1 | +0.068, 5.6 | +0.065, 5.0 |
| −2.5 | +0.116, 7.8 | +0.128, 6.0 | +0.133, 5.1 | +0.128, 5.2 |
| 0 | +0.262, 7.9 | +0.291, 7.3 | +0.290, 6.8 | +0.285, 7.1 |
| +4 | +0.504, 13.4 | +0.541, 14.0 | +0.537, 13.5 | +0.533, 13.7 |
| going straight (mean of −2.5 and −4.5) | 9.9 | 7.7 | 6.5 | 5.1 |

(† ran to the cap of 800 iterations; every level-6 row stopped on its residuals, the one at −4.5° after 633 iterations.)

## Reading

- **Each refinement of the nose takes drag off below −2.5°, and the series has not stopped.** Going straight: 9.9, 7.7, 6.5 N, the lattice 5.1 N. At −2.5° level 6 is on the lattice (3 % below), at −3.5° 12 % above, at −4.5° still 57 % above.
- **It recovers from the inside out, as a nose would.** In 2-D on the exact outline with a resolved wall, a thin cambered section keeps its lower end with 7 cells per nose radius, loses half a degree of it with 3.5 and two to two and a half degrees with 1.7 (`../../section-tables/nose/`, section 3). Level 6 has 3.9 at the base and under 2 over the outer half of the blade. The row at −4.5°, where the outer strips are within a degree of their lower end even in the lattice, is the one that has not closed.
- From 0° up the three meshes and the lattice agree within 4 % (level 6: 4 % below at 0°, 2 % below at +4°).

## What it does not say

That the fin costs 5.1 N going straight. No mesh here resolves the nose along the whole leading edge: that takes cells of 0.05 mm at the tip, a nose band and not a level. What the series says is that the difference between the level-5 polar and the lattice shrinks by a third to two thirds with one refinement of the nose, at the angles and in the order an under-resolved nose predicts.
