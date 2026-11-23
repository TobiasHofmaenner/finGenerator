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
     +3 %, slope −7 %; wall functions were the defect) — *withdrawn
     2026-11-21: that mesh had the leading-edge corner, which cancelled the
     model's late break; see "The referee's stream" below.* Table plan: 10
     sections × Re 5.7e5 and 2.8e5, −10…+16° (`~/bench-results/gen3run/tables`).
     First two sections in (`bench/section-tables/`,
     `scripts/section_table_check.py`): on t/c 0.092 table v0 stands where
     the fins trim (drag within 0–12 % from −6° to 0° for the flat section,
     to +4° for the cambered one, lift within 0.03); it is 16–27 % low in
     drag under load (+2…+12°), 3–13 % high in maximum lift, and 2.3–4× low
     in drag past the stall.
     Thin cambered sections in (`bench/section-tables/thin-cambered/`,
     `scripts/section_edges.py`): at t/c 0.070 the attached range is
     −3.5…+8°, two degrees shorter at each end than at t/c 0.092, and the
     table has it a degree or more too wide at both. **The ends of the
     attached range are v1's first job**: carried as quantities of their own
     and polars blended aligned on them, not through them. Third batch
     queued (`~/bench-results/gen3edge`): quarter-degree edge pass, and
     sections at 1–2 % camber, t/c 0.05 and 0.12, and Re 2.8e5 on a thin one.
     Open: no measured polar behind the referee's lower end yet.
     2026-11-20: thin-cambered batch complete — 4.5 % camber on t/c 0.092 is
     attached from −6° to +12°, 2 % on t/c 0.070 from −4.5° to +6°. **Table v1
     is in** (`scripts/build_section_table_v1.py`, `hydro_model="lattice-v1"`):
     v0 warped onto the referee's sections, exact at its five cambered nodes,
     held at the edge of their box outside it (t/c 0.070–0.092, camber
     2–4.5 %, Re 5.7e5). Running: the edge pass and the third batch. Queued
     behind them (`~/bench-results/gen3ctl`): the referee one surface level
     finer around three lower ends, and mesh level 5's cells with wall
     functions in 2-D on the 4.5 % / t/c 0.092 section.
     2026-11-20, later: edge pass and third batch in — **twelve cambered
     sections** (t/c 0.05–0.12, camber 1–4.5 %, one of them at Re 2.8e5).
     Both ends move a degree per 0.01 of t/c, hardly with Reynolds number.
     The v1 of the day before passed a blind check on the seven new sections
     (10 of 14 ends inside the referee's bracket). Rebuilding showed that the
     shipped file did not reproduce its own sections once a second Reynolds
     number was in, and that above Re 5.7e5 it followed v0's trend (root
     strips read 0.5–1° too wide). **Builder reworked**: ends fitted as the
     referee has them, Reynolds number apart, the cliff below the lower end
     as a mark of its own, half-octave Reynolds numbers and quarter-degree
     angles, and a report that reads the shipped file through the library
     with a leave-one-out column (ends known to 0.4° rms between sections).
     The candidate's drag at −4.5° went from 6.3 to 8.7 N (level 5: 9.4).
     **Controls in (`bench/section-tables/controls/`):** (1) the level-5 3-D
     polars' excess at −4.5° is their wall functions: the same cells in 2-D
     separate between −3.5° and −4.5° on a section the resolved wall holds to
     −7° (cd 0.0276 against 0.0145 at −4.5°). (2) **The referee's lower ends
     are not converged**: one surface level finer, thin sections stay attached
     0.25–1.5° further and 4.5 % / t/c 0.092 lets go 0.7–2.2° earlier — about
     ± 1° on every lower end in v1, and less dependence on thickness. (3) Re
     9.7e5: upper end unchanged, lower end 0.4° out.
     **Resolved 2026-11-21 (`bench/section-tables/nose/`): it was the
     outline, not the cell size.** The surface handed to the mesher had 100
     points and two splines meeting at the leading edge: a corner of 33° and
     32 µm off the section at the tip of a 0.65 mm nose, and the mesher's
     curvature rule refined only that tip. With the outline exact (400
     points, one spline through the leading edge) and cells of one size on
     the first 2 % of chord, three mesh levels agree (lift within 0.2 %,
     drag within 0.5 %, the same break), and the test section (3 % / t/c
     0.07) is attached from −6.0° to +10.0° where v1 has −4.3° to +8.1°:
     **two degrees wider at each end.** The same mesh on the old outline
     separates a degree early at each end. Finding (2) is superseded with
     it: 4.5 % / t/c 0.092 holds to −7.5° and beyond +13°. Recipe fixed
     (nose cells 0.023 mm, faces 0.375 mm; finer faces and finer
     trailing-edge corners move lift by 0.01 at most and no end). Eighteen
     sections are being rerun on it (the table's twelve cambered ones, the
     Re 9.7e5 control and five symmetric; the driver marches outward and
     finds each end itself); then v1 is rebuilt, the knee share refitted
     and the searches rerun. Everything that rests on v1's ends — the candidate's
     drag at −4.5°, "a thin cambered section stops being cheap", the hold
     numbers — is to be re-read on the rebuilt table.
   - `[x]` **The builder's own nose (2026-11-21).** `loft._section_sketch`
     drew every section with two splines whose meeting at the leading edge was
     left to the interpolator: the generated solid had the corner too
     (measured on its sketch: 33.4° and 32 µm at 100 points, 8.8° and 2 µm at
     400). Both splines now carry the section's own tangent at that vertex
     (`foil.le_tangent`): no corner at any point count; the shape error is the
     points' (39 µm at 100, 8 µm at 200, 2 µm at 400). The section face is put
     together from its edges, because a build123d sketch concatenates splines
     that meet tangentially and the concatenated curve is a refit (0.1 mm off
     at mid-chord): that, not planarity, is what stopped end tangents before.
     No print and no level-5 mesh sees the difference (cells of 0.3 mm and
     more); a 3-D run with a nose band wants `n_foil_points=400`.
   - `[x]` **The referee's stream (2026-11-21, `bench/section-gate/`).** The
     2-D referee's inlet (5 % turbulence over a tenth of the chord, the 3-D
     recipe's rule, decaying over 20 chords) had never been varied. On the
     NACA 0012 at Re 7e5 it reaches the section with an eddy viscosity 1100
     times the molecular one. Lift is the same in every stream tried; drag is
     12 % above tripped tunnels ([McC87]) and the break a quarter to half a
     degree later than in a quiet stream. A quiet stream is not the answer at
     the table's Reynolds numbers: the model then leaves the layer laminar
     over a fifth to two fifths of the chord at Re 1.4e5 ([RS09]; seen in
     the skin friction). The table moves to a held stream ([SR07]; k = 1e-3
     U², ω = 5 U/c, both kept up to the section): 4.5 % above tripped tunnels
     at Re 7e5, no laminar run at Re 1.4e5. All 35 sections were rerun
     on it, with four more where the upper end jumps (t/c 0.05 to 0.08)
     (`bench/section-tables/rerun-held/`; the old-inlet sections stay in
     `rerun/` as the comparison), and v1 was rebuilt from the 39 on
     2026-11-22 (docs/MODEL-EXTENSION.md, "Section table v1 on the converged
     referee"): the table is the referee at every section (lift within
     0.0013, drag within 1.4 %), the knee share is refitted from 0.715 to
     0.606 with the tunnel fin at 12.0° as before, a section's limit for the
     knee is the most lift it carries attached (`SectionPolar.cl_limit`), and
     D11's floor follows the gen-2 side from 0.72 to 0.70. Against a
     wall ten times finer the table's recipe reads drag 4–5 % low and its
     ends 0.5–1.5° early, on two sections alike (`bench/section-gate/`,
     section 4); proposed: keep the recipe and state the offsets (a decision
     for Tobias; the fin-level check moved side-fin knees by half a degree or
     less). The first
     gate's "passed" is withdrawn with it: on the exact outline the NACA 0012
     peaks 18 % high and 2° late and the NACA 4415 reads 11 % high at 10°, in
     every stream. That is the fully turbulent model, so the table's upper
     ends are upper bounds and the knee share stays fitted on a tunnel fin.
     The 3-D writers take the stream as an option (`held_stream`, off by
     default). The level-5 control (the twin keel alone,
     `bench/phase2b/twin-set/`): drag 5 % lower at 0–4° of incidence, 1–2 %
     at 12–16°, lift 1 % lower; every level-5 polar on record is on the old
     inlet.
   - `[x]` Lattice corrected 2026-11-20 (docs/MODEL-EXTENSION.md, "The
     lattice: control points and induced drag"): control points at the
     middle of each strip's clustering-angle step (lift of ten strips within
     0.3 % of the fine lattice; it was 2.8 % high), induced drag read in the
     far wake (`lattice.far_wake_drag`; the force sum on the bound legs was
     17 % low). The [BW04] drag polar at the tunnel's lift is matched within
     0.002 with the board mirror; level-5 polars at +4° within 3 %. Every
     fin holds 2.8 % less and pays about 0.5 N more at the working force
     than the `lattice` models said before.
   - `[!]` Knee test: resolved-wall 3-D runs DIVERGE within 40 iterations on
     the gen-2 side (59 % layer coverage) and on the [BW04] replica (78 %),
     gentle start included. Parked as its own task: continuation from a low
     angle, or mesh work on the level-4 recipe. Until then the tunnel data
     are the only referee past 12°.
   - `[x]` `fingen.sections` + shipped table v0 (NeuralFoil, tripped) and
     `lattice.solve_viscous` (strip decambering). Tunnel drag polar reproduced
     through the linear range; flat-inside drag at toe angles within 8–12 %
     of CFD; lift 20 % above the tunnel by a constant factor; no knee.
   - `[x]` Grooves: FEM check folded into `flex.py` (GROOVE_NOTCH_K = 0.60,
     GROOVE_STRESS_KT = 1.20; three anchors within 3 %).
   - `[~]` Swap it into `evaluate`: DONE behind `RiderSpec.hydro_model`
     (`"tier0"` default, `"lattice"` opt-in; `bladehydro.py`): lift slope,
     zero-lift angle, CP, trim drag as mounted, drag at the working load.
     Before/after on every archived winner: `scripts/hydro_model_compare.py`.
     Flat-inside sides cost ×3 going straight under the lattice model; a
     re-search with only flat-inside foils dodges that by thinning — so the
     default flips only after camber is searched and the goods are one-sided.
     Still to swap: interference in place of the Falk table, load shape for
     the flex model, roll damping by a rate boundary condition.
   - `[~]` Camber as a searched parameter (D8): IN, opt-in
     (`RiderSpec.side_foil = "cambered"`, one camber gene, 0–5 % at 40 %
     chord). First search: the shipped planform with 4.3 % camber on t/c 0.074.
     Its CFD polar (`bench/cambered-candidate/`) confirms the lift to 0.005 in
     C_L and disputes the drag: 9.9 N going straight against the model's
     5.4 N. Resolved (docs/MODEL-EXTENSION.md, "The cambered candidate was a
     second exploit"): two causes. (1) Table v0 draws the attached range of
     thin cambered sections too wide; with the referee's sections through
     the lattice (`scripts/rans_fed_lattice.py`) the candidate costs 8.0 N
     and is withdrawn. (2) Level-2 and level-3 polars read cambered fins high
     below about −3°: the nose is under-resolved. In 2-D on the same cells
     the sections show +26–43 % at −3.5° (`bench/section-tables/mesh-recipe/`);
     on mesh level 5 (one more surface refinement) the 3 % camber fin drops
     from 6.9 to 5.4 N at −3.5°, within 0.5 N of the lattice with referee
     sections (`bench/cambered-candidate/mesh-level-5/`). Level 5 is the
     recipe for a cambered fin's drag going straight (2026-11-20: the best
     3-D mesh there is, not a referee for the last 10 % — its friction is a
     third low and its pressure drag high, and at −4.5° it reads 1.2–2.4 N
     above the model on fins the 2-D referee has inside their range;
     `bench/cambered-candidate/mesh-level-5-v1-neutral/surface-split.md`).
     A search with
     referee sections goes to ~11 800 mm², depth 121, camber 2.3–2.6 %,
     6.1 N — outside the referee's nodes and pinned to its −3.5° sample, so
     it names the sections to run, not a fin. No cambered fin is exported
     before table v1.
     2026-11-20, on table v1 and the corrected lattice: six neutral searches
     end either on 10 700 mm², depth 140, 4 % camber with t/c 0.12 at the
     base thinning to 0.06 at the tip (6.3 N going straight), or on
     12 500–13 000 mm² with t/c 0.06–0.07 and 2–3 % camber. Both are outside
     the box of the referee's nodes; the sections at t/c 0.05 and 0.12 decide.
     Still no cambered fin to export.
     2026-11-22, on the table rebuilt from the converged referee (39
     sections, inside the box now): five of six seeds under D11 agree on
     8 200–8 900 mm², depth 138–140, 3.3–4.6 % camber on t/c 0.08–0.11,
     4.4–4.6 N going straight, hold 0.79–0.82: the same fin as on the table
     of 11-20 less its smallest versions. What stands between it and an
     export is one check: the drag going straight of a cambered fin rests on
     the 2-D referee (4.6–5.1 N), and mesh level 5 reads 6–9 N on a nose it
     does not resolve (docs/MODEL-EXTENSION.md, "Section table v1 on the
     converged referee", section 6). Either number is far below a flat inside
     face's 12.5 N; the choice of camber does not hang on it, the size of
     the claim does. Mesh level 6 on the first candidate (the same day,
     `bench/cambered-candidate/mesh-level-6-candidate/`): going straight 9.9,
     7.7 and 6.5 N on levels 2, 5 and 6 against the lattice's 5.1 N, on the
     lattice at −2.5°, 12 % above at −3.5°, 57 % at −4.5°. The series is
     still falling; a nose band along the leading edge would end it. On the
     gen-2 planform (`bench/cambered-candidate/mesh-level-6/`) level 6 has
     the flat inside face at 13.1 N going straight (level 5: 13.3, lattice
     12.5: converged) and 3 % camber on t/c 0.092 at 5.0 N (level 5: 5.9,
     lattice 4.6): the factor between the two is a 3-D CFD result now.
     Zero-lift angle tied to toe: still open.
   - `[~]` Fitted separation model for the knee: first cut IN, opt-in
     (2026-11-20, `hydro_model = "lattice-knee"`, `bladehydro.knee`,
     docs/MODEL-EXTENSION.md "The knee"). The blade leaves its line when its
     most loaded strip reaches 0.70 of its section's lift at the section's
     break; 0.70 is fitted on the [BW04] tunnel fin (12°) and then finds the
     knee of all seven side-blade polars within about a degree
     (`scripts/knee_survey.py`, `bench/knee/`). The aspect-ratio rule is 4–6°
     late on every blade slenderer than the tunnel fin: it credited the
     shipped gen-2 side with hold 1.04 where the strips give 0.74 (gen-1 side
     as ridden: 0.61). Misses the symmetric centre (7.2° against ~10°; no
     symmetric referee sections yet). Mesh level 5 in one-degree steps on
     four blades (2026-11-20, `bench/knee/one-degree/`): a side blade breaks
     inside one degree; the criterion ranks the three side blades as the CFD
     does (within 0.5°) and sits 1.1–1.6° early on all of them, lift at the
     knee 3–7 % low — the share is fitted on the board mirror; left as is,
     the hold floor moves with it. (2026-11-22: share 0.606 of the most lift
     the section carries attached, on the rebuilt table; side blades 0.5–1.5°
     early; the measured hydrofoil of [Zar14] is 0–2 % below its line at the
     criterion's angle and 2–5 % two degrees on, so the criterion marks the
     onset and "5 % below" comes two degrees later.) The centre lets go gradually and keeps
     most of its slope: its hold needs its own reading (Phase 2). Below the
     knee the lattice carries lift within 2 % and drag at turning load
     within 1–5 %. **Decided (D11):** what hold is measured against.
     Still open: nonlinear step for stall order. Original note:
     Now with a reason to go first: `hydro.stall_alpha_deg` (break held at 12°
     above AR_eff 2.5, +8° per unit of aspect ratio below) had no bench below
     AR_eff 2.5 and implies a maximum lift that dips 15 % at its kink. The
     kink is what makes an oversized fin a second optimum
     (`docs/MODEL-EXTENSION.md`, "The oversized fin"). `bench/paddle-probe/`
     is the first polar in that range and anchors the linear part there. The
     referee for the knee itself is the [BW04] tunnel fin (lift still rising
     at 24°) and the resolved-wall sections — NOT the steady 3-D polars, which
     flatten past the knee.
   - `[ ]` Discrepancy layer with uncertainty over physical features; the
     verify queue feeds it (D10).
5. `[~]` **C. Scoring rework** (Phase 1 below) — on top of the extended model,
   so the levers are defined on physics that exists. First cut IN, opt-in
   (`RiderSpec.scoring = "frontier"`, items 1.1/1.2 for the side blade): three
   goods in physical units — drag going straight, drag at the working load,
   hold — one-sided, reference-point objective, tastes as optional bands.
   What its first test showed (`scripts/frontier_demo.py`, record in
   `docs/MODEL-EXTENSION.md`):
   - hold and the peak margin are ONE reserve; scoring both made an oversized
     fin a second optimum. Fixed: hold is scored, the margin reported and gated.
   - for the 60 kg pro the speed lever is empty: the lean fin sits on its gates
     (2° peak margin, 140 mm depth corridor, minimum base), so neutral and
     speed-first aspirations return the same fin. Only hold moves the design.
   - area is nearly free in the model (lean → oversized: +1.5 N per fin going
     straight, half a noticeable step, for two steps of hold), and nothing
     contradicts it: in CFD (`bench/paddle-probe/`) the large fin is still
     linear at 12° (409 N), makes the 318 N peak force at 8° for 35 N, and
     costs half a step to one step more going straight. (Its numbers past the
     knee, like every fin's in steady RANS, are lower bounds and settle
     nothing — the tunnel fin keeps lifting to 24°.) What opposes area in the
     water is not in the model; release is the leading hypothesis, untested.
   Open, in this order: **hold as a requirement** at the speed floor of the
   design point instead of an open-ended good (needs D4); **drag at the peak
   force as a good** (item 1.3 — the one place the fins differ by felt
   amounts); **release** — the price of reserve in a snap — as the missing
   counterweight (0.1b, Phase 2 snap case); the gates that bind every lean
   winner (depth corridor = convention; shape sliders on their box edges).
6. `[ ]` **D. Centre fin** (Phase 2). 7. `[ ]` **E. Validation and release** (Phase 3).

Already done from Phase 0: 0.1 frontiers (both riders), 0.4 manoeuvre
catalogue, 0.5 model reach. 0.2 lever audit waits for B2 (its draft ranges
were inflated by the old pivot arm).

**Lever audit, first cut on the present scoring (2026-11-20, `bench/levers/`,
one rider: 60 kg, 55° at 8.5 m/s).** The two drags are results, not levers
(they move by a third of a felt step at most over every sensible setting).
Hold is cheap in drag (0.72 → 1.10 for a quarter of a step). The two tastes
are real levers (yaw stiffness 0.6–1.5 × the baseline, roll damping
0.45–1.6 ×; the fin changes visibly), free within ± 20–25 %, and tied to
each other and to hold through the size of the fin. Consequence for the
rider inputs (1.0, 1.5): ask for hold and for the feel; show the drags as
what comes out. **Also in:** `RiderSpec.bank_deg`, the lean angle of the
design turn given directly (1.0), with `skill` kept for existing rider files.

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
  **State 2026-11-20.** In the library: `RiderSpec.bank_deg` (lean angle
  direct; `speed_ms` was already direct), `hold_min` and the strip-knee floor
  and aspiration (D11). The web quiz now asks exactly these inputs
  (T-FINS-web, branch `quiz-wizard`, `fins/quiz.py`): facts → lean angle and
  speed → grip in reserve → tail and roll feel. **The quiz is kept in step
  with this list**: when an item here changes what a rider can choose, the
  quiz changes in the same piece of work. Not built yet, and what the quiz
  already sends: the two tastes as MULTIPLES of the balanced fin's own yaw
  stiffness and roll damping (`{"tastes": {"yaw_stiffness_nm_rad": 0.8,
  "roll_damping_nm_s": 1.0}}` beside the rider). Turning them into bands
  takes the balanced search first, then a second search with the band — item
  1.7. Open from the plan above: the speed floor as a second input (waits for
  D4), the finish as a logged modifier, `docs/INPUTS.md`.
- `[x]` **1.7 Tastes relative to the balanced fin.** `optimize` wrapper for a
  rider with taste multiples: search the balanced fin (no bands), read its
  yaw stiffness and roll damping, set `taste_bands` from the multiples
  (looser: an upper bound, stiffer: a lower bound, as in `bench/levers/`), and
  search again only if a multiple is off 1. The result reports both fins and,
  per good, the shortfalls in felt steps (`margins.shortfall_*`), which is
  what the quiz's result page draws. The reachable range is not the same for
  every rider (the quiz offers 0.6–1.5 × and 0.45–1.6 ×, from one rider):
  report when a band was not reached.
  *In, 2026-11-22:* `optimize.optimize_with_tastes(rider, tastes, …)` returns
  a `TastedResult`: the balanced fin, the tasted fin (none when every
  multiple is within 2 % of 1), the balanced fin's own two tastes, the bands
  the second search was held to, where its fin ended as multiples of the
  balanced one and whether that is inside the band (3 % tolerance);
  `tasted_result_to_dict` for a worker to write. It takes what the quiz
  sends as it is. Both searches start from the template and use the same
  seed; each gets the full budget. Not done here: the worker in T-FINS-web
  that calls it, and the result page.
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
  *Edge offsets: in, 2026-11-22.* Under frontier scoring the search no longer
  opens the twelve edge offsets unless asked (`RiderSpec.edge_offsets`).
  Drawn for the first time (`bench/design-points/`), the fins they made were
  slender blades on a base flare, the chord spread until five or six strips
  reach the knee criterion together; searched on the sliders and camber
  alone the fin is an ordinary raked one and reads 0.00–0.06 worse in score,
  a tenth of a felt step at most. 3-D polars of both versions for one design
  point (`bench/design-points/cfd/`, 2026-11-23): the plain fin does what
  the model says (lift within 0.004, drag within 6 % from −3.5° to the knee,
  leaves its line at 9.1°); the offset-shaped one leaves its line at the
  same angle and carries 12 % less side force there, where the model had it
  1 % ahead: the offsets had moved the criterion, not the fin. A twin of the
  plain fin with a narrow tip leaves its line 1.5° earlier (criterion: 1.8°),
  the first test of that lever. Still parked on bounds: depth (corridor),
  base (tabs), tip width (0.60).
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

## Phase 2b — the other four fin configurations (added 2026-11-20)

The quiz offers five setups. Generation 3 as it stands can design ONE blade
of one of them: the side fin of a thruster. Everything in B2 and Phase 1 (the
lattice checks, the 3-D polars, the strip knee, the hold anchor, the lever
audit) was done on thruster side fins; the thruster's own centre is Phase 2.

| setup | what the library does today | what is missing before it can be offered |
|---|---|---|
| thruster | side fin: the full generation-3 path. Centre: generation-2 logic (the speed-target defect) | Phase 2 |
| twin | the side fin by the same path, with an ASSUMED load share (0.75); no set run, no anchor for hold | 2b.2 |
| quad | the front fin as if it were a thruster side with an assumed share (0.45); the rear fin is not designed; interference is the thruster centre's, borrowed | 2b.3 |
| single | a symmetric blade on section table v0 (no referee section), and a strip knee that misses the one symmetric blade it was tried on (7.3° against about 10°) | 2b.1, 2b.4 |
| 2 + 1 | sized as if the small side fin were the dominant one; the centre, which carries the turn, is left at the template | 2b.5 |

- `[ ]` **2b.1 Symmetric sections** (shared with Phase 2). 2-D referee
  sections of the symmetric family on the settled mesh recipe (t/c 0.05–0.12,
  two Reynolds numbers), folded into table v1; then the strip knee re-read on
  the gen-1 centre polar and refitted or split by family if it still misses.
  The one-degree polar of that centre (`bench/knee/one-degree/`) shows what
  the reading has to be: its section lets go gradually from 8° and the lift
  keeps climbing at about 80 % of the slope, so a symmetric blade has an
  onset and a slower line after it, not a break. Hold for it is to be
  defined on that, not on the side blade's knee.
  *In, 2026-11-20 (`bench/phase2b/centre-thick/`):* the same centre with
  t/c 0.09 on mesh level 5 stays on its line one degree longer and then
  breaks sharply (10 % below at 10°, highest lift 0.56 against 0.63) — on a
  mesh with three cells per nose radius, so the direction is not
  established. *Running:* five symmetric sections (t/c 0.046–0.12) in the
  2-D rerun on the converged recipe.
  *In, 2026-11-22 (table rebuilt on 39 sections, nine of them symmetric;
  docs/MODEL-EXTENSION.md, "Section table v1 on the converged referee",
  sections 2 and 5):* the strip knee now sits on the thick centre's polar
  (t/c 0.09: 10.0° against 9.4°) and 4–5° before the thin blades' (gen-1
  centre, t/c 0.046: 5.2° against 9.9°; longboard single: 6.3° against
  11.6°). The cause is found. A thin symmetric section's attached range ends
  at 5–7° in a step of drag, with a bubble growing from the nose, and its
  lift goes on rising behind that end at two thirds of the slope (control to
  12°: 0.52 at the end, 0.79 at 9°, 0.90 at 10°). Tunnels are quoted with
  the same kind of kink near 5° on a 6 % section (NACA 64A006, McCullough
  and Gault, NACA TN 2502) and a highest lift of about 0.9 near 9°: from two
  secondary sources found by search, the report itself is still to be read.
  The criterion takes
  its share of the lift at the END, so on these sections it takes a share of
  the kink. On both thin blades the polar starts to leave its line where the
  most loaded strip reaches the kink itself (share 1.0: 8.5° and 10.4°),
  which is the same as 0.6 of a highest lift of 0.85–0.9. Two cautions.
  Those two polars are mesh level 5, with cells of 0.3 mm on a nose of
  0.23 mm radius: no referee for where a thin blade lets go. And by the
  referee's own rows behind the end only t/c 0.046–0.05 is of the kink kind
  (lift held or rising, drag up by a tenth to a half); from t/c 0.06 on a
  section loses 0.1–0.5 of lift there, the symmetric t/c 0.066 and 0.08 of
  the longboard single included, and the one measured symmetric foil
  ([Zar14], t/c 0.09) is on the common share. *To decide (Phase 2):* what a
  thin section's limit is in the table, its lift at the kink with a share of
  one or its highest lift behind the end with the common share. Either
  needs a referee for a thin symmetric blade first: a 3-D run with the nose
  resolved, or a tunnel polar.
  *2026-11-23, two controls and a test.* (1) The gen-1 centre on mesh level
  6: its 5 % point stays at 9.8° (level 5: 9.9°), the onset a degree later
  (`bench/knee/one-degree/`). (2) The thin symmetric section in 2-D on the
  fin recipe (wall functions, the nose cells of levels 5 and 6): it stops
  settling at 5°, its drag steps and its lift goes on, as on the resolved
  referee (`bench/section-tables/mesh-recipe/`). So the fin recipe is not
  blind to that nose, and the centre's polar is what strips of such a
  section give: on the line until the most loaded strip reaches the end of
  its attached range (a share of one: 8.1° on that blade), falling away
  gradually after it. (3) The test of that reading, with the prediction
  written down before the run: the gen-2 side planform with a symmetric foil
  of t/c 0.05, for which a share of one gives 6.3° and the common share
  3.8° (`bench/knee/one-degree/thin-sym-prediction.txt`).
  *In, 2026-11-23: the prediction held.* On both meshes the test blade is on
  its line to 6° and 5 % below it at 8.0°. More than that: the lattice on
  table v1, run through its sections' ends with no criterion at all, has that
  blade's lift within 3 % at every row to 12° and leaves its own line where
  the simulation does, row by row; the same on the gen-1 centre to 10° and on
  the longboard single to 14°, whose most loaded strips turn out to be thin
  too (its thickness tapers to 0.068 at the tip). So for a blade of thin
  symmetric sections the lattice's own polar is the model, and hold can be
  read off it. The thick centre (t/c 0.09) and every side blade still leave
  their line at about 0.6 of what their sections carry, far inside the
  attached range. What separates the two groups was put to a thickness series
  on the gen-2 planform (symmetric t/c 0.050, 0.066, 0.080) with three
  readings and their predictions written first.
  *In, 2026-11-23: the series carries no verdict, because its break is partly
  the mesh's.* On level 5 the three blades are 5 % below their lines at 8.0°,
  8.55° and 8.5°, their outer strips letting go at the same lift whatever the
  thickness; one level finer and half the speed left that where it was. A
  nose split once more (level 7: 2.5–3.2 faces on the nose radius of the outer
  strips, levels 5 and 6 about one) moves the t/c 0.080 blade's 5 % point to
  9.4°, and the sequence 8.5°, 8.7°, 9.4° has not settled. So the level-5 and
  level-6 breaks of blades with thin noses are lower bounds, the three
  readings are open, and a control one level finer is no control when both
  levels are on the same side of what has to be resolved
  (`bench/knee/one-degree/README.md`; count the faces on the nose radius of
  the most loaded strips). What the same runs do establish: read strip by
  strip from the surface pressure, the simulation has the lattice's strip
  lift within 1–2 % on every strip until one lets go.
  *The measured side, same day* (`bench/section-gate/measured/`,
  `docs/SOURCES.md`): three sections measured at Re 1e5–3e5 are members of the
  foil families ([SDF89]), and the table's sections end 5–27 % higher than
  they do, like the gate's NACA 0012 and 4415; the strip criterion is the
  classical method for swept wings ([Maki51], [HM64]: first stall from
  section data, about 20 % early on measured wings and always on that side)
  without its sweep factor; and toward the tip a strip carries more of its
  lift at the nose than its section does in two dimensions ([Pol96]; 1.03 to
  1.24 times on the outer strips of the gen-2 planform, from the lattice).
  The one fitted share stands in for all three. It is fitted on the tunnel
  fin, not on a simulation, and stays as it is until a measured case says
  otherwise.
  *And the surface, found after level 7:* the STL handed to the mesher was
  faceted through a tolerance in the wrong unit (a corner of 51–55° at the
  leading edge of the outer blade, facets 0.066 mm off a nose of 0.25 mm
  radius). Levels 5 and 6 are coarser than that; level 7 is not, so its later
  break is not yet a result either. Fixed in `finGenerator-cfd`
  (`exact_surface`).
  *Running:* the t/c 0.080 blade on the exact surface, levels 6 and 7
  (`bench/knee/one-degree/nose7-prediction.txt`); after it level 7 on the
  gen-3 side fin, the tunnel fin and the gen-2 side; rows behind the upper end
  on seventeen sections, because past 10° the lattice falls short on the
  thin centre where the table levels a thin section's lift off and the
  referee has it rising on.
- `[ ]` **2b.2 Twin.** (a) Set CFD of a twin (two keel-type side fins at
  production toe and cant) over leeway at two speeds, per-fin forces: the load
  share, the toe at which the pair makes no net side force going straight,
  what the two fins do to each other across the board. (b) Isolated 3-D polar
  of that fin on mesh level 5 in one-degree steps through its knee: the strip
  criterion has one low-aspect check so far (the paddle probe). (c) Hold
  anchor: commercial twin templates on the measure over their size-chart
  band. (d) `lattice.set_blades` for the twin against (a).
  *(b) in, 2026-11-20 (`bench/phase2b/twin-keel/`, a stand-in keel 95 mm
  deep on a 180 mm base, flat inside t/c 0.10, 0–26°):* no knee of the
  side-fin kind. Lift rises above its own line from 8° (vortex lift at the
  tip), drag steps up by 40 % between 16° and 18°, lift keeps climbing to
  1.02 at 26°. Neither the aspect-ratio rule nor the strip criterion
  describes it; the lattice's lift stays within 7 % and its drag is 19–36 %
  low beyond 16°. What ends a keel's useful range is the drag step.
  *(a) and (d) in, 2026-11-22 (`bench/phase2b/twin-set/`, two of that keel
  at toe 2°, cant 4°, 7 m/s, mesh level 5, leeway 0–12°):* the two fins do
  not feel each other (the loaded fin within 1–1.5 % of the same fin alone),
  so a twin is two isolated fins at leeway − toe and −leeway − toe. The
  loaded fin's share is not a number: 0.77 at 4° of leeway, 0.68 at 6°, 0.66
  at 8–12°, set by the toe against the foil's zero-lift angle (4.1° here)
  until the unloaded fin, its flat face on the suction side, leaves its line
  near −8…−10° of own incidence. The lattice set has the share within 0.02
  to 6° and then too low (0.59 at 12°): it keeps the unloaded fin on its
  line, 38 % more lift at 12° than the CFD — a strip driven past its
  section's lower end has no knee in the model. Going straight this foil's
  drag is lowest with no toe (9.5 N a fin, 10.8 N at 2°, 13.2 N at the 4.1°
  where it carries nothing). One mesh level finer (1.1 M cells) and at
  4 m/s the shares are the same within 0.02.
  *Open:* (c); a share from the lattice set in place of `sizing`'s 0.75; the
  unloaded fin behind its lower end. The table had no referee rows more
  than 1.5° past a flat inside face's lower end; the seven sections were run
  on to −14° and the table rebuilt on them the same day. Their lift leaves
  its line two degrees past the end and grows on at a third of the slope,
  and with it the lattice reads the four-fin set's front outside fin 51 %
  and 83 % above set CFD at 10° and 15° (before: 69 % and 94 %), the keel's
  unloaded fin 35 % at 12°. The larger part needed a rule for a strip driven
  past its lower end and a referee to fit it on: in, 2026-11-23
  (`bench/phase2b/outside-fin/`, `lattice.held_below`). The gen-2 side alone
  at −6° to −16° levels off from −9° (two meshes agree); a flat-inside
  strip's lift held 1.5° past its lower end follows it within 4 % and puts
  the four-fin set's outside fins within 6 % (front) and 13 % (rear) of
  their set CFD and the keel twin's share at 0.64 against 0.66 at 12°. Not
  closed: the outside fin's drag (19–43 % high in the lattice), and a share
  from the lattice set in place of the fixed numbers.
- `[ ]` **2b.3 Quad.** (a) Validation first: our set CFD on the commercial
  4-fin configuration of [Falk20] against its per-fin forces
  (`bench/falk/falk20_perfin_forces.csv`). (b) Our own quad over leeway at two
  speeds and two rear positions, per-fin forces: what the rear fin sees behind
  the front fin on the same rail, and the split between them. (c) The lattice
  quad against (a) and (b). (d) The rear fin as a designed member: its own
  load share, its incidence in the front fin's wash, its own toe and cant.
  (e) Hold for a rail pair, defined on the pair.
  *(a) and (c) in, 2026-11-21 (`bench/falk/quad-level2/`, `quad-level5/`,
  `quad-level5-foils/`):* with a foil as thin as theirs (t/c 0.065) the front
  inside fin is within 7–9 % of [Falk20]. The linear lattice agrees with our
  set CFD fin by fin on every fin whose flow is attached (27 values within
  0.02 at 5° and 10°, 0.04 at 15°), including what a rear fin loses behind
  the front one. Their rear SPLIT differs from ours while the rear pair's
  total does not: in the lattice 1.5–2° of toe on the rear pair (we had put
  the paper's one value, 3.5°, on all four) gives their rear fins within the
  digitizing error, and the set run with 2° confirms it (rear inside fin
  0.215 / 0.407 / 0.616 against their 0.240 / 0.410 / 0.610; the toe moves
  the same lift between the rear fins in the CFD as in the lattice; the
  rear outside fin stays 0.05–0.08 above theirs at 5° and 10°). The outside front fin lets
  go between 5° and 10° in ours with three foils, at 15° in theirs; neither
  wall-function simulation is a referee for that, and the 2-D referee has
  our cambered foil two degrees past its range there. For (d): rear toe is
  a first-order lever on which rear fin carries the load (1.5° moves
  0.08–0.09 of lift coefficient from the outside rear fin to the inside one,
  lattice and set CFD alike), so the lattice can set it.
- `[ ]` **2b.4 Single.** (a) Isolated 3-D polars of a deep single (the
  reference fleet's 240 mm longboard fin) and of a shortboard-size single,
  4–7 m/s, one-degree steps through the knee. (b) The load case: lean and
  speed of a single-fin turn, with the fin carrying everything; the
  structural case of a deep fin in a US box. (c) Hold anchor: commercial
  singles on the measure.
  *(a) in for the deep single, 2026-11-20 (`bench/phase2b/single-longboard/`,
  a stand-in 240 mm deep raked 45°, symmetric t/c 0.08, 5 m/s):* lift within
  2 % of the lattice from 4° to 12° and 5 % below its line at 11.6°; drag
  20–38 % above the lattice from 6°, because the tip stalls progressively
  with a vortex lying inboard of it (the strip model has neither). The
  angle at which that starts is not established on this mesh. The
  shortboard-size single was not run.
- `[ ]` **2b.5 2 + 1.** (a) The member roles put right: the centre is the
  dominant fin, the sides the small ones (`family_for_config`,
  `sizing.anchor`). (b) Set CFD of a 2 + 1 over leeway, per-fin forces: the
  split. (c) The centre itself comes from 2b.4.
- `[ ]` **2b.6 Lever audit per configuration.** `bench/levers/` repeated for
  one rider of each setup before the quiz offers it: the trades, and the
  ranges of the two tastes, are not the thruster's.

Order: twin (the side-fin path applies; it lacks only its set run and its
anchor), quad (published per-fin data to validate against), single, 2 + 1.
The 2-D sections are running on the converged recipe
(`bench/section-tables/nose/`); the set runs use the wall-function recipe of
the mount study, which is good for load shares at working leeway and not for
the ends of a section's range or past the knee: it separates early
(docs/MODEL-EXTENSION.md, the controls and the nose).

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

- **D12** *(decided 2026-11-20)* What the quiz shows for the four setups
  generation 3 cannot design yet (Phase 2b). **Decided: leave it as it is.**
  The quiz keeps offering all five and its "Fins" page keeps describing what
  each setup gets: the site is a preview, nobody can start a search from it,
  and when generation 3 is complete the page is close to what it should say.
  The condition that goes with it: **before Calculate is switched on**
  (`TFINS_QUIZ_CALCULATE` in T-FINS-web), every setup the quiz offers must be
  one the optimizer can design, or be taken out of the quiz at that moment.

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
- **D11** *(decided 2026-11-20, see the end of this item)* What hold is measured against, once the break is
  read off the blade's own strips ("lattice-knee"). The shipped gen-2 side
  then reads 0.74 of the peak turn force, the gen-1 side that slid 0.61, a
  tunnel-shaped fin of the same area 0.92. Options: (a) keep the peak force
  as it is and set the aspiration relative to a fin known to work (gen-2
  side = 0.74; "a little more" = 0.82); (b) revisit the peak force itself
  with D4; (c) score the force available past the knee as well, once there
  is a model for it. The searches under (a) and under the old number are in
  docs/MODEL-EXTENSION.md, "The knee".
  2026-11-20, later — a second anchor (`scripts/hold_anchor.py`,
  `bench/knee/hold-anchor.md`; rebuilt table, gen-2 side 0.73, gen-1 0.60): a
  commercial medium thruster fin (the [BW04] shape, 14.8 sq in) reads 0.82–0.86
  for a 65 kg rider and 0.67–0.70 for an 80 kg rider, the two ends of the
  weight band size charts sell a medium for, and hardly depends on level
  (lean and speed rise together). Gen 2 for its 60 kg rider sits where that
  fin sits for a 75–80 kg rider; gen 1 where it sits for a 90 kg rider, a
  size too small by the charts. Three facts, one picture: the floor is near
  0.7 on this measure. The number itself is a convention (assumed lean and
  speed; lift continues past the knee); the order of fins and these anchors
  are not.
  **Decided: (a), anchored on the gen-2 side.** Where the knee is read off the
  strips, the floor on hold is the gen-2 side's level and a search aims a
  little above it: `optimize.HOLD_FLOOR_KNEE = 0.72` (the gen-2 side reads
  0.729; agreed as "0.73, gen 2's level" and set a hair under it so that fin
  itself passes) and `HOLD_ASPIRATION_KNEE = 0.80`. `RiderSpec.hold_min`
  overrides the floor. Under those models the gate in degrees
  (`peak_margin_min_deg`, set against the 12° rule) does not apply. There is
  no reason to go lower: at hold 0.85–0.90 the searches still reach 4.6–4.8 N
  going straight against the gen-2 side's 15 N. For the field test: a ladder
  of three fins that differ only in hold (about 0.65 / 0.75 / 0.85) would
  calibrate the floor directly. (b) stays open with D4.
  2026-11-22 — the measure moved with the section table (rebuilt on the
  converged referee, knee share refitted): the gen-2 side reads 0.704, the
  gen-1 side 0.57, the commercial medium fin 0.80–0.85 for a 65 kg rider and
  0.65–0.70 for an 80 kg rider. The floor is the gen-2 side's level by this
  decision and follows it: `HOLD_FLOOR_KNEE = 0.70`. The aspiration is left
  at 0.80 as decided; it was 0.07 above the gen-2 side and is now 0.10 above
  (0.78 would keep the distance). For Tobias to confirm or move.
- **D13** *(open, 2026-11-22)* Which gates a rider from the quiz gets. The
  quiz's job carries the facts, the design turn, the hold target and the two
  tastes, and no gate, so `RiderSpec`'s defaults apply: tab gate at a safety
  factor of 1.0, bending at 1.0, no washout limit. The test rider's files,
  which made the fins ridden in Bali, have the tab gate off, bending at
  1.3–1.7 and washout at 1.5–5 %. The difference designs the fin
  (`bench/design-points/`, nine design turns for a 60 kg rider): on the
  defaults the fin is the same one only at 40° of lean; at 48° it is
  109–115 mm deep instead of 140 mm, with roll damping down to under a half
  and up to most of a step more drag at the working force; at 55° there is
  no feasible fin at any speed, because the hold floor and the tab gate
  cannot both be met. Without the tab gate the same fins read a tab safety
  factor of 0.50–0.98, the shipped gen-2 side 0.53. Options: (a) the test
  rider's practice for everyone (no tab gate, bending 1.5, washout 1.5 %);
  (b) the library defaults as they are; (c) the tab gate on a threshold the
  field supports (his fins hold at 0.53: a gate at about 0.5 would pass them
  and still stop a fin twice as loaded), with (a)'s other two. Item 1.0
  already says gate tolerances become global constants; this is which.
  Until decided, every search result states its gates, and no worker is
  built on the quiz's job as it is.
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
