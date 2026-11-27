# The NACA 4409 wing of [JS37] on the knee record's simulation recipe (started 2026-11-27)

The knee record (`../knee/one-degree/`) has three measured blades beside the recipe: the tunnel fin of [BW04] (flat inside), and two with a round symmetric nose, the hydrofoil of [Zar14] and the short blade of [Smi21]. On the flat-inside fin the recipe is on or late; on both symmetric blades it is early. For the gen-3 side's kind of section (thin, cambered, round nose) the record had no measured blade, and so no direction for the recipe's error.

Jacobs & Sherman's NACA 4409 wing is one. The generator's cambered family is the NACA four-digit construction, so this section is a member of it (4 % camber at 40 % of chord, t/c 0.09; the gen-3 side has 4.5 % and 0.083). The wing was measured in a turbulent stream (the variable-density tunnel, turbulence factor 2.64) at a fin's Reynolds numbers.

## The measured wing (`js37-4409-wing.csv`)

Rectangular, 5 × 30 in, aspect ratio 6, square tips, polished duralumin; test V.D.T. 1162. The report's Fig. 9 gives its lift against the angle "for infinite aspect ratio" at eight test Reynolds numbers. The lift in the figure is the wing's own; the 7 % by which the report raises a wing's maximum to a section's is applied in its Table I only. The points were read by eye off a 500 dpi render (±0.01 in lift and ±0.1° where a symbol stands free, ±0.02 and ±0.15° in the cluster at 12°).

The figure's angle is the test angle less 3.18 times the lift (in degrees): 0.38 is added for the closed round tunnel's walls, 3.56 taken off for the downwash of a rectangular wing of aspect ratio 6. Every point read lands within 0.15° of a whole test angle on that rule. The wing's angle in free air is the test angle plus 0.38 times the lift:

| free-air angle | −4.0° | 0.1° | 4.2° | 8.3° | 12.4° | 16.5° | 18.4° | 20.4° | 24.4° |
|---|---|---|---|---|---|---|---|---|---|
| lift, test Re 646 000 | 0.000 | 0.299 | 0.605 | 0.894 | 1.134 | 1.210 | 1.170 | 1.144 | 1.036 |
| against the line through 0.1° and 4.2° (0.0743 per degree) | | | | −1.8 % | −6.6 % | −20 % | | | |
| lift, test Re 329 000 | 0.000 | 0.299 | 0.605 | 0.894 | 1.076 | 1.172 | 1.144 | 1.108 | 1.014 |
| against the same line | | | | −1.8 % | −11.3 % | −23 % | | | |

- **The wing bends from 8° and rounds over a maximum four degrees after it has left its line by 5 %** (the report's peak of type D: gradual, with little loss beyond it). Where it is 5 % below its line is not in the data to better than "between 8.3° and 12.4°": the test has no angle between.
- The maximum is 1.21 at 16.5° (646 000) and 1.17 (329 000); Table I's section values are these times 1.07 (1.29 and 1.26).
- To 8° the points of both Reynolds numbers lie on one another.

## The case

`naca4409-c80-s240.stl` (not in the repository, 3.8 MB; md5 `cef00ac3ecffe661aa33036d23deca68`): the half wing at chord 80 mm and semi-span 240 mm on the symmetry plane, written by `finGenerator-cfd/scripts/rect_wing_surface.py OUT.stl 80 240 0.09 0.04 0.4` with this checkout's `fingen` on the path. Sections from the formula at 400 points with the nose tangent pinned, ruled between stations 2 mm apart, faceted to 1 µm: 76 856 triangles, within 0.8 µm of the NACA form in the mean (the largest offsets, 11–76 µm, are the straight face that closes the trailing edge).

`polar_angles.py` takes the surface by its `"surface"` key (finGenerator-cfd `cc93c7a`). `wing-sizer.json` is a fin of base 80 mm and depth 240 mm that only sizes the case as a fin's is sized: background cell base/10, domain from 4 bases ahead to 8 behind, 3.5 to each side, 3 depths high, the stream held on the far boundary. The rows are filed on that outline's area, 16 568 mm²; **every lift below is put on the blade's own 19 200 mm²** (× 0.8629).

At 8.48 m/s the chord Reynolds number is 646 000 (ν 1.05·10⁻⁶). Levels 5, 6, 7 put 2.9, 5.7 and 11.4 faces on the nose radius (0.71 mm), about what the gen-3 side's most loaded strips have on levels 6, 7, 8.

Plans `plan-L5.json`, `plan-L6.json`, `plan-L7.json`; strips by `wing_strips.py`. Forecast written before any row: `../knee/one-degree/nose7-prediction.txt`, item 61.

## Rows

(running)
