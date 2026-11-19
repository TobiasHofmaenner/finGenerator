# Mount-parameter perturbation study (set CFD, 2026-11-13)

Question: how much of a thruster set's steady hydrodynamics is MOUNTING (toe,
cant, side-fin station and offset — glassed into the board) and how much is
BLADE GEOMETRY (what the optimizer actually designs)? If mounting dominated,
the optimizer would be tuning the small part and every rider would need a
measured board model (`docs/BOARD-METROLOGY.md`).

Set-up: `fincfd.setcase` placed THRUSTER, 8.5 m/s, leeway 0/5/10/20°, mesh
level 2 (~430k cells), 1500 it, 8 procs on the EPYC, driver
`finGenerator-cfd/scripts/mount_sensitivity.py`, report
`finGenerator-cfd/scripts/mount_sensitivity_report.py`. Blades: Omar's shipped
gen-2 big-wave side (`fins/side-shipped-gen2.json`) + the gen-1 centre he rides
(`fins/centre-ridden-gen1.json`); geometry yardsticks swap in the gen-1 side he
rode before (`fins/side-asridden-gen1.json`) or deepen the centre to 131 mm
(with and without t/c 0.09). Baseline placement toe 3.5°, cant 8°, side_x −195,
side_y 118; mount cases are ± pairs around it: toe 2.5/4.5, cant 6/10,
side_y 103/133, side_x −170/−220. `plan.json` is the exact input; `results.json`
the per-fin coefficients (each referenced to its own planform area; see
`fingen-set-case-baseline-a05.json`); `final-report.md` the tornado and the
isolated-polar overlay. Raw cases live on the EPYC at `~/bench-results/mount/prod/`.

Headline:
- Mount envelope moves the set side force ≤ 7 % (toe −5.6/−7.4/+1.9 % at
  5/10/20°; cant ≤ 1.6 %; side_y 3–5 %; side_x ≤ 1 %). Centre share ≤ 3 pp.
- Geometry: swapping the side blade moves it 18–22 %; +22 mm centre depth moves
  the centre force +25–33 % (set +3–7 %).
- Toe acts at trim and small leeway only: 2.5→4.5° is +36 % fin drag going
  straight, +20 % at 5°, nothing at 10–20°. Zero-net-force toe 3.65° = the
  foil's zero-lift angle (3.50° from the isolated polar) — production toe trims
  this foil by construction; the gen-1 foil wanted 4.7° and ran off-trim.
- The fin working with its camber reproduces the isolated polar at β − toe
  (ratio 0.92–1.01): tier-0 "side env 1.0" confirmed. The opposite fin works
  against its camber and stalls on the flat face near own-frame −9°, plateauing
  at cl 0.2–0.4. Centre interference 0.64–0.81 in the linear range (tier-0 env
  0.716 confirmed); side_y is the only mount parameter that reaches it.
- t/c 0.046 vs 0.09 on the deepened centre: no lift gain for the thicker
  section at any angle in the set (G3 below G2) — no CFD support here for a
  t/c-dependent break angle.
