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
| **gen-3 side, level 7, exact surface** (against level 6's line) | | | −0.8 % | −1.6 % | −3.1 % | −4.1 % | | **past 13°** |
| gen-2 side, level 6, faceted surface | −1.6 % | −4.0 % | −10.7 % | | −14.3 % | | | 9.2° |
| **gen-2 side, level 6, exact surface** | −1.7 % | −5.7 % | −11.1 % | −14.6 % | | | | **8.8°** |
| **gen-2 side, level 7, exact surface** (against level 6's line) | −2.4 % | −4.6 to −7.0 % | −9.8 to −10.9 % | | | | | **8.7°** |

- **The gen-3 side fin's break at 9° to 10° was the surface and the mesh. On the exact surface it lies between 12° and 13°.** Rows to 11° stop settled after 166–200 iterations. At 12° the row runs to the cap but holds 1.071–1.076 over its last 150 iterations (lift 1.073, 4.0 % below the line). At 13° and 14° it swings (0.91–1.04 and 0.88–1.04) about means of 0.98 and 0.95.
- **In the simulation its lift falls when it breaks: 345 N at 12°, 314 N at 13°, 306 N at 14°.** I had expected a 5 % point at 9.3–9.9° (item 13), and with the rows to 11° in hand wrote here that the fall of lift in one degree seen on level 5 "does not exist on this surface". It does, three degrees later. **It is not evidence of how the fin lets go**: on the tunnel fin the same recipe has a fall after the break that the tunnel does not have (next section).
- **The gen-2 side stays where it was, within 0.4°**: 5 % below at 8.8° (9.2° on the facets), rows from 9° at the cap, their window means within ±1.5 % (8.7–8.9° for the 5 % point). Its lift goes on rising through the break: 260, 272, 277, 286 N at 8° to 11°.
- **So the two fins are much further apart than the strip criterion has them.** Criterion: 6.6° and 7.4°, 234 N and 258 N (10 % apart). Simulation on the exact surface: 8.8° and 12.1°, about 270 N and 345 N (28 % apart), the gen-3 fin on 11 % less area.
- A cambered thin nose is where the faceted surface cost most: three degrees here, against 0.3° on the thick symmetric blade and 0.4° the other way on the flat-inside one. Every earlier polar of a cambered fin in this record (the 3 % camber planform, the candidate, the tip-width pair) is on that surface and is a lower bound on its break by an unknown amount.
- **Level 7 does not confirm level 6 on this fin** (`results-exact-L7-gen3-side.json`; 1 431 211 cells, mean wall y⁺ 31; items 17 and 20). Lift at 4°, 10°, 11°, 12°: 0.5875, 0.9771, 1.0343, 1.0832, which is 0.4–1.4 % above level 6. At 13°, where level 6 swings about 0.93–0.98, level 7 is attached: the row runs to the cap holding 1.1349–1.1377. The break level 6 put between 12° and 13° was the mesh's, as level 5's at 9° to 10° had been. The 5 % point on level 7 is past 13° and not bracketed; rows at 14° and 15° are queued (item 32). **Level 8 cannot check it as the recipe stands** (item 33): on this fin the mesher ends with illegal faces (29 over 65° of non-orthogonality, 26 collapsed) and the solver diverges within 18 iterations (laptop probe; 2.15 M cells, 4.1 GiB). Whether level 7 has this fin's break is open.
- **So "level 6 on the exact surface" is not a recipe for every fin.** It held on the symmetric t/c 0.080 blade (9.0° and 9.1° on levels 6 and 7) with 1.1–1.7 faces on the nose radius of the strips that let go. This fin has 1.8–2.7 and is not settled: the count of faces on the nose radius does not say when a nose is resolved. What differs is where the break is: at 6–7° of strip incidence on the symmetric blade, at 7–8° here, under a deeper suction peak (−4.2 against −3.3 on level 6).
- **Level 7 confirms level 6 on the gen-2 side** (`results-exact-L7-gen2-side.json`; 1 215 487 cells, mean wall y⁺ 39; item 19): 0.4758 and 0.7179 at 4° and 8° (level 6: 0.4764, 0.7226), window means 0.744–0.763 at 9° (0.744–0.755) and 0.771–0.780 at 10° (0.769–0.775). Its 5 % point is 8.7° on level 7 and 8.8° on level 6.
- **So refinement moves the round nose and not the cornered one.** A flat-inside section's nose is a right-angle corner, and the flow leaves at the corner whatever the mesh does. The cambered fin's round nose holds its suction peak longer the finer it is meshed. The tunnel fin is flat inside too; its level-7 run is next (item 26).

#### The tunnel fin on the exact surface (2026-11-24)

`results-exact-L6-bw04.json` (EPYC, 8 processes; 1 269 598 cells, mean wall y⁺ 34; level 6, 7 m/s) and `results-exact-L6-bw04-laptop.json` (the same plan to 14° on 12 processes; its long wall times are the laptop's sleep). The two agree to four digits on every settled row. Predictions: `nose7-prediction.txt`, items 12 and 18.

| | 11° | 12° | 13° | 14° | 15° | 16° |
|---|---|---|---|---|---|---|
| lift, level 6, exact surface | 0.8435 | 0.8977 | 0.9496 | 0.94–1.01 (swings) | 0.89 | 0.86 |
| against its line through 0° and 4° (0.2135, 0.4447) | −0.7 % | −1.0 % | −1.6 % | −1.5 to −8 %, about −5 % | −17 % | −25 % |
| level 5, faceted surface (`results-L5bw04.json`) | −1.7 % | −1.9 % | −8.2 % | −13.0 % | | −30 % |
| tunnel [BW04]: lift | | 0.775 | | 0.82 | | 0.89 |
| tunnel, against its stated line (0.05 per degree from −3.5°) | | on it | | −6.3 % | | −8.7 % |

(Tunnel points past 12° are read off the paper's figure, ±0.03 in lift, which is ±3.5 % here.)

- Rows at 11° to 13° stop settled after 176–186 iterations. **The row at 14° swings, and its filed value is the mean of its last 150 iterations only.** On the laptop the three windows of 150 iterations before the cap average 1.006, 0.944, 1.000 (range inside the last 0.973–1.021) and the row is filed as 0.9989; on the EPYC they average 0.996, 0.960, 0.944 (0.857–1.014) and it is filed as 0.9448. Rows at 15° and 16° swing by ±0.04 about 0.89–0.91 and 0.84–0.88.
- **With the surface right, the simulation begins to break where the tunnel does**: steady and 1.6 % below its line at 13°, swinging about 5 % below it at 14°, where the tunnel has the fin on its line at 12° and 6 % below at 14°. Level 5 on the facets had it 8 % below at 13° already. I first read the laptop's filed 0.9989 as "2.3 % below at 14°, later than the tunnel"; that was one window of a swing, and the second machine showed it.
- **Past the break the two part, and the simulation is the one that is wrong.** Its lift falls: 0.95 at 13°, 0.89 at 15°, 0.86 at 16°. The tunnel's goes on rising at about two thirds of its slope: 0.82, 0.89, 0.96, 1.02 at 14°, 16°, 18°, 20°. This is the boundary `docs/CFD-BENCH.md` already names (steady, fully turbulent RANS levels off near 0.87 where the measured fin climbs to 1.10 at 24°); the exact surface has not moved it. **So this recipe says where a fin begins to let go. It does not say what the fin carries afterwards, nor how abruptly it lets go.**
- The simulation's line is 16 % steeper than the tunnel's (0.0578 against 0.05 per degree; a third of that is the tunnel wall's boundary layer, `docs/CFD-BENCH.md`), so in lift the simulation carries 0.95 at 13° where the tunnel's line has 0.825.
- **What it means for the other fins.** This is the one break in the record with a measurement beside it, and on level 6 with the exact surface the recipe has its onset within about half a degree. The 5 % points of the two side fins above stand on the same recipe. Their rows past those points do not: the fall of the gen-3 fin's lift from 12° to 13° and the gen-2 side's lift rising on through its break are both in the regime where this recipe has the tunnel fin falling and the tunnel has it rising.

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
- **Running, to take section and planform apart** (laptop, `~/bench-results/levers10`; `nose7-prediction.txt`, items 22–24 and what the strip picture forecasts for them): the gen-2 planform with the gen-3 section, the gen-3 planform with the gen-2 section, and the gen-3 fin with its tip at 0.35 of the base. On the EPYC after the level checks: the tunnel fin on level 7 (item 26), then the thin symmetric blades on level 7 (items 27, 28). The gen-2 side to 14° (item 25) was dropped: rows past a break.

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

#### The swaps: section and planform taken apart (2026-11-24, running)

Level 6, exact surface, 8.5 m/s, on the laptop (`~/bench-results/levers10`). Predictions: `nose7-prediction.txt`, items 22–24 with the forecasts added under them.

| lift against the line through 0° and 4° | 7° | 8° | 9° | 10° | 11° | 12° | 5 % below at | lift there |
|---|---|---|---|---|---|---|---|---|
| gen-2 side (flat inside, t/c 0.092) | | −1.7 % | −5.7 % | −11.1 % | −14.6 % | | 8.8° | 0.75 |
| **gen-2 planform with the gen-3 section** (4.5 % camber, t/c 0.083; `results-swap-gen2-planform-gen3-section-L6.json`) | −0.5 % | −1.5 % | −6.3 % | −9.9 % | −12.0 % | −13.9 % | **8.7°** | 0.81 |
| gen-3 side (the same section on its own planform) | | −0.2 % | −0.6 % | −1.6 % | −3.0 % | −4.0 % | 12.1° | 1.07 |

- **On the gen-2 planform the cambered section breaks at the angle the flat-inside one does, 8 % higher in lift** (1 029 850 cells, mean wall y⁺ 45; rows to 8° settled, from 9° at the cap with window means within ±0.7 %). Neither of item 22's alternatives: not at the gen-2 side's lift (0.75), not above 0.85. The forecast from the gen-3 fin's share (0.81 of the section's limit: 9.3–9.8°) is missed by more than half a degree.
- **Strips** (`strip-loads.txt`, run `gen2-planform-gen3-section-L6x`): the ones at z/depth 0.76 and 0.85 are the first to be 5 % short, at 8.1° of blade angle, at 0.75 and 0.72 of their sections' limit and 5.6° and 5.0° of incidence. Between the flat-inside fins' share (0.70) and the gen-3 fin's (0.81).
- **A lower reading until level 7 is in.** This planform thins to 0.78 of its base thickness at the tip, so the cambered foil is t/c 0.067–0.072 on the strips that let go, with 0.8–1.4 level-6 faces on the nose radius (the gen-3 fin, which thickens to its tip, has 1.8–2.7 on a local t/c of 0.092). Queued behind the other two swaps.
- **What it already says:** the section alone does not carry the gen-3 fin to 12°. On this planform the same foil is worth 8 % in lift and nothing in angle. The rest is the gen-3 planform and its thickness schedule: the outer sections there are a third thicker (t/c 0.092–0.096 against 0.067–0.072), and its wide tip keeps the outer strips' incidence lower at the same blade angle (7.7° at 12° of blade angle, where the gen-2 planform has 8.9°).

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

