# The hydrofoil of [Zar14] on the knee record's simulation recipe: a second measured break (2026-11-24 to 26)

The knee record (`../../knee/one-degree/`) has one fin with a tunnel measurement beside its break, [BW04]. This foil is a second: an unswept NACA 0009 trapezoid (span 300 mm, chords 120 to 60 mm) with forces tabulated in half-degree steps through a sudden stall (`../measured/`, Type I stainless, Re 0.6·10⁶: highest lift 0.804 at 10.5°, then 0.776 at 11° with the drag doubled). The early simulation of it (`../cfd-polar.json`) was for its lift slope, on surface cells of 0.47 mm.

Run: `finGenerator-cfd/scripts/zarruk_knee.py`: the paper's tunnel (0.6 × 0.6 × 2.6 m, ceiling no-slip, foil rotated, one mesh per angle), 7.0 m/s, and everything else the knee record's level 6: background cell = root chord / 10, surface cells 0.19 mm, exact surface, the threshold scaled, wall functions, inflow turbulence 5 %, 800 iterations. Forecast written before any run: `../../knee/one-degree/nose7-prediction.txt`, items 42–44.

## As meshed (`results-L6x.json`, EPYC, in 2026-11-25)

2.84–2.89 million cells per angle, no flagged faces, snap residual 0.3–0.5 µm, mean wall y⁺ 26–34. Ceiling boundary layer at the probe 20–23 mm (measured 19 mm).

| | 4° | 8° | 9° | 9.5° | 10° | 10.5° | 11° | 12° | 13° |
|---|---|---|---|---|---|---|---|---|---|
| lift, measured | 0.346 | 0.632 | 0.702 | 0.741 | 0.774 | 0.804 | 0.776 | 0.774 | 0.768 |
| lift, simulation | 0.329 | 0.615 | 0.667 (swings 0.65–0.68) | 0.678 (0.63–0.70) | 0.685 (0.63–0.75) | | 0.693 (0.58–0.77) | 0.599 | 0.597 |
| simulation against the measurement | −5.0 % | −2.7 % | −5.0 % | −8.5 % | −11.5 % | | | | |
| simulation against the line through the origin fitted to its 4° and 8° rows | | −1.4 % | −4.9 % | −8.4 % | −12.0 % | | −19.1 % | | |
| measurement against its line, the same construction | | −1.9 % | −3.1 % | −3.1 % | −3.8 % | −4.8 % | −12.3 % | | |
| drag, measured | | 0.032 | 0.038 | 0.042 | 0.045 | 0.050 | 0.105 | 0.157 | 0.178 |
| drag, simulation | 0.0145 | 0.033 | 0.046 | 0.062 | 0.079 | | 0.107 | 0.127 | 0.144 |

- **Attached, the simulation has the foil**: at 8° the lift is 2.7 % and the drag 3 % from the measurement, and the row settles after 227 iterations. Its line (0.0779 per degree) is the lattice's (`../lattice.md`: 0.0779–0.0782). The measurement lies above both at 4° (a kink in its curve at 4.5–5.5°, which the paper puts down to laminar flow).
- **It leaves its line at 9°, a degree and a half before the tunnel.** The rows at 9° and 9.5° (in 2026-11-26, both at the iteration cap; windows of 150 iterations 0.670, 0.669, 0.667 and 0.689, 0.690, 0.677) are 4.9 % and 8.4 % below the line: the 5 % point is at 9.0°, the measurement's at 10.5°. The drag says the same: 21 % above the measured at 9°, 46 % at 9.5°, 74 % at 10°, where the measured foil is still attached (0.045). The simulation's highest lift is 0.69 against 0.804. On lines through each curve's 8° row alone (the only construction the level-7 rows below allow yet): 9.2° against 10.6°.
- **Against the forecast (item 42):** I expected the break at 10–12°, with 9.2–11.2° as the reading "a first strip goes at the share it does on the fins" and a lift of 0.78–0.90 there. It is at or below the early end of that, and well below it in lift. By the test set beforehand (5 % point within 1° of 10.5° and highest lift within 0.05 of 0.80) the recipe does not have this break.
- **So the recipe is not late on every measured blade.** On the tunnel fin it is right on or late (14° as meshed, 16.1° with the volume refined, against 13.6°); here, as meshed, it is early. What I told Tobias on 2026-11-24, that a simulation turbulent from the nose should hold on longer than a quiet tunnel's laminar bubble, does not describe this run.
- **Past the stall it is low**: 0.60 at 12–13° against 0.77. As on the tunnel fin, rows past a break are not the measurement.
- Item 44: the ceiling's layer came out at 20–23 mm, not the 8–10 mm I expected from the early run; that run had a tenth of this one's inflow turbulence.

## With the volume refined (`results-L6x-shells.json`, complete 2026-11-26)

The knee record's shells around the foil (cells of 0.625 mm to 10 mm off the wall, 1.25 mm to 25 mm, 2.5 mm to 50 mm): 4.38–4.42 million cells per angle, no flagged faces.

| | 4° | 10° | 11° | 12° | 13° | 14° |
|---|---|---|---|---|---|---|
| lift, as meshed | 0.329 | 0.685 | 0.693 | 0.599 | 0.597 | |
| lift, volume refined | 0.327 | 0.679 (swings 0.63–0.72) | 0.749 | 0.735 (0.60–0.85) | 0.717 (0.58–0.83) | 0.695 (0.57–0.81) |
| drag, volume refined | 0.0139 | 0.077 | 0.114 | 0.133 | 0.158 | 0.168 |
| lift, measured | 0.346 | 0.774 | 0.776 | 0.774 | 0.768 | |

- **The volume does not place this stall.** At 4° the two meshes agree within 0.5 %; at 10° the foil is stalled on both (drag 0.077 and 0.079 against the measured 0.045). Item 43, second alternative; I had leaned to the first ("later by 1–2°"). On the tunnel fin the same shells moved the 5 % point by two degrees: that was a swept blade's matter, not the method's.
- Rows from 11° on are past the stall on both meshes and at the iteration cap, swinging by up to ±0.13 on the refined volume. They are not read further (rows past a break are not the measurement, here as on the tunnel fin).

## Level 7 (`results-L7x.json`, EPYC, in 2026-11-26)

Surface cells of 0.094 mm: eight faces on the nose radius at the most loaded strip instead of four. 3.49–3.51 million cells per angle, no flagged faces, snap residual 0.73–0.75 µm, mean wall y⁺ 25–26 (level 6: 30–34). The step peaked at 6.7 GiB on the EPYC (8 processes; 6.4 GiB measured on the laptop beforehand). Forecast: `nose7-prediction.txt`, item 49.

| | 8° | 9° | 10° | 11° |
|---|---|---|---|---|
| lift, measured | 0.632 | 0.702 | 0.774 | 0.776 (stalled) |
| lift, level 6 | 0.615 | 0.667 | 0.685 | 0.693 |
| lift, level 7 | 0.626 (settled, 220 iterations) | 0.687 (at the cap, steady inside 0.685–0.689) | 0.718 (windows 0.725, 0.724, 0.719; swings 0.66–0.75) | 0.721 (0.64–0.80) |
| level 6 against the measurement | −2.7 % | −5.0 % | −11.5 % | |
| level 7 against the measurement | −1.0 % | −2.1 % | −7.3 % | |
| drag: measured / level 6 / level 7 | 0.032 / 0.033 / 0.032 | 0.038 / 0.046 / 0.041 | 0.045 / 0.079 / 0.064 | 0.105 / 0.107 / 0.099 |

- **Level 7 holds the foil about a quarter of a degree longer, and it is still stalled at 10°.** At 9° it is attached where level 6 had begun to let go (drag 7 % above the measured instead of 21 %); at 10° it has let go (drag 42 % above, lift 7 % short and swinging). On lines through each mesh's own 8° row the 5 % points are 9.2° (level 6) and 9.45° (level 7) against the tunnel's 10.6°. There is no 4° row on level 7 yet, so the fitted-line construction of the first table cannot be made; if that row rises with the level as the 8° row did (1.8 %), it gives 9.2° against level 6's 9.0° and the tunnel's 10.5°. The row is queued (item 54).
- **Against the forecast (item 49):** "9° attached, 10° stalled or swinging, a move of half a degree to a degree". The rows are as forecast; the move is at or under the lower edge.
- **So on this foil the recipe is early by 1.2–1.5° on both levels**, and one level closes about a fifth of the gap. Before the stall every level-7 row is nearer the measurement (8°: 1.0 % short instead of 2.7 %).
- This is the one measured blade run at two surface levels. It moves toward its tunnel with the level, as every round-nosed fin of the knee record moves later with the level (0.6–0.8° there, with one to three faces on the nose radius at level 6 against four here).

## Which strips let go (`strips-L6x.txt`, `strips-L7x.txt`; `../../smith2021/knee/blade_strips.py`)

Lift and lowest pressure of ten spanwise strips at the last iteration. Level 6: at 8° every strip is attached (lowest pressure −3.3 to −3.8); at 9° the strips at z/span 0.65–0.85 have stopped deepening (−3.6 to −3.7, carrying 0.62–0.67) while the inner ones go on to −4.3; at 9.5° the peak has gone from z/span 0.45 outward. The most loaded strip (z/span 0.45) lets go at 0.71. Level 7: every strip attached at 9° (−4.0 to −4.65, the most loaded at 0.73); at 10° the middle of the span has let go at 0.75–0.77. In the tunnel the foil stalls with that strip at 0.86–0.88 (`../lattice.md`), which is also the section's maximum measured in a turbulent stream ([JS37]: 0.86–0.88). The recipe's strips reach 0.72–0.83 of that on level 6 and 0.85–0.89 on level 7.

## What the two measured round-nosed blades say together (2026-11-26)

The short NACA 0012 blade of [Smi21], a fin's size, in the same tunnel: on level 6 the recipe has it within 2 % of the measured lift at 12° and stalled at 13°, eight degrees before the tunnel (`../../smith2021/knee/`). So the recipe (steady, turbulent from the nose, wall functions, no layers) is **early** on both measured blades with a round symmetric nose, by 1.2–1.5° here and by eight to nine degrees there, and on or late on the one measured flat-inside fin ([BW04]: 14–16° against 13.6°). What that does to the knee record's angles: `../../knee/one-degree/README.md`, "The recipe against the two measured round-nosed blades".

What kind of stall this foil has in its tunnel, and what that means for reading these rows: `../../knee/one-degree/README.md`, "The blades by Gault's ordinate".
