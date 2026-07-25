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
modulus squared). Until the sizing gate checks stress at the first groove,
treat depth_ratio ≥ ~0.4 low on the span as structurally unvetted. Softer
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
