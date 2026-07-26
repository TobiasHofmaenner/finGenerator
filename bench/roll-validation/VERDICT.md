# Roll-damping (L_p) CFD validation — VERDICT

**Task #19 final step.** Twisted-inflow RANS cross-check of the tier-0 strip roll-damping
model (`src/fingen/roll.py`, docs/PHYSICS.md §5c). Solved **locally** (20-core Kali box,
12-rank decomposition), OpenFOAM v2512, frozen level-2 polar recipe.

## Setup

| | |
|---|---|
| Subject fin | `FinParams(foil=FLAT_INSIDE)` — default outline (depth 115, base 110, sweep 33°), t/c 9%; AR_geom 1.738 |
| Speed | 6.4 m/s (the tier-0 operating point) |
| ω sweep | 0, 1, 2, 3 rad/s (baseline + 3 — the writer's default (0,2,4) is only two non-zero points) |
| Mesh | level 2, **360 134 cells**, one mesh reused across all ω (bw04_polar pattern); y⁺ on fin 15–441 (avg 82, in-band) |
| Solver | simpleFoam, k-ω SST, wall functions; end_time 800; ran to the cap but M_x plateaus (tail std ~3e-4 N·m, 0.02%) |
| Roll axis | rollMoment FO CofR = **(0,0,0)** = board plane = tier-0 **z0 = 0**. **Axes match exactly.** |
| Inlet BC | **Documented deviation:** `exprFixedValue` uy(z)=ω·pos().z() instead of the writer's `codedFixedValue`. Physics identical (same uy(z)=ω·z field). Forced because this OpenFOAM install is **runtime-only (no wmake)** — the coded BC cannot compile its shared lib (and the root dynamicCode security check blocks it regardless). `exprFixedValue` is runtime-parsed (libfiniteVolume), needs neither. |

## Numbers

| ω [rad/s] | M_x (converged tail) [N·m] | iters | secant slope [N·m·s] |
|---:|---:|---:|---:|
| 0 | −1.58382 | 800 | — |
| 1 | −1.70072 | 800 | −0.1169 |
| 2 | −1.78747 | 800 | −0.0868 |
| 3 | −1.86227 | 800 | −0.0748 |

- **Baseline M_x(0) = −1.584 N·m** — the cambered flat-side foil's side-force roll moment at zero
  twist (CL0 ≈ 0.22, [BW04]); the slope fit removes it. LSQ **intercept −1.595** sits 0.7% below
  the baseline point (the concavity pulls the line down), i.e. baseline and intercept agree.
- **CFD slope dM_x/dω:** LSQ over all four points **−0.0922 N·m·s** (R² 0.989); near-zero secant
  (0→1, the L_p-relevant derivative at p→0) **−0.1169 N·m·s**.
- **Tier-0:** **L_p = −0.2383 N·m·s** (C_lp,fin −0.723, DATCOM lift slope 3.31/rad).

## Verdict (per item 5)

**1. Percent error of CFD slope vs tier-0 L_p.**
CFD is **39% of tier-0 (LSQ, −61%)** / **49% of tier-0 (near-zero secant, −51%)**. The strip
model **over-predicts roll damping by ~2×**. This is **not** an error to explain away — it is the
**known finite-span rolling-load deficit that strip theory omits**, anchored to Goodman & Fisher's
*rolling-flow* measurements ([GF49], NACA Rep 968 / TN 1835 — a rotated airstream about a fixed
wing, physically the same experiment as this twisted inflow): measured C_lp ≈ ½ of strip theory
across this fin's reflected-AR band (fin AR_geom 1.74 → reflected AR_full 3.48). The literature
deficit ratio (measured/strip ≈ 0.45–0.55, roughly taper-independent) predicts CFD ≈ 0.5·L_p =
**−0.119 N·m·s**; the near-zero secant **−0.117 matches this to 2%**. Two independent theories give
the same neighborhood — Toll & Queijo lifting-line (C_lp = −(a₀/8)·A/(A+4), [TQ48]) and DATCOM
§7.1.2.2 Weissinger lifting-surface. **Triangulated, not lucky.**

**2. Is the response linear?**
R² = 0.989 — linear to first order, but with a **systematic sub-linear (concave)** signature: the
secant softens 0→1: −0.117, 1→2: −0.087, 2→3: −0.075 (residual sign pattern +,−,−,+). Because L_p
is the derivative **at p→0**, the **near-zero secant (−0.117) is the L_p-relevant number**; the LSQ
slope (−0.092) is pulled shallow by the concavity and is a lower bound. The curvature is **not** the
marine quadratic (crossflow-drag) term — that *adds* damping and would make M_x(ω) *convex*; we see
the opposite sign, and the tip crossflow angle is only **1.0°/2.0°/3.0°** at ω=1/2/3 (far below the
~12–14° [BW04] stall break), so bluff-body drag is negligible. The softening is a **lifting-surface
loading-redistribution effect** — the rolling span-load builds and the induced tip relief grows with
ω — i.e. the *same* finite-span physics as the 50% level, not a new mechanism.

**3. Which tier-0 assumption dominates the discrepancy.**
The **DATCOM 3D lift slope applied uniformly inside the strip integral** (roll.py's own flagged
tier-0 choice). The strip integral weights each station by the arm **squared** (z²), so it leans on
the outer/tip strips — exactly where the real rolling load is **relieved** by the trailing-vortex
downwash of the antisymmetric loading. The single AR-averaged 3D slope cannot represent that
rolling-specific, spanwise-varying induced angle, so the tip strips are over-counted and L_p is ~2×
high. Tip relief **is** this effect; root gap (the 2 mm STL sink → CFD wets z 0..0.113 vs tier-0
0..0.115) and wall-function decambering are minor same-sign contributors (each ≲ few %). Note the
symmetry plane *reduces* tip relief at the root end, so the residual gap is genuinely the tip.

**4. Context / error bar for the spider axis.**
Tier-0 roll damping is **report-only** today (docs/PHYSICS.md §5c), a handling/depth-pricing metric.
This validation says: the strip law's **shape is right** — its span/chord scaling (damping ∝ S·s²,
the depth-pricing physics) and thus its **ranking of blades by depth is unaffected**; only the
**absolute level is ~2× high**, and consistently so (a **bias, not scatter**). When it graduates to a
priced spider axis:
- Apply a **finite-span correction** — a factor ≈ **0.5** on the reflected AR (or the AR-dependent
  DATCOM 7.1.2.2 / AVL / A/(A+4) form), **not an empirical fudge**. A single AR-mapped factor
  collapses the bias.
- After correction, attach **≈ ±15–20%**: the residual carries the concavity (which number you call
  "the" derivative), the taper-independence assumption in the ratio mapping, and this bench's own
  CFD caveats below. For **ranking only**, no correction and no error bar are needed.

### CFD-setup caveats (all push the same way — CFD ratios are slight *lower* bounds)
- **Imposed-shear attenuation.** Sampling uy(z)/(ω·z) on the ω=3 field: at the freestream station
  (x = −0.30 m) the upper-span (moment-dominant) shear is preserved to **~0.87** of nominal, falling
  to ~0.75 approaching the fin — because the `freestreamVelocity` top/side boundaries relax uy toward
  0 (they don't sustain a linear shear), plus the fin's own bound-vortex sidewash near the LE. Net:
  the fin sees ~10–15% less than the nominal ω·z, so the CFD slope is **biased low by ~10–15%** —
  correcting *toward* tier-0 moves CFD from 49% up toward ~56%, deeper into the [GF49] band. A cleaner
  tier-1 rig would impose the shear on **all** inflow boundaries or use a rotating frame.
- **Convergence.** All cases ran to the 800-iter cap (residualControl not tripped simultaneously,
  final p-residual ~3–7e-5); M_x plateaus (tail std 0.02%), so the tail mean is converged.
- **y⁺** 15–441 (avg 82): mostly in the wall-function band (bench L2 regime), a few tip/root faces
  above — acceptable for this lift-based moment, per the frozen recipe.

## Bottom line

**Tier-0 roll composition VALIDATED; absolute magnitude carries the textbook ~2× strip-theory
finite-span deficit.** The CFD roll moment is linear-in-ω to first order (R² 0.989, mildly concave),
its baseline camber offset is recovered, its damping derivative is **negative (damping)** with the
right span structure, and the L_p-relevant near-zero derivative (−0.117 N·m·s) matches the
finite-span-corrected expectation (½·tier-0 = −0.119) to **2%**. The 2× gap is the omitted
rolling-load relief — reproduced by the [GF49] rolling-flow measurements and two lifting-surface
theories — a **model-fidelity** result, not a mesh/solver/BC artifact. Recommended path to tier-1
accuracy: fold an AR-mapped finite-span factor (or read C_lp off DATCOM 7.1.2.2 / AVL) into roll.py;
until then, keep it report-only and quote the strip level as a ~2× upper bound.

*Refs: [GF49] NACA Rep 968/TN 1835 Goodman & Fisher; [TQ48] NACA TN 1581 Toll & Queijo eq. 27;
USAF DATCOM §7.1.2.2. Full literature anchoring: `out/roll-clp-anchors.md`. Data: `cases-summary.json`,
`roll-clp.json`; plot: `roll-clp.png`.*
