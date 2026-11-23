# Measured sections of the table's own families (2026-11-23)

The symmetric and the cambered foil family are NACA 4-digit constructions (`fingen.foil`). Three models in Selig, Donovan & Fraser's low-speed tests [SDF89] are therefore members of them, measured at Reynolds numbers 6e4 to 3e5, where the table has its two lower Reynolds numbers (1.4e5 and 2.8e5):

- `sdf89-naca0009.csv`: NACA 0009, the table's symmetric section of t/c 0.09 (the table's has a trailing edge of 1 % of chord).
- `sdf89-naca2.5411.csv`: NACA 2.5411, 2.5 % camber at 40 % of chord, t/c 0.11.
- `sdf89-naca6409.csv`: NACA 6409, 6 % camber at 40 %, t/c 0.09. The table ends at 5 % camber and is read there.

The rows are the book's tabulated data (chapter 13, pages 372–373), copied by eye from the page images and checked against the text layer. Princeton 3 × 4 ft low-turbulence tunnel, smooth models, no trip; lift from a force balance, drag from a wake survey, which ends where the wake gets too wide, so the rows stop at or just before the maximum. The lift plots (figures 12.61 and 12.63, to Re 1e5 only) show it: NACA 0009 0.78–0.80 at about 10°, falling to 0.65–0.70; NACA 2.5411 1.03 at 12°, then an abrupt stall to 0.8.

What the book says about the models: the NACA 0009 is "not perfectly symmetric" and has a dead band in lift about 0° (long, thin bubbles on both faces); the NACA 6409 was the one model built with open bays, its covering sagging up to 0.2 % of chord.

`against-table-v1.md` is written by `scripts/section_measured_check.py`.

## Reading

| | measured | table v1 |
|---|---|---|
| NACA 0009, lift at 4° | 0.42 at every Reynolds number | within 3 % |
| lift at 8°, Re 3.0e5 | 0.737 | 0.837 (measured 12 % below) |
| lift at 9°, Re 3.0e5 | 0.782 | 0.926 (16 % below) |
| 5 % below its own line | 6.7–7.8°, at a lift of 0.63–0.71 | 8.0–9.4°, at 0.79–0.96 |
| highest lift, Re 1.5e5 / 2.0e5 / 3.0e5 | 0.77 / 0.79 / 0.79 (last rows, 9.3°) | 0.84 / 0.91 / 1.00 |
| NACA 2.5411, lift at 2–9° | 11–14 % below the table at every angle | |
| lift slope per degree | 0.090–0.095 | 0.099–0.104 |
| highest lift, Re 1.0e5 / 2.0e5 | 1.03 at 12° (lift plot) / 1.04 at 11.3° (last row) | 1.15 / 1.24 |
| NACA 6409 (6 % camber), lift at 4–9° | within 5 % of the table **read at 5 % camber** | |
| highest lift, Re 1.0e5–2.0e5 | 1.34–1.38 | 1.41–1.49 at 5 % camber |
| drag at 4° | | 1.2–1.6 times the measured |

- **The upper end of the table's sections is late and high against these measurements, as it is against the NACA 0012 of the gate** (`../README.md`: +18 %, 2° late at Re 7e5). On the NACA 0009 the measured maximum does not grow with the Reynolds number between 1e5 and 3e5; the table's limit grows by a quarter, so the table is 5–9 % high at 1.5e5 and 27 % high at 3.0e5.
- **The measured lift curve bends long before its maximum.** The NACA 0009 is 5 % below its own line at a lift of 0.63–0.71, with the drag rising from 6°; the table's section holds its line to 0.8–0.96. A blade made of the measured section would leave its lift line where its most loaded strip carries 0.63–0.71, which is 0.67–0.85 of the table's limit at that Reynolds number.
- **The cambered sections carry less lift than the table at every angle**: lower slope, and at 6 % camber the measured section lifts what the table gives at 5 %.
- **Drag** is the difference between a smooth model with laminar runs and a section turbulent from the nose, as on the NACA 0012 (`../README.md`, section 3).

## What this does and does not say

The measurements are of smooth models in a quiet stream. A fin is sanded or hot-coated and works in broken water; the table is built for a boundary layer turbulent from the nose on a held stream of 2.6 % turbulence. Laminar bubbles lower the lift slope and round the top of these measured polars, and a turbulent stream removes them. So the two are bounds on one another, and which a fin is nearer to is not settled by this record: it needs sections measured tripped or in a turbulent stream at these Reynolds numbers.

What it does say, with the gate's NACA 0012 and NACA 4415 (+18 % and +19 % at Re 7e5): every measured section so far ends earlier and lower than the fully turbulent referee has it, by 5 to 27 %. The knee of a blade is read as a share (0.606, fitted on one tunnel fin) of the table's limit; part of what that share stands for is this, and the part differs from section to section and with the Reynolds number.

The other part is sweep. The measured record on swept wings ([HM64], reviewing [Maki51] and others; Reynolds numbers of millions, sweep 35–60°) is the method the strip criterion uses, with one more factor: the section's maximum lift is taken normal to the quarter-chord line and referred to the free stream, that is times the squared cosine of the sweep. First stall predicted so is on average 20 % low in wing lift for symmetric profiles and always on that side; outboard strips reach about the two-dimensional value, inboard strips exceed it (boundary-layer flow along the span), and separation from the nose shows on thicker sections than it does unswept, from the tip inward. The strip criterion has no sweep in it.
