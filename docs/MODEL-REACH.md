# Model reach — which design parameters tier-0 can actually see

Audit of 2026-11-19 (gen-3 item 0.5). Question: for every parameter the
optimizer may move, does the physical model have a mechanism that responds to
it, and is that mechanism physics, a proxy, or nothing? Method: one-at-a-time
perturbation of each parameter on Omar's shipped gen-2 side and on the centre
he rides, in two modes — *raw*, and *iso-area* where the base chord is
re-solved so planform area and aspect ratio stay fixed and only SHAPE changes.
Script `scripts/model_reach.py`, full tables `out/model-reach.md`.

## Verdict

The hydrodynamic model sees **four numbers**: planform area, aspect ratio,
half-chord sweep, and section thickness (which on a flat-inside side foil is
also its camber). Every other searchable gene — tip width, leading-edge
fullness, trailing-edge shape, the twelve edge offsets, tip thickness, grooves
— changes the hydro goods (speed, drive, hold, forgiveness) by exactly zero at
fixed area. The structural model sees everything. Roll damping sees the
spanwise chord distribution. The two remaining "handling" quantities, pivot
and release, are geometric proxies, and the pivot one is inverted.

## Parameter by parameter

| parameter | hydro goods | handling | structure | real effects the model lacks |
|---|---|---|---|---|
| depth | yes, via area and AR (lift slope, break angle, induced drag) | lateral stiffness; roll damping ∝ span², +26–33 % per 10 mm | yes | break angle vs AR is a heuristic, unvalidated below AR_eff 2.6 |
| base | yes, via area, AR, Reynolds number | pivot arm only | yes, root section | none major |
| sweep | lift slope only, −3 % per 10° | pivot arm (inverted, below); release proxy | washout coupling, strong: −2.7 pp side, −9.4 pp thin centre per 10° | stall onset and softness, leading-edge vortex lift, post-stall behaviour |
| tip_width_ratio | **blind** at fixed area | roll damping +7–9 % | yes | span loading, tip stall, induced-drag efficiency (e fixed at 0.90) |
| le_fullness | **blind** | pivot arm only | yes | same |
| te_shape | **blind** | pivot arm; release proxy | yes | same |
| 12 edge offsets (stage B) | **blind** | ≤ 2 % | ≤ 4 % | same; only the safety gates and proxies steer them |
| thickness_ratio | side: camber → α0 → hold and margin; form-factor drag. Centre: form factor only | blind | dominant, ∝ t³ | stall vs thickness and nose radius; drag at the toe angle |
| thickness_tip_factor | **blind** (α0 and cd0 read the root section only) | blind | yes | on a flat-inside foil a thinner tip is less camber, i.e. aerodynamic twist |
| grooves | **blind** | blind | yes, not FEM-validated | surface drag, separation |

Fixed, not searched: foil family (symmetric / flat-inside; the 70/30 `CAMBERED`
family exists but is unused), camber ratio and position (only read for the
unused family), trailing-edge thickness (no base-drag term), material (flex
only), toe / cant / positions (not in the optimizer at all).

Validation status of what the model does see: lift slope −5…+7 % on three CFD
fins; zero-lift angle within 0.5° at t/c 0.092 and 0.099; CL_max 20–22 % high;
centre interference 0.716 confirmed by the set CFD; bending and torsion
FEM-anchored at t/c 0.09, flat-inside, no grooves; roll damping calibrated to
wing data, never to a fin; isolated zero-angle drag of the symmetric centre
within 2 % (4.1 vs 4.2 N).

## Three defects found

*Status 2026-11-19: all three corrected in generation 3 (in development) —
`spider.YAW_ARM_REF_MM`, `spider.trim_drag_n`, `hydro.break_alpha_deg`, with
regression tests. The numbers below are the generation-2 behaviour that was
found. Residual of defect 2: the profile drag at negative incidence is still
missing, so the corrected model reads ≈ 5 N per gen-2 side against the set
CFD's 13.3 N; that gap waits for section data (MODEL-EXTENSION.md).*

**1. The pivot axis is inverted for every realistic fin.** `pivot` is
1 / (q·A·CLα·arm) with arm = |x_cp − base/2| + c̄/4. The centre of pressure of
an upright fin sits AHEAD of its base centre, and rake moves it aft toward it,
so the absolute value shrinks with rake up to ≈ 45° and only then grows:

| sweep parameter | 0° | 10° | 20° | 30° | 38° | 45° | 55° | 60° |
|---|---|---|---|---|---|---|---|---|
| x_cp − base/2, mm | −43 | −35 | −26 | −16 | −6 | +5 | +26 | +42 |
| "yaw stiffness", N·m/rad | 72 | 65 | 55 | 43 | 31 | 28 | 50 | 63 |

So between 0° and 45° the model scores MORE rake as MORE pivoty — the opposite
of what every shaper means by the word. The reference point is also arbitrary:
a board yaws about a point 0.4–0.6 m ahead of the fins, where a 20 mm CP shift
is a 3–5 % effect. In a band of near-equivalent goods on Omar's frontier the
axis spans ×3.7, of which the physics (tail lateral stiffness q·A·CLα) is
×1.43 and the arm ×3.2. The taste range reported in the frontier audit was
mostly this artefact.

**2. Side-fin trim drag is read in the wrong condition.** The `speed` good is
the drag of the ISOLATED fin at +1°. A side fin in a set runs at minus its toe
angle, flat face to the flow. Set CFD, per side fin at 8.5 m/s:

| | tier-0 | set CFD, toe 2.5° | toe 3.5° | toe 4.5° |
|---|---|---|---|---|
| gen-2 side, N | 8.7 | 11.2 | 13.3 | 16.1 |

The centre fin in the same runs matches its isolated value (4.2 vs 4.1 N), so
this is not mesh noise. The side pair is 86 % of the set's straight-line drag,
the model under-reads it by a third, and its real driver — how the inside face
behaves at the toe angle — does not exist in the model. Thickness, the knob the
model thinks controls side-fin speed, mostly changes a camber-induced drag term
that the toe-in is there to cancel.

**3. Thickness is an unvalidated free lunch on side fins.** On a flat-inside
foil camber = t/2, so thickening the foil pushes α0 negative, and the model
converts that 1:1 into CL_max and peak margin:

| t/c | 0.05 | 0.09 | 0.12 | 0.15 | 0.22 |
|---|---|---|---|---|---|
| α0, ° | −2.2 | −4.0 | −5.3 | −6.6 | −9.7 |
| CL_max, model | 0.89 | 1.00 | 1.08 | 1.17 | 1.36 |

The camber term was validated at t/c 0.092 and 0.099 only, where CL_max already
reads 20–22 % above CFD. On both frontiers α0 correlates with t/c at +1.00 and
max side force at +0.72…+0.90: the high-hold corner of the frontier (t/c 0.22,
60° sweep, 16 000 mm²) is this extrapolation, not a discovery. *This corrects
the earlier reading that thickness tracks hold on the frontier only through
gate selection.* A one-sided objective would drive every side fin to the
thickness ceiling.

## What the model can honestly offer as levers today

| lever | physical quantity | knob | range at near-fixed goods (Omar / 75 kg) | status |
|---|---|---|---|---|
| size | area: drag against hold and margin | depth, base | the whole frontier | sound; CL_max 20 % optimistic |
| stiff vs forgiving tail | lateral stiffness q·A·CLα against usable angle | aspect ratio | ×1.43 / ×1.20 | sound in the linear part; break angle below AR_eff 2.6 unvalidated |
| planted vs agile | roll damping ∫c·z² | depth, tip width | ×2.2 / ×1.4 | physics sound, magnitude calibrated to wings, feel unvalidated |
| pivot (as coded) | CP arm about the fin's own base | sweep, fullness | ×3.2 / ×2.0 | artefact, inverted — remove |
| release | sweep and elliptic deviation | sweep, TE shape | ×2.3 / ×4.1 | lore proxy — not offered until measured |

## Options

- **A. Shrink to what the model sees (required for gen 3).** Replace the pivot
  arm by signed, board-level lateral stiffness; drop the release proxy; read
  side-fin trim drag at the toe angle from a curve fitted to the set CFD; cap
  flat-inside thickness to the validated band until a CFD trend exists; switch
  stage B (edge offsets) off, since nothing hydrodynamic can tell the outlines
  apart; let structure and roll damping alone decide the shape sliders.
- **B. Extend the model so shape and release become real.** A vortex-lattice
  or nonlinear lifting-line layer with section polars: spanwise loading
  (induced drag, which stations stall first, tip factor as aerodynamic twist),
  centre-of-pressure travel, stall progression and post-stall slope — i.e. a
  physical release. Needs 2-D section data for the foil families over −10…+25°
  and validation against our 3-D polars. Milliseconds per evaluation.
- **C. A now, B next.** Recommended: A makes the one-sided objective safe; B is
  where the snap's physics lives and what the shape parameters are waiting for.
