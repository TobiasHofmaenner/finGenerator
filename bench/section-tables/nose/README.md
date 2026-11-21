# The referee's nose: it was the outline (2026-11-20)

Question, left by `../controls/`: one surface level finer, the referee's lower ends moved by a degree in either direction. Which mesh is converged at the nose?

Answer: none of them was, because the nose they meshed was not the section's. With the outline exact and cells of one size on the nose, three mesh levels agree within 0.3 % in lift and 0.5 % in drag, they break at the same angles, and the attached range of the test section is two degrees wider at each end than table v1 has it.

Runs: `finGenerator-cfd/scripts/section_polar.py`, resolved wall, domain ±20 chords, on 3 % camber / t/c 0.07 / chord 0.12 m / Re 5.7e5 (nose radius 0.65 mm), and on 4.5 % / t/c 0.092 as a second section. `plans.json` has every run's plan, `results.json` its rows, `series.md` every run angle by angle. Run on the laptop (`~/bench-results/meshstudy`).

## 1. The mesher's curvature rule is not a refinement series

The referee refined the surface to its finest level only where the surface turns by more than 30° within a cell. On a thin nose that is the outermost tip (x/c below 0.0005), and less of it at every level. Asking for finer cells that way moved the answer without settling it (drag coefficient × 10⁴, * = separated):

| tip cells by curvature | −4.5° | −5.0° | −5.5° | +8.0° | +8.5° |
|---|---|---|---|---|---|
| 0.19 mm (the referee of table v1) | 322* | 435* | 559* | 340 | 726* |
| 0.094 mm | 152 | 178 | 553* | 270 | 413* |
| 0.047 mm | 147 | 159 | 453* | 254 | 274 |
| 0.023 mm | 145 | 155 | 173 | 252 | 270 |

Finer cells in the band around the section, a layer stack grown to the face cell, a lower curvature threshold: none of them changes the referee's answer (`near5`, `layers`, `ang10` in `series.md`).

The series also loses the wall as it refines the tip (found 2026-11-21, reading the mesher's own summary): of the layer stack's thickness the mesher kept 99 % on the referee's mesh and 92, 88 and 72 % on the three finer ones. It takes layers off where they do not fit and still ends without an error. Every mesh with a uniform nose band (section 3 and 4) kept 97.8 % or more, the old outline's included, and every section of the rerun 99.6 % or more. The driver now records the share and refuses a resolved-wall mesh below 90 %.

## 2. The outline

The mesher's surface came from `fingen.foil.section_points` with 100 points (50 per side, cosine spaced) and two splines, one per side, meeting at the leading edge. Against the analytic section at chord 120 mm:

| outline | largest distance from the section within the first 1 % of chord | corner at the leading edge |
|---|---|---|
| 100 points, two splines (the referee) | 32 µm | 33° |
| 100 points, one spline through the leading edge | 39 µm | none |
| 400 points, two splines | 1.8 µm | 9° |
| 400 points, one spline through the leading edge | 1.8 µm | none |

The surface was also handed to the mesher in facets of 5.7° (STL angular tolerance 0.1 rad), 0.065 mm long at the nose. Cells of 0.19 mm do not see any of this. Cells of 0.02–0.09 mm mesh the corner, each level a little differently.

## 3. Exact outline, uniform nose band

`nose_level` puts cells of one size on the whole surface ahead of 2 % of chord, one level coarser to 4 %, and so on down to the face level. With the outline exact (400 points, one spline, facets of 1.1°):

| nose cells | cells per nose radius | −4.5° | −5.5° | −6.0° | −6.5° | +8.0° | +9.0° | +10.0° | +10.5° |
|---|---|---|---|---|---|---|---|---|---|
| 0.094 mm | 7 | −0.1538, 142 | −0.2616, 158 | −0.3148, 172 | 501* | 1.1694, 244 | 1.2544, 278 | 1.3174, 335 | 1308* |
| 0.047 mm | 14 | −0.1538, 142 | −0.2613, 158 | −0.3149, 171 | 497* | 1.1697, 243 | 1.2557, 277 | 1.3187, 336 | 1086* |
| 0.023 mm | 28 | −0.1537, 142 | −0.2614, 158 | −0.3147, 171 | 504* | 1.1690, 243 | 1.2538, 278 | 1.3235, 329 | 888* |
| 0.023 mm, band twice as long | 28 | −0.1536, 142 | −0.2614, 158 | −0.3144, 171 | 526* | 1.1683, 244 | 1.2519, 278 | 1.3161, 332 | 1210* |
| 0.023 mm, **old outline** | 28 | −0.1531, 144 | 484* | 481* | 529* | 1.1617, 252 | 1.2320, 312 | 1094* | 1116* |

(lift coefficient, drag coefficient × 10⁴; * = separated, drag only)

- **On the exact outline the mesh is converged from 7 cells per nose radius**: lift within 0.3 % and drag within 0.5 % up to half a degree before each end (0.6 % and 2 % at +10.0°, the last attached row), and the same break — attached at −6.0° and +10.0°, separated at −6.5° and +10.5°.
- **On the old outline the same mesh separates a degree early at each end** (at −5.5° and +9.5°) and has 2 % more drag at −4.5°, 4 % at +8°, 12 % at +9°. A corner of 33° and 32 µm at the tip of a 0.65 mm nose is what that costs.
- **The referee of table v1 had both defects.** It is separated at −4.5° and at +8.5° on this section; the table's ends for it are −4.3° and +8.1°. The attached range is about two degrees wider at each end.

## 4. Controls on the exact outline

Each against the run it varies; lift coefficient and drag coefficient × 10⁴ in `series.md`, section 3 and 4.

| control | attached rows: lift | drag | break |
|---|---|---|---|
| the same mesh on four processes instead of six | within 0.0004 (0.002 at +9.5°) | within 0.4 % | the same |
| faces one level finer (0.19 mm instead of 0.375 mm) | 0.003 lower at −4.5° and −6.0°, 0.010–0.011 lower at +8° and +10° | within 0.8 % | the same |
| trailing-edge corners two levels finer (0.047 mm; the 1.2 mm base has 25 cells across instead of 3) | 0.004–0.007 lower at every angle | within 1.2 % | the same |
| second section (4.5 % camber, t/c 0.092, nose radius 1.1 mm): nose cells 0.047 mm against 0.023 mm | within 0.002 up to +12° (0.008 at +10°), 0.018 at +13° | within 0.3 % (1.8 % at +13°) | upper end beyond +13° on both; lower end: 0.047 mm attached at −8.0° and separated at −9.0°, 0.023 mm attached at −7.5° and separated at −8.0° |

- **No control moves an end of the test section.** Six meshes on the exact outline (three nose levels, a longer band, finer faces, a finer trailing edge) bracket both ends between the same two rows.
- **Lift is known to about 0.01** (0.1° of zero-lift angle): finer faces and a finer trailing edge both lower it by that much or less. **Drag to about 1 %.**
- **An end is known to half a degree, not better.** On the second section the two nose levels agree to four digits up to −7.0° and then differ in the row at which they let go. The last attached row before an end is also the slowest to settle (2400 iterations at −7.5°, where 900 do elsewhere). Steady RANS started from rest at each angle decides the last half degree by details.
- **Rows next to an end carry up to 1 % in lift from the stopping rule.** The driver ends a row when lift and drag change by less than 0.3 % and 0.5 % between two windows of 100 iterations. Close to an end a row creeps for a long time, and one stopped at 900 iterations sits below the same row run to 1500–2100: on the second section 1.4785 against 1.486 at +10° (the same mesh run twice, the second time in the section batch), 1.6249 against 1.6430 at +13°. Away from the ends two runs of one mesh agree to four digits.
- One option of the driver did nothing until 2026-11-20: `edge_level` set only the mesher's feature-edge entry, which marks no cell in a one-cell slab. A run with it (`u8e9`) made the identical mesh and serves as the repeat in the first row. It is now the upper level of the surface refinement.

Not run yet: the exact outline on the referee's own mesh (no band) and with nose cells of 0.19 mm (`e6`, `u6`): how coarse the nose may be once the outline is right. They follow the section batch.

## 5. What it changes

**Table v1.** Its ends are the old referee's. On the test section:

| | lower end | upper end |
|---|---|---|
| referee of table v1 (old outline, tip refined by curvature) | −4.3° | +8.1° |
| table v0 (NeuralFoil) | −5.2° | +10.0° |
| exact outline, uniform nose band | between −6.0° and −6.5° | between +10.0° and +10.5° |

- v1 moved v0's ends inward by one and two degrees. The upper end was right in v0; the lower end was a degree short there, not a degree long.
- `../controls/` (b) is superseded: its finer mesh had the 4.5 % / t/c 0.092 section separated at −6.0°. On the exact outline it holds to −7.5°. "Thin sections have more room than v1 says, thick ones less" was the outline on a finer mesh; both have more.
- Everything read off v1's ends is to be read again on the rebuilt table: a side fin's drag going straight at −2.5…−4.5° of section incidence, where a thin cambered section stops being cheap (`docs/MODEL-EXTENSION.md`), the share of the section's lift at which a strip is taken to leave its line (fitted on v1's upper ends), and the hold numbers that follow from it.

**3-D CFD.** Mesh level 5 has cells of 0.3 mm and more on a fin's nose: it does not see the corner, and its early separation is its wall functions (`../controls/`, a). Nothing changes there. A 3-D referee needs what the 2-D one needed: the exact nose and a band of small cells along the whole leading edge. `fingen.loft` draws every section with the same two splines and 100 points, so the generated solid has the corner too (measured on the builder's own sketch of the test section: 33.4° and 32 µm at the default 100 points, 18.6° and 7 µm at 200, 8.8° and 2 µm at 400, the most it accepts); that has to change first.

**A real fin** (an inference: nothing here measured a fin). The break is decided by the shape of the nose at the scale of tens of micrometres: a corner with 32 µm of shape error on a 0.65 mm nose costs a degree at each end. A printed leading edge with a seam, a flat from sanding or a ridge of that size is a nose of the same kind. So the leading edge wants to be finished smooth and round with no seam on it, and the ends of a real fin's range are known to about a degree whatever a table says.

## 6. The recipe

`nose_level 9` (cells of 0.023 mm on the first 2 % of chord, one level coarser to 4 %, and so on: 14 cells per nose radius on a t/c 0.05 section, 28 on 0.07), `outline_points 400`, `smooth_nose true`, `stl_tolerance 1e-06`, `stl_angle 0.02`, faces 0.375 mm, trailing-edge corners at the face level, 13 layers from 9.3 µm, domain ±20 chords. About 68 000 cells; an attached row takes five minutes on four cores, a separated one twenty.

Each end of the attached range is found by marching: half-degree steps outward from the old end until two rows in a row (three at the lower end) are past it — not settled, or more than four times the section's lowest drag — then one row halfway between the last row inside and the first beyond. Eighteen sections are being rerun this way (the table's twelve cambered ones, the 4.5 % / t/c 0.092 section at Re 9.7e5, five symmetric sections); `scripts/build_section_table_v1.py` is rebuilt on them.
