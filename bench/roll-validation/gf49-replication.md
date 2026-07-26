# GF49 replication — the roll-method MEASURED pin (task #19)

**Date:** 2026-07-26. Twisted-inflow RANS reproduction of Goodman & Fisher's
*rolling-flow* damping-in-roll measurement ([GF49], NACA Rep 968 / TN 1835) on the
**untapered (rectangular) NACA 0012, AR 2.61, unswept** wing (their **wing 4**),
whose measured `C_lp(C_L=0) ≈ −0.22 /rad` is the external hard anchor for the
tier-0 roll model (`fingen.roll`, `roll.KAPPA_FS`). This is refinement-path **item
3** of `AUDIT-ADDENDUM.md` / `RERUN-VERDICT.md` — the independent measurement
check that arbitrates the κ tension the fixed-rig rerun left open.

Data: `gf49-replication.json`, `gf49-cases.json`; plot: `gf49-replication.png`.
Case writer: `scripts/gf49_replication.py` (reuses the frozen level-2
`fingen.cfd.case.write_case`, overwrites the STL with the rectangular wing, the
`0/U` with the roll shear, and injects the roll-moment `forces` FO — the
`roll_validation.py` pattern).

## Setup

| | |
|---|---|
| Wing | rectangular NACA 0012 (t/c 0.12, 0.4 mm blunt TE), **chord 164.1 mm, semi-span 214.2 mm** |
| Reflected AR | **AR_full = 2s/c = 2.610** (= GF49 wing 4); half-wing (semi-span) AR 1.305 |
| Re | **1.00 ×10⁶** at 6.4 m/s (GF49 tested 1–2 ×10⁶; `C_lp(C_L=0)` is a lift-slope quantity the report notes is ~Re-independent, so the Re gap is immaterial for this anchor) |
| Speed / helix | 6.4 m/s; ω {0, 1, 2} rad/s → **pb/2V {0, 0.033, 0.067}** (GF49 tested \|pb/2V\| up to 0.066 — ω=2 sits at the top of their range) |
| Mesh / solver | level 2, **470 661 cells**, one mesh reused across ω, simpleFoam k-ω SST wall functions, end_time 800 (tail std ≤ 0.3 %), 12-rank |
| Board BC | `symmetryPlane` — this solves the **symmetric-mirror** problem (α = ω·\|z\|), see mapping below |
| Inflow BC | **`exprFixedValue`** `uy(z)=ω·pos().z()` on **inlet + farfield** (the all-boundary shear fix). `codedFixedValue` is blocked on this runtime-only OpenFOAM (no `wmake` + root dynamicCode check) — same swap as `VERDICT.md`/`RERUN-VERDICT.md` |

### Method & the ×2/×4 normalization (GF49 convention)

We model the **half-wing** against the board symmetry plane exactly as every fin
case does, read its roll moment `M_x^half` about the root x-axis, and **double**
it. `C_lp` is the standard semi-span-based aircraft derivative:

```
C_l  = M_x^full / (q·S_full·b),   dM_x^full/dω = 2·dM_x^half/dω
C_lp = C_l / (p·b/2V) = 2V·(dM_x^full/dω) / (q·S_full·b²)
```

with **S_full = c·b** (full-wing area) and **b = 2s** (full span). For a
rectangular wing this reduces to strip `C_lp = −a₀/6` (a₀=2π → −1.047).

### Symmetric-mirror ≠ antisymmetric rolling (audit caveat 4)

The `symmetryPlane` board reflects the half-wing with the *same* loading sign, so
it solves the **symmetric-mirror** problem (α = ω·\|z\|), **not** true
antisymmetric rolling (α = ω·z). The audit's converged lifting line puts these
~20 % apart (tapered fin: **0.268 sym-mirror vs 0.223 antisym**, ratio 0.832). We
therefore report the raw sym-mirror CFD `C_lp` **and** the antisym-corrected value
(×0.832) and compare the latter to the measured −0.22. (The 0.832 is borrowed from
the tapered-fin LL audit — the rectangular wing's exact ratio may differ slightly;
it is the same ÷1.20 de-mirror `RERUN-VERDICT.md` used.)

## Numbers

| ω [rad/s] | M_x^half [N·m] | tail std | secant from ω=0 [N·m·s] |
|---:|---:|---:|---:|
| 0.0 | **+1.6975** | 5.1e-3 | — |
| 1.0 | −1.8754 | 1.3e-3 | **−3.573** |
| 2.0 | −5.1564 | 2.8e-3 | −3.516 (0→2); 1→2 secant −3.281 |

- **Baseline `M_x(0)=+1.70 N·m`** — a *spurious* offset. A symmetric wing at zero
  incidence should read 0; snappy's mesh is not perfectly symmetric on the thin
  section, leaving a converged (tail std 0.3 %) ~1.7 N·m pressure roll moment. It
  is a **constant** offset (same mesh, same q across ω) and **cancels in the
  derivative** dM_x/dω — the quantity `C_lp` needs. The slope is what we use.
- **Derivative dM_x^half/dω:** near-zero secant (0→1, the L_p-relevant ω→0 value)
  **−3.573**; LSQ over {0,1,2} −3.427. Mildly concave (secant softens 0→1 −3.573,
  1→2 −3.281) — smaller than the first roll run and partly the coarse {0,1,2}
  spacing; the near-zero secant is the ω→0-correct number.

### C_lp (full-wing, per rad)

| source | C_lp |
|---|---:|
| strip 2-D (−a₀/6) | −1.047 |
| strip 3-D (−a₃D/6, k=2) | −0.517 |
| **LL Toll–Queijo [TQ48]** (inviscid, antisym) | **−0.310** |
| **measured [GF49] wing 4** | **−0.220** |
| CFD sym-mirror (near-zero / LSQ) | −0.338 / −0.324 |
| **CFD antisym-corrected (near-zero / LSQ)** | **−0.281 / −0.270** |

## Verdict — FAIL the ≤15 % reproduction gate: the RANS OVER-PREDICTS by ~28 %

The antisym-corrected CFD **−0.281** over-predicts the measured **−0.22** by
**+28 %** (LSQ +23 %) — outside the ±15 % gate. **Our twisted-inflow wall-function
RANS does NOT reproduce the measured rolling derivative.** It lands right next to
the *inviscid* lifting line (−0.281 vs LL −0.310), not down at the measurement.

### Viscous-knockdown decomposition — why it fails, and what it means for κ

`C_lp` factors as (inviscid rolling relief) × (viscous / lifting-surface
knockdown). Measuring each against the inviscid LL (−0.310):

| | value/LL_antisym | reading |
|---|---:|---|
| **CFD** (antisym) −0.281 | **0.91** | wall-function RANS knocks LL down only ~9 % |
| **measured** [GF49] −0.220 | **0.71** | the real (viscous+lifting-surface) knockdown is ~29 % |

**The wall-function RANS captures the antisymmetric rolling relief (it sits on the
lifting line) but misses ~two-thirds of the viscous/lifting-surface lift loss that
the measurement shows.** Fully-turbulent SST with y⁺ 15–440 cannot resolve the
lifting-surface decambering / viscous lift knockdown that pulls the real wing from
−0.31 down to −0.22.

## κ implication — this settles the κ tension: **KAPPA_FS stays ≈ 0.73–0.78, not 0.90**

`RERUN-VERDICT.md` (fixed-rig, tapered fin, *same* wall-function method) found the
RANS sitting at **0.97 of the sym-mirror LL** → implied viscous knockdown ~0.97 →
recommended raising `roll.KAPPA_FS` 0.73 → **≈0.90**, but flagged **hedge 2**: *"if
the [GF49]-measured 0.78 is the truer lifting-surface knockdown, κ could sit as low
as 0.73–0.78 … a [GF49]-replication rerun would settle it."*

This is that rerun, and it **confirms hedge 2**:

- κ = rolling_relief (0.93) × viscous_knockdown.
- **RANS-implied** κ (from this bench's 0.91 knockdown) = 0.93 × 0.91 = **0.84**;
  the fixed-rig's 0.97 gave ~0.90. Both are **wall-function artifacts** — the RANS
  under-predicts the viscous lift loss, as the direct GF49 comparison proves.
- **Measurement-implied** κ = 0.93 × 0.71 = **0.66** (my digitized −0.22), or 0.93
  × 0.78 = **0.73** (the audit's literature knockdown). With ±0.02–0.03 digitizing
  scatter on −0.22 the measured band is κ ≈ **0.66–0.78**.

**Recommendation:** do **not** adopt the fixed-rig's κ≈0.90 — it rests on the
RANS's own weak viscous knockdown, which the independent GF49 measurement shows is
~28 % too optimistic. **`roll.KAPPA_FS` should stay in the 0.73–0.78 band** (the
literature/measurement value), with the wall-function fidelity now confirmed as a
real hedge, exactly as `RERUN-VERDICT.md` hedge 2 anticipated. A resolved-wall
(y⁺≈1, level-4) GF49 rerun is the way to pin the true viscous knockdown and close
the ambiguity for good.

### What the bench DID validate

The strip **shape** is sound: the response is linear-in-ω with the correct
(damping) sign and span structure, and the CFD reproduces the *inviscid lifting-
line* rolling derivative (−0.28 vs LL −0.31, within 10 %). The finite-span rolling
relief is captured; only the absolute **viscous** level is over-read by wall
functions — a magnitude caveat, not a shape or mechanism error. Roll damping stays
**report-only**.

## Caveats

1. **Spurious +1.70 N·m baseline** from mesh asymmetry (symmetric wing should read
   0); cancels in the derivative but flags that the level-2 snappy mesh is not
   perfectly y-symmetric. A symmetrized mesh would clean the baseline (not the
   slope).
2. **Sym→antisym factor 0.832** is the tapered-fin LL audit value, not the
   rectangular wing's own; the true-antisymmetric rig (item 2) would replace it.
3. **Wall functions** (y⁺ 15–440, fully-turbulent SST) — the very fidelity limit
   this result exposes; the resolved-wall rerun is the fix.
4. **Mild concavity** on the {0,1,2} sweep; the near-zero secant is the
   ω→0-relevant derivative used for the verdict.

*Refs: [GF49] NACA Rep 968/TN 1835 Goodman & Fisher; [TQ48] NACA TN 1581 Toll &
Queijo eq. 27; USAF DATCOM §7.1.2.2. Context: `out/roll-clp-anchors.md`,
`VERDICT.md`, `AUDIT-ADDENDUM.md`, `RERUN-VERDICT.md`.*
