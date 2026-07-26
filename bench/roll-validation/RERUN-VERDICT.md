# Roll-damping fixed-rig CFD rerun — VERDICT

**Date:** 2026-07-26. Refinement pass after the audit (`AUDIT-ADDENDUM.md`) found the
first run's damping number contaminated by two artifacts: an imposed-shear
*attenuation* (freestream lateral BCs relaxed uy toward 0, fin saw ~0.75–0.87 of
nominal) and an *analysis* concavity read off the finite-ω secants. This rerun
imposes the roll shear `uy(z) = ω·z` on **all** inflow boundaries — inlet **and**
the top/side `farfield` (the fix under test) — over a denser sweep
ω = (0, 0.5, 1, 2, 3), and extracts the ω→0 derivative.

Same frozen fidelity: mesh_level 2, **360 134 cells** (exact match to the first
run), one mesh reused across ω, 12-rank decomposition, simpleFoam k-ω SST wall
functions, end_time 800 (all tail std < 0.02 %), y⁺ on fin 15.2–441.7 (avg 81.3).
Cases live in scratchpad, not the repo. **BC deviation** (as first run): this
OpenFOAM install is runtime-only (no `wmake`), so the HEAD writer's
`codedFixedValue` cannot compile its lib; swapped to `exprFixedValue`
(`uy=ω·pos().z()`, libfiniteVolume, runtime-parsed) on inlet **and** farfield —
physics identical, fix preserved. Verified in every written `0/U` before solving.

## Numbers

| ω [rad/s] | M_x (tail mean) [N·m] | secant from ω=0 [N·m·s] | tail std |
|---:|---:|---:|---:|
| 0.0 | −1.59482 | — | 0.016 % |
| 0.5 | −1.72371 | −0.2578 | 0.006 % |
| 1.0 | −1.85065 | −0.2558 | 0.002 % |
| 2.0 | −2.10810 | −0.2566 | 0.008 % |
| 3.0 | −2.36182 | −0.2557 | 0.002 % |

- **(a) LSQ line (all 5):** slope **−0.2557 N·m·s**, R² **0.99999**, intercept −1.5954
  (= baseline M_x(0) to 0.04 %).
- **(b) ω→0 derivative** (dense low-ω 0/0.5/1): quadratic/Richardson/3-pt FD all
  coincide at **−0.2597**; 5-pt quad −0.2574, cubic −0.2552. **Honest ω→0
  |L_p| = 0.256–0.260, central 0.260 N·m·s.** No shear de-bias (preservation ≥ 1).

## 1. Rig fix effective? — **YES.**

Freestream shear preservation `uy(z)/(ω·z)` at x = −0.30 m (z 0.05–0.11, ω=2) =
**1.016** (was **0.87** in the first run). The domain now sustains the nominal
linear shear to <2 %. Near-fin stations read **1.07** (x=−0.15) and **1.32**
(x=−0.03) — *above* nominal: the fin's own bound-vortex sidewash, which is
physical and case-appropriate, not a BC artifact. The attenuation is gone.

## 2. Concavity gone? — **YES, as the audit predicted.**

The secants from ω=0 are flat (−0.258, −0.256, −0.257, −0.256); fitted curvature
d²M_x/dω² = **+0.001** (≈0); LSQ R² = 0.99999. The first run's concavity
(secant softening 0→1 −0.117, 2→3 −0.075) has **vanished**. This confirms the
audit: the concavity was the imposed-shear relaxing more at larger ω — a rig
artifact — **not** antisymmetric span-load physics. With it gone, the LSQ slope
and the ω→0 derivative coincide (−0.256 vs −0.260).

## 3. Honest κ, band, and the KAPPA_FS recommendation

**The fixed-rig number is much higher than either the first run or the audit
predicted, and it overshoots the audit band — for a physical reason the audit
itself flagged (caveat 4).**

| quantity | value |
|---|---|
| honest ω→0 \|L_p\| (CFD) | **0.260 N·m·s** |
| strip \|L_p\| (uncorrected) | 0.2383 |
| tier-0 corrected \|L_p\| (κ=0.73) | 0.1740 |
| CFD / strip = **implied κ (direct)** | **1.09** (band 1.07–1.09) |
| CFD / tier-0 corrected | 1.49 |
| audit true-antisym band 0.143–0.184 → κ | 0.60–0.77 |

**Why it lands at 1.09× strip, above even the inviscid lifting line:** the
`symmetryPlane` board makes this CFD solve the **symmetric-mirror** problem
(α = ω·|z|), **not** true antisymmetric rolling (α = ω·z) — audit caveat 4. The
audit's own independent lifting line for the *mirror* problem is **0.268 inviscid**;
the viscous CFD gives **0.260**, matching it to **3 %** (CFD 4 % below, as
viscosity should). Two consequences:

- **Measured viscous knockdown ≈ 0.97** (CFD/mirror-LL), **not the 0.78** the audit
  assumed from [GF49]. This is the single largest reason κ comes out high: κ=0.73
  = 0.93 (rolling relief) × 0.78 (viscous); the RANS reproduces the ~0.93 relief
  structure but shows almost no viscous lift knockdown for this attached-flow case.
- **De-mirrored to true antisymmetric rolling** (audit ÷1.20): derivative
  **0.216 N·m·s**, **implied κ = 0.91** (band **0.87–0.95**).

### Does κ = 0.73 stand? — **No.**

Neither reading supports it: direct (symmetric-mirror) κ = **1.09**; de-mirrored
(true antisymmetric) κ = **0.91**. Both say the finite-span + viscous knockdown for
this near-triangular fin is **modest (~10 %), not ~27 %**. 0.73 was
0.93 × 0.78; the fixed-rig RANS keeps the 0.93 but measures the viscous factor at
~0.97, not 0.78.

### Recommendation

**Raise `roll.KAPPA_FS` from 0.73 to ≈ 0.90** — the de-mirrored fixed-rig CFD value
(band 0.87–0.95), which equals rolling relief 0.93 × CFD-measured viscous ~0.97.
Two hedges the number must carry:

1. **The de-mirror (÷1.20) is the audit's lifting-line estimate, not measured.**
   The remaining ambiguity is exactly refinement-path item 2: a true-antisymmetric
   rig (rotating frame or anti-symmetry plane) is needed to confirm the 20 % and
   pin κ. Until then κ ≈ 0.90 is **provisional**.
2. **RANS viscous fidelity.** y⁺ 15–441 (wall functions, fully-turbulent SST) may
   under-predict viscous lift loss; if the [GF49]-measured 0.78 is the truer
   lifting-surface knockdown, κ could sit as low as ~0.73–0.78. A resolved-wall or
   [GF49]-replication rerun (item 3) would settle it.

**Interim:** if a single hedged number is wanted spanning the RANS-vs-[GF49]
viscous-knockdown tension, **κ ≈ 0.85 ± 0.10**; the CFD-preferred central is 0.90.
Roll damping stays **report-only** until the true-antisymmetric rig closes the
mirror gap. What is now firmly established: the shear-attenuation and concavity
artifacts are **confirmed and removed**, the strip **shape** is validated (the
response is clean-linear in ω), and the absolute knockdown is **far milder than
0.73** — the strip level is close to correct, not ~1.4× high.

*Data: `rerun-fixed-rig.json`; plot: `rerun-fixed-rig.png`. Supersedes the κ
magnitude discussion pending items 2–3 of `AUDIT-ADDENDUM.md`.*
