# CFD bench: setup, mesh-convergence ladder, frozen recipe

Status 2026-07-24. The bench measures single blades in deep-submergence
steady RANS (simpleFoam, k-ω SST, wall functions) with the board idealized
as a symmetry plane at the fin base — mirroring the [BW04] tunnel-wall
mounting. Leeway sweeps rotate the inlet vector and force directions
(freestream lateral boundaries), so one mesh serves a whole polar.

## Mesh-convergence ladder (default symmetric fin, 7 m/s, 6° leeway)

Tier-0 reference: CL 0.347 (DATCOM, k = 1.7) … 0.408 (k = 2 symmetry limit).

| Level | Cells | CL | CD | Cp_min | y⁺ | Wall (10 ranks) |
|---|---|---|---|---|---|---|
| 0 smoke | 37 576 | 0.349 | 0.0497 | −0.94 | 43–692 | 71 s |
| 1 explore | 162 522 | 0.307 | 0.0363 | −1.23 | 14–338 | 168 s |
| 2 refined | 368 418 | 0.357 | 0.0337 | −1.64 | 4–288 | 151 s |
| 3 + layers | 439 491 | **0.357** | **0.0340** | −1.56 | 4–279 | 274 s |

Increments L2→L3: **ΔCL 0.1 %, ΔCD 0.8 %** — far inside the freeze gate
(ΔCL < 3 %, ΔCD < 5 %). CL sits inside the theory band; the suction peak
deepened from −0.5 (under-resolved) to ≈ −1.6, the expected healthy value
for a loaded section at 6°.

**Frozen recipe: `mesh_level=2` for polar production** (L3 confirms it at
twice the cost; use level 3 for drag-sensitive/validation studies).

## Bugs the ladder caught on the way (all fixed, all committed)

1. **Root leak** — fin base flush with the boundary left a snappy gap;
   flow short-circuited under the root (CL *fell* with refinement).
2. **Teleported fin** — the 2 mm seal translation became 2 m
   (build123d `scale()` preserves a prior `Pos` unscaled); snappy meshed an
   empty box, forceCoeffs reported zeros. `write_case` now asserts STL placement.
3. **Slip sidewalls** — lateral `slip` patches forbade the 6° crossflow,
   channeling the domain axial: *converged cleanly to a 6× wrong answer*.
   Freestream boundaries fixed it (L0 jumped 0.070 → 0.349 on the BC change
   alone). The most dangerous CFD failure mode is converged-but-wrong; this
   is why the bench validates against theory before any number ships.

## Known caveats / open gates

- y⁺ spans 4–290: partly below the wall-function band in refined regions.
  Acceptable for lift; revisit with resolved-wall layers for final drag.
- Fully-turbulent SST (no transition model) — see PHYSICS.md §4 caveats.
## [BW04] polar-shape validation — PASSED (v0.2.0 gate)

Replica fin (elliptical-ish, 25° sweep, flat inside, t/c 9 %, 100×120 mm),
0–18° sweep on the frozen level-2 recipe, one shared mesh (solve-only cost
80–480 s/angle at 10 ranks; high angles hit the iteration cap as the flow
turns marginally steady — the steady-RANS boundary made visible):

| Gate | Result | Criterion |
|---|---|---|
| Lift slope (fit 0–8°) | 3.47/rad vs DATCOM 3.63 → **−4.6 %** | < 20 % |
| Lift-curve break | CL_max 0.856 at **α ≈ 14°** | [BW04] measured 12–14° |
| CD at α = 0 | **0.0251** (analytic est. ≈ 0.024) | plausibility band |
| Oswald e from our own CD–CL² fit | **0.94** | physical band 0.80–0.95 |

CL₀ = 0.218 at zero leeway is the flat-side section's camber lift, positive
as predicted. Post-break decay is gentle (0.856 → 0.826 over 14–18°),
matching the measured thin-airfoil/tip-stall character — but post-break
steady-RANS numbers are qualitative only; URANS owns that regime.
Plot: `out/bw04-polar.png`.
