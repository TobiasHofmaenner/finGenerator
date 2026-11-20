# Where a blade leaves its lift line (2026-11-20)

Question: tier-0 holds every blade of effective aspect ratio above 2.5 on its lift line up to 12°, the value measured on one tunnel fin ([BW04], geometric aspect ratio 1.5), and later for lower ones. Is that what the stored polars show, and can the lattice say it instead?

`survey.md` is written by `uv run python scripts/knee_survey.py --md=bench/knee/survey.md`: every stored 3-D polar that comes with a fin file, the angle at which it has fallen 5 % below the line through its 0…6° samples, the aspect-ratio rule (`hydro.break_alpha_deg`), and the strip criterion (`bladehydro.knee`: the most loaded strip at 0.715 of the lift its section has at the section's own break). The share is refitted whenever the section table is rebuilt — 0.70 on the table before the twelve-section rebuild of 2026-11-20, 0.715 on it; the survey moved by 0.5° at most.

## Reading

- **The rule is 4–6° late on every side blade slenderer than the tunnel fin.** The shipped gen-2 side, the same planform with 3 % camber (on two meshes), the cambered candidate and the gen-1 side leave their line between 4 and 8° (gen-1: 8–12°); the rule says 12°. Its lift at the break is 1.0–1.15 for these blades, above the highest lift anywhere in their polars (0.66–0.96).
- **The strip criterion, fitted on the tunnel fin alone, lands within about a degree of all seven side-blade polars**: 11.4° on the tunnel fin replica (polar 12–14°), 6.5–7.1° on the five slender ones, 13.4° on the large low fin (12–16°).
- **It misses the one symmetric blade.** The gen-1 centre leaves its line at about 10° (8–12°); the criterion says 7.3°, the rule 12°. The symmetric family has no referee section yet (table v1 is v0 there), and a thin symmetric section stalls differently. Until those sections are in, the criterion is for side blades.
- All of these polars are wall-function RANS in 4° steps: brackets, and soft in the direction of an early knee (the tunnel fin's replica is 5 % below its line at about 12°, the tunnel itself at about 13.6°). The level-5 run in one-degree steps on four blades is in `one-degree/`: a side blade breaks inside one degree, the criterion ranks the three side blades as the simulation does and sits 1.1–1.6° early on all of them, and the centre has no sharp knee.

In the model this is `hydro_model = "lattice-knee"` (opt-in): hold and the peak margin are then read at the strip knee. What it does to the fins on record and to a search: `docs/MODEL-EXTENSION.md`, "The knee".

## What hold can be anchored on

`hold-anchor.md` (`uv run python scripts/hold_anchor.py --md=bench/knee/hold-anchor.md`): hold read at the strip knee for three fins of known behaviour, over riders of 60–90 kg. A commercial medium thruster fin (the [BW04] shape, 9 566 mm² = 14.8 sq in; size charts sell a medium for about 65–80 kg) reads 0.82–0.86 at 65 kg and 0.67–0.70 at 80 kg. The gen-2 side for its 60 kg rider reads 0.73, the gen-1 side that slid 0.60 — what the commercial medium reads for a 90 kg rider. The gen-2 side has less hold than the commercial fin of the same area because it is slenderer and leaves its line 4–5° earlier. Size-chart figures are as relayed by retailers, not from the makers' own pages.
