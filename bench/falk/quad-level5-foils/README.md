# The four-fin set with two other foils, and through the lattice (2026-11-21)

Questions, left by `../quad-level5/`: with a foil as thin as theirs, does the working rail split as in [Falk20]? With a foil that has no corner at its nose, does the outside front fin stay on its lift line to 10°?

Runs: the same layout and outline on mesh level 5 at 5, 10 and 15° with a flat-inside foil of t/c 0.065 (`flat-tc065/`), with 3 % camber on t/c 0.065 (`camb3-tc065/`, the same zero-lift angle, a rounded nose), and the flat-inside foil again with 2° of toe on the rear pair instead of 3.5° (`flat-tc065-reartoe2/`, added the same day); `finGenerator-cfd/scripts/falk_quad.py --level=5 --angles=10,5,15 --tc=0.065 [--family=cambered --camber=0.03] [--rear-toe=2.0]`, EPYC `~/bench-results/falkquad/`. `lattice.md` (`uv run python scripts/falk_quad_lattice.py --md=…`) has all three foils fin by fin beside the lattice and the paper.

Lift coefficient per fin:

| leeway ° | fin | flat inside 0.09 | flat inside 0.065 | flat inside 0.065, rear toe 2° | 3 % camber 0.065 | linear lattice (flat 0.065) | [Falk20] |
|---|---|---|---|---|---|---|---|
| 5 | front inside | 0.289 | 0.224 | 0.225 | 0.264 | 0.219 | 0.210 |
| 5 | front outside | 0.243 | 0.318 | 0.318 | 0.276 | 0.303 | 0.260 |
| 5 | rear inside | 0.175 | 0.126 | 0.215 | 0.163 | 0.141 | 0.240 |
| 5 | rear outside | 0.155 | 0.204 | 0.120 | 0.185 | 0.198 | 0.070 |
| 10 | front inside | 0.565 | 0.500 | 0.502 | 0.539 | 0.492 | 0.460 |
| 10 | front outside | 0.278 | 0.385 | 0.392 | 0.368 | 0.550 | 0.565 |
| 10 | rear inside | 0.368 | 0.318 | 0.407 | 0.351 | 0.330 | 0.410 |
| 10 | rear outside | 0.307 | 0.354 | 0.273 | 0.330 | 0.336 | 0.190 |
| 15 | front inside | 0.862 | 0.797 | 0.799 | 0.834 | 0.769 | 0.730 |
| 15 | front outside | 0.300 | 0.391 | 0.398 | 0.377 | 0.784 | 0.585 |
| 15 | rear inside | 0.567 | 0.523 | 0.616 | 0.556 | 0.525 | 0.610 |
| 15 | rear outside | 0.373 | 0.438 | 0.387 | 0.423 | 0.446 | 0.375 |

## Reading

- **The thinner foil puts the front inside fin right.** With t/c 0.065 it is 7–9 % above theirs at all three angles (it was 18–38 % with 0.09), and the front pair at 5° lies on a line with a zero-lift angle of −2.6° (theirs −2.5° to −3.0°). Their fin's foil is about that thin.
- **The lattice and the set CFD agree fin by fin wherever the flow is attached.** Front inside, rear inside and rear outside, three foils, three angles: 27 values, the linear lattice within 0.02 of the CFD at 5° and 10° and within 0.04 at 15°. That includes what a rear fin loses behind the front fin of its rail (rear inside 0.141 / 0.330 / 0.525 against 0.126 / 0.318 / 0.523). Plan item 2b.3(c) is answered for the range in which the fins hold.
- **The rear split of the paper is a smaller rear toe, as far as the lattice can say.** The rear PAIR carries the same in all three sources (0.33 / 0.67 / 0.96 against their 0.31 / 0.60 / 0.99); its split does not: ours has the rear inside fin at 0.56–0.66 of the front one, theirs at 0.84–1.14. The paper gives one toe, 3.5°, and our run put it on all four fins. In the lattice, 1.5–2° on the rear pair gives their rear fins within the digitizing error at all three angles (rear inside 0.224 / 0.411 / 0.603 and rear outside 0.112 / 0.250 / 0.361 at 2°; theirs 0.240 / 0.410 / 0.610 and 0.070 / 0.190 / 0.375), rms 0.03 against 0.105 with 3.5°. Rear fins of commercial quads do carry less toe than the fronts.
- **The set CFD with 2° on the rear pair confirms it.** The rear inside fin comes out at 0.215 / 0.407 / 0.616 (theirs 0.240 / 0.410 / 0.610), its drag at 0.024 / 0.053 / 0.109 (theirs 0.035 / 0.055 / 0.110); it carries 0.77–0.95 of the front fin on its rail (theirs 0.84–1.14; with 3.5° it was 0.56–0.66). The rear fins' rms distance from the paper falls from 0.114 to 0.041. The front fins do not move (within 0.007).
- **The toe does in the CFD what it does in the lattice.** Taking 1.5° off the rear toe moved +0.089 / +0.089 / +0.093 onto the rear inside fin (lattice +0.083 / +0.081 / +0.078) and −0.084 / −0.081 / −0.051 off the rear outside one (lattice −0.086 at all three angles; at 15° that fin is partly separated). The lattice is within 0.013 of the new run on the rear inside fin and within 0.03 on the rear outside one.
- **What stays open is the rear outside fin at 5° and 10°:** 0.120 and 0.273 against their 0.070 and 0.190, with 1.4–2 × their drag (0.042 / 0.089 against 0.030 / 0.045). It is the fin behind the one neither simulation referees. Half a degree less toe would take another 0.03 off it and put as much onto the inside fin, which is already right; the lattice's best fit (1.5°, rms 0.026) is no better than 2° (0.031) within the digitizing error of the paper's curves.
- **The outside front fin lets go between 5° and 10° with every foil**, corner or no corner: 0.37–0.39 at 10° where the line has 0.55 and theirs has 0.565. Theirs lets go between 10° and 15°. The nose corner of the flat-inside family is not the cause.
- **For the cambered foil that is what the 2-D referee expects.** Through the lattice (the fin alone, table v0), the strips of that fin work at −5.3° of section incidence on average at 5° of leeway and at −8° at 10° (down to −10.7° along the blade). The converged 2-D referee ends the attached range of a 3 % / t/c 0.07 section between −6.0° and −6.5° (`../../section-tables/nose/`). At 5° the fin is just inside, at 10° two degrees past.
- **Neither simulation is a referee there.** Ours separates early on a wall-function mesh (`../../section-tables/controls/`): at 5° the outside front fin already has 1.6–2 × their drag (0.064–0.078 against 0.040) at the same lift. Theirs is wall-function RANS as well, on a coarser mesh (1.2 million cells for four fins, y+ 30–90), and keeps that fin's lift on its line at 10°, where a section like ours is 2° past its range. What an outside fin does between 5° and 15° of leeway is open in both.

## What it means for the model

- For a rail pair in the working range the lattice is good enough to design with: the split and the interference come out as the set CFD has them.
- A quad's rear toe is a first-order lever on which rear fin carries the load: 1.5° of toe moves 0.08–0.09 of lift coefficient from the outside rear fin to the inside one at every angle, in the lattice and in the set CFD alike. The lattice can be used to set it.
- The outside rail from 10° of leeway is separated flow on the unfoiled face. No tool here predicts its lift to better than a third; the drag of the two simulations agrees better (0.12–0.13 against 0.115 at 10°) than their lift.
