# Section-recipe gate: what the 2-D referee can referee (2026-11-19, rewritten 2026-11-21)

Purpose: before a section table is trusted, the 2-D recipe has to reproduce measured sections. Driver: `finGenerator-cfd/scripts/section_polar.py` (simpleFoam, kOmegaSST fully turbulent, resolved wall, domain ±20 chords, one-cell slab). Measurements: NACA 0012 at Re 7e5 ([SK81], `bench/ref-sk81-naca0012-re0.7M.dat`), NACA 4415 at Re 7.5e5 ([Hof96], `bench/ref-osu-naca4415-re0.75M.dat`), both with natural transition, and the fits of more than forty tunnels' NACA 0012 results in [McC87].

`runs.json` has every run named here (plan, mesh, rows); `scripts/section_gate_tables.py` prints the tables from it. Raw cases: laptop `~/bench-results/sections2` and `sections3`.

## Verdict

| quantity | referee against measurement | what it is good for |
|---|---|---|
| lift inside the attached range | NACA 4415: within 3 % from 0° to 6°. NACA 0012: 4–6 % below [SK81] at 4–8°, 4 % above the slope [McC87] fits to better tunnels | yes |
| drag | that of a section turbulent from the nose: at zero lift inside the band tripped tunnels give for the NACA 0012 (section 3), about twice an untripped section's | yes, as that |
| where the attached range ends | late and high. NACA 0012: peak 1.26–1.27 at 13.0–13.25° against 1.075 at 11° (+18 %, 2° late; seven sources in [McC87] put the maximum at about 1.0–1.15 at this Reynolds number). NACA 4415: +11 % at 10°, +19 % at 14°, no peak below 15° | an upper bound |

The first version of this record (2026-11-19) said "passed: maximum lift within 3 %". That did not hold (section 1). The peak is the fully turbulent model's and no mesh or stream moves it (sections 2 and 3). The lattice's knee is therefore fitted on a tunnel fin, not read off the table's ends (`docs/MODEL-EXTENSION.md`).

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

- The table's 35 sections are rerun on the held stream (`../section-tables/rerun-held/`, with a row-by-row comparison against the old-inlet sections of `../section-tables/rerun/`). Expected from the controls: lift unchanged, drag 4–7 % lower, ends a quarter to half a degree earlier.
- Both gate sections and the two controls on the first cell's height (half the height, `first_yplus 1`) run on the held stream with the rerun; their rows go into `runs.json` and this record when they are in.
- The 3-D recipe has the same inlet rule and 4 base chords of fetch instead of 20 chords, so its stream at the fin is yet another one. `fincfd` takes the held stream as an option (`CaseSpec.held_stream`, `write_set_case(held_stream=True)`), off by default: every 3-D record so far is on the decaying stream. On mesh level 5 friction is a third low from the wall functions in any case (`docs/CFD-BENCH.md`); a control on a known fin is to run before 3-D drag is compared across the two streams.

## Files

- `runs.json`: every run of sections 2 and 3 (`scripts/section_gate_tables.py <section> <run> ...` prints a table: `naca0012`, `naca4415`, `camb3-tc070-re140k`, `camb3-tc070-re570k`).
- `plan-gate.json`, `plan-gate-wf.json`, `results-resolved.json`, `results-wf.json`: the first gate (section 1).
