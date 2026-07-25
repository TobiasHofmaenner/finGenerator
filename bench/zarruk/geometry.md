# Zarruk et al. (2014) hydrofoil — geometry & experimental setup spec for CFD replication

Source: author-accepted manuscript of Zarruk, G.A., Brandner, P.A., Pearce, B.W., Phillips, A.W.
(2014), "Experimental study of the steady fluid–structure interaction of flexible hydrofoils",
J. Fluids and Structures 51:326–343. Local file: `zarruk2014-original.pdf` (29-page preprint,
dated 1 Sep 2014). Page numbers below refer to this preprint's printed page numbers
(= PDF page numbers).

## 1. Planform (all six models identical)

| Quantity | Value | Source |
|---|---|---|
| Planform | upright/unswept trapezoidal | p.4, Sec. 2.2 |
| Span s | 0.300 m | p.4 |
| Root ("base") chord | 0.120 m | p.4 |
| Tip chord | 0.060 m | p.4 |
| Taper ratio | 0.5 (derived from 60/120) | derived |
| Mean chord c | 0.090 m (used for Re_c and coefficient normalization) | p.11, Sec. 2.5 |
| Aspect ratio | 3.33 (paper's stated value; = s/c = 0.3/0.09) | abstract, p.4 |
| Sweep | none ("unswept geometry was deliberately chosen") | p.4 |
| Twist / camber | none stated; symmetric sections, straight foil | Sec. 2.2 |
| Planform area | 0.027 m^2 (s×c, implied by blockage ratio 0.075 of 0.36 m^2) | p.11–12 |

Note the paper reports AR = 3.33, i.e. s/c_mean (semi-span aspect ratio of the cantilevered
foil). Geometric full-foil aspect ratio if mirrored at the root would be 6.67.

## 2. Section profiles

### Type I — standard NACA0009
Thickness distribution (standard NACA 4-digit, Eq. 1, p.4):

  y = 5 t (0.2969 x^0.5 − 0.126 x − 0.3516 x^2 + 0.2843 x^3 − 0.1015 x^4)

with t = 0.09 (9% thickness-to-chord), x = chordwise coordinate /c. This is the classic
open-TE NACA equation; TE half-gap 0.2%c → total TE thickness ~0.2%c per the paper's
statement (p.5: modification increases TE thickness "from 0.2% to 1.3%c").

### Type II — modified NACA0009 (thicker TE for CFRP manufacture)
Identical except the LAST coefficient of the polynomial (Eq. 2, p.4):

  y = 5 t (0.2969 x^0.5 − 0.126 x − 0.3516 x^2 + 0.2843 x^3 − 0.08890 x^4)

Effect (p.5 & Fig. 3, p.6): thickness increases gradually from ~mid-chord aft, raising the
trailing-edge thickness from 0.2%c (Type I) to 1.3%c (Type II). Everything else (planform,
t/c=0.09) identical.

## 3. Models tested

| Model | Section | Material | Notes | Source |
|---|---|---|---|---|
| Type I - SS | NACA0009 | Stainless steel 316L | machined from solid billet, integral mounting flange | p.4 |
| Type I - AL | NACA0009 | Aluminum 6061-T6, anodized ~5 um | same | p.4 |
| Type II - SS | mod. NACA0009 | SS 316L | extended base clamped in housing | p.5 |
| Type II - AL | mod. NACA0009 | AL 6061-T6 | same | p.5 |
| Type II - CFRP00 | mod. NACA0009 | carbon/glass-epoxy hybrid, UD carbon at 0 deg | RTM molded | p.5–6 |
| Type II - CFRP30 | mod. NACA0009 | UD carbon at 30 deg (offset toward LE) | p.6–7 |

Manufacturing tolerance: ±0.1 mm on surface, 0.8 um surface finish; NO added roughness /
turbulence stimulation (p.5).

## 4. Structural properties (Table 2, p.10) — needed to convert dimensionless deflections

| Property | I-SS | II-SS | I-AL | II-AL | CFRP00 | CFRP30 |
|---|---|---|---|---|---|---|
| K (N/mm), tip load at c/4 | 61.7 | 60.2 | 23 | 22.1 | 20.0 | 8.2 |
| E (GPa) | 193 | 193 | 71 | 71 | 65 | 26 |
| I (mm^4), base section | 5956 | 6148 | 5956 | 6350 | 6148 | 6148 |
| J (10^3 mm^4) | 860.4 | 854.5 | 860.4 | 854.7 | 854.5 | 854.5 |
| rho_H (kg/m^3) | 7900 | 7900 | 2700 | 2700 | 1600 | 1600 |
| f_n air (Hz) | 100 | 96 | 100 | 96 | 112 | 72 |
| f_n water (Hz) | 62 | 61 | 42 | 41 | 41 | 26 |

G used for twist normalization (p.24–25): CFRP00 22 GPa, CFRP30 9 GPa (estimated, "merely
for comparison purposes").

## 5. Mounting & tunnel installation (critical for CFD domain)

- Facility: Cavitation Research Laboratory variable-pressure water tunnel, University of
  Tasmania (AMC). Test section 0.6 m square × 2.6 m long (p.3).
- Foil cantilevered VERTICALLY from the tunnel CEILING through a 0.16 m dia penetration,
  mounted on a six-component force balance (p.10, Sec. 2.5; Figs. 1–2, p.5).
- Fairing disk: the 0.16 m penetration is faired (to 50 um) by a disk mounted ON THE FOIL
  (measurement side of the balance) with nominal 0.5 mm radial clearance — i.e. the root
  boundary is a disk flush with the ceiling, gap 0.5 mm (p.10–11).
- Root boundary condition: cantilever; Type I via integral flange; Type II clamped between
  profiled plates in a housing (p.4–5, Figs. 1–2).
- Foil positions tested: 0.7 m and 1.3 m from test-section entrance (Type I); Type II at
  0.7 m only. Ceiling boundary-layer thickness (99% U) ~19 mm at 0.7 m and ~26 mm at 1.3 m;
  effect of this difference on lift < 1% (p.11).
- Span = half the 0.6 m test-section dimension: tip gap to floor = 0.3 m.

## 6. Flow conditions

- Velocity range 2–12 m/s, absolute pressure 4–400 kPa capability (p.3); tests pressurized
  to 200 kPa to suppress cavitation (p.11).
- Re_c = U c/nu with c = 0.09 m; tested Re_c = 0.2, 0.4, 0.6, 0.8, 1.0 ×10^6 (p.11)
  → U ≈ 2.2, 4.4, 6.7, 8.9, 11.1 m/s for 15 C water.
- Incidence: 0.5 deg steps; up to 15 deg (beyond stall) for Re_c ≤ 0.6e6; limited to 9 deg
  (0.8e6) and 6 deg (1.0e6) by the 1 kN load limit for Type I (p.11); Fig. 9 shows Type II
  0.8e6 data to 10 deg. Hysteresis loops ±15 deg at 0.6e6 (Figs. 12–13).
- Incidence accuracy: absolute < 0.1 deg; incremental precision < 0.001 deg; 0.05 deg
  backlash correction applied in hysteresis tests (p.11).
- Freestream turbulence intensity ~0.5%; velocity spatially uniform to ±0.5%, temporal
  variation < 0.2% (p.3–4, Sec. 2.1).
- Velocity measurement precision: 0.007 / 0.018 m/s (low/high-range transducer) (p.3).
- Water: demineralized, conductivity ~1 uS/cm; tunnel volume 365 m^3 (p.3).

## 7. Corrections applied by the authors (i.e. data are RAW w.r.t. confinement)

- NO confinement/blockage corrections applied: "On this basis no confinement corrections
  have been applied to the present results" (p.4). Blockage ratio (planform area / tunnel
  cross-section) = 0.075; effect "expected to be negligible" citing Mueller & Batill (1982)
  and Hackett et al. (2000) (p.11–12).
- Consequence for CFD: replicate IN-TUNNEL (0.6×0.6×2.6 m section, foil at 0.7 m from
  entrance, ceiling BL 19 mm, fairing disk root) or accept confinement differences.
  The authors themselves note "Computational models will also be developed with the same
  flow domain as for the experiments" (p.4).
- Transition: no roughness/tripping; smooth model; laminar-flow effects present at
  Re_c ≤ 0.6e6 (Re-dependence of forces), forces Re-independent for 0.8e6 and above
  (abstract; p.12). CFD should consider transition modeling at the lower Re.

## 8. Force / moment / deflection measurement chain

- Six-component force balance, calibration precision < 0.5% on all components (p.11).
- Sampling 1 kHz, 10–30 s (similar number of chord passages at each Re) (p.11).
- Coefficients (p.12): CL = 2L/(rho U^2 s c); CD = 2D/(rho U^2 s c); CM = 2M/(rho U^2 s c^2);
  CN, CA analogous (body axes). Moment origin: MID-CHORD; flow-fixed or body-fixed axes.
- Unsteady content pre-stall: RMS of normal force < 1.4% of mean up to stall; post-stall up
  to 6.4% (SS/AL) (p.13); no hysteresis pre-stall (Figs. 12–13).
- Tip deflection: image cross-correlation of tip photographs (Canon EOS 50D, 4752×3168 px),
  calibrated by known tip chord; targets near LE/TE of tip face; measured for all Re at
  2–10 deg in 2 deg steps; uncertainty worst 13% (alpha=2, Re=0.2e6), best 2% (alpha=6,
  Re=1.0e6), average 3.2% (p.11).
- Stall: nominally 10.5 deg for metal foils at all Re tested (p.12).

## 9. Key steady-FSI results for the metal foils (validation targets)

- Forces of SS vs AL foils "compare closely for all Re_c and alpha" → deformation has
  little effect on forces for metal foils (p.12).
- Max tip deflection at Re=1.0e6, alpha=6: Type I: SS 4.9 mm / AL 13.4 mm; Type II: SS
  5.0 mm / AL 12.5 mm (p.15). No resolvable twist for SS/AL (p.15).
- Dimensionless deflection delta' = delta*E*I/(F_N s^3): Type I: SS mean 0.204, AL 0.202,
  independent of alpha and Re_c (Fig. 18 caption, p.23); Type II: SS 0.227, AL 0.219 with
  mild Re dependence converging for Re_c > 0.6e6 (Fig. 19 caption, p.23; p.17).
- CFRP twist (for later FSI work): dimensionless twist theta*G*J/(P s^3) nominally constant;
  CFRP30 twist ~5.7x CFRP00, opposite sign (p.24–25); anchors: at Re=1.0e6, alpha=6:
  CFRP00 +0.6 deg (LE defl 15.4/TE 14.9 mm), CFRP30 −2.2 deg (LE 20.8/TE 22.6 mm)
  (Fig. 17 caption, p.22).
