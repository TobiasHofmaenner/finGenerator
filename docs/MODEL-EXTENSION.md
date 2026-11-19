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

Table v1 therefore has three corrections to carry, in this order of weight:
the stall (maximum lift and what the drag does after it), drag under load,
and the deep negative angles of cambered sections (−8°, −10°: table 0.4–0.6
of RANS). The trim range needs none on these two sections.

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
