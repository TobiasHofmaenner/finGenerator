# Falk surf-fin CFD papers — validation reference for the multi-fin CFD tier

Extracted for the multi-fin CFD validation tier. Every quantitative claim carries a cite:
`(p.X)` = stated in text on that page; `(Fig.N)` / `(Table N)` = from a figure/table.
Numbers read off plots are explicitly labelled **[digitized]** with an uncertainty.

**Access status**
- **[Falk20]** Falk et al. (2020), *Numerical Investigation of the Hydrodynamics of Changing Fin
  Positions within a 4-Fin Surfboard Configuration*, Appl. Sci. 10(3):816, doi:10.3390/app10030816.
  **MDPI OPEN ACCESS — full text obtained** (`falk20.pdf`, 23 pp). Note: mdpi.com is Akamai-blocked
  from this host; the PDF was pulled from the CDN mirror `res.mdpi.com/d_attachment/applsci/applsci-10-00816/article_deploy/applsci-10-00816.pdf`.
- **[Falk19]** Falk, Kniesburges, Janka, Grosso, Becker, Semmler, Döllinger (2019), *Computational
  hydrodynamics of a typical 3-fin surfboard setup*, J. Fluids Struct. 90:297–314,
  doi:10.1016/j.jfluidstructs.2019.07.006. **CLOSED ACCESS — full text NOT obtainable.**
  Unpaywall: `is_oa=false`, `oa_status="closed"`, zero OA locations; confirmed also via Semantic
  Scholar (`isOpenAccess=false`), CORE (0 hits), OpenAIRE (`CLOSED`), BASE (0), FAU open.fau.de (0).
  What we have for Falk19: (a) the **abstract** (qualitative only); (b) its **total 3-fin CL/CD
  curve**, which Falk20 re-plots in its Fig 17 (digitized here); (c) Falk20's textual description of
  the Falk19 method. **Falk19's per-fin numbers are a GAP** — see end.

---

## ★ Validation targets for the tier-0 interference model (summary) ★

The usable per-fin interference data all come from **Falk20 Figure 10** (commercial 4-fin config
T:80/A:150, FCS Accelerator II fins). Coefficients are ~velocity-independent (Falk20 Sec 3.2, 4.3),
so a single coefficient curve serves all four speeds. **These are DIGITIZED from Fig 10 plots
(±0.02–0.03); the paper does not tabulate them.**

**Fin labels:** IF = inside fin (wave-crest side, the "working"/loaded fin); OF = outside fin
(shore side, "passive"). front_* = front pair, rear_* = rear pair. In interference terms the IF pair
is the loaded (windward-ish) side and the OF pair is the lightly-loaded side whose rear fin sits
squarely in the front fin's wake.

### (i) Front-vs-rear asymmetry — at the lift peak AoA = 20° (Fig 10a)
| fin | CL @20° | vs its front counterpart |
|---|---|---|
| front_IF | **1.05** | (reference, most loaded fin) |
| rear_IF  | **0.81** | rear IF = **77%** of front IF → **−23% rear deficit** |
| front_OF | **0.45** | (already post-stall; OF stalls at 15°, p.12) |
| rear_OF  | **0.47** | ≈ front_OF at 20° (rear OF not yet deep in wake) |

So at peak lift the loaded (inside) rear fin carries ~23% less lift than the loaded front fin,
purely from operating in its downwash. The mean of all four = **0.695** (stated max mean CL 0.69, p.18).

### (ii) Rear-fin deficit vs its own front fin — the OF-pair wake shadow (Fig 10a,b)
The clearest interference signal. The **rear OF sits fully in the wake of the front OF** for
AoA≈25–35° (p.12), which collapses its load:
| AoA | front_OF CL | rear_OF CL | rear/front | front_OF CD | rear_OF CD |
|---|---|---|---|---|---|
| 25° | 0.415 | 0.255 | 61% | 0.255 | 0.108 |
| **30°** | **0.465** | **0.075** | **16% (−84%)** | **0.335** | **0.035 (~−90%, "nearly zero", p.12)** |
| 35° | 0.47 | 0.115 | 24% | 0.40 | 0.07 |
| 45° | 0.595 | 0.615 | ~100% (rear OF has moved OUT of wake, p.12) |

The IF-pair rear deficit is much milder (front flow not interrupted, p.12): e.g. at 30°,
front_IF 0.755 vs rear_IF 0.70 (rear = 93%).

**What the CFD must reproduce:**
1. Rear inside fin ≈ 0.77–0.93 × front inside fin lift (deficit grows toward the stall peak).
2. Rear outside fin lift collapses to ~15–25% of the front outside fin over AoA 25–35° (deep-wake
   shadow), and its drag to ~10% ("nearly zero"), then recovers to ~parity by 45° as it exits the wake.
3. Front OF stalls earlier (15°) than the other three fins (20°) (p.12).
4. Whole-set mean: max CL 0.69 @20°, max CD 0.61 @45°, max L/D 7.44 @5° (all stated, p.18–19).

### Matched operating point to run
- **Geometry:** FCS Accelerator II fins — depth 116 mm, base 111 mm, single-fin planform area
  9860 mm², cant 8.5°, toe-in 3.5°, asymmetric foil (flat inner / cambered outer) on the two rail
  (side) fins; symmetric foil on the centre fin (3-fin case). Commercial 4-fin layout **T:80/A:150**:
  front-fin transverse spacing 330 mm (±165 mm from centreline), rear-fin transverse spacing 170 mm
  (±85 mm), rear fins 150 mm axially downstream of front fins. Board reference = ROBERTS Surfboards
  "The Dreamcatcher 6′8″". No board surface in the model — flat bottom wall stands in for the board.
- **Fluid:** water, ρ = 997 kg/m³, ν = 0.8926×10⁻⁶ m²/s (⇒ μ ≈ 8.90×10⁻⁴ Pa·s), incompressible (Ma<0.012).
- **Reference for coefficients:** A_ref = single-fin planform area 9.86×10⁻³ m²; ρ = 997; velocity = u_in.
- **Speeds:** 5, 7.5, 10, 18 m/s (coefficients ≈ identical across all four). Suggest **10 m/s** as the
  primary match (mid-range, realistic surfing speed; Re≈1.2×10⁶ on base chord — see note).
- **Angles:** 0, 5, 10, 15, 20, 25, 30, 35, 40, 45° (5° steps). RANS for 0–15°, URANS for ≥20°.

---

## PAPER 1 — [Falk20] Falk et al. 2020, 4-fin (Appl. Sci. 10:816) — PRIMARY SOURCE

### A. Fin geometry / template
- Fins: **FCS Accelerator II** (FCS, Newport Beach, NSW/Australia), CT-scanned (Siemens SOMATOM
  Definition AS 64), surface reconstructed via Marching Cubes (p.6).
- **Depth 116 mm, base length 111 mm, planform area 9860 mm²** per fin (p.7, Fig 6a).
- **Cant ≈ 8.5°, Toe-In ≈ 3.5°** (p.7, Fig 5a). ✔ Confirms the ~3.5°/~8.5° in our notes.
- Section: rail fins **asymmetric — flat inside surface, curved (cambered) outside surface**; centre
  fin symmetric (p.7, Fig 5a,b). Thickness not stated numerically.
- Layout (commercial "T:80/A:150", p.7–8, Fig 6a): front-fin transverse spacing **330 mm**, rear-fin
  transverse spacing **170 mm**, rear-to-front axial distance **150 mm**. Rotation axis for AoA is at
  the mid-point between the front-fin leading edges (Fig 6b).
- Board: fins arranged as on **ROBERTS Surfboards "The Dreamcatcher 6′8″"** (p.6). CT scan was done on
  a 3-fin NSP board (Fig 4a); only the fins (no board) are simulated.
- 10 additional rear-fin positions studied: transverse T:0–120 mm, axial A:0–200 mm (p.8, Fig 7).
- No sweep/rake value given numerically (only the planform in Fig 6a).

### B. Flow conditions
- **Inflow speeds: 5, 7.5, 10, 18 m/s** (p.3, p.9, p.11) — representing wave heights 0.9/2.8/6.0/25.6 m (Fig 1).
- Water: **ρ = 997 kg/m³, ν = 0.8926×10⁻⁶ m²/s** (p.9). Ma = 0.003–0.012 (incompressible) (p.9).
- **Reynolds number: NOT stated in the paper.** [computed estimate] Re = u·base/ν with base=0.111 m:
  ≈ 6.2×10⁵ (5 m/s), 9.3×10⁵ (7.5), 1.24×10⁶ (10), 2.24×10⁶ (18). Labelled as our estimate.
- Reference area for coefficients = single-fin planform area 9860 mm² (Eq. 5–6, p.11); no chord-based
  reference length is used (area-based 3-D coefficient).
- **AoA sweep: 0°→45° in 5° steps** (p.9, "0° < AoA < 45° in 5° steps"). Plots also show extra markers
  at ~2.5° and 7.5° in the low-AoA linear region. Positive AoA = clockwise fin rotation = left-hand
  bottom-turn (p.9). General surfing range −45°…45° (p.5).

### C. Numerical method
- Solver: **STAR-CCM+** (Siemens PLM, Plano TX), cell-centre finite-volume, incompressible N–S (p.10–11).
- Turbulence: **SST k-ω** (two-equation eddy-viscosity), **RANS for AoA 0–15°, URANS for AoA ≥20°**
  (p.10–11). High-y+ wall treatment (log-law), y+ target 60, range 30–90 (p.11).
- Mesh: **unstructured polyhedral**, wake refinement downstream of fins, **10 prism layers** (2–8 mm
  total, set by speed) (p.9–10). Grid-independence over 6 meshes; **chosen mesh M4 ≈ 1.2 million cells**
  (M5/M6 differ 0.3–0.4% in CD) (p.9–10, Fig 9b). (Report says 2.0–2.2M "around the fins" for the
  finest — the production mesh is 1.2M.)
- Time stepping (URANS): 2nd-order implicit, time step set per-AoA to CFL = 1.0±0.5 at fin surfaces (p.11).
- Domain / BCs (p.9, Fig 8): rectangular box; front fins **3×base from inlet**, outlet **3×base
  downstream** at p = 0 Pa; inlet velocity = u_in; **fin surfaces + bottom wall = no-slip walls**
  (bottom wall stands in for the board); **two sidewalls + top = symmetry planes**.
- Compute: Emmy & Lima clusters, RRZE (p.11).

### D. Per-fin & total force results — THE VALIDATION TARGETS
**Definitions (p.5, p.11):** lift F_L ⟂ flow, drag F_D ∥ flow; +lift = board turns toward shore,
−lift = turns into wave pocket; +drag along flow. Coefficient c = F/(0.5·ρ·A_ref·u²), A_ref = single-fin
planform area (Eq. 5–6). Mean coefficient of the set = Σ(4 fin forces)/Σ(4 fin areas) = simple average
(equal areas). "Windward"/"leeward" is not the paper's language — it uses IF (inside/working) vs OF
(outside/passive); see label note above.

**Per-fin CL & CD vs AoA (Fig 10a,b, p.12)** — the core dataset. Fully digitized in
`falk20_perfin_forces.csv`. **[digitized ±0.02–0.03]**. Key stated trends (p.12):
- Both IF peak at AoA 20°, then stall; front IF lift > rear IF lift throughout ("non-interrupted flow
  at front fins").
- Front OF stalls early at **15°** (flat suction side forces LE separation); rear OF stalls at 20°.
- Rear OF lift/drag collapse in the front-OF wake over 25–35°, drag "reduced to nearly zero", then
  both recover to a max at 45° when it moves out of the wake.
- (See the summary tables at the top for the extracted asymmetry / deficit numbers.)

**Total-set coefficients & forces** (`falk20_total_forces.csv`):
- Mean CL vs AoA and mean CD vs AoA: Fig 12a / 13a (four speeds overlap) and Fig 10 red curve.
  Stated: **max mean CL = 0.69 @ 20°** (p.18); **max mean CD = 0.61 @ 45°** (p.18); **max L/D = 7.44
  @ 5°** (p.19).
- **Total lift force** (sum of 4 fins) vs AoA per speed, Fig 12b **[digitized]**: 18 m/s peaks
  ~4450 N @20° (dips to ~2950 N @35°, back to ~3800 N @45°); 10 m/s ~1370 N @20°; 7.5 m/s ~770 N;
  5 m/s ~340 N. (Cross-check: CL 0.69·0.5·997·9.86e-3·18²·4 = 4396 N ✓.)
- **Total drag force** vs AoA per speed, Fig 13b **[digitized]**: 18 m/s ~1350 N @20° → ~3850 N @45°;
  10 m/s ~1200 N @45°; 7.5 ~680 N; 5 ~300 N.
- Rear-fin position study (Fig 14–16, Sec 3.3/4.4): max mean CL falls from **0.87 (T:0) → ~0.70
  (T:50–120)** (p.14, p.19); axial shift barely changes max CL (**0.72 A:0 → 0.69 A:50–200**, p.20);
  stall point moves 30°(T:0)→20°(T:120); max L/D rises ~9.5% shifting rear fins transversely inboard,
  only ~2.8% axially (p.16). These are for the 10 alternative layouts, not the commercial one.

### E. 3-fin vs 4-fin comparison (Fig 17–18) — bridge to Falk19
Falk20 re-plots the **Falk19 total 3-fin** CL/CD as its "FCS Accel. 3-fin" curve (digitized in
`falk19_3fin_total_forces.csv`, **[digitized ±0.03]**):
- 3-fin total **max CL ≈ 0.74 @ 20°** (Fig 17a); text: 3-fin vs 4-fin max CL differ 6.8% (p.18) →
  0.69·1.068 = 0.737 ✓.
- 3-fin total **max CD ≈ 0.50 @ 40–45°** (Fig 17b); max CD difference 3-fin vs 4-fin = 23% @35° (p.18).
- 3-fin total **max L/D ≈ 7.55 @ 6.25°** (Fig 18 annotation).
- Also plotted (dashed) for context: Gudimetla et al. [13] FCS k2.1 3-fin & 4-fin (different fins;
  k2.1 4-fin max CL differs 27.3% from Accelerator, stall at 35° vs 20°) (p.18) — NOT our template.

---

## PAPER 2 — [Falk19] Falk et al. 2019, 3-fin (J. Fluids Struct. 90:297) — ABSTRACT + reflected data only

**Full text could not be obtained (closed access).** Everything below is from the abstract, the
Falk20 description of ref [11], and the total 3-fin curve reflected in Falk20 Fig 17.

### A–C. Setup (from Falk20's account of [11] and the Falk19 abstract)
- Same commercial 3-fin ("Thruster") position of THE DREAMCATCHER, **same FCS Accelerator fins**, same
  authors/method family (Falk20 p.17). So geometry A above (depth 116 / base 111 / area 9860 mm²,
  cant 8.5°, toe 3.5°, asymmetric rail fins + symmetric centre fin) carries over to the 3-fin case.
- Rectangular domain, no board — same modelling strategy (Falk20 p.9 cites [13,41] and [11]).
- **RANS + URANS, SST k-ω**; RANS good for 0–15°, URANS needed ≥20° (Falk20 p.10–11, attributing to [11]).
- **AoA 0°→45°** (abstract; Falk20 p.2).
- Abstract (verbatim fragments recovered via search): reports "lift and drag coefficient **for each
  fin** and the entire configuration and lift-to-drag ratio for the entire fin configuration";
  "unsteady effects as flow separation combined with vortex shedding occur at high angles of attack
  above 20° … high negative influences on stability"; "**vortices shed from an outside fin might
  excite the centre fin to vibrations**". (Abstract text only — no numbers.)
- Falk20 (p.11) states: "a validation of the 3-fin configuration against experimental data was shown
  in [11]." → Falk19 contains an **experimental validation** (this is the likely home of any isolated/
  single-fin baseline). Could not read the values.

### D. Falk19 force results available to us
- **Total 3-fin CL/CD only** (digitized from Falk20 Fig 17): max CL ≈ 0.74 @20°, max CD ≈ 0.50 @40–45°,
  max L/D ≈ 7.55 @6.25°. See `falk19_3fin_total_forces.csv`.
- **PER-FIN 3-fin data (windward-front / leeward-front / centre) — NOT AVAILABLE** (paywalled).

---

## Gaps / could not obtain
1. **Falk19 full text — not obtainable.** Closed access, no legal OA copy indexed (Unpaywall/S2/CORE/
   OpenAIRE/BASE/FAU all negative). Only the abstract + Falk20-reflected total 3-fin curve were captured.
2. **Falk19 per-fin forces/coefficients** (the two front side fins vs the centre/rear fin, and any
   isolated single-fin experimental baseline the abstract implies) — **GAP.** These would be the ideal
   3-fin thruster interference target; they exist in Falk19 but are behind the paywall.
3. **Isolated / single-fin baseline in Falk20 — does not exist.** Falk20 has no isolated-fin run; its
   "rear-fin deficit" is rear-vs-front *within* the 4-fin set (still a valid interference signal). Any
   isolated-fin comparison must come from Falk19 (unobtained) or be generated by us.
4. **Falk20 per-fin values are digitized, not tabulated.** No table of per-fin CL/CD exists in the
   paper; all per-fin numbers here are read off Fig 10 (±0.02–0.03; ±0.03–0.05 at AoA≤10 where curves
   bunch). Total forces from Fig 12b/13b are ±3–5% (18 m/s) to ±15% (5 m/s low-AoA).
5. **Reynolds number** not stated in either paper (only Mach for Falk20); Re values here are our
   computed estimates on base chord.
6. **Foil thickness, sweep/rake angles** not given numerically in Falk20 (only the planform drawing
   Fig 6a and the flat-inner/cambered-outer description).
7. Falk20 velocity for the Fig 10 per-fin plot is not stated explicitly; it is immaterial because the
   paper shows coefficients are speed-independent (Sec 3.2/4.3).

## Files written (all under …/scratchpad/falk/)
- `falk-reference.md` — this document
- `falk20_perfin_forces.csv` — per-fin CL & CD vs AoA, commercial 4-fin (Fig 10) [digitized]
- `falk20_total_forces.csv` — mean CL/CD + total lift/drag force vs AoA per speed (Fig 10/12/13) [digitized]
- `falk19_3fin_total_forces.csv` — total 3-fin CL/CD (from Falk20 Fig 17) [digitized]
- `falk20.pdf` — full open-access Falk20 paper; `falk20.txt` — its extracted text
- figure crops: `fig10a_big.png`, `fig10b_big.png`, `fig17a_big.png`, `fig17b_big.png` (digitization sources)
