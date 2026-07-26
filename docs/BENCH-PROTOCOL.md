# Physical stiffness bench — run protocol

Status 2026-07-26. Task #7 (user-side), the structural anchor for the tier-0
flex model (`src/fingen/flex.py`). The rig inverts that beam: push a clamped
blade with a known force at a known spanwise station, measure displacement,
and hand `scripts/bench_intake.py` a CSV that comes back as a material card
(`E_eff_mpa`) — the number that replaces the `E_PLACEHOLDER_MPA = 7000 MPa`
guess flex.py carries today.

**The rig.** 100 kg load cell on a rail sled, SFU1204 ball screw (lead
4 mm) turned by a stepper with an integrated controller, roller/PTFE tip
onto the clamped fin. `displacement = steps · lead / (steps_per_rev ·
microstep)`; `force = load cell`. Three systematics you cannot ignore:
series compliance (frame + cell spring), ball-nut backlash (0.02–0.05 mm at
reversal), and printed-polymer temperature sensitivity (~1–2 %/°C). The
first two are calibrated out below; the third you log and report.

## 0. One-time calibrations (redo only if you touch the rig)

1. **Rig compliance vs a rigid post.** Clamp a steel/aluminium post in
   place of the fin, hard against the tip. Drive the sled in the *same
   force band you use on fins* (0 → ~120 N) and record `force_N,disp_mm`.
   The post barely moves, so what you log is the rig stretching under load —
   frame flex + load-cell spring, in series with any fin. Save it as a
   two-column CSV (`force_N,disp_mm`, header row) and name it in every fin
   run's `compliance_file:` header. The intake interpolates it and subtracts
   `disp_rig(force)` from each sample before fitting stiffness. Redo after
   any re-clamp of the frame or a new load cell.
2. **Backlash (load-free reversal).** With no fin (or the tip clear of it),
   advance a few mm, then command a reversal and watch the *force* stay at
   zero while the screw turns: the microsteps commanded before the tip moves
   again = the nut dead-band. `backlash_mm = dead_band_steps · lead /
   (steps_per_rev · microstep)`. Do it 5×, take the mean; expect
   0.02–0.05 mm. Put it in the `backlash_mm:` header — the intake adds it to
   the unloading branch to close the dead-band.
3. **Session temperature.** Note the shop temperature at the start and end
   of a session in the `temp_C:` header (a mid-clamp probe on the blade is
   better). PET-CF/PAHT-CF read ~1–2 %/°C, so a card measured at 15 °C and
   one at 28 °C are not the same material — the card carries `temp_C` so the
   comparison stays honest. Keep a session inside ±2 °C if you can.

## Test A — stiffness staircase (the headline number)

1. **Clamp.** Print the blade with a rectangular root block below the base
   line. Clamp ≥ 15 mm of that block with the jaws flush to the **base line
   (z = 0)** — that is the model's cantilever root. Everything spanwise is
   measured from the jaw face. Snug the jaws; a soft clamp reads as false
   compliance the rigid-post calibration cannot catch.
2. **Contact station (the moment-match).** You push at one station but you
   care about the *root moment* the fin sees in the water. Reproduce it:
   `F_contact = F_work · (z_cp / z_contact)` where the fractions are span
   fractions (span cancels). Worked example — `WORK_FORCE_N = 120 N` at the
   center of pressure `z_cp ≈ 0.43·span` (`sizing.py` uses 0.45; 0.43 is the
   CFD lift centroid of this foil), pushing at `z_contact = 0.75·span`:
   `F_contact = 120 · 0.43/0.75 = 68.8 N`. On the default 115 mm depth
   that is a 5.93 N·m root moment delivered at the 86.25 mm station. Mark
   the station, set it in `station_mm:`.
3. **Precondition.** 3 cycles to ~80 % of the planned peak, no recording —
   seats the contact and settles first-pull creep.
4. **Staircase.** Step up in ~8–10 even displacement steps to peak, then
   step back down the same steps (record **both** branches — the
   unloading branch is what carries the hysteresis and the backlash check).
   Dwell 1–2 s at each step and average the samples in the dwell (kills load-
   cell noise and lets the step settle). Keep the peak below yield — Test A
   is non-destructive; failure is Test E.
5. Direction `toward_face` or `away_face` (see Test B). One CSV per sweep.

## Test B — bidirectional (toward-face vs away-face)

Repeat Test A pushing the *other* way. Fins are asymmetric (flat-inside
foils; grooves on one face only, doubly so), so the two directions give
different K — that asymmetry is real data, not error. Two cards per station,
`direction:` distinguishes them. Grooved blades especially: the grooved face
in tension vs compression is a different beam.

## Test C — relaxation holds

At 2–3 of the staircase levels, hold displacement fixed for 60–120 s and
keep recording. The force decays (viscoelastic relaxation). The intake fits
`F(t) = F_inf + A·e^(−t/τ)` on each hold and reports τ — the time constant
that tells you how much of the flex is springy vs creepy. Do the holds on
the way up so the seating creep is already out.

## Test D — EI(z) profiling

Run Test A at 2–3 contact stations (e.g. 50 %, 75 %, 90 % span). One E from
one station is a point; three stations that all invert to the same `E_eff`
confirm the beam shape (the tier-0 EI(z)); a drift means the section
schedule or the root-compliance knockdown is off for this print, not the
modulus. Same clamp, same session.

## Test E — displacement-controlled failure (sacrificial)

Print a throwaway blade. **Eye protection on regardless** — CF-filled prints
let go with a snap. Drive *displacement*, not force, and creep up slowly:
past the elastic line you'll see a **force plateau / rollover** (the section
yielding) well before fracture — that plateau, not the break, is the useful
number. Compare peak stress to the design allowables in `sizing.py`
(`_MATERIAL_ALLOW_MPA`: pet-cf 32.75 MPa, paht-cf 31.25 MPa — already
knocked down ×0.5 for print/layup over an SF of 2, so real first-yield
should land well above them, confirming `FORCE_SF = 1.3` has margin).

## Test F — fatigue

Script cycles between two staircase levels overnight (the controller can run
this unattended). Target ~10⁵ cycles for a first screen. Inspect at
intervals (e.g. every 10⁴): re-run a short Test A staircase and watch K —
a softening knee flags a growing crack, usually at the groove band or the
root fillet. Photograph the suspect band each inspection.

## Test G — seawater soak recheck (before the Bali batch)

Soak PET-CF and PAHT-CF coupons/blades in seawater 1 week. Re-run Test A
(same station, same clamp) before and after and compare `E_eff` and K. PET
hydrolyses; PAHT-CF is the wet-service candidate — this test is what decides
which resin ships. Log soak days in the run notes and keep the before/after
cards paired.

## CSV format (what `bench_intake.py` reads)

Header lines start with `#` as `# key: value`; the first non-comment line is
the column header, then the rows.

```
# fin_id: sidefin-petcf-004
# fin_params: out/sidefin-004/fingen-case.json   # or step_ref: sidefin-004.step
# lead_mm: 4.0
# usteps: 16
# steps_per_rev: 200
# spool: NA                 # not a spooled actuator — ball screw; kept for the shared header
# backlash_mm: 0.03
# compliance_file: compliance-rigid-post.csv
# temp_C: 22.5
# station_mm: 86.25
# direction: toward_face     # toward_face | away_face
time_s,steps,force_N
0.00,0,0.05
1.20,480,7.10
...
```

Run it: `uv run python scripts/bench_intake.py run.csv --fin-json
out/sidefin-004/fingen-case.json`. Out comes `run.card.json`
(`E_eff_mpa`, `K_measured`, `R2`, `temp_C`, hysteresis area, relaxation τ,
full provenance) and a dark QC plot (`run.qc.png`: both branches, the fit
line, residuals). Drop `--fin-json` to get K + QC without the modulus
inversion.
