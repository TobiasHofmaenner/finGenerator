# The knee in one-degree steps (mesh level 5, 2026-11-20)

Question: the stored 3-D polars bracket each blade's knee within 4°. Where is it within the bracket, and does the strip criterion (`bladehydro.knee`) rank blades the way the simulation does?

Four blades on mesh level 5 (wall functions), a symmetry plane at the base, in one-degree steps around the expected knee: the [BW04] tunnel fin replica at 7 m/s, the shipped gen-2 side, the best side of the table-v1 model (4.2 % camber, t/c 0.089) and the gen-1 centre at 8.5 m/s. Plans `plan-knee-*.json`, results `results-*.json` (run on the EPYC, `~/bench-results/gen3ladder`). The rows are in `../survey.md`.

## Lift against its own line

| blade | last row on its line (deviation) | next row | 5 % below at | strip criterion, same mirror | C_L at the last row on the line: simulation / criterion |
|---|---|---|---|---|---|
| tunnel fin [BW04] | 12° (−1.9 %) | 13°: −8.2 % | 12.5° | 11.4° | 0.886 / 0.86 |
| gen-2 side, flat inside | 8° (−2.1 %) | 9°: −7.3 % | 8.6° | 7.0° | 0.721 / 0.67 |
| best table-v1 side, 4.2 % camber | 8° (−1.7 %) | 9°: −7.0 % | 8.6° | 7.5° | 0.780 / 0.74 |
| gen-1 centre, symmetric, t/c 0.046 | 8° (−1.5 %) | 9°: −4.1 %, 10°: −5.1 %, 12°: −7.6 % | 9.9° | 7.3° | 0.447 / 0.41 |

## Reading

- **The three side blades break sharply, inside one degree**: within 2 % of the line at one angle, 7–8 % below it at the next, and every row past it runs to the iteration cap. The centre does not: its thin symmetric section lets go gradually (1.5 % at 8°, 5 % at 10°, 8 % at 12°) and its lift keeps climbing at about 80 % of the slope.
- **The criterion ranks the side blades as the simulation does.** The tunnel fin's knee is 4.0° later than either slender side in the simulation (12.5° against 8.6°); the criterion says 4.4° and 3.9°. It puts the flat-inside side 0.5° earlier than the cambered one where the simulation has them level.
- **Its level is early by 1.1–1.6°, evenly** (5 % point; 0.5–1.0° against the last row on the line), and the lift it reads at the knee is 3–7 % below the simulation's last row on the line. That is the fit: `KNEE_FRACTION` puts the tunnel fin at 12.0° on the board mirror, which is 11.4° on the perfect mirror of a tunnel wall and of these runs. A share of 0.745–0.785 instead of 0.715 would put the three on their last attached row, 0.77–0.82 on their 5 % point. The share is left where the tunnel put it: hold is anchored on what the gen-2 side reads with it (D11), so a common shift moves the floor with the blades; and level 5 is itself early (13 % below the line at 14° where the tunnel is 6 % below).
- **The centre's knee is a different thing.** Onset is where the criterion roughly has it (7.3° against 8–9°), but nothing is lost there. Hold for a centre fin needs its own reading when the centre comes up (plan Phase 2).
- **Lift and drag below the knee** (lattice on table v1, perfect mirror, against these rows): lift within 2 % from 4° to the knee on all three side blades; drag at turning load (7–11°) within 1–5 %. At low incidence the flat-inside blades read 11–25 % more drag than level 5 and the cambered one within 4 % down to −3.5° (−18 % at −4.5°, where level 5 has separated early — `bench/section-tables/controls`). Level 5's friction is a third low (docs/CFD-BENCH.md), so the low-incidence gap on the flat-inside blades is not all the model's.

## One mesh level finer, and a pair that differs in tip width alone (2026-11-22)

Two questions the four polars above left open: does the knee move with the mesh, and does the criterion's strongest lever, tip width, exist? (`../../design-points/`: from 0.25 to 0.60 of the base the criterion moves a side fin's knee by three degrees, and no two polars differed in tip width alone.)

- `results-L6-flat.json`: the shipped gen-2 side on mesh level 6 (1 009 370 cells, mean wall y⁺ 49), 6° to 12°, with the rows at 0° and 4° of `../../cambered-candidate/mesh-level-6/`.
- `../../design-points/cfd/sliders-L5.json` and `tip035-L5.json`: the generation-3 side fin for 8.5 m/s and 55° of lean (8 690 mm², 4.5 % camber, tip 0.60 of the base) and the same fin with its tip at 0.35 (8 095 mm²), mesh level 5, one-degree steps.

Lift against each polar's own line through 0° and 6°:

| blade | 7° | 8° | 9° | 10° | 12° | 5 % below at | strip criterion, same mirror |
|---|---|---|---|---|---|---|---|
| gen-2 side, level 5 (above) | −0.7 % | −1.8 % | −7.1 % | −10.5 % | −16.5 % | 8.6° | 6.6° |
| gen-2 side, level 6 | −0.4 % | −1.1 % | −3.4 % | −10.2 % | −15.7 % | 9.2° | 6.6° |
| gen-3 side, tip 0.60 | −0.5 % | −1.4 % | −3.2 % | −15.3 % | −20.0 % | 9.1° | 7.4° |
| the same, tip 0.35 | −1.1 % | −6.7 % | −8.7 % | −14.1 % | −18.8 % | 7.6° | 5.6° |

- **The knee is about half a degree later on the finer mesh.** The gen-2 side is still within 3.4 % of its line at 9° on level 6, where level 5 has it 7 % below and at the iteration cap; from 10° the two agree again. Below the knee the two meshes agree within 1 % in lift. The knees of level 5 above are early by that much on this fin.
- **Tip width does to the knee what the criterion says.** The narrow tip lets go between 7° and 8°, the wide one between 9° and 10°: 1.5° apart in the simulation, 1.8° in the criterion. The aspect-ratio rule has both at 11.7°.
- **The criterion's level is the same on the new fins as on the old**: 1.7° and 2.0° before the 5 % point, against 2.0° on the gen-2 side at the same mesh level. It marks where a blade starts to leave its line (`../../zarruk/lattice.md`).
- The lattice's lift on the generation-3 fin is within 0.2 % of level 5 up to 6° and 1 % at 8°. At their last rows on the line the wide-tipped fin carries 22 % more side force than its twin (C_L 0.881 at 9° on 8 690 mm² against 0.774 at 7° on 8 095 mm²); the model's hold says 25 %.
- **The thin symmetric centre on level 6** (`results-L6-centre.json`, 2026-11-23): on its line to 9° (−0.6 %) and 6.1 % below it at 10°, where level 5 has it leave gradually from 8° (−1.5 %, −4.1 %, −5.1 %). The 5 % point is the same, 9.8° against 9.9°; the onset is a degree later and the break sharper. Neither mesh resolves this fin's nose (radius 0.23 mm at the base, cells of 0.39 and 0.19 mm), and most of the level-6 rows ran to the iteration cap from 6° on. The criterion has this blade at 4.9°: it takes its share of the lift at the end of the thin section's attached range, which is a step in drag and not a limit of lift (`../../section-tables/rerun-held/`, the controls).


## A test with its prediction written first: a thin symmetric foil on the gen-2 side's planform (2026-11-23)

The reading under test came out of the two controls on the thin centre (above, and `../../section-tables/mesh-recipe/`): a thin symmetric blade stays on its lift line until its most loaded strip reaches the END of its section's attached range, a share of one where the criterion takes 0.606, and falls away gradually behind it. A reading fitted on one blade is not tested by that blade. So a second one was made, the shipped gen-2 side's planform with a symmetric foil of t/c 0.05 at every station (`fin-gen2-planform-sym-tc050.json`), and what each reading says about it was written down before the run (`thin-sym-prediction.txt`): a share of one puts the onset at 6.3° and the 5 % point near 8°; the common share puts the onset at 3.8°; the aspect-ratio rule says 12°.

`results-L5-thin-sym.json`, `results-L6-thin-sym.json`: 8.5 m/s, a symmetry plane at the base, mesh levels 5 and 6 (mean wall y⁺ 68 and 46; plans `plan-thin-sym-*.json`). Lift against each polar's own line through its rows up to 4°:

| mesh | 5° | 6° | 7° | 8° | 9° | 10° | 12° | 5 % below at |
|---|---|---|---|---|---|---|---|---|
| level 5 | +0.2 % | −0.9 % | −2.2 % | −5.1 % | −7.6 % | −10.9 % | −17.7 % | 8.0° |
| level 6 | | −0.3 % | −1.6 % | −5.3 % | −7.7 % | | | 7.9° |
| the lattice on table v1, run through its sections' ends | −0.1 % | −0.5 % | −1.8 % | −3.7 % | −7.2 % | −10.7 % | −17.4 % | 8.4° |

- **The prediction held on both meshes.** The blade is on its line to 6° and 5 % below it at 8.0°. The common share would have had it leave before 4°.
- **The 5 % point follows the onset at the distance it has on the side blades**: 1.7° here (6.3° to 8.0°) and on the gen-1 centre (8.1° to 9.8°); on the six one-degree polars of side blades it is 1.0–2.6° behind the common share (2.0° on the gen-2 side at level 5).
- **The rows from 5° up ran to the iteration cap and are still usable.** Each swings about a mean that holds: on level 5 the means of the last four windows of 100 iterations stay within 0.003 at 6° and 7°, 0.004 at 8°, 0.007 at 9° and 0.009 at 10° (lift 0.39 to 0.58), on level 6 within 0.003 at every row; the swing inside a window is 0.01 at 6° and grows to 0.09 at 12°. A deviation of 5 % is 0.026 in lift at 8°.
- **The lattice needs no criterion for this blade.** Run through its sections' ends on table v1 (perfect mirror, `lattice_beside_polar.py`), it has the lift of level 5 within 3 % and of level 6 within 2 % at every row up to 12°, and it leaves its own line where the simulation does, row by row (the third line of the table). The same holds on the gen-1 centre up to 10° (lift within 1.8 % of level 5 and 3.5 % of level 6; own deviation −1.4 %, −3.5 %, −5.2 % at 8°, 9°, 10° against −1.5 %, −4.1 %, −5.1 % on level 5). Past 10° it falls short on that blade (−4.7 % at 11°, −7.5 % at 12° against level 5): the table levels a thin section's lift off three degrees behind its end, where the referee's control has it rising on.
- **Its drag is not checked by these rows.** The lattice reads 9 % (level 6) to 21 % (level 5) less drag at 4° and 26–38 % less from 6° up. On this section in 2-D the fin recipe reads 30–43 % more drag than the resolved referee at 4° and about 10–45 % more from 6° to 9°, where neither settles (`../../section-tables/mesh-recipe/`, the thin symmetric section), so most of that gap is the wall-function mesh on a thin nose; how much is not is open.

### Which blades follow their sections to the end

`../survey.md` now carries both brackets for every blade: where the most loaded strip reaches the end of its section's attached lift (a share of one), and where the lattice's own polar, run through the ends, is 5 % below its line. The 5 % points below are the survey's (lines through 0…6° for a polar, 2° and 6° for the lattice).

| blade | sections of its most loaded strips: t/c, end of the attached range, lift there | common share ° | share of one ° | lattice's own polar 5 % below at ° | simulation 5 % below at ° | lattice lift against the simulation |
|---|---|---|---|---|---|---|
| gen-2 planform, symmetric t/c 0.05 | 0.05; 5.1–5.5°; 0.52–0.57 | 3.8 | 6.3 | 8.6 | 8.0–8.1 | within 3 % to 12° |
| gen-1 centre (t/c 0.046 at the base, 0.055 at the tip) | 0.05; 5.5°; 0.57 | 4.9 | 8.1 | 10.2 | 9.8–9.9 | within 3.5 % to 10° |
| longboard single, raked 45° (t/c 0.08 at the base, 0.068 at the tip) | about 0.07 at Re 2.2–2.7e5; 6.9–7.4°; 0.72–0.77 | 6.1 | 10.1 | 12.8 | 11.6 | within 3.3 % to 14° |
| gen-1 centre planform, t/c 0.09 at the base | 0.09–0.10; 11.3°; 1.1 | 9.5 | 15.7 | beyond 20 | 9.4 | +4 % to 9°, +14 % at 10°, +36 % at 14° |
| side blades, flat inside and cambered (fourteen polars of ten blades) | | 5.6–13.9 | 12.5–25.3 | 16.4 to beyond 20 | 6–14 (the one-degree polars: 7.6–12.5) | |

- **Three symmetric blades follow their sections to the end, and all three have thin sections where the load is highest**: ends at 5–7.5° with a lift of 0.52–0.77 there. The lattice's own polar is 0.4–1.2° late at the 5 % point on them. The longboard single belongs with them, which the record had as unexplained: its base is t/c 0.08, but its thickness tapers and its most loaded strips are short chords near the tip.
- **The thick centre and every side blade leave their line at about 0.6 of what their sections carry**, with every strip still far inside its attached range (the thick centre's most loaded strip is at 6° of its own incidence where its section goes to 11.3°). The tunnel fin does the same in the tunnel, so that is not the simulation's doing alone.
- What separates the two groups is not settled by these polars. Three readings of it, and a thickness series on one planform that tells them apart, are in the next section.

## What separates the two groups: three readings, and a thickness series that tells them apart (2026-11-23, running)

Written before the runs; `sym-series-prediction.txt` is the file as it stood when the container was started (06:20Z).

The two groups differ in how much lift their sections carry at the end of the attached range (0.5–0.8 against 1.0–1.5), and no pair of polars varies that on one planform between a thin and a thick section. Three readings fit all the polars so far:

- **A, what ships**: a blade leaves its line at the common share of its section's own limit, and thin symmetric sections are an exception.
- **B**: a symmetric blade follows its sections to their ends, whatever the thickness, and the thick centre's early break is the wall-function mesh.
- **C**: a strip carries the smaller of two things, its section's own end and a limit that does not depend on the nose: 0.606 of what a thick section of the family carries at that Reynolds number. A thin section ends first; a thick one never reaches its end.

The series: the gen-2 side's planform with symmetric foils of t/c 0.066 and 0.080 (`fin-gen2-planform-sym-tc066.json`, `-tc080.json`; both are referee sections at Re 5.7e5), 8.5 m/s, mesh level 5, beside the t/c 0.05 blade above. Where each reading puts the onset, and the 5 % point 1.6–2.0° later (`series_pred.py`):

| reading | t/c 0.066: onset, 5 % point | t/c 0.080: onset, 5 % point |
|---|---|---|
| A, the common share of its own limit | 5.0°, 6.7° | 6.9°, 8.7° |
| B, a share of one | 8.3°, 10.1° | 11.3°, 13.1° |
| C, the smaller of its own end and 0.606 of the thick section's limit | 7.2°, 9.0° | 7.2°, 9.0° |

A has the t/c 0.066 blade let go earlier than the t/c 0.05 one (6.7° against 8.0°); B and C have it later. B has the t/c 0.080 blade hold four degrees longer than A or C.

### The series on mesh level 5 (in, 2026-11-23 08:15Z)

`results-L5-sym-tc066.json`, `results-L5-sym-tc080.json` (594 000 and 568 000 cells, mean wall y⁺ 70 and 73). Lift against each polar's own line through its rows up to 4°, and the lift the lattice gives the most loaded strip:

| foil | 5° | 6° | 7° | 8° | 9° | 10° | 11° | 5 % below at | most loaded strip: lift at 6° and 7° | its section's lift at the end of the attached range |
|---|---|---|---|---|---|---|---|---|---|---|
| t/c 0.050 (above) | +0.2 % | −0.9 % | −2.2 % | −5.1 % | −7.6 % | −10.9 % | | 8.0° | 0.51, 0.57 | 0.53 |
| t/c 0.066 | 0.0 % | +0.1 % | −1.5 % | −3.5 % | −6.2 % | −11.5 % | −14.5 % | 8.55° | 0.51, 0.60 | 0.71 |
| t/c 0.080 | | −1.1 % | −2.6 % | −3.2 % | −7.0 % | −11.2 % | −14.2 % | 8.5° | 0.52, 0.60 | 0.97 |

| reading | t/c 0.066: said, found | t/c 0.080: said, found |
|---|---|---|
| A, the common share of its own limit | 6.7°, 8.55° | 8.7°, 8.5° |
| B, a share of one | 10.1°, 8.55° | 13.1°, 8.5° |
| C, the smaller of its own end and 0.606 of the thick section's limit | 9.0°, 8.55° | 9.0°, 8.5° |

- **B is out.** The t/c 0.080 blade is 5 % below its line four and a half degrees before a share of one has it there. Its most loaded strip is at 0.53–0.62 of what its section carries where the blade starts to leave (6° to 7°) and at 0.74 at the 5 % point.
- **A is out on the t/c 0.066 blade.** It had that blade let go 1.3° before the t/c 0.050 one; it lets go half a degree after it.
- **C is within half a degree on both, on the late side.**
- **The three blades let go at the same lift of the most loaded strip**, between 0.51 and 0.60, though their sections carry 0.53, 0.71 and 0.97 at the end of the attached range. The thin one is at its section's end there; the other two are cut off at the same level with their sections' ends far away. That is what C says in other words, with the level a little under 0.606 of the thick section's limit (0.59–0.61 at these strips).
- **Not yet a result about blades:** all three meshes have cells of 0.39 mm at a nose whose radius at the most loaded strips is 0.09 to 0.35 mm, so the mesh cannot tell these three noses apart, and a blade that lets go at one level whatever its nose is also what such a mesh would produce. Level 6 on the t/c 0.080 and 0.066 blades is running, with what each outcome would mean written first (`sym-series-controls-prediction.txt`). The same file has a third control, the t/c 0.066 blade at 5 m/s: the longboard single (5 m/s) follows its sections to their ends where this blade (8.5 m/s, sections of the same thickness) lets go at 0.84 of them, and speed and rake are confounded between the two.
- The rows from 6° up ran to the cap; the means of their last four windows of 100 iterations hold within 0.001–0.003 at 6° to 8° on the t/c 0.066 blade and within 0.005 on the t/c 0.080 one (0.013 at 9°).

### The controls: level 6 and half the speed leave the break where it was, a finer nose moves it by 0.7° (2026-11-23)

`results-L6-sym-tc080.json` (1 062 664 cells, mean wall y⁺ 45–47), `results-L5-sym-tc066-5ms.json` (the level-5 mesh at 5 m/s, mean wall y⁺ 42–44 against 70), predictions in `sym-series-controls-prediction.txt`. Then `results-L7-sym-tc080.json`: mesh level 7, which is level 6 with the surface split once more where a level-6 cell still sees more than 30° of it (`finGenerator-cfd`, `fincfd.case`): 1 276 353 cells, mean wall y⁺ 36–37, nose faces of 0.086 mm along the whole leading edge. Prediction in `sym-series-nose-prediction.txt`, written with the two controls read and before the run.

Lift against each polar's own line through 0° and 4°:

| | faces per nose radius at z/depth 0.76 / 0.85 / 0.92 | 6° | 7° | 8° | 9° | 10° | 11° | 5 % below at |
|---|---|---|---|---|---|---|---|---|
| t/c 0.080, level 5 | 0.80 / 0.74 / 0.75 | −1.1 % | −2.6 % | −3.2 % | −7.0 % | −11.2 % | −14.2 % | 8.5° |
| t/c 0.080, level 6 | 1.27 / 1.10 / 0.99 | −0.2 % | −0.6 % | −2.1 % | −6.4 % | −9.6 % | | 8.7° |
| t/c 0.080, level 7 | 3.19 / 2.77 / 2.45 | −0.2 % | −0.3 % | −0.75 % | −2.6 % | −8.4 % (not settled) | −9.2 % | 9.4° |
| t/c 0.066, level 5, 8.5 m/s | 0.61 / 0.49 / 0.40 | +0.1 % | −1.5 % | −3.5 % | −6.2 % | −11.5 % | −14.5 % | 8.55° |
| t/c 0.066, level 5, 5 m/s | the same mesh | +0.2 % | −1.5 % | −3.7 % | −7.6 % | −10.3 % | −13.4 % | 8.3° |

- **Level 6 and half the speed both said "the blade, not the mesh"; level 7 says the mesh is in it.** Level 6 moved the t/c 0.080 blade's 5 % point by 0.2°; at 5 m/s the t/c 0.066 blade has the lift of 8.5 m/s within 0.2 % to 8°. By what was written before them, that was the blade's own break. Level 7 then has the same blade 2.6 % below its line at 9°, where levels 5 and 6 have it 7.0 and 6.4 % below: the branch of its prediction that says the unresolved nose made those strips let go. Its rows at 10° and 11° (written after 9° was read; `nose7-prediction.txt`, item 5) show the break is later, not gone: 8.4 and 9.2 % below, 5 % point at 9.4°. The 5 % points of the three levels are 8.5°, 8.7°, 9.4°, a sequence that has not settled; the lattice run through its sections' ends would have the blade 1.4 % below its line at 10° and 5 % below at 13.2°.
- **Why one level did not show it and two did.** Levels 5 and 6 both put about one face or less on the nose radius of the strips that let go; level 7 puts two and a half to three. Halving the speed changes the wall units of the first cell, not what the mesh sees of the nose. A control one level finer is no control when both levels are on the same side of what has to be resolved: count the faces on the nose radius of the most loaded strips (`strip_loads.py` prints them).
- **So the thickness series on levels 5 and 6 does not carry what was read from it.** The lift at which the outer strips let go rises with the resolution of the nose and has not been shown to settle, so "the same level whatever the thickness" is at least partly the mesh, and none of the three readings above is refuted or supported. What level 7 still shows: the thick blade leaves its line three to four degrees before its sections' ends would have it. The gen-3 side fin's level-5 polar (about one face per nose radius, a sharp break between 9° and 10°) is open in the same way; the flat-inside blades less so, because the curved side of a half-section's nose has four times the radius of a symmetric section of the same thickness.
- Rows: level 6 from 7° up ran to the cap, swinging about means that hold within 0.001 (7°, 8°), 0.004 (9°) and 0.009 (10°) over the last three windows of 150 iterations. On level 7 the rows to 8° stop settled after 146–250 iterations, where 7° and 8° swung on level 6; 9° swings by ±0.02 about 0.554; 10° was still falling at the cap (windows 0.598, 0.595, 0.579: 5.5 to 8.4 % below the line, so the 5 % point is 9.4–9.9°); 11° holds within 0.001.

#### The surface the mesher was given (found 2026-11-23, after level 7 was read)

`stl_nose.py` cuts the fin's STL at a span station and lists the facets around the leading edge. On the surface every 3-D polar so far was meshed on (25 952 triangles):

| span station | chord | nose radius | corner at the leading edge | facets off the section (first 3 % of chord) |
|---|---|---|---|---|
| 60 mm (z/depth 0.43) | 75 mm | 0.53 mm | 16° | up to 0.048 mm |
| 106 mm (0.76) | 37 mm | 0.26 mm | 55° | up to 0.066 mm |
| 119 mm (0.85) | 33 mm | 0.23 mm | 51° and 19° | up to 0.058 mm |

The case builder exported with the library's default tolerance, which is relative: 1e-3 of each face's size, about 0.1 mm on a fin. (This paragraph first blamed a tolerance taken in metres; the export call shows the relative flag.) With 400 points per section and an absolute deflection of 1 µm (`exact_surface` in `fincfd.case`, set by mesh levels 7 and 8; 0.7 million triangles, 14 s, 2.7 GB) the same cuts are within 0.010 mm of the NACA form and no corner exceeds 10°; with the default 100 points per section and fine facets a corner of 31° stays at the leading edge. The reruns below were meshed on the option's first version, which passed 2e-6 to the same relative setting: 2.57 million triangles for the same nose (0.0095 mm, 9°), and a peak of 33 GB while writing it, which is what took the EPYC down on 2026-11-23 when the tunnel fin's case was being written there.

- **What it does to the record above.** Nose faces of 0.31–0.43 mm (level 5) and 0.22 mm (level 6) are three to seven times the facets' error; level 7's (0.086 mm) are the size of it. Both were rerun on the exact surface (`plan-exact-tc080-L6.json`, `plan-exact-tc080-L7.json`; next section): level 6 had read the break 0.3° early on the facets, level 7 up to 0.8° late. Every polar above this section is on the faceted surface; for nose faces of 0.3 mm and more (levels 2 to 5) the error is at most what level 6 shows. Level 8 was stopped before it produced a row.
- **The order was wrong.** `docs/CFD-BENCH.md` has had the rule since 2026-11-21 (the 2-D referee's outline): compare the surface with the analytic shape at the scale of the cells asked for, before refining. The level-7 mesh was run first and the surface looked at after.

#### The thick symmetric blade on the exact surface: levels 6 and 7 agree (2026-11-23, 14:06Z)

`results-exact-L6-sym-tc080.json` (1 057 207 cells, mean wall y⁺ 45), `results-exact-L7-sym-tc080.json` (1 261 916 cells, y⁺ 36). Predictions: `nose7-prediction.txt`, items 10 and 11, and what was found under item 11's date.

**In doubt since 2026-11-24:** this level-7 mesh is not fully on the surface (its last snapping move still wanted 5.4 µm on average and 95 µm at most, a cell being 95 µm; level 6: 0.3 µm). See "Level 7 as it was meshed" below. The agreement of the two levels stands only when the rerun is in (`nose7-prediction.txt`, item 38).

| lift against the line through 0° and 4° | 8° | 9° | 10° | 11° | 5 % below at |
|---|---|---|---|---|---|
| level 6, faceted surface | −2.1 % | −6.4 % | −9.6 % | | 8.7° |
| level 7, faceted surface | −0.75 % | −2.6 % | −8.4 % (not settled) | −9.2 % | 9.4–9.9° |
| **level 6, exact surface** | −1.4 % | −5.0 % | −8.8 % | | **9.0°** |
| **level 7, exact surface** | −0.5 % | −4.8 % | −8.4 % | −10.4 % | **9.1°** |

- **On the exact surface one more level at the nose no longer moves the break.** Lift agrees within 0.8 % at every row between 1.1–1.7 and 2.4–4.1 faces on the nose radius of the outer strips. The 5 % point of this blade is 9.0–9.1°.
- **The faceted surface was visible to both levels, in opposite directions.** Level 6 read the break 0.3° early on it. Level 7 read it late: at 9° the faceted nose carried 2.5 % more lift than the round one, which I had expected the other way round (a corner as the sharper nose). The sequence 8.5°, 8.7°, 9.4° that looked like a mesh not yet converged was a surface changing under the mesh.
- **Rows.** Level 7: 8° stops settled after 177 iterations; 9° holds its mean within 0.002 over three windows; 10° and 11° drift down by 0.02 and 0.01 over the last 450 iterations. Level 6: all rows from 8° at the cap, means within 0.003 (8°), 0.007 (9°), 0.009 (10°).
- **The strips, on both levels:** the ones at z/depth 0.65 to 0.92 are 5 % short of the lattice at blade angles of 8.0° to 8.7°, at a lattice strip lift of 0.56–0.70, which is 0.61–0.72 of what their sections carry and 3.3–4.1° of incidence before their sections' ends. With the nose loading of those strips (1.03, 1.08, 1.14 at z/depth 0.76, 0.85, 0.92) the share is 0.73–0.76 at all three.
- **Reproduced on the surface as it is written now and on another machine** (`results-exact-L6-sym-tc080-laptop.json`; absolute deflection of 1 µm, 0.7 million triangles, 12 processes on the laptop): 0.2527 at 4° and 0.5401 at 9° against 0.2527 and 0.5404, 1 057 339 cells against 1 057 207.
- **What that is and is not.** It is this recipe's answer for this blade, no longer the mesh's or the surface's: wall functions, a boundary layer turbulent from the nose. It is two degrees after the strip criterion's onset (6.9°) and four before the lattice run through its sections' ends (13.2°). Whether the gap to the sections' ends is the blade (three dimensions) or the recipe (wall functions against the table's resolved wall) is not separated by it. The thinner blades of the series have not been rerun on the exact surface, so the three readings stay open.

#### The gen-3 side fin and the gen-2 side on the exact surface (2026-11-24)

`results-exact-L6-gen3-side.json` (1 206 026 cells, mean wall y⁺ 40), `results-exact-L6-gen2-side.json` (1 009 563 cells, y⁺ 48); level 6, 8.5 m/s. Predictions: `nose7-prediction.txt`, items 13, 14 and 16, each with what was found.

| lift against the line through 0° and 4° | 8° | 9° | 10° | 11° | 12° | 13° | 14° | 5 % below at |
|---|---|---|---|---|---|---|---|---|
| gen-3 side, level 5, faceted surface | −2.1 % | −3.9 % | −16.0 % | −17.7 % | −20.6 % | | | 9.1° |
| **gen-3 side, level 6, exact surface** | −0.2 % | −0.6 % | −1.6 % | −3.0 % | −4.0 % | −17.6 % | −24.0 % | **12.1°** |
| **gen-3 side, level 7, exact surface** (line through level 6's 0° and its own 4°; a mesh the mesher flags, below) | | | −1.3 % | −2.2 % | −3.6 % | −4.6 % | −19 % | **13.0–13.1°** |
| gen-2 side, level 6, faceted surface | −1.6 % | −4.0 % | −10.7 % | | −14.3 % | | | 9.2° |
| **gen-2 side, level 6, exact surface** | −1.7 % | −5.7 % | −11.1 % | −14.6 % | | | | **8.8°** |
| **gen-2 side, level 7, exact surface** (against level 6's line; a mesh not fully on the surface, below) | −2.4 % | −4.6 to −7.0 % | −9.8 to −10.9 % | | | | | **8.7°** |

- **The gen-3 side fin's break at 9° to 10° was the surface and the mesh. On the exact surface it lies between 12° and 13°.** Rows to 11° stop settled after 166–200 iterations. At 12° the row runs to the cap but holds 1.071–1.076 over its last 150 iterations (lift 1.073, 4.0 % below the line). At 13° and 14° it swings (0.91–1.04 and 0.88–1.04) about means of 0.98 and 0.95.
- **In the simulation its lift falls when it breaks: 345 N at 12°, 314 N at 13°, 306 N at 14°.** I had expected a 5 % point at 9.3–9.9° (item 13), and with the rows to 11° in hand wrote here that the fall of lift in one degree seen on level 5 "does not exist on this surface". It does, three degrees later. **It is not evidence of how the fin lets go**: on the tunnel fin the same recipe has a fall after the break that the tunnel does not have (next section).
- **The gen-2 side stays where it was, within 0.4°**: 5 % below at 8.8° (9.2° on the facets), rows from 9° at the cap, their window means within ±1.5 % (8.7–8.9° for the 5 % point). Its lift goes on rising through the break: 260, 272, 277, 286 N at 8° to 11°.
- **So the two fins are much further apart than the strip criterion has them.** Criterion: 6.6° and 7.4°, 234 N and 258 N (10 % apart). Simulation on the exact surface: 8.8° and 12.1°, about 270 N and 345 N (28 % apart), the gen-3 fin on 11 % less area.
- A cambered thin nose is where the faceted surface cost most: three degrees here, against 0.3° on the thick symmetric blade and 0.4° the other way on the flat-inside one. Every earlier polar of a cambered fin in this record (the 3 % camber planform, the candidate, the tip-width pair) is on that surface and is a lower bound on its break by an unknown amount.
- **Level 7 does not confirm level 6 on this fin** (`results-exact-L7-gen3-side.json`; 1 431 211 cells, mean wall y⁺ 31; items 17 and 20). Lift at 4°, 10°, 11°, 12°: 0.5875, 0.9771, 1.0343, 1.0832, which is 0.4–1.4 % above level 6. At 13°, where level 6 swings about 0.93–0.98, level 7 is attached: the row runs to the cap holding 1.1349–1.1377. The break level 6 put between 12° and 13° was the mesh's, as level 5's at 9° to 10° had been. **Rows at 14° and 15° (item 32) bracket it: 1.0225 and 1.0306, both swinging** (window means 1.013–1.020 and 1.005–1.050, inside the last window 0.97–1.06 and 0.94–1.09), after 1.1361 at 13°. The 5 % point on that mesh is 13.0–13.1°, at a lift of 1.14 (366 N), a degree after level 6's. **But that mesh carries 715 693 faces the mesher flags, and the level-8 probe (item 33: flagged faces, solver diverging within 18 iterations) failed for the same reason: a threshold of the recipe, not the level.** See "Level 7 as it was meshed" below. Whether level 7 has this fin's break is open until both are rerun.
- **So "level 6 on the exact surface" is not a recipe for every fin.** It held on the symmetric t/c 0.080 blade (9.0° and 9.1° on levels 6 and 7) with 1.1–1.7 faces on the nose radius of the strips that let go. This fin has 1.8–2.7 and is not settled: the count of faces on the nose radius does not say when a nose is resolved. What differs is where the break is: at 6–7° of strip incidence on the symmetric blade, at 7–8° here, under a deeper suction peak (−4.2 against −3.3 on level 6).
- **Level 7 reads the gen-2 side as level 6 does** (`results-exact-L7-gen2-side.json`; 1 215 487 cells, mean wall y⁺ 39; item 19): 0.4758 and 0.7179 at 4° and 8° (level 6: 0.4764, 0.7226), window means 0.744–0.763 at 9° (0.744–0.755) and 0.771–0.780 at 10° (0.769–0.775). Its 5 % point is 8.7° on level 7 and 8.8° on level 6. **Not a confirmation yet (found the same afternoon):** that level-7 mesh is not fully on the surface (below), so the two levels agreeing says less than I wrote here at noon. Rerun queued (item 37).
- **Withdrawn until those reruns are in: "refinement moves the round nose and not the cornered one".** I read the pair of level checks as a flat-inside corner fixing the break on any mesh and a round nose holding longer the finer it is meshed. One of the two level-7 meshes was unsnapped in places and the other flagged; the reading rests on neither.

#### The tunnel fin on the exact surface (2026-11-24)

`results-exact-L6-bw04.json` (EPYC, 8 processes; 1 269 598 cells, mean wall y⁺ 34; level 6, 7 m/s) and `results-exact-L6-bw04-laptop.json` (the same plan to 14° on 12 processes; its long wall times are the laptop's sleep). The two agree to four digits on every settled row. Predictions: `nose7-prediction.txt`, items 12 and 18.

| | 11° | 12° | 13° | 14° | 15° | 16° | 20° |
|---|---|---|---|---|---|---|---|
| lift, level 6, exact surface | 0.8435 | 0.8977 | 0.9496 | 0.94–1.01 (swings) | 0.89 | 0.86 | 0.75–0.77 (swings) |
| against its line through 0° and 4° (0.2135, 0.4447) | −0.7 % | −1.0 % | −1.6 % | −1.5 to −8 %, about −5 % | −17 % | −25 % | −45 % |
| level 5, faceted surface (`results-L5bw04.json`) | −1.7 % | −1.9 % | −8.2 % | −13.0 % | | −30 % | |
| tunnel [BW04]: lift | | 0.775 | | 0.82 | | 0.89 | 1.02 |
| tunnel, against its stated line (0.05 per degree from −3.5°) | | on it | | −6.3 % | | −8.7 % | −13 % |

(Tunnel points past 12° are read off the paper's figure, ±0.03 in lift, which is ±3.5 % here.)

- Rows at 11° to 13° stop settled after 176–186 iterations. **The row at 14° swings, and its filed value is the mean of its last 150 iterations only.** On the laptop the three windows of 150 iterations before the cap average 1.006, 0.944, 1.000 (range inside the last 0.973–1.021) and the row is filed as 0.9989; on the EPYC they average 0.996, 0.960, 0.944 (0.857–1.014) and it is filed as 0.9448. Rows at 15° and 16° swing by ±0.04 about 0.89–0.91 and 0.84–0.88.
- **With the surface right, the simulation begins to break where the tunnel does**: steady and 1.6 % below its line at 13°, swinging about 5 % below it at 14°, where the tunnel has the fin on its line at 12° and 6 % below at 14°. Level 5 on the facets had it 8 % below at 13° already. I first read the laptop's filed 0.9989 as "2.3 % below at 14°, later than the tunnel"; that was one window of a swing, and the second machine showed it.
- **Past the break the two part, and the simulation is the one that is wrong.** Its lift falls: 0.95 at 13°, 0.89 at 15°, 0.86 at 16°. The tunnel's goes on rising at about two thirds of its slope: 0.82, 0.89, 0.96, 1.02 at 14°, 16°, 18°, 20°. This is the boundary `docs/CFD-BENCH.md` already names (steady, fully turbulent RANS levels off near 0.87 where the measured fin climbs to 1.10 at 24°); the exact surface has not moved it. **So this recipe says where a fin begins to let go. It does not say what the fin carries afterwards, nor how abruptly it lets go.**
- **At 20° the simulation carries 0.76 where the tunnel has 1.02** (item 29; window means 0.754, 0.774, 0.756, inside the last 0.72–0.79). I expected it on the old plateau, 0.84–0.90, which was read on levels 2 and 5 to 16° and on level 2 at 20° (0.862). On this mesh the lift goes on falling past 16°, where level 2 held 0.86: what the simulation carries past the break depends on the mesh as well. The same fin with the volume around it refined (item 30) is in the section after this one: it changes the row at 16°.
- The simulation's line is 16 % steeper than the tunnel's (0.0578 against 0.05 per degree; a third of that is the tunnel wall's boundary layer, `docs/CFD-BENCH.md`), so in lift the simulation carries 0.95 at 13° where the tunnel's line has 0.825.
- **What it means for the other fins.** This is the one break in the record with a measurement beside it, and on level 6 with the exact surface the recipe has its onset within about half a degree (**on this volume mesh; with the volume refined it is about two degrees later, next section**). The 5 % points of the two side fins above stand on the same recipe. Their rows past those points do not: the fall of the gen-3 fin's lift from 12° to 13° and the gen-2 side's lift rising on through its break are both in the regime where this recipe has the tunnel fin falling and the tunnel has it rising.

#### The tunnel fin with the volume around it refined: the break moves two degrees (2026-11-24, 14:40Z)

Tobias asked why the simulation is wrong past a break: the method, how it is applied, or the mesh. The one thing never varied in this record was the volume mesh off the wall: on every level the cells are a quarter of the background cell from 7 mm off the fin and half of it beyond. `CaseSpec.volume_shells` refines it: on the tunnel fin, cells of 0.625 mm to 10 mm off the wall, 1.25 mm to 25 mm, 2.5 mm to 50 mm, on the level-6 surface mesh (`results-exact-L6-bw04-shells.json`; 2 365 973 cells against 1 269 598, mean wall y⁺ 34, mesher clean, peak 5.1 GiB with 8 processes). Predictions: `nose7-prediction.txt`, items 29–31 and 39–41.

| tunnel fin, 7 m/s | 4° | 13° | 14° | 15° | 16° | 18° | 20° |
|---|---|---|---|---|---|---|---|
| level 6, volume as it was | 0.4447 | 0.9496 | 0.97–1.02 (swings) | 0.89 | 0.84–0.88 (swings) | – | 0.75–0.77 (swings) |
| **level 6, volume refined** | 0.4429 | 0.9447 | 1.003 (range 0.992–1.014) | 1.042–1.053 over three windows (range 1.028–1.061) | **1.07–1.08** (range 1.06–1.10) | 1.05–1.07 over three windows (range 0.95–1.09) | 0.78, 0.86, 0.92 over three windows (range 0.71–1.00), not settled |
| against the line through 0.2135 and its own 4° | | −1.5 % | −1.3 % | −1.9 to −3.0 % | −4.2 to −5.1 % | −14 to −16 % | |
| tunnel [BW04]: lift | | about 0.80 (0.775 at 12°) | 0.82 | | 0.89 | 0.96 | 1.02 |
| tunnel, against its stated line | | on it at 12° | −6.3 % | | −8.7 % | −11 % | −13 % |

- **Before the break the volume does not matter**: 0.4 % and 0.5 % at 4° and 13°, as item 30 required.
- **At 16° it decides the row.** On the mesh as it was the fin has broken there (0.86, 25 % below its line, drag 0.189). With the volume refined it carries 1.08, about 5 % below its line, at the same drag (0.186). I had not forecast this row.
- **So where this fin's lift is 5 % below its line depends on the volume mesh: about 14° as meshed, about 16° refined, 13–14° in the tunnel.** The agreement "within about half a degree" on level 6 (above) owed something to a coarse volume. With the volume resolved, the simulation holds the lift about two degrees longer than the tunnel does. That is the direction in which the two-dimensional recipe misses a measured section (`docs/CFD-BENCH.md`: the resolved recipe peaks 19 % high and 2° late against [SK81]). Rows at 14°, 15° and 18° bear it out (in 16:08Z; item 39): the two meshes carry the same lift at 14° and part between 14° and 15°, and on the refined volume the lift is 1.3 % and 2–3 % below its line there, each row swinging by about 1 %. At 18° the row swings between 0.95 and 1.09 about 1.05, below the 16° row. **The 5 % point on the refined volume is at 16.1°, the highest lift about 1.08 at 16–17°; the tunnel's 5 % point is at about 13.6° (12° on its line, 14° at −6.3 ± 3.5 %), so the simulation is two to three degrees late.** Against the forecast: 14° came out 0.7 % above the range given for it, 15° at its upper edge, 18° as said.
- **At 20° neither mesh has the tunnel's 1.02**, and the refined row does not settle: it fell to 0.71 and was climbing through 0.92 at the cap. A steady solver on a flow that is not steady; a time-accurate run on this mesh (item 31) is what could say what the model carries there.
- **Every 5 % point in this record is on the volume mesh as it was.** The gen-2 side and the gen-3 side run next with the same shells (items 40, 41). If both move by about the tunnel fin's two degrees, the ratios between fins may stand while the angles do not. If they move by different amounts, the ratios are the mesh's too.

#### Level 7 as it was meshed: a volume threshold that did not scale (found 2026-11-24, 13:45Z)

The tunnel fin's level-7 run (item 26) stopped in its first row: the mesher ended "with 828882 illegal faces" and the solver diverged. That sent me to the mesher's logs of every exact-surface mesh, which I had not read for the level-7 ones.

The recipe's `minVol` was 1e-13 m³: the smallest volume the mesher accepts for the pyramid from a face to its cell's centre. It is an absolute number, and the mesh scales with the fin's base chord. An untouched cube of edge a has pyramids of a³/6.

| mesh | finest cell | its pyramid over the threshold | faces flagged at the end | what the last snapping move still wanted, mean / largest |
|---|---|---|---|---|
| gen-2 side, level 6 | 0.193 mm | 12 | none | 0.3 µm / 13 µm |
| symmetric t/c 0.080, level 6 | 0.193 mm | 12 | none | 0.3 µm / 24 µm |
| gen-3 side, level 6 | 0.163 mm | 7.3 | none | 0.4 µm / 55 µm |
| tunnel fin, level 6 | 0.156 mm | 6.4 | none | 0.4 µm / 63 µm |
| **gen-2 side, level 7** | 0.096 mm | 1.5 | none | **3.8 µm / 91 µm** |
| **symmetric t/c 0.080, level 7** | 0.096 mm | 1.5 | none | **5.4 µm / 95 µm** |
| **gen-3 side, level 7** | 0.082 mm | 0.91 | **715 693** (12 over 65° of non-orthogonality, 20 collapsed) | 0.2 µm / 7 µm |
| **tunnel fin, level 7** | 0.078 mm | 0.79 | **828 882** (6 and 23); solver diverged | 0.2 µm / 3 µm |
| **gen-3 side, level 8** (probe) | 0.041 mm | 0.11 | **3 115 616** (29 and 26); solver diverged | |

- **Below the threshold every finest cell is an error before snapping starts** (760 836 faces on the gen-3 fin). The mesher accepts a snapping move when it leaves no more errors than it began with, so its quality control is switched off: the surface is snapped in full, and the few dozen cells that the snap collapses or skews pass with the rest. The gen-3 fin's solver ran on them; the tunnel fin's and level 8's did not.
- **Just above it the mesher refuses the snap instead.** With the threshold at two thirds of a cube's pyramid, a move that squeezes a finest cell by a third fails the check and is scaled back, to nothing where it has to be (a scaling of zero appears 25 times in the gen-2 side's log and never in the gen-3 fin's). The mesh ends "without any errors" and part of its surface is not on the fin: ten times the level-6 meshes' residual on average, a whole cell at most. Where on the blade those points are, I have not looked.
- **So no level-7 result in this record stands as it was read**: not the thick symmetric blade's agreement of levels 6 and 7 (9.0° and 9.1°), not the gen-2 side's (8.8° and 8.7°), not the gen-3 side's later break (13.0–13.1° against 12.1°). What I told Tobias at 11:50Z, that levels 6 and 7 end without flagged faces, was wrong for the gen-3 fin. **Level 6 is not touched by this**: the threshold is 8–16 % of its finest cells' pyramids, all four meshes end clean and are on the surface to under half a micrometre on average.
- **Fixed in finGenerator-cfd** (`fincfd.case._min_vol`): a fifth of the finest cube's pyramid, and never above 1e-13, so every mesh up to level 6 is written as it was. The polar driver now prints and files what the mesher says of each mesh (`mesh` in a results file: cells, flagged faces and the failed checks, what the last snapping move still wanted).
- **Rerun with it** (`nose7-prediction.txt`, items 34–38): the tunnel fin, the gen-2 side, the gen-3 side and the thick symmetric blade on level 7; the gen-3 side on level 8 if its mesh is then clean. The thin symmetric blades (items 27, 28) and the first swap on level 7 (item 22″) had not started and get the fixed threshold.

#### Strip loads of the three fins (2026-11-24)

`strip-loads.txt`, runs `gen3-side-sliders-L6x`, `flat-inside-L6x`, `bw04-L6x-laptop` (level 6, exact surface). Prediction: `nose7-prediction.txt`, item 21.

| the strip is 5 % short of the lattice at | z/depth 0.38 | 0.52 | 0.65 | 0.76 | 0.85 | 0.92 |
|---|---|---|---|---|---|---|
| gen-2 side: blade angle | 10.3° | 9.7° | 8.8° | 8.2° | 8.6° | 9.5° |
| lattice strip lift there | 0.87 | 0.92 | 0.97 | 0.99 | 0.95 | 0.85 |
| share of the section's limit | 0.55 | 0.60 | 0.66 | 0.70 | 0.68 | 0.62 |
| gen-3 side: blade angle | 12.7° | 12.2° | 12.1° | 11.7° | 12.0° | 12.2° |
| lattice strip lift there | 1.17 | 1.25 | 1.28 | 1.18 | 1.08 | 0.97 |
| share of the section's limit | 0.72 | 0.78 | 0.81 | 0.75 | 0.69 | 0.63 |
| faces on the nose radius, gen-3 side | 3.2 | 2.7 | 2.4 | 2.3 | 2.1 | 1.8 |

- **Up to its last attached row each fin's strips are on the lattice**: within 1 % inboard on all three, 3–5 % short at z/depth 0.65–0.85 on the gen-3 fin at 11° and 12°. The two strips at the tip gain 10–80 % on the lattice as the angle rises, as on the symmetric blades.
- **The most loaded strip's share of its section's limit at the last attached row** (lattice, same mirror): tunnel fin 0.66 at 13° (0.70 at 14°, where its strips at z/depth 0.76 and 0.85 are the first to lose ground); gen-2 side 0.68 at 8° (0.74 at 9°); symmetric t/c 0.080 blade 0.70–0.72; **gen-3 side 0.81 at 12°**. The two flat-inside fins and the symmetric blade let go at one share, about 0.70, on planforms as different as the tunnel fin's and the gen-2 side's: the strip rule carries the planform. The cambered fin holds to 0.81 or more of a limit that is already the highest of the four (1.58 against 1.42 on the gen-2 side's strip). One share for every section, as `bladehydro.knee` has it, reads the cambered fin early by that ratio.
- **The gen-3 fin lets go all at once, the gen-2 side from the outside in.** On the gen-3 fin every strip from the root to the tip falls 5 % short within 11.7° to 12.8° of blade angle. On the gen-2 side the strips at z/depth 0.65–0.85 go at 8.2° to 8.8°, the ones inboard of them hold to 9.7°, 10.3°, 10.5°, and the root strip is not 5 % short at 11°. In the simulation that is the fall of lift on the one and the flattening on the other; these are rows past the break, which the tunnel fin shows this recipe does not get right (above). The lattice's strips alone do not show it: the angles at which the six strips from z/depth 0.38 to 0.92 reach a common share are spread over 3.7° on the gen-3 fin and 4.7° on the gen-2 side. Once the mid-span strips of the gen-3 fin go, their neighbours go with them.
- **Nose suction before letting go**, lowest pressure coefficient on the strips at z/depth 0.52–0.85: gen-3 side −3.6 to −4.2 (12°), gen-2 side −1.6 to −2.2 (8°), tunnel fin −1.9 to −2.4 (13°), symmetric blade −2.4 to −3.3 (8°). All on level 6, whose faces clip the peak (on the symmetric blade level 7 reads −5.2 where level 6 reads −2.8), so this compares fins only loosely. Both flat-inside fins let go at the same level.
- **A candidate for the flat-inside level, not tested:** the generator draws a right-angle corner where the flat face meets the outer surface at the nose (`fingen.foil`), and the 3-D surface has it. The table's flat-inside sections were run with that corner rounded to 0.5 mm (`../../section-tables/flat-corner/`: no difference at +2°; not compared at high angles), which is what a sanded print has. So on a flat-inside fin the simulation and the table's section do not have the same nose.
- **Nose loading is not the difference**: 1.02, 1.05, 1.09, 1.14 at z/depth 0.65 to 0.92 on the gen-3 planform, 1.03, 1.08, 1.14 at 0.76 to 0.92 on the gen-2 planform (`nose_loading.py`).
- **The face count uses the local section** (corrected 2026-11-24: it had used the base thickness; the gen-3 fin thickens to 1.16 of it at the tip, the gen-2 planform thins to 0.78). The gen-3 fin has 1.8–2.7 level-6 faces on the nose radius of the strips that let go, more than the symmetric blade on which levels 6 and 7 agreed (1.1–1.7). The gen-2 planform with the gen-3 foil has 0.8–1.4: that swap on level 6 is a lower reading until its level-7 run is in.
- **Run since, to take section and planform apart** (laptop, `~/bench-results/levers10`; `nose7-prediction.txt`, items 22–24 and what the strip picture forecasts for them): the gen-2 planform with the gen-3 section and the gen-3 planform with the gen-2 section are in ("The swaps" below); the gen-3 fin with its tip at 0.35 of the base is running. The tunnel fin on level 7 (item 26) failed in the mesher ("Level 7 as it was meshed"). The gen-2 side to 14° (item 25) was dropped: rows past a break.

#### Strip loads from the surface pressure

`strip_loads.py` sums the pressure on the fin patch of a saved row over the lattice's ten strips (`strip-loads.json`: every run; `strip-loads.txt`: the tables; `strip_loads_all.sh` makes both), and sets each strip beside the lattice's strip on table v1, run through its sections' ends.

Corrected 2026-11-24: the case sinks the fin 2 mm below the floor, and the strips were cut 2 mm too far inboard on the fin. With the stations right the numbers of this section moved by 0.03 at most, the face count at the nose is read at the nose of every strip, and the last strip is no longer empty. All runs were extracted again.

- **Until a strip lets go, the lattice has every strip's lift within 1–2 %** on the t/c 0.066 and 0.080 blades, at every angle and on every mesh (the t/c 0.050 blade's inboard strips run 2–5 % above the lattice from 5° on). The two strips at the tip are the exception: the one at z/depth 0.97 gains 5–15 % on the lattice as the angle rises, the last 15–50 %. The lift line of a blade is the sum of strips that each behave as the lattice says.
- **The strips that let go first are at z/depth 0.76 to 0.92**, by a collapse of the suction peak at the nose while the inboard strips' peaks go on rising. The lattice's strip lift where the simulation's strip is 5 % short:

| | z/depth 0.76 | 0.85 | 0.92 | what the section carries there at the end of its attached range |
|---|---|---|---|---|
| t/c 0.050, level 5 | 0.58 | 0.55 | 0.49 | 0.53–0.51 |
| t/c 0.050, level 6 | 0.57 | 0.44 | 0.47 | |
| t/c 0.066, level 5 | 0.61 | 0.48 | 0.46 | 0.71–0.68 |
| t/c 0.066, level 5, 5 m/s | 0.58 | 0.47 | 0.48 | |
| t/c 0.080, level 5 | 0.65 | 0.50 | 0.48 | 0.97–0.92 |
| t/c 0.080, level 6 | 0.63 | 0.57 | 0.50 | |
| t/c 0.080, level 7 | 0.71 | 0.66 | 0.68 | |

  The same level on three thicknesses, two meshes and two speeds is what a nose the mesh cannot see produces; level 7 lifts it at the two strips that go first. (Rows that swing are one instant of the swing: ±0.05 on these numbers.)
- **The suction peak itself was clipped.** Lowest pressure coefficient on the strips at z/depth 0.65–0.92 at 7°, before any of them has let go: −2.2 to −2.9 on level 6, −3.4 to −4.1 on level 7.

#### The swaps: section and planform taken apart (2026-11-24)

Level 6, exact surface, 8.5 m/s, on the laptop (`~/bench-results/levers10`). Predictions: `nose7-prediction.txt`, items 22–24 with the forecasts added under them.

| lift against the line through 0° and 4° | 7° | 8° | 9° | 10° | 11° | 12° | 5 % below at | lift there |
|---|---|---|---|---|---|---|---|---|
| gen-2 side (flat inside, t/c 0.092) | | −1.7 % | −5.7 % | −11.1 % | −14.6 % | | 8.8° | 0.75 |
| **gen-2 planform with the gen-3 section** (4.5 % camber, t/c 0.083; `results-swap-gen2-planform-gen3-section-L6.json`) | −0.5 % | −1.5 % | −6.3 % | −9.9 % | −12.0 % | −13.9 % | **8.7°** | 0.81 |
| **gen-3 planform with the gen-2 section** (flat inside, t/c 0.092; `results-swap-gen3-planform-gen2-section-L6.json`) | | −1.5 % | −2.5 % | −3.4 % | −4.2 % | −14 to −18 % | **11.1°** | 0.98 |
| gen-3 side (the same section on its own planform) | | −0.2 % | −0.6 % | −1.6 % | −3.0 % | −4.0 % | 12.1° | 1.07 |

- **On the gen-2 planform the cambered section breaks at the angle the flat-inside one does, 8 % higher in lift** (1 029 850 cells, mean wall y⁺ 45; rows to 8° settled, from 9° at the cap with window means within ±0.7 %). Neither of item 22's alternatives: not at the gen-2 side's lift (0.75), not above 0.85. The forecast from the gen-3 fin's share (0.81 of the section's limit: 9.3–9.8°) is missed by more than half a degree.
- **Strips** (`strip-loads.txt`, run `gen2-planform-gen3-section-L6x`): the ones at z/depth 0.76 and 0.85 are the first to be 5 % short, at 8.1° of blade angle, at 0.75 and 0.72 of their sections' limit and 5.6° and 5.0° of incidence. Between the flat-inside fins' share (0.70) and the gen-3 fin's (0.81).
- **A lower reading until level 7 is in.** This planform thins to 0.78 of its base thickness at the tip, so the cambered foil is t/c 0.067–0.072 on the strips that let go, with 0.8–1.4 level-6 faces on the nose radius (the gen-3 fin, which thickens to its tip, has 1.8–2.7 on a local t/c of 0.092). Queued behind the other two swaps.
- **What it already says:** the section alone does not carry the gen-3 fin to 12°. On this planform the same foil is worth 8 % in lift and nothing in angle. The rest is the gen-3 planform and its thickness schedule: the outer sections there are a third thicker (t/c 0.092–0.096 against 0.067–0.072), and its wide tip keeps the outer strips' incidence lower at the same blade angle (7.7° at 12° of blade angle, where the gen-2 planform has 8.9°).

**The planform swap (in 2026-11-24, 13:36Z; item 23).** 1 169 314 cells, mean wall y⁺ 41. Lift 0.2808 and 0.5531 at 0° and 4°; 0.8128, 0.8715, 0.9290 at 8° to 10° (stopped settled after 176–194 iterations), 0.9868 at 11° (at the cap, steady to 0.0001); 12° swings (window means 0.944, 0.901, 0.912), 13° 0.87.

- **The planform carries most of it.** With the gen-2 side's flat-inside section the gen-3 planform breaks at 11.1° at a lift of 0.98 (317 N at 11°), against 8.8° and 0.75 on the gen-2 planform. Item 23's first alternative in lift ("near 1.0"), 0.4° before its range. The forecast from the flat-inside fins' share (item 23′: 9.6–10.2° at 0.89–0.93) is missed by a degree.
- **On level 6 the lift at the 5 % point comes apart into two factors:**

| lift at the 5 % point (angle), level 6 | gen-2 planform | gen-3 planform | planform alone |
|---|---|---|---|
| flat inside, t/c 0.092 | 0.75 (8.8°) | 0.98 (11.1°) | ×1.31, +2.3° |
| 4.5 % camber, t/c 0.083 | 0.81 (8.7°) | 1.07 (12.1°) | ×1.32, +3.4° |
| section alone | ×1.08, −0.1° | ×1.09, +1.0° | |
| strip criterion, lift at its knee | 0.649 and 0.650 | 0.788 and 0.803 | ×1.21 to ×1.24; section ×1.00 to ×1.02 |

  The criterion has the planform's direction and two thirds of its size, and the section at nothing where the simulation has 8–9 %.
- **The share at which a strip lets go does not go with the section family alone** (`strip-loads.txt`, run `gen3-planform-gen2-section-L6x`). On this fin every strip is within 4 % of the lattice at 11°; the most loaded one (z/depth 0.65) is then at 0.77 of its section's limit and 7.0° of incidence. The same flat-inside family lets go at 0.70 and 6.0° on the gen-2 planform and on the tunnel fin. By planform, the first strip to go: gen-2 planform 0.70 (flat inside) and 0.75 (cambered); gen-3 planform 0.77 and 0.81. Each section's limit is already read at the strip's own thickness and Reynolds number, so this is something the lattice with its section table does not carry.
- **What differs between the planforms, as candidates and not tested:**
  - *The mesh.* It scales with the base chord, and the gen-2 planform's outer chords are small against its base (tip at 0.37 of it, against 0.60). The strip that lets go first has 200 level-6 cells on its chord on the gen-2 side (38.9 mm) and 290 on the gen-3 planform (47.7 mm). The level-7 check that would rule this out for the gen-2 side is in doubt (below).
  - *Thickness.* Flat inside, the first strip to go is t/c 0.077 on the gen-2 side, 0.090 on the tunnel fin, 0.101 here. The table has the limit and the end of each, and the share should be the same if the table were all.
  - *Not sweep:* 28.0°, 25.9° and 25.0° on the gen-2 side, the gen-3 planform and the tunnel fin.
- Like the gen-3 side, this fin's strips are all 5 % short within one degree of each other (11.1° to 11.8°, read between the rows at 11° and 12°, the second of them past the break).
- **Limits of this table.** Level 6 only. The cambered section on the gen-2 planform is a lower reading (above). On level 7 the gen-3 side reads 13.0–13.1° at 1.14, which would put the section at ×1.16 on the gen-3 planform, on a mesh that is flagged. Nothing in `bladehydro.knee` is changed by it yet.

#### The narrow tip on the exact surface: 8°, and not yet believed (2026-11-24, 16:20Z)

The gen-3 side fin with its tip at 0.35 of the base instead of 0.60 (`fin-gen3-tip035.json`, 8 095 mm²), level 6, exact surface, volume as meshed, on the laptop (`results-exact-L6-gen3-tip035.json`: 1 155 529 cells, no flagged faces, snap residual 0.42 µm, mean wall y⁺ 39). Prediction: `nose7-prediction.txt`, item 24 and the two forecasts under it.

| lift against the line through 0° and 4° | 8° | 9° | 10° | 11° | 12° | 13° | 5 % below at | lift there |
|---|---|---|---|---|---|---|---|---|
| gen-3 side, tip 0.60 (above) | −0.2 % | −0.6 % | −1.6 % | −3.0 % | −4.0 % | −17.6 % | 12.1° | 1.07 |
| **the same, tip 0.35** | −5.3 % (−3.1 to −5.4 over three windows) | −8.0 % | −10.3 % | −12.1 % | −16.3 % | −18.7 % | at or just before 8° | 0.81 |

(0.3234 and 0.5908 at 0° and 4°; 0.8131, 0.8509, 0.8899, 0.9310, 0.9416, 0.9698 from 8° to 13°. Every row from 8° on ran to the iteration cap and swings by 1.5–2.5 %. There is no row between 4° and 8° yet: 6° and 7° are running, item 45.)

- **None of the forecasts.** The criterion's lever said 10–10.5° (1.8° before the wide tip), the strip share 9.3–9.8°, the strip incidence 10.0–10.5°, and "the pair's difference was the facets" within a degree of 12.1°. The fin leaves its line four degrees before its twin, at a lift of 0.81 against 1.07: a ratio of 0.76 where the criterion has 0.86.
- **It is the outer quarter of the span** (`strip-loads.txt`, run `gen3-side-tip035-L6x`). The four strips at z/depth 0.76–0.97 (chords 32 to 18 mm) carry 0.76–0.81 of the lattice's lift at 8°, normalised at 4°, and fall 5 % short at 4.8–5.1° of blade angle, at 0.42–0.57 of their sections' limit and 1.2–3.7° of section incidence. No strip of any other fin in this record lets go below 0.66 of its limit. Inboard of z/depth 0.52 the strips hold to 11–12.6°.
- **Those four strips are the coarsest in the record, twice over.** Faces per nose radius: 1.6, 1.4, 1.25, 1.0 (the wide tip: 1.8–2.7). And the volume: as meshed the cells are 0.33 mm from 3 mm off the wall and 0.65 mm from 7 mm, a 150th of the root chord and a 50th of these. The volume moved the tunnel fin's break by two degrees with a tip chord of 45 mm (above). I had counted neither before the run.
- **The exact surface moved the wide tip and not the narrow one.** On the facets at level 5 the pair read 9.1° and 7.6° (lines through 0° and 6°); on the exact surface at level 6, 12.1° and about 8°. A blade whose noses are still under-resolved after the change would do that.
- **So 8° is a lower reading of this fin's break**, as the cambered section on the gen-2 planform is. Queued on the EPYC (items 46, 47): this fin with the volume shells, and on level 7. If neither moves it, the tip lever is about twice what the strip rule reads, and the rule is wrong for narrow tips.

#### What a blade does to a strip's nose

On a finite blade a strip carries more of its lift at the nose than the same section in two dimensions, more so toward the tip of a swept blade ([Pol96]; at the root of rectangular wings 1.08 to 1.36 times at aspect ratios 2.5 to 1.0, computed and borne out by measured nose pressures at 1.4 and 1.0), and separation at the nose follows that loading, not the strip's lift. `nose_loading.py` reads it off the lattice (first chordwise panel's share of the strip's circulation over a two-dimensional plate's): on the gen-2 planform 1.03 at z/depth 0.76, 1.08 at 0.85, 1.14 at 0.92, 1.24 at 0.97; on the tunnel fin 1.11, 1.17, 1.23, 1.33. The strip criterion compares strip lift with the section's limit and has neither this nor the sweep factor of the measured swept-wing record ([Maki51], [HM64]; `../../section-gate/measured/README.md`). Both are known, parameter-free terms; the one fitted number (0.606 on the tunnel fin) presently stands in for them and for the table's sections ending later than measured ones.

#### Flex: every simulation here is of the rigid blade (2026-11-23)

All 2-D and 3-D runs use the unloaded shape; the knee is computed for the rigid blade. The flex model (`fingen.flex`: bending, and an incidence change per station from rake coupling and torsion) is used for the structural gates and a small lift change, and is not fed back into either. At 250 N and 8.5 m/s in PPA-CF it gives the gen-2 side a tip deflection of 5.5 mm and +0.2° at the tip, the gen-3 side 8.5 mm and −1.1°, the commercial-shaped tunnel fin 2.5 mm and +0.2°.

`flex_knee_whatif.py` turns each lattice strip by that incidence change at the blade's own load and reads the knee again. **A what-if, not a result** (the twist has only a sign check against [Zar14], and no flexed blade has been simulated):

| | rigid knee | with the flex model's twist |
|---|---|---|
| gen-2 side, PPA-CF | 7.06°, 224 N | 6.93°, 223 N |
| gen-3 side, PPA-CF | 7.89°, 250 N | 7.96°, 252 N |
| gen-3 side, PET-CF | 7.89°, 250 N | 7.99°, 253 N |
| tunnel fin's shape, PPA-CF | 12.30°, 292 N | 12.08°, 291 N |

Under 1.5 % in force and 0.25° in angle: the gen-3 side's tip twists off by a degree, but the strip that reaches its limit first sits at z/depth 0.65, where the change is −0.2°, and the inboard strips twist the other way. **Pinned, to run once the rigid blade is settled on the exact surface:** one polar of the gen-3 side on its flexed shape (deflection and incidence change per station from the flex model at the knee's force) beside the rigid one. A layup two to three times softer than these prints (commercial fins flex to about 10 % of their depth in the water, [Krz24]) would not be covered by this estimate.

#### Flex as a lever: what a load-driven twist could buy (what-ifs, 2026-11-23)

Tobias's idea: printing lets the flex be tuned finely, so a fin might be low in drag going straight and change shape for the turn. `twist_ceiling.py` asks the lattice what a twist that grows with the load could add to the force at the knee. **None of this is a result**: it is the strip criterion applied to a twisted lattice, with no structure behind the twist and no simulation of the twisted blade.

| | gen-2 side | gen-3 side |
|---|---|---|
| rigid knee | 224 N | 250 N |
| tip twisting off 2° at that force (zero at the root, growing as the square of the span) | +3.2 % | +1.4 % |
| 4° | +6.7 % | +2.8 % |
| 8° | +14.9 % | +5.7 % |
| every strip at the share together (the ceiling) | +49 %, with 10–20° of twist | +24 %, with 6–14° |

- **The direction is the right one.** A raked blade bending under load turns its outer part to less incidence (`fingen.flex`, rake coupling), which unloads the strips that reach their limit first, and it costs nothing going straight because there is no load to twist it.
- **The gain per degree is small**, about 1.6 % of the knee's force per degree at the tip on the gen-2 side and 0.7 % on the gen-3 side, whose planform the search has already shaped so that its strips reach the share nearly together. The printed fins twist by 0.2° to 1° today.
- The ceiling needs a twist no flex will give. What stays open is the other half of the idea (a section that gains camber under load, which a solid section does not do by itself: a soft trailing edge gives way, which takes camber off) and what flex does past the knee, where there is no model.

