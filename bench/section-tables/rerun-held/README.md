# The sections on the held stream (2026-11-21 and 22)

The 35 sections of `../rerun/` again, on the stream the gate record settles on (`../../section-gate/`, section 3): k = 10⁻³ U² (turbulence intensity 2.58 %) and ω = 5 U/c, both held at those values up to the section by the model's sustaining terms ([SR07], [RS09]) instead of decaying from an inlet 20 chords away. Everything else is the recipe of `../nose/` and `../rerun/`: exact outline, nose cells of 0.023 mm on the first 2 % of chord, faces 0.375 mm, a layer stack of about 0.45 mm from a first cell of two wall units, domain ±20 chords, chord 0.12 m, trailing edge 1.2 mm, the same angles and the same marches.

Why: the old inlet's turbulence reached the section with an eddy viscosity several hundred to a thousand times the molecular one. Lift does not see it; drag is 5–12 % above what tripped tunnels give for a NACA 0012, and the break a quarter to half a degree later than in a quiet or a held stream. A quiet stream is no alternative at these Reynolds numbers: the model then leaves the layer laminar over a fifth to two fifths of the chord at Re 1.4e5.

- `results.json`: every section's plan and rows, with `complete` and the machine it ran on. Written by the collector (`~/bench-results/sections3/collect.py`) and replaced as sections finish.
- `ends.md`: where each attached range ends, read as in `../rerun/`.
- `against-old-inlet.md`: each finished section against the same section of `../rerun/`: the largest difference in lift and the ratio of drag over the rows inside both attached ranges, and both pairs of ends.

What differs from `../rerun/` besides the stream:

- **Seven wall layers at every Re 1.4e5 section.** Two of them (3 % / t/c 0.07 and 4.5 % / t/c 0.092) had ten in `../rerun/`, a stack twice as thick as at the other Reynolds numbers; the control there read 0.014 more lift and 1.4 % less drag on seven, with the same ends. Their rows in `against-old-inlet.md` carry that difference too.
- **The two symmetric t/c 0.09 sections at Re 2.8e5 and 1.4e5** are meshed with the face-weight floor of 0.02 from the start (`../rerun/`: two sections lost their layers at a threshold).
- **All 35 sections are run**, the six that `../rerun/` did not reach included.
- **Four sections are added (2026-11-22), 39 in all**, in the band of thickness where the upper end jumps as the stall moves from the nose to the trailing edge: 3 % camber at t/c 0.06 and 0.075, 4.5 % camber at t/c 0.06, flat inside at t/c 0.06, all at Re 5.7e5. On the first 25 sections the upper end of the 3 % cambered family goes 6.6°, 10.1°, 13.1° at t/c 0.05, 0.07, 0.08, and the table built with one section left out misses that section's upper end by 1.0° (cambered) and 1.7° (flat inside) rms. That gap is as large as what a finer wall moves and larger than what the stream does.
- **A row that swings about a steady mean counts as settled** (`cycle` in `results.json`, listed in the kit's `cycles.json`): four flat-inside rows at −2.5°, whose lift swings by ±0.002 to ±0.008 about a mean that holds to four digits over 1800 iterations, with settled rows on both sides.

The wall: every section's mesh keeps its layers on all faces and has a mean wall y⁺ of 1.26–1.44 at 0° (all 39 sections, and both gates). What that wall costs against a finer one (drag 4–5 % low, ends 0.5–1.5° early) is in `../../section-gate/`, section 4.

The table is built from this record (`scripts/build_section_table_v1.py`, its default since 2026-11-22; `../table-v1-nodes.md` has the table at every section).

## Behind an end: two controls (2026-11-22)

A march stops three rows past an end. Two sections were run on from their last settled row, on the same mesh and stream (`controls/`), to see what the table is carrying there: the thin symmetric section upward to 12°, the flat-inside section downward to −12°.

No row behind an end settles. The steady solver swings: inside the last 300 iterations lift ranges over more than its own mean (at 7° on the symmetric section from −0.5 to +1.2), and the means of the last three windows differ by up to 0.3. The one exception is the flat-inside row at −5°, a bounded cycle (−0.154 … −0.090 about −0.118). The numbers below are the means the driver reports and say where the flow is going, not what it is.

| symmetric, t/c 0.046, Re 5.7e5 | 5° (settled) | 6° | 7° | 8° | 9° | 10° | 12° |
|---|---|---|---|---|---|---|---|
| c_l, control | 0.516 | 0.59 | 0.72 | 0.66 | 0.79 | 0.90 | 1.00 |
| c_l, table v1 | 0.516 | 0.55 | 0.63 | 0.64 | 0.64 | 0.65 | 0.69 |
| c_d, control | 0.0307 | 0.048 | 0.079 | 0.098 | 0.121 | 0.157 | 0.227 |
| c_d, table v1 | 0.0304 | 0.050 | 0.076 | 0.101 | 0.124 | 0.144 | 0.179 |

| flat inside, t/c 0.092, Re 5.7e5 | −4.5° (settled) | −5° | −6° | −7° | −8° | −10° | −12° |
|---|---|---|---|---|---|---|---|
| c_l, control | −0.072 | −0.118 | −0.20 | −0.34 | −0.32 | −0.35 | −0.45 |
| c_l, table v1 | −0.073 | −0.118 | −0.23 | −0.33 | −0.41 | −0.49 | −0.54 |
| c_l on the section's line | −0.05 | −0.10 | −0.21 | −0.31 | −0.42 | −0.63 | −0.85 |
| c_d, control | 0.0479 | 0.0548 | 0.070 | 0.095 | 0.105 | 0.134 | 0.172 |
| c_d, table v1 | 0.0479 | 0.0553 | 0.073 | 0.091 | 0.114 | 0.157 | 0.194 |

- **A thin symmetric section has no highest lift in reach.** Behind its end the lift goes on at about two thirds of the slope, to 1.0 at 12°, while the drag is 2 to 7 times what it was at the end: a bubble from the nose that grows with the angle (thin-aerofoil stall). The end of its attached range is where the drag steps, not where it stops lifting. The table has the drag within 5 % to 9° and 21 % low at 12°; its lift levels off at 0.64–0.69, which is v0's shape from three degrees behind the end.
- **A flat inside face driven from its curved side** keeps its lift line two degrees past the lower end (to −7°) and holds at −0.33 … −0.45 from there, half of the line at −12°. The table follows to −7° and reads 0.09–0.14 more lift (negative) from −8° on, and 8–17 % more drag.
- Neither changes a number the model uses today: the knee is read inside the attached range (`SectionPolar.cl_limit`), and every strip of a blade going straight or in its turn works inside it. They bear on two things that are open: the knee of a thin symmetric blade (`docs/GEN3-PLAN.md` 2b.1), and the fin on the outside of a turn, which the lattice keeps on its lift line where set CFD has it leave (`../../phase2b/twin-set/`).
