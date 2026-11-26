# The short blade of [Smi21] on the knee record's simulation recipe: stalled between 12° and 13°, eight degrees before the tunnel (2026-11-25/26)

The short blade of `../` (NACA 0012, unswept trapezoid, root chord 120 mm, tip 80 mm, span 120 mm: a fin's size) in its tunnel at Re 1.0·10⁶ on the mean chord (10.5 m/s), with the thinnest ceiling layer of the paper's series (16 % of the span, 19.1 mm). After the tunnel fin of [BW04] and the hydrofoil of [Zar14] (`../../zarruk/knee/`) the third measured break put beside the recipe, and the second with a round symmetric nose.

Run: `finGenerator-cfd/scripts/zarruk_knee.py --blade smi21-short`: the tunnel's test section with a no-slip ceiling, one mesh per angle, and everything else the knee record's level 6 (background cell = root chord / 10, surface cells 0.19 mm, exact surface, wall functions, no layers, inflow turbulence 5 %, steady, 800 iterations, a row = the mean of its last 160). Forecast written before any row: `../../knee/one-degree/nose7-prediction.txt`, item 48.

## Rows (`results-short-L6x.json`; 4°, 12°, 16°, 18° on the laptop, 13° and 14° on the EPYC, in 2026-11-26 11:38Z)

2.52–2.57 million cells per angle, no flagged faces, snap residual 0.37–0.46 µm, mean wall y⁺ 51 / 47 / 45 / 46 / 40 / 37.

| | 4° | 12° | 13° | 14° | 16° | 18° |
|---|---|---|---|---|---|---|
| lift, measured | 0.184 | 0.604 | 0.662 | 0.715 | 0.810 | 0.906 |
| lift, simulation | 0.201 (settled, 377 iterations) | 0.594 (settled, 474) | 0.593 (at the cap; windows 0.617, 0.585, 0.595; range 0.536–0.632) | 0.580 (at the cap; 0.572, 0.614, 0.579; 0.489–0.681) | 0.510 (at the cap; windows of 150 iterations 0.571, 0.570, 0.511; range in the last 0.433–0.590) | 0.540 (at the cap; 0.498, 0.511, 0.537; 0.435–0.703) |
| simulation against the measurement | +9 % | −1.6 % | −10 % | −19 % | −37 % | −40 % |
| drag, measured | 0.0138 | 0.0637 | 0.0745 | 0.0853 | 0.108 | 0.134 |
| drag, simulation | 0.0143 | 0.0647 | 0.106 | 0.125 | 0.166 | 0.205 |

- **Attached, the simulation has the blade**: at 12° the lift is 1.6 % and the drag 1.6 % from the measurement. At 4° it is 9 % high; the lattice (`../lattice.md`) is 7 % high there in a uniform stream. The measured lift per degree rises from 0.046 at 4° to 0.050 at 12°; the simulation's is 0.050 and 0.0495.
- **The simulated blade lets go between 12° and 13°; the tunnel holds this blade to 21°** (5 % point 21.4°, sudden stall after 21.0° at a lift of 1.03). At 13° the lift is 10 % under the measurement and the drag 42 % over it, and the row no longer settles. The recipe is early by eight to nine degrees. Item 52 had 13° and 14° attached and the stall between 14° and 15° (one in two); "before 14°" was the one-in-six case, and it is before 13°.
- **Against the forecast (item 48):** neither alternative. One had the simulation at 17–21°, the other, which I expected, at 22–24.5° (a simulation turbulent from the nose outlasting a laminar bubble's burst). By the test set beforehand the recipe does not have this break.
- Rows at 20° to 24° were stopped unread (the 20° row was solving): past this recipe's break they say nothing.

## Where the lift goes: every strip from the ceiling to the tip (`strips-short-L6x.txt`, `blade_strips.py`)

Lift of ten spanwise strips from the surface pressure of the last iteration, on each strip's own chord, and the lowest pressure coefficient in the strip:

| z / span | 0.05 | 0.15 | 0.25 | 0.35 | 0.45 | 0.55 | 0.65 | 0.75 | 0.85 | 0.95 |
|---|---|---|---|---|---|---|---|---|---|---|
| 12°: lift | 0.565 | 0.601 | 0.620 | 0.627 | 0.626 | 0.620 | 0.608 | 0.589 | 0.553 | 0.583 |
| 12°: lowest pressure | −2.42 | −2.60 | −2.74 | −2.81 | −2.82 | −2.80 | −2.78 | −2.69 | −2.51 | −2.45 |
| 13°: lift | 0.613 | 0.635 | 0.624 | 0.597 | 0.585 | 0.636 | 0.651 | 0.634 | 0.586 | 0.611 |
| 13°: lowest pressure | −1.81 | −1.83 | −1.67 | −1.40 | −1.30 | −1.57 | −1.86 | −2.14 | −2.28 | −2.58 |
| 16°: lift | 0.536 | 0.516 | 0.496 | 0.507 | 0.523 | 0.521 | 0.540 | 0.539 | 0.518 | 0.515 |
| 16°: lowest pressure | −1.43 | −1.43 | −1.29 | −1.45 | −1.45 | −1.43 | −1.40 | −1.32 | −1.60 | −2.58 |

- **It starts at mid-span, where the load is highest, not at the ceiling.** At 13° the suction peak has gone most at z/span 0.35–0.45 (−1.3 to −1.4, from −2.8 at 12°), the two strips that carried the most at 12°; the strips at the ceiling have −1.8 and the tip still holds −2.3 to −2.6. A corner separation at the ceiling would start at the other end. The strips let go at a lift between 0.63 (carried at 12°) and 0.68 (asked at 13°); in the tunnel the blade stalls with that strip at 1.06 (`../lattice.md`).
- **At 16° every strip has lost its nose suction**: 0.50–0.54 from the ceiling to the tip, lowest pressure −1.3 to −1.6 (the tip strip stands apart at every angle: −1.3 at 4°, −2.6 here), against 0.57–0.63 and −2.4 to −2.8 four degrees earlier. A stall of the nose along the whole span, not a separation in the ceiling's corner and not a tip's.
- **The ceiling's layer is not the cause.** At the probe it is 28–41 mm by the 99 % rule, which the blade's own field disturbs (the profile has its bend at 20–25 mm; measured 19.1 mm). The paper's own series has a thicker layer delay the stall, by two degrees from 16 % to 47 % of the span.

## The solver passes through the attached state at the measured lift and does not keep it

The force history from a uniform start: at 16° the lift stands at 0.84 after 10–40 iterations and at 0.76–0.81 up to iteration 160 (measured: 0.81), then falls to 0.5 and swings. At 18°: 0.94–0.95, then 0.87–0.90 up to iteration 100 (measured: 0.91), then falls. So the attached flow at the measured lift is a state this mesh can carry for a hundred iterations, and the steady solution is not it.

## Reading

- **This is `docs/CFD-BENCH.md`'s gate 3 on a blade of a fin's size.** In 2-D the wall-function recipe held the lift slope of a NACA 0012 and lost a third of its maximum lift against [SK81] ("steady wall-function RANS can't hold the suction peak"); with the wall resolved it peaked 18 % above and 2° late (`../../section-gate/`). The bench record filed the first as a section matter that a low-aspect blade dilutes. It is not diluted here: the most loaded strip carries 0.63 attached at 12° and lets go before 0.68, under the 2-D gate's 0.73.
- **With [Zar14] that makes two measured round-nosed blades, and the recipe is early on both**: 1.2–1.5° on the NACA 0009 foil at Re 0.6·10⁶ (levels 6 and 7), eight to nine degrees on this NACA 0012 at Re 1.0·10⁶. The thicker blade, whose section carries more, is the one missed by more: what the recipe lacks grows with what the nose has to hold. On the flat-inside tunnel fin, which lets go from the trailing edge, it is on or late.
- **What the recipe is good for on such a blade:** the loads while it is attached (within 2 % at 12°), and comparisons that every mesh agrees on. Not the angle at which a round nose lets go.
- **What it is not evidence of:** that a fin's round nose lets go where this simulation has it. For symmetric noses the knee record's break angles are lower readings by this; for the cambered gen-3 section the direction is not known (`../../knee/one-degree/README.md`, "The recipe against the two measured round-nosed blades").
- The measured stall is a laminar bubble's burst on a polished blade in a quiet tunnel (`../README.md`); a sanded, coated fin in broken water need not hold as long. That caveat is unchanged, and it is about the tunnel, not about this simulation: the most loaded strip lets go at 0.63–0.68, and the section alone carries 1.07 in a wind tunnel at Re 7·10⁵ ([SK81], natural transition).

## Level 7 at 16°: stalled as on level 6 (`results-short-L7x.json`, in 2026-11-26 11:29Z)

Surface cells of 0.094 mm, 2 792 781 cells, no flagged faces, snap residual 0.77 µm, mean wall y⁺ 35 (level 6: 40). Forecast item 53: stalled, three in four.

| 16° | lift | drag |
|---|---|---|
| measured | 0.810 | 0.108 |
| level 6 | 0.510 (windows 0.571, 0.570, 0.511) | 0.166 |
| level 7 | 0.499 (windows 0.491, 0.460, 0.500; range in the last 0.40–0.62) | 0.166 |

The history repeats level 6's: 0.83–0.85 at iterations 20–40, 0.73–0.77 up to iteration 160, 0.41–0.52 from 280 on. The strips (`strips-short-L7x.txt`, last iteration) carry 0.41–0.49 from the ceiling to the tip with lowest pressures of −1.1 to −1.5. One level, which moved the fins' round-nosed breaks by 0.6–0.8° and the [Zar14] foil's by a quarter of a degree, does nothing for a miss of five degrees.

## Running (2026-11-26)

- The row at 15° on level 6 (EPYC; stalled after 355 iterations as the two before it).
