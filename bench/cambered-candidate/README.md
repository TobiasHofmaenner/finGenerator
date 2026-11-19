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
- **Drag of a cambered section at negative incidence: the model is 35–55 % low.** Going straight at the production toe the candidate costs 9.1 N in CFD, not 5.1 N; the 3 % camber fin 6.9 N, not 4.5 N. The 3 % camber runs converged at these angles (155–405 iterations), so this is not solver noise. At 0…+4° the same fins agree within 2–15 %, and the flat-inside fin agrees within 6–14 % at the negative angles — the gap is specific to cambered sections run below their low-drag range.
- **The search exploited exactly that gap.** In the section table (NeuralFoil, boundary layer tripped) a cambered section's drag is nearly flat from −2.5 to −4.5°, so more camber and a thinner section cost nothing going straight and the optimum ran to 4.3 % camber on t/c 0.074. In CFD more camber on a thinner section costs: 9.1 N against 6.9 N for 3 % camber on t/c 0.092, with the zero-lift angle pushed to −4.4°, past the 3.5° toe.
- **The cambered foil still beats the flat one going straight, by less than modelled:** 9.1 N (candidate) or 6.9 N (3 % camber) against 13.4 N. The 3 % section is the better of the two cambered fins in trim; the candidate holds more lift (0.79 against 0.72).
- **Which side is wrong is not settled by this run.** NeuralFoil's flat-inside drag matched resolved-wall 2-D RANS; for cambered sections at negative incidence the referee is the resolved-wall section runs now on the EPYC (`camb3-tc092`, `camb2-tc092`, `camb35-tc092`, and the corner the search went to: `camb45-tc070`, `camb3-tc070`, `camb45-tc092`, `camb2-tc070`). Until they land, the model's trim drag of any cambered blade is a lower bound and its preferred camber is not a design.

## Consequence

`side_foil = "cambered"` stays opt-in and no cambered fin is exported from the lattice model before the section table carries RANS data for cambered sections at negative incidence (table v1). The flat-inside numbers and every lift number are unaffected.
