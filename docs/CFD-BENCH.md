# CFD bench: setup, mesh-convergence ladder, frozen recipe

Status 2026-07-25. The bench measures single blades in deep-submergence
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
4. **Probe on the lattice** — snappy's `locationInMesh` sat at exact
   multiples of the background cell; the tunnel domain's round 2.1 m length
   made the coincidence exact and snappy refused the point (fail-loud,
   thankfully). The probe is now offset 0.37 cells off the lattice.

## Validation roadmap

Completed tiers: mesh ladder (frozen L2) · DATCOM theory band · [BW04]
shape gates · [BW04] point-by-point gates · tunnel-wall systematic
(≈ ⅓ of slope gap, measured) · transition tier (null on lift, −8 % drag)
· Oswald-e internal consistency. Open items, in execution order —
thoroughness is cheap relative to what a wrong bench would cost:

1. **ERCOFTAC T3A flat plate** *(in progress)* — the transition-model
   implementation itself, against the canonical transition benchmark.
2. **NASA TMR 2D flat plate** (turbmodels.larc.nasa.gov) — Cf(x)/u⁺
   against CFL3D/FUN3D reference solutions: the k-ω SST implementation +
   wall-function behavior isolated from meshing. The gold standard for
   "is my solver setup sane"; their 2D bump / NACA 0012 / RAE 2822
   families follow if the plate passes.
3. **Extruded NACA 0012 vs [SK81]** — section machinery against the
   tabulated polars the tier-0 model cites, incl. post-stall.
4. **Zarruk 2014 towing-tank replication** — modern force + deflection
   data with published uncertainties; the drag-fidelity anchor BW04's
   digitization cannot provide, and an FSI hook via tip deflections.
5. **URANS post-knee study** (16–24°) — does unsteady vortex lift
   reproduce the measured CL climb to 1.10 that steady RANS plateaus
   below? Gates optimizer use of near-stall axes.
6. **[Els22] groove replication** — grooved vs plain replica pair;
   their +11 % L/D at 30° (partially URANS-dependent).
7. **Physical structure bench** (user-side) — force–stroke stiffness
   (plain vs grooved, replicating [For24] panel C), load-to-failure vs
   FORCE_SF allowables, seawater-soak stiffness recheck.
8. **Multi-fin interference vs [Falk19/Falk20]** — anchors
   CONFIG_DOMINANT_SHARE; blocked on fin-set assembly geometry.

Parked (out of scope until the single-blade bench is exhausted):
free-surface ventilation/cavitation (multiphase); re-running the
transition tier with measured tunnel Tu if the [BW04] authors reply.

## Known caveats / open gates

- y⁺ spans 4–290: partly below the wall-function band in refined regions.
  Acceptable for lift; revisit with resolved-wall layers for final drag.
- Fully-turbulent SST (no transition model) — see PHYSICS.md §4 caveats.
## [BW04] polar-shape validation — PASSED (v0.2.0 gate, first-pass replica)

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

## [BW04] point-by-point validation (definitive replica)

The replica was refit against the paper's Table 1 geometry (area
9 566 mm² vs stated 9 620, **−0.6 %**; AR_geo 1.51; elliptic deviation
0.061) and swept 0–24° on the frozen level-2 recipe, one shared mesh.
Gates are now against *their measurement*, not just theory
(`scripts/bw04_compare.py`; digitized Fig. 2 with ±0.02–0.03 reading
uncertainty; data preserved in `bench/bw04-polar-ideal.json`):

| Gate | Result | Criterion | Verdict |
|---|---|---|---|
| Lift slope (fit 0–8°) | 0.0572/° vs measured 0.0500/° → **+14.5 %** | < 15 % | PASS |
| Zero-lift angle | −3.77° vs measured −3.5° → Δ 0.27° | < 1° | PASS |
| Mean \|ΔCL\| (linear range) | **0.070** | < 0.05 | **FAIL** |
| CD at α = 0 | 0.0260 vs measured ≈ 0.030 | ± 0.02 | PASS |

DATCOM cross-check: the CFD slope is within 3 % of the k = 2 theory value
(3.28 vs 3.37/rad) — theory and CFD agree with each other and both sit
above the tunnel. The knee lands at α ≈ 14° (measured break 12–14°) and
the drag polar tracks the measured points to 20°. Past the knee their CL
keeps climbing (to 1.10 at 24°, laminar-bubble burst + unsteady vortex
lift) while steady fully-turbulent RANS plateaus at 0.87 — the known
model-scope boundary, not a mesh problem. Plot: `out/bw04-comparison.png`.

## Tunnel-wall experiment — how much of the offset is *their* wall?

[BW04] mounted the fin through a tunnel-wall boundary layer they state as
span/6 ≈ 20 mm (1/7-power profile). Our bench idealizes that wall as a
symmetry plane — a perfect reflection with no BL. Hypothesis: their wall
BL unloads the fin root and drags the whole measured curve down; ours
doesn't, hence the offset. Test: `CaseSpec(tunnel_wall=True)` turns the
board plane into a no-slip wall with 1.3 m of upstream fetch (flat-plate
correlation → δ ≈ 20 mm at the fin), rerun the linear range
(`scripts/bw04_tunnel.py`, data `bench/bw04-polar-tunnel.json`).

Sampled profile at the fin station: δ99 ≈ 50 mm as meshed (edge smeared
by the coarse floor cells), displacement thickness **4.7 mm — ≈ 1.9× a
textbook 20 mm turbulent BL**. The modeled deficit is therefore *generous*:
whatever share of the gap it explains is an upper bound.

| | slope [/°] | α_ZL | mean \|ΔCL\| 0–8° |
|---|---|---|---|
| Ideal reflection wall | 0.0572 | −3.77° | 0.070 |
| Modeled tunnel wall | 0.0548 | −3.77° | 0.051 |
| [BW04] measurement | 0.0500 | −3.5° | — |

Verdict: the wall BL is real but partial — it closes **≈ ⅓ of the slope
excess** (and moves the offset gate from clear fail to the 0.05 boundary)
while leaving the zero-lift angle untouched, exactly the predicted
signature. The residual +9.6 % has three honest candidates, in likely
order: the paper states its slope to one significant figure (0.05/°);
fully-turbulent SST vs their transitional Re ≈ 6.6×10⁵ flow; digitizing
error. The mean-ΔCL gate stays **red** until a transition model
(γ-Reθ, the next validation tier) can close it for physics reasons
rather than gate-widening.

## Transition tier (γ-Reθ) — a clean null on lift, a real shift on drag

Setup: `CaseSpec(transition=True)` = kOmegaSSTLM on the mesh-level-4
resolved wall (1.19 M cells, absolute prism layers targeting cell-center
y⁺ ≈ 1; achieved y⁺ 0.07–113, avg 11 — ≈ 10 % of faces near the root/tip
seams lost their layers, away from the transition zone). Inlet Tu 1 %
(assumed — the tunnel's value is unpublished), verified by a line probe
to survive undecayed to the fin (0.99 → 1.00 %). Ideal reflection wall,
angles 0/4/8°, 2 500 iterations each (~1.5–1.8 h per angle at 10 ranks).
Data: `bench/bw04-polar-transition.json`.

The model does real transition physics here: at α = 0 the fin runs
**≈ 87 % laminar** (surface eddy viscosity below molecular over the front
90 % of chord, transition only near the TE — matching the extensive
laminar running [BW04]'s own flow visualization describes), and drag
drops accordingly (CD₀ 0.0260 → 0.0245, −8 % at α = 8°).

| ideal wall, 0–8° | slope [/°] | α_ZL | mean \|ΔCL\| |
|---|---|---|---|
| Fully-turbulent SST | 0.0572 | −3.77° | 0.070 |
| γ-Reθ transition | **0.0574** | −3.81° | 0.073 |
| [BW04] measurement | 0.0500 | −3.5° | — |

**Verdict: transition modeling does not move linear-range lift** — the
laminar boundary layer is marginally thinner, decambers the section
marginally less, and nudges CL microscopically *up*. Combined with the
tunnel-wall result, the gap decomposition is: wall BL ≈ ⅓ (measured,
generous upper bound), transition ≈ 0 (measured), remainder — most
plausibly the paper's one-significant-figure slope statement (0.05/°
spans 0.045–0.055; our wall-corrected 0.0548 sits inside it) plus
digitizing error. The linear-range bench is not hiding a physics
deficiency; the red mean-ΔCL gate measures the experiment's reporting
precision as much as our model. Transition's real value going forward is
**drag** (laminar CD₀ feeds the speed axis) and the post-knee regime,
where [BW04]'s laminar-bubble burst lives — steady linear-range lift
never needed it.
