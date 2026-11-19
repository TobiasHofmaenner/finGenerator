# Section-recipe gate — NACA 0012 at Re 700 000 against [SK81] (2026-11-19)

Purpose: before any section table is trusted, the 2-D recipe has to reproduce a measured section. Reference: Sheldahl & Klimas Table 2, Re 7e5 block (`bench/ref-sk81-naca0012-re0.7M.dat`, natural transition). Driver: `finGenerator-cfd/scripts/section_polar.py` — simpleFoam, kOmegaSST fully turbulent, ±20 c graded domain, slab collapsed to a one-cell 2-D mesh; `wall: resolved` adds 14 prism layers from 12.9 µm (y⁺ ≈ 0.2–1 over the section). The old recipe is `sk81_naca0012.py` (±4 c, wall functions, CFD-BENCH item 3). Raw cases: EPYC `~/bench-results/section/gate-*`.

| α ° | measured CL | old recipe | wide domain, wall functions | wide domain, resolved wall | measured CD | resolved CD |
|---|---|---|---|---|---|---|
| 0 | 0.000 | -0.001 | -0.000 | 0.000 | 0.0067 | 0.0130 |
| 4 | 0.440 | 0.395 | 0.416 | 0.422 | 0.0083 | 0.0143 |
| 8 | 0.880 | 0.715 | 0.720 | 0.816 | 0.0128 | 0.0187 |
| 10 | 1.034 | 0.734 | 0.755 | 0.979 | 0.0159 | 0.0235 |
| 12 | 1.039 | 0.603 | 0.793 | 1.110 | 0.0195 | 0.0330 |
| 14 | 0.628 | 0.554 | 0.852 | 0.644 | 0.0236 | 0.1687 |
| 16 | 0.470 | 0.630 | 1.070 | 1.043 | 0.2100 | 0.2310 |

| | measured | old recipe | wall functions | resolved wall |
|---|---|---|---|---|
| lift slope 0–8°, per rad | 6.30 | 5.12 (-19 %) | 5.16 (-18 %) | 5.84 (-7 %) |
| maximum lift before the break | 1.075 at 11° | 0.73 at 10° | no clean maximum, ≈ 0.79 with drag already ×10 at 10° | 1.11 at 12° |
| drag at 0° | 0.0067 (laminar run) | 0.0083 | 0.0069 | 0.0130 (fully turbulent flat-plate estimate 0.0126) |

## Reading

- **Passed, with the resolved wall:** maximum lift within 3 %, the break within about 1°, lift slope 7 % low (a fully turbulent boundary layer against a naturally transitional measurement). Drag sits on the fully turbulent estimate, twice the measured laminar value, as it must.
- **The wall treatment was the defect, not the domain.** Widening the domain alone leaves the wall-function result where it was: slope −18 %, the suction peak lost near 8–10°.
- **Consequence for the 3-D bench:** every isolated-fin and set polar we have uses wall functions (mesh level 2). Their linear range is validated; their maximum-lift values are lower bounds and may be low by a similar margin. A level-4 (resolved-wall) polar of one fin near the knee is the direct test.
- Past the break (14°, 16°) the steady solver wanders; those rows are not data.
- Cost: a 60 000-cell mesh; every attached angle settles within 500 iterations, so with the driver's `stop_when_converged` a polar costs about a minute per attached angle on 8 cores.
