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

## Measured in a turbulent stream: NACA Report 586 (2026-11-25, 10:23Z)

The paragraph below asked for "sections measured tripped or in a turbulent stream at these Reynolds numbers". Jacobs & Sherman [JS37] is that: nine NACA 4-digit sections in the variable-density tunnel, whose stream has a turbulence factor of 2.64 (about the 2.6 % the table's held stream assumes), from a test Reynolds number of 4·10⁴ to 3·10⁶, on polished metal wings of aspect ratio 6. `js37-clmax.csv` is the section maximum lift of its Table I (the wing's maximum times 1.07) with the report's type of lift-curve peak; `vdt-against-table-v1.md` (`scripts/section_vdt_check.py`) sets it beside the table's `cl_limit`. The report gives each value at an "effective" Reynolds number, 2.64 times the test value; the comparison is read at the test Reynolds number, the model's own viscous scale.

| test Re | 1.65·10⁵ | 3.3·10⁵ | 6.5·10⁵ |
|---|---|---|---|
| NACA 0009: measured / table | 0.85 / 0.87 | 0.86 / 1.02 | 0.88 / 1.15 |
| NACA 0012 | 0.89 / 0.97 | 0.91 / 1.10 | 1.18 / 1.25 |
| NACA 0015 | 0.98 / 0.91 | 1.09 / 1.04 | 1.28 / 1.21 |
| NACA 0018 | 1.03 / 0.89 | 1.15 / 1.03 | 1.26 / 1.21 |
| NACA 4409 (nearest the gen-3 side's section: 4.5 % camber, t/c 0.083) | 1.23 / 1.40 | 1.26 / 1.49 | 1.29 / 1.61 |
| NACA 4412 | 1.31 / 1.29 | 1.36 / 1.45 | 1.46 / 1.62 |
| NACA 4415 | 1.35 / 1.20 | 1.41 / 1.39 | 1.48 / 1.58 |

- **The table is high on the sections of 9 % thickness and about right at 12 %.** NACA 4409: +14 %, +18 %, +25 % (and +12 % at 0.8·10⁵). NACA 0009: +2 %, +19 %, +30 %. The 12 % sections lie within −8 % to +21 %, the 15 % and 18 % ones at or below the measurement (the table's limit is the most lift carried *attached*, which on a section that stalls from the trailing edge is less than its maximum, so those rows are not like for like).
- **The measured maximum of a thin section does not grow with the Reynolds number in this range; the table's does.** NACA 4409: 1.21, 1.23, 1.26, 1.29 from 0.8 to 6.4·10⁵, all rounded peaks (type D); the table goes from 1.36 to 1.61. NACA 0009: 0.83 to 0.88, and still 0.94 at 1.3·10⁶. The report's reading: below a critical Reynolds number, which is higher the smaller the nose radius, the boundary layer separates laminar just behind the nose whatever the stream, and the maximum sits "of the order of 0.8" for every symmetric thickness. A layer turbulent from the nose, which is what the table has, is the far side of that critical range.
- **The table has the thickness trend of the limit the wrong way round at these Reynolds numbers.** Measured at 3.3·10⁵: 1.26, 1.36, 1.41 for 9 %, 12 %, 15 % at 4 % camber, and 0.86, 0.91, 1.09, 1.15 for the symmetric series. Table: 1.49, 1.45, 1.39 and 1.02, 1.10, 1.04, 1.03. In the table a thinner section costs nothing in hold; in the tunnel it costs about 0.1 of lift per 3 % of thickness. (Part of the table's falling side is the attached-limit reading named above; the thin side, where the two readings coincide, is the part that is high.) A search that is paid for thin sections in drag and not charged in hold will take them: this goes to plan item 3.4 and to the knee criterion's rework, and nothing is changed by it yet.
- **Camber is worth about 0.4 of section lift at every one of these Reynolds numbers** (NACA 4409 against 0009: 0.38–0.41; 4412 against 0012 below its critical range: 0.42–0.45), and the cambered sections lose their lift gently (type D throughout). The table has 0.46–0.53 at 9 % and 0.32–0.37 at 12 %. So the direction of the gen-3 side's section is the measured one and the table has camber's worth about right; what is overstated on that section is the thin section's limit as a whole.
- **The measured unswept blade stalls at its section's measured maximum.** The hydrofoil of [Zar14] (NACA 0009, Re 4–8·10⁵ along the span, a quiet tunnel) stalls with its most loaded strip at 0.76–0.84 of the table's limit, which is a lift of 0.86–0.88 (`../../zarruk/lattice.md`); the section's measured maximum is 0.85–0.88 here and 0.77–0.79 in [SDF89] at 1.5–3·10⁵. That blade's "share" is the table's excess on its section, as the paragraph below supposed. The NACA 0012 blades of [Smi21] say the same less sharply: strips at 1.06–1.21 at the stall (`../../smith2021/lattice.md`, Re 0.4–1.0·10⁶, quiet tunnel) against a measured section maximum of about 1.08 at 7·10⁵ in a quiet tunnel ([SK81], `../README.md`) and 0.91–1.18 from 3.3 to 6.6·10⁵ here. On unswept blades the classical rule ([Maki51]: a wing stalls where a strip reaches its section's maximum) holds within about a tenth when the section's maximum is the measured one.

What this does not give: a flat-inside section (none was tested; by the height of its suction side behind the nose it stands with the 18 % sections, `../../knee/one-degree/README.md`, "The blades by Gault's ordinate"), a rough or hot-coated surface, and a stream more turbulent than that tunnel's.

## What this does and does not say

The measurements are of smooth models in a quiet stream. A fin is sanded or hot-coated and works in broken water; the table is built for a boundary layer turbulent from the nose on a held stream of 2.6 % turbulence. Laminar bubbles lower the lift slope and round the top of these measured polars, and a turbulent stream removes them. So the two are bounds on one another, and which a fin is nearer to is not settled by this record: it needs sections measured tripped or in a turbulent stream at these Reynolds numbers.

What it does say, with the gate's NACA 0012 and NACA 4415 (+18 % and +19 % at Re 7e5): every measured section so far ends earlier and lower than the fully turbulent referee has it, by 5 to 27 %. The knee of a blade is read as a share (0.606, fitted on one tunnel fin) of the table's limit; part of what that share stands for is this, and the part differs from section to section and with the Reynolds number.

The other part is sweep. The measured record on swept wings ([HM64], reviewing [Maki51] and others; Reynolds numbers of millions, sweep 35–60°) is the method the strip criterion uses, with one more factor: the section's maximum lift is taken normal to the quarter-chord line and referred to the free stream, that is times the squared cosine of the sweep. First stall predicted so is on average 20 % low in wing lift for symmetric profiles and always on that side; outboard strips reach about the two-dimensional value, inboard strips exceed it (boundary-layer flow along the span), and separation from the nose shows on thicker sections than it does unswept, from the tip inward. The strip criterion has no sweep in it.
