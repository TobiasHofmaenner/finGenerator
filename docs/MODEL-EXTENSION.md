# Model extension — what a fast method can add (gen-3 step B0)

2026-11-19. Follow-up to [MODEL-REACH.md](MODEL-REACH.md): for every parameter
the tier-0 hydrodynamics cannot see, is there an analytical or numerical method
that is fast enough to run inside the optimizer loop — no CFD in the loop — and
does it agree with the CFD we already have? Probe: `scripts/vlm_probe.py`,
full tables `out/vlm-probe.md`.

## The method that was tested

A vortex lattice in plain numpy: horseshoe vortices on each blade's actual
planform, a mirror image in the board plane (our CFD uses a symmetry plane
there), flow tangency at the panel three-quarter-chord points. Section camber
enters per spanwise strip, so a thinner tip on a flat-inside foil is also a
less cambered one. Blades are placed exactly as `fingen.assembly` places them
(toe, cant, hands), so the same code solves one fin or the whole set, each fin
in the others' wash.

## Evidence

| check | result |
|---|---|
| rectangular wings AR 2 / 4 / 6 | lift slope 2.52 / 3.66 / 4.26 per rad against published ≈ 2.47 / 3.6 / 4.2 |
| isolated lift slope vs CFD | gen-2 side 1.00, gen-1 side 1.02, thin centre 1.13 (tier-0: 0.96 / 1.01 / 1.07) |
| lift at 0° from camber vs CFD | 0.239 vs 0.228 and 0.333 vs 0.325 (tier-0: 0.254, 0.305) |
| set CFD, 12 cases at 5°, per-fin lift | correlation with CFD +0.91 centre, +1.00 inside fin, +0.93 outside fin; level 9–17 % high |
| centre interference factor, baseline | 0.64 vs CFD 0.67 (tier-0: fixed table, 0.72) |
| … with side offset 103 / 118 / 133 mm | 0.60 / 0.64 / 0.68 vs CFD 0.64 / 0.67 / 0.72 — the trend tier-0 cannot have |
| … with the gen-1 sides instead | 0.73 vs CFD 0.76 — interference depends on the side blade |
| toe at which the side pair carries no net force | 3.68° vs CFD 3.65° |
| first-stall consistency | CFD CL_max of both side fins (0.83, 0.96) is reproduced by ONE section cl_max of 1.16 through each fin's own span loading; the thin centre implies 0.75 |
| cost, unoptimised numpy, one core | ≈ 3 ms per blade at 36 panels, ≈ 7 ms for the three-fin set at 60 panels; converged to 1–2 % at that resolution; tier-0 `evaluate` is ≈ 10 ms |

The lattice is inviscid and linear. It matches the thick side foils almost
exactly and over-reads the 4.6 % centre by 13 %; in the set it reads about
10 % high on all fins. Both are the signature of missing section viscosity,
which is what the section tables below supply. At 10° leeway the fin working
against its camber has stalled in the CFD and the linear lattice cannot know.

## What the probe says about the physics

- **Outline shape hardly changes lift or induced drag.** At fixed area and
  depth, a full step of tip width, edge fullness or trailing-edge shape moves
  the lift slope by ≤ 3 % and the span efficiency by ≤ 1.3 %. Tier-0's
  blindness there was costing almost nothing.
- **Outline shape decides where the fin is loaded, hence where and when it
  stalls.** Peak local lift over mean lift runs from 1.28 (wide tip) to 1.50
  (narrow tip), and the peak sits between 67 % and 86 % of span. That is ± 8 %
  on the lift at first stall, and it is the stall progression — tip first and
  gradual, or everywhere at once. This is the hydrodynamic meaning of outline
  shape, and it is what "release" is made of.
- **Rake moves the centre of pressure**, about 12–15 mm per 10°, with almost
  no change in lift.
- **Tip thickness becomes visible**: on the gen-2 side, tip factor 0.6 / 0.78
  / 1.2 gives lift at 0° of 0.220 / 0.239 / 0.284, i.e. it moves the zero-lift
  angle and therefore the toe at which the fin trims.

## Parameter by parameter

| not accounted for today | fast method | what it adds | status |
|---|---|---|---|
| tip width, LE fullness, TE shape, 12 edge offsets | lattice | span loading, first-stall station and lift, CP, true load shape for the flex model | **probed, validated on lift** |
| sweep → CP, stall order | lattice | CP travel; which stations stall first | **probed**; stall softness needs the nonlinear step |
| thickness_tip_factor | lattice with per-strip camber and per-strip section data | zero-lift angle of the whole fin, tip stall | **probed** |
| toe, cant, fin positions; centre interference | lattice on the placed set | geometry-aware interference instead of the fixed Falk table; trim toe; the outside fin | **probed, validated on 48 CFD points** |
| thickness → stall; camber → max lift; nose radius | 2-D section tables cl(α), cd(α) over family, t/c, Reynolds number; microseconds as a lookup | section cl_max and its angle, replacing the AR-only break and the camber guard | method standard; **data source to choose** (below) |
| side-fin drag at the toe angle | same tables at negative incidence | the 8 N per fin tier-0 does not see | same; needs the tables |
| Reynolds number / speed band | same tables | cl_max and drag at the speed floor | same |
| release, post-stall | lattice iterated with the section tables past stall (nonlinear lifting-surface) | lift curve through and beyond the break, per fin | feasible in cost (tens of ms per polar); **accuracy unknown** until compared with high-angle CFD |
| roll damping, yaw damping, the snap's drive phase | lattice with a rotation-rate boundary condition | replaces the strip integral and its wing-calibrated factor; the snap at 200°/s is quasi-steady (reduced frequency ≈ 0.02) | straightforward, not yet probed |
| trailing-edge thickness | Hoerner base-drag formula | ≈ 10 % of profile drag at 0.7 mm on a 70 mm chord, more toward the tip | analytic, instant |
| surface finish | rough-plate friction formula | raw print vs epoxy coat | analytic, instant; a process input, not a design parameter |
| grooves, hydrodynamic side | calibrated delta from the groove A/B CFD (CFD-BENCH item 6) | measured: −1…−3 % lift below the knee, lift −6 % and drag +16 % at the knee, null at 30° | data exists; grooves are flex hinges, not flow devices |

## Section data: three ways to get it

All three are a table lookup inside the loop.

| source | effort | note |
|---|---|---|
| NeuralFoil (PyPI, numpy only) | minutes | a neural surrogate of XFOIL; installing it was blocked by the session's permission rules, needs an explicit go-ahead |
| XFOIL (system package), tables precomputed | hours | the reference low-Reynolds panel code; not installed |
| 2-D RANS on the EPYC, tables precomputed | recipe gate first, then a day of compute | the quasi-2-D recipe exists (`scripts/sk81_naca0012.py`) but reads NACA 0012 lift slope −19 % and CL_max −32 % against [SK81] (±4c domain, wall functions); it needs the wider domain and the resolved wall, and must pass that benchmark before any table is trusted |

## Section data: first results (NeuralFoil, 2026-11-19)

`scripts/section_probe.py`, tables in `out/section-probe.md`. NeuralFoil 0.3.3
run in a throwaway overlay (`uv run --with neuralfoil`); it drags in
aerosandbox and casadi, so it is a table generator, not a runtime dependency.
Boundary layer tripped at 5 % chord, Re 5.7e5 on a 70 mm chord.

| quantity | NeuralFoil | reference |
|---|---|---|
| zero-lift angle, flat-inside t/c 0.09 | −3.4…−3.5° | set CFD −3.50°; water tunnel [BW04] −3.5° on the same section; tier-0 thin-airfoil −4.0° |
| gen-2 side fin going straight, toe 2.5 / 3.5 / 4.5° | 11.2 / 15.2 / 19.2 N | set CFD 11.2 / 13.3 / 16.1 N; tier-0 ≈ 5 N |
| gen-1 side fin, toe 3.5° | 10.7 N | set CFD 11.0 N |
| fin CL_max = section cl_max ÷ lattice peak loading | 0.98 / 1.23 / 0.91 | CFD 0.83 / 0.96 / 0.58 |
| cost | 3 ms per 77-angle polar | – |

**Works:** zero-lift angle and the drag of a flat-inside foil at negative
incidence, in level and in trend with toe. That closes the residual of the
trim-drag fix once the tables exist.

**Undecided:** maximum lift. *(Corrected the same day after re-reading
[CFD-BENCH.md](CFD-BENCH.md): the disagreement below is with our RANS, and the
bench record says the RANS is the soft side — NACA 0012 section CL_max 32 % low
with wall functions against [SK81], and the tunnel's post-knee climb is
transition physics no fully turbulent run reproduces, steady or URANS. So the
truth for the gen-2 side lies somewhere between 0.83 and ≈ 1.0, and neither
tool can referee it.)* The tool says the 9 % flat-inside section
is linear to cl ≈ 1.25 and peaks at 1.40; the 3-D evidence says fins leave the
linear line at a local cl of 0.85–1.0 (our RANS on three fins; the [BW04]
tunnel data on an elliptic fin, linear to CL 0.78 at 12°). The thin symmetric
centre has no defined maximum in the tool at all. NeuralFoil's own confidence
is low on our flat-inside shapes (0.1–0.8 against 0.9+ on conventional
sections), so this is where 2-D RANS has to referee. Note also that [BW04]
measured lift still RISING to 1.10 at 24° where our steady RANS replica of the
same fin flattens at 0.86: steady RANS is not a safe referee past the knee.

### The flat inside face is the drag

Same thickness, same Reynolds number, own incidence −3.5° (going straight at
3.5° toe), side-fin area 9734 mm²:

| inside-face foil | zero-lift angle | drag per side fin going straight | lift as the outside fin at 5° leeway (cl at −8.5°) | lift as the inside fin at 5° / 10° leeway | section cl_max | tool confidence |
|---|---|---|---|---|---|---|
| flat inside (every side fin we have made) | −3.4° | 15.2 N (CFD: 13.3) | −0.33 | 0.59 / 1.14 | 1.40 | 0.1–0.8 |
| conventional camber 3 % at 40 %, round nose | −3.1° | 4.5 N | −0.60 | 0.52 / 1.07 | 1.47 | 0.9–1.0 |
| conventional camber 2 % | −2.1° | 4.4 N | −0.71 | 0.40 / 0.96 | 1.39 | 0.8–1.0 |
| symmetric | 0° | 4.5 N | −0.93 | 0.17 / 0.73 | 1.14 | 0.6–1.0 |

A flat-inside foil has its low-drag range centred at +2° of its own incidence
and runs at −3.5° when toed in: the flow has to turn the sharp inside corner of
the leading edge. A conventionally cambered section with nearly the same
zero-lift angle trims at the same toe, lifts within 10 % at working angles,
does almost twice the work as the outside fin, and costs a third of the drag
going straight — about 18–21 N per set, near 15 % of a 60 kg rider's total
board drag. That is the first speed lever in this whole study that would be
felt, and it is the industry's "flat / 80-20 / inside foil" distinction.
fingen's geometry code already has the family (`FoilFamily.CAMBERED`); the
optimizer has never used it and tier-0 cannot tell the two apart. The
flat-inside numbers are CFD-backed; the cambered ones are tool-only at high
confidence. One isolated CFD polar of the gen-2 side planform with the 3 %
cambered section, including −4.5 / −3.5 / −2.5°, settles it.

**CFD result, same day (`bench/foil-family/`).** Confirmed, and it is a trade,
not a free gain. Isolated fin, same planform, level-2 RANS:

| | flat inside | cambered 3 % |
|---|---|---|
| drag going straight (zero side force), per fin | 13.4 N | 6.4 N |
| drag at 144 N of side force (CL 0.4) | 11.4 N | 10.0 N |
| drag at 216 N of side force (CL 0.6) | 19.8 N | 24.0 N |
| maximum lift in the polar | 0.83 | 0.71 |
| zero-lift angle | −3.5° | −2.9° |

The isolated flat-inside fin at −2.5 / −3.5 / −4.5° reproduces its drag in the
full set (11.2 / 13.4 / 16.1 N against 11.2 / 13.3 / 16.1 N), so the penalty is
the foil's. The cambered section halves it, stays ahead up to ≈ 150 N of side
force per fin, and loses beyond: more drag when loaded hard and 14 % less
maximum lift. The inside-face camber is therefore a real lever with a felt
range at both ends — ≈ 14 N per set going straight against drive and hold in
hard turns — which is exactly the kind of lever the gen-3 spider is meant to
offer. NeuralFoil had the drag gap right (direction and size) and the
maximum-lift ordering wrong.

## How CFD data can extend the fast model — the methods

The question (Tobias, 2026-11-19): the fast physical model is where the value
is; what methods exist to push it beyond its own physics with numerical data?

| method | what it is | data it needs | use here |
|---|---|---|---|
| A. calibrated physics | fit the few free constants of a physical model | 3–10 runs | **already in use**: CD0_CAL, K_STALL, KAPPA_FS, root and torsion compliance, the Falk deficit table |
| B. fidelity decomposition | compute each piece at the cheapest fidelity that gets it right: 3-D inviscid lattice × 2-D viscous section tables | a dense 2-D table (cheap, 3–4 dimensions) | the spine of the extension; how propeller, rotor and wind-turbine codes reach near-CFD accuracy in milliseconds |
| C. low-order phenomenon models | a physical law with 3–5 fitted parameters for the hard part: Kirchhoff / Leishman–Beddoes separation for knee, post-stall and (with lags) dynamic stall; Polhamus suction analogy for low-aspect-ratio vortex lift | polars per section family | knee, release, re-grip, the snap |
| D. multi-fidelity discrepancy model | CFD ≈ ρ·fast(x) + δ(x), δ a Gaussian process or low-order fit on a few PHYSICAL features (AR, sweep, peak loading, t/c, camber, Re, α); co-kriging, space mapping are variants | tens of 3-D runs, because the fast model already carries the trend | a thin residual layer that also returns an uncertainty: the model knows where it is unvalidated |
| E. active learning | spend CFD where uncertainty × relevance is largest | the loop, not more data | the verify queue and the EPYC worker are this loop in manual form; make every run training data and track error on fresh winners |
| F. mining each run | sectional loads, separation line, wake from every 3-D run instead of three coefficients | none extra | 20–50 calibration points per run for B and C |
| G. reduced-order field models | POD / DMD of CFD fields | many snapshots | only if pressure maps are wanted (FEM loads) |
| H. black-box surrogate | a network or GP on raw design variables | thousands of 3-D runs, no extrapolation | not a moat: anyone with compute can do it |

The top fidelity is not CFD. Our bench record shows where RANS itself is
wrong (section CL_max, everything past the knee), so experiments — [BW04],
[Zar14], [SK81], anything new — sit above it, and D handles such a ladder
natively (recursive co-kriging). Recommended architecture: B and C as the
physics, D as a thin correction with uncertainty, E as the operating loop, F
as the data habit. The method is textbook; the asset is the validated archive
in the right coordinates and the record of which CFD numbers can be trusted.

## Section recipe gate: passed with a resolved wall (2026-11-19)

`bench/section-gate/`, driver `finGenerator-cfd/scripts/section_polar.py`.
NACA 0012 at Re 7e5 against [SK81]:

| | measured | old recipe (±4 c, wall functions) | ±20 c, wall functions | ±20 c, resolved wall |
|---|---|---|---|---|
| lift slope, per rad | 6.30 | 5.12 | 5.16 | 5.84 |
| maximum lift | 1.075 at 11° | 0.73 at 10° | ≈ 0.79, soft | 1.11 at 12° |
| drag at 0° | 0.0067 (laminar run) | 0.0083 | 0.0069 | 0.0130 (fully turbulent estimate 0.0126) |

The wall treatment was the defect, not the domain. With prism layers to
y⁺ ≈ 1 the recipe holds the suction peak: maximum lift within 3 %, the break
within about 1°, slope 7 % low. Section tables can be built on it. Two
consequences beyond sections:

- **Our 3-D polars are wall-function runs.** Their linear range is validated,
  but their maximum lift is a lower bound and may be low by a comparable
  margin. If so, tier-0's "20 % high" on maximum lift is partly the CFD being
  low, and NeuralFoil's higher section values are closer to right than they
  looked. A level-4 polar of the gen-2 side at 8 / 12 / 16° tests this directly
  (queued, `~/bench-results/gen3run/knee`).
- **NeuralFoil was right about our flat-inside section.** First resolved-wall
  points for the gen-2 foil (t/c 0.092, Re 5.7e5), 2-D RANS against NeuralFoil
  tripped: lift at 0° 0.426 / 0.39–0.42, at 4° 0.861 / 0.85, at 12° 1.346 /
  1.32–1.35; drag coefficient at −3.5° 0.0423 / 0.0422. The section really
  holds a lift coefficient of 1.35 at 12°; the open question is only how much
  of that a low-aspect-ratio fin keeps, which is the knee test.
- **Drag from wall-function runs is not a level to trust either** (0.0069
  against 0.0130 on the same section); the 3-D drag comparisons in this note
  are A/B deltas on one recipe and stand as such.

## Grooves, structural side: FEM check (2026-11-19)

`bench/groove-fem/`. Shipped gen-2 side at its 318 N peak load, plain and with
3 or 6 grooves: the beam model captures 60–75 % of the softening (tip
deflection +24 % predicted against +41 % in FEM for six deep grooves) and
misses the stress concentration at the groove roots (raw FEM peaks 41–51 MPa
against 34–46 in the beam's groove band). Grooves are a stronger flex lever
than tier-0 says and need a depth-dependent softening factor and a stress
concentration factor of about 1.2. On this blade the plain beam is also 39 %
too soft, so the deflection and washout gates are conservative here.

## Viscous lattice: strips that follow their section polar (2026-11-19)

`fingen.sections` reads a shipped table (`src/fingen/data/sections_v0.npz`,
built offline by `scripts/build_section_table.py` from NeuralFoil, boundary
layer tripped: symmetric and flat-inside over ten thicknesses, cambered over
five thicknesses and six cambers, five Reynolds numbers, −16…+24°).
`lattice.solve_viscous` couples it to the lattice by the usual decambering
iteration: every strip gets an incidence offset until its lift equals what its
section gives at the incidence it works at. About 4 ms per angle for one blade.

Against the water-tunnel fin [BW04] (7 m/s; the only experiment we have):

| α ° | CL model | CL measured | CL wall-function RANS | CD model | CD measured (± 0.02) |
|---|---|---|---|---|---|
| 0 | 0.205 | 0.175 | 0.214 | 0.028 | 0.030 |
| 4 | 0.457 | 0.375 | 0.447 | 0.036 | 0.035 |
| 8 | 0.692 | 0.575 | 0.671 | 0.058 | 0.055 |
| 12 | 0.929 | 0.775 | 0.871 | 0.095 | 0.090 |
| 16 | 1.16 | 0.89 | 0.856 | 0.143 | 0.16 |
| 20 | 1.29–1.38 | 1.02 | 0.862 | 0.20 | 0.25 |
| 24 | 1.42 | 1.10 | 0.815 | 0.26 | 0.38 |

Against our own isolated polars (level-2 wall-function RANS, 8.5 m/s), drag
per fin in N:

| blade | −4.5° | −3.5° | −2.5° | 0° | 4° |
|---|---|---|---|---|---|
| gen-2 side, flat inside: model / CFD | 17.3 / 16.1 | 14.8 / 13.4 | 12.6 / 11.2 | 9.4 / 8.8 | 11.7 / 12.7 |
| same planform, cambered 3 %: model / CFD | 4.9 / 8.8 | 4.5 / 6.9 | 4.4 / 6.0 | 5.4 / 5.8 | 10.1 / 10.2 |

Reading:
- **Drag is right where it could be checked.** The tunnel's drag polar is
  reproduced through the linear range, and the flat-inside fin's drag at the
  toe angles — the 8 N per fin tier-0 could not see — comes out within 8–12 %
  of the CFD. This closes the residual of the trim-drag fix.
- **Lift level is high by a constant factor.** Model / tunnel ≈ 1.2 from 0 to
  12°; our wall-function RANS sits in between (1.14). Lift slopes against our
  own polars are 8–11 % high on the sides, 16 % on the thin centre. The lattice
  assumes a perfect mirror and the section table has slopes above 2π; which of
  the three is nearest the truth is not settled.
- **The post-knee climb is there, the knee is not.** The model keeps climbing
  as the tunnel fin does (RANS, steady or unsteady, flattens), but it climbs
  straight through 12° where the measured curve bends: at 12° no strip is near
  its section break (they work at 4–6°). The measured knee is a
  three-dimensional onset the strip coupling cannot produce; it has to stay an
  empirical element, as tier-0's break angle is.
- **Past the first stalled strip the iteration is not reliable** (it is damped
  and smoothed against the saw-tooth mode but does not always converge); those
  rows are estimates and flagged.
- The cambered foil's drag at negative incidence disagrees (model flat at
  4.5 N, CFD rising to 8.8 N). Wall-function drag levels are not a referee;
  the resolved-wall section tables include this foil.

Open on the referee side: the resolved-wall 3-D runs meant to test the knee
diverge within 40 iterations on both the gen-2 side and the tunnel replica,
gentle start included (`finGenerator-cfd/scripts/polar_angles.py`). That
recipe needs a continuation from low angle or mesh work; until then the tunnel
data are the only truth past 12°.

## The switch into the evaluation, and its first before/after (2026-11-19)

`RiderSpec.hydro_model` selects which hydrodynamics score a blade: `"tier0"`
(the default, unchanged) or `"lattice"` — lift slope, zero-lift angle, centre
of pressure and drag from `bladehydro.py` (viscous lattice + section table,
the blade toed in as mounted, board mirror strength 0.85 ≈ tier-0's reflection
factor 1.7). The break angle, the structure, release and stability are tier-0's
in both. Cost: 28 ms per fresh blade against 18 ms.

`scripts/hydro_model_compare.py` scores every archived winner twice
(`out/hydro-model-compare.md`). The pattern, in Newtons at 8.5 m/s:

| blade | going straight, tier-0 → lattice | at the 93 N working load |
|---|---|---|
| gen-1 big-wave side (flat inside, 6611 mm²) | 3.8 → 11.5 | 6.4 → 7.7 |
| all-round side (flat inside, 6730 mm²) | 3.7 → 10.7 | 6.5 → 7.1 |
| small-wave side (flat inside, 7272 mm², t/c 0.063) | 3.7 → 9.9 | 7.2 → 6.8 |
| shipped gen-2 side (flat inside, 9734 mm²) | 5.1 → 14.9 | 7.4 → 9.6 |
| ridden centre (symmetric, 7673 mm²) | 3.7 → 3.2 | 7.7 → 6.6 |

Every flat-inside side fin costs about three times what tier-0 thought going
straight, and about the same under load; symmetric centres read slightly
better. Peak margin drops 0.2–0.7° (the lattice zero-lift angle is smaller than
thin-airfoil theory on the root section, because the tip is thinner): the
shipped gen-2 side reads +1.27° against its 2° gate.

A re-search of Omar's gen-2 spec under the lattice model (one seed, 6000
evaluations — a look, not a design) moves to a low, wide, thin blade (depth
114, area 11 750 mm², AR 1.1, t/c 0.054 with a 0.5 tip factor): with only the
flat-inside family to choose from, the search dodges the flat-face penalty by
thinning the camber away. That is the model saying the foil family is the
missing parameter. The default therefore stays `"tier0"` until camber is
searched and the scoring is one-sided; flipping it now would trade one
artefact for another.

*Read again after "The oversized fin" below:* that blade (AR 1.1, effective
1.88) and two of the three later camber-free seeds (effective AR 2.06 and
2.22) sit where the break rule adds 2–5° of stall angle. Thinning the camber
away was not the whole story; the low aspect ratio was at least partly the
same second valley.

## The board as a mirror: lattice experiment (2026-11-19)

`scripts/board_edge_probe.py`, tables in `out/board-edge-probe.md`. All our
CFD and the lattice treat the board as an infinite wall; tier-0 softens that
to an effective-aspect-ratio factor 1.7 instead of 2.0, worth −9 % of lift
slope. Model: the wetted board is a finite rectangle of vortex rings, and
outside it the free surface releases pressure (the high-Froude condition;
Froude number on the fin chord ≈ 8). One blade at a time, untoed, uncanted.
The method converges with grid size and returns to within 1.8 % of the
infinite wall as the footprint grows, so read the numbers as ± 2 points,
biased toward too much loss.

| blade | situation | lift slope vs infinite wall |
|---|---|---|
| centre fin | tail half-width 160–230 mm, tail edge 150 mm behind the base centre | −6.5…−7.2 % |
| centre fin | tail edge only 90 mm behind | −12.8 % |
| side fin, 118 mm off the stringer | rail 72 mm outboard, tail edge 350 mm behind (its real position) | −9.2 % |
| side fin | rail 42 / 72 / 112 mm outboard, tail edge 150 mm behind | −16.0 / −11.9 / −9.2 % |
| either | wetted length ahead of the fin 200–900 mm | no effect |
| any | no board at all, fin through a free surface | −47 % |

Reading: (1) tier-0's 1.7 was a fair lumped guess — the real board costs
about 5–7 % on the centre and 7–12 % on the sides. (2) The sides lose 2–5
points more than the centre, so the perfect-wall CFD slightly flatters them.
(3) What matters is how close the fin sits to an edge — the rail for a side
fin, the tail for the centre — not how much board is ahead. A narrow tail or
a fin set close to the rail pays up to 16 %. By the agreed rule (CFD only above
10 %) the standard layout does not clearly qualify; the edge-distance
sensitivity is worth keeping as a formula once board dimensions are inputs.
Not modelled: viscosity, the actual wetted shape and spray, bank (a buried
inside rail gives that fin MORE wall, a lifted outside rail less).

## The oversized fin: what the first cut of frontier scoring exposed (2026-11-19)

`RiderSpec.scoring = "frontier"` scores a blade on goods in physical units,
one-sided, by the reference-point method (see the block in `optimize.py`).
Its first test, `scripts/frontier_demo.py` on the 60 kg pro's big-wave spec
with the lattice model and camber searched, asked for three different things
— neutral, speed first, hold first — and got the same answer three times: a
side fin of 15 400 mm², half again the size of the shipped one.

Standing rule for this project: an answer that looks wrong is not capped,
gated or scored away. It is either a shortcoming of the model or it is
correct, and the work is to find out which. This section is that work.

### 1. It was not the best fin, even under the rule that returned it

27 searches: three versions of the surplus rule × three sets of aspirations ×
three seeds, 6000 evaluations each, then every fin found scored under every
rule and every set of aspirations.

| aspirations | first-cut rule returned (3 seeds) | best fin any search found, scored by the same rule |
|---|---|---|
| neutral | 15 000–15 400 mm², objective +0.19…+0.20 | 9 800 mm², +0.06 |
| speed first | the same three fins, +0.62…+0.63 | 9 600 mm², +0.48 |
| hold first | 14 600–15 000 mm², −0.44…−0.51 | 15 400 mm², −0.52 |

Six searches of six stopped on the large fin where a lean one scores better.
And under every rule tried there are only two distinct best fins, not three:
neutral and speed first share the lean fin (≈ 9 700 mm², 5.1 N going
straight, hold 1.14, margin 2.0°), hold first takes the large one. The lean
fin sits on its gates — the rider file's 2° peak margin, the 140 mm depth
corridor, the minimum base — so asking for less drag cannot move it. **For
this rider the speed lever is empty.**

### 2. Two valleys, and what separates them

The straight line in design space from the lean fin to the oversized one
(every parameter interpolated, neutral aspirations):

| along the line | area mm² | AR | straight N | work N | hold | margin ° | yaw stiffness N·m/rad | roll damping N·m·s | first-cut objective |
|---|---|---|---|---|---|---|---|---|---|
| lean | 9 996 | 1.96 | 5.10 | 6.33 | 1.14 | +2.0 | 296 | 0.48 | +0.06 |
| 20 % | 10 949 | 1.74 | 5.37 | 6.65 | 1.17 | +2.4 | 305 | 0.49 | +0.15 |
| 40 % | 11 967 | 1.55 | 5.67 | 6.98 | 1.20 | +2.6 | 311 | 0.51 | +0.25 |
| 50 % | 12 502 | 1.47 | 5.82 | 7.15 | 1.21 | +2.8 | 313 | 0.52 | +0.31 |
| 60 % | 13 055 | 1.39 | 5.97 | 7.33 | 1.30 | +4.0 | 315 | 0.52 | +0.27 |
| 80 % | 14 213 | 1.24 | 6.28 | 7.69 | 1.47 | +6.1 | 318 | 0.54 | +0.22 |
| oversized | 15 433 | 1.11 | 6.60 | 8.06 | 1.62 | +7.9 | 319 | 0.54 | +0.19 |

Three things can be read off it.

**Area at a fixed depth buys almost no force per degree.** Lift slope × area
grows 12 % while the area grows 54 % (346 → 389 cm²/rad): a blade's side
force per degree is set by its depth, the slender-wing result. That is also
why yaw stiffness (+8 %) and roll damping (+13 %) barely notice the extra
chord. What the area can buy is a later break.

**The later break is one uncalibrated rule.** `hydro.stall_alpha_deg` holds
the break at 12° down to an effective aspect ratio of 2.5 and then adds 8° per
unit of aspect ratio below it ("heuristic … pending CFD calibration"; every
bench it was checked against sits at AR_eff ≥ 2.5, `docs/PHYSICS.md`). The
kink is the 50 % row: hold and margin take off exactly there. Read as a
maximum lift coefficient, the rule gives 0.98 at the lean fin, falls to 0.83
at the kink and recovers to 0.90 at the oversized one — a dip no physics asks
for:

| along the line | AR_eff | break ° | lift slope /rad | C_L at the break | F_max, relative |
|---|---|---|---|---|---|
| lean | 3.33 | 12.0 | 3.46 | 0.98 | 1.00 |
| 30 % | 2.80 | 12.0 | 3.17 | 0.89 | 1.04 |
| 50 % | 2.49 | 12.1 | 2.98 | 0.83 | 1.06 |
| 70 % | 2.23 | 14.2 | 2.79 | 0.88 | 1.22 |
| oversized | 1.88 | 16.9 | 2.52 | 0.90 | 1.42 |

**The first-cut scoring counted that reserve twice.** Hold (F_max / F_peak)
and the peak margin in degrees are one quantity, tied by the linear lift
curve: margin = (α_break − α_zero)·(1 − 1/hold). Both were goods in the sum.
The double credit is what turns the far end of the line into a second valley
(+0.19) behind a ridge (+0.31); the lean valley is deeper (+0.06) but narrow,
pinned between gates, and the search fell into the wide one every time.

### 3. What CFD says about the oversized fin

If the large fin is an artefact of the break rule, CFD will show it stalling
like any other fin. `bench/paddle-probe/`: the first-cut winner (15 433 mm²,
depth 131, base 120, 3.5 % camber, t/c 0.070, effective aspect ratio 1.88 —
the first polar this project has below 2.5), isolated on the symmetry plane,
8.5 m/s, level-2 RANS.

| own incidence ° | C_L | side force N | drag N | iterations |
|---|---|---|---|---|
| -3.5 | -0.004 | -2 | 10.6 | 800 (cap) |
| +0.0 | +0.163 | 93 | 9.3 | 800 (cap) |
| +4.0 | +0.353 | 202 | 17.1 | 131 |
| +8.0 | +0.547 | 312 | 33.2 | 131 |
| +12.0 | +0.715 | 409 | 65.3 | 800 (cap) |
| +16.0 | +0.846 | 483 | 111.1 | 800 (cap) |
| +20.0 | +0.839 | 479 | 155.4 | 800 (cap) |
| +24.0 | +0.849 | 485 | 206.7 | 800 (cap) |

The same polars read as a rider loads a fin, drag at equal side force
(`scripts/polar_at_force.py`; "—" = the fin never makes that force, or, in
the first column, was not run at −3.5°; every largest force is a lower bound,
wall functions):

| fin | area mm² | going straight (−3.5°) N | largest force N | at ° | drag at 93 N | drag at 200 N | drag at 250 N | drag at 290 N | drag at 318 N |
|---|---|---|---|---|---|---|---|---|---|
| gen-1 side as ridden (flat inside) | 6611 | — | 234 | 12 | 8.2 | 16.1 | — | — | — |
| 3 % camber on the shipped planform | 9734 | 6.9 | 258 | 16 (last angle run) | 7.5 | 20.0 | 38.6 | — | — |
| shipped gen-2 side (flat inside) | 9734 | 13.4 | 299 | 16 (last angle run) | 9.2 | 16.9 | 27.0 | 47.3 | — |
| cambered candidate (4.3 %) | 10054 | 9.1 | 295 | 16 (last angle run) | 7.9 | 15.8 | 25.7 | 44.5 | — |
| oversized fin (3.5 % camber) | 15433 | 10.6 | 485 | 24 (last angle run) | 9.3 | 17.0 | 24.2 | 30.0 | 35.1 |

What this polar can and cannot referee. Steady wall-function RANS flattens a
fin's lift past the knee; the one measurement we have, the [BW04] tunnel fin
(effective aspect ratio 2.6), does not flatten: C_L 0.775 at 12°, 0.96 at 18°,
1.10 at 24° (`docs/CFD-BENCH.md`; "Viscous lattice" above). So every row past
the knee of every fin in the table — the largest forces, the drag at 290 N of
the normal-sized fins, the plateau of the large one — is a lower bound on lift
and an upper bound on what the fin can still do. The first reading of this run
ignored that and was corrected the same evening. What is left:

- **The late break is real.** The large fin is still on the straight part of
  its lift curve at 12° (409 N; 202 N at 4°, 312 N at 8°), where every
  normal-sized fin has reached its knee. The model's figure for it, 516 N at
  16.9°, is not contradicted: the CFD shows at least 483 N.
- **The model's hold for the normal-sized fins is not contradicted either.**
  CFD stops them at 258–299 N; the model says 332–362 N, a lift coefficient
  of 0.96–0.98. The tunnel fin reaches 0.96 at 18° and keeps going. So the
  ranking and the size of the gap — about 40 % more hold for half again the
  area — stand on the model at both ends, checked by CFD at the large end and
  by the tunnel at the normal end.
- **It makes the peak turn force well inside its linear range**: 318 N at
  about 8° for 35 N of drag. A normal-sized fin has to be at its knee to make
  318 N. What that costs it cannot be settled with the tools at hand: about
  36 N if it stays linear to 12° as the tunnel fin did, about 57 N with the
  tunnel fin's own coefficients on its area, more in this CFD. So the large
  fin is at least as cheap in the hard turn and possibly much cheaper.
- **Going straight it costs more**, 10.6 N against 9.1 N (candidate) or 6.9 N
  (3 % camber on the shipped planform): 1.5–3.7 N per fin, half a step to one
  step. The model reads 6.6 N — the same gap between model and level-2 CFD
  as on every cambered fin at negative incidence, not yet attributed
  (`bench/cambered-candidate/`).
- **Lift: the lattice is within 7 % up to 16°** (0.510 against 0.547 at 8°)
  and has the zero-lift angle to 0.2°. Its drag is 0.80–0.86 of CFD from 0°
  to 8°.

So the answer to "is it an exploit or is it correct" is: nothing measured or
computed contradicts it. For a 318 N turn at 8.5 m/s the large fin has more
margin, no more drag in the turn, and costs half a step to a step going
straight. The second valley was real physics seen through a kinked rule and
counted twice.

### 4. What changed, and what did not

Changed, because it was wrong:

- **The reserve is scored once.** Three goods: drag going straight, drag at
  the working load, hold. The peak margin is reported and stays the rider's
  gate. The saturating surplus credit that had been added first — it made the
  three answers differ, which is why it looked like a fix — is removed again:
  it flattened the second valley without saying why the valley was there.
- `scripts/frontier_demo.py` searches every set of aspirations from several
  seeds and scores every fin found under every set, so a preference of the
  scoring can be told from a search that stopped in the wrong valley.

Nine searches under the corrected rule (3 seeds each):

| aspirations | fins returned | going straight N | at work load N | hold | margin ° |
|---|---|---|---|---|---|
| neutral (straight ≤ 4.9 N, work ≤ 6.2 N, hold ≥ 1.15) | 9 750–10 800 mm², depth 138–140 | 5.0–5.4 | 6.3–6.7 | 1.14 | +2.0 |
| speed first (≤ 3.7 N, ≤ 4.9 N, hold ≥ 1.05) | the same fins, seed for seed | 5.0–5.4 | 6.3–6.7 | 1.14 | +2.0 |
| hold first (≤ 7.4 N, ≤ 8.7 N, hold ≥ 1.45) | 14 700–14 900 mm², depth 135–138 | 6.4–6.5 | 7.7–7.8 | 1.51 | +6.1…+6.3 |

No search ends in the wrong valley any more. Seeds still differ by up to 0.17
of a noticeable step at the lean end (5.0 against 5.4 N), and in shape far
more than in score: tip width 0.14–0.58, sweep 24–35°, t/c 0.07–0.10 for the
same goods — the outline sliders are free, as `docs/MODEL-REACH.md` said.

Not changed, on purpose:

- **No ceiling on area, no penalty on low aspect ratio.** The large fin is
  what the model and the CFD say a rider gets who asks for hold 1.45.
- **The break rule.** It is not replaced by a guess; it gets calibrated on
  the polars (plan item B2, separation model).
- **The gates.** But two of them are now on record as binding every lean
  winner: the 140 mm depth corridor, which is convention and not physics
  (`optimize._DEPTH_CORRIDOR_MM`), and the rider file's 2° peak margin. The
  large fins sit on three slider box edges (tip width 0.6, leading-edge
  fullness 1.0, trailing-edge shape 1.0): the box, not the physics, decides
  where they stop.

### 5. What the model still cannot say

The model says that, for a 318 N peak turn at 8.5 m/s, more area buys real
hold for a small price going straight, and neither the CFD nor the tunnel
data contradict it. Riders do not ride side fins this large on a thruster, so
something that opposes area is missing from the model — or from our picture of
the load. What this investigation leaves on the table:

1. **Release — a hypothesis, not a finding.** The snap needs the tail to let
   go on demand and take hold again (plan, "the snap has three fin phases";
   quads are "harder to release … when attacking the lip"). Nothing in the
   model prices that: the release proxy is a planform heuristic, not offered
   in gen 3, so reserve is all gain and no cost. Whether a large fin releases
   worse cannot be read from this polar: its plateau from 16° to 24° is
   post-knee RANS, and the measured conventional fin does not let go inside
   24° either. It needs the high-angle work of plan item 0.1b with a method
   that can be trusted there, or the field.
2. **Hold is a requirement, not a good without end.** A rider cannot use
   force beyond the hardest turn they make. The physical statement is "the
   fins hold my hardest turn down to my lowest speed": F_max falls with V²,
   so hold at the design speed and the lowest speed that still holds are one
   number, V_hold = V / √hold (hold 1.14 → 0.94 V; 1.51 → 0.81 V; 1.62 →
   0.79 V). With the speed floor of the design point as an input (decision
   D4) hold becomes a floor the search must meet, and the surplus stops being
   something to pay for.
3. **Drag at the peak force: nobody can read it yet.** The lattice path has
   no drag rise toward the break: 27 N at 318 N for the lean fins, 28–29 N
   for the large ones. CFD gives 35 N for the large fin, on the straight part
   of its curve; for the lean ones the answer lies between about 36 N and
   "past the limit", depending on a knee that neither the model nor steady
   RANS resolves. Plan item 1.3 (drag at the peak force as a good) needs the
   separation model first, and that model needs the tunnel data and the
   resolved-wall sections, not these polars, as its referee.
4. **The peak force itself, and what the field says about size.** 318 N is
   bank angle 55° × the fins' share × the side fin's share. Two fins
   bracket it loosely: the gen-1 side (model hold 0.86) came with "feels
   sliding", the shipped gen-2 side (model hold 1.09) with "control way
   better" — though part of the first complaint
   was later traced to the centre fin, so this is consistent with the hold
   scale, not a proof of it. The same step, +47 % area, was reported as "can
   feel some drag": the model reads +3.4 N per fin there, 5.5 % of board drag
   for the pair, one noticeable step. Lean → oversized is another +54 % of
   area, so a rider would probably feel it going straight as well.
5. **Cambered blades at negative incidence** (`bench/cambered-candidate/`):
   the model reads 35–55 % less drag going straight than the level-2 CFD.
   The 2-D section data are not the cause — resolved-wall RANS of the 3 %
   camber section agrees with the table from −6° to +4° (next section) — so
   it is either a real effect of the thin outer sections or the mesh, and
   the search's taste for 3.4–4.4 % camber on thin sections stands or falls
   with that. A level-3 run of the same fin and the thin-section RANS runs
   decide it.

## Section table v0 against resolved-wall RANS: the first two sections (2026-11-19)

The section runs on the EPYC (`finGenerator-cfd/scripts/section_polar.py`,
resolved wall, the recipe that passed the [SK81] gate) are the referee for the
table the lattice reads. `bench/section-tables/results.json` holds what has
finished; `scripts/section_table_check.py` prints every finished section
beside the table. Two of twenty so far, both t/c 0.092 at Re 5.7e5:

| α ° | flat inside: cd RANS | cd table | ratio | 3 % camber: cd RANS | cd table | ratio |
|---|---|---|---|---|---|---|
| −6 | 0.0770 | 0.0753 | 0.98 | 0.0173 | 0.0151 | 0.88 |
| −4.5 | 0.0556 | 0.0533 | 0.96 | 0.0146 | 0.0132 | 0.90 |
| −3.5 | 0.0423 | 0.0424 | 1.00 | 0.0137 | 0.0125 | 0.92 |
| −2.5 | 0.0319 | 0.0315 | 0.99 | 0.0133 | 0.0123 | 0.92 |
| 0 | 0.0185 | 0.0175 | 0.94 | 0.0130 | 0.0125 | 0.97 |
| +4 | 0.0177 | 0.0138 | 0.78 | 0.0156 | 0.0140 | 0.90 |
| +8 | 0.0260 | 0.0189 | 0.73 | 0.0225 | 0.0186 | 0.82 |
| +10 | 0.0354 | 0.0269 | 0.76 | 0.0309 | 0.0243 | 0.79 |
| +12 | 0.0623 | 0.0466 | 0.75 | 0.1217 | 0.0339 | 0.28 |
| +16 | 0.3291 | 0.1417 | 0.43 | 0.2573 | 0.0984 | 0.38 |

- **Where the fins trim, the table stands.** Drag within 0–12 % from −6° to
  0° for both sections; the flat inside face costs three times the cambered
  one at −3.5° in RANS as in the table (0.042 against 0.014). Lift within
  0.03 (0.04 for the flat section at −6°).
- **Under load the table is low in drag**, 16–27 % from +4° to +10° (flat
  inside already from +2°). That is part of why the lattice reads a fin's
  drag 16–28 % below the 3-D CFD at 8–12°.
- **Maximum lift is high and the stall is missing.** RANS: 1.36 at 10° (flat)
  and 1.29 at 10° (cambered), then a plateau with the drag jumping fourfold.
  Table: 1.41 at 10° and 1.46 at 14°, with a quarter to a half of the drag
  past the stall.
- **The cambered section has no drag penalty at negative incidence in 2-D.**
  Its low-drag range is flat from −6° to +2°. So the 35–55 % by which the
  model reads less drag than the level-2 CFD on cambered fins going straight
  (`bench/cambered-candidate/`) does not come from the section data.
  *Read again after the next section: true of this t/c 0.092 section, not of
  thin ones, whose range ends at −3.5°; the table misses that, and it is most
  of the candidate's gap.*

Table v1 therefore has three corrections to carry, in this order of weight:
the stall (maximum lift and what the drag does after it), drag under load,
and the deep negative angles of cambered sections (−8°, −10°: table 0.4–0.6
of RANS). The trim range needs none on these two sections.

## The cambered candidate was a second exploit: where a thin cambered section stops being cheap (2026-11-19)

*Note of 2026-11-21: the 2-D referee this chapter rests on meshed a nose that
was not the section's ("The referee's nose", below). Its ends are two degrees
narrow at each end, and section 1's conclusion is withdrawn until table v1 is
rebuilt. The chapter is kept as the record of what was read at the time.*

The first search with camber free returned a thin, strongly cambered blade
(4.3 % camber, t/c 0.074) at 5.4 N going straight, and the level-2 CFD read it
at 9.9 N (`bench/cambered-candidate/`). The first referee section (3 % camber
at t/c 0.092) sided with the table, so the gap was left as "the fin or the
mesh". The thin sections that were queued to test the physical explanation
have run, and with them three further checks. The gap has two causes, one in
the model's section table and one in the CFD mesh, and the table's is the
larger for the candidate.

### 1. The table draws the attached range of a thin cambered section too wide

Resolved-wall 2-D RANS, Re 5.7e5, the recipe of the section gate
(`bench/section-tables/thin-cambered/`, `scripts/section_table_check.py`,
`scripts/section_edges.py`):

| α ° | 3 % camber, t/c 0.092: cd RANS | table | 3 % camber, t/c 0.070: cd RANS | table | 4.5 % camber, t/c 0.070: cd RANS | table |
|---|---|---|---|---|---|---|
| −6 | 0.0173 | 0.0151 | 0.0501 * | 0.0339 | 0.0591 * | 0.0546 |
| −4.5 | 0.0146 | 0.0132 | **0.0322** * | 0.0146 | **0.0447** * | 0.0186 |
| −3.5 | 0.0137 | 0.0125 | 0.0139 | 0.0127 | 0.0154 | 0.0136 |
| −2.5 | 0.0133 | 0.0123 | 0.0129 | 0.0118 | 0.0136 | 0.0125 |
| 0 | 0.0130 | 0.0125 | 0.0128 | 0.0121 | 0.0139 | 0.0126 |
| +4 | 0.0156 | 0.0140 | 0.0165 | 0.0134 | 0.0177 | 0.0143 |
| +8 | 0.0225 | 0.0186 | 0.0340 | 0.0228 | 0.0278 | 0.0225 |
| +10 | 0.0309 | 0.0243 | 0.1165 * | 0.0396 | 0.1052 * | 0.0364 |

\* the run did not settle within 3000 iterations: the flow has separated, and
the value says "outside the attached range", not what it costs there.

The attached range of the t/c 0.092 section runs from −6° to +10°. At
t/c 0.070 it runs from −3.5° to +8°: two degrees shorter at each end. The
table has the thin sections attached to about −4.5° (4.5 % camber) and −5.25°
(3 %) below and to +10° above, so it is a degree or more too generous at both
ends. Inside the range the table is 5–10 % low in drag and 4–5 % high in lift
slope, as on the first two sections.

Why the lower end matters so much for a side fin: the board fixes the toe at
3.5°, so going straight with ±1° of leeway the blade works at −2.5° to −4.5°
of own incidence. A cambered section there is 3–4° below the incidence its
nose is shaped for; the flow has to turn round the nose onto the inside face,
and a thin nose lets go first. The thin sections end their attached range
inside that band, the t/c 0.092 section 1.5° below it.

### 2. Through the lattice, the referee sections close most of the gap on the candidate

`scripts/rans_fed_lattice.py` applies the ratio RANS / table of the four
cambered nodes (t/c 0.070 and 0.092, 3 and 4.5 % camber; the fourth still
running and filled from the other three) to every strip's table polar and
solves the same lattice:

| own incidence ° | candidate (4.3 % camber, t/c 0.074–0.083): CFD level 2 N | table v0 N | RANS sections N | 3 % camber on the shipped planform (t/c 0.092–0.072): CFD level 2 N | CFD level 3 N | table v0 N | RANS sections N |
|---|---|---|---|---|---|---|---|
| −4.5 | 12.0 | 5.6 | 10.1 | 8.8 | 9.9 | 4.9 | 6.3 |
| −3.5 | 9.1 | 5.1 | 7.4 | 6.9 | 7.7 | 4.5 | 4.9 |
| −2.5 | 7.8 | 5.2 | 5.9 | 6.0 | – | 4.4 | 4.8 |
| 0 | 7.9 | 6.7 | 7.1 | 5.8 | 6.0 | 5.4 | 5.6 |
| +4 | 13.4 | 12.5 | 12.9 | 10.2 | – | 9.9 | 10.1 |
| going straight (mean of −2.5 and −4.5) | 9.9 | 5.4 | **8.0** | 7.4 | – | 4.6 | **5.5** |

The candidate's 5.4 N going straight was the table's wide range, not the fin:
with referee sections it is 8.0 N, and every quarter degree by which the true
edge differs from the middle of its 1° sampling bracket moves that by about
0.4 N. The 3 % camber blade on the thicker shipped planform moves only from
4.6 to 5.5 N, because its inner half is on t/c 0.08–0.09 sections that are
still attached. Lift is unchanged (within 0.02 in CL on both blades).

So the search had done with camber what it did with area the same day: it
walked to the edge of a cliff the model had drawn in the wrong place. Camber
buys hold, mostly through the zero-lift angle (the candidate reads 1.14, the
3 % blade 1.04, on 3 % less area). With the table as it was that cost 0.8 N
per fin going straight (5.4 against 4.6); with the referee sections it costs
2.5 N (8.0 against 5.5). Camber for hold against drag at the fixed toe is a
real tradeoff, and table v0 hid most of it.

### 3. The rest of the gap is the level-2 mesh at the nose

With referee sections the model still reads less than the level-2 CFD at
negative incidence: 4.9 against 6.9 N on the 3 % camber blade at −3.5°, where
every section of that blade is attached in 2-D. The level-3 run (prism layers
added, same surface cells) had not removed that. Two checks, and the second
corrected my reading of the first.

**The same sections in 2-D on the 3-D recipe** (`bench/section-tables/mesh-recipe/`):
wall functions, no layers, surface cells of chord/160 — what level 2 gives a
section at the fin's base — and coarser and finer, beside the resolved-wall
runs. Ratio to the resolved-wall value in brackets:

| section | wall, surface cell | cd at −4.5° | cd at −3.5° | cd at −2.5° | cd at 0° | cd at +4° | cl at −3.5° / 0° / +4° |
|---|---|---|---|---|---|---|---|
| camb3-tc070 | resolved, c/640 | 0.0322 | 0.0139 | 0.0129 | 0.0128 | 0.0165 | −0.044 / +0.340 / +0.771 |
| | wall functions, c/640 | 0.0247 (×0.76) | 0.0121 (×0.87) | 0.0094 (×0.73) | 0.0091 (×0.71) | 0.0128 (×0.77) | −0.046 / +0.343 / +0.782 |
| | wall functions, c/320 | 0.0320 (×0.99) | 0.0179 (×1.29) | 0.0113 (×0.87)* | 0.0110 (×0.86) | 0.0152 (×0.92) | −0.056 / +0.325 / +0.759 |
| | wall functions, c/160 | 0.0330 (×1.02) | 0.0177 (×1.28) | 0.0127 (×0.99) | 0.0127 (×0.99) | 0.0198 (×1.20) | −0.051 / +0.325 / +0.691 |
| | wall functions, c/80 | 0.0306 (×0.95) | 0.0241 (×1.74) | 0.0207 (×1.60) | 0.0164 (×1.28) | 0.0235 (×1.42) | +0.143 / +0.389 / +0.774 |
| camb3-tc092 | resolved, c/640 | 0.0146 | 0.0137 | 0.0133 | 0.0130 | 0.0156 | −0.041 / +0.345 / +0.778 |
| | wall functions, c/160 | 0.0306 (×2.10)* | 0.0172 (×1.26)* | 0.0135 (×1.01) | 0.0129 (×1.00) | 0.0194 (×1.25) | −0.029 / +0.332 / +0.651 |
| | wall functions, c/80 | 0.0312 (×2.14) | 0.0235 (×1.72) | 0.0215 (×1.62) | 0.0181 (×1.39) | 0.0213 (×1.36) | −0.025 / +0.121 / +0.463 |
| camb45-tc070 | resolved, c/640 | 0.0447 | 0.0154 | 0.0136 | 0.0139 | 0.0177 | +0.124 / +0.510 / +0.935 |
| | wall functions, c/160 | 0.0491 (×1.10)* | 0.0219 (×1.43) | 0.0165 (×1.21) | 0.0138 (×0.99) | 0.0221 (×1.25) | +0.111 / +0.484 / +0.780 |
| | wall functions, c/80 | 0.0503 (×1.12) | 0.0371 (×2.41) | 0.0255 (×1.88) | 0.0180 (×1.30) | 0.0210 (×1.18) | −0.007 / +0.290 / +0.696 |

\* not settled within 3000 iterations. Lift is in the last column.

At chord/160 all three sections read 26–43 % more drag at −3.5° than on the
resolved wall and agree with it at 0°; the t/c 0.092 section, attached to −6°
on the resolved wall, has let go by −4.5°. So the level-2 recipe ends the
attached range about a degree early at negative incidence. At +4° the same
cells cost 10–17 % of the lift and add 20–25 % drag. (Chord/80 gets the lift
wrong by up to 0.2 at every angle, which no 3-D polar shows; the 2-D slab at
that resolution is not a fair stand-in and is left out.)

The two finer wall-function meshes kept the early rise, and I read that as
"the wall treatment, not the cell size". That reading was wrong, and the
table shows why it could not carry it: at chord/320 and chord/640 the first
cell sits in the buffer layer (y+ 5–90), the friction is under-read by
14–29 %, and wall functions are not valid there. Refining the 2-D mesh
changed two things at once.

**The fin itself on a finer surface** (`bench/cambered-candidate/mesh-level-5/`;
mesh level 5 = level 2 with one more surface refinement, cells of base/320,
547 000 cells, still wall functions; at 8.5 m/s the first cell stays in the
log layer, y+ 12–162, mean 74):

| own incidence ° | level 2 N | level 3 N | level 5 N | model, table v0 N | model, RANS sections N |
|---|---|---|---|---|---|
| −4.5 | 8.8 | 9.9 | 7.0 † | 4.9 | 6.3 |
| −3.5 | 6.9 | 7.7 | 5.4 † | 4.5 | 4.9 |
| 0 | 5.8 | 6.0 | 5.6 | 5.4 | 5.6 |
| +4 | 10.2 | – | 11.0 (C_L 0.461 against 0.410) | 9.9 | 10.1 |

† at the 800-iteration cap. (Corrected 2026-11-20: the residuals had not met
their criterion, but the forces are steady, within 1.5 % over the last 200
iterations. These are converged values.)

One refinement of the surface takes 1.5–1.8 N off the level-2 polar at the
negative angles and leaves 0° where it was. What remains between the 3-D
polar and the model with referee sections is 0.5 N at −3.5° and 0.7 N at
−4.5°. So:

- **The level-2 surface is too coarse at the nose of a cambered blade run
  below its zero-lift angle.** The frozen recipe was converged on a symmetric
  fin at +6° (`docs/CFD-BENCH.md`), level 3 against level 2, which share
  their surface cells; that ladder could not see this.
- **Level-2 and level-3 polars of cambered fins read high below about −3°**
  and are not a referee for their drag going straight. Level 5 is, to about
  half a newton per fin, and it agrees with the lattice on referee sections.
  (2026-11-20: weaker than this reads. Its total is made of friction read a
  third low and pressure drag read high; see "What level 5's drag is made
  of".)
- At +4° level 5 carries 12 % more lift than level 2 (0.461 against 0.410;
  the lattice has 0.43), which is the lift the coarse nose was losing.

### 4. What the search does with referee sections

*Read again after "Section table v1" below: this search used the plain ratio
blend. With the ends of the attached range carried properly the search keeps
the camber and thickens the section instead; the move to more area and less
camber was the blend.*

Three neutral searches (seeds 0–2, 6000 evaluations, the corrected frontier
rule) with the RANS correction applied to every cambered section the lattice
asks for. All three end on the same score, +0.447, with the rider-file peak
margin of 2.0° binding:

| | found with table v0 (three neutral searches, earlier section) | found with RANS sections |
|---|---|---|
| area mm² | 9 750 – 10 800 | 11 730 – 11 915 |
| depth mm | 138 – 140 (the corridor) | 121 – 122 |
| camber % | 4.2 – 4.4 | 2.3 – 2.6 |
| t/c at the root, tip factor | 0.076 – 0.089, 1.08 – 1.19 | 0.058 – 0.075, 0.53 – 0.93 |
| going straight N, as scored when found | 5.0 – 5.4 | 6.1 |
| the same fins scored with RANS sections | 6.2 – 6.8 (peak margin 1.89 – 1.96°, under the 2° gate) | 6.1 (2.00°) |
| at working load N, with RANS sections | 6.7 – 7.2 | 7.3 |
| hold, with RANS sections | 1.13 | 1.13 |

Camber became expensive, so the search bought the same hold with a fifth more
area on a lower blade. Going straight costs 6.1 N per fin, not the 5.0–5.4 N
the table promised. The move itself is worth little: the old optima, scored
with the same referee sections, cost 6.2–6.8 N and miss the peak-margin gate
by a tenth of a degree. The valley is flat — a large change of shape for a
few tenths of a newton — as it was in the nine searches of the earlier
section. Against the flat-inside foil (14.9 N by the same model) every one of
these fins is a different class. Three things about the new optimum are not
the fin's:

- **It left the part of the design space the referee covers.** Camber
  2.3–2.6 % and roots down to t/c 0.058 lie outside the four nodes
  (3–4.5 %, t/c 0.070–0.092), where the correction is held at the nearest
  node. Root thickness, tip factor and base differ freely between the three
  seeds at the same score: the model has no opinion there, which is itself
  the finding.
- **It is pinned to a sample.** At −4.5° of own incidence the three blades
  hold every strip at −3.2° to −3.5° effective incidence — the last angle at
  which the thin sections are attached in the 1° sampling — by carrying a
  little negative lift there, so the induced flow relieves the sections. The
  relief is real physics. That it lands on −3.5° is the sampling.

- **It crossed the kink in the stall rule.** The three blades have an
  effective aspect ratio of 2.10–2.16 and take their break at 14.7–15.2°
  from `stall_alpha_deg`; the optima found with table v0 sit at 3.0–3.4 with
  the break at 12°. With camber expensive, the search bought its hold on the
  side of the kink that has one bench point (the paddle probe, linear to 12°)
  and no referee for where the break really is. Same shortcoming as the
  oversized fin, reached by another road.

The first two say what to run next, and it is queued behind the present batch: finer
angles at both ends of every cambered section's attached range
(`finGenerator-cfd/scripts/section_edge_plan.py`: quarter-degree steps inside
the 1° bracket), and five more sections — 2 and 3 % camber at t/c 0.05, 1 %
at t/c 0.07, 3 % at t/c 0.12, and 3 % at t/c 0.07 at the lower Reynolds
number the outer strips run at.

### 5. What changed in the record, and what is open

Changed:

- "Where the fins trim, the table stands" in the section above holds for the
  two t/c 0.092 sections it was written on, not for thin cambered ones.
- The cambered candidate is withdrawn as a design
  (`bench/cambered-candidate/README.md`). A good cambered side fin costs about
  6 N going straight by the model with referee sections, not 4.5–5.4 N. The
  flat inside face still costs 13–15 N by model and CFD alike.
- Level-2 and level-3 polars are no referee for a cambered fin's drag below
  about −3° of own incidence; mesh level 5 (one more surface refinement) is
  the recipe for that question. Their drag from 0° up to the knee stays as
  it was (with the wall-function caveats of `docs/CFD-BENCH.md`); their lift
  under load is a few percent low.
- No cap or gate was added. The scoring is unchanged; the section data are
  what was wrong, and they are being replaced by the referee's.

Open:

- **The referee's lower end has no measurement behind it.** The section gate
  tested the recipe on the upper end of a 12 % symmetric section. The lower
  end of a thin cambered one is a leading-edge separation on the other face,
  in fully turbulent RANS; a measured polar of such a section at negative
  lift is being looked for.
- **Table v1 has to interpolate on the ends, not through them.** The lower
  end moves about a degree per 0.01 of t/c. A linear blend between a section
  that is attached and one that is not smears the cliff over the gap between
  nodes, and the search then parks every strip on the last attached sample.
  v1 will carry the two ends of the attached range as quantities of their
  own (from the quarter-degree edge pass) and blend polars aligned on them.
- **The knee comes with it.** Thin sections end their attached range at +8°,
  not +10°, with a maximum attached lift of 1.13 (3 % camber) against 1.29 at
  t/c 0.092. Once the table carries that, the blade's break can be read from
  the sections through the lattice and compared with the [BW04] tunnel fin,
  in place of `stall_alpha_deg` and its kink.
- **Levers the search does not have.** The toe is the board's (3.5°), so a
  side fin going straight always runs 3–4° below the incidence a cambered
  nose is shaped for. Where the camber sits along the chord and how the nose
  is shaped decide how much of that a section tolerates; both are fixed in
  the cambered family (maximum camber at 40 % chord) and in the table.
- **The 3-D referee for cambered trim drag is one fin at three angles so
  far.** Level 5 on the candidate and on the flat-inside fin is running. The
  resolved-wall 3-D recipe still diverges (parked), so level 5 keeps its
  wall functions and their softness at a suction peak.

## Section table v1: v0 moved onto the referee's sections (2026-11-20)

Table v0 has the right shapes and the wrong ends; the RANS sections have the
right ends and are too few, and too coarse in angle, to be a table. v1
(`scripts/build_section_table_v1.py`, `src/fingen/data/sections_v1.npz`) is
v0 warped: the angle axis of every v0 polar is stretched piecewise-linearly
so that the centre of its low-drag range stays and its two ends land where
the referee has them, its drag is scaled to the referee's level, and its
lift keeps v0's line (with the referee's slope) plus v0's departure from
that line carried along with the ends. Seven numbers per section do it. They
are measured at every finished RANS section and carried over the rest of the
grid by a least-squares plane in thickness, camber and log Reynolds number
per foil family, held constant outside the box the nodes span. The ends are
quantities of their own, so between a section that is attached at some angle
and one that is not, v1 moves the cliff; it does not average across it.

At the four nodes it was built on (`bench/section-tables/table-v1-nodes.md`):

| section | lower end °: RANS / v0 / v1 | upper end °: RANS / v0 / v1 | drag level v1 / v0 | lift slope v1 / v0 | lift retention | cd v1 / RANS over the settled rows: min … max | largest cl difference |
|---|---|---|---|---|---|---|---|
| flat-tc092-re570k | -1.38 / -0.81 / -1.48 | +11.00 / +11.51 / +11.00 | 1.244 | 0.967 | 0.79 | 0.95 … 1.10 | 0.020 |
| camb3-tc092-re570k | -6.09 / -7.23 / -5.94 | +10.17 / +12.44 / +10.18 | 1.039 | 0.975 | 0.57 | 0.96 … 1.19 | 0.005 |
| camb45-tc070-re570k | -3.67 / -4.47 / -3.66 | +8.33 / +10.03 / +8.33 | 1.097 | 0.972 | 0.50 | 0.93 … 1.30 | 0.003 |
| camb3-tc070-re570k | -3.77 / -5.06 / -3.95 | +8.09 / +9.59 / +8.10 | 1.065 | 0.971 | 0.71 | 0.90 … 1.11 | 0.006 |

The warp alone removes what had looked like a separate defect: v0's
"16–27 % low in drag under load" was mostly its knee sitting 1.5–2.3° too
far out. With the ends in place, drag inside the range is within 0.90–1.19
of the RANS, one last attached row at 1.30 (v0: 0.73–0.97), lift within 0.006
up to the knee on the
cambered sections, and the knee is a maximum again. Past the knee v1 keeps
v0's drag, moved with the end; nothing referees it there.

`hydro_model = "lattice-v1"` reads it; `"lattice"` keeps v0 and every earlier
number. The table is a parameter through `sections`, `lattice` and
`bladehydro`, not global state.

### The comparison's own boundary condition

Checking v1 against the level-5 polar showed an error in every lattice-against-CFD
table before this one: the lattice was solved with the weakened mirror that
stands for a real board in `bladehydro` (strength 0.85), the CFD holds the fin
on a symmetry plane (strength 1). With the matching mirror the lattice
carries 8 % more lift. The "lift within 0.005 in C_L" of the candidate
against its level-2 polar was two offsets of that size cancelling: the
weakened mirror, and a level-2 mesh whose coarse nose loses lift.
`scripts/lattice_vs_polar.py` and `scripts/rans_fed_lattice.py` now use the
perfect mirror; drag at negative incidence moves by under 0.2 N (little
induced drag near zero lift), the lift columns move.

### Against the finer 3-D mesh

`scripts/lattice_vs_polar.py bench/cambered-candidate/mesh-level-5 bench/cambered-candidate/mesh-level-5-candidate --table=v1`
(level 5, perfect mirror on both sides):

| own incidence ° | 3 % camber, shipped planform: C_L CFD / v1 | drag N CFD / v1 | candidate: C_L CFD / v1 | drag N CFD / v1 / ratio blend / v0 |
|---|---|---|---|---|
| −4.5 | −0.085 / −0.092 | 7.0 † / 5.6 | −0.001 / −0.003 | 9.4 † / 7.3 / 10.1 / 5.6 |
| −3.5 | −0.019 / −0.026 | 5.4 † / 4.9 | +0.062 / +0.065 | 7.1 / 6.0 / 7.2 / 5.1 |
| −2.5 | +0.044 / +0.040 | 4.8 / 4.6 | +0.128 / +0.130 | 6.0 / 5.7 / 5.7 / 5.2 |
| 0 | +0.207 / +0.206 | 5.6 / 5.6 | +0.291 / +0.292 | 7.3 / 7.1 / 7.0 / 6.7 |
| +4 | +0.461 / +0.467 | 11.0 / 10.1 | +0.541 / +0.548 | 14.0 / 12.9 / 12.9 / 12.5 |
| going straight | | **5.9** / 5.1 | | **7.7** / 6.5 / 7.9 / 5.4 |

† at the iteration cap.

- **Lift: within 0.007 at every angle on both blades.** This is the first
  comparison in which the mesh, the boundary condition and the section data
  are all in order, and the lattice's lift stands.
- **Drag at 0° within 3 %; at +4° the lattice is 8 % low**, of which about
  5 % is its near-field induced drag (a far-wake evaluation gives 10.7 N;
  the near-field sum on 10 × 2 panels under-reads induced drag by about a
  tenth, noted in `lattice.trefftz_cdi`). (Fixed 2026-11-20, "The lattice:
  control points and induced drag": the deficit was 17 %, and +4° is now
  within 3 %.)
- **The flat inside face reads 13.3 N going straight on level 5**, 13.7 N
  on level 2 (`bench/cambered-candidate/mesh-level-5/`): its separation is
  fixed by the corner of the face and the mesh does not move it. The lattice
  has it at 15.0 N (v0) and 15.3 N (v1), 12–15 % high, and v1's drag level
  for this family — one section, taken at its minimum — makes 0° worse (9.9
  against 8.2 N). So by this mesh camber saves 5.6–7.4 N per fin; the model
  says 8.8–10.2 N.
- **The best fin of the v1 searches costs 6.1 N going straight on level 5**
  (`bench/cambered-candidate/mesh-level-5-v1-neutral/`; v1: 5.5 N). From
  −3.5° to 0° model and CFD agree within 3 %; at −4.5° the CFD reads 6.8 N
  against 5.6. Against the candidate at the same hold
  that is 1.6 N per fin from the thicker section (7.7 → 6.1), where the
  model had 1.0 N: the direction v1 found is right.
- **Between the nodes v1 is about a newton too kind.** Both blades have
  their sections between t/c 0.070 and 0.092. v1 moves the lower end of the
  attached range evenly with thickness between those two nodes; the 3-D
  polar says the range stays short for longer (candidate 9.4 N at −4.5°,
  v1 7.3, the plain blend 10.1). The candidate costs 7.7 N going straight,
  not 6.5. Two sections at t/c 0.080 are queued to measure the middle.
  (2026-11-20: the 4.5 % / t/c 0.092 section came back attached to −6°, and
  the best v1 fin, built from it, shows the same excess at −4.5° on level 5.
  This is no longer a statement about v1 between its nodes; whether level 5
  or the referee is nearer at −4.5° is open, see the next section.)

### What the search does on v1

The first build of v1 kept v0's grid, and its best fin came back on t/c 0.090
from root to tip: a grid node. Between nodes the library interpolates
plainly, and between t/c 0.07 and 0.09 that still turned the cliff into two
half steps, so the search parked on the node. v1 now ships on a finer grid
(t/c in steps of 0.005, camber in steps of 0.5 %), filled from v0 with the
ends aligned. On that table, six neutral and three hold-first searches (6000
evaluations, corrected frontier rule), and every earlier optimum rescored:

| found with | area mm² | depth | camber % | t/c root × tip factor | AR_eff | going straight N (v1) | hold (v1) | score (v1) |
|---|---|---|---|---|---|---|---|---|
| v1, neutral, seeds 0, 1, 3 | 10 000 – 10 180 | 140 | 4.1 – 4.2 | 0.089 – 0.092 × 0.97 – 1.04 | 3.3 | 5.5 – 5.6 | 1.14 | +0.23 … +0.25 |
| v1, neutral, seeds 2, 4, 5 | 11 750 – 11 970 | 125 – 138 | 3.1 – 3.2 | 0.071 – 0.094 | 2.3 – 2.7 | 5.7 – 5.8 | 1.13 – 1.15 | +0.43 … +0.48 |
| v1, hold first (three seeds) | 14 550 – 14 880 | 132 – 135 | 3.0 – 3.1 | 0.072 – 0.082 | 2.05 – 2.09 | 6.8 – 6.9 | 1.48 | −0.19 (its own aspirations) |
| table v0, neutral (three seeds) | 9 750 – 10 800 | 138 – 140 | 4.2 – 4.4 | 0.076 – 0.089 × 1.08 – 1.19 | 3.0 – 3.4 | 5.6 – 5.8 | 1.13 | margin 1.86–1.93°, under the gate |
| ratio blend, neutral (three seeds) | 11 730 – 11 915 | 121 – 122 | 2.3 – 2.6 | 0.058 – 0.075 × 0.53 – 0.93 | 2.1 – 2.2 | 6.8 – 8.5 | 1.13 | margin 1.98–1.99° |

- **On v1 the lean fin is back, on a thicker section.** Three of six seeds
  end on the same blade: 140 mm deep, about 10 000 mm², 4.2 % camber, t/c
  0.09 from root to tip (v0's optima: 0.076–0.089 at the root, thicker toward
  the tip). Thickness is what keeps the lower end of the attached range
  clear of the −4.5° the fin sees going straight; v1 prices it. 5.5 N going
  straight, hold 1.14, where v0 had promised 5.0–5.4. Its level-5 polar
  reads 6.1 N (above).
- **The move to more area and less camber was the blend plus the missing
  nodes, not the fin.** Those optima have sections thinner than any node; on
  v1 they cost 6.8–8.5 N.
- **Half the neutral seeds end in a worse valley** (+0.43 … +0.48 against
  +0.23), some on the far side of the stall-rule kink. A sharper cliff makes
  a rougher landscape; the search needs more starts than three before a v1
  result is taken as the optimum.
- **Hold first is where it was:** about 14 700 mm² on the far side of the
  kink, 6.8–6.9 N, hold 1.48.

### What is provisional in v1

- **Between nodes.** The level-5 polars say the lower end does not move
  evenly with thickness between t/c 0.070 and 0.092; v1 assumes it does and
  is about 1 N per fin low there. The t/c 0.080 sections decide.
- **The decisive node for the current optimum is not in yet.** It sits at
  4.2 % camber on t/c 0.09; v1's ends there come from the plane through the
  other three cambered nodes (lower end −5.5°). The 4.5 % / t/c 0.092
  section is the next one to finish. (In since 2026-11-20: attached from −6°
  to +12°.)
- Below t/c 0.070, above 0.092, below 3 % camber and away from Re 5.7e5 the
  corrections are held at the nearest node; the third batch (t/c 0.05, 0.08
  and 0.12, 1 and 2 % camber, Re 2.8e5) and the quarter-degree edge pass
  replace that. The symmetric family has no finished section and is v0
  unchanged.
  (In since 2026-11-20: twelve cambered sections, and the builder reworked —
  "Twelve cambered sections, and a table read the way the model reads it".)
- The ends are located inside 1–2° sampling brackets by linear
  interpolation of the drag.
- **The referee's lower end against measurements.** Tabulated UIUC low-speed
  tunnel polars of comparable sections, looked up for this purpose, put the
  lower corner within about a degree of the RANS on either side: E387 (9.1 %
  thick, 3.8 % camber, tripped, Re 5e5) cd 0.0147 at −4.2° and 0.036 at
  −5.2°; SD7037 (9.2 %, 3.0 %, Re 3e5) 0.0149 at −4.0°, 0.0225 at −5.0°,
  0.058 at −5.9°; A18 (7.3 %, 3.8 %, tripped, Re 3e5) 0.0166 at −4.7°. None
  is our section, none is fully turbulent, and their noses differ; at 9 %
  they contradict table v0's −7.2° and sit at or up to a degree inside the
  RANS bracket (−6 … −8°), at 7 % they cannot separate the two. Reliability
  about ±1°.
- **Induced drag.** The lattice's near-field sum is about a tenth low in
  induced drag. Nothing at the working load (0.2 N); 2 N at the peak force.
  (Fixed 2026-11-20; it was 17 % and half a newton at the working force.)
- **The flat-inside family** has one RANS section (t/c 0.092); its level is
  held for every thickness, and the lattice over-reads the shipped fin's
  drag going straight by 2 N against level 5. Three more flat sections are
  in the main plan.

## Two more referee sections, what level 5's drag is made of, and the lattice's induced drag (2026-11-20)

### 1. The last two thin sections

`bench/section-tables/thin-cambered/` is complete (`scripts/section_edges.py`):

| section (Re 5.7e5) | settled from … to | lower end between | knee between | table v0: lower end / knee |
|---|---|---|---|---|
| 2 % camber, t/c 0.070 | −4.5° … +6° | −4.5 and −6° | +6 and +8° | −5.5° / +9.5° |
| 3 % camber, t/c 0.070 | −3.5° … +8° | −3.5 and −4.5° | +8 and +10° | −5.25° / +10.0° |
| 4.5 % camber, t/c 0.070 | −3.5° … +8° | −3.75 and −4.0° (edge pass) | +8 and +10° | −4.5° / +10.5° |
| 3 % camber, t/c 0.092 | −6° … +10° | −6 and −8° | +10 and +12° | −7.25° / +12.0° |
| 4.5 % camber, t/c 0.092 | −6° … +12° | −6 and −8° | +12 and +14° | −6.25° / +10.5° |

- **4.5 % camber on t/c 0.092 is attached from −6° to +12°**: cd 0.0137 at
  −2.5°, 0.0156 at −4.5°, 0.0178 at −6°, cl 1.49 at +12°. That is the
  section the best fin of the v1 searches is built from. It works at −2.5 to
  −4.5° going straight, a degree and a half inside the range.
- Thickness moves the lower end by about 2.5° between t/c 0.070 and 0.092;
  camber between 3 and 4.5 % hardly moves it. The knee moves with both.
- With five cambered nodes a plane no longer passes within 0.4° of their
  ends. v1 now adds to the plane what each node still misses, spread to its
  neighbourhood by inverse-square distance (one unit = 0.02 in t/c, 1.5 % in
  camber, a factor two in Reynolds number). At a node v1 is that node: ends
  within 0.2° (the table's grid), lift within 0.008, drag 0.90–1.19 of the
  referee inside the range. The one exception is the last sample before an
  end (up to 1.4): v1's rise toward an end starts earlier than the referee's.
  `bench/section-tables/table-v1-nodes.md`.

### 2. What level 5's drag is made of

The best fin of the v1 searches read 6.8 N at −4.5° on level 5 where the
model has 5.6 N, and the referee section says the blade is well inside its
range there. To see what the 3-D number consists of, the stored cases were
sampled on the fin's surface (`finGenerator-cfd/scripts/sample_surface.sh`:
wall shear stress and pressure per face) and split into pressure and
friction drag on the lattice's own strips
(`finGenerator-cfd/scripts/surface_split.py`; tables in
`bench/cambered-candidate/mesh-level-5-v1-neutral/surface-split.md`).

**The rows marked as capped are converged.** They stopped at 800 iterations
because the residuals had not met their criterion; the forces are steady:
within 0.01 % over the last 200 iterations on this fin and on the candidate
at −4.5°, within 0.3 % on the flat-inside fin, within 1.5 % on the 3 %
cambered fin at −4.5° and +8°. Earlier notes call these rows unsettled; that
was read off the iteration count and is wrong.

| own incidence ° | level 5: drag N = pressure + friction | lattice, table v1: drag N = induced + profile |
|---|---|---|
| −4.5 | 6.84 = 4.71 + 2.13 | 5.65 = 0.00 + 5.64 |
| −3.5 | 5.50 = 3.23 + 2.27 | 5.45 = 0.08 + 5.37 |
| −2.5 | 5.33 = 2.85 + 2.48 | 5.59 = 0.40 + 5.19 |

The same split on the referee's own cases
(`finGenerator-cfd/scripts/section_surface.py`), and the 3-D strip at 73 mm
of span (chord 74 mm, t/c 0.091, Re 6.0e5) beside the referee's 4.5 % /
t/c 0.092 section at the incidence the lattice gives that strip:

| section incidence ° | level 5 strip: cd = pressure + friction | referee section: cd = pressure + friction |
|---|---|---|
| −3.2 (fin at −2.5°) | 0.0119 = 0.0051 + 0.0068 | 0.0140 = 0.0044 + 0.0096 |
| −3.8 (fin at −3.5°) | 0.0117 = 0.0056 + 0.0061 | 0.0146 = 0.0051 + 0.0095 |
| −4.4 (fin at −4.5°) | 0.0155 = 0.0100 + 0.0055 | 0.0155 = 0.0061 + 0.0094 |

(The referee's split is sampled at −2.5, −4.5 and −6° — friction 0.0097,
0.0094, 0.0085, pressure 0.0040, 0.0062, 0.0093 — and interpolated.)

- **Level 5 reads friction 30–40 % low**, at every strip and every angle:
  0.0055–0.0077 against the referee's 0.0094–0.0097. Its first cell is about
  as tall as the boundary layer is thick over the forward third of the
  blade; the wall function has nothing to stand on there.
- **It reads pressure drag high**, mostly on the two strips nearest the
  base (0.4–0.6 N more than the model at all three angles), and at −4.5°
  along the whole span.
- **Between −2.5° and 0° the two cancel**, and the total agrees with the
  model within 5 %. That agreement is real as far as it goes — lift, induced
  drag and the order of the fins (flat inside far above cambered, thin
  cambered above thick cambered) do not depend on it — but level 5 is not
  an independent referee for the last 5–10 % of a cambered fin's drag.
- **At −4.5° both show the same thing and differ in size.** Toward the
  lower end of the range the pressure part grows and the friction part
  falls before any flow reverses: on the referee section (no reversed shear
  at −4.5 or −6°; suction spike −3.3 and −4.7 at 0.5 % of chord) and on
  the 3-D fin (reversed shear on under 5 % of the inside face of the two
  outermost strips only; spike −2.7 at the base). On level 5 the pressure
  part rises about twice as fast. Either its surface — three cells across
  the nose radius — loses nose suction, or the referee is generous at this
  end; tunnel polars of comparable 9 % sections put the corner at or up to
  a degree earlier than the referee does ("What is provisional in v1").
  The 2-D check on the 3-D recipe (`bench/section-tables/mesh-recipe/`)
  showed wall-function cells of this size ending the range early, which
  favours the first reading without proving it.
- **So the drag going straight of the best fin is 5.6 N by the model and
  6.1 N by level 5, and which is nearer is open.** Two controls are queued
  behind the edge pass: three sections again around their lower ends with
  the referee's surface one level finer (chord/1280 at the nose), and the
  4.5 % / t/c 0.092 section with wall functions on level 5's cells at the
  Reynolds number of a fin's base at 8.5 m/s (9.7e5), beside a resolved
  partner at that Reynolds number.

### 3. The lattice: control points and induced drag

Two errors in the lattice itself, found while chasing the +4° rows (model
8–9 % below level 5):

- **Induced drag was read from the force on the bound legs.** On a swept
  blade that sum is 10–18 % below what the wake carries, at any lattice
  density: it gave span efficiencies of 1.11–1.21, and a planar wake cannot
  exceed 1. `lattice.far_wake_drag` reads it in the far wake instead, for
  any number of placed blades and a partial image; `solve_viscous` now uses
  it (`cd_induced`; the old number stays as `cd_induced_near`).
- **The control points sat at the middle of each strip's width.** The strips
  are clustered toward the tip in equal steps of an angle; the control
  point belongs at the middle of the angle step. With that, ten strips carry
  the fine lattice's lift within 0.3 % (it was 2.8 % high and converged
  slowly) and its far-wake drag within 0.3 %. Textbook checks
  (`scripts/vlm_probe.py`): rectangular wings of aspect ratio 2 / 4 / 6
  have slopes 2.47 / 3.61 / 4.21 per radian against published 2.47 / 3.6 /
  4.2; the elliptic planform has span efficiency 0.99.

| best fin of the v1 searches at +4°, inviscid | C_L | induced drag N |
|---|---|---|
| 10 × 2 panels, as it was (strip-middle control points, force sum) | 0.547 | 7.45 |
| 10 × 2 panels, now | 0.531 | 8.46 |
| 40 × 4 panels, now | 0.532 | 8.48 |

Against the tunnel ([BW04], digitised to ±0.02 in C_D) the comparison has to
be made at the tunnel's lift, not its angle: on the perfect mirror the model
lifts 15 % more than the tunnel at the same angle, and the old test passed
at equal angle because that extra lift made up for the missing induced
drag. With the weakened image of the board model (0.85) the lift line is the
tunnel's within 5 %, and at the tunnel's lift:

| tunnel C_L | 0.175 | 0.375 | 0.575 | 0.775 |
|---|---|---|---|---|
| tunnel C_D | 0.030 | 0.035 | 0.055 | 0.090 |
| model, far wake | 0.0303 | 0.0366 | 0.0564 | 0.0901 |
| model, force sum (as it was) | 0.0299 | 0.0345 | 0.0515 | 0.0809 |

Against level 5 (`scripts/lattice_vs_polar.py … --table=v1`, perfect mirror):

| own incidence ° | 3 % camber, shipped planform: drag N CFD / model | candidate: CFD / model | best v1 fin: CFD / model |
|---|---|---|---|
| −4.5 | 7.0 / 5.5 | 9.4 / 7.0 | 6.8 / 5.6 |
| −3.5 | 5.4 / 4.8 | 7.1 / 6.0 | 5.5 / 5.5 |
| −2.5 | 4.8 / 4.6 | 6.0 / 5.8 | 5.3 / 5.6 |
| 0 | 5.6 / 5.7 | 7.3 / 7.4 | 7.1 / 7.3 |
| +4 | 11.0 / 10.7 | 14.0 / 13.9 | 13.9 / 13.8 |

The loaded rows are within 3 % now (they were 8–9 % low). Lift is 0.005 to
0.011 below level 5 from 0° to +4° where it had been within 0.007 either
way: the old agreement contained the lattice's 2.8 %.

What this does to every earlier number from the `lattice` and `lattice-v1`
models: a fin holds 2.8 % less than they said and pays about half a newton
more at the working force (the earlier best: 7.3 N against 6.8). All
earlier optima sit 2–3 % short of their hold requirement on the corrected
model.

### 4. What the search does on the corrected model

Six neutral searches, 6000 evaluations, table v1 with five cambered nodes:

| seeds | area mm² | depth | camber % | t/c root × tip factor | AR_eff | going straight N | at the working force N | hold | score |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 10 720 | 140 | 4.0 | 0.119 × 0.53 | 3.1 | 6.3 | 7.6 | 1.14 | +0.54 |
| 0, 1, 3, 4, 5 | 12 520 – 12 960 | 132 – 133 | 2.3 – 3.0 | 0.061 – 0.069 × 0.83 – 1.18 | 2.3 – 2.4 | 6.3 – 6.5 | 7.9 | 1.14 | +0.67 |

- **Both answers have left the referee's nodes.** The better one puts t/c
  0.12 at the base and thins to 0.063 at the tip; the other five run t/c
  0.06–0.07 with 2–3 % camber. The cambered nodes span t/c 0.070–0.092 and
  2–4.5 % camber; outside that box v1 holds its corrections at the box's
  edge while v0's shapes keep changing with thickness. The search has gone
  to where the table is least checked, on both sides at once.
- That is the result to act on, not a candidate: the third 2-D batch
  (t/c 0.05 and 0.12, 1 % camber, Re 2.8e5; running) puts nodes exactly
  there. Scores are higher than on the earlier model (+0.23 before) because
  the same aspirations now have to be met with less lift and more induced
  drag.
- Five of six seeds end in the worse valley. The search's robustness on v1
  is unchanged and still an open item.

## The knee: where a blade leaves its lift line (2026-11-20)

Hold is the force a blade makes at its break over the force the turn asks
for, and the break angle has been tier-0's rule through every model so far:
12° for any effective aspect ratio above 2.5 (the value measured on the one
tunnel fin, [BW04], geometric aspect ratio 1.5), later below. The viscous
lattice had no knee of its own. Two things changed that.

### 1. The strips run to their sections' breaks put the knee ten degrees late

With table v1 and the board mirror the tunnel fin's lift line runs straight
to 22° before its first strip reaches its section's break; the tunnel has
the fin on its line at 12° and 6 % below it at 14°. At 12° the most loaded
strip of that fin works at a local lift coefficient of 0.91, 68 % of what
its section has at its own break. So the blade's knee is not the 2-D
section's stall carried through strip theory. Whatever ends the line —
transition on a real section, spanwise flow on a swept blade, the tip — it
ends when the hardest-working strip is at about 70 % of the fully turbulent
section's lift.

### 2. That one number, fitted on the tunnel fin, finds the knee of the other polars

`bladehydro.knee`: follow every strip's lift along its own line through the
working range; the knee is the first angle at which one of them reaches
`KNEE_FRACTION` = 0.70 of its section's lift at the section's break. 0.70
puts the tunnel fin at 12.0° on the board mirror. Nothing else is fitted.
`scripts/knee_survey.py` against every stored 3-D polar that comes with a
fin file (`bench/knee/`; polars are wall-function RANS in 4° steps, so their
knee is a bracket; perfect mirror on the model side, as in the CFD):

| blade | geometric aspect ratio | polar is 5 % below its line between | aspect-ratio rule | strip criterion | C_L at the knee: rule / criterion | highest C_L in the polar |
|---|---|---|---|---|---|---|
| tunnel fin [BW04], flat inside | 1.51 | 12–14° (tunnel: 12–14°) | 12.0° | 11.4° | 0.85 / 0.86 | 0.87 |
| gen-2 side as shipped, flat inside | 2.01 | 4–8° | 12.0° | 7.1° | 1.01 / 0.68 | 0.83 |
| same planform, 3 % camber (mesh level 2 and level 5) | 2.01 | 4–8° | 12.0° | 6.1° | 0.95 / 0.59 | 0.71, 0.66 |
| cambered candidate | 1.95 | 4–8° | 11.9° | 6.4° | 1.01 / 0.68 | 0.79 |
| gen-1 side as ridden, flat inside | 2.60 | 8–12° | 12.0° | 7.3° | 1.15 / 0.82 | 0.96 |
| large low fin (paddle probe) | 1.11 | 12–16° | 16.9° | 14.3° | 0.89 / 0.83 | 0.85 |
| gen-1 centre as ridden, symmetric | 1.53 | 8–12° | 12.0° | 7.2° | 0.65 / 0.41 | 0.58 |

- **The rule is 4–6° late on every side blade slenderer than the tunnel
  fin.** It carries their line to a lift of 1.0–1.15, above the highest lift
  anywhere in their polars. This is the old finding that tier-0's maximum
  lift reads 20–26 % above CFD; it had been put down to wall functions
  being soft. The tunnel-anchored criterion says the same as the CFD.
- **The criterion lands inside or within a degree of every side-blade
  bracket.** A slender blade reaches the share earlier because each degree
  loads its strips more, a tip-loaded one earlier than one that spreads its
  load, a section with more maximum lift later. The rule knows none of
  these above aspect ratio 2.5.
- **It misses the one symmetric blade** (7.2° against about 10°). The
  symmetric family has no referee section yet, and a thin symmetric
  section stalls differently. For now the criterion is for side blades.
- Soft spots: one tunnel fin fixes the number; the polars are coarse in
  angle and wall-function runs tend to bend early (the tunnel fin's replica
  is 5 % down at about 12°, the tunnel itself at about 13.6°). The level-5
  run in one-degree steps on four blades is in: section 6.

### 3. What it does to the fins on record

`hydro_model = "lattice-knee"` (opt-in; table v1, corrected lattice, break
angle from `bladehydro.knee`). 60 kg rider, 8.5 m/s, peak turn force 318 N:

| fin | area mm² | geometric aspect ratio | break: rule / strips | hold: rule / strips | margin to the break at the peak force: rule / strips |
|---|---|---|---|---|---|
| gen-1 side as ridden (flat inside) | 6 611 | 2.60 | 12.0° / 7.7° | 0.82 / 0.61 | −3.3° / −7.6° |
| gen-2 side as shipped (flat inside) | 9 734 | 2.01 | 12.0° / 7.5° | 1.04 / 0.74 | +0.6° / −3.8° |
| tunnel fin [BW04] | 9 566 | 1.51 | 12.0° / 12.0° | 0.92 / 0.92 | −1.3° / −1.3° |
| cambered candidate | 10 054 | 1.95 | 11.9° / 6.8° | 1.09 / 0.76 | +1.4° / −3.6° |
| best fin of the first v1 searches | 10 004 | 1.96 | 12.0° / 8.9° | 1.11 / 0.90 | +1.6° / −1.6° |
| large low fin (paddle probe) | 15 433 | 1.11 | 16.9° / 15.6° | 1.54 / 1.43 | +7.2° / +5.8° |

- **At equal area the tunnel-shaped fin holds a quarter more than the
  shipped gen-2 side** (0.92 against 0.74); under the rule the slender one
  held more (1.04 against 0.92). The rule paid for aspect ratio twice: less
  induced drag and more hold. (Depth still goes to 135–140 mm in the
  searches below — induced drag alone is reason enough — but area and
  fullness now answer to hold.)
- **The field record reads the same way round.** The gen-1 side, reported
  as sliding and losing control in the top turn, is at 0.61; the gen-2 side
  that replaced it and is ridden without that complaint is at 0.74. Both
  are past their knee at the peak force this rider's sheet asks for — a
  blade keeps lifting past its knee (the tunnel fin by another 40 % up to
  24°, at a steep price in drag) — so a hold below 1 is not a fin that
  cannot turn. But it means the aspiration of 1.15 and the 2° margin gate
  were numbers in the rule's currency.

### 4. What a search does with it

Six seeds each, 6000 evaluations, neutral aspirations, cambered side foil:

| requirement | area mm² | depth | geometric aspect ratio | camber % | t/c at the base | knee | hold | going straight N | at the working force N | score |
|---|---|---|---|---|---|---|---|---|---|---|
| as it was: hold 1.15, margin ≥ 2° — seeds 1, 3, 4 | 11 090 – 11 760 | 138 – 140 | 1.66 – 1.72 | 2.8 – 3.2 | 0.087 – 0.107 | 12.7 – 13.2° | 1.16 – 1.18 | 5.4 – 5.7 | 7.5 – 7.6 | +0.46 … +0.53 |
| as it was — seeds 0, 2, 5 | 10 510 – 11 000 | 133 – 140 | 1.69 – 1.80 | 2.0 – 2.9 | 0.135 – 0.212 | 16.2 – 17.6° | 1.10 – 1.11 | 5.4 – 5.9 | 7.8 – 7.9 | +0.60 … +0.67 |
| moved with the shipped gen-2 side: hold 0.82, margin ≥ −2.4° — all six | 8 750 – 9 390 | 135 – 140 | 2.02 – 2.18 | 2.9 – 3.6 | 0.083 – 0.106 | 9.9 – 10.9° | 0.85 – 0.91 | 4.5 – 5.0 | 6.7 – 6.9 | +0.17 … +0.21 |

("Moved with the shipped gen-2 side": that fin loses 0.30 of hold and 4.4°
of margin when its knee is read off the strips; the aspiration and the gate
are moved by the same amounts, so the search is asked for what the present
model thinks it is asking for, measured at the real knee.)

- **Asked for the same reserve as before, the fin grows by an eighth and
  fills out**: about 11 300 mm² at the same depth, aspect ratio 1.7 instead
  of 2.0, knee at 13°. Three of the six seeds find it.
- **The other three buy the knee with section thickness** (t/c 0.14–0.21,
  swept 50–60 mm): far above the thickest referee section (0.092; 0.12 is
  running). There table v1 is table v0, and v0's maximum lift keeps rising
  with thickness. This is the "thickness as a free lever" defect of tier-0
  coming back through the table; it names the sections to run (3 % camber
  at t/c 0.16 and 0.20), it is not a fin.
- **Asked for what the shipped gen-2 side delivers and a little more, all
  six seeds agree**: 8 750–9 400 mm², depth 135–140, 3–3.5 % camber on t/c
  0.08–0.11, knee at 10–11°. Hold 0.85–0.91 against the shipped fin's 0.74,
  4.5–5.0 N going straight against its 15.3 N. The two-valley landscape of
  the rule is gone here: the spread between seeds is 0.05 in score.
- None of these is a candidate yet. They rest on a knee criterion with one
  anchor, on the open half newton at −4.5°, and on sections up to t/c 0.106
  where the thickest cambered node is 0.092.

### 5. What is open, and what needs a decision

- **Hold needs a new anchor.** With the knee read off the strips, "hold
  1.15" is no longer what the shipped fins have. Either the aspiration is
  set relative to a fin that is known to work (the gen-2 side: 0.74), or
  the peak turn force is revisited (decision D4: at what speed is the
  hardest turn made). The search results above show both readings.
  **Decided 2026-11-20 (D11):** anchored on the gen-2 side. A second anchor
  agrees with it: a commercial medium thruster fin reads 0.82–0.86 for a 65 kg
  rider and 0.67–0.70 for an 80 kg rider, the band size charts sell it for
  (`scripts/hold_anchor.py`, `bench/knee/hold-anchor.md`); the gen-2 side
  reads 0.73 for its 60 kg rider, the gen-1 side that slid 0.60. Under
  `"lattice-knee"` the floor is `HOLD_FLOOR_KNEE = 0.72` and the aspiration
  `HOLD_ASPIRATION_KNEE = 0.80`; the gate in degrees does not apply there.
- ~~The one-degree knee run on mesh level 5 (four blades).~~ Done: section 6.
- Symmetric sections for the centre fin's knee.
- Sections thicker than t/c 0.12.
- The criterion says where the line ends, not what happens after it. How
  much force is left past the knee, and what it costs, is still the
  release question.

### 6. One-degree steps on four blades: the criterion ranks them right and sits a degree early

`bench/knee/one-degree/` (mesh level 5, a symmetry plane at the base; the
criterion on the same perfect mirror, table v1 as rebuilt, share 0.715):

| blade | last row on its line | next row | 5 % below at | strip criterion | C_L at the last row on the line: CFD / criterion |
|---|---|---|---|---|---|
| tunnel fin [BW04] | 12° (−1.9 %) | 13°: −8.2 % | 12.5° | 11.4° | 0.886 / 0.86 |
| gen-2 side, flat inside | 8° (−2.1 %) | 9°: −7.3 % | 8.6° | 7.0° | 0.721 / 0.67 |
| best table-v1 side, 4.2 % camber | 8° (−1.7 %) | 9°: −7.0 % | 8.6° | 7.5° | 0.780 / 0.74 |
| gen-1 centre, symmetric | 8° (−1.5 %) | 9°: −4.1 %, 12°: −7.6 % | 9.9° | 7.3° | 0.447 / 0.41 |

- **A side blade breaks inside one degree.** Within 2 % of its line at one
  angle, 7–8 % below at the next, and every row past it runs to the
  iteration cap. The 4° polars could not show this.
- **The ranking holds.** The tunnel fin breaks 4.0° later than either
  slender side in the CFD, 4.4° and 3.9° later by the criterion. The
  criterion separates the flat-inside side from the cambered one by 0.5°
  where the CFD has them level.
- **The level is early by 1.1–1.6°, evenly, and the lift at the knee 3–7 %
  low.** That is the fit, not the form: the share puts the tunnel fin at
  12.0° on the board mirror, which is 11.4° on the perfect mirror these
  runs and a tunnel wall have. 0.745–0.785 would put the three blades on
  their last attached row. The share stays where the tunnel put it: the
  hold floor is what the gen-2 side reads with it (D11), so a common shift
  moves floor and blades together, and level 5 is itself early (13 % below
  the line at 14°, where the tunnel is 6 % below).
- **The centre has no knee of this kind.** Onset is about where the
  criterion has it, but its thin symmetric section lets go gradually and
  the lift keeps climbing at about 80 % of the slope. Hold for a centre fin
  needs its own reading (plan Phase 2).
- **Below the knee the lattice on table v1 carries these rows**: lift
  within 2 % from 4° up to the knee on all three side blades, drag at
  turning load (7–11°) within 1–5 %. At low incidence the flat-inside
  blades read 11–25 % more drag than level 5 and the cambered one within
  4 % down to −3.5°; level 5's friction is a third low, so that gap is not
  all the model's.

## Twelve cambered sections, and a table read the way the model reads it (2026-11-20)

Record: `bench/section-tables/README.md` ("Twelve cambered sections"),
`bench/section-tables/table-v1-nodes.md`, `scripts/build_section_table_v1.py`.

### 1. What the seven new sections say

The edge pass put quarter- to half-degree steps at both ends of the four thin
sections; the third batch added t/c 0.05 (2 and 3 % camber), 0.08 (3 and
4.5 %), 0.12 (3 %), 1 % camber at t/c 0.07, and the 3 % / t/c 0.07 section
again at Re 2.8e5.

- Both ends of the attached range move about a degree per 0.01 of t/c, evenly
  from 0.05 to 0.12 (3 % camber: lower end −2.8 → −8.6°, upper end +6.3 →
  +12.8°). Camber moves the upper end by 0.75° per percent and the lower end
  by 0.35° per percent the other way.
- Reynolds number hardly moves them: 0.2° and 0.1° between 2.8e5 and 5.7e5,
  where table v0 has 0.6° and 0.9°. The minimum drag falls by 9 %.
- Below the lower end the drag jumps from 1.2–1.7 × its minimum to 2.3–5 ×
  within one step of the rows. Table v0 takes a degree for that.

**The blind check.** Before the new sections were used, the v1 of the day
before (five cambered sections) was asked for their ends: ten of fourteen
inside the referee's bracket, four 0.25–0.5° outside (v0: five inside).

### 2. Two faults in how v1 was carried between its sections

Rebuilt on twelve sections with the method of the day before, v1 read the
4.5 % / t/c 0.070 section with its lower end at −4.25° (referee −3.8°) and
its drag at −4.5° at 0.028 (referee 0.045). The builder's own report said
−3.76°. The report checked the builder's formula at the section; the model
reads the shipped file through `sections.polar`.

1. **The file did not contain the referee's Reynolds number.** v0's grid has
   4e5 and 8e5, and 5.7e5 is read as the plain mean of the two. While every
   section was at 5.7e5 the correction was the same at both grid values and
   the mean came out right. With one section at 2.8e5, Reynolds number became
   a direction the corrections vary in, the correction at 4e5 a blend of all
   twelve sections', and the mean wrong.
2. **Above 5.7e5 the ends followed v0's Reynolds-number trend**, three times
   the measured one or more. The root strips of a fin are at 8e5–9.5e5 at
   8.5 m/s: their attached range was read 0.5–1° too wide, in every v1 so far.

Both lower the drag the model reads at −4.5° for a blade whose root sections
are near their lower end — the cambered candidate.

### 3. The builder now

- The two ends are fitted **as the referee has them**. A plane in thickness
  and camber misses the referee's upper ends by 0.20° rms and their distance
  from v0 by 0.57°: v0's ends are irregular, the referee's are not. Each
  section's remainder is spread to its neighbourhood as before, so at a
  section v1 is that section.
- **Reynolds number apart.** Its trend is read where a section was run at
  more than one and applied on top; outside the measured range the ends stay
  where they were last measured. In thickness and camber, outside the
  sections' box, v0's trend carries on from the box's edge as before.
- **The cliff is a mark of its own**: the angle where the drag passes 2.5 ×
  its minimum moves with the lower end, so v1's rise below the lower end is
  as steep as the referee's rows resolve it.
- **Finer grids**: Reynolds number in half octaves (5.7e5 is on the grid),
  angles in quarter degrees from −10 to +14°. The file is 2.7 MB.
- **The report reads the shipped file through the library**, and adds for
  every section the ends a table built without it predicts.

Read through the library, v1 now has every upper end within 0.02° of the
referee, every lower end within 0.05° (4.5 % / t/c 0.092: 0.2°, it lies
between two thickness nodes), and the rows past the cliff within 20 % (v0:
40–60 % low).

**How well the table is known between its sections**: leaving one out, its
lower end is predicted within 0.40° rms and its upper end within 0.43° rms.
The largest misses are at the corners of the box: the upper end of t/c 0.12
comes out 1.3° early — v0's thickness trend flattens above 0.09 where the
referee's does not, which is the trend v1 still follows above 0.12 — and the
lower end of 4.5 % / t/c 0.092 1.1° early.

**What the warp does not carry.** Inside the range the referee's drag rises
with lift earlier than v0's: v1 reads 6–14 % low at +4…+6°, about 3–5 % of a
blade's drag at the working force. And the referee's drag stays flat right up
to the cliff where v0 creeps up: v1 reads 9–19 % high in the last half degree
before the lower end.

The knee share was refitted on the new table (`KNEE_FRACTION` 0.70 → 0.715;
the section's break is now read on quarter degrees): the tunnel fin stays at
12.0° on the board mirror and the survey moves by 0.5° at most
(`bench/knee/survey.md`).

### 4. Against the finer 3-D mesh, again

Level 5, perfect mirror, drag in N (lattice on the rebuilt v1 / CFD):

| own incidence | 3 % camber on the shipped planform (t/c 0.092) | cambered candidate (4.3 %, t/c 0.074) | best fin of the first v1 searches (4.2 %, t/c 0.089) | flat inside, shipped |
|---|---|---|---|---|
| −4.5° | 5.3 / 7.0 | 8.7 / 9.4 | 5.6 / 6.8 | 17.6 / 15.8 |
| −3.5° | 4.7 / 5.4 | 6.1 / 7.1 | 5.4 / 5.5 | 15.0 / 13.0 |
| −2.5° | 4.6 / 4.8 | 5.9 / 6.0 | 5.6 / 5.3 | 12.7 / 10.8 |
| 0° | 5.7 / 5.6 | 7.3 / 7.3 | 7.3 / 7.1 | 10.1 / 8.2 |
| +4° | 10.7 / 11.0 | 13.8 / 14.0 | 13.7 / 13.9 | 13.1 / 11.8 |

- **The candidate at −4.5° went from 6.3 to 8.7 N** (CFD 9.4): its sections
  are past their lower end there, and the table had hidden it. Going straight
  on the board mirror the model now has it at 7.3 N (it was 6.4; level 5:
  7.7).
- **The two blades on thicker sections are unchanged** at 5.3 and 5.6 N
  against 7.0 and 6.8: the referee has t/c 0.09 inside its range at −4.5°.
  That part of the gap is between the referee and the 3-D mesh, not in the
  table.
- From −2.5° to +4° lattice and level 5 agree within 5 % on all three
  cambered blades. The flat-inside blade is 11–24 % high throughout: one
  referee section, its level held for every thickness.

### 5. What the search does on the rebuilt table

`lattice-knee`, six seeds per setting, 6 000 evaluations each (the settings of
"The knee", section 4):

| requirement | seeds agreeing | area mm² | depth mm | camber % | t/c | knee ° | going straight N | at the working force N | hold |
|---|---|---|---|---|---|---|---|---|---|
| moved with gen 2 (hold 0.82, margin ≥ −2.4°) | 4 of 6 | 8 100–9 300 | 137–139 | 3.1–4.3 | 0.088–0.109 | 9.7–10.7 | 4.6–4.8 | 6.7–6.8 | 0.85–0.90 |
| as before (hold 1.15, margin ≥ 2°) | 2 of 6 | 8 840–8 990 | 138–139 | 4.5–4.6 | 0.109 | 13.1–13.2 | 5.3 | 7.2 | 1.14 |

- **The fin for the requirement moved with gen 2 did not change** with the
  table: on the table before it was 8 750–9 390 mm², 2.9–3.6 % camber, t/c
  0.083–0.106, 4.5–5.0 N going straight.
- **The fin for the old requirement shrank from 11 100–11 800 mm² to about
  8 900 mm²**, and went from 3 % to 4.5 % camber. The rebuilt table gives a
  4.5 % section of t/c 0.11 more lift at its break than the old one did
  (upper end +0.75° per percent of camber, +0.95° per 0.01 of t/c), so less
  area carries the same force to the knee. It sits on the most cambered
  section measured and close to the thickest: a corner of the box again.
- **The seeds that do not agree** go where nothing is measured: t/c 0.13–0.21
  at the root (three seeds of the old requirement, one of the new), or 50–60°
  of sweep with a knee at 15–20° (two and one). All of them score worse than
  the fins in the table. Sections of t/c 0.16 and 0.20 are planned; the strip
  criterion has no measured swept blade behind it.
- **A seam in the table, found by a seed and closed.** A cambered foil with
  exactly zero camber was read from the symmetric family's block, which has
  no referee section and is v0 unchanged: its knee sat 2–3° above the 0.5 %
  row next to it, and one seed went to zero camber for it (knee 18°). v1 now
  carries a camber-free row of the cambered family's own
  (`cambered_zero_row` in the table's meta, read by `fingen.sections`).

**With the decision on hold (D11, the same day):** floor 0.72 (the gen-2
side's level), target 0.80, the gate in degrees not applied. Six seeds of six
agree:

| | area mm² | depth mm | camber % | t/c | knee ° | going straight N | at the working force N | hold |
|---|---|---|---|---|---|---|---|---|
| six seeds | 7 050–8 850 | 135–140 | 3.0–4.7 | 0.093–0.132 | 9.0–10.8 | 4.4–4.5 | 6.4–6.6 | 0.78–0.86 |

The six are the same fin in what is scored and not the same fin in shape:
area differs by a quarter, yaw stiffness by ±10 % (227–275 N m/rad), roll
damping by ±11 % (0.39–0.49 N m s). On this part of the frontier looseness
and roll feel are free to choose — which is what a rider's taste is for.

### 6. The controls: the 3-D mesh separates early, and the referee's lower ends are not converged

Record: `bench/section-tables/controls/` (`~/bench-results/gen3ctl`). Three
questions, three answers. A star marks a run that did not settle.

**(a) What do the 3-D mesh's cells read in 2-D?** 4.5 % camber on t/c 0.092
at Re 9.7e5 (a fin's root at 8.5 m/s), resolved wall against wall functions on
the surface cells of mesh level 5 and of level 4; drag coefficient:

| own incidence | resolved wall | wall functions, level-5 cells | wall functions, level-4 cells |
|---|---|---|---|
| +4° | 0.0183 | 0.0145 | 0.0236 (lift 0.75 against 0.95) |
| 0° | 0.0140 | 0.0094 | 0.0126 |
| −2.5° | 0.0127 | 0.0098 | 0.0135 |
| −3.5° | 0.0131 | 0.0130 | 0.0174 |
| −4.5° | 0.0145 | 0.0276 | 0.0342* |
| −6° | 0.0161 | 0.0575* | 0.0618* |

- On level-5 cells the section has a quarter to a third less drag where it
  is attached, and its inside face lets go between −3.5° and −4.5°, where the
  resolved wall holds to −7°. At −4.5° it reads 1.9 × the resolved drag.
- **That is the gap of the level-5 3-D polars at −4.5°** on the two blades
  whose sections the referee has attached (6.8–7.0 N against the model's
  5.3–5.6 N): the wall-function mesh separates early. The model stands
  there, as far as the referee's own lower end does — see (b).
- It also says again why level 5 and the model agree within 5 % from −2.5°
  to +4°: in level 5 a friction deficit and a pressure excess cancel.

**(b) Is the referee converged at the nose?** (Superseded: see "The referee's
nose" below.) The same sections with the
surface one level finer (c/1280 against c/640); lift and drag coefficient:

| section | own incidence | referee (c/640) | finer (c/1280) |
|---|---|---|---|
| 3 % / t/c 0.070 | −2.5° | +0.065, 0.0129 | +0.046, 0.0125 |
| | −4.0° | −0.098, 0.0150 | −0.117, 0.0140 |
| | −4.5° | −0.155, 0.0322* | −0.171, 0.0152 |
| | −6.0° | −0.231, 0.0501* | −0.216, 0.0471* |
| | +8.0° | +1.126, 0.0340 | +1.138, 0.0262 |
| 4.5 % / t/c 0.070 | −3.5° | +0.124, 0.0154 | +0.101, 0.0141 |
| | −4.0° | +0.048, 0.0305* | +0.046, 0.0154 |
| | −4.5° | −0.044, 0.0447* | −0.108, 0.0419* |
| 4.5 % / t/c 0.092 | −4.5° | +0.020, 0.0156 | −0.006, 0.0145 |
| | −6.0° | −0.144, 0.0178 | −0.157, 0.0415* |
| | −7.0° | −0.246, 0.0231 | −0.191, 0.0690* |

- **No.** On the finer mesh the two thin sections stay attached further
  (lower end beyond −4.5° instead of −4.3°; between −4.0° and −4.5° instead
  of −3.8°), and the thicker one lets go EARLIER: separated at −6.0°, where
  the referee holds it to −7.0°. Its lower end lies between −4.5° and −6.0°,
  not at −6.7°.
- The referee's lower ends therefore carry about ± 1° from its own mesh, and
  the finer mesh has them depend much less on thickness: for 4.5 % camber
  about −4.2° at t/c 0.070 and about −5.2° at 0.092, where the referee has
  −3.8° and −6.7°. The leave-one-out of section 3 had already singled this
  section out (predicted −5.6° from the other eleven), and the tunnel polars
  of 9 % sections quoted under "What is provisional in v1" have the corner at
  −4.5° to −5.2°.
- Inside the range the finer mesh has 3–9 % less drag and 0.02 less lift at
  every angle (0.2° of zero-lift angle); at +8° on the thin section 23 %
  less drag, so the upper end is not converged either.

**(c) What does Reynolds number do above 5.7e5?** The 4.5 % / t/c 0.092
section at 9.7e5 on the referee recipe: upper end 11.2° (11.2° at 5.7e5),
lower end −7.0° (−6.7°), minimum drag 7 % lower. The table, which keeps the
ends above 5.7e5, had predicted exactly that upper end and the lower end
0.4° short. Subject to (b): this is the recipe that is not converged there.

**Where this leaves the −4.5° question.** For the 3-D mesh it is answered: at
that angle level 5 is wrong by its wall functions. For the referee it is
not: a fin on t/c 0.09–0.11 toed in 3.5° works at −2.5° to −4.5°, and with the
finer mesh's lower end between −4.5° and −6.0° its margin is 0 to 1.5°, not
the 2° table v1 gives it. Thin sections have more room than v1 says, thick
ones less.

**Superseded on 2026-11-21.** (b), and with it this paragraph on the −4.5°
question, was a finer mesh resolving a wrong nose: see "The referee's nose"
below. (a) and (c) stand; (c)'s section is rerun on the new recipe.

## Three blades the model was not built on (2026-11-20)

Record: `bench/phase2b/`. Everything before this chapter was tested on thruster
side fins and one centre. Three isolated blades for the other setups went
through mesh level 5 (`docs/GEN3-PLAN.md`, Phase 2b): a deep single, the gen-1
centre with twice its thickness, and a keel of the twin kind. The two new
outlines are stand-ins drawn for the run. Lattice at mirror strength 1.0 on
table v1 (`lattice-vs-level5.md` in each folder).

| blade | geometric aspect ratio | 5 % below its own line at | aspect-ratio rule | strip criterion | lattice lift | lattice drag |
|---|---|---|---|---|---|---|
| single, 240 mm deep, raked 45°, symmetric t/c 0.08, 5 m/s | 2.07 | 11.6° | 12.0° | 7.4° | within 2 % from 4° to 12° | 4 % low at 4°, 20 % at 6°, 32 % at 8°, 38 % at 10° |
| gen-1 centre with t/c 0.09 (0.046 as ridden), 8.5 m/s | 1.53 | 9.4° (thin: 9.9°) | 12.0° | 11.6° (thin: 7.3°) | 5 % high from 4° | not read |
| keel, 95 mm deep on a 180 mm base, flat inside t/c 0.10, 7 m/s | 0.61 | never: lift rises above its line from 8° | 23.7° | 26.7° | within 7 % to 26° | 26–32 % high at 0–4°, 19 % low at 16°, 30–36 % low beyond |

- **A raked single loses its drag before its lift.** The strip split
  (`strip-split.md`) shows the outermost strips giving up their lift from 6°
  and the strips just inboard carrying 20–28 % more than the lattice: a tip
  that stalls progressively with a vortex lying on the blade. The loss moves
  inboard with angle (station 232 mm at 6°, 221 at 8°, 204 at 10°). Total
  lift hardly notices; pressure drag at 8° is 14.2 N where the lattice has
  6.6 N of induced drag. The strip model has no such mechanism: its tip
  strips sit at 4–5.5° of section incidence, inside their sections' range.
- **A keel makes vortex lift.** From 8° its lift is above its own line (at
  16° the strips from 72 mm outward carry 0.67–0.90 where the lattice has
  0.55–0.63); between 16° and 18° the drag steps up by 40 % and the rows stop
  converging; lift then climbs on to 1.02 at 26°. The lattice's lift stays
  within 7 % by two errors that cancel (no vortex lift, no loss). What ends
  this blade's useful range is the drag step, and neither rule sees it.
- **The thicker symmetric centre** stays on its line a degree longer and then
  breaks sharply (10 % below at 10°, highest lift 0.56 against 0.63). Table
  v1 on the symmetric family is v0 and says the opposite (criterion 11.6°
  against 7.3°).

**How far this can be trusted.** Level 5 puts 2.2 cells on the nose radius at
the single's root and 0.6 at its station 204 mm, about 3 on the thick centre's
root, 0.75 on the thin one's; and it separates early by its wall functions (the
controls, 6(a)). The next chapter shows what a nose resolved that coarsely is
worth: nothing at the ends of a section's range. So the ANGLE at which the
single's tip starts to stall, and the thick centre's sharp break, are not
established. The direction is: a raked tip goes first and costs drag, a keel's
vortex lift is not small, and the strip model contains neither. Both need a
3-D run with the nose resolved along the whole leading edge before they enter
the model.

## The referee's nose: it was the outline (2026-11-21)

Record: `bench/section-tables/nose/` (laptop, `~/bench-results/meshstudy`).
Section 6(b) of "Twelve cambered sections" left the 2-D referee open: one
surface level finer, its lower ends moved by a degree in either direction.
This chapter closes it, and takes back part of what the two chapters before
it concluded. Test section throughout: 3 % camber, t/c 0.07, chord 0.12 m, Re
5.7e5, nose radius 0.65 mm. A star marks a run that did not settle in 3000
iterations: separated.

### 1. Refining by the mesher's curvature rule is not a refinement series

The referee refined the surface to its finest level where it turns by more
than 30° within a cell. On a thin nose that is the outermost tip (x/c below
0.0005), and less of it at every level. Drag coefficient × 10⁴:

| tip cells by curvature | −4.5° | −5.0° | −5.5° | +8.0° | +8.5° |
|---|---|---|---|---|---|
| 0.19 mm (the referee of table v1) | 322* | 435* | 559* | 340 | 726* |
| 0.094 mm | 152 | 178 | 553* | 270 | 413* |
| 0.047 mm | 147 | 159 | 453* | 254 | 274 |
| 0.023 mm | 145 | 155 | 173 | 252 | 270 |

Every level moves both ends outward and none repeats the one before. A finer
band around the section, a layer stack grown to the face cell and a lower
curvature threshold change nothing.

### 2. The outline the mesher was given

The surface came from `fingen.foil.section_points`: 100 points, cosine
spaced, and two splines, one per side, that meet at the leading edge.

| outline | largest distance from the section within the first 1 % of chord | corner at the leading edge |
|---|---|---|
| 100 points, two splines (the referee) | 32 µm | 33° |
| 100 points, one spline through the leading edge | 39 µm | none |
| 400 points, two splines | 1.8 µm | 9° |
| 400 points, one spline through the leading edge | 1.8 µm | none |

It was also handed over in facets of 5.7°. Cells of 0.19 mm see none of this;
cells of 0.02–0.09 mm mesh the corner, each level a little differently. The
series of section 1 was converging onto the wrong nose.

### 3. Exact outline, cells of one size on the nose: three levels agree

`nose_level` puts cells of one size on the whole surface ahead of 2 % of
chord, one level coarser to 4 %, and so on down to the face cells. Lift
coefficient and drag coefficient × 10⁴:

| nose cells | cells per nose radius | −4.5° | −6.0° | −6.5° | +8.0° | +10.0° | +10.5° |
|---|---|---|---|---|---|---|---|
| 0.094 mm | 7 | −0.1538, 142 | −0.3148, 172 | 501* | 1.1694, 244 | 1.3174, 335 | 1308* |
| 0.047 mm | 14 | −0.1538, 142 | −0.3149, 171 | 497* | 1.1697, 243 | 1.3187, 336 | 1086* |
| 0.023 mm | 28 | −0.1537, 142 | −0.3147, 171 | 504* | 1.1690, 243 | 1.3235, 329 | 888* |
| 0.023 mm, band twice as long | 28 | −0.1536, 142 | −0.3144, 171 | 526* | 1.1683, 244 | 1.3161, 332 | 1210* |
| 0.023 mm, **old outline** | 28 | −0.1531, 144 | 481* | 529* | 1.1617, 252 | 1094* | 1116* |

- **Converged from seven cells per nose radius**: lift within 0.3 % and drag
  within 0.5 % up to half a degree before each end, and the same break —
  attached at −6.0° and +10.0°, separated at −6.5° and +10.5°.
- **The same mesh on the old outline separates a degree early at each end**
  (at −5.5° and +9.5°) and has 2 % more drag at −4.5°, 4 % at +8°, 12 % at
  +9°. That is the price of a 33° corner and 32 µm on a 0.65 mm nose.
- Controls on the exact outline: the same mesh on another process count
  (lift within 0.002, drag 0.4 %), faces one level finer (lift 0.003–0.011
  lower, drag 0.8 %), trailing-edge corners two levels finer (lift
  0.004–0.007 lower, drag 1.2 %). None moves an end. Lift is known to about
  0.01, drag to about 1 %.
- A second section (4.5 % camber, t/c 0.092) at 0.047 and 0.023 mm: equal to
  four digits up to −7.0° and +12°, attached beyond +13° on both, and the
  lower end at −8.0° or later on one and between −7.5° and −8.0° on the
  other. **An end is known to half a degree**: the last attached row is the
  slowest to settle, and a steady solver started from rest decides it by
  details.

### 4. What it takes back

| test section (3 % camber, t/c 0.07) | lower end | upper end |
|---|---|---|
| referee of table v1 | −4.3° | +8.1° |
| table v0 (NeuralFoil) | −5.2° | +10.0° |
| exact outline | between −6.0° and −6.5° | between +10.0° and +10.5° |

- **Table v1 is two degrees narrow at each end on this section**, and v0 was
  closer than the referee it was corrected with: right at the upper end, a
  degree SHORT at the lower. "The table draws the attached range of a thin
  cambered section too wide" (the chapter on the cambered candidate, section
  1) rested on this referee and is withdrawn. What was real in that chapter
  is its section 3: the level-2 3-D mesh.
- **Section 6(b) is superseded**, and with it "thin sections have more room
  than v1 says, thick ones less". Its finer mesh had 4.5 % / t/c 0.092
  separated at −6.0°; on the exact outline that section holds to −7.5°. Both
  kinds have more room.
- **The −4.5° question** (section 6, end): a fin on t/c 0.09–0.11 toed in
  3.5° works at −2.5° to −4.5°. With the lower end at −7.5° its margin is
  three degrees, not the "0 to 1.5°" of that section. For a fin on t/c 0.07
  the margin at −4.5° is a degree and a half where v1 had none.
- **No evidence is left that a thin cambered side fin pays extra going
  straight.** The 2-D referee said so and was wrong; mesh level 5 says so
  and separates early by its wall functions (6(a)). The cambered candidate
  (4.3 % camber, t/c 0.074: v0 model 5.4 N, level 5 7.7 N) is open again
  until the table is rebuilt.
- **The strip knee reads each strip against its section's break.** On
  cambered blades those breaks are up to two degrees early in v1, so their
  knees are early too (the one-degree comparison of "The knee", section 6,
  has the criterion 1.1–1.6° early). The share itself (0.715) is fitted on
  the tunnel fin, whose flat-inside sections this rerun does not touch, and
  so are the three fins that anchor hold. Until the flat-inside family is
  rerun on an exact outline as well, a cambered blade and a flat-inside one
  are read against referees of different quality.
- **The flat-inside family is the next rerun, and not the same problem.**
  Its nose has a real corner where the flat face meets the curved one. What
  a referee needs there is not the exact outline but the corner a fin
  actually has after printing and sanding: a study over the corner's radius.

### 5. What it does not change, and what it suggests

- Mesh level 5 has cells of 0.3 mm and more on a fin's nose. It does not see
  the corner; its early separation is its wall functions and its coarse nose,
  as before. A 3-D referee needs what the 2-D one needed: the exact nose and
  small cells along the whole leading edge. `fingen.loft` draws each section
  with the same two splines and 100 points, so the generated solid has the
  corner; no print and no present mesh resolves it, a resolved-nose mesh
  would.
- An inference, not a measurement: if 32 µm and a corner cost a section a
  degree at each end, a printed leading edge with a seam, a sanding flat or a
  ridge of that size is a nose of the same kind. The leading edge wants to be
  finished smooth and round, with no seam on it; and the ends of a real fin's
  range are known to about a degree whatever a table says.

### 6. The recipe and the rerun

Nose cells 0.023 mm on the first 2 % of chord (14 cells per nose radius on
t/c 0.05), 400 outline points, one spline through the leading edge, facets
of 1.1°, faces 0.375 mm, 13 layers from 9.3 µm: about 68 000 cells, five
minutes per attached row on four cores. The driver now finds each end by
marching outward in half-degree steps until two rows (three at the lower
end) are past it, then one row halfway (`section_polar.py`, `march`).
Eighteen sections run this way from 2026-11-20 23:27Z on three machines: the
table's twelve cambered ones, 4.5 % / t/c 0.092 at Re 9.7e5, and five
symmetric sections (t/c 0.046–0.12), the first referee data for that family.

## What a fast method cannot do — the rest

- **Post-stall magnitude on a low-aspect-ratio swept blade.** Strip methods get
  the order of stall right and the level only roughly; leading-edge vortex lift
  and three-dimensional separation are outside them. Needs the high-angle CFD
  (plan item 0.1b) to calibrate, possibly unsteady.
- **Re-entry and ventilation.** A fin coming back into the water at high
  sideslip, with or without air entrainment. No fast model.
- **The real board under bank.** The upright case is now estimated (section above: 5–7 % centre, 7–12 % sides); a banked board with one rail buried and one lifted is not.
- **Post-knee lift is transition physics** (CFD-BENCH item 5): URANS is a clean null, so the only referee past the knee is experiment or a resolved-wall transition run, and the answer depends on surface finish and on how turbulent the water is.
- **Grooves** are settled on the flow side by the A/B (no benefit, knee penalty); what is unvalidated is their structural model (no FEM anchor for grooved sections).
- **Anything unsteady beyond quasi-steady rates**: dynamic stall in the snap,
  free-surface effects, flex-flow coupling in time.
