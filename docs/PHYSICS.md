# Physics & math foundation

This document pins down the math fingen implements, with citations into
[SOURCES.md](SOURCES.md) (keys like `[BW04]`). It is the spec for `foil.py`, `outline.py`,
`loft.py`, and the future hydro/sizing/structure modules. Geometry code uses millimetres;
physics formulas below are SI unless noted.

## 1. Operating envelope

Fluid properties (standard seawater at ~15–20 °C): density ρ ≈ 1025 kg/m³, kinematic
viscosity ν ≈ 1.05×10⁻⁶ m²/s.

**Speeds.** GPS field data give mean wave-riding speed **6.4 ± 0.1 m/s** and top speeds
**~9.7–9.9 m/s** [Forsyth24]; competition maxima average ~9.3 m/s [Far12]. Turning-load
evaluation uses **7 m/s** following [ShormISEA20]; the measured-pressure river-wave dataset
sits at ~4 m/s [Knies25]. Design envelope: **3–10 m/s**, with 10–15 m/s reserved for
tow-in/step-up extensions [BW04].

**Wave speed from wave height.** Shallow-water celerity c = √(gh) with depth-limited breaking
H_b = γ_b·h_b (γ_b ≈ 0.8 typical, Miche/Goda forms available) gives

    c ≈ √(g·H_b/γ_b)        [Dro26]

A rideable wave requires surfer speed ≥ peel rate, which bounds design speed from below
[Sca03]. This maps the UI's "wave size" input onto design speed.

**Reynolds number.** Re = V·c̄/ν with chord c̄ ≈ 0.10 m spans **≈ 3×10⁵–10⁶** over the
envelope — the transitional regime where laminar separation bubbles matter [Dre89, Sel95,
Win18, Ren26]. Measured fin polars are nearly Re-invariant across exactly this range [BW04],
which justifies designing to a single mid-envelope Re with low-Re checks at the slow end.

## 2. Fin geometry conventions

Industry parameters (all published per-fin by manufacturers): **depth** (base plane → tip),
**base** (chord at the board), **area**, **sweep/rake angle**, **foil type** [FCS26, Fut26].
Validation anchor — a medium thruster side fin: base ≈ 110 mm, depth ≈ 115 mm,
area ≈ 9800 mm², sweep 32–37°, flat inner foil; center fin 50/50 symmetric [FCS26, Fut26].
Test-fin geometry in the canonical experiment: AR 3, 25° sweep, t/c 9%, half-NACA-0009 with
flat pressure side [BW04].

**Placement.** Production conventions: thruster front fins toe-in ≈ 1/4″ over the box
(≈ 3–4°), cant 7–9° (≈ 5° for big-wave boards); quad rears 1/8–3/16″ toe, 3–5° cant [Gre26].
CFD studies of production setups used toe 3.5°, cant 8.5° [Falk20]; the instrumented-fin field
study used toe 4° [Knies25]. fingen defaults: **toe 3.5°, cant 8.0°**.

**Parameter interface.** Precedent for exposing ≈10 user-facing parameters (depth, sweep, base,
foil profile, tip geometry, cant, fin system) [Nov21]; optimization-grade parameterization via
chord/depth/sweep/camber/camber-position/thickness [Sak17].

## 2b. Fin-set assembly conventions (`assembly.py`)

Toe and cant are **placement transforms**, not blade geometry: one right-hand blade is
lofted and CHECKed, its left-hand mate is `export.mirror_hand` of it (mirror across the
y = 0 plane), and each blade is toed, canted and translated into the set. The assembly
frame is each blade's own frame — no remapping — so `fin_solid` output is placed directly:

- **+x aft** (toward the tail; a blade's LE is at local x = 0, TE at +x),
- **+y toward the right rail** (outboard for the right fin; the canonical right-hand blade's
  foil bulges to +y with its flat/inboard face on y = 0, per `export.py`),
- **+z up, out of the board** (blades hang in z ≥ 0; the board plane is z = 0).

The origin is the center-fin base center; side blades are positioned by their base-center
offset from it, so front fins sit at **negative side_x** (forward) [Gre26].

**Sign convention.** Toe is a rotation about the vertical **z** axis; **nose-in (leading edge
toward the stringer) is positive toe**. Cant is an outward lean about the longitudinal **x**
axis (the tip leans toward the near rail). Left and right take **opposite signs of the same
magnitude**: the right fin is `+toe` about +z and `−cant` about +x, the left the negatives.

**Cant × the z ≥ 0 convention (the classic bug).** A canted blade's root must stay on the
board plane. Cant therefore rotates about the x-parallel line through the blade's **own base
centerline** (base-face center, recentered to the origin) *before* the outboard translation —
never about the global x axis after translating to side_y, which would lift the whole root by
`side_y·sin(cant)` (centimetres off the board). Rotating about the base centerline leaves only
the finite base-thickness tilt (≤ ~1 mm at 8°), so `bbox.min.Z ≈ 0` for every placed blade.

**Defaults** (production conventions [Gre26]; CFD'd production setups toe 3.5°/cant 8.5° [Falk20]):

| Config | Slots | Toe | Cant | Notes |
|---|---|---|---|---|
| SINGLE | center | 0° | 0° | rides the stringer, symmetric foil |
| TWIN | 2 sides | 3.5° | 8.0° | forward + outboard, no center |
| THRUSTER | 2 sides + center | fronts 3.5° | fronts 8.0° | center 0/0; sides forward of center [Gre26 1/4″ toe, 7-9° cant] |
| QUAD | front pair + rear pair | fronts 3.5°, rears 2.0° | fronts 8.0°, rears 4.0° | rears have their own x/y/toe/cant [Gre26 1/8-3/16″ toe, 3-5° cant] |
| 2+1 | 2 sides + big center | 3.5° | 8.0° | center box tunable between single and thruster |

Fore-aft/lateral offsets (side_x ≈ −195 mm, side_y ≈ 118 mm; quad rears −60/95 mm) are
representative shortboard cluster spacing (front fins ≈ 8″ ahead of the rear box, ≈ 4.6″ off
the stringer [Gre26]); the exact values are board-width dependent, so their scalar bounds stay
loose and the **minimum safe spacing** — which depends on blade thickness, toe and cant — is
enforced geometrically by a pairwise solid-intersection check at assembly (a `ValueError` on
interpenetrating blades), not by a fixed number. The set exports as one multi-solid STL surface
named `fins` (snappyHexMesh meshes it as a single patch) or a STEP scene for CAD.

## 3. Outline math (`outline.py`)

The planform (side-view silhouette) is built from Bézier curves in Bernstein form,

    B(u) = Σᵢ C(n,i)·uⁱ·(1−u)ⁿ⁻ⁱ·Pᵢ,   u ∈ [0,1]

evaluated by de Casteljau [PT97, Far02]. Control points are the design variables; this is
well-posed because Bézier curves interpolate their endpoints, their end tangents align with the
control polygon (used to enforce base flatness and tip direction), and the
variation-diminishing property guarantees oscillation-free outlines from monotone control
polygons [Far02]. Degree ≈ 6 suffices for foil-grade fidelity; higher degrees add parameters
without accuracy [Jai17]. Bernstein-basis parameters are the aerodynamic-community standard
for shape optimization (CST) [Kul08].

**Three-layer design space.** (1) *Representation*: what shapes are expressible — degree-7
Bézier edges plus the tip lobe; the optimizer's playground, kept maximally free via the
level-2 control-point offsets (`le_dx`/`te_dx`), which span the full Bézier family
(Bernstein completeness [Kul08]). (2) *Templates*: the six level-1 sliders map to control
polygons through weight vectors calibrated so defaults resemble known-rideable commercial
templates — an empirical prior, not physics. (3) *Objective*: physics lives in the hydro
model/CFD, never in construction constants. Every shape tweak gets a number attached: the
`elliptic_deviation` metric (RMS distance of c(z) from same-area elliptic loading, the
first-order induced-drag proxy [Pra21]) — e.g. the commercial-look concave default costs
~0.08 versus a straight TE, a trade the CFD stage must adjudicate, not the defaults.

The trailing edge takes a signed shape parameter (−1 concave cutaway … +1 convex/keel-like),
and the planform closes with an **elliptical tip lobe**: above the span height where the chord
equals the tip width, c(z) is scaled by √(1−u²) with the lobe centerline following the outline's
mean line — a rounded, rake-following tip tangent to the edges below it (commercial templates
end in such a lobe, not a point).

The outline yields a spanwise **chord schedule** {z, x_LE(z), c(z)} sampled at n stations,
from which derived quantities follow:

    S  = ∫ c(z) dz                    (planform area)
    AR = d²/S                         (geometric aspect ratio, d = depth)
    Λ  = sweep angle of the LE (or half-chord line for lift-slope formulas)

## 4. Section math (`foil.py`)

NACA 4-digit construction [Jac33, AvD59]:

**Thickness distribution** (x normalized by chord, t = t/c):

    y_t(x) = 5t·(0.29690√x − 0.12600x − 0.35160x² + 0.28430x³ − 0.10150x⁴)

**Camber line** (max camber m at position p):

    y_c = (m/p²)(2px − x²)                     x < p
    y_c = (m/(1−p)²)((1−2p) + 2px − x²)        x ≥ p

**Assembly:** thickness applied perpendicular to the camber line
(x_u = x − y_t·sinθ, y_u = y_c + y_t·cosθ, θ = atan(dy_c/dx)); leading-edge radius
r_LE = 1.1019·(t/c)²·c [AvD59].

**Variants:**
- *Center fins:* symmetric 50/50 (m = 0), t/c ≈ 6–10% [FCS26, SK81].
- *Side fins:* flat inner face with the full section shape on the outer face (the classic
  "flat foil"), equivalent to a half-thickness symmetric section plus camber [BW04, Fut26].
- *Printability:* trailing edge truncated to a finite thickness (0.6–0.8 mm per material
  preset) — an engineering constraint applied after the analytic section is generated.

Section polars for the fast model come from XFOIL-class analysis with e^N transition (the
correct tool at this Re) [Dre89], anchored to tabulated data: symmetric NACA sections over the
full AoA range [SK81], low-Re wind-tunnel polars [Sel95]. At the slowest speeds (Re ≲ 10⁵),
thick sections lose L/D to laminar separation, which motivates thinner sections for
small/slow-wave fins [Win18, Ren26].

**Thinning grooves** (`GrooveParams`, off by default): spanwise channels over the
upper half-span that locally thin the section — the G1/G2 fins of [Els22, For24].
Their CFD puts the payoff at high incidence (+11 % L/D at the 30° stall angle:
drag −13 %, lift −3.8 %); the bench test shows the grooved blade is also more
flexible, so the channels double as tuned flex hinges. The papers give count,
length and spacing (6 × 60 mm, 6 mm apart) but not depth, width or profile —
those are free parameters here, deliberately: the CFD optimizer owns them. Our
construction: a raised-cosine bump per channel in span (smooth walls), full
depth from the leading edge (the scalloped LE of their photos), fading out by
85 % of local chord so the TE stays printable. Grooves thin the *envelope about
the camber line*, so cambered sections groove cleanly. Structure note: the
grooved band loses section modulus where it sits. Validation forces the band
to start above 12 % of depth, so the z = 0 root section (tab junction, root
stress check §8) stays full thickness — but a deep groove low on the span can
still be the *critical bending section* (the moment there is nearly the root
moment while the modulus cut is disproportionate: thickness enters the section
modulus squared). The tier-0 groove-band stress check now exists: `flex.py`
(§5b) evaluates σ = M/W at every station — groove centers injected exactly —
and reports the band's own maximum next to the root value; for the default
groove set the critical section indeed falls inside the band, so grooved
candidates are gated on that margin, not just the root check. Softer
tips are the expected (and in [For24], desired) side effect.

## 5. Loft (`loft.py`)

Foil sections are generated at each outline station, all with **identical degree and knot
structure**, then skinned into a B-spline surface (OCCT `ThruSections`). Compatible section
parameterization is required — knot merging across incompatible sections produces wiggles and
control-point explosion [PT02]; the skinning algorithm itself is the standard one [PT97].
The solid is closed with a flat base at z = 0 (tab systems attach here later).

**Groove-band skinning:** ThruSections' global surface fit is unstable against
short-wavelength thickness alternation (a 5 % thinning dip produced metre-scale
skin excursions — measured during development). Grooved fins therefore use a
segmented loft: smooth fit below and above the band, *ruled* loft (linear
between stations, overshoot-free by construction) through it, with stations
injected at channel edges/quarters/centers and gap midpoints; the segments
share exact boundary sections so the fuse joins on identical planar faces.

## 5b. Tier-0 flex model (`flex.py`)

The blade is a tapered solid-section cantilever [GT97, Zar14], solved numerically on the
station arrays (cumulative trapezoids — milliseconds, optimizer-embeddable). Per station,
from the actual section polygon: area A, bending inertia I about the chordwise neutral axis
(asymmetry of flat-inside/grooved sections resolved), and the solid-thin-section strip
torsion constant J = (1/3)∫t(x)³dx — valid for t/c ≤ 0.15 and NOT the polar moment, which
grossly overestimates torsional stiffness of non-circular sections [BAH96, Roa01]. The
distributed side load defaults to w ∝ c (uniform CL; callable override) and is integrated
twice for slope θ(z) and deflection δ(z). Two mechanisms change local incidence:

- **Rake coupling**: Δα = −θ·sinΛ_e, with Λ_e the local sweep of the elastic axis
  (section-centroid locus, differentiated through a chord-weighted cubic fit — the raw locus
  curls forward inside the tip lobe on millimetre chords carrying no load). An unswept axis
  gives exactly zero, matching the no-resolvable-twist metal foils of [Zar14].
- **Direct torsion**: the sectional cp (≈ quarter chord) sits ahead of the elastic axis, so
  m = w·(x_ea − x_c/4) integrated with GJ twists the blade nose-up [BAH96] — the sign of the
  +0.6° measured on the torsionally soft CFRP00 blade of [Zar14].

Derived outputs: washout lift knockdown ΔCL/CL = a·∫Δα·c dz/S · qS/F with hydro's DATCOM
slope (§6); wet natural frequency from a Rayleigh quotient on the static shape with the 2D
flat-plate added mass πρ_w(c/2)² per unit span [BAH96] — added mass dominates thin blades
and is what separates the steel [Zar14] foil's 62 Hz in water from 100 Hz in air; a
strip-theory torsional divergence speed from q_D = ∫GJφ′²/∫a·c·e·φ² (reducing to the classic
(π/2s)²·GJ/(c²e′a) for the uniform wing [BAH96]; sweep neglected, so conservative for raked
fins, whose washout raises the true divergence speed); and the per-station bending stress
σ = M·y/I against the §8 allowables — with the groove band's own maximum reported, the
tier-0 critical-section check promised in §4.

**Calibration.** The pure wetted-span beam misses root warping, shear lag and plate behavior,
all growing with how stubby the blade is: bending compliance is scaled by 1 + 0.55·(c_root/s),
one slope calibrated on the two available 3D anchors — the measured [Zar14] Type I δ′ = 0.204
(slender, c/s = 0.4, needs ×1.18 over the raw beam) and the CalculiX demo blade (stubby,
c/s ≈ 0.96, needs ×1.51) — both land within a few percent, and the [Zar14] wet frequency
follows to −4 %. Torsion carries no such factor yet (no torsional anchor). E defaults to a
7000 MPa PET-CF print placeholder until the load-cell rig measures effective printed-blade
moduli [PETCF, Fis23]; the FEM tier (scripts/fem_demo.py) re-anchors per-geometry. Validity:
pre-stall distributed loads, small deflections, solid thin sections.

## 5c. Tier-0 roll dynamics (`roll.py`)

Rail-to-rail feel is a **roll** problem (rotation p about the fore-aft x axis), and the fin's
job there is to *damp* it. When the board rolls, a blade element at height z above the roll
axis is swept sideways at p·z_eff (z_eff = z + z0, z0 the roll-axis height above the board —
default 0, referencing it to the fin root); the forward speed U converts that into a local
incidence Δα = p·z_eff/U, whose extra lift opposes the roll. This is the exact roll analogue of
a wing's damping in roll [Pol49], solved as a strip integral on the chord schedule
(milliseconds, optimizer-embeddable — the same numeric spirit as §5b).

**Two regimes.**
- **z² (at speed).** The lift-based roll-damping derivative L_p = ∂(roll moment)/∂p =
  −q·a/U·∫c(z)·z_eff² dz (a = the fin's DATCOM lift slope §6). The arm enters *squared* — once
  for the induced incidence, once for the moment arm — so at fixed chord damping grows with span
  **cubed**. Rectangular closed form ∫c·z² dz = c·s³/3, so the dimensionless C_lp = L_p·U/(q·S·s²)
  → −a/3 (the *uncorrected* strip value — the finite-span correction below scales it). This is the
  dominant fin contribution to roll feel while moving.
- **z³ (near zero speed).** With no forward flow there is no lift; the swept element pushes water
  broadside as a flat plate (normal-force coefficient C_d ≈ 1.1 [Hoe75]), a drag moment
  M_drag = −½ρC_d·∫c(z)·z_eff³ dz · p·|p| — quadratic in p, reported separately as the low-speed
  number.

**Finite-span calibration (the z² lift term only).** The strip integral already substitutes the
fin's **3D** DATCOM lift slope for the 2D section slope (§6), so it is *not* a raw-2D over-predictor.
A converged lifting-line solve (validated against the elliptic closed form, [TQ48], and [GF49])
gives our **near-triangular tapered** default fin C_lp = −0.2228 vs the strip's −0.2384 — an
*additional* rolling-specific finite-span relief of only **~7 %**, not 2×. The apparent "~2×" of the
original bench attribution was **apples-to-oranges** (it compared the *rectangular* closed form
−a₃D/6 → C_lp ≈ −1.10 for "fingen" against rectangular [GF49] wings, whereas the actual tapered fin
is −0.72; see the correction banner in `out/roll-clp-anchors.md` §4 and
`bench/roll-validation/AUDIT-ADDENDUM.md`).

The observed twisted-inflow **CFD/strip ≈ 0.49** decomposes into one real effect and three
artifacts: **0.93** (real antisymmetric rolling relief, lifting-line vs strip) × **0.78** (real
viscous / lifting-surface knockdown, LL → measured [GF49]) × **0.80** (rig artifact — the imposed
shear is relaxed by the freestream lateral BCs, so the fin sees ~0.75–0.87 of nominal ω·z) ×
**0.85** (analysis artifact — the concave secant read at finite ω vs the true ω→0 derivative; a
Richardson extrapolation recovers −0.124…−0.138 N·m·s). The concavity is itself a **rig artifact**
(the BCs relax a larger imposed shear proportionally more), *not* span-load physics. And the
`symmetryPlane` board solves the **symmetric-mirror** problem (α = ω·|z|), ~20 % different from true
*antisymmetric* rolling, so the [GF49]-rig equivalence is inexact. De-artifacted, the honest
**CFD/strip ≈ 0.70** (band 0.56–0.77), i.e. tier-0's real over-prediction is only **≈1.3–1.4×**.

roll.py therefore keeps the strip integral as the geometric backbone — it carries the c(z)·z²
distribution, the cant/offset/z0 arm machinery and the set composition, all validated in *shape* by
the CFD — and multiplies **only the lift-loading term** (L_p and its sweep/heave diagonals) by an
**audit-calibrated constant**

  **κ = KAPPA_FS = 0.73** (provenance: 0.93 rolling relief × 0.78 viscous knockdown; honest band
  0.56–0.77),

**not** the textbook A/(A+4) — that form matched an artifact-laden 0.49 and is ~2× too aggressive
here. κ is **planform-dependent** (this value fits the near-triangular default taper; a rectangular
planform carries more rolling relief and would take a smaller κ) and **provisional**: the refinement
path is a fixed-rig CFD rerun (shear imposed on all inflow boundaries — already applied to
`scripts/roll_validation.py`) with an ω→0 extrapolation, plus a [GF49] bench replication. [TQ48]
(Toll & Queijo, NACA TN 1581) and [GF49] (Goodman & Fisher) remain the theory family and measured
class the calibration is anchored to; the reflected aspect ratio A = AR_full = 2·AR_geom (a fin
mirrors across the board plane [GF49]) is still reported (`ar_full`) as provenance context. The
uncorrected strip value is exposed as `l_p_strip` (auditable: l_p_strip/l_p = 1/κ). **The
added-inertia (πc²/4·z²) and broadside-drag (z³) terms are NOT scaled**: they are apparent-mass and
bluff-body-drag quantities, not lifting-surface loads, so the rolling-load relief — an
induced-downwash effect specific to the *lift* loading — does not apply to them.

**Roll added inertia** I_add = ρ·∫(πc(z)²/4)·z_eff² dz — the 2D flat-plate apparent mass
πρ_w(c/2)² per span [BAH96], moment-weighted by z_eff² like any mass moment of inertia (∝ c² s³
for a rectangle; the same added-mass line as the §5b wet frequency, here weighted for roll).

**Set geometry.** A side blade at lateral offset y_f is off the roll axis, so rolling both
*sweeps* it (the z-component, as for the center fin) and *heaves* it (a vertical velocity p·y_f
from the offset). On an upright blade the heave is pure spanwise flow and makes no lift; **cant**
γ tilts the lift normal to n̂ = (0, cosγ, sinγ), and the incidence-driving normal-wash and the
roll-moment arm both reduce to ℓ(z) = z + z0·cosγ + y_f·sinγ (reciprocity). Damping is
q·a/U·∫c·ℓ² dz per blade; the sweep contribution carries cosγ (it *decreases* with cant) while
the y_f·sinγ heave *rises* from zero. The arm is mirror-symmetric, so a right and a left side
blade add the same positive damping — a thruster's pair adds to the center fin. The center fin
(y_f = γ = 0) is the pure-sweep case. Placement fields come from `assembly.py`; toe is neglected
(second order for roll).

**Outputs & scope.** L_p (and C_lp), I_add, the low-speed drag coefficient, a roll time constant
τ = I_add/|L_p|, and a rail-to-rail agility proxy 1/|L_p| (higher = looser). The time constant
uses I_add **only**: the board+rider rotational inertia — which actually sets the maneuver
timescale — and the board's own hydrostatic/rail roll *stiffness* are **out of scope**. The
division of labour is deliberate: the **board dominates static roll stiffness**, the **fins
dominate roll damping at speed**, and this module is the fin-damping half. τ is thus the fin's own
roll-rate decay time (milliseconds — a relative feel index, not an absolute maneuver time). The
product-relevant result is that at *fixed area* damping ∝ S·s² and inertia ∝ S·s, so a deep,
narrow blade damps and resists roll far more than a shallow, wide one of the same area — the
physics that prices depth, and the intended eventual replacement for the empirical depth-corridor
fence in the optimizer (deferred until CFD confirms the pricing; report-only for now).

**Validation.** The quadrature is checked against the rectangular closed forms (c·s³/3, ρπc²s³/12,
c·s⁴/4) to 0.1 % and the span/chord scalings pinned on the uncorrected `l_p_strip` backbone
(test_roll). The strip **shape** (its S·s² depth scaling — the depth-ranking the module exists for)
is validated by the twisted-inflow RANS bench (bench/roll-validation, committed a51ddbc) and by the
converged lifting-line audit; only the **absolute level** carries the (now modest) finite-span
knockdown. For the default fin at 6.4 m/s the calibrated **|L_p| = 0.174 N·m·s** (strip 0.238,
κ = 0.73) sits at the top of the **de-artifacted CFD derivative band 0.143–0.184 N·m·s** — the audit
Richardson ω→0 derivative −0.124…−0.138 divided by the shear-preservation 0.75–0.87 — consistent
with a tier-0 over-prediction of **≈1.3–1.4×**.

> **Superseded (see `bench/roll-validation/AUDIT-ADDENDUM.md`).** The committed VERDICT.md's "~2×
> strip deficit" attribution and its "CFD near-zero secant −0.117 within 2 % of ½·strip −0.119"
> comparison are **withdrawn**: the ½·strip target came from a rectangular-vs-tapered mix-up, and
> −0.117 is an artifact-laden finite-ω secant, not the ω→0 derivative. An independent
> factor-of-2 audit (converged lifting-line, N = 80–480) verified the roll code clean — formula,
> units, quadrature and CFD moment path all confirmed — but reattributes the discrepancy to
> 0.93 rolling relief × 0.78 viscous knockdown × 0.80 shear-rig artifact × 0.85 concave-secant
> analysis artifact. The strip SHAPE stands; the 2× magnitude claim does not.

scripts/roll_validation.py stages the (fixed-rig) cross-check: the single-fin case with the uniform
inlet replaced by a codedFixedValue shear uy(z) = ω·z imposed on **both the inlet and the top/side
farfield** (a freestreamVelocity farfield let the imposed shear relax ~10–15 % before the fin — the
audit-endorsed rig fix), plus a `forces` FO reporting M_x about the root, at a baseline + a denser
low-ω sweep (0, 0.5, 1, 2, 3) for the ω→0 extrapolation — the CFD dM_x/dω→0 against the calibrated
tier-0 L_p (the EPYC solves it; the script only writes the dictionaries).

## 6. Fast hydro model (lift, drag, stall)

The fin is a low-aspect-ratio swept wing next to a wall.

**Effective aspect ratio.** The board acts as an end plate / reflection plane at the fin base:
a fin on a large wall behaves like half of a doubled-span wing (AR_eff → 2·AR_geom in the
ideal limit); finite end-plate effectiveness follows the 1 + 1.9·h/b form [Hem28, Hoe75].
fingen treats the reflection-plane factor k ∈ [1, 2] as a calibration parameter (the board is
a finite, curved, moving plate — k ≈ 1.6–1.9 expected).

**Lift-curve slope.** The production formula is DATCOM §4.1.3.2 [DAT78], the closed form of
Polhamus's swept-wing result [Pol49] with Diederich's planform parameter structure [Die51]:

    C_Lα = 2π·AR / (2 + √(AR²·β²/κ² · (1 + tan²Λ_c/2 / β²) + 4))

with β = 1 (incompressible), κ = a₀/2π (section slope ratio), Λ_c/2 = half-chord sweep.
Limits it must (and does) satisfy: Helmbold at Λ = 0, AR < 4 [And17]; slender-wing
C_Lα = πAR/2 as AR → 0 [Jon46]; Küchemann's a₀ → a₀cosΛ swept-Helmbold as a cross-check
[Kuc52]. Foundations: lifting line [Pra21].

**Nonlinear lift.** At the fin's AR (~1.5–3.5 effective) linear theory under-predicts beyond a
few degrees. Add the Polhamus leading-edge-suction analogy term [Pol66]:

    C_L = K_p·sinα·cos²α + K_v·cosα·sin²α

with the caveat from modern flat-plate data that side-edge (tip) vorticity, not a
leading-edge vortex, supplies the nonlinear term on low-sweep planforms — calibrate K_v
accordingly [Tra23, Hoe75].

**Induced drag.**

    C_Di = C_L² / (π·e·AR_eff)        [Pra21, Osw33]

with span efficiency e ≈ 0.85–0.95 for fin-like tapered planforms (calibrated later against
CFD). Profile drag from section polars [SK81, Dre89].

**Stall.** Measured fin stall onset: lift-curve break at **α ≈ 12–14°**, a mix of tip stall
and trailing-edge stall, nearly Re-independent in the operating range [BW04]. The design
margin below this is the primary spin-out guard (§7).

## 7. Free surface: ventilation & cavitation (spin-out)

Spin-out is modeled as **atmospheric ventilation** of a surface-piercing/near-surface lifting
body [You17]. Mechanism (two necessary conditions + trigger): (1) separated or cavitating flow
at sub-atmospheric pressure on the suction side, (2) a continuous air path from the free
surface — the surface "seal" must rupture [Swa74, Har16]. Natural inception on yawed struts
occurs post-stall (α ≳ 20°), but disturbances trigger it earlier [BS59]. Consequence: an
abrupt, hysteretic loss of most of the fin's lift [You17, Har16].

Design rules implemented:
- **Stall margin = ventilation margin.** Keep design C_L well below the α ≈ 12–14° break
  [BW04, Swa74]: a section that stays attached cannot naturally ventilate.
- **Speed dependence.** Governing parameter is the depth-Froude number Fr_h = U/√(g·h); at
  higher Fr_h the tail-ventilation inception angle *decreases* with speed, so margins tighten
  at speed [You17, AF26]. Avoid ogive-like base sections (base ventilation) [AF26].
- **Free-surface de-rating.** Lift is de-rated near the surface: significant for submergence
  h/c < 2, severe below h/c < 1 [Das00, Tag26].
- **Cavitation is a diagnostic, not a driver.** σ = (p_∞ − p_v)/(½ρU²), inception at
  σ_i = −C_p,min [Bre95]; at fin depths this yields inception speeds ≳ 10–15 m/s — marginal
  for ordinary surfing, relevant only for tow-in extensions. fingen reports −C_p,min but
  optimizes against ventilation/stall.

## 8. Loads & structure (3D printing)

**Measured loads** (design cases): per-fin side force up to **~300 N** with surface pressure
differentials **14–20 kPa** (90 kg rider, ~4 m/s) [Knies25]; in-ocean fin flex up to **~10%**
(tip deflection / depth) at ~6 m/s, 8–9% in turns vs 2–3% paddling, with associated bench
stiffness ~3.6 N/mm and ~310 N per-fin turn loads [Krz24, Krz22].

**Model.** Euler–Bernoulli tapered cantilever: tip deflection δ = ∫ M(x)/(E·I(x)) dx, base
stress σ = M·c/I, with I(z) computed from the discretized foil sections [GT97], cross-checked
against tabulated tapered-beam cases [Roa01]. The cantilever idealization for foil-sectioned
fins is experimentally validated (including composite anisotropy effects) [Zar14].

**Materials** (ISO 178 bending, dry, from manufacturer TDS):

| Material | E_flex XY | E_flex Z | σ_flex XY | σ_flex Z | Notes |
|---|---|---|---|---|---|
| PET-CF [PETCF] | 5320 MPa | 2210 MPa | 131 MPa | 49 MPa | stiffer |
| PAHT-CF [PAHTCF] | 4230 MPa | 1820 MPa | 125 MPa | 61 MPa | tougher, wet-stable |

**Print-orientation rule.** Bending stress must lie in the layer (XY) plane: the Z-direction
carries ~2.5× less bending strength, so fins are printed flat or on-edge, never standing on
the base [Ahn02, PETCF]. Use orientation-appropriate moduli, not datasheet-longitudinal, in
E·I (orientation changes modulus by up to ~2× for short-CF polymers) [Fis23]. Comparison
context: printed fins are mechanically and on-water comparable to commercial fins
[Gat17, Forsyth24, NN21].

## 9. Sizing closure (rider → fin area)

The chain from user inputs to geometry:

1. **Required side force.** Coordinated-turn balance for combined rider+board mass M at speed
   v and turn radius R: F = M·v²/R, with R = v²/(g·tanφ) at bank angle φ [SH-turn — grey
   literature; force-balance picture peer-reviewed in ShormISEA20, Falk19]. "Surf style/skill"
   maps to turn-rate demand: measured cutback durations 0.55/0.45/0.35 s
   (intermediate/expert/pro) at 7 m/s [ShormISEA20].
2. **Area from force.** Standard appendage sizing [LE14]:

       A_total = F / (½·ρ·v²·C_L,design)

   with C_L,design set by the stall/ventilation margin (§6–7), and the load shared between
   fins per configuration [Falk19]. Sanity anchor: ~300 N on a 0.015 m² fin at moderate speed
   [Knies25] — order one-third of rider weight per fin.
3. **Shape from style.** Rake/upright trade-off (drawn-out hold vs pivot), thickness/section
   from design speed (§4), placement from configuration (§2) — validated against commercial
   template ranges [FCS26, Fut26, Gre26].

## 10. CFD & optimization stage

- **Solver setup:** RANS with SST k-ω for attached/pre-stall polars; URANS for post-stall and
  high-AoA points where steady solutions miss separation dynamics [Falk19, Falk20]. AoA sweep
  0–45° at multiple speeds [Falk20]. Transition-aware treatment at low Re where affordable
  [Ren26].
- **Optimization:** Latin-hypercube DOE over the fin parameter vector + surrogate/GA — the
  published precedent achieved ~62% L/D improvement over a baseline [Sak17]; modern practice
  favors surrogate-based loops [Ren26].
- **Dynamic validation:** maneuver-driven simulations (measured roll/pitch/yaw histories) as
  the high-fidelity check [ShormISEA20]; field metrics (speed, turn magnitude/power) for
  on-water validation [Forsyth24, Shorm20].
- **Free-surface tier:** VOF (+ Schnerr–Sauer if cavitation is enabled) for ventilation-margin
  studies [Tag26, AF26]; until then, deep-submergence CFD with §7 margins applied analytically.
