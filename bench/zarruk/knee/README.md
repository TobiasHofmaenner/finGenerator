# The hydrofoil of [Zar14] on the knee record's simulation recipe: a second measured break (2026-11-24/25)

The knee record (`../../knee/one-degree/`) has one fin with a tunnel measurement beside its break, [BW04]. This foil is a second: an unswept NACA 0009 trapezoid (span 300 mm, chords 120 to 60 mm) with forces tabulated in half-degree steps through a sudden stall (`../measured/`, Type I stainless, Re 0.6·10⁶: highest lift 0.804 at 10.5°, then 0.776 at 11° with the drag doubled). The early simulation of it (`../cfd-polar.json`) was for its lift slope, on surface cells of 0.47 mm.

Run: `finGenerator-cfd/scripts/zarruk_knee.py`: the paper's tunnel (0.6 × 0.6 × 2.6 m, ceiling no-slip, foil rotated, one mesh per angle), 7.0 m/s, and everything else the knee record's level 6: background cell = root chord / 10, surface cells 0.19 mm, exact surface, the threshold scaled, wall functions, inflow turbulence 5 %, 800 iterations. Forecast written before any run: `../../knee/one-degree/nose7-prediction.txt`, items 42–44.

## As meshed (`results-L6x.json`, EPYC, in 2026-11-25)

2.84–2.89 million cells per angle, no flagged faces, snap residual 0.3–0.5 µm, mean wall y⁺ 26–34. Ceiling boundary layer at the probe 20–23 mm (measured 19 mm).

| | 4° | 8° | 10° | 10.5° | 11° | 12° | 13° |
|---|---|---|---|---|---|---|---|
| lift, measured | 0.346 | 0.632 | 0.774 | 0.804 | 0.776 | 0.774 | 0.768 |
| lift, simulation | 0.329 | 0.615 | 0.685 (swings 0.63–0.75) | | 0.693 (0.58–0.77) | 0.599 | 0.597 |
| simulation against the line through the origin fitted to its 4° and 8° rows | | −1.4 % | −12.0 % | | −19.1 % | | |
| measurement against its line, the same construction | | | −3.8 % | −4.8 % | −12.3 % | | |
| drag, measured | | 0.032 | 0.045 | 0.050 | 0.105 | 0.157 | 0.178 |
| drag, simulation | 0.0145 | 0.033 | 0.079 | | 0.107 | 0.127 | 0.144 |

- **Attached, the simulation has the foil**: at 8° the lift is 2.7 % and the drag 3 % from the measurement, and the row settles after 227 iterations. Its line (0.0779 per degree) is the lattice's (`../lattice.md`: 0.0779–0.0782). The measurement lies above both at 4° (a kink in its curve at 4.5–5.5°, which the paper puts down to laminar flow).
- **It stalls between 8° and 10°, one to two and a half degrees before the tunnel.** At 10° the measured foil is still attached (drag 0.045) and the simulated one has let go (lift 12 % below its line, swinging, drag 0.079). The simulation's highest lift is 0.69 against 0.804. There is no row at 9° or 9.5° yet to place it closer.
- **Against the forecast (item 42):** I expected the break at 10–12°, with 9.2–11.2° as the reading "a first strip goes at the share it does on the fins" and a lift of 0.78–0.90 there. It is at or below the early end of that, and well below it in lift. By the test set beforehand (5 % point within 1° of 10.5° and highest lift within 0.05 of 0.80) the recipe does not have this break.
- **So the recipe is not late on every measured blade.** On the tunnel fin it is right on or late (14° as meshed, 16.1° with the volume refined, against 13.6°); here, as meshed, it is early. What I told Tobias on 2026-11-24, that a simulation turbulent from the nose should hold on longer than a quiet tunnel's laminar bubble, does not describe this run.
- **Past the stall it is low**: 0.60 at 12–13° against 0.77. As on the tunnel fin, rows past a break are not the measurement.
- Item 44: the ceiling's layer came out at 20–23 mm, not the 8–10 mm I expected from the early run; that run had a tenth of this one's inflow turbulence.

## With the volume refined

Running (EPYC; 4.38–4.40 million cells, no flagged faces). In so far: 0.327 at 4°, within 0.5 % of the mesh above; **0.679 at 10°, swinging 0.63–0.72, drag 0.077: stalled as on the mesh as it was.** The volume does not place this stall (item 43, second alternative; I had leaned to the first).

## Next

Rows at 9° and 9.5° as meshed, to place the stall; and level 7 (eight faces on the nose radius instead of four), rows 8° to 11°, forecast item 49. Both queued on the EPYC.

The level-7 mesh at 10° (laptop, mesh only, 2026-11-25 10:02Z): 3 502 279 cells against 2 872 462, no faces flagged, snap residual 0.73 µm mean (level 6: 0.43 µm; the sound level-7 fin meshes 0.55–1.37 µm). Memory: surface export and mesher 5.1 GiB, 20 iterations with 8 processes 6.4 GiB (6.3 GiB of it process memory by the cgroup's own count). Released on the EPYC at 10:08Z under its 24 GiB cap.

What kind of stall this foil has in its tunnel, and what that means for reading these rows: `../../knee/one-degree/README.md`, "The blades by Gault's ordinate".
