# Thin-foil low-Re section polar — the free-run exploit, HYDRO half (task #17)

**Date:** 2026-07-27. Extruded-section polar of the **thin-foil free-run winner's
actual section** (`out/freerun-95kg-pro-free-b2.json`: flat-inside, **t/c 0.0446**,
sharp LE) at its **mean-chord Re** and the 95 kg pro speed, to answer the dossier's
open CFD question (`out/freerun-dossiers.md` "THIN FOIL"): does a 0.045-class
sharp-LE section **keep its 2π slope and Hoerner cd0** at fin Re (2-7×10⁵), or
**separate early / carry a drag penalty tier-0 misses**?

Data: `section-polar.json`, `section-polar-cases.json`; plot: `section-polar.png`.
Writer: `scripts/thinfoil_section.py` — the validated SK81-style quasi-2D
extruded-section slab (`scripts/sk81_naca0012.py`), run on a **resolved wall**
(cell-center y⁺≈1, 16 prism layers) with **two turbulence tiers on one shared
mesh**: γ-Reθ transition (kOmegaSSTLM, Tu 1 % — the validated transition tier,
`bench/bw04-polar-transition`) as primary, and fully-turbulent (kOmegaSST, Tu 5 %
— the SK81 tier convention) as the pessimistic drag bracket.

## Setup

| | |
|---|---|
| Section | flat-inside, **t/c 0.0446**, camber 0, 0.7 mm blunt TE (the winner's section) |
| Chord / speed | mean chord **77.3 mm**, U **8.5 m/s** (95 kg pro) → **Re 6.25×10⁵** (mid fin band) |
| Mesh | quasi-2D slab, **425 027 cells**, resolved wall y⁺ 0.03-0.9 (avg ~2.5), 16 layers, one mesh copied across angles |
| Angles | 0-10° / 2° (winner works at **α 7.1°** — inside the sweep) |
| Solver | simpleFoam, end_time 2000; transition + fully-turbulent tiers |
| tier-0 refs | SECTION_SLOPE **2π = 6.283/rad**; Hoerner cd0 = 2·cf·(1+2t+60t⁴) = **0.01118** (cf 0.074/Re^0.2 = 0.00513) |

## The polar (CL, CD per angle)

| α° | CL (lm) | CD (lm) | CL (ft) | CD (ft) |
|---:|---:|---:|---:|---:|
| 0 | 0.177 | 0.0139 | 0.170 | 0.0171 |
| 2 | 0.371 | **0.0123** | 0.372 | 0.0172 |
| 4 | 0.568 | 0.0171 | 0.572 | 0.0215 |
| 6 | 0.761 | 0.0262 | 0.766 | 0.0295 |
| 8 | 0.914 | 0.0473 | **0.929** | 0.0499 |
| 10 | 0.916 | **0.1188** | 0.861 | 0.1147 |

(lm = γ-Reθ transition, ft = fully-turbulent. Drag bucket floor at α≈2°.)

## Slope / cd0 / knee vs tier-0

| metric | tier-0 | transition (γ-Reθ) | fully-turbulent |
|---|---:|---:|---:|
| lift slope (0-6°) | 2π = 6.283 | **5.581/rad (−11.2 %)** | 5.698/rad (−9.3 %) |
| zero-lift cd0 (CD-CL² intercept) | 0.01118 | **0.01240 (×1.11)** | 0.01601 (×1.43) |
| cd0 at α=0 (incl. CL0 lift-drag) | 0.01118 | 0.01392 (×1.25) | 0.01710 (×1.53) |
| stall knee / CL_max | (slope-only) | ~8-10°, **0.916** | ~8°, 0.929 |

## Verdict — the thin-foil HYDRO claim SURVIVES (with a thin forgiveness margin)

**1. 2π-class slope — KEPT.** The transition section holds **5.58/rad, −11 %**
below 2π; fully-turbulent −9 %. Both are *inside* the SK81 wall-function
decambering band (the validated 12 % NACA 0012 read −18.7 % there) — the thinner
0.045 section is actually **better**, not worse. The dossier's fear that a sharp
thin LE loses its slope does **not** materialize.

**2. Hoerner cd0 — KEPT (fair tier +11 %).** The *fair* zero-lift profile drag
(the transition drag-bucket intercept) is **0.0124, only +11 %** over the tier-0
Hoerner cd0. Hoerner is a good estimate; the section really is low-drag. The
fully-turbulent tier overshoots to **+43 %** — the pessimistic bracket (see task
#22 below), *worse* than the needle's +24 % for the thicker section, because a
sharp thin LE forced fully-turbulent carries relatively more pressure drag.

**3. Early separation — MILD, not catastrophic.** The section stays attached and
near-linear through 6°; the stall knee is **~8-10°** (transition CL plateaus 8→10
while CD explodes 0.047→0.119; fully-turbulent CL_max at 8°). That is a few degrees
earlier than a thick section's 12-14° break — the sharp-LE early-separation the
dossier flagged is **real but mild**. Crucially, the winner's **α_work 7.1° sits
just below the knee** (attached, CL≈0.83, CD≈0.035): the section delivers its lift
at the working point. The cost is a **thin forgiveness margin** (~1-3° to stall) —
a `forgiveness`-axis concern, not a `speed`/`drive`/`hold` one.

**Bottom line:** the thin-foil exploit's **hydrodynamic** rewards — low cd0 (drives
`speed`/`drive`) and full 2π-slope side force (drives `hold`) — are **CFD-real at
fin Re**. The section does not lose its polar. What it loses is a couple of degrees
of stall margin, exactly where the dossier said the physics-gate story lives. As
the dossier's adjudication path stated, the exploit's fate now rests entirely on
the **structural** half (static/impact/fatigue at t/c 0.045) — the user's structure
rig, which CFD cannot arbitrate. **HYDRO: survives. Go/no-go: structure bench.**

## Implication for task #22 (Re-aware cd0 term)

This run + the needle run (`bench/freerun-needle`, commit 2454f01) give two
transition-tier CFD points across the fin band:

| run | Re | t/c | tier-0 Hoerner cd0 | CFD zero-lift cd0 | CFD cd0 @α=0 |
|---|---:|---:|---:|---:|---:|
| needle (3-D fin) | 3.46×10⁵ | 0.076 | 0.01334 | — (not extracted) | 0.01659 (**×1.24**) |
| thin section (2-D) | 6.25×10⁵ | 0.045 | 0.01118 | 0.01240 (**×1.11**) | 0.01392 (×1.25) |

**Three things this pins for task #22:**

1. **The "+24 % cd0" is mostly the α=0 lift-drag, NOT a profile-drag Re penalty.**
   Both runs read **~+24-25 % at α=0**, but that compares CD(α=0) — which for these
   cambered/flat-inside sections carries the CL0≈0.17 lift-drag — against the
   *zero-lift* Hoerner term. The *fair* like-for-like (the CD-CL² drag-bucket
   intercept) is only **+11 %**. Task #22 must compare zero-lift-to-zero-lift, or it
   will over-correct cd0 by ~2×. The profile floor at fin Re is only **~10 %** above
   the current Hoerner formula — a modest nudge, not a rewrite.

2. **Do NOT base the Re-aware cf on fully-turbulent flow.** The fully-turbulent cf
   over-predicts profile drag by **+30-43 %** at these Re; fin-Re flow is
   transitional (laminar running verified — the transition tier drops cd0 ~29 %
   below fully-turbulent here, 0.0124 vs 0.0160). The existing `cf = 0.074/Re^0.2`
   (a mild fully-turbulent-flat-plate value) already lands only ~10 % below the
   transitional truth, so it is closer to right than a "proper" turbulent cf would
   be. Effective cf (zero-lift cd0 / 2·form): transition **0.00569** vs tier-0
   0.00513 at Re 6.25×10⁵.

3. **The Re-trend over 2-7×10⁵ is mild; the real tier-0 drag miss is the STALL-DRAG
   term, not cd0.** The @α0 ratio is nearly flat (needle ×1.24 @ 3.5e5, thin ×1.25 @
   6.3e5) — the excess is section-shape/lift-drag driven, not a steep Re slope, so a
   Re-aware cd0 correction beyond a ~+10 % floor bump buys little. Both runs instead
   show the dominant tier-0 failure is **above CL≈0.7-0.9**, where CD diverges
   1.8-4.5× the `cdi = CL²/(π·e·AR)` quadratic (thin: 0.026→0.047→0.119 over 6→8→10°;
   needle: 1.3-3×). **Task #22's leverage is a stall/separation drag term above
   CL≈0.7, with only a ~10 % zero-lift cd0 floor bump — not an aggressive Re-aware
   cf.**

## Caveats

- Fair-cd0 (drag-bucket intercept) fit over α ≤ 4° (3 points); α=10° is deep stall
  (y⁺ spikes to 234 transition / 110 fully-turbulent) — a lower bound on post-knee
  drag per the URANS-study convention, not a resolved value.
- The needle point is a 3-D fin CD@α=0 (profile + induced-at-CL0), so it only
  supports the @α0 column; its fair zero-lift cd0 was not extracted.
- Quasi-2-D section (both z-faces symmetryPlane): a pure section polar, no 3-D
  induced drag — the section's own profile+pressure drag, correct for the cd0/slope
  question.

*Refs: `out/freerun-dossiers.md` (THIN FOIL); `out/freerun-95kg-pro-free-b2.json`;
`bench/freerun-needle/adjudication.md` (needle drag decomposition, commit 2454f01);
`docs/CFD-BENCH.md` items 3-4 (SK81/Zarruk section tier), transition tier.*
