# The fin on the outside of a turn, alone (2026-11-23)

Question. In every set run on record (the twin of `../twin-set/`, the thruster of `../../mount/`, the four-fin layout of `../../falk/`) the fin on the outside of the turn, driven from its curved side with its flat inside face on the suction side, leaves its lift line near −8° to −10° of own incidence and levels off. The lattice keeps it on the line and reads up to twice its lift. Rows behind the lower end of the flat-inside sections went into the section table on 2026-11-22 and closed the smaller part of that (`../../section-tables/rerun-held/`): the 2-D referee's lift goes on growing there, on rows that never settle. What does one such fin do alone, where no set is in the way, and is that mesh?

The shipped gen-2 side (flat inside, t/c 0.092, 9 734 mm², `../../mount/fins/side-shipped-gen2.json`) alone on a symmetry plane at 8.5 m/s, own incidence −6° to −16°, with `finGenerator-cfd` `scripts/polar_angles.py`: mesh level 5 (543 503 cells, mean wall y⁺ 77) and mesh level 6 (1.0 M cells, y⁺ 41), wall functions, old inlet. `level5.json`, `level6.json`; `lattice.md` is written by `scripts/outside_fin_lattice.py`.

| own incidence ° | −6 | −7 | −8 | −9 | −10 | −12 | −14 | −16 |
|---|---|---|---|---|---|---|---|---|
| C_L, level 5 | −0.167 | −0.216 | −0.263 | −0.285 | −0.293 | −0.299 | −0.314 | −0.347 |
| C_L, level 6 | −0.163 | | −0.254 | | −0.298 | −0.320 | | −0.352 |
| C_D, level 5 | 0.0593 | 0.0706 | 0.0836 | 0.0954 | 0.1060 | 0.1251 | 0.1450 | 0.1700 |
| C_D, level 6 | 0.0580 | | 0.0821 | | 0.1059 | 0.1278 | | 0.1702 |
| lattice, strips on the table as it is: C_L | −0.158 | −0.211 | −0.276 | −0.338 | −0.384 | −0.434 | −0.492 | −0.513 |
| lattice, lift held 1.5° past the lower end: C_L | −0.158 | −0.211 | −0.261 | −0.283 | −0.294 | −0.314 | −0.313 | −0.316 |
| the same: C_D | 0.0536 | 0.0646 | 0.0782 | 0.0934 | 0.1105 | 0.1457 | 0.1812 | 0.2154 |

(Rows from −6° to −12° ran to the cap of 800 iterations on both meshes; −14° and −16° stopped on their residuals.)

## Reading

- **Alone, the fin does what it does in a set, and it is not the mesh.** It follows its lift line to −8° and levels off from −9° at −0.29 to −0.35. The two meshes agree within 0.02 in lift and 2 % in drag at every angle both ran.
- **The lattice follows it to −8° and then carries on**: 19 % too much lift at −9°, 30 % at −10°, 40–57 % from −12° on. At −9° every one of its ten strips is past the lower end of its section's attached range, by 1.5° at the root.
- **One number closes it: a flat-inside strip's lift is held at its value 1.5° past the lower end** (`lattice.held_below`, `LOWER_HOLD_DEG`). With it the lattice is within 4 % rms of this polar from −6° to −16° (within 4 % at every angle to −14°, 9 % low at −16°); 1.0° gives 15 %, 2.0° 12 % (`lattice.md`). It is fitted here and nowhere else.
- **Checked, not fitted, on the sets** (`../../falk/quad-level5-foils/lattice.md`, `../twin-set/lattice.md`):

| | lattice as it was | with the hold | set CFD |
|---|---|---|---|
| four-fin set, flat inside t/c 0.09, front outside fin at 10°, 15° | 0.420, 0.549 | 0.294, 0.316 | 0.278, 0.300 |
| rear outside fin | 0.327, 0.421 | 0.296, 0.326 | 0.307, 0.373 |
| flat inside t/c 0.065, front outside fin | 0.554, 0.690 | 0.360, 0.386 | 0.385, 0.391 |
| rear outside fin | 0.330, 0.477 | 0.351, 0.397 | 0.354, 0.438 |
| twin keel, unloaded fin at 8°, 12° | 0.175, 0.306 | 0.175, 0.256 | 0.149, 0.226 |
| twin keel, share of the loaded fin at 12° | 0.59 | 0.64 | 0.66 |

  The front outside fins come from 36–94 % above their set CFD to within 6 %, the rear ones to within 13 % (low), the three other fins of each set stay within 6 %. The keel's unloaded fin is 13–17 % high instead of 17–35 %: a blade of aspect ratio 0.6 leaves its line a little before this rule lets it.
- **Flat-inside sections only.** A cambered section's table already loses its lift behind the lower end. On the one cambered set on record (3 % camber, t/c 0.065) the lattice reads the front outside fin 4 % and 15 % high as it is and would read it 23 % and 21 % low with the hold; `held_below` leaves cambered and symmetric strips alone.

## What this does not settle

- **Drag.** The hold is on lift. The lattice's drag of this fin is within 9 % to −10° and 15–27 % above the simulation from −12° on; on the four-fin set's front outside fins it is 19–43 % above at 10° and 15°, with or without the hold. The section drag behind a lower end is the 2-D referee's, and a blade that has let go as a whole has less.
- **Why 1.5°.** It is where one blade of aspect ratio 2 levels off, on wall functions. The 2-D referee's sections keep their line for two degrees past the end and grow on from there; the blade levels at once. The rule is the knee's twin for the far side of the section, and like the knee's share it is one number from one fin.
- Nothing in a single fin's score reads it: going straight and in its own turn a strip stays inside its range. It is for sets, where the shares between fins are still fixed numbers (`docs/GEN3-PLAN.md` 2b).
