# The sections again, on the converged recipe: the old inlet (2026-11-20/21, closed at 29 of 35)

**Superseded as the table's source on 2026-11-21 by `../rerun-held/`** (the same sections on a held stream; see "The stream" below). What this record established about the recipe, the marching, soft upper ends, wall layers and the two lost meshes holds there too.

The referee's sections of `../results.json`, `../thin-cambered/` and `../third-batch/` were meshed from an outline with a corner at the leading edge (`../nose/`). These are the same sections on the recipe that converges: exact outline, nose cells of 0.023 mm on the first 2 % of chord, faces 0.375 mm, 13 layers from 9.3 µm (scaled with Reynolds number), domain ±20 chords, chord 0.12 m, trailing edge 1.2 mm.

- `results.json`: every section's plan and rows, with `complete` and the machine it ran on. Written by the collector (`~/bench-results/sections2/collect.py`) and replaced as sections finish.
- `ends.md`: where each attached range ends. A row is past an end when it did not settle within 3000 iterations or has more than four times the section's lowest drag; the end lies between the last row inside and the first past it (a quarter degree apart where the march bisected).

Each section runs a fixed list of angles inside its range and two marches: outward in half degrees from near the old end until two rows in a row (three at the lower end) are past it, then one row halfway into the bracket. Symmetric sections run at positive angles only.

Sections (35): the table's eleven cambered ones at Re 5.7e5, and 4.5 % / t/c 0.12, 3 % and 4.5 % / t/c 0.15 (searches have gone there with no referee behind them); 3 % / t/c 0.07 and 3 % / t/c 0.05 also at 2.8e5 and 1.4e5; 4.5 % / t/c 0.092 also at 9.7e5 and 1.4e5; symmetric at t/c 0.046, 0.066, 0.080, 0.090, 0.120 and 0.150, t/c 0.090 also at 2.8e5 and 1.4e5, t/c 0.046 also at 1.4e5; flat inside with a nose-corner radius of 0.5 mm (`../flat-corner/`) at t/c 0.050, 0.065, 0.092 and 0.120, and t/c 0.092 also at 2.8e5 and 1.4e5.

The three thin sections at lower Reynolds number were added on 2026-11-21: a fin's tip strips work at t/c 0.04–0.06 and Reynolds numbers of 1–2 × 10⁵, and a table built from the first ten sections gave such sections about ±3° of range by a trend read at t/c 0.07 and 0.092.

Two corrections on 2026-11-21, after four sections stopped with errors:

- **t/c 0.15, not 0.16.** The three thickest sections were planned at t/c 0.16; fingen draws no section above 0.15 (`FoilParams`), and the driver refused them. They run at 0.15, the thickest a fin's root can be.
- **Seven wall layers at Re 1.4e5.** The driver's stack has at least ten layers, which at Re 1.4e5 is 0.86 mm against 0.45 mm at the other Reynolds numbers. On the 0.5 mm corner of the flat inside face the mesher dropped it (13 % kept) and the driver's layer check refused the mesh. The sections at Re 1.4e5 that had not run yet (flat inside t/c 0.092, symmetric t/c 0.090 and 0.046, 3 % / t/c 0.05) use seven layers (0.43 mm). The two that had (3 % / t/c 0.07, 4.5 % / t/c 0.092) kept 99.8 % of ten; `ctl-camb3-tc070-re140k-l7` repeats six rows of the first with seven.

**An upper end can be soft** (read 2026-11-21 from the force histories, at 22 of 35). "Not settled" covers two things. A section with a sharp nose stall is separated in the first row past its end: lift down by a sixth or more, drag three to ten times higher (3 % / t/c 0.07: 1.324 at +10.0°, 1.101 at +10.25°). A thick or strongly cambered section stalls from the trailing edge, and its first rows past the end are a small steady oscillation around a mean that no longer moves: 4.5 % / t/c 0.092 at Re 1.4e5 holds a lift of 1.3725–1.3728 from iteration 1500 to 3000 at +11.5°, swinging by ±0.6 % in lift and ±3 % in drag. The driver's rule (the last 100 iterations within 0.6 % of the lift) counts that as not settled, so the end is put where the flow stops being steady, while lift still rises:

| section | end by the rule | rows past it with lift still rising | then |
|---|---|---|---|
| 4.5 % / t/c 0.092, Re 1.4e5 | +11.0…+11.25° (1.351) | 1.363, 1.373, 1.377 at +11.25, +11.5, +12.0° | march stopped |
| 4.5 % / t/c 0.15 | +13.0…+13.25° (1.586) | 1.597, 1.608, 1.623, 1.624 at +13.25, +13.5, +14.0, +14.5° | 1.482, 1.456 at +15.0, +15.5° (the three rows added) |
| 4.5 % / t/c 0.12 | +13.75…+14.0° (1.663) | 1.672 at +14.0° | 1.603 at +14.5° |
| 4.5 % / t/c 0.092 | +13.75…+14.0° (1.657) | 1.661 at +14.0° | 1.580 at +14.5° |
| 4.5 % / t/c 0.092, Re 9.7e5 | +14.5…+14.75° (1.737) | 1.743 at +14.75° | 1.728, 1.568 at +15.0, +15.5° |
| 3 % / t/c 0.12 | +14.0…+14.25° (1.567) | 1.571, 1.580 at +14.25, +14.5° | 1.046 at +15.0° |
| flat inside t/c 0.12 | +13.0…+13.25° (1.664) | 1.672, 1.678 at +13.25, +13.5° | 1.493 at +14.0° |

- **The table is not affected at the sections.** The builder takes every row, inside and past the ends, and a polar's break is read off its lift curve (`SectionPolar.alpha_break_deg`: the slope down to 30 % of the linear one), not off the end. Checked on the build at 22 sections: the table returns every row past an upper end to 0.001 in lift.
- **The end itself is early by a quarter to half a degree on these sections**, and by a degree or more on the first two, where the march ended before the mean lift had turned. Both run three more rows (to +13.5° and +15.5°). Lower ends are not soft at Re 5.7e5 (drag 1.3–1.9 times the lowest in the last row inside, 4–9 times in the first past it); on thin sections and at Re 1.4–2.8e5 drag climbs by 40–100 % in the first row past the end and keeps climbing.

**The first cell's height** is the one mesh direction `../nose/` did not vary. Its centre sits at one wall unit over most of the section and at 4–5 on the first 0.5 % of chord near an upper end (read off the gate's rows at 12° and 13.25°; the largest values a row reports, 10–25, are the four cells on the trailing edge's base, which carry no layers). Two controls with half the first cell, `ctl-naca0012-re700k-y1` and `ctl-camb3-tc070-re570k-y1`, run on the held stream with `../rerun-held/`; their result is recorded in `../../section-gate/`.

**Seven layers against ten at Re 1.4e5** (`ctl-camb3-tc070-re140k-l7`, six rows of 3 % / t/c 0.07): both ends fall between the same rows (−4.5…−4.75° and +8.25…+8.5°). Lift is 0.014 higher at 0° and +4° (0.325 against 0.311, 0.737 against 0.722) and drag 1.4 % lower; at the two last rows inside the ends lift differs by 0.010–0.014 the other way. So at Re 1.4e5 the sections on seven layers and those on ten differ by about 0.014 in lift, more than the 0.01 the mesh controls at Re 5.7e5 gave, and their ends are comparable.

**Two sections lost their layers at a threshold** (symmetric t/c 0.09 at Re 2.8e5 and 1.4e5, 2026-11-21). In the mesher's first layer pass 20 of 200 000 faces had an interpolation weight below its floor of 0.05; it took the layers off those faces, which made more such faces beside them, and after its passes 12.5 % of the stack was left. The driver refused both meshes. The same section at Re 5.7e5 had no such face. Both run again with the floor at 0.02 (`min_face_weight`, a new option of the driver; every other section keeps 0.05): Re 2.8e5 kept 99.9 % of ten layers.

**The stream, and why this record stops at 29 sections** (2026-11-21, `../../section-gate/`). The referee's inlet carried 5 % turbulence with a length of a tenth of the chord, the 3-D recipe's rule, which nobody had varied. On the NACA 0012 gate lift is the same in every stream up to the break; the old inlet's drag is 5–12 % above what tripped tunnels give and its break a quarter to half a degree later than in a quiet or a held stream. The table moves to a held stream, and all 35 sections are rerun on it in `../rerun-held/`, which also compares the two row by row. This record stays as the old-inlet side of that comparison: 29 sections complete. Not run on the old inlet: 1 % / t/c 0.07, flat inside t/c 0.065, 3 % / t/c 0.05 at Re 2.8e5 and 1.4e5, symmetric t/c 0.046 at Re 1.4e5, all but one row of 3 % / t/c 0.08, and the three rows added to 4.5 % / t/c 0.092 at Re 1.4e5. Two of the Re 1.4e5 sections here have ten wall layers and the others seven; on the held stream all have seven.

Two gates run with the batch and are kept out of this record: NACA 0012 at Re 7e5 against [SK81] and NACA 4415 at Re 7.5e5 against [Hof96] (`../../section-gate/`).

Read by `scripts/build_section_table_v1.py` (complete sections only). What a row is known to: lift 0.01, drag 1 %, an end half a degree (`../nose/`, section 4).
