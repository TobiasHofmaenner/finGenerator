# Section tables — resolved-wall 2-D RANS of fingen's foil families (in progress)

The referee for `fingen.sections` (table v0: NeuralFoil, boundary layer tripped) and the data for table v1. Driver `finGenerator-cfd/scripts/section_polar.py`, resolved wall (first cell at y+ ≈ 1), domain ±20 chords, chord 0.12 m, trailing edge 1.2 mm — the recipe that passed the [SK81] NACA 0012 gate (`bench/section-gate/`).

| folder | what | state on 2026-11-20 |
|---|---|---|
| `results.json` | main plan: flat inside (t/c 0.05 / 0.07 / 0.092 / 0.12), symmetric (0.046 / 0.066 / 0.09), cambered at t/c 0.092 (2 / 3 / 3.5 %), each at Re 5.7e5 and 2.8e5, −10…+16° | 2 of 20 sections finished, paused behind the batches below |
| `thin-cambered/` | cambered at t/c 0.07 (2 / 3 / 4.5 %) and 4.5 % at t/c 0.092 — the corner a camber-free search goes to | finished; quarter-degree steps at both ends of each range are being added (edge pass) |
| `mesh-recipe/` | three of those sections again on the 3-D fin recipe (wall functions, surface cells chord/80 … chord/640): how much of a 3-D polar is the mesh | finished |
| third batch (running after the edge pass) | 2 and 3 % camber at t/c 0.05, 1 % at t/c 0.07, 3 % at t/c 0.12, 3 % at t/c 0.07 at Re 2.8e5 | – |
| controls (queued) | the referee one surface level finer (chord/1280 at the nose) around the lower ends of three sections; the 4.5 % / t/c 0.092 section at Re 9.7e5 with wall functions on mesh level 5's cells, beside a resolved partner | – |
| `table-v1-nodes.md` | section table v1 against every finished section (written by `scripts/build_section_table_v1.py --report=…`) | five cambered nodes, one flat-inside |

Each `results.json` is a snapshot of a running or finished job and is replaced as sections finish. Read them with

    uv run python scripts/section_table_check.py     # every finished section beside the table, angle by angle
    uv run python scripts/section_edges.py           # where each section's attached range ends, RANS against table
    uv run python scripts/rans_fed_lattice.py        # the lattice with RANS/table ratios applied, against the 3-D polars

Readings in `docs/MODEL-EXTENSION.md`: "Section table v0 against resolved-wall RANS" (the first two sections) and "The cambered candidate was a second exploit" (the thin sections, the mesh-recipe check and what they do to the search).

## What stands so far

- Inside the attached range the table is 5–10 % low in drag (22 % for the flat-inside section at its minimum) and 4–5 % high in lift slope; zero-lift angles agree within 0.2°.
- **The ends of the attached range are where the table is wrong.** 3 % camber at t/c 0.092: attached from −6° to +10° in RANS, and the table agrees within its sampling. At t/c 0.070 (3 and 4.5 % camber) the range is −3.5° to +8°; the table has it reach −4.5…−5.25° and +10°. A side fin going straight at the 3.5° toe works at −2.5 to −4.5°.
- **4.5 % camber at t/c 0.092 is attached from −6° to +12°** (cd 0.0156 at −4.5°, 0.0178 at −6°, cl 1.49 at +12°); 2 % camber at t/c 0.070 from −4.5° to +6°. Thickness moves the lower end by about 2.5° between t/c 0.070 and 0.092, camber between 3 and 4.5 % hardly; the knee moves with both.
- **What the drag consists of** (`finGenerator-cfd/scripts/section_surface.py` on the stored cases; `bench/cambered-candidate/mesh-level-5-v1-neutral/surface-split.md`): at −2.5° about 70–75 % friction. Toward the lower end the pressure part grows and the friction part falls before any flow reverses (4.5 % / t/c 0.092: pressure 0.0040 → 0.0062 → 0.0093 at −2.5 / −4.5 / −6°, no reversed shear); past the end the shear is reversed over a third of the inside face (3 % / t/c 0.070 at −4.5°). Around the nose there are ten to thirteen faces within the first 1 % of chord (both faces together) and y+ stays below 4.
- Past either end the RANS runs do not settle (3000 iterations): they say the flow has separated, not what it costs. The table's drag there is a quarter to a half of those values.
