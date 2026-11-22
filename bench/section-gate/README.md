# Section-recipe gate: what the 2-D referee can referee (2026-11-19, rewritten 2026-11-21, the wall 2026-11-22)

Purpose: before a section table is trusted, the 2-D recipe has to reproduce measured sections. Driver: `finGenerator-cfd/scripts/section_polar.py` (simpleFoam, kOmegaSST fully turbulent, resolved wall, domain ±20 chords, one-cell slab). Measurements: NACA 0012 at Re 7e5 ([SK81], `bench/ref-sk81-naca0012-re0.7M.dat`), NACA 4415 at Re 7.5e5 ([Hof96], `bench/ref-osu-naca4415-re0.75M.dat`), both with natural transition, and the fits of more than forty tunnels' NACA 0012 results in [McC87].

`runs.json` has every run named here (plan, mesh, rows); `scripts/section_gate_tables.py` prints the tables from it. Raw cases: laptop `~/bench-results/sections2` and `sections3`.

## Verdict

| quantity | referee against measurement | what it is good for |
|---|---|---|
| lift inside the attached range | NACA 4415: within 3 % from 0° to 6°. NACA 0012: 4–6 % below [SK81] at 4–8°, 4 % above the slope [McC87] fits to better tunnels | yes |
| drag | that of a section turbulent from the nose: at zero lift inside the band tripped tunnels give for the NACA 0012 (section 3), about twice an untripped section's. On the table's wall it is 4–5 % below the same model on a wall ten times finer, on both sections alike (section 4) | yes, as that |
| where the attached range ends | late and high. NACA 0012: peak 1.26–1.27 at 13.0–13.25° against 1.075 at 11° (+18 %, 2° late; seven sources in [McC87] put the maximum at about 1.0–1.15 at this Reynolds number). NACA 4415: +11 % at 10°, +19 % at 13.5°. A finer wall moves the ends later still, by 0.5–1.5° (section 4) | an upper bound |

The first version of this record (2026-11-19) said "passed: maximum lift within 3 %". That did not hold (section 1). The peak is the fully turbulent model's. The surface mesh does not move it (section 2), the stream moves the break by half a degree (section 3), and a finer wall moves it later, away from the measurement (section 4). The lattice's knee is therefore fitted on a tunnel fin, not read off the table's ends (`docs/MODEL-EXTENSION.md`).

## 1. The first gate (2026-11-19), and why its verdict is withdrawn

| α ° | measured c_l | old recipe (±4 c, wall functions) | ±20 c, wall functions | ±20 c, resolved wall | measured c_d | resolved c_d |
|---|---|---|---|---|---|---|
| 0 | 0.000 | -0.001 | -0.000 | 0.000 | 0.0067 | 0.0130 |
| 4 | 0.440 | 0.395 | 0.416 | 0.422 | 0.0083 | 0.0143 |
| 8 | 0.880 | 0.715 | 0.720 | 0.816 | 0.0128 | 0.0187 |
| 10 | 1.034 | 0.734 | 0.755 | 0.979 | 0.0159 | 0.0235 |
| 12 | 1.039 | 0.603 | 0.793 | 1.110 | 0.0195 | 0.0330 |
| 14 | 0.628 | 0.554 | 0.852 | 0.644 | 0.0236 | 0.1687 |
| 16 | 0.470 | 0.630 | 1.070 | 1.043 | 0.2100 | 0.2310 |

(`plan-gate.json`, `plan-gate-wf.json`, `results-resolved.json`, `results-wf.json`; the old recipe is `sk81_naca0012.py`, CFD-BENCH item 3.)

- **What stands: the wall treatment was the defect of the old recipe, not the domain.** With wall functions the suction peak is lost near 8–10° on either domain (lift slope −18 %, no clean maximum). Every 3-D polar on mesh levels 2 to 5 uses wall functions: their maximum lift is a lower bound.
- **What does not: "maximum lift within 3 %, the break within about 1°".** It compared 1.110 at 12° with the measured peak of 1.075 at 11° on a grid of two degrees, on a mesh whose outline had a corner at the leading edge and whose nose was refined by curvature only (`../section-tables/nose/`, found a day later). That mesh reads 6 % less lift at 12° than the converged recipe and is separated at 14°. The early separation of a defective nose and the late break of the model cancelled.

## 2. The two measured sections on the converged recipe

Exact outline, nose cells of one size, 14 layers; chord 0.2 m and a trailing edge of 0.4 mm for the NACA 0012 (70 779 cells), the NACA 4415 likewise (71 877 cells). Rows every half degree to the break, a quarter degree at it. Old inlet (section 3 has the others).

**NACA 0012, Re 7e5, against [SK81]**

| α ° | measured c_l | c_d | referee c_l | c_d |
|---|---|---|---|---|
| 0 | 0.000 | 0.0067 | 0.0000 | 0.01260 |
| 4 | 0.440 | 0.0083 | 0.4234 | 0.01422 |
| 8 | 0.880 | 0.0128 | 0.8297 | 0.01928 |
| 10 | 1.034 | 0.0159 | 1.0176 | 0.02355 |
| 11 | 1.075 | 0.0175 | 1.1048 | 0.02623 |
| 12 | 1.039 | 0.0195 | 1.1859 | 0.02938 |
| 13 | 0.874 | 0.0216 | 1.2550 | 0.03349 |
| 13.25 | 0.812 (i) | 0.0221 | 1.2723 | 0.03458 |
| 13.5 | 0.751 (i) | 0.0226 | 1.2843* | 0.03577 |
| 14 | 0.628 | 0.0236 | 0.9186* | 0.11535 |

**NACA 4415, Re 7.5e5, against [Hof96]**

| α ° | measured c_l | c_d (wake) | referee c_l | c_d |
|---|---|---|---|---|
| -4 | 0.020 | 0.0132 | 0.0081 | 0.01448 |
| 0 | 0.430 | 0.0089 | 0.4166 | 0.01476 |
| 2 | 0.611 (i) | 0.0079 | 0.6290 | 0.01609 |
| 4 | 0.848 (i) | 0.0092 | 0.8399 | 0.01821 |
| 6 | 1.022 (i) | 0.0104 | 1.0440 | 0.02108 |
| 8 | 1.163 (i) | 0.0146 | 1.2293 | 0.02473 |
| 10 | 1.260 (i) | 0.0175 | 1.3998 | 0.02924 |
| 12 | 1.314 (i) | 0.0217 | 1.5299 | 0.03541 |
| 14 | 1.358 (i) | 0.0274 | 1.6140 | 0.04497 |
| 14.25 | 1.368 | 0.0282 | 1.6215 | 0.04662 |
| 15 | 1.377 (i) | | 1.6427* | 0.05285 |

((i): measured value interpolated between two angles; *: not settled within 3000 iterations.)

- **Lift inside the range agrees.** NACA 4415: within 3 % from 0° to 6°. NACA 0012: 3.8 % and 5.7 % below [SK81] at 4° and 8°, 1.6 % below at 10°. [SK81]'s slope (0.110 per degree) is itself 8 % above the fit of the best tunnels in [McC87] (0.1017 per degree at this Reynolds number, extended a factor of three below the range it was fitted on); the referee's 0.106 lies between.
- **The break is late and the peak high.** NACA 0012: last settled row 1.272 at 13.25°, against 1.075 at 11°: +18 %, 2.25° late. The seven sources of [McC87]'s first two groups (no trip, its Fig. 13) put the maximum at about 1.0–1.15 at Re 7e5, rising steeply with Reynolds number; the referee's value is what they measure at Re 1.0–1.4 million. NACA 4415: 5.7 % high at 8°, 11 % at 10°, 19 % at 14°, still rising at 15° where the measured section peaks (1.38 at 15.3°). With grit on the leading edge the measured section peaks at 1.11 at 11.2°.
- **Why** (an inference; no run here separates the two). Both measurements have natural transition at a Reynolds number where a laminar bubble sits near the nose and the layer behind it is thicker than a turbulent one grown from the nose. The model has no bubble, and it keeps a turbulent layer attached longer than tunnels do at this Reynolds number. A mesh does not change it (`../section-tables/nose/`: six meshes, the same break), nor does the stream (section 3).
**On the table's stream** (held, section 3; the same two meshes, 2026-11-22; `naca0012/held-gate`, `naca4415/held-gate` in `runs.json`):

| NACA 4415 α ° | measured c_l | old inlet c_l | c_d | held c_l | c_d |
|---|---|---|---|---|---|
| -4 | 0.020 | 0.0081 | 0.01448 | -0.0013 | 0.01337 |
| 0 | 0.430 | 0.4166 | 0.01476 | 0.4162 | 0.01375 |
| 4 | 0.848 (i) | 0.8399 | 0.01821 | 0.8403 | 0.01719 |
| 8 | 1.163 (i) | 1.2293 | 0.02473 | 1.2292 | 0.02349 |
| 12 | 1.314 (i) | 1.5299 | 0.03541 | 1.5296 | 0.03406 |
| 13 | 1.327 (i) | 1.5731 | 0.03983 | 1.5785 | 0.03829 |
| 13.5 | 1.338 (i) | 1.5872 | 0.04270 | 1.5967 | 0.04075 |
| 13.75 | 1.348 (i) | | | 1.6040* | 0.04234 |
| 14 | 1.358 (i) | 1.6140 | 0.04497 | 1.5993* | 0.04433 |
| 14.5 | 1.372 (i) | 1.6309* | 0.04850 | 1.3688* | 0.06209 |

- **NACA 4415:** lift within 0.6 % of the old inlet's at every settled row, drag 7 % lower at 0° and 4–5 % lower from 8° on. Last settled row 13.5° (14.25° on the old inlet): 1.597 against the measured 1.338, +19 %. Lift stays at 1.60 to 14.0° and is down to 1.37 at 14.5°.
- **NACA 0012:** the gate is the stream study's held run a second time, on the other machine (section 3 has its rows). The two agree within 0.2 % in lift and drag and break in the same row (attached at 13.0°, past the end at 13.25°).

- **Drag is not comparable with these two measurements**: both are untripped (0.0067 and 0.0089 at 0°), the model is turbulent from the nose (0.0126 and 0.0148). The [Hof96] section with grit has a lowest drag of 0.0150, the referee 0.0145: the old inlet gives a smooth section the drag of one with a heavily roughened nose. Section 3 has the comparison that can be made.

## 3. The stream

The referee's inlet carried 5 % turbulence with a length of a tenth of the chord: the 3-D recipe's rule, never varied. Between the inlet and the section, 20 chords away, the model's turbulence decays, and what arrives is set by the domain's length: on the NACA 0012 at Re 7e5 an intensity of 3.3 % and an eddy viscosity 1100 times the molecular one.

Streams run on the gate's mesh (NACA 0012, Re 7e5; lift coefficient, drag coefficient × 10⁴, * not settled):

| stream | at the section | 0° | 8° | 12° | 12.5° | 13° | 13.25° | 13.5° | 14° |
|---|---|---|---|---|---|---|---|---|---|
| old inlet: 5 %, length 0.1 c, decaying | 3.3 %, eddy viscosity ×1100 | 126.0 | 0.8297, 193 | 1.1859, 294 | 1.2192, 315 | 1.2550, 335 | 1.2723, 346 | 1.2843*, 358 | 0.9186* |
| quiet: 1 %, eddy viscosity ×10, decaying | 0.2 %, ×8 | 109.5 | 0.8265, 169 | 1.1909, 262 | 1.2296, 278 | 1.2645, 297 | 1.0358* | 0.8740* | 0.7622* |
| quieter: k = 10⁻⁶ U², ω = 5 U/c, decaying | ×0.1 | 109.2 | 0.8271, 169 | 1.1910, 260 | 1.2296, 278 | 0.9860* | | 0.9083* | |
| **held: k = 10⁻³ U² (2.58 %), ω = 5 U/c** | as set, ×140 | 117.8 | 0.8290, 182 | 1.1885, 281 | 1.2252, 299 | 1.2580, 320 | 0.8189* | 0.6830* | 1.2363* |
| held, low: k = 10⁻⁴ U² (0.82 %), ω = 5 U/c | as set, ×14 | 110.4 | 0.8258, 171 | 1.1874, 265 | 1.2246, 282 | 0.7902* | | 0.6732* | |
| held, short scale: k = 10⁻³ U², ω = 60 U/c | as set, ×12 | 113.9 | 0.8004, 174 | 1.0641, 266 | 0.9646* | | | | |

(The quieter stream is separated at 12.75° as well. "Held" keeps k and ω at their values up to the section with the model's sustaining terms, [SR07]; OpenFOAM's `decayControl`, driver options `tu`, `omega_cu`, `sustain`.)

- **Lift does not depend on the stream**: within 0.5 % up to 12° in the five streams that leave the layer alone, within 0.9 % in the last degree before the break.
- **The break moves by half a degree.** Last attached row: 13.25–13.5° on the old inlet, 13.0° in the quiet and in the held stream, 12.5° in the quieter and in the low held one. The highest attached lift is 1.22–1.27 in all five, 14–18 % above [SK81]'s peak.
- **Drag depends on the stream by 15 %.** Ratio quiet to old inlet: 0.87–0.89 at every angle. Held to old: 0.93–0.96.

**Which drag is right.** A fully turbulent run is to be compared with tripped sections, not with [SK81]'s. [McC87] fits the tripped drag at zero lift of the best tunnels as 0.0017 + 0.91 / (log₁₀ Re)^2.58: twice the flat-plate friction law plus a constant. Its tripped points lie between about 3 and 12 million (its Fig. 4), so Re 7e5 is an extrapolation by a factor of four, and it matters how: with the constant kept the fit gives 0.0113; with the form drag growing with the friction (the usual factor 1 + 2 t/c + 60 (t/c)⁴ on the same friction law, which agrees with the fit within 1 % at Re 6 million) 0.0120.

| stream | c_d at 0° | against 0.0113 | against 0.0120 |
|---|---|---|---|
| old inlet | 0.01260 | +11.8 % | +5.2 % |
| held | 0.01178 | +4.5 % | −1.7 % |
| held, low | 0.01104 | −2.0 % | −7.8 % |
| quiet | 0.01095 | −2.8 % | −8.6 % |

([McC87] counts a tunnel as agreeing with its fits when its drag at zero lift is within 0.0010.)

**Why not the quiet stream.** In a quiet stream the SST model leaves a boundary layer laminar up to a length Reynolds number of about 4×10⁴ and is not fully turbulent before 1–3×10⁵ ([RS09]); where it turns depends on the grid and the pressure gradient, not on any physics of transition. Skin friction read from the runs (`finGenerator-cfd/scripts/section_friction.py`; c_f × 1000, median per band of chord):

| NACA 0012, Re 7e5, 0° | x/c 0.02–0.04 | 0.04–0.07 | 0.07–0.10 | 0.2–0.3 | 0.4–0.5 | 0.6–0.7 | 0.9–0.97 |
|---|---|---|---|---|---|---|---|
| old inlet | 9.12 | 7.91 | 7.33 | 5.66 | 4.52 | 3.74 | 2.38 |
| held | 8.96 | 7.81 | 7.25 | 5.58 | 4.43 | 3.64 | 2.30 |
| quiet | 7.99 | 6.65 | 6.97 | 5.45 | 4.27 | 3.45 | 2.10 |

| 3 % camber, t/c 0.07, Re 1.4e5, lower side | x/c 0.07–0.10 | 0.10–0.15 | 0.15–0.2 | 0.2–0.3 | 0.3–0.4 | 0.4–0.5 |
|---|---|---|---|---|---|---|
| 0°: old inlet | 5.61 | 5.06 | 5.12 | 4.80 | 4.68 | 4.77 |
| 0°: held | 5.52 | 4.91 | 5.00 | 4.73 | 4.62 | 4.71 |
| 0°: held, low | 4.97 | 3.89 | 4.05 | 4.54 | 4.52 | 4.59 |
| 0°: quiet | 4.92 | 3.76 | 3.79 | 4.50 | 4.51 | 4.59 |
| +4°: old inlet | 7.77 | 6.11 | 5.35 | 4.82 | 4.71 | 4.80 |
| +4°: held | 7.69 | 6.00 | 5.20 | 4.70 | 4.62 | 4.71 |
| +4°: held, low | 7.40 | 5.56 | 4.60 | 3.90 | 4.24 | 4.49 |
| +4°: quiet | 7.37 | 5.52 | 4.53 | 3.64 | 3.95 | 4.43 |

- **At Re 7e5 the quiet stream has a laminar run over the first 7 % of chord** (friction 12–16 % lower there), and at 8° on the lower side to 15 %. Behind it the friction stays 4–12 % below the old inlet's.
- **At Re 1.4e5, the table's lowest Reynolds number, the run covers a fifth to two fifths of the chord** on the lower side (friction 15–26 % lower), and where it sits moves with the angle. On the upper side at 0° it reaches from 10 % to 30 % of chord. Drag is 9 % below the old inlet's at 0° and +4°. A table built on that would carry the model's switch-on point in its Reynolds-number trend.
- **The low held stream (0.82 %) has the quiet stream's runs**, a little shorter; its drag is within 0.6 % of the quiet stream's at both Reynolds numbers.
- **The held stream at 2.58 % shows no such run at either Reynolds number**: its friction follows the old inlet's within 1–3.5 % from the nose to the trailing edge.

**Why not a shorter length scale.** Holding k = 10⁻³ U² with ω = 60 U/c gives the lowest eddy viscosity of the held streams and a drag on the fit (0.0114). But lift is 3.5 % low at 8° and the section lets go by 12.5°. On the aft upper side at 8° its friction falls to 40 % of the other streams' by the trailing edge (0.41 against 1.03 at x/c 0.9–0.97; 1.23 against 1.80 at 0.8–0.9): the stream's ω is higher than the boundary layer's own in its outer part, the sustaining term holds it up there, and the outer layer loses its eddy viscosity. A held stream's ω has to stay well below the layer's; 5 U/c is the value of [SR07] and [RS09]. The run was stopped after four rows.

**The stream chosen: held, k = 10⁻³ U², ω = 5 U/c** (`"tu": 0.02582, "omega_cu": 5.0, "sustain": true`). It is the highest of the three [RS09] test; they note that above 1 % the stream begins to act on the turbulent layer itself, and it does here: 4.5 % more drag than the fit, friction 2–10 % above the quiet stream's behind its laminar run. It is the one stream that is turbulent from the nose at Re 1.4e5 and inside the band of tripped drag at Re 7e5, and it arrives at the section as set whatever the domain. Against the old inlet on the test section's sibling at Re 1.4e5 (3 % camber, t/c 0.07, ten layers):

| α ° | old inlet c_l | c_d | held c_l | c_d | held, low c_l | c_d | quiet c_l | c_d |
|---|---|---|---|---|---|---|---|---|
| -5 | -0.2296* | 0.04219 | -0.2134* | 0.04000 | | | | |
| -4.75 | -0.1890* | 0.03277 | -0.1856* | 0.03328 | | | -0.1895* | 0.03537 |
| -4.5 | -0.1662 | 0.02418 | -0.1629 | 0.02408 | | | -0.1602* | 0.02654 |
| -3.5 | -0.0634 | 0.01732 | -0.0612 | 0.01670 | -0.0608 | 0.01605 | -0.0605 | 0.01595 |
| 0 | 0.3108 | 0.01592 | 0.3123 | 0.01535 | 0.3104 | 0.01457 | 0.3107 | 0.01449 |
| 4 | 0.7220 | 0.01968 | 0.7219 | 0.01888 | 0.7188 | 0.01804 | 0.7191 | 0.01795 |
| 8 | 1.0545 | 0.03359 | 1.0473* | 0.03281 | | | | |
| 8.25 | 1.0658 | 0.03666 | 1.0321* | 0.03752 | | | | |
| 8.5 | 1.0492* | 0.03988 | 1.0181* | 0.04305 | | | | |

- **Lower end:** in the same row on the old inlet and in the held stream (attached at −4.5°, past it at −4.75°). In the quiet stream −4.5° is already past it.
- **Upper end:** the held stream is past it at +8.0°, where the old inlet is attached to +8.25°: more than a quarter of a degree earlier. The rerun's march finds where.
- **Drag** is 3.6–4.1 % lower in the held stream than on the old inlet here, 4.7–5.3 % at Re 5.7e5 (the test section, first rows of the rerun) and 6.5 % at Re 7e5 (NACA 0012). The old inlet's eddy viscosity grows with Reynolds number, 220 times the molecular one here and 1100 at Re 7e5, and its drag excess with it. The quiet and the low held stream are 8–9 % below the old inlet, their laminar runs included.

On the test section at Re 5.7e5 the quiet stream against the old inlet: lift within 0.004, drag 10–11 % lower, and both ends earlier: −6.25° is past the end (attached on the old inlet), +10.0° is past it (1.324 attached on the old inlet). The held stream there: lift within 0.003 of the old inlet, attached at −6.0° and past the end at −6.5° like the old inlet; the rest of its rows are in `../section-tables/rerun-held/`.

**Consequences.**

- The table's sections are rerun on the held stream (`../section-tables/rerun-held/`, with a row-by-row comparison against the old-inlet sections of `../section-tables/rerun/`): the 35 of the first rerun and four more in the band of thickness where the upper end jumps (t/c 0.05 to 0.08). Expected from the controls: lift unchanged, drag 4–7 % lower, ends a quarter to half a degree earlier.
- Both gate sections ran on the held stream with the rerun (section 2), and with them a series on the first cell's height (section 4).
- The 3-D recipe has the same inlet rule and 4 base chords of fetch instead of 20 chords, so its stream at the fin is yet another one. `fincfd` takes the held stream as an option (`CaseSpec.held_stream`, `write_set_case(held_stream=True)`), off by default: every 3-D record so far is on the decaying stream. On mesh level 5 friction is a third low from the wall functions in any case (`docs/CFD-BENCH.md`); a control on a known fin is to run before 3-D drag is compared across the two streams.

## 4. The wall (2026-11-22)

The table's recipe makes the first cell two flat-plate wall units thick (9.3 µm on the test section at Re 5.7e5, 12.9 µm on the NACA 0012) and grows the layers from it at a ratio of 1.2. Measured on the test section's runs (`finGenerator-cfd`'s y⁺ record, read per face): the wall cells' centres sit at a median y⁺ of 1.2 at 0° (90 % of the faces below 1.9) and at 3–6 on the first 0.2 % of chord at +10°. On every mesh the stack tapers to nothing over the last 3 % of chord (y⁺ 2–8 there) and the blunt base carries none (y⁺ to 12, to 22 on the NACA 0012). The series below does not refine those two places.

**The series.** First cell at a half, a quarter and a tenth of the table's height, layers at the same ratio up to the same outer cell (the stack is 0.76–0.88 mm thick on the NACA 0012 in all four), held stream. Lift coefficient, drag coefficient × 10⁴:

| test section (3 % camber, t/c 0.07, Re 5.7e5) | layers | median y⁺ at 0° | 0° | +4° | +10° | upper end between | lower end between |
|---|---|---|---|---|---|---|---|
| 9.3 µm (the table's) | 13 | 1.20 | 0.3423, 122.2 | 0.7728, 154.3 | 1.3233, 318.1 | +10.0° and +10.25° | −6.0° and −6.25° |
| 4.7 µm | 17 | 0.61 | 0.3388, 124.5 | 0.7701, 156.8 | 1.3299, 306.0 | +10.75° and +11.0° | −6.25° and −6.5° |
| 2.3 µm | 21 | 0.31 | 0.3374, 126.3 | 0.7678, 159.2 | 1.3223, 306.4 | +11.0° and +11.25° | −6.5° and −6.75° |
| 0.9 µm | 26 | 0.13 | 0.3373, 127.6 | 0.7654, 160.9 | 1.3206, 308.7 | +11.25° and +11.5° | −6.5° and −6.75° |

| NACA 0012, Re 7e5 | layers | 0° | 8° | 12° | 13° | 14° | upper end between |
|---|---|---|---|---|---|---|---|
| 12.9 µm (the table's) | 14 | 117.8 | 0.8290, 182.1 | 1.1865, 281.6 | 1.2595, 319.0 | 0.8697* | 13.0° and 13.25° |
| 6.5 µm | 18 | 120.7 | 0.8256, 185.0 | 1.1889, 279.7 | 1.2619, 316.0 | | 13.25° and 13.5° |
| 3.2 µm | 22 | 123.0 | 0.8215, 188.3 | 1.1806, 285.4 | 1.2540, 321.3 | 1.3112, 369.4 | 14.25° and 14.5° |
| 1.3 µm | 27 | 123.8 | 0.8177, 191.6 | 1.1704, 292.4 | 1.2486, 327.0 | 1.3023, 376.7 | 14.5° and 14.75° |

(`held`, `held-gate`, `held-y1`, `held-y05`, `held-y02` in `runs.json`. The two finest NACA 0012 walls were continued from 14.25° in quarter degrees: the 3.2 µm wall's last settled row is 14.25° (1.3230, 384.6), the 1.3 µm wall's 14.5° (1.3252, 408.4).)

- **Drag rises as the wall is refined and has not levelled.** At 0°: +1.9, +3.4, +4.4 % on the test section and +2.5, +4.4, +5.1 % on the NACA 0012 against the table's wall. At 8° on the NACA 0012: +1.6, +3.4, +5.2 %, the last step as large as the first.
- **Lift falls by about 1 %.** Test section: 0.005 at 0°, level over the last step; 1.0 % at +4°. NACA 0012: 0.4–0.5 % per step from 8° to 13°, 1.4 % in all at 8°, not levelled.
- **Both ends move outward.** Test section: the upper end by 1.25°, the lower by 0.5°, the last step a quarter of a degree at the upper end and none at the lower. NACA 0012: by 1.25° and then 1.5° on the two finest walls, the last step a quarter of a degree here too, and its highest lift goes from 1.26 to 1.33.
- **Away from the measurements.** The measured NACA 0012 peaks at 1.075 at 11° ([SK81]). The table's wall holds to 13.0° (1.26), the two finest to 14.25° and 14.5° (1.32 and 1.33). Drag at 0° against the tripped fit of section 3 (0.0113–0.0120): 0.01178 on the table's wall, 0.01238 on the finest. Both lie inside the 0.0010 [McC87] allows a tunnel.
- **What it is** (an inference from the series and one source). The ω equation's solution rises as 1/y² toward a smooth wall and the wall cell's value is set from the cell's own height; a first cell at y⁺ 1 with a growth of 1.2 does not resolve it. [EPV18] is a study of exactly this question for steady RANS without wall functions (read: its abstract). That ω-based models want y⁺ near 0.1 is the reading of a review that cites it, not something read in the paper.

**The wall cell's treatment is not the cause.** OpenFOAM's `omegaWallFunction`, the wall condition on ω in every run, blends by default: the wall cell's ω is the root of the sum of squares of the viscous and the log-law value, and the cell's production of k is replaced by the log-law form at any y⁺ (v2512 source: the replacement is skipped only for `stepwise` blending below the laminar y⁺). Two controls on the table's mesh, test section, held stream:

| wall cells | 0° | +4° | −6.0° | −6.25° | +10.0° |
|---|---|---|---|---|---|
| blended (the table's) | 0.3423, 122.2 | 0.7728, 154.3 | −0.3120, 162.8 | past the end | 1.3233, 318.1 |
| stepwise: viscous ω and the model's own production below y⁺ 11 | 0.3421, 122.2 | 0.7727, 154.1 | −0.3117, 165.3 | past the end | past the end |
| stepwise, and k = 0 on the wall instead of a zero gradient | 0.3421, 122.2 | 0.7727, 154.1 | −0.3117, 165.3 | past the end | past the end |

(`held-stepwise`, `held-stepwise-k0`.) Away from the ends the rows are the same to four digits, so the blended wall cell is not what separates the table's wall from the finer ones. At the upper end the stepwise wall lets go at least a quarter of a degree earlier. The wall's value of k plays no part.

**From rest, or from the row before.** Every row of the table starts from rest. Two sweeps through the test section's upper end, each row starting from the one before it (`held-up`, `held-down`):

| α ° | 9.0 | 9.5 | 9.75 | 10.0 | 10.25 | 10.5 | 11.0 | 12.0 |
|---|---|---|---|---|---|---|---|---|
| from rest | 1.2550, 266.6 | 1.2936, 287.7 | | 1.3233, 318.1 | 1.0834* | 1.1230* | 1.0524* | |
| sweep upward | | 1.2936, 287.4 | | 1.3234, 318.2 | 1.3567* | 1.0851* | 1.0652* | 0.9949* |
| sweep downward from 12.5° | 1.2557, 265.7 | 1.2937, 287.5 | 1.3103, 300.8 | 1.0875* | 1.0881* | 1.0755* | 1.0693* | 1.0197* |

- **The end is not a start-up effect.** The upward sweep is attached at +10.0° with the from-rest row's numbers and lets go in the next row, like the rows from rest.
- **There is a loop a quarter to half a degree wide.** Coming down, the flow stays separated at +10.0° and reattaches at +9.75°. A row from rest finds the loop's upper edge.

**The mesher takes thin layers off without an error.** snappyHexMesh refuses a cell whose determinant is below `minDeterminant` (0.001). For a wall cell of thickness t on a face of size a that is 7812 (t/a)⁴: an aspect ratio of about 50. A first cell of 2.3–3.2 µm is below it on the faces behind the nose band, one of 0.9 µm everywhere. The first attempts at the two finer walls lost their layers that way:

| first cell | the mesher's share of the stack | mean wall y⁺ |
|---|---|---|
| 2.3 µm (test section) | 97.6 % | 3.6 |
| 3.2 µm (NACA 0012) | 92.2 % | 17.6 |
| 0.9 µm | 0.87 % (refused by the driver) | |

- **The share is a count over faces of the slab, and most faces are nose cells.** A mesh with no layers on most of its chord still reads 97.6 %. The mean wall y⁺ shows it; the driver now prints it per row and flags a mean above the first cell's nominal height plus 0.3 (the base and the taper before it are 0.15 of the mean on every mesh).
- **The valid series** runs with `min_determinant 1e-12` and `min_vol 1e-20`: every face keeps its layers, 99.9 % of the stack.
- **Every section of the rerun was checked this way:** mean wall y⁺ 1.26–1.44 at 0°, all faces with layers.
- Runs named `-y05`, `-y02`, `-y05v`, `-y02v` in `~/bench-results/sections3` are the invalid meshes. They are not in `runs.json`.

**What it means for the table.**

- The table's recipe is the same model at the usual wall spacing, with known offsets against a wall ten times finer: drag 4–5 % low, lift up to 1.4 % high, the upper end 1.25–1.5° early and the lower end 0.5° early.
- The offsets are close to common to the two sections (drag at 0°: 4.4 % and 5.1 %; upper end: 1.25° and 1.5°), which is what a ranking of sections needs.
- A finer wall has no natural stopping point (drag is not level at a median y⁺ of 0.13) and moves the ends further from the measured ones.
- Proposed: the table stays on its wall, with these offsets stated. The check that decides it is at the fin level: shift the table's ends by these amounts and see what moves in the knee, the hold numbers and the searches.

**The check at the fin level, first pass (2026-11-22, on 29 of the 39 sections).** A second table is built from the same record with every lower end moved out by 0.5° and every upper end by 1.25°. The rows filling the gap continue lift at the slope of the last interval and drag at the logarithmic slope of the four rows before the last; on the test section they follow the finest wall's rows within 0.006 in lift and 2 % in drag. Knee of each blade (`scripts/knee_survey.py`, perfect mirror, share 0.715), in degrees of own incidence:

| blade | table as built | ends moved | with the section's limit read as its highest lift inside the range: as built | ends moved |
|---|---|---|---|---|
| tunnel fin [BW04], flat inside | 14.0 | 14.1 | 14.9 | 15.5 |
| gen-2 side as shipped, flat inside | 8.4 | 8.6 | 8.9 | 9.3 |
| gen-1 side as ridden, flat inside | 8.7 | 9.2 | 9.2 | 9.7 |
| gen-2 planform, 3 % camber | 8.0 | 7.9 | 8.5 | 8.7 |
| cambered candidate (4.3 %, t/c 0.074) | 8.1 | 7.8 | 8.5 | 8.8 |
| best v1-model side (4.2 %, t/c 0.089) | 9.8 | 9.6 | 10.3 | 10.7 |
| gen-1 centre, symmetric t/c 0.046 | 6.8 | 7.8 | 7.1 | 8.2 |
| longboard single, symmetric t/c 0.08 | 7.7 | 8.8 | 8.0 | 9.1 |
| gen-1 centre with t/c 0.09 | 11.0 | 12.0 | 11.6 | 12.7 |

(The last two columns are on the board mirror, which reads half a degree later throughout.)

- **Side fins: the knee moves by half a degree or less**, the hold numbers by 0.01–0.02 (gen-2 side, 65 kg intermediate: 0.72 to 0.73), the lattice's polars against CFD not at all inside the working range. Their sections have rounded lift tops: 1.25° more range is 3–4 % more lift at the end.
- **Symmetric fins: the knee moves by a full degree.** A symmetric section's lift runs straight to its end, so the end's angle is its lift. The wall matters for a centre fin's knee and not for a side fin's.
- **The cambered knees moved the wrong way (8.1° to 7.8° with later ends), and that is the model's break, not the wall.** A section's limit is read where its lift slope falls below 30 % of the line's (`SectionPolar.alpha_break_deg`). On a rounded top a small change of shape moves that point by a degree: on the candidate's critical strip from 12.4° (the end) to 11.4° with the end at 13.7°, 2.3 % less lift. Reading the limit as the highest lift inside the attached range gives the same knees on the table as built (within 0.1°) and moves every blade the same way when the ends move. To be changed with the knee's refit at the rebuild.

## Files

- `runs.json`: every run of sections 2 to 4 (`scripts/section_gate_tables.py <section> <run> ...` prints a table: `naca0012`, `naca4415`, `camb3-tc070-re140k`, `camb3-tc070-re570k`).
- `plan-gate.json`, `plan-gate-wf.json`, `results-resolved.json`, `results-wf.json`: the first gate (section 1).
