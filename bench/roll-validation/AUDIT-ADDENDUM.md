# Roll-damping (L_p) validation — AUDIT ADDENDUM (supersedes VERDICT.md's magnitude claim)

**Date:** 2026-07-26. **Status:** the independent factor-of-2 audit below **overturns the basis** of
the finite-span correction first read off this bench. `VERDICT.md` and `out/roll-clp-anchors.md` §4
are corrected accordingly. The roll code itself was **verified clean** by the audit — formula, units,
strip quadrature, and the CFD roll-moment path are all confirmed. What changes is the **attribution
and magnitude** of the tier-0 over-prediction, and therefore the applied correction factor.

## What the audit did

A converged lifting-line (LL) solve, N = 80–480 spanwise stations (Richardson-converged), checked
against the elliptic closed form, Toll & Queijo TN 1581 eq. 27 [TQ48], and Goodman & Fisher [GF49].
It recomputed the rolling derivative of the **actual near-triangular tapered default fin** (not a
rectangular stand-in) and decomposed the twisted-inflow CFD/tier-0 ratio.

## The three findings that overturn the 2×

1. **Tier-0 already uses the 3D slope, so the residual rolling relief is ~7 %, not 2×.** The strip
   integral substitutes the fin's 3D DATCOM lift slope for the 2D section slope. A converged LL gives
   the tapered fin **C_lp = −0.2228** vs tier-0 strip **−0.2384** — an *additional* rolling-specific
   finite-span relief of only **~7 %**. The anchors-file §4 "~2×" table was **apples-to-oranges**: it
   used the *rectangular* closed form −a₃D/6 → C_lp ≈ **−1.103** for "fingen" (the actual tapered fin
   is **−0.723**) and compared it to rectangular [GF49] wings.

2. **Honest decomposition of the observed CFD/tier-0 = 0.49** — one real effect, three artifacts:

   | factor | value | nature |
   |---|---|---|
   | antisymmetric rolling relief (LL vs strip) | **0.93** | real physics |
   | viscous / lifting-surface knockdown (LL → measured [GF49]) | **0.78** | real physics |
   | imposed-shear attenuation (freestream lateral BCs relax uy to ~0.75–0.87 of nominal) | **0.80** | **rig artifact** |
   | concave secant at finite ω vs the ω→0 derivative (Richardson → −0.124…−0.138) | **0.85** | **analysis artifact** |

   0.93 × 0.78 × 0.80 × 0.85 ≈ 0.49. Only the first two are physics.

3. **The concavity is a rig artifact, not span-load physics.** The imposed linear shear is relaxed
   *proportionally more* at larger ω by the freestream lateral BCs, so the secant softens with ω. It
   is not the antisymmetric span-load building with roll rate (VERDICT.md's reading). The
   L_p-relevant number is the ω→0 derivative, recovered by extrapolation.

## Two further caveats

4. **Symmetric-mirror ≠ antisymmetric rolling.** The `symmetryPlane` board boundary solves the
   *symmetric-mirror* problem (α = ω·|z|), which differs ~20 % from true *antisymmetric* rolling
   (α = ω·z). So even the [GF49]-rig equivalence — the headline "our bench IS the rolling-flow
   experiment" claim — is **inexact**. A true-antisymmetric rig (rotating frame, or an anti-symmetry
   plane) is the clean setup.

5. **Best de-artifacted ratio.** After removing the shear and concavity artifacts, the honest
   **CFD/tier-0 ≈ 0.70, band 0.56–0.77.** Equivalently the de-biased ω→0 derivative is
   **−0.124…−0.138 N·m·s** before de-attenuating the shear; dividing by the 0.75–0.87 shear
   preservation gives a true-derivative band **≈ 0.143–0.184 N·m·s**.

## What this means for the model

- **Strip SHAPE: still validated.** The S·s² depth scaling — the depth *ranking* the module exists
  to give the optimizer — is unaffected. Only the absolute level carries a knockdown.
- **The applied correction is now `roll.KAPPA_FS = 0.73`** — an **audit-calibrated constant**
  (provenance 0.93 rolling relief × 0.78 viscous knockdown; honest band 0.56–0.77), **not** the
  textbook A/(A+4) = 0.465, which fit the artifact-laden 0.49 and is ~2× too aggressive. κ is
  **planform-dependent** (this value fits the near-triangular default taper) and **provisional**.
- **Honest tier-0 over-prediction: ≈1.3–1.4×** (was reported ~2×).
- **Withdrawn from VERDICT.md:** (a) the "~2× strip-theory finite-span deficit" attribution; (b) the
  "CFD near-zero secant −0.117 matches ½·L_p −0.119 to 2 %" comparison (the ½·strip target was the
  rectangular mix-up; −0.117 is an artifact-laden finite-ω secant). VERDICT.md's data (M_x tables,
  convergence, y⁺) and its shear-attenuation and concavity *observations* stand; its physical
  *interpretation* of them as span-load physics is superseded by the artifact decomposition above.

## Refinement path (to graduate κ from provisional)

1. **Fixed-rig CFD rerun** — impose uy(z) = ω·z on **all** inflow boundaries (inlet + top/side
   farfield: already applied to `scripts/roll_validation.py`) so the fin sees ≈ nominal shear, over a
   **denser low-ω sweep (0, 0.5, 1, 2, 3)** with an **ω→0 Richardson extrapolation**.
2. **True-antisymmetric setup** (rotating frame or anti-symmetry plane) to remove the symmetric-mirror
   ~20 % bias.
3. **[GF49] bench replication** — build the untapered NACA 0012 wings and read C_lp directly, to pin
   the viscous knockdown independently of the tapered-fin CFD.

*Refs: [GF49] NACA Rep 968/TN 1835 Goodman & Fisher; [TQ48] NACA TN 1581 Toll & Queijo eq. 27; USAF
DATCOM §7.1.2.2. Superseded doc: `VERDICT.md`. Data: `roll-clp.json`, `cases-summary.json`.*
