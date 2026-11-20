# Three blades for the other setups, isolated, mesh level 5 (2026-11-20)

Questions, from `docs/GEN3-PLAN.md` Phase 2b: what does a deep single do through its knee (2b.4a), what does a keel-type twin fin do (2b.2b), and does a thicker symmetric foil let a centre fin hold longer (2b.1)?

Isolated fins on a symmetry plane, mesh level 5 (wall functions), run on the compute node with finGenerator-cfd `scripts/polar_angles.py`. The two new outlines are stand-ins drawn for this run, not commercial templates.

| folder | blade | area | geometric aspect ratio | speed |
|---|---|---|---|---|
| `single-longboard/` | single, 240 mm deep, 160 mm base, raked 45°, symmetric t/c 0.08 | 27 869 mm² | 2.07 | 5 m/s |
| `centre-thick/` | the gen-1 centre as ridden, with t/c 0.09 instead of 0.046 | 7 673 mm² | 1.53 | 8.5 m/s |
| `twin-keel/` | keel, 95 mm deep, 180 mm base, flat inside t/c 0.10 | 14 790 mm² | 0.61 | 7 m/s |

The twin keel stops at 26° (27°, 28° and 30° were not run: the node was needed elsewhere). A fourth blade, a 180 mm single, was not run.

`lattice-vs-level5.md`: `uv run python scripts/lattice_vs_polar.py bench/phase2b/<folder> … --table=v1`. `strip-split.md`: the pressure and friction parts strip by strip. Rows that end before 800 iterations stopped on the solver's residuals with their forces flat; rows at 800 ran to the cap and are averages of a force that still swings by 1–10 %.

## Lift against each blade's own line (through its 0…6° rows)

| blade | deviation by angle | 5 % below at | aspect-ratio rule | strip criterion, same mirror |
|---|---|---|---|---|
| longboard single | 8°: +0.4 %, 9°: −0.6 %, 10°: −3.0 %, 11°: −4.2 %, 12°: −5.5 %, 14°: −13.4 % | 11.6° | 12.0° | 7.4° |
| gen-1 centre, t/c 0.09 | 8°: −0.4 %, 9°: −1.2 %, 10°: −10.0 %, 12°: −14.6 %, 14°: −25.3 % | 9.4° | 12.0° | 11.6° |
| gen-1 centre, t/c 0.046 (`../knee/one-degree/`) | 8°: −1.5 %, 9°: −4.1 %, 10°: −5.1 %, 12°: −7.6 % | 9.9° | 12.0° | 7.3° |
| twin keel | 8°: +6 %, 12°: +12 %, 16°: +16 %, 18°: +9 %, 20…26°: +9…+13 % | never | 23.7° | 26.7° |

## Reading

- **The longboard single keeps its lift and loses its drag.** Lift is within 2 % of the lattice from 4° to 12°. Drag is not: the lattice reads 4 % less than level 5 at 4°, 20 % less at 6°, 32 % at 8°, 38 % at 10° (5 m/s: 16.5 N against 11.2 N at 8°), on rows that are converged and on their lift line. The strip split shows where: from 6° the outermost strips lose their lift (at 8°, stations 221–238 mm carry 0.40, 0.11 and 0.01 where the lattice has 0.57, 0.47 and 0.28) while the strips just inboard carry 20–28 % MORE than the lattice (0.67 and 0.77 against 0.55 and 0.60). The loss moves inboard with angle — station 232 at 6°, 221 at 8°, 204 at 10°. That is a tip that stalls progressively with a vortex lying on the blade inboard of it, which a blade raked 45° is expected to do; the total lift hardly notices, the pressure drag does (14.2 N at 8° against 6.6 N of induced drag in the lattice). The strip model has no such thing: its tip strips sit at 4–5.5° of section incidence, inside their sections' range.
- **A thicker symmetric foil buys the centre nothing here.** With t/c 0.09 the gen-1 centre stays on its line one degree longer (9° against 8°) and then breaks sharply — 10 % below the line at 10°, 25 % at 14° — where the thin one lets go gradually and keeps climbing. Highest lift in the polar: 0.56 against 0.63. The section table says the opposite (criterion 11.6° against 7.3°): on the symmetric family it is still table v0, which credits thickness with a later break. The lattice also reads this blade's lift 5 % high from 4° on.
- **The twin keel has no knee of the side-fin kind.** Its lift rises ABOVE its own line from 8° (a low, broad blade makes vortex lift at its tip: at 16° the strips from 72 mm outwards carry 0.67–0.90 where the lattice has 0.55–0.63), dips once between 16° and 18° — where drag jumps by 40 % and the rows stop converging — and then climbs again to 1.02 at 26° without a maximum in sight. The lattice's lift stays within 7 % all the way, by two errors that cancel (no vortex lift, no loss); its drag is 19 % low at 16° and 30–36 % low beyond. At 0° and 4° it is the other way round: the lattice reads 26–32 % MORE drag, with the flat-inside sections sitting right at the lower end of their range (section incidence −1.7° at 4°, lower end −1.45°). Neither the aspect-ratio rule (23.7°) nor the strip criterion (26.7°) describes this blade: what ends its useful range is the drag step at 16–18°.

## What these runs cannot say

Mesh level 5 puts cells of base/320 on the nose: 2.2 cells per nose radius at the longboard fin's root and 0.6 at its station 204 mm, about 3 on the thick centre's root, 0.75 on the thin one's. The 2-D nose study of the same day (`../section-tables/nose/`) shows how much the nose decides: a shape error of 32 µm at the tip of a 0.65 mm nose moves both ends of a section's attached range by a degree, and the converged answer is two degrees wider at each end than the referee's before it. `docs/CFD-BENCH.md` already has level 5 separating early by its wall functions. So the angle at which the longboard fin's tip starts to stall, and the thick centre's sharp break, are not established: both are what an under-resolved nose would also produce. What is established is the direction — a raked tip goes first, and vortex lift on a keel is not small — and that the strip model contains neither.

Before any of this enters the model: one of these blades with the nose resolved along its whole leading edge (the 3-D counterpart of the 2-D nose band), then the per-configuration work in Phase 2b.
