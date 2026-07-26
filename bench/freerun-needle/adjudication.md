# HIGH-ASPECT NEEDLE — transition-tier CFD adjudication

**Exploit-adjudication #17, nomination #1** (free-run study). The needle fin
rebuilt exactly from `out/freerun-60kg-cruiser-free-b1.json` (full Bézier
offsets + 3 grooves), run on the EPYC box with the **validated transition
machinery** (`bench/bw04-polar-transition`): γ-Reθ (kOmegaSSTLM), level-4
resolved-wall mesh, inlet Tu 1 %, rotated-inlet freestream polar, board =
symmetry plane (k = 2 reflector). Evaluated at the **60 kg cruiser rider speed
5.5 m/s** to put the outer span at its true tip-chord Re (~2–3×10⁵,
transitional). Deliverable numbers in `needle-polar.json` /
`adjudication.json`; curves in `needle-polar.png`.

## The question
The needle's tier-0 reward (release −0.205, the largest single-axis reward in
the study) rests on an extrapolation stack — DATCOM lift slope, induced-drag
collapse `cdi = CL²/(π·0.9·AR_eff)`, `stall_alpha_deg(AR)`, constant section
behavior — evaluated **past the validated fleet envelope** (AR 2.66, depth
176 mm). Does the blade keep its predicted lift slope and low induced drag, or
does tip-Re transition / early LE separation kill the claimed advantage?

## Setup summary
| | |
|---|---|
| Turbulence model | kOmegaSSTLM (γ-Reθ transition) |
| Mesh | level-4 resolved wall, **1,529,071 cells** (well under 8 M cap) — one mesh reused across all angles |
| Inlet Tu | 1 % (tunnel-grade, per validated recipe) |
| Speed | 5.5 m/s → Re_meanchord 345,600; outer-span band ~1.8×10⁵ (90 % span) to ~2.7×10⁵ |
| Angles | 0–16° in 2° steps (9 cases) |
| Cores | 12 (of 16 vCPU), sequential cases |
| **y⁺ on fin** | **min 0.09, mean 10.6, max 85–160** ← see deviation note |
| Convergence | α 0–8° converged on residualControl (p,U ~1e-6); **α 10–16° hit the 2500-iter cap** (residuals plateau 7e-5…9e-4) — unsteady separation steady RANS can't fully converge; forces are tail-averaged means |

### ⚠ Deviation from the validated setup (not chosen — emergent)
The resolved-wall recipe *targets* cell-center y⁺ ≈ 1. The measured fin y⁺ came
out **mean ≈ 10.6, max ≈ 85–160** — the prism-layer stack did not resolve the
viscous sublayer on this thin (t/c 0.076), grooved, high-AR blade (thin
trailing edge / tip / groove medial-axis constraints collapse the layers — the
classic thin-geometry layering problem). Consequence:
- **Integral forces (CL, CD, CM) remain trustworthy** — SST-LM blends to wall
  functions, and the linear-range cases converged cleanly.
- **The γ-Reθ transition-LOCATION readout is NOT reliable** — I do not report
  transition-onset positions. Item (d) is inferred from the force behavior only.

## Numbers (CFD vs tier-0)
DATCOM slope: **3.868/rad (0.0675/°) @ k=2** (fair CFD/symmetry-plane line),
**3.670/rad (0.0640/°) @ k=1.7** (optimizer reward basis). cd0 = 0.0133.
tier-0 break = 12°.

| α° | CL | CD | CM | L/D | CD_CFD / CD_tier0(k2) | conv |
|---|------|-------|--------|------|------|------|
| 0 | 0.184 | 0.0166 | −0.149 | 11.1 | 1.06 | conv |
| 2 | 0.319 | 0.0181 | −0.226 | 17.6 | 0.90 | conv |
| 4 | 0.448 | 0.0239 | −0.299 | **18.8** | 0.90 | conv |
| 6 | 0.577 | 0.0378 | −0.370 | 15.3 | 1.07 | conv |
| 8 | 0.702 | 0.0591 | −0.432 | 11.9 | 1.28 | conv |
| 10 | 0.804 | 0.0853 | −0.468 | 9.4 | 1.52 | capped |
| 12 | 0.897 | 0.1217 | −0.498 | 7.4 | 1.82 | capped |
| 14 | **0.935** | 0.1663 | −0.503 | 5.6 | 2.33 | capped |
| 16 | 0.905 | 0.2085 | −0.502 | 4.3 | 3.08 | capped |

CFD lift slope (fit 0–8°): **3.709/rad (0.0647/°)**, zero-lift −2.9°.

## Verdicts

**(a) Lift slope vs DATCOM — PASS.** CFD 3.709/rad vs DATCOM **−4.1 % (k=2)**,
**+1.1 % (k=1.7)** — far inside the 25 % gate. The DATCOM lift-slope
extrapolation to AR 2.66 is **confirmed**: high-AR really does buy the predicted
slope. `hold` (∝ slope·area·break) is validated on the lift side. The +0.18 CL
offset at α=0 is the flat-inside foil camber (consistent with the validated
bw04 transition case's +0.22), not an anomaly.

**(b) Drag polar vs cd0+cdi — PARTIAL (real at cruise, fails under load).**
- **Attached range (α ≤ 6°, CL ≤ 0.58): the induced-drag collapse is REAL** —
  the drag polar tracks tier-0 within ±10 % (ratios 0.90–1.07), and the scored
  drive/speed working points (CL ≈ 0.41 / trim) actually **beat** tier-0 (peak
  L/D 18.8 at CL 0.45 vs tier-0 ~16.8). The least-controversial claim in the
  dossier — high-AR lowers induced drag — holds at cruise.
- **Above CL ≈ 0.7 (α ≥ 8°): CFD drag diverges hard** — 1.3× at 8°, 1.8× at
  12°, up to ~3× near the break. The constant-efficiency quadratic `cdi` has no
  separation/stall-drag term, so it badly underpredicts drag as the section
  loads up.
- **Profile cd0 is +24 %** (0.0166 vs 0.0133): the section does **not** hold its
  Re-700k (SK81/Zarruk) polar at the needle's 2–3×10⁵ outer-span Re — exactly
  the "no tip-Re correction" gap the dossier flagged.

**(c) Break vs stall_alpha_deg — PASS (tier-0 was conservative).** CL_max at
**14°**, 2° **later** than the 12° prediction. The feared early tip-Re break did
**not** happen — the needle keeps (slightly exceeds) its forgiveness margin.
*Caveat:* α ≥ 10° cases are capped/un-converged at y⁺ ~10, so per the URANS-study
convention the post-knee magnitude is a **lower bound**, not a resolved value.

**(d) Separation / transition anomaly — no early collapse; location not
resolvable.** With y⁺ ~10 the transition-onset location is untrustworthy, so no
positions are reported. The **forces** show a drag-rise onset at α ≈ 7–8° (CD
peels off the quadratic) and a **gentle** CL_max with a soft post-peak
(0.935 → 0.905 over 14 → 16°) — signatures of **progressive trailing-edge /
outer-span separation**, not an abrupt LE stall. The feared tip-Re LE-separation
collapse was **not** seen in this steady-RANS bench.

**(e) BOTTOM LINE — the needle's advantage PARTIALLY SURVIVES.**
- **Survives:** the lift slope (DATCOM, gate pass), the induced-drag collapse
  **at cruise**, and the break angle (14 > 12). These are the load-bearing,
  least-controversial claims. A deep high-AR blade genuinely delivers the
  predicted lift and cruise efficiency — the needle is **not** a pure model
  artifact.
- **Erodes:** `speed`/`drive` **magnitude under hard load** (CL > 0.7). CFD drag
  runs 1.3–3× tier-0 and L/D collapses 12 → 5 from α 8 → 14°. The hard-turn
  efficiency the raw numbers promise is optimistic.
- **The wrong tier-0 line item is the DRAG decomposition** — the profile cd0
  (no tip-Re correction) and the constant-efficiency `cdi = CL²/(π·0.9·AR_eff)`
  quadratic past CL ≈ 0.7 (no stall-drag term). **Not** the DATCOM slope,
  **not** `stall_alpha_deg`.
- **Release specifically:** the tier-0 release axis is a **geometric proxy**
  (sweep + elliptic deviation) that CFD cannot falsify directly. Its intended
  physics replacement — the post-peak lift gradient — is **gentle** here, which
  *directionally supports* a high release rather than killing it. Low confidence
  (near-stall regime, capped convergence, y⁺ ~10); URANS is needed to close it.
- **⚠ Ventilation / surface-piercing is NOT adjudicable with this bench.** A
  176 mm deep, narrow, high-AR blade near the free surface is the canonical
  ventilation geometry, and this deep-submergence single-phase tier cannot see
  it. Ventilation could dump the very lift the whole reward assumes — it is the
  single largest un-tested risk and the needle can ship only with this flag.

## Routing
The needle is not falsified but is **conditionally cleared**: the high-AR
premise is real, tier-0's drag model is the piece to fix (add a transitional-Re
cd0 correction and a stall-drag term above CL ~0.7), and the go/no-go now hinges
on the **parked multiphase ventilation tier**, not this one.
