# Section tables — resolved-wall 2-D RANS of fingen's foil families (in progress)

**2026-11-21: the sections in `results.json`, `thin-cambered/` and `third-batch/` were meshed from an outline with a corner at the leading edge (`nose/`). Their ends of the attached range are about two degrees narrow at each end, and table v1 with them. Everything below is the record of that referee; the rerun on the converged recipe replaces it.**

The referee for `fingen.sections` (table v0: NeuralFoil, boundary layer tripped) and the data for table v1. Driver `finGenerator-cfd/scripts/section_polar.py`, resolved wall (first cell at y+ ≈ 1), domain ±20 chords, chord 0.12 m, trailing edge 1.2 mm — the recipe that passed the [SK81] NACA 0012 gate (`bench/section-gate/`).

| folder | what | state on 2026-11-20 |
|---|---|---|
| `results.json` | main plan: flat inside (t/c 0.05 / 0.07 / 0.092 / 0.12), symmetric (0.046 / 0.066 / 0.09), cambered at t/c 0.092 (2 / 3 / 3.5 %), each at Re 5.7e5 and 2.8e5, −10…+16° | 2 of 20 sections finished, paused behind the batches below |
| `thin-cambered/` | cambered at t/c 0.07 (2 / 3 / 4.5 %) and 4.5 % at t/c 0.092 — the corner a camber-free search goes to | finished, with quarter- to half-degree steps added at both ends of each range (edge pass, `plan-edge.json`) |
| `mesh-recipe/` | three of those sections again on the 3-D fin recipe (wall functions, surface cells chord/80 … chord/640): how much of a 3-D polar is the mesh | finished |
| `third-batch/` | 4.5 and 3 % camber at t/c 0.08, 2 and 3 % at t/c 0.05, 1 % at t/c 0.07, 3 % at t/c 0.12, 3 % at t/c 0.07 at Re 2.8e5; half-degree steps toward the lower end, one-degree steps toward the knee | finished |
| `controls/` | the referee one surface level finer (c/1280) around the lower ends of three sections; the 4.5 % / t/c 0.092 section at Re 9.7e5 resolved, and with wall functions on the cells of 3-D mesh levels 5 and 4. NOT read by the table builder | finished 2026-11-20; its finding on the referee's lower ends is superseded by `nose/` |
| `nose/` | why the referee did not converge at the nose: the outline handed to the mesher (100 points, two splines meeting at the leading edge), and the recipe that does converge (exact outline, cells of one size on the nose). NOT read by the table builder | finished 2026-11-21: **every section above was run on the old outline and has its attached range about two degrees narrow at each end; all are being rerun** |
| `rerun/` | every cambered and symmetric section again on the converged recipe (`nose/`), each end of the attached range found by marching in half degrees and bisecting; the flat-inside family with a nose-corner radius of 0.5 mm; three Reynolds numbers (1.4e5 / 2.8e5 / 5.7e5, and 9.7e5) at two sections. `ends.md` lists where each range ends. THE sections table v1 is rebuilt on | running: see `ends.md` |
| `flat-corner/` | the flat-inside section (t/c 0.092) with nose-corner radii of 0.1 … 1.0 mm at the angles a side fin sees going straight. NOT read by the table builder | finished |
| `table-v1-nodes.md` | section table v1 against every finished section (written by `scripts/build_section_table_v1.py --report=…`) | twelve cambered nodes at eleven sections, one flat-inside |

Each `results.json` is a snapshot of a running or finished job and is replaced as sections finish. Read them with

    uv run python scripts/section_table_check.py     # every finished section beside the table, angle by angle
    uv run python scripts/section_edges.py           # where each section's attached range ends, RANS against table
    uv run python scripts/rans_fed_lattice.py        # the lattice with RANS/table ratios applied, against the 3-D polars

Readings in `docs/MODEL-EXTENSION.md`: "Section table v0 against resolved-wall RANS" (the first two sections) and "The cambered candidate was a second exploit" (the thin sections, the mesh-recipe check and what they do to the search).

## What stands so far

- Inside the attached range the table is 5–10 % low in drag (22 % for the flat-inside section at its minimum) and 4–5 % high in lift slope; zero-lift angles agree within 0.2°.
- **The ends of the attached range are where the table is wrong.** A side fin going straight at the 3.5° toe works at −2.5 to −4.5°; at t/c 0.070 the referee ends the range at −3.8° (4.5 % camber) and −4.3° (3 %), table v0 at −4.6° and −5.2°. All twelve cambered sections are in the next section.
- **4.5 % camber at t/c 0.092 is attached from −6° to +12°** (cd 0.0156 at −4.5°, 0.0178 at −6°, cl 1.49 at +12°); 2 % camber at t/c 0.070 from −4.5° to +6°. Thickness moves the lower end by about 2.5° between t/c 0.070 and 0.092, camber between 3 and 4.5 % hardly; the knee moves with both.
- **What the drag consists of** (`finGenerator-cfd/scripts/section_surface.py` on the stored cases; `bench/cambered-candidate/mesh-level-5-v1-neutral/surface-split.md`): at −2.5° about 70–75 % friction. Toward the lower end the pressure part grows and the friction part falls before any flow reverses (4.5 % / t/c 0.092: pressure 0.0040 → 0.0062 → 0.0093 at −2.5 / −4.5 / −6°, no reversed shear); past the end the shear is reversed over a third of the inside face (3 % / t/c 0.070 at −4.5°). Around the nose there are ten to thirteen faces within the first 1 % of chord (both faces together) and y+ stays below 4.
- Past either end the RANS runs do not settle (3000 iterations): they say the flow has separated, not what it costs. The table's drag there is a quarter to a half of those values.

## Twelve cambered sections (2026-11-20)

Edge pass and third batch are in; `table-v1-nodes.md` lists every section with the referee's ends, table v0's and table v1's. Ends as `scripts/build_section_table_v1.py` reads them: lower end where cd passes 1.5 × its minimum, upper end where it passes 3 ×.

| t/c | camber % | Re | lower end ° | upper end ° | minimum cd | cl at the last attached row |
|---|---|---|---|---|---|---|
| 0.050 | 2 | 5.7e5 | −3.1 | +6.1 | 0.0119 | 0.65 |
| 0.050 | 3 | 5.7e5 | −2.8 | +6.3 | 0.0123 | 0.76 |
| 0.070 | 1 | 5.7e5 | −5.1 | +6.4 | 0.0121 | 0.75 |
| 0.070 | 2 | 5.7e5 | −4.6 | +7.4 | 0.0123 | 0.93 |
| 0.070 | 3 | 5.7e5 | −4.3 | +8.1 | 0.0126 | 1.13 |
| 0.070 | 3 | 2.8e5 | −4.1 | +8.2 | 0.0139 | 1.10 |
| 0.070 | 4.5 | 5.7e5 | −3.8 | +9.0 | 0.0135 | 1.34 |
| 0.080 | 3 | 5.7e5 | −5.0 | +9.1 | 0.0128 | 1.22 |
| 0.080 | 4.5 | 5.7e5 | −4.6 | +9.8 | 0.0136 | 1.39 |
| 0.092 | 3 | 5.7e5 | −6.1 | +10.2 | 0.0129 | 1.29 |
| 0.092 | 4.5 | 5.7e5 | −6.7 | +11.2 | 0.0137 | 1.49 |
| 0.120 | 3 | 5.7e5 | −8.6 | +12.8 | 0.0141 | 1.42 |

- **Both ends move about a degree per 0.01 of t/c**, over the whole span from 0.05 to 0.12 (3 % camber: lower end −2.8 → −8.6°, upper end +6.3 → +12.8°). Camber moves the upper end by 0.75° per percent and the lower end by 0.35° per percent the other way: more camber, less room below.
- **Reynolds number hardly moves them.** Between 2.8e5 and 5.7e5 (3 % camber, t/c 0.070) the lower end moves by 0.2° and the upper by 0.1°; table v0 moves them by 0.6° and 0.9°. The minimum drag falls by 9 % (v0: 15 %). One pair so far; the section at Re 9.7e5 among the controls is the second.
- **Below the lower end there is a cliff**: the drag goes from 1.2–1.7 × its minimum to 2.3–5 × within one step of the rows (a quarter to half a degree), and the first row past it is the first that does not settle. Table v0 takes a degree for the same rise.
- **Table v0 against the twelve**: lower end 0.4–1.4° too far out (one exception, 4.5 % at t/c 0.092, within 0.1°), upper end 0.1–2.3° late, lift slope 2–4 % high, drag level 1–13 % low.

### Table v1, rebuilt

A blind check came first: the v1 of the day before (five cambered sections, all at t/c 0.070 and 0.092) against the seven new ones, before they were used. Ten of the fourteen ends lay inside the referee's bracket, the other four 0.25–0.5° outside it; v0 had five inside.

Rebuilding on all twelve showed two faults in how v1 was carried between its sections, both invisible to the builder's own report, which checked its formula and not the shipped file:

1. **The table did not contain the referee's Reynolds number.** v0's grid has 4e5 and 8e5; a section at 5.7e5 was read as the plain mean of the two. As long as every section was at 5.7e5 the correction was the same at both and the mean came out right. With one section at 2.8e5 the correction at 4e5 became a blend of every section's, and the 4.5 % / t/c 0.070 section was read with its lower end at −4.25° instead of −3.8° and half the drag at −4.5° (0.028; referee 0.045).
2. **Above 5.7e5 the ends followed v0's Reynolds-number trend**, which is three times the measured one or more. A fin's root strips are at 8e5–9.5e5: their range was read 0.5–1° too wide.

The builder now fits the two ends as the referee has them (a plane in thickness and camber fits them twice as well as it fits their distance from v0), treats Reynolds number apart and keeps the ends where they were last measured outside the measured range, carries the cliff's width as a third mark, ships half-octave Reynolds numbers and quarter-degree angles, and writes its report through `fingen.sections`. Read that way, v1 has every upper end within 0.02°, every lower end within 0.05° (4.5 % / t/c 0.092: 0.2°, between two thickness nodes), the rows past the cliff within 20 % (v0: 40–60 % low there).

**Between its sections** the table is known as well as leaving one out says: predicted from the other eleven, a section's lower end is off by 0.40° rms and its upper end by 0.43° rms. The largest misses are the box's corners — the upper end of t/c 0.12 comes out 1.3° early (v0's thickness trend flattens where the referee's does not), the lower end of 4.5 % / t/c 0.092 1.1° early.

**What the warp does not carry**: inside the range the referee's drag rises with lift earlier than v0's, so v1 reads 6–14 % low at +4…+6°; and the referee's drag stays flat right up to the cliff where v0 creeps up, so v1 reads 9–19 % high in the last half degree before the lower end.

## The controls (2026-11-20)

`controls/results.json`; reading in `docs/MODEL-EXTENSION.md`, "Twelve cambered sections…", section 6.

- **Wall functions on level-5 cells separate early.** 4.5 % / t/c 0.092 at Re 9.7e5: drag coefficient 0.0276 at −4.5° against 0.0145 with the resolved wall (and a quarter to a third less drag where attached). The level-5 3-D polars' excess at −4.5° is this.
- **The referee's lower ends are not converged.** One level finer at the surface, the two thin sections stay attached 0.25–1.5° further and the 4.5 % / t/c 0.092 section lets go 0.7–2.2° earlier (separated at −6.0°; the referee has −6.7°). About ± 1° on every lower end in the table above, and less dependence on thickness than it shows.
- **Reynolds number 9.7e5** on the referee recipe: upper end unchanged (11.2°), lower end 0.4° further out, minimum drag 7 % lower.

Until the finer check says which recipe is converged, the lower ends in table v1 are good to about a degree, and no further sections are run on c/640.
