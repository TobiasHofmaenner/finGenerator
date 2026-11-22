# The sections on the held stream (running since 2026-11-21)

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
- **A row that swings about a steady mean counts as settled** (`cycle` in `results.json`, listed in the kit's `cycles.json`): three flat-inside rows at −2.5°, whose lift swings by ±0.006 about a mean that holds to four digits over 1800 iterations, with settled rows on both sides.

The wall: every section's mesh keeps its layers on all faces and has a mean wall y⁺ of 1.26–1.44 at 0° (all 39 sections, and both gates). What that wall costs against a finer one (drag 4–5 % low, ends 0.5–1.5° early) is in `../../section-gate/`, section 4.

The table (`scripts/build_section_table_v1.py --sections=rerun-held`) is rebuilt from this record when it is complete.
