# Gen 3 work package — "optimize first, then consult the spider"

Started 2026-11-19. Owner: Tobias. Status legend: `[ ]` open, `[~]` in progress,
`[x]` done, `[?]` needs a decision (listed in §D).

## Why a bigger step

Two defects found in gen 1/2 that small patches cannot fix:

1. **The centre fin.** Gen 1 drove it to the thinnest blade the flex gates
   allow (t/c 0.046, SF and deflection exactly on the limits); gen 2 drove it to
   a t/c 0.17 slab. Same cause, opposite ends: `speed` is a two-sided point
   target, thickness is the only drag knob at fixed planform, and the fleet
   rank turns 0.3 N into 20 points. The centre's design load (Falk steady
   share 0.45) is also unverified against the manoeuvre the rider actually
   feels it in (the snap, back foot over the centre), and nothing checks that
   the centre is in the water when the board is banked.
2. **The objective punishes free improvements.** Four of seven axes are
   monotone goods (speed, drive, hold, forgiveness); the two-sided distance
   taxes overshooting them. Documented instances: the slab; the first gen-2 pro
   search parking peak margin at +0.05° ("spent every other degree on speed");
   the shipped gen-2 side landing at forgiveness 69.8 vs target 70. The
   peak-margin gate was a one-axis patch for this.

Evidence: `bench/mount/` (set CFD: mounting ≤ 7 %, geometry 20–30 %, side env
1.0 and centre env 0.716 confirmed, no t/c lift effect on the centre),
`out/landscape-probe.json` (feasible shell 2–5 % of the cube, non-convex,
condition ~19 000, thickness nearly flat), `out/multistart-*.json` (optima sit
on gates: depth 140.0 ceiling, area-max).

## Principles for gen 3

- **Monotone goods are maximised, not targeted.** Speed, drive, hold,
  forgiveness get floors from the rider and are otherwise pushed to the
  Pareto frontier. Reference-point (achievement) scalarisation, not a
  two-sided distance.
- **Tastes are chosen on the frontier.** Pivot, stability, release (whatever
  survives the audit) are consulted only where improving one costs another.
  Bands, not points.
- **Physical units, rider-scaled.** No six-fin rank. Newtons, L/D, degrees,
  ratios to the rider's own peak force and drag budget.
- **A lever must be felt.** Each offered lever must move its quantity across
  its range by more than a perceptibility threshold (§D2). If the frontier does
  not give that range, the lever is not offered.
- **Thickness is stiffness.** Below t/c ≈ 0.10 it is not a drag knob
  (0.3 N per fin). Flex gates and, if the A/B says so, a felt stiffness
  quantity decide it.
- **The manoeuvre model is the pro's, not our sketch of it (2026-11-19, a second
  pro rider + footage).** There is almost never a steep banked "top turn" where
  the fins approach stall or partly leave the water. The board runs nearly
  straight up the face with the whole tail engaged at low bank; at the apex a
  SNAP yaws the board rapidly, the fins leave the water deliberately for a
  fraction of a second (no control issue), re-enter, and the ride continues in
  a lower cruise turn. Consequences: the steady banked turn (bank angle,
  F_peak = m·g·tan φ, stall margin) describes the bottom turn and rail carves;
  the snap is an impulsive YAW at low bank with the back foot over the centre,
  where the tail's lateral stiffness (force per degree of sideslip, i.e. the
  inverse of our `pivot` quantity) is what the rider feels; the RE-ENTRY after
  the snap is a high-sideslip impact under load where capacity and post-stall
  behaviour decide whether the tail slides. "Not much feedback" from the
  centre reads as low tail lateral stiffness, not as stall or emersion.
  Corroboration (stock images + surfertoday "frontside snap", 2026-11-19):
  the approach is "perpendicular to the wave face" with the tail buried in the
  lip; at the lip "extend your back leg", "stay low while the board pivots and
  completes the arc"; "the thruster's back fin will tighten your turn to keep
  the board working like a clock hand" — the centre is the pivot pin; quads are
  "harder to release the fins when attacking the lip"; the post-snap spray fan
  is the tail skidding at very high sideslip, a controlled release, not a
  failure; a 360 is possible from it. So the snap has three fin phases:
  **drive** (small sideslip, lateral stiffness, centre as fulcrum), **release**
  (sideslip far past the break, the lift must fall off predictably), **re-grip**
  (lift recovers as sideslip comes back, arrests the rotation; a snatchy re-grip
  throws the rider). `release` is therefore not a lore axis to drop — it is the
  physics of the snap we have not measured yet (post-break lift gradient and
  recovery; our polars stop at 16°, the set run has one 20° point).
- **Two load cases, a speed band.** Steady carve (sides dominant, Falk share)
  and snap (centre dominant, foot-station lever-arm split); evaluated at the
  rider's speed floor as well as the design speed (needed CL ∝ 1/V²).

## Order of work (revised 2026-11-19)

Tobias reordered the package: errors first, then the model, then everything
else. The phases below keep their content; this is the sequence.

1. `[x]` **A. Fix the obvious model errors.** Done 2026-11-19, generation
   stamp bumped to 3 (in development), regression tests added:
   pivot arm (signed, board-level — `spider.YAW_ARM_REF_MM`); side-fin trim
   drag read as mounted (`spider.trim_drag_n`); camber no longer converted
   into max lift beyond the validated thickness (`hydro.break_alpha_deg`).
   Known residual of the second: profile drag at negative incidence, ≈ 8 N per
   side fin, waits for section data.
2. `[x]` **B0. Fast-method check, parameter by parameter.** Done:
   `docs/MODEL-EXTENSION.md`, `scripts/vlm_probe.py`. A numpy vortex lattice
   reproduces our CFD lift slopes (1.00–1.13), the set's interference and its
   trends, and the trim toe (3.68° vs 3.65°) at 3–7 ms.
3. `[x]` **B1. Talk about the rest** — done 2026-11-19, all defaults agreed
   (D8–D10 below): foil family tested in CFD; 2-D tables after the recipe
   passes [SK81]; release not offered in gen 3, stall order reported; grooves
   kept as a flex device (A/B flow cost, FEM check of the grooved section);
   edge offsets revisited once the lattice is in; board edge by a lattice
   experiment first, CFD only above 10 %; architecture = lattice + section
   tables + fitted separation model, a thin discrepancy layer with
   uncertainty, the verify queue as the learning loop, every run mined.
4. `[~]` **B2. Build the lattice layer** (D7, approved).
   - `[x]` `src/fingen/lattice.py` + `tests/test_lattice.py` (16 tests: textbook
     wings, the three CFD lift slopes, set interference and its side-offset
     trend, zero-net-force toe, mirror symmetry, convergence, cost). The probe
     scripts now run on the library kernel.
   - `[~]` Section tables: driver `finGenerator-cfd/scripts/section_polar.py`.
     [SK81] gate PASSED with the resolved wall (`bench/section-gate/`: CL_max
     +3 %, slope −7 %; wall functions were the defect). Table plan: 10
     sections × Re 5.7e5 and 2.8e5, −10…+16° (`~/bench-results/gen3run/tables`).
   - `[~]` Knee test: gen-2 side at mesh level 4 (resolved wall), 8 / 12 / 16°
     (`~/bench-results/gen3run/knee`) — are the wall-function 3-D CL_max values
     low, as the section gate suggests?
   - `[ ]` Grooves: fold the FEM check (`bench/groove-fem/`) into `flex.py` —
     softening factor ×1.3–1.7 on the groove increment, stress concentration
     ≈ 1.2 on the band stress.
   - `[ ]` Swap it into `evaluate`: lift slope and CP (pivot arm), interference
     in place of the Falk table, load shape for the flex model, roll damping
     by a rate boundary condition; before/after on every rider spec.
   - `[ ]` Camber as a searched parameter (D8), zero-lift angle tied to toe.
   - `[ ]` Fitted separation model for the knee; nonlinear step for stall order.
   - `[ ]` Discrepancy layer with uncertainty over physical features; the
     verify queue feeds it (D10).
5. `[ ]` **C. Scoring rework** (Phase 1 below) — on top of the extended model,
   so the levers are defined on physics that exists.
6. `[ ]` **D. Centre fin** (Phase 2). 7. `[ ]` **E. Validation and release** (Phase 3).

Already done from Phase 0: 0.1 frontiers (both riders), 0.4 manoeuvre
catalogue, 0.5 model reach. 0.2 lever audit waits for B2 (its draft ranges
were inflated by the old pivot arm).

## Phase 0 — evidence before design (no model change)

- `[~]` **0.1 Frontier characterisation.** Sample the feasible shell for Omar
  (60 kg PRO 8.5 m/s) and a 75 kg intermediate (6.4 m/s); keep the
  non-dominated set in the four monotone goods, in physical units. Report per
  rider: frontier extent per good; which sliders move along it; kinks (knee,
  gates); and the range each taste quantity (yaw stiffness, roll damping,
  release proxy) spans across the frontier. Script
  `scripts/frontier.py`, output `out/frontier-<rider>.json` + a sheet.
  Acceptance: a table "lever → range on the frontier in physical units" for
  both riders. Cost: evaluate is 10 ms, 200k samples ≈ 35 core-minutes.
- `[ ]` **0.1b High-angle polars for release.** Isolated polars at 20/25/30/35°
  for the three field fins (gen-1 side, gen-2 side, ridden centre) on the EPYC,
  steady RANS first (past ~25° treat as indicative, URANS later if it matters).
  Question: does the post-break lift gradient separate the three, and does it
  order them the way the riders did? Decides whether `release` can be a
  measured lever (post-break slope) or stays unoffered.
- `[ ]` **0.2 Lever audit.** From 0.1 plus the perceptibility thresholds (§D2):
  keep / merge / drop for each of the seven axes, with the number that decided
  it. This is the gate for Phase 1. → decision **D1**.
- `[x]` **0.4 Manoeuvre catalogue (done 2026-11-19).** `docs/MANOEUVRES.md`: WSL
  judging criteria mapped onto fin quantities; the carve-vs-slide split; 16
  manoeuvres with fin phases and load cases; published speeds (per-wave
  average ≈ 4.6 m/s, typical peak ≈ 7, competitive mean max ≈ 9–10, fastest
  12.5) and the one published snap telemetry point (9.1 m/s, >200°/s, 1.77 g —
  which matches the 55° bank). Feeds 1.0 (speed band wording), 2.1, 2.2′ and
  the lever audit.
- `[x]` **0.5 Model reach audit (done 2026-11-19).** `docs/MODEL-REACH.md`,
  `scripts/model_reach.py`, `out/model-reach.md`. Hydro sees four numbers
  (area, AR, half-chord sweep, thickness-as-camber); tip width, LE fullness,
  TE shape, the 12 offsets, tip thickness and grooves are invisible to the
  goods. Three defects: the pivot arm is inverted for sweep < 45°; side-fin
  trim drag is read on the isolated fin at +1° while the set CFD says 13.3 N
  per fin at the toe angle vs the model's 8.7; thickness-as-camber is
  extrapolated 1:1 into CL_max far beyond its validation (t/c 0.09–0.10) and
  manufactures the frontier's high-hold corner. → **D7**.
- `[ ]` **0.1c Section data and the foil-family test (updated 2026-11-19).**
  NeuralFoil probe done (`docs/MODEL-EXTENSION.md`): it reproduces zero-lift
  angle and the flat-inside drag at toe angles (11.2 / 15.2 / 19.2 N vs set CFD
  11.2 / 13.3 / 16.1), but over-reads maximum lift by 16–29 % through the
  lattice. Compute, in order: (i) one isolated 3-D polar of the gen-2 side
  planform with `FoilFamily.CAMBERED` 3 % at 40 %, angles −4.5, −3.5, −2.5, 0,
  4, 8, 12, 16°, plus the same negative angles for the flat-inside original —
  tests the claim that the flat inside face costs ≈ 9 N per fin going
  straight — **DONE 2026-11-19** (`bench/foil-family/`, driver
  `finGenerator-cfd/scripts/polar_angles.py`): confirmed, see D8; (ii) 2-D RANS section
  tables on the EPYC — new driver `finGenerator-cfd/scripts/section_polar.py`
  (±20 c graded domain, resolved wall, slab collapsed to a true 2-D mesh);
  [SK81] NACA 0012 gate launched 2026-11-19 (`~/bench-results/section`), the
  old recipe read slope −19 %, CL_max −32 %: flat-inside, cambered 2–3 %, symmetric; t/c 0.05–0.12; Re 3e5 and
  6e5; −10…+16° — referees the section lift limit (tool 1.25–1.40 vs 0.85–1.0
  implied by the fins).
- `[ ]` **0.3 Field anchor set.** The three fins with rider verdicts (gen-1
  sides "sliding in the top turn", gen-2 sides "control way better, a bit of
  drag", gen-1 centre "not much feedback in the snap") become a regression set:
  any new scoring must order them consistently with the verdicts.

## Phase 1 — scoring rework

- `[ ]` **1.0 Input model: facts, design point, preferences.** Decided
  2026-11-19: no presets, no skill or wave-size inputs, no target prior. Three
  kinds of input, kept visibly apart, each with a written definition, unit,
  physics path and "what you will notice" in `docs/INPUTS.md`:

  **Facts** (not choices): weight; mounting system (tabs); fin configuration;
  material. Finish (epoxy coat) logged as a modifier later.

  **Design point** (physics, chosen directly by the rider, explained):

  | input | range | what it sets | what we tell the rider |
  |---|---|---|---|
  | bank angle φ | 30–55° | peak turn force F_peak = m·g·tan φ × fin share; the load the structure is sized for and the stall margin is read at | "how far you lay the board over in your hardest turn": 30° ≈ 0.6 g sideways, cruising turns; 40° ≈ 0.85 g, committed carves; 48° ≈ 1.1 g; 55° ≈ 1.4 g, full-rail pro turn. For a 60 kg rider that is 128 → 318 N on the fin |
  | speed band | design speed and floor, m/s | q at which drag, L/D and capacity are read; the floor sets the needed CL (∝ 1/V²) and the immersion/snap cases | "your down-the-line speed in the waves this set is for": ~5–6 m/s small/soft, ~6.5–8 m/s head-high, ~8–10 m/s big/steep. (Assumption to confirm: both numbers are direct inputs, like φ.) |

  The old `Skill` table (bank 30/40/48/55°, speed 5.5/6.4/7.5/8.5 m/s) stays
  only as a migration map for existing `riders/*.json`; it is no longer an
  input. `default_spider_targets` (the skill/weight prior on the spider) is
  retired. Wave size does not exist as an input; a quiver is two design points.

  **Preferences** (the spider): the surviving taste levers (0.2) as bands, and
  the floors on the monotone goods, forgiveness first, each with a hard
  physical minimum, a suggested value for the chosen design point, and the
  exchange rates from the frontier ("pivot 40 → 70 costs 6 N at trim and 2°
  of margin here"). No prior from anything; the rider chooses.

  Gate tolerances (stress SF, washout, deflection) stop being per-rider fields
  and become global constants, or functions of the design point if the field
  data says so. `area_max_factor`, `practical_corridor` stay developer
  switches. Web quiz follows `docs/INPUTS.md` later (UX, not this package).
- `[ ]` **1.1 Physical-unit axes.** Replace `_normalize` (fleet rank) with
  per-axis physical scales: trim drag and turn-load drag in N relative to the
  rider's estimated board drag; L/D at work and at peak; hold as
  F_max/F_peak; forgiveness in degrees; pivot as yaw stiffness per rider
  moment; stability as roll damping per rider roll inertia. Document each
  scale in `docs/PHYSICS.md`.
- `[ ]` **1.2 Reference-point objective.** Monotone goods: achievement
  scalarising function `max_i w_i (t_i − f_i) + ρ Σ (t_i − f_i)`, targets are
  floors/aspirations, overshoot free and rewarded by ρ. Tastes: band penalty,
  zero inside the band. Gates unchanged except 1.4.
- `[ ]` **1.2a Remove what the model cannot see (option A of MODEL-REACH).**
  Pivot → signed board-level tail lateral stiffness q·A·CLα (no arm); release
  proxy dropped until 0.1b; side-fin trim drag evaluated at the toe angle from
  a curve fitted to the set CFD (toe default 3.5°); flat-inside t/c capped to
  the validated band until 0.1c; stage B (edge offsets) off; shape sliders left
  to structure, roll damping and safety only.
- `[ ]` **1.3 Turn-load drag.** Add drag at the peak force to the drive/speed
  reading (this is where fins differ 3×; trim differs 1.3×).
- `[ ]` **1.4 Fold the peak-margin gate into one-sided forgiveness.** Floor by
  skill (pro 2°, intermediate 5°, cruiser 8°; to confirm), gate removed.
- `[ ]` **1.5 Rider-facing lever descriptions.** For each surviving lever: what
  it changes on the fin, what it costs, what the rider will feel, the range in
  plain words. Lives in `docs/LEVERS.md`, surfaced by the web app later.
- `[ ]` **1.6 Before/after.** `scripts/before_after.py` on every `riders/*.json`
  and on the Phase 0.3 anchor set. Report what moved and why.

## Phase 2 — the centre fin

- `[ ]` **2.1 Snap load case (reformulated 2026-11-19).** Not a banked peak
  turn with a load share. An impulsive yaw at low bank, tail fully immersed,
  back foot over the centre: the centre's job is tail lateral stiffness,
  dF/dβ = q·A·slope·env, and its force at the sideslip the snap builds before
  the fins exit. Quasi-steady first (unsteady lift build-up noted, not
  modelled). The foot-station lever arm still sets how much of the tail load
  the centre takes versus the sides (F_c = F·(x_f − x_s)/(x_c − x_s)); it needs
  board stations and pad kick (→ **D3**). Today's ridden centre has ≈ 0.57 of a
  side's lateral stiffness (area 0.79 × env 0.72), which already reads as the
  complaint.
- `[ ]` **2.2 Immersion gate — premise withdrawn.** The bank-induced
  "centre out of the water in the top turn" picture is not what happens; the
  fins leave the water only in the snap itself, briefly and by intent. Dropped
  unless footage shows a partially emerged tail in the carve. Replaced by
  **2.2′ Re-entry case:** after the snap the fins re-enter at high sideslip
  under the rider's weight; capacity at high α and the shape of the post-stall
  plateau (gen-2 side: 0.80 → 0.83 from 12° to 16°; ridden centre 0.55 → 0.58)
  decide whether the tail slides on landing. Define the re-entry sideslip and
  load from footage (→ **D3**), score as a one-sided floor on capacity at that
  angle.
- `[ ]` **2.3 Speed floor.** Evaluate capacity, forgiveness and the snap case at
  the rider's speed floor (big-wave: 6 m/s), not only the design speed.
- `[ ]` **2.4 Centre role under the new scheme.** Replace
  `_CENTER_TARGET_OVERRIDES` with the centre's own floors and the subset of
  levers that apply to a symmetric blade; keep env 0.716 (confirmed).
- `[ ]` **2.5 Stiffness as a felt quantity (conditional).** If the A/B
  (131/0.066 vs 131/0.090) says the stiffer centre feels better, add tip
  deflection at peak load as a monotone good or a band; otherwise the flex
  gates alone decide thickness. Blocked on field result.

## Phase 3 — validation and release

- `[ ]` **3.1 CFD spot checks** on the new winners for Omar's two specs
  (isolated polars; one set run if the centre changed planform).
- `[ ]` **3.2 Generation 3 stamp**, `docs/PHYSICS.md` §scoring rewrite,
  rider-spec migration (targets → floors/bands), CLI/web surface of levers.
- `[ ]` **3.3 Field loop.** Omar's A/B result, then first gen-3 set; session
  log `riders/omar/sessions.md`.

## Parallel track (in flight, independent of gen 3)

- `[ ]` A/B centres for Omar: ridden template at depth 131, t/c 0.066 and
  0.090, exported through today's gates under the gen-1 spec, isolated polars
  on the EPYC, same epoxy finish as the sides; coat the current centre too.
- `[ ]` Commit: `finGenerator-cfd/scripts/mount_sensitivity{,_report}.py`;
  `finGenerator` `bench/mount/`, `docs/BOARD-METROLOGY.md`, this file.
- `[ ]` Tier-0 parameter and governing-equations sheet (owed since before the
  mount study).
- `[ ]` Backlog, unchanged: slope calibration; speed-axis sensitivity after a
  big-wave session; quads (rear spacing, Falk20).

## D — decisions needed from Tobias

- **D1** Lever survivors (after 0.2). `release`: keep the *concept* (it is the
  snap's release/re-grip physics) but offer it only once 0.1b gives a measured
  post-break quantity; until then the sweep/elliptic proxy is not shown.
  `stability` (roll model uncalibrated): drop unless 0.1 shows a large,
  explainable range. `speed` as a *taste* lever: gone, it becomes a maximised
  good. `pivot` (yaw stiffness): keep, it is the snap's drive phase and the
  "clock hand" the article describes.
- **D2** Perceptibility thresholds. Proposal to confirm or change: a lever
  must move its quantity by at least 5 % of total board drag (≈ 8 N for Omar
  at 8.5 m/s) for drag levers; 2° of margin or 20 % of peak force for
  hold/forgiveness; 30 % of yaw stiffness for pivot; stability TBD after 0.1.
- **D3** Snap- and re-entry-case inputs (footage reviewed with a second pro rider is the source): Omar's board photo with tape (side box offset and
  stations, pad kick position), his back-foot position in the carve and in the
  snap, and a bank-angle assumption (30° default?).
- **D4** Speed band per rider (published anchors in MANOEUVRES.md §4: per-wave average 4.6, typical peak 7, competitive mean max 9–10, fastest 12.5 m/s): design speed and floor (Omar big-wave 8.5 / 6.0?).
- **D6** *(decided 2026-11-19)* No wave-size input, no skill input, no presets:
  the rider sets bank angle (30–55°) and speed band directly and we explain the
  meaning. Presets are a later UX layer. Open sub-point: speed band as two
  direct numbers (design speed + floor) — assumed yes.
- **D7** *(decided 2026-11-19)* Both: fix what is wrong now, then extend the
  model with a vortex-lattice layer and section polars so outline shape, tip
  stall and release become physical. Open sub-decisions: the section-data
  source (NeuralFoil / XFOIL / 2-D RANS tables) and what to do with the
  parameters no fast method covers (docs/MODEL-EXTENSION.md, last section).
- **D8** *(confirmed by CFD 2026-11-19, `bench/foil-family/`)* Foil family as a
  design parameter and a rider lever: inside-face camber from ≈ 2 % (fast in
  trim: 6.4 vs 13.4 N per side fin going straight) to the flat inside face
  (≈ 4.6 % equivalent: less drag above ≈ 150 N per fin, 14 % more maximum
  lift). To build: camber as a searched parameter with section data per
  camber; zero-lift angle tied to the board's toe.
- **D9** *(decided 2026-11-19, all defaults agreed)* "The rest": (1) foil-family CFD test: yes,
  running. (2) 2-D RANS tables: yes, after the recipe passes [SK81]. (3)
  Release: no field referee before ≈ April 2027; post-knee
  is transition physics, so no CFD referee either — not offered in gen 3,
  stall order reported. (4) Grooves and edge offsets: "kind of" — grooves stay
  as a flex device (flow side settled by the A/B: no benefit, knee penalty),
  their structural model needs an FEM anchor; offsets revisited once the
  lattice is in. (5) Board / free surface: lattice experiment DONE
  (`scripts/board_edge_probe.py`): centre −5…7 %, sides −7…12 % of lift slope
  against the infinite wall, driven by distance to the rail and to the tail
  edge; tier-0's 1.7 factor (−9 %) stands; no CFD by the 10 % rule.
- **D10** *(decided 2026-11-19)* Model-fusion architecture
  (docs/MODEL-EXTENSION.md, "How CFD data can extend the fast model"): lattice
  + section tables + a fitted separation model as physics, a thin
  multi-fidelity discrepancy layer with uncertainty, the verify queue as the
  active-learning loop, every run mined for sectional data.
- **D5** Migration policy: do existing riders' shipped designs get re-scored
  and re-offered, or frozen at their generation?
