# Manoeuvres — what surfers do, how it is judged, what it asks of the fins

Research note for gen 3 (2026-11-19). Purpose: ground the grading — axes, load
cases, floors — in the manoeuvres riders actually perform and in how the sport
itself scores them, instead of in our own sketch of a "turn". Sources are in
[SOURCES.md](SOURCES.md) §10; web pages were read as data, not authority, and
anything quantitative is flagged with its provenance.

## 1. How the sport grades surfing

The WSL scores each wave 0–10 on five criteria [WSL26]: *commitment and degree
of difficulty; innovative and progressive manoeuvres; combination of major
manoeuvres; variety of manoeuvres; speed, power and flow.* Bands: 2.0–4.9 fair,
5.0–6.4 good, 6.5–7.9 very good, 8.0–10 excellent. A 10 needs all five "in the
critical section of the wave"; the criteria "are weighted toward commitment and
difficulty" [JM26]. Across the 2015 tour, aerials scored higher than tube rides
and turns but were completed only 45 % of the time [For17].

What the judged qualities are, in fin physics:

| judged quality | what the fin has to deliver | our quantity |
|---|---|---|
| speed | low drag at trim AND in the turn; lift at small sideslip while pumping | trim drag, peak-load drag, lift slope |
| power | transmit a large side force without letting go | capacity vs F_peak (hold), tail lateral stiffness |
| flow | predictable re-grip after every release; no snatch | post-break lift shape, re-grip (release axis) |
| commitment in the critical section | hold the hardest turn the wave allows | margin at the peak load, re-entry capacity |
| progressive (tail slides, airs, reverses) | release cleanly on demand, re-grip after rotation | release + re-grip; landing capacity |

Nothing in the criteria rewards drag. "Speed" is always good — the sport's own
grading confirms that `speed` must be a maximised good, never a two-sided
target (docs/GEN3-PLAN.md §Principles).

## 2. Two families of turn

Kelly Slater's distinction (quoted via the search excerpt of [Sla11]; the page
itself blocks automated access): "any successful carving turn is done in the
fins and on the rail. Slides, on the other hand, are done with the rotation
pivoting around the front of the board, ahead of the fins … the fins are just
along for the ride, waiting to grab when you need them … when you release your
fins, you lose speed."

- **Rail turn / carve.** Back foot loaded, nose lifted, rail buried, "a pivot
  point at the tail where the fins are" [BFT]. The fins see a sustained
  side force along an arc. This is the steady banked load case: F = m·g·tan φ
  shared onto the fins, with the stall margin and L/D under load as the
  figures of merit.
- **Pivot / slide.** Weight forward and up, rotation about a point ahead of the
  fins, tail pushed through the water past the fins' break, fins released and
  then re-engaged. Figures of merit: how much the tail resists rotation before
  release (yaw stiffness, the "clock hand" [ST26]), how the lift falls away
  past the break, and how it comes back.

Every manoeuvre below is one of these, a sequence of them, or a flight between
them.

## 3. Catalogue

Technique summaries from [HS26], [Surfd21], [ST26], [BFT], [BC]; fin phases
and load cases are our reading.

| manoeuvre | where / what | technique essentials | fin phases | load case for us |
|---|---|---|---|---|
| trim, pumping | along the face, "using the top third" | weight shifts up/down the face, "good rail work"; speed from gravity | small sideslip, lift at low α; rail-to-rail roll | trim drag, lift slope, roll damping |
| bottom turn | bottom/mid face; sets up everything | lean in, compress, redirect up; *tight* (sharp arc, for snaps/airs) vs *drawn-out* (speed, for slopey waves); exit phase decides what follows [Whi24] | steady rail turn, highest sustained force of the ride | carve case at the rider's bank angle; capacity, margin, L/D under load |
| carve / power carve | mid face, below the lip | "bury that rail", weight on the back foot, nose slightly up; deeper = more radical | rail turn, sustained | carve case |
| cutback | from the shoulder back toward the pocket | at the top shift weight back, lean toward the trough, lead with head and shoulders; buries the outside rail "and engages the fins" | rail turn with a direction reversal; >300°/s peak yaw rate recorded [Pat17] | carve case; yaw stiffness sets how tight it can be |
| roundhouse cutback | figure-of-eight: cutback + rebound off the foam | as cutback, then a second redirect off the whitewater | rail turn → impact/re-grip on the foam | carve case + re-grip |
| snap / off-the-lip | pocket or lip, approach ~30–50° to vertical | deep bottom turn, "get perpendicular to the wave face", at the lip extend the back leg, "push the board away on your back leg", "stay low while the board pivots"; 9.1 m/s entry, >200°/s yaw, 1.77 g peak recorded [Pat17] | drive (tail fully engaged, centre as pivot pin) → release (tail past the break, fins briefly out) → re-grip | snap case: tail lateral stiffness, release shape, re-grip |
| layback snap | top of the wave at the apex of a steep bottom turn | weight to the heels, lean back into the wave, use the wave to stand back up | as snap, longer release | snap case |
| tail slide / fins-free snap | extension of a snap, "high and dry" fins | "enough power to lose your fins", unweight the back foot, hold "until the fins re-engage"; up to 180° | release held deliberately → re-grip under load | re-entry case: capacity at high α, re-grip without snatch |
| reverse, 360 | any section, easiest with whitewater | unweight the back foot, rotate to face the sea, "finish by re-engaging the fins"; pushing the nose into the face "pops the fins out" | full release through 180–360° → re-grip | re-entry case |
| floater | over a breaking section, timed as the lip falls | shallow bottom turn for horizontal speed, weight even, "slide over the top", board flat "not on rail" | fins largely unloaded, board flat; landing shock | landing / re-entry; structural impact |
| foam climb | over already-broken whitewater | as floater; air pockets make it unstable | as floater | as floater |
| closeout re-entry | end of the wave | a snap, floater or airdrop timed to escape the lip | one of the above | — |
| barrel | inside the breaking wave | crouch, centre, stall with a hand or by weighting the tail, "micro rail adjustments", pump inside | small sideslip at high speed, fine trim | trim drag, lift slope at low α |
| aerials (straight air, air reverse, alley-oop, rodeo …) | launched off the lip, landed on the face or flats | bottom turn ~45°, pop off the lip, "kick the tail out", follow the rail through hips and shoulders, compress to land; 45 % completion on tour [For17] | fins unloaded in flight → landing re-grip at arbitrary sideslip | landing case: capacity at high α, structural impact |
| nose riding (longboard) | walking to the nose | out of scope for thrusters | — | — |

## 4. Numbers worth keeping

| quantity | value | source |
|---|---|---|
| mean of per-surfer maximum wave speed, competition | 33.4 ± 6.5 km/h = 9.3 m/s; highest 45 km/h = 12.5 m/s | [Far12] |
| average speed per wave / typical peak wave speed | 16.7 km/h = 4.6 m/s / 25.2 (19–31) km/h = 7.0 m/s | GNSS review summarising Farley et al., via [Far12] search context |
| mean max speed, training session, regional competitors | 35.3 ± 4.9 km/h = 9.8 m/s | Secomb et al., via search context |
| snap: entry speed, peak yaw rate, peak g | 9.13 m/s; >200°/s; 1.77 g | [Pat17], one example ride |
| cutback: peak yaw rate | >300°/s | [Pat17] |
| aerial completion rate, 2015 tour | 45.4 % (55.4 % in finals) | [For17] |

Two inferences, ours, from those numbers:

- **The snap puts the tail past the break by construction.** At 200°/s
  (3.5 rad/s) a tail 0.6–0.8 m behind the rotation centre moves sideways at
  2–3 m/s; against 9 m/s of forward speed that is 13–18° of sideslip from the
  rotation alone, on top of the board's path angle. No fin holds attached flow
  there. Release is not a failure mode of the snap, it is the snap — which is
  why `release` has to become a measured quantity (GEN3-PLAN 0.1b) rather than
  a lore proxy.
- **The 1.77 g peak matches the 55° bank input.** If that reading is the total
  acceleration magnitude, the lateral component is √(1.77² − 1) ≈ 1.46 g, i.e.
  a bank angle of ≈ 55.6°. Our "pro" bank of 55° gives 1.43 g lateral, 1.74 g
  total. One data point, but it says the top of the 30–55° range is real.

Speed band for the rider input (GEN3-PLAN D4/D6): the published spread is
4.6 m/s per-wave average, 7 m/s typical peak, 9–10 m/s mean maximum for
competitive surfers, 12.5 m/s the fastest recorded. A rider's "design speed"
is their typical peak; the "floor" is where they still need the fin to hold,
around the per-wave average. Our PRO default of 8.5 m/s sits at the
competitive mean maximum, which is consistent with Omar's forecast-tagged
sessions.

## 5. What this changes in the grading

1. **Load cases are manoeuvre families, not axes.** Carve (steady, banked,
   F = m·g·tan φ), snap (drive → release → re-grip, yaw ≈ 200°/s), re-entry /
   landing (capacity at high α under the rider's weight), trim / pump (low α,
   drag and lift slope). Every fin quantity we grade should be read in the
   case where the rider meets it.
2. **The centre's job is defined by the snap.** It is the pivot pin ("clock
   hand"); its tail lateral stiffness is what the back foot feels in the drive
   phase, and its post-break behaviour is what the release feels like. Stall
   margin at a banked peak force is the wrong figure of merit for it.
3. **Release and re-grip are first-class.** Tail slides, reverses, airs and
   even the ordinary snap all end in a re-grip. "Flow" in the judging language
   is largely re-grip predictability. This needs high-angle data (0.1b).
4. **The judged "speed" has two halves.** Drag at trim and drag while loaded
   in the carve; the sport never wants more of either. One-sided goods.
5. **No manoeuvre wants a two-sided property.** The only genuine taste
   quantities are how tight the board turns for a given input (yaw stiffness),
   how planted it feels rail to rail (roll damping), and how the tail lets go
   (release shape). Those are the levers; everything else is a good with a floor.
