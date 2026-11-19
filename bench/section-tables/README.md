# Section tables — resolved-wall 2-D RANS of fingen's foil families (in progress)

The referee for `fingen.sections` (table v0: NeuralFoil, boundary layer tripped) and the data for table v1. Driver `finGenerator-cfd/scripts/section_polar.py`, resolved wall (first cell at y+ ≈ 1), domain ±20 chords, chord 0.12 m, trailing edge 1.2 mm — the recipe that passed the [SK81] NACA 0012 gate (`bench/section-gate/`).

| folder | what | state on 2026-11-19 |
|---|---|---|
| `results.json` | main plan: flat inside (t/c 0.05 / 0.07 / 0.092 / 0.12), symmetric (0.046 / 0.066 / 0.09), cambered at t/c 0.092 (2 / 3 / 3.5 %), each at Re 5.7e5 and 2.8e5, −10…+16° | 2 of 20 sections finished, paused behind the batches below |
| `thin-cambered/` | cambered at t/c 0.07 (2 / 3 / 4.5 %) and 4.5 % at t/c 0.092 — the corner a camber-free search goes to | 2 of 4 finished |
| `mesh-recipe/` | three of those sections again on the 3-D fin recipe (wall functions, surface cells chord/80 … chord/640): how much of a 3-D polar is the mesh | finished |
| third batch (queued) | quarter-degree steps at both ends of each cambered section's attached range; 2 and 3 % camber at t/c 0.05, 1 % at t/c 0.07, 3 % at t/c 0.12, 3 % at t/c 0.07 at Re 2.8e5 | starts when `thin-cambered` ends |

Each `results.json` is a snapshot of a running or finished job and is replaced as sections finish. Read them with

    uv run python scripts/section_table_check.py     # every finished section beside the table, angle by angle
    uv run python scripts/section_edges.py           # where each section's attached range ends, RANS against table
    uv run python scripts/rans_fed_lattice.py        # the lattice with RANS/table ratios applied, against the 3-D polars

Readings in `docs/MODEL-EXTENSION.md`: "Section table v0 against resolved-wall RANS" (the first two sections) and "The cambered candidate was a second exploit" (the thin sections, the mesh-recipe check and what they do to the search).

## What stands so far

- Inside the attached range the table is 5–10 % low in drag (22 % for the flat-inside section at its minimum) and 4–5 % high in lift slope; zero-lift angles agree within 0.2°.
- **The ends of the attached range are where the table is wrong.** 3 % camber at t/c 0.092: attached from −6° to +10° in RANS, and the table agrees within its sampling. At t/c 0.070 (3 and 4.5 % camber) the range is −3.5° to +8°; the table has it reach −4.5…−5.25° and +10°. A side fin going straight at the 3.5° toe works at −2.5 to −4.5°.
- Past either end the RANS runs do not settle (3000 iterations): they say the flow has separated, not what it costs. The table's drag there is a quarter to a half of those values.
