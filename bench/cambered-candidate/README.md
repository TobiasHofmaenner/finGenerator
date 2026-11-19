# Cambered candidate — the first fin the lattice model chose with camber free (isolated CFD, 2026-11-19)

Question: with the side blade allowed to choose its camber (`RiderSpec.side_foil = "cambered"`) and scored by the lattice model (`hydro_model = "lattice"`), the search for the 60 kg pro's big-wave spec returned the shipped planform with a thin, strongly cambered section — 4.3 % camber at 40 % chord, t/c 0.074, tip factor 1.12, 10 054 mm² (`fins/side-cambered-candidate.json`). The model read it at 5.4 N going straight against 14.9 N for the shipped flat-inside fin. Does CFD agree?

Isolated fin on the symmetry plane, 8.5 m/s, level-2 RANS with wall functions, driver `finGenerator-cfd/scripts/polar_angles.py`; plan and raw results beside this file. The table is `scripts/lattice_vs_polar.py bench/cambered-candidate bench/foil-family`: the same blades solved by `bladehydro.point` at the CFD's speed and angles.

| own incidence ° | candidate 4.3 %: CFD N | lattice N | ratio | 3 % camber, shipped planform: CFD N | lattice N | ratio | flat inside, shipped: CFD N | lattice N | ratio |
|---|---|---|---|---|---|---|---|---|---|
| −4.5 | 12.0 | 5.6 | 0.47 | 8.8 | 4.9 | 0.55 | 16.1 | 17.1 | 1.06 |
| −3.5 (straight at the 3.5° toe) | 9.1 | 5.1 | 0.56 | 6.9 | 4.5 | 0.64 | 13.4 | 14.8 | 1.11 |
| −2.5 | 7.8 | 5.2 | 0.67 | 6.0 | 4.4 | 0.73 | 11.2 | 12.8 | 1.14 |
| 0 | 7.9 | 6.7 | 0.85 | 5.8 | 5.4 | 0.92 | 8.8 | 9.8 | 1.11 |
| +4 | 13.4 | 12.5 | 0.94 | 10.2 | 9.9 | 0.98 | 12.7 | 11.7 | 0.92 |
| +8 | 26.0 | 21.9 | 0.84 | 22.3 | 18.1 | 0.81 | 24.8 | 19.4 | 0.78 |
| +12 | 45.6 | 34.6 | 0.76 | 41.2 | 30.0 | 0.73 | 43.3 | 31.1 | 0.72 |
| +16 | 70.4 | 53.8 | 0.76 | 66.0 | 48.2 | 0.73 | 66.5 | — | — |

Lift coefficient, candidate: CFD −0.006 / +0.054 / +0.116 / +0.262 / +0.504 at −4.5 / −3.5 / −2.5 / 0 / +4°; lattice −0.003 / +0.058 / +0.118 / +0.268 / +0.507. Zero-lift angle −4.4° in both. Maximum lift in the CFD polar 0.79 (flat inside 0.83, 3 % camber 0.72; wall-function values, lower bounds).

## Reading

- **Lift: the model is right.** Within 0.005 in CL from −4.5 to +4° on a fin it had never been compared with, zero-lift angle included.
- **Drag at negative incidence: the model and this CFD disagree by 35–55 %.** Going straight at the production toe the candidate costs 9.1 N in the level-2 CFD and 5.1 N in the model; the 3 % camber fin 6.9 N against 4.5 N. The 3 % camber runs converged at these angles (155–405 iterations), so this is not solver noise. At 0…+4° the same fins agree within 2–15 %, and the flat-inside fin agrees within 6–14 % at the negative angles — the gap is specific to cambered blades run below their zero-lift angle.
- **Two causes, found the same night** (`docs/MODEL-EXTENSION.md`, "The cambered candidate was a second exploit"; data in `bench/section-tables/thin-cambered/` and `mesh-recipe/`):
  1. *The model's section table is too generous for thin cambered sections.* Resolved-wall 2-D RANS has the 3 % camber section attached from −6° to +10° at t/c 0.092 (as the table says) but only from −3.5° to +8° at t/c 0.070, at 3 and at 4.5 % camber; the table lets the thin ones run to −4.5…−5.25°. Going straight at the 3.5° toe a side fin works at −2.5 to −4.5°. With the RANS / table ratios applied strip by strip (`scripts/rans_fed_lattice.py`) the candidate reads 10.1 / 7.4 / 5.9 N at −4.5 / −3.5 / −2.5° instead of 5.6 / 5.1 / 5.2 N, and **8.0 N going straight instead of 5.4 N**; the 3 % camber fin on the thicker shipped planform 5.5 N instead of 4.6 N.
  2. *The wall-function mesh reads cambered fins high below about −3°.* The same sections run in 2-D on the 3-D recipe (wall functions, surface cells chord/160 or chord/320) show 26–42 % more drag at −3.5° than on the resolved wall, and nothing extra at −2.5° or 0° (4.5 % camber: +21 % at −2.5°). Wall functions cannot hold the suction peak on the inside of the nose — the weakness `docs/CFD-BENCH.md` records for maximum lift, mirrored. So the level-2 and level-3 numbers in the tables here are upper readings at −3.5 and −4.5°, not a referee.
- **Adding prism layers does not remove it** (`mesh-level-3/`: the 3 % camber fin again, level 3 = level 2 plus four layers, same surface cells):

| own incidence ° | level 2: C_L | drag N | level 3: C_L | drag N | lattice model N | 2-D section cd (resolved wall) |
|---|---|---|---|---|---|---|
| -4.5 | -0.089 | 8.8 | -0.102 | 9.9 | 4.9 | 0.0146 |
| -3.5 | -0.030 | 6.9 | -0.043 | 7.7 | 4.5 | 0.0137 |
| +0.0 | +0.166 | 5.8 | +0.164 | 6.0 | 5.4 | 0.0130 |

  Level 3 reads 10–12 % more drag than level 2 at the negative angles and 4 % more at 0°, so the excess is not a missing-layer artefact. Both levels use wall functions, which is what the 2-D check above identifies.
- **The cambered foil still beats the flat one going straight by a wide margin:** 8.0 N (candidate) or 5.5 N (3 % camber) with referee sections, against 14.9 N for the flat inside face by the same model (13.4 N in CFD, where the flat face separates at its corner on any mesh). What changed is the choice among cambered fins: more camber buys hold and, at the fixed toe, costs drag going straight — 2.5 N per fin between these two blades, where the table had said 0.8 N.

## Consequence

The candidate is withdrawn as a design: it sat on the edge of an attached range the table had drawn a degree too wide. `side_foil = "cambered"` stays opt-in and no cambered fin is exported from the lattice model until section table v1 carries the referee's ends of the attached range (`bench/section-tables/`, third batch queued). A first search with the RANS ratios applied lands on about 11 800 mm², depth 121 mm, 2.3–2.6 % camber and 6.1 N going straight — outside the referee's nodes and pinned to its −3.5° sample, so a pointer to the sections still to run, not a fin. The flat-inside numbers and every lift number are unaffected.
