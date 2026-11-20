# Mesh level 5 on the best fin of the first table-v1 searches (2026-11-20)

The blade three of six neutral searches on section table v1 ended on (`docs/MODEL-EXTENSION.md`, "Section table v1"): 10 004 mm², depth 140 mm, base 104 mm, 4.2 % camber on t/c 0.089 at the root and 0.093 at the tip (`fins/side-v1-neutral.json`). The model reads it at 5.5 N going straight with hold 1.14. Same mesh and driver as `../mesh-level-5/`; lattice columns from `scripts/lattice_vs_polar.py <this folder> --table=v1` (perfect mirror).

| own incidence ° | level 5: C_L, drag N | lattice, table v1: C_L, drag N | lattice, table v0 N |
|---|---|---|---|
| −4.5 | −0.010, 6.8 † | −0.009, 5.6 | 5.0 |
| −3.5 | +0.058, 5.5 | +0.056, 5.3 | 4.9 |
| −2.5 | +0.123, 5.3 | +0.121, 5.4 | 5.0 |
| 0 | +0.285, 7.1 | +0.286, 6.9 | 6.6 |
| +4 | +0.539, 13.9 | +0.546, 12.6 | 12.3 |
| going straight (mean of −2.5 and −4.5) | **6.1** | 5.5 | 5.0 |

† at the 800-iteration cap.

## Reading

- **The thicker section does what the model said, and a little more.** 6.1 N going straight against 7.7 N for the candidate on t/c 0.074 at the same hold (1.14): 1.6 N per fin from thickness, where the model had 1.0 N (5.5 against 6.5).
- **From −3.5° to 0° the model is within 3 %**, lift within 0.002. At −4.5° the CFD does not settle and reads 1.2 N more: on all three cambered blades run on this mesh the fin is at the edge of its attached range at −4.5°, a little earlier than table v1 has it. The 4.5 % / t/c 0.092 referee section, which decides v1's lower end here, has not finished.
- **+4°: lift within 0.007, drag 9 % low** — the lattice's near-field induced drag again.
