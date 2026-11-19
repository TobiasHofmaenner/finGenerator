# Grooved-section FEM check (2026-11-19)

Question (gen-3 decision D9.4): grooves stay in the design space as a flex
device, but their structural model in `flex.py` had never been compared with a
3-D solve ("Fitted at t/c 0.09, flat-inside, no grooves"). Blade: Omar's shipped
gen-2 side, PPA-CF, 317.7 N peak load, `scripts/validate_fin_fem.py` (gmsh +
CalculiX, C3D10, element size 1.4 mm). Groove geometry: 60 mm long, 3 mm wide,
6 mm pitch, outer face.

| variant | tip deflection tier-0 mm | FEM mm | FEM / tier-0 | softening vs plain, tier-0 | softening vs plain, FEM | band stress tier-0 MPa | FEM p99.9 MPa | FEM raw max MPa |
|---|---|---|---|---|---|---|---|---|
| plain | 6.99 | 5.02 | 0.72 | – | – | 17.4 | 16.3 | 16.6 |
| 3 grooves, depth 0.35 t, from 45 % span | 7.50 | 5.57 | 0.74 | +7 % | +11 % | 31.7 | 21.2 | 29.6 |
| 6 grooves, depth 0.35 t, from 45 % span | 8.03 | 6.02 | 0.75 | +15 % | +20 % | 34.2 | 23.9 | 41.0 |
| 6 grooves, depth 0.50 t, from 30 % span | 8.70 | 7.08 | 0.81 | +24 % | +41 % | 45.7 | 28.2 | 50.9 |

Reading:
- **Direction right, size short.** The beam model captures 60–75 % of the
  softening grooves cause, and the gap grows with groove depth. As a flex
  lever, grooves are stronger than tier-0 says: six deep grooves add 41 % tip
  deflection, not 24 %.
- **Local stress peaks are missed.** Tier-0's groove-band stress is above the
  FEM's 99.9th percentile but below its raw maximum for the six-groove cases
  (41 and 51 MPa against 34 and 46): the groove roots concentrate stress. Against
  the 62 MPa allowable that is a local safety factor of 1.2–1.5 at the peak
  load — a fatigue question the beam cannot see.
- **Separate observation:** on this blade the plain beam model is 39 % too soft
  (6.99 vs 5.02 mm), so the deflection and washout gates are conservative by
  about that much here.
- Use: a calibration of the groove softening (×1.3–1.7 on the tier-0
  increment, depth-dependent) and a stress-concentration factor of about 1.2
  on the band stress — a small instance of extending the fast model with
  numerical data. Flow side: see `bench/groove-ab` (no benefit, knee penalty).
