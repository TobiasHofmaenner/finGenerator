# Which levers a rider would feel (2026-11-20, one rider)

Question (GEN3-PLAN: "a lever must be felt, or it is not offered"): with the scoring as it stands (`scoring="frontier"`, `hydro_model="lattice-knee"`, cambered side foil, hold floor 0.72 and target 0.80), what does moving each rider input actually buy and cost?

One rider: 60 kg, 55° of lean at 8.5 m/s, thruster side fin, PPA-CF, FCS II (the test rider's file in `riders/`). One input moved at a time, 6 000 evaluations per search, 2–3 seeds per point (6 for the baseline). The yardstick for "felt" is the plan's D2 assumption: 5 % of the rider's board drag for the set, i.e. **3.1 N per side fin**; for hold 0.20 of the peak turn force.

Inputs moved: the hold target (`aspirations={"hold": …}`), and a band on each taste as a multiple of the baseline fins' median (`taste_bands`: yaw stiffness 237 N m/rad, roll damping 0.446 N m s; "≤ 0.6 ×" is the band (0, 0.6 × median), "≥ 1.25 ×" the band (1.25 × median, ∞)). Best seed per point; in brackets the range over the seeds.

| point | drag going straight N | drag at the working force N | hold | yaw stiffness N m/rad | roll damping N m s | area mm² | depth mm | sweep ° | camber % |
|---|---|---|---|---|---|---|---|---|---|
| hold target 0.72 | 4.28 | 6.36 | 0.72 | 245 | 0.465 | 8 295 | 140 | 21 | 3.0 |
| **baseline (hold target 0.80)** | 4.41 (4.41–4.52) | 6.44 (6.44–6.61) | 0.78 (0.78–0.86) | 227 (227–275) | 0.391 (0.39–0.49) | 7 084 (7 055–8 846) | 136 | 25 | 4.7 |
| hold target 0.90 | 4.55 | 6.61 | 0.89 | 251 | 0.446 | 7 558 | 138 | 27 | 4.3 |
| hold target 1.00 | 4.99 | 6.86 | 0.97 | 267 | 0.469 | 8 399 | 139 | 27 | 4.5 |
| hold target 1.15 | 5.09 | 7.04 | 1.10 | 252 | 0.497 | 8 563 | 138 | 23 | 4.4 |
| yaw stiffness ≤ 0.6 × (looser) | 4.20 | 7.51 | 0.74 | 144 | 0.195 | 6 723 | 109 | 5 | 5.0 |
| yaw stiffness ≤ 0.8 × | 4.49 | 6.69 | 0.77 | 190 | 0.341 | 7 056 | 129 | 18 | 5.0 |
| yaw stiffness ≥ 1.25 × (stiffer) | 4.74 | 6.73 | 0.80 | 296 | 0.497 | 9 459 | 140 | 30 | 3.0 |
| yaw stiffness ≥ 1.6 × (not reached: 332–368) | 5.75–7.36 | 7.55–9.39 | 0.87–1.65 | 332–368 | 0.54–0.60 | 11 975–15 079 | 140 | 37–57 | 2.3–3.5 |
| roll damping ≤ 0.6 × (quicker) | 4.09 | 6.93 | 0.75 | 194 | 0.267 | 7 415 | 118 | 33 | 3.9 |
| roll damping ≤ 0.8 × | 4.37 | 6.98 | 0.85 | 237 | 0.352 | 8 675 | 125 | 30 | 3.1 |
| roll damping ≥ 1.25 × (calmer) | 5.24 | 7.21 | 1.05 | 288 | 0.579 | 10 483 | 139 | 24 | 2.6 |
| roll damping ≥ 1.6 × | 6.81 | 8.59 | 1.52 | 333 | 0.706 | 14 223 | 140 | 30 | 3.4 |

## Reading

- **The two drags are results, not levers.** Over every sensible setting they move by 4.1–5.2 N going straight and 6.4–7.5 N at the working force: a third of a felt step at most. Only the far stiff and calm ends (a 14 000–15 000 mm² fin) cost a full step.
- **Hold is cheap in drag.** From 0.72 to 1.10, almost two felt steps of hold, costs 0.8 N going straight and 0.7 N at the working force: a quarter of a felt step. The search buys it with camber and section, not area (8 300 → 8 560 mm²), and the feel hardly moves (yaw stiffness 245 → 252, roll damping 0.47 → 0.50). What more hold costs in how the tail releases is not in the model.
- **The tastes are real levers.** Yaw stiffness can be moved from 0.6 × to about 1.5 × the baseline and roll damping from 0.45 × to 1.6 ×, and the fin changes visibly: 109 mm deep and upright at the loose end, 140 mm deep and 15 000 mm² at the stiff end.
- **Within about ± 20–25 % a taste is free** (under 0.5 N either way). The loose and quick ends cost up to 1 N at the working force (a third of a step); the stiff and calm ends cost one step in both drags.
- **The two tastes are tied.** Looser comes with quicker, stiffer with calmer: both follow the size and depth of the fin. Some room remains (at yaw stiffness 190, roll damping 0.27–0.34, through depth against sweep). And a stiffer or calmer fin has more hold whether it was asked for or not (1.05–1.65).
- **Even the baseline's six seeds differ by ± 10 % in both tastes** at the same score: inside that range the choice is free.

One rider, one design point, a model without a release term and with a section table whose lower ends are still under review. The steps of D2 are an assumption, not a measurement.
