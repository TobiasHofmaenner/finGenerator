# A four-fin set against [Falk20]'s per-fin forces, mesh level 2 (2026-11-20)

Question (plan 2b.3a): before our own quads are simulated, does our set recipe reproduce what the four fins of a commercial quad do, fin by fin?

Run: `finGenerator-cfd/scripts/falk_quad.py` — the layout of [Falk20] (fronts 330 mm apart, rears 170 mm apart and 150 mm behind, toe 3.5° and cant 8.5° on all four), four equal flat-inside fins of 9 856 mm² (theirs: a scanned commercial fin of 9 860 mm²; ours is an outline of the same depth, base and area), 10 m/s, no board, steady RANS with wall functions on mesh level 2. Rows in `falk-quad.md`, data in `falk-quad.json`; theirs digitized in `../falk20_perfin_forces.csv` (±0.03–0.05).

| leeway ° | inside rail, front + rear lift: ours / theirs | outside rail, front + rear: ours / theirs | mean drag of the four: ours / theirs |
|---|---|---|---|
| 5 | 0.466 / 0.450 (+4 %) | 0.398 / 0.330 (+21 %) | 0.050 / 0.034 |
| 10 | 0.927 / 0.870 (+7 %) | 0.579 / 0.755 (−23 %) | 0.086 / 0.066 |
| 15 | 1.339 / 1.340 (0 %) | 0.667 / 0.960 (−31 %) | 0.138 / 0.126 |
| 20 (theirs unsteady) | 1.575 / 1.860 (−15 %) | 0.692 / 0.920 (−25 %) | 0.195 / 0.212 |
| 25 (theirs unsteady) | 1.663 / 1.580 (+5 %) | 0.652 / 0.670 (−3 %) | 0.248 / 0.253 |

## Reading

- **The working rail agrees as a pair**: within 7 % over their steady range. Its split does not: ours loads the front fin more (rear / front 0.61, 0.65, 0.78 at 5, 10, 15°; theirs 1.14, 0.89, 0.84). Their curves are bunched below 10° and read off a figure, so the split at 5° is inside the digitizing error; at 10° it is not.
- **The outside rail does not agree.** Our front outside fin stops at a lift of 0.27–0.30 from 10° on with high drag; theirs reaches 0.57–0.59. That fin works at minus (leeway + toe), flow onto its foiled face with the flat face as the suction side — the incidence at which mesh level 2 is known to let go early on these sections (`bench/section-tables/mesh-recipe`, `bench/cambered-candidate/mesh-level-5`). So this is as likely our mesh as their fins.
- **Drag going straight is twice theirs** (0.033 against 0.016 per fin). All four fins sit at −3.5° there, the same incidence, the same suspicion.
- Not a validation yet. The check is the same layout on mesh level 5 at 5, 10 and 15° (running, `~/bench-results/falkquad/level5` on the EPYC). Until it is in, nothing about rear fins should be taken from this run except that the working pair's total is right.
