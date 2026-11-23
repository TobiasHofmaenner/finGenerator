# Mesh recipe check — cambered sections in 2-D on the 3-D fin recipe (2026-11-19)

Question: the level-2 and level-3 polars of cambered fins read 35–55 % more drag than the lattice model below the zero-lift angle. With referee sections the model still reads less at −3.5° (`scripts/rans_fed_lattice.py`). Is the remainder the fin, or the wall-function mesh the 3-D runs use?

Three sections of `../thin-cambered/` and `../results.json` again, same driver and Reynolds number (5.7e5), but with `wall: "wf"` and a coarser surface — `surface_level` 4 is chord/160, the cells mesh level 2 puts on a section at a fin's base; 3 is chord/80 (the outer blade); 5 and 6 are chord/320 and chord/640. Ratio to the resolved-wall value in brackets, `*` = not settled in 3000 iterations.

| section | wall, surface cell | cd at −4.5° | cd at −3.5° | cd at −2.5° | cd at 0° | cd at +4° | cl at −3.5° / 0° / +4° |
|---|---|---|---|---|---|---|---|
| 3 % camber, t/c 0.070 | resolved, c/640 | 0.0322 | 0.0139 | 0.0129 | 0.0128 | 0.0165 | −0.044 / +0.340 / +0.771 |
| | wall functions, c/640 | 0.0247 (×0.76) | 0.0121 (×0.87) | 0.0094 (×0.73) | 0.0091 (×0.71) | 0.0128 (×0.77) | −0.046 / +0.343 / +0.782 |
| | wall functions, c/320 | 0.0320 (×0.99) | 0.0179 (×1.29) | 0.0113 (×0.87)* | 0.0110 (×0.86) | 0.0152 (×0.92) | −0.056 / +0.325 / +0.759 |
| | wall functions, c/160 | 0.0330 (×1.02) | 0.0177 (×1.28) | 0.0127 (×0.99) | 0.0127 (×0.99) | 0.0198 (×1.20) | −0.051 / +0.325 / +0.691 |
| | wall functions, c/80 | 0.0306 (×0.95) | 0.0241 (×1.74) | 0.0207 (×1.60) | 0.0164 (×1.28) | 0.0235 (×1.42) | +0.143 / +0.389 / +0.774 |
| 3 % camber, t/c 0.092 | resolved, c/640 | 0.0146 | 0.0137 | 0.0133 | 0.0130 | 0.0156 | −0.041 / +0.345 / +0.778 |
| | wall functions, c/160 | 0.0306 (×2.10)* | 0.0172 (×1.26)* | 0.0135 (×1.01) | 0.0129 (×1.00) | 0.0194 (×1.25) | −0.029 / +0.332 / +0.651 |
| | wall functions, c/80 | 0.0312 (×2.14) | 0.0235 (×1.72) | 0.0215 (×1.62) | 0.0181 (×1.39) | 0.0213 (×1.36) | −0.025 / +0.121 / +0.463 |
| 4.5 % camber, t/c 0.070 | resolved, c/640 | 0.0447 | 0.0154 | 0.0136 | 0.0139 | 0.0177 | +0.124 / +0.510 / +0.935 |
| | wall functions, c/160 | 0.0491 (×1.10)* | 0.0219 (×1.43) | 0.0165 (×1.21) | 0.0138 (×0.99) | 0.0221 (×1.25) | +0.111 / +0.484 / +0.780 |
| | wall functions, c/80 | 0.0503 (×1.12) | 0.0371 (×2.41) | 0.0255 (×1.88) | 0.0180 (×1.30) | 0.0210 (×1.18) | −0.007 / +0.290 / +0.696 |

## Reading

- **At the cell size level 2 gives a fin's base, the attached range ends about a degree early at negative incidence.** At chord/160 all three sections read 26–43 % more drag at −3.5° than on the resolved wall and agree with it at 0°. The t/c 0.092 section, attached to −6° on the resolved wall, has let go by −4.5°.
- **The same cells cost lift and add drag under load.** At +4°, chord/160 reads 10–17 % less lift and 20–25 % more drag; at chord/640 the lift is back within 1.5 %.
- **The two finer wall-function rows do not separate cell size from wall treatment.** Their first cell sits in the buffer layer (y+ 5–90) and they under-read friction by 14–29 %; wall functions are not valid there. I first read their persisting rise at −3.5° as "the wall treatment, not the cell size". The 3-D run on a finer surface with the first cell in the log layer (`bench/cambered-candidate/mesh-level-5/`) says otherwise: there one refinement removes most of the excess (6.9 → 5.4 N at −3.5° on the 3 % camber fin).
- **Chord/80 is too coarse to use.** Its lift is wrong by up to 0.2 at every angle, which the 3-D polars do not show; the 2-D slab at that resolution is not a fair stand-in for the 3-D mesh.

So: level-2 and level-3 polars of cambered fins read high below about −3° of own incidence, because the nose is under-resolved there, and are not a referee for drag going straight. Mesh level 5 (`finGenerator-cfd`, level 2 with one more surface refinement) is.

Driver options added for this check: a section may carry its own `wall` and `surface_level` (`finGenerator-cfd/scripts/section_polar.py`).

## The thin symmetric section on the same recipe (2026-11-23)

Question, from the centre fin: the resolved referee has a symmetric section of t/c 0.046 end its attached range at 5.1° in a step of drag, with the lift going on behind it (`../rerun-held/`, the controls). Level-5 and level-6 polars of the gen-1 centre, which carries that section, stay on their lift line to 8–9° (`../../knee/one-degree/`). Is the 3-D recipe blind to what happens at that nose?

`sym-tc046.json`: the section at Re 5.7e5 with wall functions and surface cells of 0.375 mm and 0.19 mm (the nose cells of mesh levels 5 and 6 on that fin), old inlet.

| | 4° | 5° | 6° | 7° | 8° | 9° | 10° | 12° |
|---|---|---|---|---|---|---|---|---|
| wall functions, 0.375 mm: c_l | 0.444 | 0.55* | 0.63* | 0.72* | 0.69* | 0.81* | 0.88* | 1.00* |
| c_d | 0.0200 | 0.042* | 0.069* | 0.095* | 0.108* | 0.142* | 0.175* | 0.234* |
| wall functions, 0.19 mm: c_l | 0.431 | 0.53* | 0.63* | 0.68* | 0.76* | 0.83* | 0.82* | 0.88* |
| c_d | 0.0182 | 0.036* | 0.068* | 0.086* | 0.111* | 0.135* | 0.153* | 0.202* |
| resolved referee and its control: c_l | 0.432 | 0.516 | 0.59* | 0.72* | 0.66* | 0.79* | 0.90* | 1.00* |
| c_d | 0.0140 | 0.0307 | 0.048* | 0.079* | 0.098* | 0.121* | 0.157* | 0.227* |

(* not settled in 3000 iterations.)

- **It is not blind.** On the fin recipe the section stops settling at 5° too, its drag steps there, and its lift goes on at about two thirds of the slope to 0.9–1.0 at 12°: the same polar as the resolved one, with 30–40 % more drag at 4° and 5°.
- So the centre's polar is what strips of this section give: on the line until the most loaded strip reaches 5.1°, which is 8.1° of the blade's incidence, and falling away gradually after it because each strip keeps lifting. The strip criterion, which takes 0.606 of the lift at the section's end, reads that blade at 4.9°: for a section that ends in a kink and not in a loss of lift, the share is the wrong thing to take. `docs/GEN3-PLAN.md` 2b.1 has the test of that reading.

