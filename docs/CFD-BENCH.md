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

### What the ladder did not cover (2026-11-20)

The ladder converged a symmetric fin at +6°, and levels 2 and 3 share their
surface cells. Two things it could not see, both found on cambered side fins
run below their zero-lift angle (`bench/cambered-candidate/`,
`bench/section-tables/mesh-recipe/`, `docs/MODEL-EXTENSION.md`):

- **Level 2 and 3 read a cambered fin's drag high below about −3° of own
  incidence** (by 1.5–2.6 N per fin at 8.5 m/s): the nose is under-resolved
  and the attached range ends about a degree early. Use `mesh_level=5`
  (level 2 with one more surface refinement: base/160 on the faces, base/320
  at the nose and trailing edge, 550 000 cells, first cell still in the log
  layer) for a cambered fin's drag going straight.
- **A wall-function total can agree for the wrong reasons.** On level 5 the
  friction part of the drag is 30–40 % below a resolved-wall section's and
  the pressure part above it; near zero lift the two cancel within 5 %. Read
  lift, induced drag and the order of fins off these polars; not the last
  10 % of drag, and not where an attached range ends. Split a case with
  `finGenerator-cfd/scripts/sample_surface.sh` and `surface_split.py`.
- **A row at the iteration cap is not an unsettled row.** The cap counts
  residuals. Check the force history (`postProcessing/forceCoeffs`): the
  capped level-5 rows are steady within 0.01–1.5 % over their last 200
  iterations.
- **The geometry handed to the mesher has its own resolution**
  (2026-11-21, `bench/section-tables/nose/`). The 2-D referee's outline had
  100 points and two splines meeting at the leading edge: a corner of 33° and
  32 µm of shape error on a 0.65 mm nose. Cells of 0.19 mm did not see it;
  cells of 0.02–0.09 mm meshed it, and a day of nose refinement moved the
  ends of the attached range back and forth by a degree. With the outline
  exact the mesh converges from seven cells per nose radius, and the range is
  two degrees wider at each end. Before refining, compare the surface with
  the analytic shape at the scale of the cells asked for; and refine a
  region, not a criterion (the mesher's curvature rule refines less area at
  every level). `fingen.loft` draws fins with the same two splines: a 3-D
  mesh with a resolved nose needs that changed first.
- **The 3-D fin surface was faceted far coarser than its sections**
  (2026-11-23, `bench/knee/one-degree/`). `fincfd.case` exported the STL
  with the library's default tolerance, which is relative (1e-3 of each
  face's size, about 0.1 mm on a fin): 26 000 triangles, and on the outer blade a corner
  of 51–55° at the leading edge with facets up to 0.066 mm off a nose of
  0.23–0.26 mm radius. Levels 5 and 6 (nose faces 0.2–0.4 mm) are coarser
  than that; a nose split once more (level 7, 0.086 mm) is not, and its
  result cannot be told from the facets'. `CaseSpec.exact_surface` (400
  points per section, an ABSOLUTE deflection of 1 µm; levels 7 and 8 set it)
  gives a nose within 0.010 mm of the section with no corner above 10°, in
  14 s and 2.7 GB. Its first version passed 2e-6 to the relative setting and
  needed 33 GB to write the same nose: measure what a new step takes before
  it runs on a shared machine. Cut the STL with
  `bench/knee/one-degree/stl_nose.py` before any run whose nose faces are
  under 0.3 mm.
- **A control one level finer is no control when both levels are on the same
  side of what has to be resolved** (same record). Levels 5 and 6 agreed on a
  thick symmetric blade's break within 0.2° with about one face on the nose
  radius of the strips that let go; so did half the speed. Count the faces on
  the nose radius of the most loaded strips (`strip_loads.py` prints them)
  and say what the next level would have to change.
- **A swinging row's filed value is the mean of its last 150 iterations,
  one sample of the swing** (2026-11-24). The tunnel fin at 14° on level 6
  filed 0.999 on one machine and 0.945 on another (12 and 8 processes, every
  settled row identical to four digits): 2.3 % or 7.6 % below its line,
  with the measurement at 6 %. Print the window means of every row at the
  cap (`bench/knee/one-degree/hist.py`) and quote their spread, not the filed
  number.
- **A threshold of the mesh recipe that is an absolute size has to be read
  against the finest cell before a finer level or a smaller fin is run**
  (2026-11-24). `minVol` was 1e-13 m³. On level 7 the untouched cells of a
  fin under 108 mm of base are below it: the mesher counts every one as an
  error before it snaps, accepts any move that leaves no more errors than
  that, and ends "with 715693 illegal faces" on a mesh that then runs (or
  diverges, as two others did). On a larger fin the cells are just above it
  and the mesher refuses part of the snap instead: it ends "without any
  errors" with points a cell width off the surface. Three level checks were
  read off such meshes (`bench/knee/one-degree`, "Level 7 as it was
  meshed"). The threshold now follows the finest cell, and `polar_angles.py`
  prints a `mesh:` line per mesh (flagged faces, and what the last snapping
  move still wanted: a fraction of a micrometre on a sound mesh). Read it
  before any force.
- **The mesher ends "without any errors" on a mesh that lost its wall
  layers** (2026-11-21). snappyHexMesh takes a layer stack off again where it
  does not fit. A flat-inside section with a nose corner of 0.1 mm radius kept
  1.9 layers of 13 and gave plausible forces, with y+ up to 19 on a wall meant
  to be resolved. Read the layer summary in `log.snappyHexMesh` (mean layers,
  percent of the target thickness) for every mesh; `section_polar.py` records
  it and refuses a resolved-wall mesh below 90 %. The 2-D rerun's sections
  have 99.6 % or more.

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
- **The stream (2026-11-21, `bench/section-gate/` section 3).** Every case
  here sets 5 % turbulence with a length of a tenth of the chord at the
  inlet and lets it decay on the way to the fin; what arrives depends on
  the upstream fetch (20 chords in the 2-D referee, 4 base chords in the
  3-D cases). In 2-D that stream does not move lift, adds 5–12 % to a
  NACA 0012's drag against tripped tunnels ([McC87]) and delays the break by
  a quarter to half a degree. A quiet stream is no cure below Re of a
  million: the SST model then runs laminar over the first part of the
  chord ([RS09]). The 2-D referee has used a held stream since then
  ([SR07]; k = 1e-3 U², ω = 5 U/c). The 3-D writers take it as an option
  (`held_stream`), off by default, and no 3-D record uses it yet: drag
  from 2-D sections on the held stream and from 3-D cases is not on the
  same stream. Compare fully turbulent drag with tripped data only; item 3
  above and the first section gate compared with untripped [SK81].
- **Maximum lift of a 2-D section is the model's, not the section's**
  (`bench/section-gate/` section 2): with a resolved wall and an exact
  nose the NACA 0012 at Re 7e5 peaks 18 % above [SK81] and 2° late, the
  NACA 4415 reads 11 % high at 10°. Wall functions err the other way
  (item 3). A section's upper end from RANS is an upper bound.
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
