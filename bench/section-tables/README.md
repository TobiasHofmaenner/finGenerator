# Section tables — resolved-wall 2-D RANS of fingen's foil families (in progress)

The referee for `fingen.sections` (table v0: NeuralFoil, boundary layer tripped) and the data for table v1. Driver `finGenerator-cfd/scripts/section_polar.py`, resolved wall (first cell at y+ ≈ 1), domain ±20 chords, chord 0.12 m, trailing edge 1.2 mm — the recipe that passed the [SK81] NACA 0012 gate (`bench/section-gate/`). Plan: flat inside (t/c 0.05 / 0.07 / 0.092 / 0.12), symmetric (0.046 / 0.066 / 0.09) and cambered (t/c 0.092 with 2 / 3 / 3.5 % camber) at Re 5.7e5 and 2.8e5, −10…+16°; a second batch adds cambered sections at t/c 0.07 (2 / 3 / 4.5 %) and 4.5 % at t/c 0.092, the corner a camber-free search goes to.

`results.json` is a snapshot of the running job (2026-11-19: 2 of 20 sections finished, a third under way) and is replaced as sections finish. Read it with

    uv run python scripts/section_table_check.py

which prints every finished section beside the shipped table. First reading in `docs/MODEL-EXTENSION.md`, "Section table v0 against resolved-wall RANS".
