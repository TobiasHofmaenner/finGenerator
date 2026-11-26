# The NACA 0012 blades of [Smi21]: two more measured breaks (2026-11-24)

Smith, Brandner, Pearce, Venning, Moreau & Clarke (2021), *J. Fluids and Structures* 102:103225 (`docs/SOURCES.md`). The tunnel of the knee record's one measured fin ([BW04]) and of the hydrofoil of [Zar14]. Two blades with a geometry that can be built exactly: NACA 0012, unswept trapezoid, root chord 120 mm, tip 80 mm, span 240 mm and span 120 mm (a fin's size), hung from the ceiling, forces in half-degree steps up through stall and back down, with the ceiling's boundary layer measured and thickened in steps.

- `measured/`: every curve of the paper's figures 10 and 12–15, read out of the figures' own vector lines (`extract_curves.py`; the paper itself is not in the repository). Normal force, axial force and pitching moment in the paper's body axes, the lift and drag they give, up and down sweeps. 23 conditions: the long blade with 8 % of its span in the ceiling's layer at Re 0.4–1.2·10⁶; both blades at Re 1.0·10⁶ against the depth of immersion.
- `measured-summary.md` (`summary.py`): one line per condition.
- `lattice.md` (`scripts/smith_lattice.py`): the viscous lattice and the strip criterion on the two blades in their thinnest layer.

One thing in the source: in figures 13 and 15 the curves labelled 8 % and 13 % of span are the same points. Figure 10 has the 8 % case at Re 1.0·10⁶ with other values (highest normal force 1.10 at 17.0° against 1.04 at 17.5°). The 8 % case is taken from figure 10 here; `long-b240-Re1.0e6-db0.08.csv` is kept as drawn.

## What was measured

| blade, layer on the blade | Re | lift per degree, 0–4° | lift 5 % below its line (0°, 4°) at | stall on the way up after | back on the up-curve from |
|---|---|---|---|---|---|
| long (span 240 mm), 8 % of span | 0.4·10⁶ | 0.0689 | 13.2° | 16.0° | 13.5° |
| | 0.6·10⁶ | 0.0659 | 15.8° | 17.5° | 14.0° |
| | 0.8·10⁶ | 0.0665 | 16.6° | 16.5° | 14.5° |
| | 1.0·10⁶ | 0.0672 | 17.1° | 17.0° | 14.5° |
| short (span 120 mm), 16 % of span | 1.0·10⁶ | 0.0462 | 21.4° | 21.0° | 17.0° |
| short, 27–47 % | 1.0·10⁶ | 0.0448–0.0436 | 22.1–23.2° | 22.0–23.0° | 17.5–19.0° |
| short, 59–90 % | 1.0·10⁶ | 0.0430–0.0401 | 22.9–24.2° | gradual, highest at 22.5–24.5° | – |
| long, 13–45 % | 1.0·10⁶ | 0.0655–0.0607 | 16.9–16.0° | 18.0–19.0° | 15.0–17.5° |

- **Both blades hold their line to the stall and then drop at once** (normal force from 1.0–1.1 to 0.7–0.8 within half a degree) as long as less than half the span is in the ceiling's layer. The authors read the stall, and a bump in the slope before it (0.066 per degree rising to 0.08 between 5° and 9° on the long blade), as a laminar separation bubble that shortens and bursts.
- **The Reynolds number moves the 5 % point by four degrees on the long blade** (13.2° at 0.4·10⁶, 17.1° at 1.0·10⁶), the stall itself by one. The bump comes earlier at low Reynolds number and steepens the line the 5 % is measured from.
- **The wall's layer moves the stall by two degrees on the short blade** (21.0° with 16 % of the span in it, 23.0° with 47 %) and makes it gradual from 59 % on.
- **A blade that has stalled comes back 2.5° to 4° lower** (3° to 5.5° by the paper's reading of its loops).
- Drag at zero lift: 0.0072–0.0093 on the long blade, falling with Reynolds number; 0.0107 on the short one.

## Against the lattice and the strip criterion (`lattice.md`)

| blade | Re | lift per degree: measured / lattice | measured 5 % point | lattice's own polar 5 % below at | most loaded strip at the measured stall: share of its section's limit, margin to the section's end | strip criterion (share 0.606) |
|---|---|---|---|---|---|---|
| long | 0.4·10⁶ | 0.0689 / 0.0688 | 13.2° | 14.9° | 0.95, +0.8° | 9.3° |
| long | 0.6·10⁶ | 0.0659 / 0.0693 | 15.8° | 16.2° | 0.97, +0.6° | 10.0° |
| long | 0.8·10⁶ | 0.0665 / 0.0696 | 16.6° | 16.6° | 0.91, +1.7° | 10.2° |
| long | 1.0·10⁶ | 0.0672 / 0.0697 | 17.1° | 16.7° | 0.92, +1.6° | 10.4° |
| short | 1.0·10⁶ | 0.0462 / 0.0492 | 21.4° | 20.6° | 0.81, +3.2° | 14.4° |

- **The lattice has the lift slope within 0–6 %**, high where the blade stands in the wall's layer (a uniform stream in the lattice: 4–5 % on the long blade from Re 0.6·10⁶, 6 % on the short one).
- **Run to the ends of its sections, the lattice has the 5 % point within 0.8° of the measurement on both blades from Re 0.6·10⁶** (1.7° late at 0.4·10⁶). These blades follow their sections to the end: at the measured stall the most loaded strip is at 0.81–0.97 of the most lift its section carries attached, 0.6° to 3.2° before the section's own end. The section here is the table's symmetric t/c 0.12, which the 2-D gate has high and late against [SK81] (`../section-gate/`): on these two blades that end is where the measurement is.
- **The strip criterion is six to seven degrees early on them.** At the angle it gives, the measured lift is 4–10 % *above* its line (the bump), and still above it two degrees on. Its share of 0.606 was set on fins; the measured blades now span 0.7 (the tunnel fin, 25° of sweep, flat inside, t/c 0.09), 0.76–0.84 (the hydrofoil of [Zar14], unswept, t/c 0.09) and 0.81–0.97 (these, unswept, t/c 0.12).
- **So the share at which a blade lets go is not one number, and the measurements order it by the nose**: the thicker and rounder the section, the nearer the blade comes to its section's own limit. *(Corrected 2026-11-25: by the suction side's height at 1.25 % chord the tunnel fin has the bluntest nose of the three and the smallest share; what orders them is the kind of stall, `../knee/one-degree/README.md`, "The blades by Gault's ordinate".)* The simulations of the knee record say the same in their way (0.66–0.75 on narrow tips with small noses, 0.77–0.81 on the wide-tipped cambered fin). That is the classical reading (a wing stalls where a strip reaches its section's maximum, less for thin noses and sweep; [Maki51], [HM64], [Pol96]). Nothing in `bladehydro.knee` is changed by this.

## What this does not settle

- The measured stalls are a bubble's, on polished blades in a quiet tunnel; the section table and every 3-D simulation of the record are turbulent from the nose. That the lattice lands on them is an agreement of two different mechanisms at one angle, at Reynolds numbers of 0.6–1.0·10⁶.
- A fin under a board stands in the board's boundary layer and in broken water, sanded and coated. The paper's own series says such a layer delays the stall and softens it. Which reference binds a fin in the sea is open.
- Simulated in 3-D on the knee record's recipe, 2026-11-25/26 (`knee/`): the short blade is within 2 % of the measured lift at 12° and stalled at 16°, five degrees before the tunnel. The recipe's wall functions do not carry this nose's suction peak; the first bullet's expectation (a simulation turbulent from the nose at least as late as the tunnel) did not hold.
