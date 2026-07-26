# Sources

Annotated bibliography for the math and physics implemented in fingen. Every entry below was
located online and verified on 2026-07-24 (metadata checked against the publisher page, DOI
record, or an official repository copy). Where a publisher blocks automated access
(ScienceDirect, MDPI, AIAA, SAGE), verification used the DOI record plus a secondary
repository, noted per entry. Citation keys (e.g. `[BW04]`) are used throughout
[PHYSICS.md](PHYSICS.md) and in code comments.

---

## 1. Surf-fin hydrodynamics (experiments & CFD)

### [BW04] Brandner & Walker (2004) — Hydrodynamic Performance of a Surfboard Fin
*Proc. 15th Australasian Fluid Mechanics Conference, Sydney, paper AFMC00105.*
[Wayback copy](https://web.archive.org/web/2020/https://www.aeromech.usyd.edu.au/15afmc/proceedings/papers/AFMC00105.pdf) —
original USyd PDF is 404; existence verified via the published proceedings TOC (ISBN 978-1-62748-434-3).
The canonical water-tunnel experiment on a surfboard side fin: elliptical planform, 25° sweep,
flat pressure side, half-NACA-0009 section (span 120 mm, base 100 mm, AR 3, t/c 9%), tested at
−6°…26° incidence, Re 2×10⁵–10⁶.
**Cited for:** baseline fin geometry defaults; near-Re-invariance of the polars over the fin's
operating range; lift-curve break (stall onset) at α ≈ 12–14°; force nondimensionalisation.

### [Falk19] Falk et al. (2019) — Computational hydrodynamics of a typical 3-fin surfboard setup
*Journal of Fluids and Structures 90:297–314.* [DOI 10.1016/j.jfluidstructs.2019.07.006](https://doi.org/10.1016/j.jfluidstructs.2019.07.006)
First URANS (SST k-ω) simulation of a full thruster set, AoA 0–45°; quantifies inter-fin
interference and the optimal pre-stall AoA band for peak lift.
**Cited for:** SST k-ω RANS/URANS as the CFD methodology; treating the fin set as an
interacting system; URANS above stall; existence of a finite design-C_L band.

### [Falk20] Falk et al. (2020) — Hydrodynamics of Changing Fin Positions within a 4-Fin Surfboard Configuration
*Applied Sciences 10(3):816, open access.* [DOI 10.3390/app10030816](https://doi.org/10.3390/app10030816)
STAR-CCM+ RANS/URANS quad-fin position study, AoA 0–45° at four inflow speeds; studied
configuration used toe-in ≈ 3.5°, cant ≈ 8.5°.
**Cited for:** default toe/cant values; fin placement as an optimization variable; the AoA sweep
matrix for polar generation; quad-vs-thruster lift/drag trends.

### [Sak17] Sakellariou, Rana & Jenkins (2017) — Optimisation of the surfboard fin shape using CFD and genetic algorithms
*Proc. IMechE Part P: J. Sports Engineering and Technology 231(4):344–354.* [DOI 10.1177/1754337117704538](https://doi.org/10.1177/1754337117704538)
GA + Latin-hypercube DOE over 42 fin designs parameterized by chord, depth, sweep, camber,
camber position and thickness (NACA 4-digit), evaluated with steady SST k-ω at 10 m/s / 10°.
**Cited for:** the fin parameterization strategy; the DOE + optimizer architecture; the
10 m/s / 10° reference operating point; ~62% L/D improvement as achievable headroom.

### [Knies25] Kniesburges et al. (2025) — Measurements of the hydrodynamic pressure on a surfboard fin during surfing
*Scientific Reports 15:10331.* [DOI 10.1038/s41598-025-94834-0](https://doi.org/10.1038/s41598-025-94834-0)
First in-situ pressure measurements on a fin during surfing (sensor-instrumented 3D-printed
side fin, toe-in 4°, 90 kg rider, ~4 m/s river wave): suction side to −7 kPa, pressure side to
+17 kPa, differentials 14–20 kPa, estimated peak per-fin lift ~300 N on 0.015 m² area.
**Cited for:** structural design loads (ΔP ≈ 20 kPa, ~300 N per fin); validation of the
F = C_L·½ρv²A magnitude used in sizing; 3D-printed fins as viable instruments.

### [Shorm20] Shormann & in het Panhuis (2020) — Performance evaluation of humpback whale-inspired shortboard surfing fins
*PLOS ONE 15(4):e0232035, open access.* [DOI 10.1371/journal.pone.0232035](https://doi.org/10.1371/journal.pone.0232035)
Field study (~2,000 waves, motion sensors): tubercled/serrated CF-composite 3D-printed fins vs
commercial fins; 89% of metrics improved, cutback yaw power +16.4%.
**Cited for:** optional tubercle features; CF-reinforced printing as a manufacturing route;
rotational-power field metrics for later validation.

### [ShormISEA20] Shormann, Oggiano & in het Panhuis (2020) — Numerical CFD Investigation of Shortboard Surfing: Fin Design vs. Cutback Turn Performance
*Proceedings (MDPI) 49(1):132 (ISEA 2020), open access.* [DOI 10.3390/proceedings2020049132](https://doi.org/10.3390/proceedings2020049132)
Dynamic URANS/DES of a thruster set through cutbacks driven by measured roll/pitch/yaw
histories; turn durations 0.55/0.45/0.35 s (intermediate/expert/WCT) at 7 m/s.
**Cited for:** turning as a rider-imparted force balance against fin lift; mapping "surf
style/skill" to turn-rate demand; ~7 m/s design speed for turning loads.

### [Els22] Elshahomi et al. (2022) — Computational fluid dynamics performance evaluation of grooved fins for surfboards
MRS Advances 7, 2022. [doi:10.1557/s43580-022-00311-5](https://doi.org/10.1557/s43580-022-00311-5).
CFX RANS (SST k-ω, 5.6 m/s, angles to 45°) on a thruster template with 6 spanwise
grooves (60 mm long, 6 mm apart) on the outer face: at the 30° stall angle drag
drops 13 ± 1 % and lift 3.8 ± 0.5 % → L/D +11 ± 1 %. Groove depth/width/profile
are not specified in the paper.
**Cited for:** the thinning-groove option (`GrooveParams`); its expected effect
lives at high incidence, not in the linear range.

### [For24] Forsyth et al. (2024) — Grooved fins field study (Sci Rep / PMC11021506)
Scientific Reports 14, 2024. [PMC11021506](https://pmc.ncbi.nlm.nih.gov/articles/PMC11021506/).
Field validation of [Els22]: G1 (outer-face grooves) and G2 (both faces) against a
3D-printed control; 4 of 6 surfers ≥10 % faster on G1, larger turn magnitudes, and
bench force–stroke curves showing the grooved blade is measurably more flexible —
the grooves double as flex hinges. Groove band visible in Fig. 1: upper half-span,
channels parallel to the base, running from the leading edge aft (scalloped LE).
**Cited for:** groove placement defaults (band location, count, pitch) and the
flex side-effect noted in `GrooveParams`.

### [Rom21] Romanin et al. (2021) — Surfing equipment and design: a scoping review
*Sports Engineering 24:21.* [DOI 10.1007/s12283-021-00358-x](https://doi.org/10.1007/s12283-021-00358-x)
PRISMA review of 17 studies; fin design is the joint-largest theme, dominated by computational
lift/drag analysis; calls out lack of standardization.
**Cited for:** background; CFD as the field's standard methodology; the standardization gap a
reproducible generator addresses.

---

## 2. Field measurements & operating envelope

### [Forsyth24] Forsyth et al. (2024) — Understanding the relationship between surfing performance and fin design
*Scientific Reports 14:8734, open access.* [DOI 10.1038/s41598-024-58387-y](https://doi.org/10.1038/s41598-024-58387-y) · [PMC copy](https://pmc.ncbi.nlm.nih.gov/articles/PMC11021506/)
Six surfers, GPS/IMU, four fin variants (commercial, printed replica, two grooved prints) over
35 sessions: mean riding speed 6.4 ± 0.1 m/s, top speed 9.7 ± 0.1 m/s; grooved G1 fins improved
turn metrics; printed fins comparable to commercial.
**Cited for:** design speeds (mean 6.4, top ~10 m/s); printed≈commercial equivalence; grooves
as a credible generator feature.

### [Far12] Farley, Harris & Kilding (2012) — Physiological Demands of Competitive Surfing
*J. Strength and Conditioning Research 26(7):1887–1896.* [DOI 10.1519/JSC.0b013e3182392c4b](https://doi.org/10.1519/JSC.0b013e3182392c4b)
GPS study of 12 ranked surfers in competition: average max speed 33.4 ± 6.5 km/h (~9.3 m/s);
wave riding only ~8% of heat time.
**Cited for:** upper bound of the speed envelope; low-speed dominance motivating low-Re checks.

### [Sca03] Scarfe, Elwany, Mead & Black (2003) — The Science of Surfing Waves and Surfing Breaks
*Scripps Institution of Oceanography Technical Report.* [eScholarship](https://escholarship.org/uc/item/6h72j1fz)
Review defining surfing-wave parameters (breaking height H_b, peel angle, intensity, section
length) and the surfer-speed ≥ peel-rate requirement.
**Cited for:** wave-side operating envelope; peel-rate lower bound on design speed.

### [Dro26] Dronkers — Breaker index
*Coastal Wiki (Flanders Marine Institute), accessed 2026-07-24.* [coastalwiki.org/wiki/Breaker_index](https://www.coastalwiki.org/wiki/Breaker_index)
Depth-limited breaking criterion γ_b = H_b/h_b (Miche, Goda) and shallow-water celerity
c = √(gh).
**Cited for:** the wave-height → wave-speed mapping c ≈ √(gH_b/γ_b).

---

## 3. Classical wing theory (lift & drag models)

### [Pra21] Prandtl (1921) — Applications of Modern Hydrodynamics to Aeronautics
*NACA Report 116.* [NTRS 19930091180](https://ntrs.nasa.gov/citations/19930091180)
Lifting-line theory from the source: induced AoA, elliptic loading, C_Di = C_L²/(πAR).
**Cited for:** lifting-line foundations and the induced-drag equation.

### [Jon46] Jones (1946) — Properties of Low-Aspect-Ratio Pointed Wings…
*NACA Report 835.* [NTRS 19930091913](https://ntrs.nasa.gov/citations/19930091913)
Slender-wing theory: C_Lα = (π/2)AR in the AR→0 limit.
**Cited for:** the low-AR limit our lift-slope formula must asymptote to.

### [Pol66] Polhamus (1966) — A Concept of the Vortex Lift of Sharp-Edge Delta Wings…
*NASA TN D-3767.* [NTRS 19670003842](https://ntrs.nasa.gov/citations/19670003842)
Leading-edge-suction analogy: C_L = K_p sinα cos²α + K_v cosα sin²α.
**Cited for:** the nonlinear vortex-lift extension at high AoA / high rake.

### [Pol49] Polhamus (1949) — A Simple Method of Estimating the Subsonic Lift and Damping in Roll of Sweptback Wings
*NACA TN 1862.* [NTRS 19930082534](https://ntrs.nasa.gov/citations/19930082534)
Origin of the closed-form swept-wing lift-curve slope later canonized in DATCOM; reduces to
Helmbold at Λ=0 and to πAR/2 as AR→0. Also the paper's other half: a strip estimate of the
**damping in roll** of a wing.
**Cited for:** the sweep-corrected C_Lα implemented for raked fins; the lift-based roll-damping
derivative L_p in the tier-0 roll model (`fingen.roll`).

### [Die51] Diederich (1951) — A Plan-Form Parameter for Correlating Certain Aerodynamic Characteristics of Swept Wings
*NACA TN 2335.* [NTRS 19930082969](https://ntrs.nasa.gov/citations/19930082969)
Collapse parameter F = A/(κ cosΛ); basis of the Helmbold–Diederich equation.
**Cited for:** the sweep-scaling structure of the lift slope; half-chord sweep absorbing taper.

### [Kuc52] Küchemann (1952/1956) — Span and Chordwise Loading on Straight and Swept Wings of any Given Aspect Ratio
*ARC R&M 2935.* [Cranfield AERADE](https://reports.aerade.cranfield.ac.uk/handle/1826.2/3498)
Source of the swept Helmbold form (a₀ → a₀cosΛ) reproduced in Anderson.
**Cited for:** the minimal sweep correction to Helmbold.

### [DAT78] Hoak & Finck (1978) — USAF Stability and Control DATCOM, §4.1.3.2
*AFFDL, Wright-Patterson AFB.* [Full scan (Datcom+ mirror)](https://www.holycows.net/datcom/Downloads/USAF%20Stability%20and%20Control%20DATCOM.pdf)
The production wing lift-curve-slope equation with sweep, section-slope ratio κ and
compressibility; valid across the fin regime AR 1–3.5, Λ 25–37°.
**Cited for:** the exact C_Lα formula implemented in the fast hydro model.

### [Osw33] Oswald (1933) — General Formulas and Charts for the Calculation of Airplane Performance
*NACA Report 408.* [NTRS 19930091482](https://ntrs.nasa.gov/citations/19930091482)
Introduces the span-efficiency factor e.
**Cited for:** C_Di = C_L²/(π e AR) with non-elliptic planforms.

### [Hem28] Hemke (1928) — Drag of Wings with End Plates
*NACA Report 267.* [NTRS 19930091335](https://ntrs.nasa.gov/citations/19930091335)
Image-system theory of end plates: effective-AR increase vs plate-height/span.
**Cited for:** modeling the board as an end plate / reflection plane at the fin base.

### [And17] Anderson (2017) — Fundamentals of Aerodynamics, 6th ed.
*McGraw-Hill, ISBN 978-1-259-12991-9.*
Ch. 5: lifting line, induced drag, and Helmbold's equation recommended for AR < 4.
**Cited for:** textbook form of Helmbold and the swept (Küchemann) variant.

### [Hoe75] Hoerner & Borst (1975) — Fluid-Dynamic Lift, 2nd ed.
*Hoerner Fluid Dynamics.* [Internet Archive scan](https://archive.org/details/FluidDynamicLiftHoerner1985)
Empirical compendium: low-AR nonlinear (sin²α cross-flow) lift, end-plate factor
(1 + 1.9 h/b), reflection-plane doubling for a fin on a wall, and bluff-plate normal-force
(drag) coefficients.
**Cited for:** effective-AR treatment and the empirical nonlinear lift term; the flat-plate
normal-force coefficient C_d ≈ 1.1 in the zero-speed roll-drag form (`fingen.roll`).

### [Tra23] Traub (2023) — Lift Components of Low Aspect Ratio Rectangular Flat Plate Wings
*Aerospace 10(7):597, open access.* [DOI 10.3390/aerospace10070597](https://doi.org/10.3390/aerospace10070597)
AR 0.5–3 flat-plate data decomposition: potential + side-edge vortical lift; cautions against
crediting leading-edge vortex lift on unswept planforms; low Re-sensitivity.
**Cited for:** modern calibration/validation of the low-AR lift model in exactly the fin's AR range.

---

## 4. Foil sections at low Reynolds number

### [Jac33] Jacobs, Ward & Pinkerton (1933) — The Characteristics of 78 Related Airfoil Sections…
*NACA Report 460.* [NTRS 19930091108](https://ntrs.nasa.gov/citations/19930091108)
The original NACA 4-digit definition: thickness polynomial and two-parabola camber line.
**Cited for:** the exact section equations implemented in `foil.py`.

### [AvD59] Abbott & von Doenhoff (1959) — Theory of Wing Sections
*Dover, 704 pp.* [Google Books record](https://books.google.com/books/about/Theory_of_Wing_Sections.html?id=lWe8AQAAQBAJ)
Complete NACA construction: thickness ⊥ camber line, r_LE = 1.1019 (t/c)²·c, plus tabulated
section data.
**Cited for:** section-construction conventions and baseline section characteristics.

### [Dre89] Drela (1989) — XFOIL: An Analysis and Design System for Low Reynolds Number Airfoils
*Low Reynolds Number Aerodynamics, LNE 54, Springer.* [DOI 10.1007/978-3-642-84010-4_1](https://doi.org/10.1007/978-3-642-84010-4_1)
Panel method + integral boundary layer + e^N transition; built for transitional separation
bubbles — exactly the fin's Re regime.
**Cited for:** the section-polar engine and its validity envelope.

### [SK81] Sheldahl & Klimas (1981) — Aerodynamic Characteristics of Seven Symmetrical Airfoil Sections…
*Sandia SAND80-2114.* [OSTI 6548367](https://www.osti.gov/biblio/6548367)
NACA 0009–0025 tabulated C_l/C_d/C_m, Re 10⁴–10⁷, α −180°…+180°.
**Cited for:** symmetric-section polar lookup tables including post-stall.

### [Sel95] Selig et al. (1995) — Summary of Low-Speed Airfoil Data, Vol. 1
*SoarTech (UIUC LSATs).* [UIUC PDF](https://m-selig.ae.illinois.edu/uiuc_lsat/Low-Speed-Airfoil-Data-V1.pdf)
Wind-tunnel polars for 34 airfoils at Re 3×10⁴–5×10⁵; large low-Re performance degradation.
**Cited for:** low-Re validation data; Re-dependence motivating speed-dependent section choice.

### [Win18] Winslow et al. (2018) — Basic Understanding of Airfoil Characteristics at Low Reynolds Numbers
*J. Aircraft 55(3):1050–1061.* [DOI 10.2514/1.C034415](https://doi.org/10.2514/1.C034415)
(AIAA page blocks bots; verified via DOI record + [ResearchGate copy](https://www.researchgate.net/publication/321835620).)
Laminar separation degrades thick conventional sections at Re 10⁴–10⁵; thin/cambered plates
can win at the lowest Re.
**Cited for:** thickness/camber decisions at the slow end of the envelope.

### [Ren26] Ren et al. (2026) — Laminar separation bubble dynamics and aerodynamic optimization of low-Re airfoils
*Frontiers in Mechanical Engineering, mini-review, open access.* [DOI 10.3389/fmech.2026.1850561](https://doi.org/10.3389/fmech.2026.1850561)
Organizes low-Re section design around LSB control; surveys transition-aware CFD and
surrogate optimization as current best practice.
**Cited for:** transition-aware CFD in the optimization loop; LSB as governing physics.

---

## 5. Free surface: ventilation & cavitation (spin-out)

### [You17] Young, Harwood, Miguel Montero, Ward & Ceccio (2017) — Ventilation of Lifting Bodies: Review
*Applied Mechanics Reviews 69(1):010801.* [DOI 10.1115/1.4035360](https://doi.org/10.1115/1.4035360)
The authoritative review: flow regimes, transition mechanisms, Froude/Weber/cavitation scaling.
**Cited for:** spin-out modeled as ventilation; depth-Froude number Fr_h = U/√(gh) as the
governing similarity parameter.

### [Har16] Harwood, Young & Ceccio (2016) — Ventilated cavities on a surface-piercing hydrofoil…
*J. Fluid Mechanics 800:5–56.* [DOI 10.1017/jfm.2016.373](https://doi.org/10.1017/jfm.2016.373)
Towing-tank experiments at immersed AR = 1.0 (fin-like): ventilation requires separated
sub-atmospheric flow **and** an air path; hysteresis between wetted/ventilated states.
**Cited for:** the two-condition inception criterion behind the spin-out heuristic; closest
validation dataset for fin CFD.

### [Swa74] Swales, Wright, McGregor & Rothblum (1974) — The Mechanism of Ventilation Inception on Surface Piercing Foils
*J. Mechanical Engineering Science 16(1):18–24.* [DOI 10.1243/JMES_JOUR_1974_016_005_02](https://doi.org/10.1243/JMES_JOUR_1974_016_005_02)
Separation or cavitation is necessary but not sufficient; the free-surface "seal" must also
rupture (three rupture modes).
**Cited for:** the necessary-condition logic: attached, above-vapor-pressure sections are
ventilation-resistant.

### [BS59] Breslin & Skalak (1959) — Exploratory Study of Ventilated Flows About Yawed Surface-Piercing Struts
*NASA Memo 2-23-59W.* [NTRS 19980228299](https://ntrs.nasa.gov/citations/19980228299)
Classic strut experiments: natural ventilation develops post-stall (α ≳ 20°); surface
disturbances trigger it earlier.
**Cited for:** spin-out risk growing with AoA; stall margin as the ventilation guard.

### [AF26] Aguiar Ferreira et al. (2026) — On the ventilation of surface-piercing hydrofoils under steady-state conditions
*J. Fluid Mechanics 1028:A25, open access.* [DOI 10.1017/jfm.2026.11126](https://doi.org/10.1017/jfm.2026.11126)
Delft towing tank, AR_h 1.0/1.5, Fr_h 0.5–2.5: nose ventilation at low Fr_h, tail ventilation
(inception angle decreasing with speed) at high Fr_h; bistable region larger than previously mapped.
**Cited for:** speed-dependent ventilation margins; avoiding ogive-like base sections.

### [Das00] Daskovsky (2000) — The hydrofoil in surface proximity, theory and experiment
*Ocean Engineering 27(10):1129–1159.* [DOI 10.1016/S0029-8018(99)00032-3](https://doi.org/10.1016/S0029-8018(99)00032-3)
Lift loss vs submergence: significant below h/c ≈ 2, severe below h/c ≈ 1.
**Cited for:** free-surface lift de-rating near the fin tip/base region.

### [Bre95] Brennen (1995) — Cavitation and Bubble Dynamics, Ch. 1
*Oxford UP; open-access Caltech edition.* [CaltechBOOK 1995.001](https://media.library.caltech.edu/CaltechBOOK:1995.001/chap1.htm)
σ = (p_∞ − p_v)/(½ρU²); ideal inception at σ_i = −C_p,min.
**Cited for:** the cavitation-inception diagnostic (marginal below ~10–15 m/s at fin depths).

### [Tag26] Taghinia & Esmaeili (2026) — CFD Analysis of Cavitating Hydrofoils Near the Sea Surface…
*J. Applied Fluid Mechanics 19(2):76–91, open access.* [DOI 10.47176/jafm.19.2.3703](https://doi.org/10.47176/jafm.19.2.3703)
VOF + Schnerr–Sauer study of near-surface foils: shallow submergence lowers C_L and C_D.
**Cited for:** two-phase methodology for eventual free-surface CFD; near-surface de-rating.

---

## 6. Turning dynamics & sizing methodology

### [LE14] Larsson & Eliasson (2014) — Principles of Yacht Design, 4th ed.
*McGraw-Hill/Adlard Coles, ISBN 9780071823739.* [Google Books record](https://books.google.com/books/about/Principles_of_Yacht_Design.html?id=kQhPAgAAQBAJ)
Ch. 6 (Keel and Rudder Design): sizing lifting appendages from required side force,
A = F/(½ρv²C_L) with AR/sweep-corrected lift slope.
**Cited for:** the sizing-module methodology — this is standard naval-architecture practice.

### [SH-turn] SurfHydrodynamics.com — Physics of the turn in surfing *(grey literature)*
[surfhydrodynamics.com/en/viragesurf.html](https://www.surfhydrodynamics.com/en/viragesurf.html), accessed 2026-07-24.
Coordinated-turn model: F = Mv²/R, L_h = Mg·tanφ, R = v²/(g·tanφ).
**Cited for:** explicit statement of the turning closure. Non-peer-reviewed — always pair with
[ShormISEA20] and [Falk19] for the peer-reviewed force-balance picture.

---

## 7. Curve & surface math (CAGD)

### [PT97] Piegl & Tiller (1997) — The NURBS Book, 2nd ed.
*Springer, ISBN 3-540-61545-8.* [DOI 10.1007/978-3-642-59223-2](https://doi.org/10.1007/978-3-642-59223-2)
Bernstein/Bézier, B-splines, de Casteljau/de Boor, and the Ch. 10 skinning (lofting) algorithm
that OCCT implements.
**Cited for:** the outline curve math and the loft's underlying NURBS representation.

### [Far02] Farin (2002) — Curves and Surfaces for CAGD, 5th ed.
*Morgan Kaufmann, ISBN 978-1-55860-737-8.* [ScienceDirect book record](https://www.sciencedirect.com/book/9781558607378/curves-and-surfaces-for-cagd)
Endpoint interpolation/tangency, convex-hull and variation-diminishing properties.
**Cited for:** why Bézier control points are well-behaved user-facing design parameters.

### [Jai17] Jaiswal (2017) — Shape Parameterization of Airfoil Shapes Using Bezier Curves
*I-DAD 2016, LNME, Springer, pp. 79–85.* [DOI 10.1007/978-981-10-1771-1_13](https://doi.org/10.1007/978-981-10-1771-1_13)
Degree-6 Bézier reproduces airfoils accurately; degree 4 insufficient, degree 8 no gain.
**Cited for:** the choice of low-order (≈6) Bézier curves for sections/outlines.

### [Kul08] Kulfan (2008) — Universal Parametric Geometry Representation Method
*J. Aircraft 45(1):142–158.* [DOI 10.2514/1.29958](https://doi.org/10.2514/1.29958)
CST: class function × Bernstein shape function; <10 coefficients per surface to wind-tunnel
tolerance.
**Cited for:** Bernstein-basis parameters as the aerodynamic-community-standard design variables.

### [PT02] Piegl & Tiller (2002) — Surface skinning revisited
*The Visual Computer 18:273–283.* [DOI 10.1007/s003710100156](https://doi.org/10.1007/s003710100156)
Failure modes of B-spline skinning with incompatible section knot vectors.
**Cited for:** building all spanwise sections with identical degree/knot structure before lofting.

---

## 8. Structures & 3D printing

### [GT97] Gere & Timoshenko (1997) — Mechanics of Materials, 4th ed.
*PWS, ISBN 0534934293.* [Internet Archive](https://archive.org/details/mechanicsofmater00gere)
Euler–Bernoulli bending: σ = My/I, tapered cantilever deflection by integrating M/(EI).
**Cited for:** the structural model of the fin as a tapered cantilever.

### [Roa01] Young & Budynas (2001) — Roark's Formulas for Stress and Strain, 7th ed.
*McGraw-Hill, ISBN 9780071501811.* [Google Books record](https://books.google.com/books/about/Roark_s_Formulas_for_Stress_and_Strain.html?id=pummClLoFXEC)
Tabulated cantilever and tapered-beam formulas.
**Cited for:** closed-form cross-checks of the numerical structural model.

### [BAH96] Bisplinghoff, Ashley & Halfman (1955/1996) — Aeroelasticity
*Addison-Wesley 1955; corrected Dover republication 1996, 880 pp., ISBN 978-0-486-69189-3.*
[AbeBooks ISBN record](https://www.abebooks.com/9780486691893/Aeroelasticity-Dover-Books-Aeronautical-Engineering-0486691896/plp)
The classical aeroelasticity text: static aeroelastic phenomena (torsional divergence of a
uniform cantilever wing, q_D = (π/2s)²·GJ/(c²e′a), and its strip-theory generalizations),
swept-wing bending–incidence coupling (washout ∝ −θ·sinΛ), thin-section torsion, and the 2D
incompressible apparent (added) mass πρb² of a plate of semichord b.
**Cited for:** the tier-0 flex module — the strip divergence estimate, the rake bend-twist
coupling, the solid-thin-section torsion constant, and the flat-plate added mass in the
wet-frequency Rayleigh quotient.

### [Zar14] Zarruk, Brandner, Pearce & Phillips (2014) — Steady fluid-structure interaction of flexible hydrofoils
*J. Fluids and Structures 51:326–343.* [DOI 10.1016/j.jfluidstructs.2014.09.009](https://doi.org/10.1016/j.jfluidstructs.2014.09.009)
Tapered NACA0009 cantilever hydrofoils (metal + CFRP): tip deflection/twist vs load; layup
orientation causes bend-twist coupling.
**Cited for:** validating the cantilever model for foil-sectioned fins; anisotropic stiffness
as a directional knockdown.

### [Ahn02] Ahn, Montero, Odell, Roundy & Wright (2002) — Anisotropic material properties of FDM ABS
*Rapid Prototyping Journal 8(4):248–257.* [DOI 10.1108/13552540210441166](https://doi.org/10.1108/13552540210441166)
Foundational FDM anisotropy study: strength strongly dependent on raster/layer orientation.
**Cited for:** print-orientation constraints (layer planes aligned with spanwise bending stress).

### [Fis23] Fisher, Almeida, Falzon & Kazanci (2023) — Tension and Compression Properties of 3D-Printed Composites
*Polymers 15(7):1708, open access.* [DOI 10.3390/polym15071708](https://doi.org/10.3390/polym15071708) · [PMC copy](https://pmc.ncbi.nlm.nih.gov/articles/PMC10096896/)
Short-CF nylon: roughly factor-2 modulus difference across print orientations.
**Cited for:** orientation-appropriate modulus (not datasheet-longitudinal) in E·I calculations.

### [FibPET26] Polymaker — Fiberon PET-CF17 Technical Data Sheet V1.0
[TDS PDF](https://3d.nice-cdn.com/upload/file/TDS_FIBERON-PET-CF17_V1.0_EN.pdf), accessed 2026-07-26
(text-extracted from the official PDF). The user's actual print filament (17 wt% carbon-fiber
PET). Full ISO-method table, all values for specimens **annealed 120 °C / 10 h** (stated on the
TDS): ISO 178 bending modulus XY 4744.4 ± 136.3 MPa / Z 2768.2 ± 422.6 MPa; bending strength XY
109.3 ± 2.0 / Z 43.4 ± 8.8 MPa; ISO 527 tensile (Young's) modulus XY 5481.0 ± 223.7 / Z 3558.8 ±
260.4 MPa; tensile strength XY 65.9 ± 1.0 / Z 27.9 ± 1.3 MPa; ISO 1183 density 1.34 g/cm³ at
23 °C; Tg 79.3 °C; HDT 105 °C @1.8 MPa / 147.5 °C @0.45 MPa; equilibrium water absorption ≈0.53%
at 70% RH (low uptake → near-indifferent to humid/seawater service).
**Cited for:** the PRIMARY `pet-cf` material card in `fingen.materials` (e_mpa = XY bending
modulus 4744 MPa) and the derived sizing allowable in `fingen.sizing`
(`_MATERIAL_ALLOW_MPA["pet-cf"]` = 109.3 · 0.5 / 2 = 27.325 MPa). Datasheet numbers are the
annealed ceiling; the load-cell rig measures the real as-printed/annealed state.

### [PETCF] Bambu Lab (2023) — Technical Data Sheet V3.0 — PET-CF
[TDS PDF](https://wiki.bambulab.com/filament-acc/petcf-ppacf/07689de83afd4cc480f136c7697e6de3.pdf)
(official server requires a browser user agent; re-pulled and text-extracted 2026-07-26).
ISO 178 bending modulus XY 5320 ± 270 MPa / Z 2210 ± 180 MPa; bending strength XY 131 ± 6 /
Z 49 ± 5 MPa; ISO 527 tensile modulus XY 4730 ± 260 / Z 2160 ± 170 MPa; tensile strength XY
74 ± 6 / Z 35 ± 5 MPa; density 1.29 g/cm³. Specimens annealed/dried 80 °C / 12 h.
**Cited for:** the secondary `bambu-pet-cf` comparison card in `fingen.materials` and the ~2.4×
XY/Z anisotropy; no longer the `pet-cf` default (superseded by [FibPET26], the user's filament).

### [PAHTCF] Bambu Lab (2023) — Technical Data Sheet V3.0 — PAHT-CF
[TDS PDF](https://wiki.bambulab.com/filament-acc/asacf-pahtcf/65f1b18a6d6142d794a1a6a00f1496ef.pdf)
(official server requires a browser user agent; re-pulled and text-extracted 2026-07-26).
ISO 178 bending modulus XY 4230 ± 210 MPa / Z 1820 ± 170 MPa; bending strength XY 125 ± 7 /
Z 61 ± 5 MPa; ISO 527 tensile modulus XY 3860 ± 230 / Z 2180 ± 130 MPa; tensile strength XY
92 ± 7 / Z 47 ± 5 MPa; Charpy XY 57.5 kJ/m² (unnotched); density 1.06 g/cm³ (PA12+CF); retains
properties when wet.
**Cited for:** the `bambu-paht-cf` comparison card in `fingen.materials` AND the structural
analog behind the approximated Elegoo `paht-cf` card (same PA12+CF class) — its X-Y/Z modulus
and strength ratios fill Elegoo's Z-direction gaps. Also anchors the retained paht-cf sizing
allowable (125 · 0.5 / 2 = 31.25 MPa).

### [ELPAHT26] Elegoo — PAHT-CF (PA12 Carbon Fiber) filament, published specifications
[Product page](https://us.elegoo.com/products/paht-cf-filament-1-75mm-colored-1kg) and the
[filamentdb aggregation](https://www.filamentdb.app/filament/elegoo/paht-cf-carbon-fiber),
accessed 2026-07-26. The user's actual PAHT-CF filament; no thorough TDS is published. Only a
few X-Y, dry values are given: flexural modulus 5089 MPa, flexural strength 138 MPa, tensile
strength 87 MPa, elongation at break 14.2%, unnotched Charpy 70.4 kJ/m²; base polymer PA12-CF.
No Z-direction data, no density, no test standard stated.
**Cited for:** the PRIMARY `paht-cf` material card in `fingen.materials`, built as an
`"approximated"` card — Elegoo's own X-Y numbers plus Bambu-analog [PAHTCF] fill and a PA12
wet-conditioning derate [3DXPA]; see that card's `derivation` field for the exact split and
uncertainty. Test G (docs/BENCH-PROTOCOL.md) is decision-grade for this card.

### [3DXPA] 3DXTech — PA6-CF vs. PA12-CF Carbon Fiber Nylon comparison *(grey literature)*
[3dxtech.com/blogs/featured/pa6-cf-vs-pa12-cf-carbon-fiber-nylon-comparison](https://www.3dxtech.com/blogs/featured/pa6-cf-vs-pa12-cf-carbon-fiber-nylon-comparison),
accessed 2026-07-26. Compares moisture behaviour: PA6 absorbs 3-9% water and its stiffness drops
in humid environments (a companion figure gives PA6-CF flexural modulus ~7453 MPa dry vs
~5666 MPa conditioned, ≈24% loss), whereas PA12-CF absorbs <1% and "maintains its stiffness
regardless of ambient humidity."
**Cited for:** the PA12-CF conditioned/wet modulus retention (~0.85, band ~10-20%) applied to
the Elegoo `paht-cf` card and its sizing allowable — the honest, material-appropriate knockdown
(NOT the PA6/66 30-50% figure). Non-peer-reviewed vendor material; the load-cell rig's Test G
supersedes it.

### [PLA] Bambu Lab — Technical Data Sheet V3.0 — PLA Basic
[TDS PDF](https://store.bblcdn.com/s1/default/58b85d0f3db94878854a28fdb8a0006e/Bambu_PLA_Basic_Technical_Data_Sheet.pdf),
accessed 2026-07-26 (text-extracted from the official PDF). ISO 178 bending modulus XY 2750 ± 160
MPa / Z 2370 ± 150 MPa; bending strength XY 76 ± 5 / Z 59 ± 6 MPa; ISO 527 tensile modulus XY
2580 ± 220 / Z 2060 ± 170 MPa; tensile strength XY 35 ± 4 / Z 31 ± 3 MPa; density 1.24 g/cm³.
**Cited for:** the generic `pla` low-stiffness reference card in `fingen.materials` — NOT a
seawater candidate, kept only for card wiring and filament comparison.

### [Gat17] Gately et al. (2017) — Additive Manufacturing, Modeling and Performance Evaluation of 3D Printed Fins
*MRS Advances 2(16):913–920.* [DOI 10.1557/adv.2017.107](https://doi.org/10.1557/adv.2017.107)
Printed ABS/CF/GF/PEI fins: mechanically comparable to commercial fins; similar on-water
performance.
**Cited for:** the project premise (printed ≈ commercial) and CFD+print coupling precedent.

### [Nov21] Novak (2021) — A Parametric Method to Customize Surfboard and SUP Fins for Additive Manufacturing
*Computer-Aided Design & Applications 18(2):297–308, open access.* [PDF](https://cad-journal.net/files/vol_18/CAD_18(2)_2021_297-308.pdf) · DOI 10.14733/cadaps.2021.297-308
Grasshopper parametric fin system with ~10 user-facing parameters; two fins printed and
water-trialled.
**Cited for:** direct precedent for the parametric-interface design; FFF viability.

### [NN21] Novak & Novak (2021) — Is additive manufacturing improving performance in Sports? A systematic review
*Proc. IMechE Part P 235(3):163–175.* [DOI 10.1177/1754337120971521](https://doi.org/10.1177/1754337120971521) · [UTS OPUS copy](https://opus.lib.uts.edu.au/bitstream/10453/144564/2/AMSportsSystematicReview-Final.pdf)
26 studies: AM products improved (38%) or matched (31%) conventional equipment.
**Cited for:** background on AM sporting-goods evidence, surfing included.

### [Krz22] Krzyzanowski & in het Panhuis (2022) — A 3D-printed instrumented surfboard fin for measuring fin flex
*MRS Advances 7:175–179.* [DOI 10.1557/s43580-021-00191-1](https://doi.org/10.1557/s43580-021-00191-1)
Strain-gauge-instrumented printed fins; linear response to 7.7% fin flex.
**Cited for:** fin-flex percentage as the deflection metric; bench load method.

### [Krz24] Krzyzanowski & in het Panhuis (2024) — Measuring the flex in surfboard fins during surfing
*MRS Advances 9:499–504.* [DOI 10.1557/s43580-024-00795-3](https://doi.org/10.1557/s43580-024-00795-3)
First in-ocean fin-flex measurements: up to ~10% flex at ~6 m/s, 8–9% in turns vs 2–3%
paddling; associated lab stiffness 3.6 N/mm, ~310 N per fin in turns.
**Cited for:** in-service deflection targets and the stiffness envelope for printed fins.

---

## 9. Industry references (grey literature)

### [FCS26] FCS Fin Data — official specification tables
[surffcs.com/pages/fcs-fin-data](https://www.surffcs.com/pages/fcs-fin-data), accessed 2026-07-24.
Base, depth, area, sweep and foil type for the full FCS range. Example — Reactor Medium side
fin: base 110 mm, depth 115 mm, area 9824 mm², sweep 32.0°, flat foil.
**Cited for:** the industry parameter set and validation targets for generated geometry.

### [Fut26] Futures Fins — R3 Legacy Series specifications
[futuresfins.com/products/r3-legacy-series](https://futuresfins.com/products/r3-legacy-series), accessed 2026-07-24.
Per-fin area/height/base/foil specs; flat side foils + 50/50 center convention; Ride Number
system (speed-generating ↔ speed-control).
**Cited for:** thruster template conventions; rake/style family framing.

### [Gre26] Greenlight Surf Co. — Surfboard Fin Position and Design guide
[greenlightsurfsupply.com](https://greenlightsurfsupply.com/pages/surfboard-fin-design-greenlight-surfboard-design-guide), accessed 2026-07-24.
Production installation conventions: thruster fronts 1/4" toe, 7–9° cant (≈5° big-wave);
quad rears 1/8–3/16" toe, 3–5° cant; keels 0°.
**Cited for:** default toe/cant placement values and their drive/pivot trade-offs.
