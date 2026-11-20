# The four-fin set on mesh level 5: the mesh was not it, the stand-in's foil is part of it (2026-11-20)

Question, left by `../quad-level2/`: our outside rail carries 23–31 % less than [Falk20]'s and our fins have twice the drag going straight. Is that mesh level 2 letting go early on a fin that takes the flow on its foiled face?

Run: the same layout and the same stand-in fin on mesh level 5 at 5, 10 and 15° (`finGenerator-cfd/scripts/falk_quad.py --level=5 --angles=10,15,5`, EPYC `~/bench-results/falkquad/level5`). Rows in `falk-quad.md`, data in `falk-quad.json`.

| leeway ° | fin | C_L level 2 | C_L level 5 | C_L [Falk20] | C_D level 2 | C_D level 5 | C_D [Falk20] |
|---|---|---|---|---|---|---|---|
| 5 | front inside | 0.290 | 0.289 | 0.210 | 0.027 | 0.025 | 0.030 |
| 5 | front outside | 0.242 | 0.243 | 0.260 | 0.079 | 0.078 | 0.040 |
| 5 | rear inside | 0.176 | 0.175 | 0.240 | 0.030 | 0.028 | 0.035 |
| 5 | rear outside | 0.156 | 0.155 | 0.070 | 0.064 | 0.062 | 0.030 |
| 10 | front inside | 0.562 | 0.565 | 0.460 | 0.052 | 0.051 | 0.050 |
| 10 | front outside | 0.273 | 0.278 | 0.565 | 0.124 | 0.124 | 0.115 |
| 10 | rear inside | 0.366 | 0.368 | 0.410 | 0.051 | 0.050 | 0.055 |
| 10 | rear outside | 0.306 | 0.307 | 0.190 | 0.118 | 0.117 | 0.045 |
| 15 | front inside | 0.751 | 0.862 | 0.730 | 0.119 | 0.111 | 0.100 |
| 15 | front outside | 0.296 | 0.300 | 0.585 | 0.166 | 0.166 | 0.190 |
| 15 | rear inside | 0.588 | 0.567 | 0.610 | 0.098 | 0.097 | 0.110 |
| 15 | rear outside | 0.371 | 0.373 | 0.375 | 0.170 | 0.169 | 0.105 |

| leeway ° | inside rail, front + rear: level 5 / theirs | outside rail: level 5 / theirs | mean drag of the four: level 5 / theirs |
|---|---|---|---|
| 5 | 0.464 / 0.450 (+3 %) | 0.399 / 0.330 (+21 %) | 0.048 / 0.034 |
| 10 | 0.933 / 0.870 (+7 %) | 0.586 / 0.755 (−22 %) | 0.085 / 0.066 |
| 15 | 1.430 / 1.340 (+7 %) | 0.673 / 0.960 (−30 %) | 0.136 / 0.126 |

## Reading

- **Level 5 repeats level 2.** Eleven of the twelve lift values move by 2 % or less and no drag value by more than 0.008. The one that moves is the front inside fin at 15° (0.75 to 0.86), a fin at 11.5° of own incidence, past its knee on the coarse mesh and not on the fine one. The outside front fin stops at 0.28–0.30 on both. So the suspicion of `../quad-level2/` is not confirmed — and not cleared either, because level 5 shares what makes a mesh let go early there (wall functions and two cells per nose radius, `bench/section-tables/`).
- **The stand-in's foil is too thick, and that explains the working rail's split.** The two front fins see the same leeway with the toe added on one and subtracted on the other. Read as one lift line, their front pair has a slope of 0.047–0.051 per degree and a zero-lift angle of −3.0° (at 5°) and −2.5° (at 10°). Ours at 5° has 0.053 per degree and −3.9°, which is exactly what the model gives the stand-in's flat-inside foil of t/c 0.09 (−3.95°). Their fin behaves like a flat-inside foil of t/c 0.06–0.07 (−2.6° to −3.1°). With a degree more of built-in incidence our front inside fin carries more (0.289 against 0.21 at 5°, where (leeway − toe − zero-lift angle) × slope gives 0.29 and 0.21), and the rear fin behind it less.
- **The outside front fin is a separate matter.** Theirs is still on that line at 10° (13.5° onto its foiled face, lift 0.565); ours has left it between 5° and 10° and stays at 0.28–0.30. Three candidates, not yet told apart: the stand-in's nose (our flat-inside family has a sharp corner where the flat face meets the nose, a scanned commercial fin has a rounded one); the mesh (both levels); their simulation.

## Next

Running on the EPYC (`level5-tc065`, then `level5-camb3-tc065`): the same set with t/c 0.065 — does the working rail's split come out as theirs — and with a cambered foil of the same zero-lift angle (3 % camber, t/c 0.065: a rounded nose and no corner) — does the outside front fin then stay on its line to 10°.
