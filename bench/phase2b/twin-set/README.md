# A twin set over leeway: what each fin carries (2026-11-22)

Questions, from `docs/GEN3-PLAN.md` 2b.2 (a) and (d): how a twin splits its side force between the two fins, at what toe a fin of the pair carries nothing going straight, what the two fins do to each other across the board, and whether the lattice's set (`lattice.set_blades`) reads the same.

The pair: two of the stand-in keels of `../twin-keel/` (95 mm deep on a 180 mm base, flat inside t/c 0.10, 14 790 mm²), toe 2°, cant 4°, 165 mm either side of the centreline, on a flat wall, 7 m/s. Set CFD with finGenerator-cfd `scripts/twin_set.py` on mesh level 5 (wall functions, 482 412 cells, surface cells 1.1 and 0.56 mm, no wall layers, mean wall y⁺ 95–103 on both fins at every angle), the old inlet, 1500 iterations per angle (every row ran to the cap). Lift is counted across the flow in the set's frame, the same direction for both fins, each on its own area. "Right" is the fin the flow meets on its flat inside face (the loaded one), "left" the one it meets on its curved face.

- `level5/twin-set.json`: the six leeway angles.
- `level2/twin-set.json`: the coarser-mesh control at 4° and 8° (282 295 cells, mean y⁺ 160–180).
- `keel-held-stream/`: the keel alone on mesh level 5 on the held stream of `../../section-gate/` (the 3-D control of that stream), to set beside `../twin-keel/results.json`.
- `lattice.md`: `uv run python scripts/twin_set_lattice.py bench/phase2b/twin-set/level5/twin-set.json --md=…` (section table v1 of 2026-11-22, built on the held-stream sections).

*Running (2026-11-22):* the set one mesh level finer at 8°, 12° and 4°, and the level-5 set at 4 m/s.

## The set

| leeway ° | C_L right | C_L left | C_D right | C_D left | share of the loaded fin | the same on mesh level 2 |
|---|---|---|---|---|---|---|
| 0 | +0.054 | −0.053 | 0.0292 | 0.0292 | – | |
| 2 | +0.106 | −0.004 | 0.0255 | 0.0356 | 1.04 | |
| 4 | +0.165 | +0.051 | 0.0254 | 0.0452 | 0.77 | 0.75 (+0.160, +0.054) |
| 6 | +0.229 | +0.107 | 0.0298 | 0.0596 | 0.68 | |
| 8 | +0.299 | +0.149 | 0.0384 | 0.0769 | 0.67 | 0.64 (+0.292, +0.162) |
| 12 | +0.449 | +0.226 | 0.0681 | 0.1177 | 0.66 | |

The same rows as one fin's polar over its own incidence (leeway − toe on the right fin, −leeway − toe on the left), lift in the fin's own frame, drag in newtons at 7 m/s:

| own incidence ° | −14 | −10 | −8 | −6 | −4 | −2 | 0 | +2 | +4 | +6 | +10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C_L | −0.226 | −0.149 | −0.107 | −0.051 | +0.004 | +0.054 | +0.106 | +0.165 | +0.229 | +0.299 | +0.449 |
| C_D | 0.1177 | 0.0769 | 0.0596 | 0.0452 | 0.0356 | 0.0292 | 0.0255 | 0.0254 | 0.0298 | 0.0384 | 0.0681 |
| drag N | 43.7 | 28.6 | 22.1 | 16.8 | 13.2 | 10.8 | 9.5 | 9.4 | 11.1 | 14.3 | 25.3 |

## Reading

- **The two fins do not feel each other.** The loaded fin in the set against the same keel alone on the same mesh (`../twin-keel/`): own incidence 0°, lift 0.106 against 0.105 and drag 0.0255 against 0.0252; 4°, 0.229 against 0.229 and 0.0298 against 0.0294; 10°, 0.449 against 0.454 between the alone rows at 8° and 12°. That is within 1–1.5 %, at 330 mm between fins 95 mm deep. A twin is two isolated fins at own incidences leeway − toe and −leeway − toe; the thruster set of `../../mount/` said the same of its side fins.
- **The share is not a number, it is the toe against the foil's zero-lift angle.** The fin carries nothing at an own incidence of −4.1° (the row at −4°: +0.004), so going straight a fin of this pair carries nothing at 4.1° of toe; the linear lattice says 4.12°. At 2° of toe each fin is 2.1° above its zero-lift angle going straight and pushes outward with 20 N. With both fins on their lift lines the loaded fin's share is

  $$\text{share} = \tfrac12\left(1 + \frac{|\alpha_0| - \text{toe}}{\text{leeway}}\right)$$

  which gives 0.76, 0.68, 0.63 and 0.59 at 4°, 6°, 8° and 12°. The CFD has 0.77, 0.68, 0.67, 0.66: on that curve to 6°, above it from 8°. A pair toed at its foil's zero-lift angle would share evenly on the line. `fingen.sizing` assumes 0.75 at every load.
- **From 8° of leeway the unloaded fin is off its line.** At own incidence −10° and −14° its flat face is the suction side and it makes lift at 75 % and 68 % of its earlier slope, for twice the loaded fin's drag: at 8° it adds a third of the pair's side force and two thirds of its drag. The thruster set (`../../mount/`, mesh level 2) has its outside fin let go near −9° in the same way. This is why the share stops falling at about two thirds.
- **Going straight, toe costs drag on this foil.** Per fin 9.5 N with no toe, 10.8 N at 2°, 13.2 N at 4°, where it carries nothing. The lowest drag is at an own incidence of 0…+2°, with the flow along the flat face and the fin pushing outward, not at zero lift.

## The lattice beside it

Perfect mirror, the same pair, strips on section table v1 (`lattice.md` is on the table of 2026-11-22, built on the 39 held-stream sections of `../../section-tables/rerun-held/`; the column before it is the table of 2026-11-20).

| leeway ° | share: CFD | viscous lattice, table of 11-20 | table of 11-22 | lift of the unloaded fin: CFD | lattice, table of 11-22 |
|---|---|---|---|---|---|
| 2 | 1.04 | 0.96 | 1.03 | −0.004 | −0.004 |
| 4 | 0.77 | 0.73 | 0.77 | +0.051 | +0.057 |
| 6 | 0.68 | 0.65 | 0.70 | +0.107 | +0.108 |
| 8 | 0.67 | 0.62 | 0.64 | +0.149 | +0.175 |
| 12 | 0.66 | 0.59 | 0.59 | +0.226 | +0.312 |

- The loaded fin's lift is within 0.02 at every angle and equal at 12°; on the table of 11-22 the share is within 0.02 to 6°.
- **The lattice keeps the unloaded fin on its line.** At 12° it reads 38 % more lift on it than the CFD, and 13 % more side force for the pair (9 % at 8°). Its strips pass the lower end of the flat-inside section's attached range (−4.8°) from 6° of leeway on: section incidence −3.9…−5.7° from tip to root at 6°, −4.3…−6.0° at 8°, −5.1…−7.3° at 12°. Behind that end the table carries the lift on along the line, down to −0.4 at −8°, and so do the 2-D referee's rows there, which are not settled (t/c 0.092, Re 5.7e5: −0.12 at −5°, −0.23 at −6°). The lattice has a knee for a strip that reaches its section's limit on the working side and none for one driven past its lower end.
- Drag of the loaded fin: the lattice reads 8–20 % more than level 5 up to 8° and 10 % less at 12°; level 5's friction is low (`docs/CFD-BENCH.md`), and on the held stream it would read another 5 % less (below).

## The controls

- **Mesh.** Level 2 against level 5: the loaded fin's lift 2–3 % lower, the unloaded fin's 6 % and 9 % higher (4°, 8°), the share 0.02–0.03 lower. The unloaded fin's lift behind its lower end moves with the mesh, and the coarser mesh sits nearer the lattice; the finer run is to say which way it goes on.
- **Stream.** The keel alone, held stream against the old inlet (`../twin-keel/`), own incidence 0°, 4°, 8°, 12°, 16°: drag −4.8 %, −5.1 %, −3.7 %, −2.2 %, −1.3 %; lift −0.4 % to −1.2 %. The 2-D referee lost 5–12 % of its drag by the same change; on wall functions the 3-D polar loses about 5 % at low incidence. Every level-5 polar in this repository is on the old inlet.

## What this does not say

- One fin, one toe, one speed. The keel is a stand-in, low and broad (aspect ratio 0.61), with vortex lift from 8° of own incidence; a deeper twin fin has a knee, and where it sits against the unloaded fin's fall-off is not shown here.
- Where the unloaded fin leaves its line is read on wall functions, with cells of 0.56 mm at the nose. Two meshes and two sets agree on about −8…−10° of own incidence. The 2-D referee's attached range ends at −4.8° of section incidence, which this keel's inboard strips reach at about −8° of own incidence (6° of leeway); behind that end the referee's lift is unsettled, not lost, so the two do not disagree on where, only on what follows.
- The turn itself. At the lean angles the library sizes for, a pair of this area works beyond 12° of leeway.
