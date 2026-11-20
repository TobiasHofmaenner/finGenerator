# Mesh level 5 on the best fin of the first table-v1 searches (2026-11-20)

The blade three of six neutral searches on section table v1 ended on (`docs/MODEL-EXTENSION.md`, "Section table v1"): 10 004 mm², depth 140 mm, base 104 mm, 4.2 % camber on t/c 0.089 at the root and 0.093 at the tip (`fins/side-v1-neutral.json`). Same mesh and driver as `../mesh-level-5/`; lattice columns from `scripts/lattice_vs_polar.py <this folder> --table=v1` (perfect mirror), with the lattice as corrected on 2026-11-20 (control points, far-wake induced drag) and table v1 with five cambered nodes.

| own incidence ° | level 5: C_L, drag N | lattice, table v1: C_L, drag N | lattice, table v0 N |
|---|---|---|---|
| −4.5 | −0.010, 6.8 † | −0.012, 5.6 | 5.0 |
| −3.5 | +0.058, 5.5 | +0.052, 5.5 | 4.9 |
| −2.5 | +0.123, 5.3 | +0.115, 5.6 | 5.1 |
| 0 | +0.285, 7.1 | +0.275, 7.3 | 6.9 |
| +4 | +0.539, 13.9 | +0.528, 13.8 | 13.4 |
| going straight (mean of −2.5 and −4.5) | **6.1** | 5.6 | 5.0 |

† stopped at the 800-iteration cap on its residuals; the force is steady within 0.01 % over the last 200 iterations. A converged value.

## Reading

- **The thicker section does what the model said.** 6.1 N going straight against 7.7 N for the candidate on t/c 0.074 at the same hold: 1.6 N per fin from thickness, where the model has 0.8 N (5.6 against 6.4).
- **From −3.5° to +4° the model is within 5 %**, lift within 0.011 (model lower).
- **At −4.5° level 5 reads 1.2 N more than the model, and which is nearer is open.** The referee's 4.5 % / t/c 0.092 section is attached from −6° to +12°, so by the 2-D referee this blade is a degree and a half inside its range at −4.5°. `surface-split.md` shows what the 3-D number is made of: friction a third below the referee's, pressure drag above it and rising twice as fast toward −4.5°, no reversed flow. Either the level-5 surface loses suction at the nose (three cells across its radius), or the referee is generous at this end. Two 2-D controls are queued (`bench/section-tables/README.md`).

## On the rebuilt table (2026-11-20, later)

On table v1 rebuilt on twelve cambered sections the lattice reads this blade 5.6 / 5.4 / 5.6 / 7.3 / 13.7 N at −4.5 / −3.5 / −2.5 / 0 / +4° (level 5: 6.8 / 5.5 / 5.3 / 7.1 / 13.9): unchanged within 0.1 N, the −4.5° row included. Its hold under the strip criterion went from 0.90 to 0.83 (knee 7.9°). The first of the two controls is in: with the surface one level finer the referee keeps two thin sections attached where it had them separated, so of the two readings above, "the level-5 surface is too coarse at the nose" has gained and "the referee is generous at this end" has lost. A check one level finer again is queued (`docs/MODEL-EXTENSION.md`, "Twelve cambered sections…", section 6).
