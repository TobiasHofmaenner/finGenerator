# The gen-2 planform one mesh level finer: flat inside and 3 % camber (2026-11-22)

Question: the two numbers the choice between a flat inside face and camber rests on are drag going straight, 12.5 N against 4.6 N per fin in the lattice on this planform. Mesh level 5 has 13.3 N and 5.9 N (`../mesh-level-5/`). Does either move with the mesh?

The shipped gen-2 side fin (flat inside, t/c 0.092, 9 734 mm²) and the same planform with 3 % camber, on mesh level 6 of `finGenerator-cfd` (level 2 with two more surface refinements; 1 009 370 and 1 024 704 cells, wall functions, mean wall y⁺ 45–49), the same driver, speed (8.5 m/s), angles and inlet as the level-5 polars. Drag in N; lattice: `uv run python scripts/lattice_vs_polar.py bench/cambered-candidate/mesh-level-6 --table=v1` (section table of 2026-11-22).

| own incidence ° | flat inside: level 5 | level 6 | lattice | 3 % camber: level 2 | level 5 | level 6 | lattice |
|---|---|---|---|---|---|---|---|
| −4.5 | 15.8 † | 15.7 † | 14.6 | 8.8 | 7.0 † | 5.7 | 4.8 |
| −3.5 | 13.0 † | 12.8 | 12.2 | 6.9 | 5.4 † | 4.6 | 4.5 |
| −2.5 | 10.8 † | 10.6 | 10.4 | 6.0 | 4.8 | 4.3 | 4.5 |
| 0 | 8.2 | 8.0 | 8.4 | 5.8 | 5.6 | 5.3 | 5.5 |
| +4 | 11.8 | 11.4 | 11.9 | 10.2 | 11.0 | 10.5 | 10.7 |
| going straight (mean of −2.5 and −4.5) | 13.3 | 13.1 | 12.5 | 7.4 | 5.9 | 5.0 | 4.6 |

(† ran to the cap of 800 iterations. Lift: level 6 within 0.005 of level 5 on both blades; the lattice within 0.005 on the cambered blade and 0.01–0.02 above on the flat one.)

## Reading

- **The flat inside face does not move with the mesh.** Level 6 is 1–4 % below level 5 at every angle, and the lattice within 6 % of it: 13.1 N going straight against 12.5.
- **The cambered blade does, below 0°.** One refinement takes 12–18 % off from −2.5° to −4.5°, where level 5 had already taken 20 % off level 2. Level 6 is within 5 % of the lattice from −3.5° to +4° and 16 % above it at −4.5°: 5.0 N going straight against 4.6.
- **So on one planform, in 3-D CFD on the finest mesh there is, the flat inside face costs 13.1 N going straight and 3 % camber 5.0 N.** The lattice's 12.5 and 4.6 are the same statement within 5–8 %.
- The thinner candidate (4.3 % on t/c 0.074, `../mesh-level-6-candidate/`) has further to go on the same mesh: on the lattice at −2.5°, 57 % above at −4.5°.
