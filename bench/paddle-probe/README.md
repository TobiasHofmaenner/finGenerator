# Paddle probe — is the oversized fin an artefact? (isolated CFD, 2026-11-19)

Question: the first cut of frontier scoring (`RiderSpec.scoring = "frontier"`) returned the same side fin for three different sets of aspirations — 15 433 mm², depth 131, base 120, tip width, leading-edge fullness and trailing-edge shape all on their slider limits, 3.5 % camber on t/c 0.070 (`fins/side-paddle-probe.json`). Its geometric aspect ratio is 1.11, effective 1.88: below 2.5, where `hydro.stall_alpha_deg` lets the break come 8° later per unit of aspect ratio and where no bench existed. The model credits it with a maximum side force of 516 N at 16.9° (8.5 m/s) against 347–362 N for normal-sized fins. Is that real, and what does it cost?

Isolated fin on the symmetry plane, 8.5 m/s, level-2 RANS with wall functions, driver `finGenerator-cfd/scripts/polar_angles.py`; plan and raw results beside this file. The diagnosis this run belongs to is in `docs/MODEL-EXTENSION.md`, "The oversized fin".

| own incidence ° | C_L | side force N | drag N | iterations |
|---|---|---|---|---|
| -3.5 | -0.004 | -2 | 10.6 | 800 (cap) |
| +0.0 | +0.163 | 93 | 9.3 | 800 (cap) |
| +4.0 | +0.353 | 202 | 17.1 | 131 |
| +8.0 | +0.547 | 312 | 33.2 | 131 |
| +12.0 | +0.715 | 409 | 65.3 | 800 (cap) |
| +16.0 | +0.846 | 483 | 111.1 | 800 (cap) |
| +20.0 | +0.839 | 479 | 155.4 | 800 (cap) |
| +24.0 | +0.849 | 485 | 206.7 | 800 (cap) |

## Drag at equal side force, against the fins that have polars

`scripts/polar_at_force.py bench/foil-family bench/cambered-candidate bench/paddle-probe --polar="gen-1 side as ridden (flat inside)":6611:bench/mount/side-asridden-gen1-verify-polar.json --merge=foil-family/flat-inside=bench/foil-family/flat-inside-verify-polar.json --forces=93,200,250,290,318` ("—" = the fin never makes that force; wall-function values, so every largest force is a lower bound):

| fin | area mm² | going straight (−3.5°) N | largest force N | at ° | drag at 93 N | drag at 200 N | drag at 250 N | drag at 290 N | drag at 318 N |
|---|---|---|---|---|---|---|---|---|---|
| gen-1 side as ridden (flat inside) | 6611 | — | 234 | 12 | 8.2 | 16.1 | — | — | — |
| foil-family / cambered-3pct | 9734 | 6.9 | 258 | 16 (last angle run) | 7.5 | 20.0 | 38.6 | — | — |
| foil-family / flat-inside | 9734 | 13.4 | 299 | 16 (last angle run) | 9.2 | 16.9 | 27.0 | 47.3 | — |
| cambered-candidate / cambered-candidate | 10054 | 9.1 | 295 | 16 (last angle run) | 7.9 | 15.8 | 25.7 | 44.5 | — |
| paddle-probe / paddle-probe | 15433 | 10.6 | 485 | 24 (last angle run) | 9.3 | 17.0 | 24.2 | 30.0 | 35.1 |

## The lattice model on the same blade

`scripts/lattice_vs_polar.py bench/paddle-probe`:

| own incidence ° | CL CFD | CL lattice | drag CFD N | drag lattice N | lattice / CFD | CFD iterations |
|---|---|---|---|---|---|---|
| -3.5 | -0.004 | +0.004 | 10.6 | 6.4 | 0.60 | 800 (cap) |
| +0.0 | +0.163 | +0.158 | 9.3 | 8.0 | 0.85 | 800 (cap) |
| +4.0 | +0.353 | +0.333 | 17.1 | 14.7 | 0.86 | 131 |
| +8.0 | +0.547 | +0.510 | 33.2 | 26.5 | 0.80 | 131 |
| +12.0 | +0.715 | +0.686 | 65.3 | 44.1 | 0.67 | 800 (cap) |
| +16.0 | +0.846 | +0.860 | 111.1 | 67.8 (strips not converged) | 0.61 | 800 (cap) |
| +20.0 | +0.839 | +1.017 | 155.4 | 95.0 (strips not converged) | 0.61 | 800 (cap) |
| +24.0 | +0.849 | +1.160 | 206.7 | 123.8 (strips not converged) | 0.60 | 800 (cap) |

## Reading

- **The late break is real.** The side force climbs to 483 N at 16° and stays on that level through 24° (479 N, 485 N); wall functions make this a lower bound. The rule's 16.9° and 516 N are within 7 % of that. For the normal-sized fins the same model is 16–29 % generous (332–362 N against 258–299 N), so in CFD terms the large fin's advantage in hold is bigger than the model says.
- **It makes the 318 N peak turn force at about 8°, for 35 N of drag.** None of the normal-sized fins makes 318 N in these polars; near their limit (290 N) they pay 44–47 N where the large fin pays 30 N. Up to about 250 N all of them cost the same.
- **Going straight it costs 10.6 N**, against 9.1 N for the cambered candidate and 6.9 N for 3 % camber on the shipped planform. The model reads 6.4 N: cambered sections at negative incidence, under-read again (`bench/cambered-candidate/`).
- **Lift from the lattice is within 7 % up to 16°**, a little low at 8–12°; it has no break, so it runs straight on through 24°. Its drag falls behind as the angle grows (0.80 of CFD at 8°, 0.67 at 12°, 0.61 at 16°): the strip model has no drag rise toward the break.
- **It does not let go.** From 16° to 24° the side force sits on a plateau (483 / 479 / 485 N) while the drag doubles. The gen-1 side, for comparison, loses 7 % of its force between 12° and 16°. For a carve that is reserve; for a snap, where the tail has to break free on demand, it is the opposite of what the manoeuvre needs — and the model has no term for it.

## Consequence

The oversized fin is not an artefact of the break rule: for a 318 N turn at 8.5 m/s the CFD prefers it on every quantity the model scores except drag going straight. What the model lacks is not a limit on area but the terms that oppose it in the water — the ability to release the tail on demand, and a drag rise toward the break. Nothing is capped; the break rule gets calibrated on this polar together with the five at higher aspect ratio.
