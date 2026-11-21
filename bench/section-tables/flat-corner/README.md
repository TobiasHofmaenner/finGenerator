# The nose corner of a flat-inside section (2026-11-21)

Question: a flat-inside section has more than twice its working-side drag at the −2.5…−4.5° it sees going straight, toed in. Its nose is a real corner, where the flat face meets the curved one at a right angle. Does rounding that corner bring the drag down?

Answer: a little. A radius of 1 mm (0.8 % of chord) takes 16 % off at −3.5° against a radius of 0.25 mm, and below 0.25 mm the radius makes no difference. With 1 mm the section still has twice its working-side drag there. The flat face is what costs, not its edge.

Runs: `finGenerator-cfd/scripts/section_polar.py` with `corner_radius` (an arc tangent to the flat face and to the outer surface replaces the corner; the rest of the section is untouched), on t/c 0.092, chord 0.12 m, Re 5.7e5, the recipe of `../nose/` (nose cells 0.023 mm, 13 layers from 9.3 µm, domain ±20 chords). `results.json` has the rows and each mesh's layer record. Run on the laptop (`~/bench-results/sections2`).

| nose corner | layers the mesher kept (of 13) | −4.5° | −3.5° | −2.5° | +2° |
|---|---|---|---|---|---|
| sharp, first recipe (corner cells 0.19 mm) | 12.3 (98.7 %) | −0.083, 555* | +0.024, 423* | +0.141, 319* | +0.648, 163 |
| sharp, this recipe | 2.5 (19.8 %) | not run | not run | not run | not run |
| radius 0.1 mm | 1.9 (15.4 %) | −0.081, 511 | +0.030, 383 | +0.145, 286 | +0.650, 148 |
| radius 0.25 mm | 12.9 (99.9 %) | −0.079, 513 | +0.032, 384 | +0.148, 287 | +0.649, 156 |
| radius 0.5 mm | 12.9 (99.9 %) | −0.074, 486 | +0.038, 361 | +0.151, 269 | +0.650, 155 |
| radius 1.0 mm | 12.9 (99.9 %) | −0.066, 438 | +0.045, 321 | +0.156, 239 | +0.650, 154 |

(lift coefficient, drag coefficient × 10⁴; * = not settled in 3000 iterations)

- **The radius matters from a quarter millimetre up.** Against 0.25 mm, a radius of 0.5 mm has 6 % less drag at −3.5° and −2.5°, one of 1.0 mm 16–17 %. On the working side (+2°) the three agree within 1 %, and the lift is the same everywhere.
- **Below a quarter millimetre it does not.** The 0.1 mm run has the drag of the 0.25 mm run at all three negative angles (within 0.4 %). Its mesh is not a referee's (next point), but drag at these angles is the pressure drag of the separated flat face and does not depend on the wall being resolved. The first-recipe sharp node sits 8–11 % above: recipe and corner together, not to be taken apart.
- **A corner sharper than 0.25 mm cannot be meshed with a resolved wall on this recipe.** The layer stack does not fit around it with cells of 0.023 mm: the mesher kept 1.9 layers of 13 at 0.1 mm and 2.5 on the sharp corner, and ended without an error. The 0.1 mm run went through before that was noticed: y+ up to 19, and 5 % less drag at +2° than its neighbours, where friction is most of the drag. Its rows stay in `results.json` as what such a mesh gives; the sharp run was stopped. The driver now refuses a resolved-wall mesh that kept less than 90 % of its stack.
- **The rounded runs settle.** All rows with a radius of 0.25 mm or more settled within 900–1500 iterations; the first-recipe sharp node did not settle at any negative angle.

## What it changes

- **The flat-inside penalty going straight stands.** At −3.5° the section has 0.032–0.038 of drag coefficient against 0.0155 on its working side, whatever the corner. No finish removes it; a cambered section at the same lift has 0.014 there (`../rerun/`).
- **A finishing instruction worth having.** A printed and sanded corner has a radius of a few tenths of a millimetre already. Taking it to 1 mm is worth about a sixth of the section's drag going straight and costs nothing on the working side. That is drag of the section; what it is in newtons on a fin follows when the table has the family.
- **The table's flat-inside family is rerun with a corner radius of 0.5 mm** (0.4 % of chord: a sanded corner), at t/c 0.05, 0.065, 0.092 and 0.12 and at three Reynolds numbers for t/c 0.092. A sharp corner is what the generator draws; no fin has one after printing and sanding, and no mesh with a resolved wall either. The one flat-inside section the table stands on until then is the first-recipe sharp node, 15 % above the 0.5 mm run at −3.5°.
