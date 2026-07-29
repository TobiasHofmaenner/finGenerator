# FEM bench: what the structural tier can and cannot tell us

Companion to CFD-BENCH.md. That document validates the *loads*; this one
validates what the fin does with them. Same discipline: every number here
is either converged and stated with its convergence evidence, or it is
labelled as not converged and explained.

The headline is a warning, so it goes first.

## The max-stress readout is not a result

A CalculiX run reports `max von Mises`. On this geometry that number is
**meaningless**, and it took a full day of laddering to establish why.

The tabs are fused to the blade with a boolean union, leaving a sharp
re-entrant corner at the base plane (z = 0) with **270° of material**.
Williams' 1952 wedge solution says the elastic stress there goes as
`σ ~ r^(λ−1)` with λ = 0.5445 — **unbounded**. Not "hard to resolve":
the exact solution of the continuum problem is infinite. The FE value
therefore rises without limit under refinement, at a predicted rate of
`h^-0.4555`.

Fitting our own ladders recovers **0.443** against that theoretical
0.4555 (mean of four ladders; individual fits scatter 0.19–0.61 because
the corner node lands differently on every remesh). The divergence is
not numerical error. It is the model being asked a question that has no
finite answer.

Consequences, all of which we hit:

* No gmsh setting fixes it. Refinement, curvature adaptation and
  higher-order elements change how *fast* you climb, never whether you
  stop. Second-order elements climb faster.
* No boundary condition fixes it — the corner is geometric.
* Error-driven adaptive remeshing would **run away**: high error →
  refine → higher stress → higher error. Never automate it here.
* An earlier "junction SF 1.49" quoted from a single mesh was pure
  artefact. It was the singularity at whatever resolution we stopped at.

## Blade peak: 24.9 MPa, and it is mid-span

The blade is a different story: nothing singular, and it converges hard.

| geometry | nodes | blade peak | spread |
|---|---|---|---|
| base-plane (no tabs) | 13 844 → 212 222 | 25.80 → 25.88 MPa | **0.7 % over 15×** |

Then we varied everything else that could move it:

| varied | range | blade peak |
|---|---|---|
| mesh | 13.8 k → 261 k nodes | 25.77 – 25.95 |
| support model | 4 different BCs | 25.8 – 25.9 |
| foundation stiffness | k = 30 → 3000 N/mm³ | 25.94 – 25.87 |
| large displacement | linear vs NLGEOM | 25.9 → **24.9** |

**Mesh-, BC- and stiffness-independent.** That is expected on reflection —
the blade stress is set by statics, not by how the box holds the root —
but it is worth having measured rather than assumed.

The peak sits at **z = 65.5 mm on a 122.6 mm span (53 %)**, stable to
0.2 mm across a 6× mesh change. Not at the root:

```
z   3– 20   17.30 MPa
z  20– 40   19.99
z  40– 60   25.26
z  60– 80   25.88   <- peak
z  80–100   21.81
z 100–123    6.72
```

A tapered fin thins faster than its bending moment falls, so the
governing station is mid-span. **This is the finding with design
consequences** — see "What tier-0 must change" below.

NLGEOM moves it to 24.9 MPa (−3.7 %) with tip deflection 12.16 mm vs
12.60 linear. At 10 % of span the small-strain assumption was starting
to cost us, in the conservative direction: the moment arm shortens as
the fin bends.

**Which is why the default stays LINEAR.** Both nonlinear modes make the
answer *less* conservative, and they are not free — measured on one
CL 2.0 rung, same geometry, sequential:

| mode | wall clock | blade peak |
|---|---|---|
| linear | **28 s** | 25.77 MPa |
| `--nlgeom` | 37 s (+32 %) | 24.90 |
| `--plastic --nlgeom` | 82 s (**~3×**) | 25.01 |

Plasticity buys 0.5 % for 3× the runtime, and what little moves is
geometric, not material — the whole blade sits far below the ~60 MPa
knee. A softening law at a stress singularity is also a classic
increment-cutback / non-convergence case, so defaulting it on would
trade passing rungs for slow or failing ones. Both flags stay **opt-in
cross-checks**: their value is provenance ("the blade is elastic", "the
corner is benign"), not the headline number.

## The support condition, bracketed then modelled

`--support` grew four modes because each answers a different question:

| mode | what it is | what it is for |
|---|---|---|
| `rigid-box` | everything below z = −1 fixed | conservative bound |
| `tab-base` | only the tab's bottom face fixed | tests tier-0's assumption that the whole root moment crosses z = 0 |
| `base-plane` | no tabs, base face fixed | removes the corner entirely — the clean blade number |
| `spring` | grounded springs, k = k_found × bearing area | the physical model: the box is compliant, not rigid |

`rigid-box` was the original and it was **badly chosen**: its clamp sat
1 mm below the corner, superimposing a clamp-edge singularity on the
geometric one. That is why the z = 0.5–2 mm bands never settled while
z ≥ 3 did.

Worth stating plainly: **a fixed BC is itself a singularity source.**
`base-plane` has no re-entrant corner at all and *still* shows 38 %
spread at z = 0, because a face pinned in all DOF adjacent to a free
face is a discontinuity in boundary condition. No BC is free.

## Reading the junction honestly

The singular field decays, so at fixed distance the stress is finite and
converges. That is standard hot-spot / structural-stress practice, and
it is the only defensible way to read this corner.

| band | spread over the finest rungs |
|---|---|
| z = 0 (the corner) | 14.5 % — never converges |
| z = 0.5 – 2.0 | 5–12 % — inside the singular field |
| z = 3.0 | 4.4 % |
| z = 5.0 | **1.9 %** — 18.28 MPa, solid |

Extrapolating linearly from z = 3 and z = 5 to the notch:

| support | junction hot-spot | SF |
|---|---|---|
| spring k = 100 (compliant box) | 26.2 MPa | **1.90** |
| rigid-box (fully fixed) | 26.9 MPa | 1.85 |
| spring k = 1000 (stiff box) | 27.7 MPa | 1.80 |
| tab-base (no side support) | 38.6 MPa | 1.29 |

Every *physical* model lands within 6 %. `tab-base` is the outlier and
is unphysical — a tab with zero side bearing does not occur in a box.

A caution recorded for the next person: in the raw *corner* values the
junction stress looks non-monotonic in k (minimum near k ≈ 30–100).
That does not survive the hot-spot read, where it is flat across
physical stiffnesses. It was singularity artefact, not physics.

## Why the junction is not a failure mechanism

The decisive argument is not a simulation result. It is a comparison of
length scales.

Giving the solver a yield limit (`*PLASTIC`, knee assumed at 60 MPa)
produced **no yielding at all** — peak 33.8 MPa. So we sized the bubble
that *would* yield, from the fitted singularity coefficient:

```
elastic field reaches yield at r = 146 µm
```

| length | size | vs. yield bubble |
|---|---|---|
| **plastic zone** | **146 µm** | — |
| finest element at the corner | 499 µm | 3.4× bigger |
| material critical distance L | 520 µm | 3.6× bigger |
| nozzle-formed corner radius | 300 µm | 2.1× bigger |
| one print layer | 200 µm | 1.4× bigger |
| chopped carbon fibre | 100 µm | 0.7× **smaller** |

**The region where this fin exceeds Hooke's law is about the size of one
carbon fibre**, and smaller than a printed layer. Robust to the assumed
knee: even a pessimistic 40 MPa gives 356 µm, still inside L.

L here is Taylor's critical distance, `L = (1/π)(K_IC/σ_u)²`, the length
over which stress must be elevated for a material to register it:

| material | L | behaviour |
|---|---|---|
| mild steel | 4.97 mm | you cannot break it at a scratch |
| **PA12-CF (ours)** | **0.52 mm** | notch-tolerant |
| soda-lime glass | 0.062 mm | a scratch *is* the failure |

That contrast is the whole story: same equations, same singularities,
different length scale.

To *resolve* a 146 µm zone with ~5 elements would need 29 µm elements at
the corner — 17× finer than our finest run. We were never going to see
it, and it was never going to matter.

**Verdict, SCOPED: for this fin the blade governs at SF 2.00 and the tab
junction is not a failure mode.**

That scope is not a formality — the argument does not generalise, and an
earlier draft of this document wrongly stated it as a general result.
The measured fin is a **46 kg rider on CLICK_TAB**: the LARGEST tab
section in the system (S_tab ≈ 492 mm³) at the LIGHTEST load in the
supported range. The whole sub-L argument rests on r_p = 146 µm, and
under small-scale yielding r_p scales as σ², so it degrades fast:

| rider / system | tab stress | implied r_p | vs L = 520 µm |
|---|---|---|---|
| 46 kg CLICK_TAB (measured) | 50.9 MPa | 146 µm | **below** ✓ |
| 80 kg DUAL_TAB | 158 MPa | ~700 µm | above ✗ |
| 95 kg PRO CLICK_TAB | 122 MPa | ~450 µm | marginal |
| 95 kg PRO DUAL_TAB | 238 MPa | ~2.7 mm | far above ✗ |
| 120 kg PRO DUAL_TAB | 293 MPa | ~4 mm | far above ✗ |

**So the tab gate stays on by default.** It may be retired only inside
the validated envelope (CLICK_TAB at martina-class loads), never as a
global default — every rider constructed without an explicit
`tab_sf_min` would otherwise be silently un-gated.

Static argument only, in any case. The failure this gate exists to
prevent — snapping flush at the deck — is a fatigue/impact mode, and a
converged static FEM cannot speak to it.

## Fillets: attempted, abandoned, and why

Considerable effort went into blending the junction. It does not work
and should not be retried:

* The blend must add material into the void quadrant — **which is the
  box slot**. Tab is 6.15 mm in a 6.35 mm slot, so the available radius
  is the 0.2 mm fit clearance. A 0.6 mm fillet makes the tab 6.75 mm and
  the fin will not seat.
* OCCT declines the blend on the boolean result regardless (4 of 10
  edges, and never the load-bearing ones). Chamfer "applied" 12 blends
  on 10 edges — it was cutting edges created by its own earlier cuts.
* It is moot anyway: a 0.4 mm nozzle cannot lay a sharp internal corner,
  so the printed part carries a radius near the maximum that would fit,
  and that radius is *below the material's own critical distance*.

`fingen.tabfillet` and the `--root-fillet` / `--tip-fillet` flags are
retained only for reproducing this negative result.

## What tier-0 must change

**`sizing.base_bending_stress_mpa` evaluated only the base section**, and
on THIS fin that under-read the peak: 19.40 MPa predicted against a
mid-span truth of 25.9, i.e. SF 2.57 reported where the answer is 1.92.

**But that is a property of this fin, not of the gate.** An adversarial
sweep of the 144-fin archive corrected an earlier draft here:

* the base **IS** the critical section for **~45 %** of archived fins;
* a naive station-sweep replacement reads **LOWER** than the old gate on
  **76 %** of them, because dropping the 0.45 arm for the distributed
  load's true 0.372 centroid removes a 1.21× moment inflation that more
  than covers the peak/base ratio on most shapes.

So the honest statement is: **the two models fail in opposite halves of
the design space**, and the fix is neither one alone.

**Shipped fix: the envelope.** `sizing.peak_bending_stress_mpa` returns
`max(base_bending_stress_mpa, flex_report(...).stress_max_mpa)` —
root-plane pad where the root governs, station sweep where it does not.
Verified never to read below the gate it replaced. `check_anchor` takes
the already-solved flex value from `optimize.evaluate` so the hot path
pays for one flex solve, not two.

Two implementation traps found and avoided:

* A station sweep **cannot** be built on top of the CP point load.
  `M(z) = F·(a − z)` is zero beyond `a = 0.45·depth = 55.2 mm`, so its
  max is always z = 0 — it lands at z/d 0.24 instead of the measured
  0.53. The `w ∝ c(z)` load shape is REQUIRED, not a refinement.
* Re-implementing the sweep inside `sizing.py` aliases the groove band
  (48 uniform stations vs a 6 mm groove pitch — up to −21 % on grooved
  fins). `fingen.flex` already injects `groove_station_z`; delegate to
  it rather than duplicating it.

Left deliberately alone, with provenance amended rather than refitted:

* `CP_SPAN_FRACTION = 0.45` vs a measured centroid of 0.375. Retained as
  a deliberate ~1.2× pad on a single-section estimate — it is precisely
  what keeps the root half of the envelope conservative.
* `KT_TAB = 2.5` vs an effective **1.5–2.1** implied by the hot-spot
  read. Conservative, gates nothing, and the back-out is an
  extrapolation rather than a converged K_t. These two are coupled —
  they multiply in the tab moment — so changing one alone double-counts.
* `STRUCTURAL_SF`, both print knockdowns, and the allowable derivation:
  **nothing measured today speaks to the strength side** of the
  inequality. A stress FEM carries no strength information; refitting
  them off one would be a category error.

## Method notes

Tier-1 structural runs go through `finGenerator-cfd/scripts/fin_case_b.py`:
CFD on the tab-less blade → surface pressure → mapped onto the FEM faces
→ scaled to the anchor's design peak → CalculiX. The CFD is cached, so a
mesh ladder after the first rung is gmsh + ccx only.

Rungs are independent and run **concurrently** (`fem_ladder_par.sh`) —
8 rungs in ~6 minutes wall-clock against ~50 sequential.

Supporting tools:

* `hotspot_probe.py` — band stresses vs mesh, with the convergence
  spread. Use this, not the max, at any tabbed geometry.
* `corner_probe.py` — nodes on the singular edge, local element size,
  and the extracted singularity coefficient.
* `fem_to_vtk.py` — rebuilds the *load* and *clamp* as VTK from the
  solved deck, for visual verification of what the solver actually saw.
  Both are reconstructed from files on disk; no re-solve.

CalculiX gotchas paid for the hard way:

* `*SPRING` counts as a **material**. One card per node declares 1600+
  and ccx rejects the deck — bin the stiffnesses (we use 16 quantiles).
* A `*SPRING` card is DOF then constant with **no blank temperature
  line**; the blank parses as a second data point and the card is
  refused with "*SPRING card without data".
* Nodal stress is extrapolated from Gauss points. At a singular corner
  that extrapolation is unreliable and not even reliably monotonic — our
  finest rung reported a *lower* corner peak than the one before it.
  Extract from a range of r; never sample r → 0.
