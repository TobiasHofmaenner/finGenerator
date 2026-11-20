# The knee in one-degree steps (mesh level 5, 2026-11-20)

Question: the stored 3-D polars bracket each blade's knee within 4°. Where is it within the bracket, and does the strip criterion (`bladehydro.knee`) rank blades the way the simulation does?

Four blades on mesh level 5 (wall functions), a symmetry plane at the base, in one-degree steps around the expected knee: the [BW04] tunnel fin replica at 7 m/s, the shipped gen-2 side, the best side of the table-v1 model (4.2 % camber, t/c 0.089) and the gen-1 centre at 8.5 m/s. Plans `plan-knee-*.json`, results `results-*.json` (run on the EPYC, `~/bench-results/gen3ladder`). The rows are in `../survey.md`.

## Lift against its own line

| blade | last row on its line (deviation) | next row | 5 % below at | strip criterion, same mirror | C_L at the last row on the line: simulation / criterion |
|---|---|---|---|---|---|
| tunnel fin [BW04] | 12° (−1.9 %) | 13°: −8.2 % | 12.5° | 11.4° | 0.886 / 0.86 |
| gen-2 side, flat inside | 8° (−2.1 %) | 9°: −7.3 % | 8.6° | 7.0° | 0.721 / 0.67 |
| best table-v1 side, 4.2 % camber | 8° (−1.7 %) | 9°: −7.0 % | 8.6° | 7.5° | 0.780 / 0.74 |
| gen-1 centre, symmetric, t/c 0.046 | 8° (−1.5 %) | 9°: −4.1 %, 10°: −5.1 %, 12°: −7.6 % | 9.9° | 7.3° | 0.447 / 0.41 |

## Reading

- **The three side blades break sharply, inside one degree**: within 2 % of the line at one angle, 7–8 % below it at the next, and every row past it runs to the iteration cap. The centre does not: its thin symmetric section lets go gradually (1.5 % at 8°, 5 % at 10°, 8 % at 12°) and its lift keeps climbing at about 80 % of the slope.
- **The criterion ranks the side blades as the simulation does.** The tunnel fin's knee is 4.0° later than either slender side in the simulation (12.5° against 8.6°); the criterion says 4.4° and 3.9°. It puts the flat-inside side 0.5° earlier than the cambered one where the simulation has them level.
- **Its level is early by 1.1–1.6°, evenly** (5 % point; 0.5–1.0° against the last row on the line), and the lift it reads at the knee is 3–7 % below the simulation's last row on the line. That is the fit: `KNEE_FRACTION` puts the tunnel fin at 12.0° on the board mirror, which is 11.4° on the perfect mirror of a tunnel wall and of these runs. A share of 0.745–0.785 instead of 0.715 would put the three on their last attached row, 0.77–0.82 on their 5 % point. The share is left where the tunnel put it: hold is anchored on what the gen-2 side reads with it (D11), so a common shift moves the floor with the blades; and level 5 is itself early (13 % below the line at 14° where the tunnel is 6 % below).
- **The centre's knee is a different thing.** Onset is where the criterion roughly has it (7.3° against 8–9°), but nothing is lost there. Hold for a centre fin needs its own reading when the centre comes up (plan Phase 2).
- **Lift and drag below the knee** (lattice on table v1, perfect mirror, against these rows): lift within 2 % from 4° to the knee on all three side blades; drag at turning load (7–11°) within 1–5 %. At low incidence the flat-inside blades read 11–25 % more drag than level 5 and the cambered one within 4 % down to −3.5° (−18 % at −4.5°, where level 5 has separated early — `bench/section-tables/controls`). Level 5's friction is a third low (docs/CFD-BENCH.md), so the low-incidence gap on the flat-inside blades is not all the model's.
