# What the level-5 drag of the best table-v1 fin is made of (2026-11-20)

Stored cases of this folder's polar, sampled on the fin's surface (wall shear stress and pressure per face: `finGenerator-cfd/scripts/sample_surface.sh`) and split into pressure and friction drag on the lattice's ten strips (`finGenerator-cfd/scripts/surface_split.py <this folder> <samples> -4.5 -3.5 -2.5`). "cd section" is table v1 at the incidence the lattice gives the strip; the last column is the 3-D strip minus that, in newtons. Sweep moves pressure drag toward the base at zero lift, so read the change of a strip from one angle to the next, and the totals.


### own incidence -4.5°

3-D case: 6.84 N = pressure 4.71 + friction 2.13. Lattice with table v1: 5.65 N = induced 0.00 + profile 5.64.

| station mm | chord mm | t/c | Re / 1e5 | section incidence ° | section's lower end ° | cl: 3-D / lattice | cd 3-D: pressure + friction | cd section | 3-D − section, N |
|---|---|---|---|---|---|---|---|---|---|
| 11 | 102.4 | 0.089 | 8.3 | -4.41 | -6.65 | -0.007 / -0.010 | 0.0151 + 0.0057 | 0.0139 | +0.57 |
| 33 | 96.7 | 0.090 | 7.8 | -4.41 | -6.55 | -0.006 / -0.011 | 0.0124 + 0.0061 | 0.0141 | +0.34 |
| 53 | 87.0 | 0.090 | 7.0 | -4.42 | -6.15 | -0.008 / -0.011 | 0.0113 + 0.0057 | 0.0146 | +0.16 |
| 73 | 74.4 | 0.091 | 6.0 | -4.42 | -5.90 | -0.011 / -0.012 | 0.0100 + 0.0055 | 0.0153 | +0.01 |
| 90 | 60.1 | 0.091 | 4.9 | -4.43 | -5.70 | -0.009 / -0.013 | 0.0088 + 0.0057 | 0.0163 | -0.07 |
| 106 | 46.1 | 0.092 | 3.7 | -4.43 | -5.50 | -0.028 / -0.015 | 0.0156 + 0.0062 | 0.0177 | +0.10 |
| 119 | 37.4 | 0.092 | 3.0 | -4.43 | -5.20 | -0.025 / -0.015 | 0.0241 + 0.0058 | 0.0193 | +0.17 |
| 129 | 32.7 | 0.092 | 2.6 | -4.41 | -5.10 | -0.011 / -0.013 | 0.0153 + 0.0054 | 0.0202 | +0.01 |
| 135 | 24.9 | 0.092 | 2.0 | -4.38 | -4.95 | +0.001 / -0.011 | 0.0042 + 0.0054 | 0.0220 | -0.06 |
| 139 | 14.1 | 0.093 | 1.1 | -4.26 | -4.85 | +0.001 / -0.007 | -0.0002 + 0.0006 | 0.0261 | -0.02 |

### own incidence -3.5°

3-D case: 5.50 N = pressure 3.23 + friction 2.27. Lattice with table v1: 5.45 N = induced 0.08 + profile 5.37.

| station mm | chord mm | t/c | Re / 1e5 | section incidence ° | section's lower end ° | cl: 3-D / lattice | cd 3-D: pressure + friction | cd section | 3-D − section, N |
|---|---|---|---|---|---|---|---|---|---|
| 11 | 102.4 | 0.089 | 8.3 | -3.90 | -6.65 | +0.052 / +0.047 | 0.0126 + 0.0060 | 0.0134 | +0.42 |
| 33 | 96.7 | 0.090 | 7.8 | -3.88 | -6.55 | +0.057 / +0.049 | 0.0096 + 0.0063 | 0.0136 | +0.18 |
| 53 | 87.0 | 0.090 | 7.0 | -3.86 | -6.15 | +0.058 / +0.051 | 0.0074 + 0.0059 | 0.0140 | -0.05 |
| 73 | 74.4 | 0.091 | 6.0 | -3.82 | -5.90 | +0.059 / +0.054 | 0.0056 + 0.0061 | 0.0146 | -0.15 |
| 90 | 60.1 | 0.091 | 4.9 | -3.77 | -5.70 | +0.066 / +0.058 | 0.0053 + 0.0068 | 0.0154 | -0.12 |
| 106 | 46.1 | 0.092 | 3.7 | -3.71 | -5.50 | +0.059 / +0.063 | 0.0091 + 0.0063 | 0.0164 | -0.02 |
| 119 | 37.4 | 0.092 | 3.0 | -3.71 | -5.20 | +0.077 / +0.062 | 0.0117 + 0.0060 | 0.0175 | +0.00 |
| 129 | 32.7 | 0.092 | 2.6 | -3.80 | -5.10 | +0.065 / +0.053 | 0.0068 + 0.0064 | 0.0184 | -0.05 |
| 135 | 24.9 | 0.092 | 2.0 | -3.89 | -4.95 | +0.035 / +0.043 | 0.0022 + 0.0071 | 0.0202 | -0.05 |
| 139 | 14.1 | 0.093 | 1.1 | -3.99 | -4.85 | +0.001 / +0.024 | -0.0002 + 0.0006 | 0.0245 | -0.02 |

### own incidence -2.5°

3-D case: 5.33 N = pressure 2.85 + friction 2.48. Lattice with table v1: 5.59 N = induced 0.40 + profile 5.19.

| station mm | chord mm | t/c | Re / 1e5 | section incidence ° | section's lower end ° | cl: 3-D / lattice | cd 3-D: pressure + friction | cd section | 3-D − section, N |
|---|---|---|---|---|---|---|---|---|---|
| 11 | 102.4 | 0.089 | 8.3 | -3.37 | -6.65 | +0.111 / +0.105 | 0.0116 + 0.0064 | 0.0131 | +0.40 |
| 33 | 96.7 | 0.090 | 7.8 | -3.34 | -6.55 | +0.119 / +0.108 | 0.0087 + 0.0066 | 0.0133 | +0.16 |
| 53 | 87.0 | 0.090 | 7.0 | -3.29 | -6.15 | +0.122 / +0.113 | 0.0064 + 0.0065 | 0.0136 | -0.04 |
| 73 | 74.4 | 0.091 | 6.0 | -3.22 | -5.90 | +0.126 / +0.120 | 0.0051 + 0.0068 | 0.0141 | -0.12 |
| 90 | 60.1 | 0.091 | 4.9 | -3.12 | -5.70 | +0.142 / +0.129 | 0.0048 + 0.0074 | 0.0147 | -0.09 |
| 106 | 46.1 | 0.092 | 3.7 | -2.99 | -5.50 | +0.140 / +0.141 | 0.0068 + 0.0068 | 0.0156 | -0.05 |
| 119 | 37.4 | 0.092 | 3.0 | -2.99 | -5.20 | +0.162 / +0.140 | 0.0082 + 0.0073 | 0.0165 | -0.02 |
| 129 | 32.7 | 0.092 | 2.6 | -3.18 | -5.10 | +0.131 / +0.119 | 0.0052 + 0.0076 | 0.0174 | -0.05 |
| 135 | 24.9 | 0.092 | 2.0 | -3.38 | -4.95 | +0.078 / +0.096 | 0.0036 + 0.0077 | 0.0190 | -0.04 |
| 139 | 14.1 | 0.093 | 1.1 | -3.70 | -4.85 | +0.001 / +0.055 | -0.0001 + 0.0006 | 0.0235 | -0.02 |

## The same split on the referee's sections

Resolved-wall 2-D cases of `bench/section-tables/thin-cambered/` (`finGenerator-cfd/scripts/section_surface.py`). The friction part is the wall shear summed around the perimeter, the pressure part the recorded total minus it. Reversed shear within 1 % of chord on the outside face is the stagnation point, not separation.

### camb45-tc092-re570k

| incidence ° | cd | friction part | pressure part | inside face: lowest cp at x/c | reversed x/c | outside face: lowest cp at x/c | reversed x/c | faces in the first 1 % of chord | y+ median / highest in the first 5 % |
|---|---|---|---|---|---|---|---|---|---|
| -6.00 | 0.0178 | 0.0085 | 0.0093 | -4.69 at 0.0055 | none | -0.33 at 0.3828 | 0.003–0.006 | 10 | 0.9 / 4.1 |
| -4.50 | 0.0156 | 0.0094 | 0.0062 | -3.27 at 0.0055 | none | -0.43 at 0.3672 | 0.003–0.003 | 10 | 1.0 / 3.5 |
| -2.50 | 0.0137 | 0.0097 | 0.0040 | -1.85 at 0.0055 | none | -0.57 at 0.3453 | none | 10 | 1.0 / 3.0 |

### camb3-tc070-re570k

| incidence ° | cd | friction part | pressure part | inside face: lowest cp at x/c | reversed x/c | outside face: lowest cp at x/c | reversed x/c | faces in the first 1 % of chord | y+ median / highest in the first 5 % |
|---|---|---|---|---|---|---|---|---|---|
| -4.50 | 0.0322 | 0.0059 | 0.0263 | -1.91 at 0.0002 | 0.006–0.355 | -0.24 at 0.3764 | none | 13 | 0.9 / 3.6 |
| -3.50 | 0.0139 | 0.0092 | 0.0047 | -2.75 at 0.0041 | 0.006–0.008 | -0.28 at 0.3764 | none | 13 | 1.0 / 3.8 |
| -2.50 | 0.0129 | 0.0098 | 0.0031 | -1.94 at 0.0041 | none | -0.34 at 0.3452 | none | 13 | 1.0 / 3.2 |

## Reading

- Level 5 reads friction 30–40 % below the referee's sections at every strip and angle (0.0055–0.0077 against 0.0092–0.0098) and pressure drag higher; between −2.5° and 0° the two roughly cancel in the total.
- Toward the lower end of the attached range the pressure part grows and the friction part falls on both, with no reversed flow on the 4.5 % / t/c 0.092 section down to −6°. On level 5 the pressure part rises about twice as fast between −3.5° and −4.5°.
- Surface cells of this mesh at the base: chord/160 on the faces, chord/320 over the first 3 % of chord and at the trailing edge; three cells across the nose radius. The referee has chord/320 and chord/640, ten to thirteen faces around the first 1 % of chord, and a resolved wall.
