# CFD bench: setup, mesh-convergence ladder, frozen recipe

> **Note (repo split).** The CFD harness itself — the `fingen.cfd` package and the
> solver/mesh driver scripts referenced throughout this document
> (`scripts/tmr_flatplate.py`, `sk81_naca0012.py`, `zarruk_polar.py`, `bw04_*.py`,
> `falk_thruster.py`, and the rest) — now lives in a **separate private compute
> repo**. This public repository retains the validation *findings* recorded here
> and the benchmark data under `bench/`; the script paths named below are
> historical pointers into that private repo, not files in this tree.

> **Structural results live in FEM-BENCH.md.** This document validates the
> *loads*; that one validates what the fin does with them — mesh ladders,
> support-condition studies, and the stress-singularity analysis that
> determines which FEM numbers may be quoted at all.

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

1. **ERCOFTAC T3A flat plate** — ✅ DONE. Tutorial mesh, kOmegaSSTLM,
   Tu 3.3 %: laminar plateau tracks Blasius, transition onset at
   Re_x 1.1×10⁵ vs measured ≈ 1.4×10⁵ (≈ 20 % early — inside the
   published scatter of γ-Reθ implementations, onset being sensitive to
   the inlet viscosity ratio), turbulent recovery converges onto the
   measured Cf within a few % downstream. Mean |ΔCf| 12 % (dominated by
   the steep mid-transition region). The transition-model machinery our
   CaseSpec(transition=True) mode uses reproduces the canonical
   benchmark. Plot: `out/t3a-validation.png`.
2. **NASA TMR 2D flat plate** — ✅ DONE (`scripts/tmr_flatplate.py`;
   the TMR now lives at tmbwg.github.io/turbmodels). Incompressible
   analog at Re_L 5×10⁶ vs the CFL3D SST reference: wall-resolved mesh
   (y⁺ 0.04–0.12) hits Cf(0.97) within **−2.5 %** with mean |ΔCf| 1.8 %
   and the u⁺(y⁺) profile on the law-of-the-wall reference through
   sublayer, log layer and wake — the SST implementation is sane. The
   production wall-function band (y⁺ 12–91, our fin-bench regime) lands
   Cf(0.97) within **−0.2 %** with mean |ΔCf| 3.7 %, the error
   concentrated in the leading-edge transient (x < 0.25) where y⁺ falls
   out of band — for the fin this is a small chord fraction. Plot:
   `out/tmr-flatplate.png`. Their 2D bump / NACA 0012 / RAE 2822
   families remain available as follow-ups.
3. **Extruded NACA 0012 vs [SK81]** — ✅ DONE (`scripts/sk81_naca0012.py`,
   data `bench/sk81-naca0012-700k.json`). Forensics first: the popular
   OWENSAero digitization of the SK81 tables is **mislabeled 10×** (its
   "Re 3.6M" is the report's 360k block — verified digit-for-digit against
   the original scan; SK81 has no 3.6M table). Reference re-transcribed
   from the scan's Re 700k block (`bench/ref-sk81-naca0012-re0.7M.dat`).
   Quasi-2D extruded section, fin-bench L2-style wall-function recipe:
   lift slope 5.12 vs 6.30/rad (**−18.7 %, PASS < 20 %**), decomposed by
   a ±8c domain probe — 28 % domain confinement, the rest wall-function
   decambering. CD₀ +24 % vs the transitional measurement (expected:
   fully-turbulent vs natural laminar run). Break onset lands within
   1–3° of the table but CL_max is 32 % soft — steady wall-function RANS
   can't hold the suction peak; the resolved-wall (level-4) rerun is the
   known upgrade path. Verdict: section-level numbers carry the
   wall-function regime's documented limits at high loading, while the
   3D fin bench (AR-diluted) stays inside its measured gates — exactly
   the tiered picture the ladder exists to draw. Plot:
   `out/sk81-naca0012.png`.
4. **Zarruk 2014 replication** — ✅ DONE (`scripts/zarruk_polar.py`,
   `bench/zarruk/cfd-polar.json`, plot `out/zarruk-typeI-ss.png`).
   In-tunnel simulation (0.6×0.6 m section, no-slip ceiling, foil
   rotated per angle — their data carry no blockage corrections), Type
   I-SS foil, Tu 0.5 % measured. Re 10⁶ gates: lift slope 4.68 vs
   measured 4.82/rad (**−2.9 %, PASS**), CM within 3 % everywhere
   (independently pins the planform/CP call), CD at α=6° within
   0.0004 of measurement — the drag-fidelity anchor BW04 couldn't
   provide. CD₀ low by 0.006 (their balance carries root-fairing
   parasitics we don't model). Re 0.6×10⁶ stall side: early separation
   as expected fully-turbulent (transition tier upgrade available).
   **Tier-0 flex pre-validation**: pressure-integrated root moment +
   the paper's own stiffness gives tip deflection 4.29 mm vs their
   4.9 mm anchor — CFD load itself only −3 %; the residual is water-
   temperature/q ambiguity at fixed Re. The beam-model approach is
   validated before the flex track even opens. Ceiling-BL caveat:
   natural growth gives 8.2 vs 19 mm measured (clean-inlet undershoot;
   paper states BL variation moves lift < 1 %).
5. **URANS post-knee study** — ✅ DONE (`scripts/bw04_urans.py`, EPYC
   container, ~5.8 h wall; `bench/urans-bw04/urans.json`). **Clean null:
   time resolution is not the missing physics.** URANS means sit within
   1–2 % of the steady plateau (16°: 0.853 vs 0.856; 20°: 0.853 vs
   0.862; 24°: 0.830 vs 0.815) with negligible oscillation (CL std
   ≈ 1e-4 — the separated state is quasi-steady at this fidelity),
   recovering only ~4 % of the steady-vs-measured gap. Conclusion: the
   measured post-knee climb (to 1.10 at 24°) is **transition physics**
   — [BW04]'s own attribution, the bursting laminar separation bubble —
   which fully-turbulent modeling cannot produce at any time
   resolution. Two consequences: (a) the steady plateau is a genuine
   model prediction, not a solver artifact — steady RANS post-knee
   numbers are as good as URANS ones here, at 1/50th the cost;
   (b) closing the post-knee gap requires the transition model on the
   resolved-wall mesh (γ-Reθ post-stall — a known-hard regime, parked
   with honest expectations). Optimizer guidance: near-stall axes use
   the knee LOCATION (validated ±1–3°) and treat post-knee magnitudes
   as lower bounds.
6. **[Els22] groove replication** — ✅ DONE, both tiers
   (`bench/groove-ab/`, `bench/els22/`). Steady 0–20° on the BW04
   replica: grooves never help (knee penalty ΔL/D −10…−19 %). Referee
   experiment at THEIR claim point — Merrick-template fin, 30°,
   time-resolved: **ΔL/D −0.5 % (ΔCL −0.2 %, ΔCD +0.3 %) — a NULL**
   within bench noise, vs their claimed +11 % L/D (−13 % drag). The
   +11 % does not reproduce on a mesh-frozen, measurement-validated
   bench under the G1 interpretation of their (unspecified) groove
   profile. Surviving explanations: their groove depth/width/profile
   differ from our interpretation (ask Wollongong), channel resolution
   (2–5 cells at level 2), or their steady-CFX-at-30° number sits in
   the converged-but-wrong band our bench documents. Meanwhile
   [For24]'s *field* gains (real surfers, faster, preferred) stand —
   and with the hydro path null at every angle tested, the
   **flex-mediated explanation** (their grooved fins measured softer)
   is now the leading hypothesis, quantifiable by the flex track.
7. **Physical structure bench** (user-side) — force–stroke stiffness
   (plain vs grooved, replicating [For24] panel C), load-to-failure vs
   FORCE_SF allowables, seawater-soak stiffness recheck.
8. **Multi-fin interference vs [Falk19/Falk20]** — ✅ DONE
   (`src/fingen/cfd/setcase.py`, `scripts/falk_thruster.py`, per-fin
   summary `bench/falk/thruster-run-summary.json`; ~75 min on the EPYC,
   one shared L2 mesh, 0–30°). The interference structure is
   textbook-correct: **toe hands load between the fronts** (windward
   0.40 vs leeward 0.85 CL at 20° — the progressive-feel mechanism,
   measured), and the **center-rear deficit grows with angle** (−21 %
   at 5°, ≈parity 10–20°, **−27 % at 30°** as the front wake sweeps
   across it). Totals peak 0.62 at 20–25° vs Falk19's ≈0.74 with a
   *different blade* (their FCS template, no-slip board, URANS ≥20°) —
   an absolute gap that is geometry difference, not physics failure.
   Caveats: Falk19's per-fin thruster data is paywalled everywhere
   (verified via five OA indices — ask the authors), so per-fin anchors
   are Falk20's quad patterns (qualitative agreement); the 35–45°
   post-stall tail was skipped (leeway bound, both codes questionable
   there anyway). Exact-anchor follow-up available on demand:
   replica-fit their FCS template like BW04 and rerun. The
   CONFIG_DOMINANT_SHARE heuristics can now be replaced by measured
   interference curves.

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
