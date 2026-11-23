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
