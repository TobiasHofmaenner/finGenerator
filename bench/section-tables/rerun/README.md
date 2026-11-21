# The sections again, on the converged recipe (running since 2026-11-20)

The referee's sections of `../results.json`, `../thin-cambered/` and `../third-batch/` were meshed from an outline with a corner at the leading edge (`../nose/`). These are the same sections on the recipe that converges: exact outline, nose cells of 0.023 mm on the first 2 % of chord, faces 0.375 mm, 13 layers from 9.3 µm (scaled with Reynolds number), domain ±20 chords, chord 0.12 m, trailing edge 1.2 mm.

- `results.json`: every section's plan and rows, with `complete` and the machine it ran on. Written by the collector (`~/bench-results/sections2/collect.py`) and replaced as sections finish.
- `ends.md`: where each attached range ends. A row is past an end when it did not settle within 3000 iterations or has more than four times the section's lowest drag; the end lies between the last row inside and the first past it (a quarter degree apart where the march bisected).

Each section runs a fixed list of angles inside its range and two marches: outward in half degrees from near the old end until two rows in a row (three at the lower end) are past it, then one row halfway into the bracket. Symmetric sections run at positive angles only.

Sections (31): the table's twelve cambered ones at Re 5.7e5, and 4.5 % / t/c 0.12, 3 % and 4.5 % / t/c 0.16 (searches have gone there with no referee behind them); 3 % / t/c 0.07 also at 2.8e5 and 1.4e5; 4.5 % / t/c 0.092 also at 9.7e5 and 1.4e5; symmetric at t/c 0.046, 0.066, 0.080, 0.090, 0.120 and 0.160, t/c 0.090 also at 2.8e5 and 1.4e5; flat inside with a nose-corner radius of 0.5 mm (`../flat-corner/`) at t/c 0.050, 0.065, 0.092 and 0.120, and t/c 0.092 also at 2.8e5 and 1.4e5.

Read by `scripts/build_section_table_v1.py` (complete sections only). What a row is known to: lift 0.01, drag 1 %, an end half a degree (`../nose/`, section 4).
