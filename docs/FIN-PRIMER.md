# Fin physics & systems primer

A plain-language reference for how surf fins work and what the different systems are.
Citation keys (`[BW04]` etc.) refer to [SOURCES.md](SOURCES.md); the implementable math
lives in [PHYSICS.md](PHYSICS.md).

## 1. The physics core

### A fin is a low-aspect-ratio swept wing at leeway

The board drifts slightly sideways relative to its velocity vector; that drift angle is the
fin's angle of attack (AoA). Everything a fin does — drive, hold, pivot — is side force
generated at that AoA: F = ½ρV²·A·C_L.

Envelope numbers: mean riding speed 6.4 m/s, top ~10 m/s (GPS-measured) [Forsyth24, Far12];
chord Reynolds numbers 3×10⁵–10⁶ [BW04]. Measured in-service loads: **~300 N per fin**,
pressure differentials 14–20 kPa [Knies25]; tip flex ~10% of depth while riding [Krz24].
Rule of thumb: a loaded fin carries about a third of the rider's weight in side force.

### Three regimes of the lift curve

1. **Linear** at small AoA — slope set by the DATCOM swept-wing formula [DAT78], with the
   board acting as a reflection plane that nearly doubles effective aspect ratio [Hem28, Hoe75].
2. **Nonlinear vortex boost** as AoA grows — tip/edge vorticity adds lift (Polhamus suction
   analogy [Pol66, Tra23]); this is why low-aspect fins are forgiving.
3. **Lift-curve break at α ≈ 12–14°** — measured on a real fin, nearly Reynolds-independent;
   a mix of tip stall and trailing-edge stall [BW04].

### Spin-out is ventilation

Two conditions must both hold [Swa74, Har16]: separated (or cavitating) suction-side flow
**and** an air path from the free surface (the surface "seal" ruptures). A fin whose flow
stays attached cannot naturally ventilate — so **stall margin is the spin-out guard**. The
margin tightens with speed (depth-Froude-number effect [You17, AF26]), and the lift loss is
abrupt and hysteretic [Har16] — the tail lets go all at once and doesn't immediately re-grip.
Cavitation needs ≳10–15 m/s at fin depths [Bre95]: tow-in territory, not everyday surfing.

### Turning is a force balance

The rider banks; the turn needs centripetal force M·v²/R, supplied by fins + rail
[SH-turn, ShormISEA20, Falk19]. Skill maps to turn-rate demand: measured cutbacks take
~0.35 s (pro) vs ~0.55 s (intermediate) at the same 7 m/s [ShormISEA20]. That converts
"surf style" into an engineering requirement:
style → turn radius/rate → required side force → fin area at a design C_L safely below stall.

### Low-Reynolds subtlety

In small/slow waves (Re ~10⁵), laminar separation bubbles degrade thick sections badly —
thin sections win [Win18, Sel95, Ren26]. Section thickness should be a function of design
speed, not a constant.

## 2. Systems by fin count

Each configuration answers "where does the side force come from, at what drag cost":

| Config | Layout | Physics |
|---|---|---|
| **Single** | one large 50/50 center fin, no toe/cant | A rudder/keel in the naval-architecture sense: all hold, long moment arm, drawn-out pivots. Longboards/mids. |
| **Twin** | two canted, cambered side fins | Fast (no center-fin drag), loose; missing center fin = less yaw damping, less hold at speed. Fish, small waves. |
| **Thruster** | 2 toed/canted side fins + symmetric center | Toe-in (~3.5°) pre-loads the system: the outside fin reaches working AoA instantly. Center fin is symmetric (works both directions) and restores yaw stability. An *interacting* system, not three isolated foils [Falk19]. |
| **Quad** | 4 fins, no center | CFD: quads make **more lift and more drag** than thrusters over most of the AoA range [Falk20] (contra marketing "quads are faster"). Trade: hold-without-center-fin near the rail (barrels) vs thruster centerline stability. Rear-fin position measurably moves the lift/drag balance [Falk20]. |
| **2+1** | single box + small sides | Mid-length compromise, tunable between single and thruster feel. |
| **5-fin** | five boxes | A convertible (thruster or quad), not five-fin surfing. |

## 3. Systems by template (planform style)

The rake/upright spectrum — our sweep parameter:

- **Raked/swept** (sweep ≳ 33°): center of pressure moves aft → longer moment arm to the
  surfer's pivot → drawn-out carves, more hold, forgiving stall. Point-break and big-wave
  templates; fish keels are the extreme.
- **Upright/pivot** (sweep ≲ 30°): shorter moment arm → tighter initiation, quicker release.
  High-performance shortboard templates.
- Industry recognition that rake is the primary style axis: Futures publishes a "Ride Number"
  spectrum from speed-control (raked) to speed-generating (upright) [Fut26].

## 4. Systems by foil (cross-section)

- **50/50 symmetric** — center fins; must work in both directions [FCS26].
- **Flat foil** — side fins: flat inner face, all shape outboard; effectively camber pointed
  into the turn. This is the canonical measured fin [BW04] and what FCS/Futures ship
  [FCS26, Fut26].
- **70/30, 80/20** — partial camber; 2+1 sides, some quads.
- **Inside foil** — concave inner face; more lift at low AoA, more drag; premium option.

## 5. Placement parameters

- **Toe-in** (~3.5° fronts [Gre26, Falk20]): trades straight-line drag for turn responsiveness.
- **Cant** (~8° fronts, 3–5° quad rears [Gre26, Falk20]): tilts the lift vector so it stays
  useful as the board rolls onto rail.
- **Fore-aft cluster position**: sets the moment arm — forward = pivoty, back = drive.

## 6. Mount systems (deferred)

FCS II dual tabs, Futures single long tab, longboard US box. The hydrodynamics above is
independent of the mount — it is a pure mechanical-interface problem, which is why fingen
starts with a flat base and adds tab systems later.

## 7. The parameter vector

Everything above collapses into one vector per fin set — configuration, area, depth/base,
sweep, foil family + thickness, toe/cant, position — where every axis has a physical
mechanism and a citable source. That vector is what `fingen` generates geometry from and
what the optimizer will eventually search over.
