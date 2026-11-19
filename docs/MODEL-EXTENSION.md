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
