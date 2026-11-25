# Section table v1 against maximum lift measured in a turbulent stream [JS37]

Written by `scripts/section_vdt_check.py` from `js37-clmax.csv` (NACA Report 586, Table I). Measured: variable-density tunnel, turbulence factor 2.64, polished models; section value = 1.07 times the maximum of a rectangular wing of aspect ratio 6. Peak: A drops at once, C breaks between two branches, D is rounded and gradual. Table: turbulent from the nose, held stream; `cl_limit`, read at the test Reynolds number and at the effective one. A `*` marks a table value read at its edge (camber above 5 %, or thickness or Reynolds number outside it).

| section | Re effective | Re test | measured c_l max | peak | table limit at Re test | table over measured | table limit at Re effective | table over measured |
|---|---|---|---|---|---|---|---|---|
| NACA 0009 | 1.76e+06 | 6.67e+05 | 0.88 | D | 1.15 | +30% | 1.20* | +36% |
| NACA 0009 | 8.82e+05 | 3.34e+05 | 0.86 | D | 1.02 | +19% | 1.18 | +37% |
| NACA 0009 | 4.46e+05 | 1.69e+05 | 0.85 | D | 0.87 | +2% | 1.08 | +27% |
| NACA 0009 | 2.23e+05 | 8.45e+04 | 0.83 | D | 0.80* | -3% | 0.94 | +13% |
| NACA 0012 | 1.74e+06 | 6.59e+05 | 1.18 | A | 1.25 | +6% | 1.31* | +11% |
| NACA 0012 | 8.71e+05 | 3.3e+05 | 0.91 | D | 1.10 | +21% | 1.29 | +42% |
| NACA 0012 | 4.49e+05 | 1.7e+05 | 0.89 | D | 0.97 | +9% | 1.18 | +32% |
| NACA 0015 | 1.73e+06 | 6.55e+05 | 1.28 | C | 1.21 | -6% | 1.27* | -1% |
| NACA 0015 | 8.74e+05 | 3.31e+05 | 1.09 | C | 1.04 | -5% | 1.24 | +14% |
| NACA 0015 | 4.38e+05 | 1.66e+05 | 0.98 | D | 0.91 | -8% | 1.12 | +14% |
| NACA 0015 | 2.22e+05 | 8.41e+04 | 0.89 | D | 0.86* | -3% | 0.95 | +7% |
| NACA 0018 | 1.73e+06 | 6.55e+05 | 1.26 | D | 1.21 | -4% | 1.28* | +2% |
| NACA 0018 | 8.66e+05 | 3.28e+05 | 1.15 | C | 1.03 | -11% | 1.25 | +9% |
| NACA 0018 | 4.3e+05 | 1.63e+05 | 1.03 | A | 0.89 | -13% | 1.11 | +8% |
| NACA 0018 | 2.14e+05 | 8.11e+04 | 0.96 | D | 0.85* | -12% | 0.93 | -3% |
| NACA 2412 | 1.73e+06 | 6.55e+05 | 1.33 | D | 1.45 | +9% | 1.53* | +15% |
| NACA 2412 | 8.79e+05 | 3.33e+05 | 1.16 | D | 1.27 | +10% | 1.50 | +29% |
| NACA 2412 | 4.38e+05 | 1.66e+05 | 1.08 | D | 1.12 | +4% | 1.35 | +25% |
| NACA 2412 | 2.18e+05 | 8.26e+04 | 1.08 | D | 1.07* | -1% | 1.17 | +9% |
| NACA 4409 | 1.7e+06 | 6.44e+05 | 1.29 | D | 1.61 | +25% | 1.70* | +32% |
| NACA 4409 | 8.69e+05 | 3.29e+05 | 1.26 | D | 1.49 | +18% | 1.66 | +31% |
| NACA 4409 | 4.38e+05 | 1.66e+05 | 1.23 | D | 1.40 | +14% | 1.54 | +25% |
| NACA 4409 | 2.18e+05 | 8.26e+04 | 1.21 | D | 1.36* | +12% | 1.44 | +19% |
| NACA 4412 | 1.68e+06 | 6.36e+05 | 1.46 | D | 1.62 | +11% | 1.71* | +17% |
| NACA 4412 | 8.74e+05 | 3.31e+05 | 1.36 | D | 1.45 | +7% | 1.67 | +23% |
| NACA 4412 | 4.33e+05 | 1.64e+05 | 1.31 | D | 1.29 | -2% | 1.53 | +17% |
| NACA 4412 | 2.19e+05 | 8.3e+04 | 1.32 | D | 1.21* | -8% | 1.35 | +2% |
| NACA 4415 | 1.73e+06 | 6.55e+05 | 1.48 | D | 1.58 | +7% | 1.68* | +14% |
| NACA 4415 | 8.82e+05 | 3.34e+05 | 1.41 | D | 1.39 | -1% | 1.63 | +16% |
| NACA 4415 | 4.31e+05 | 1.63e+05 | 1.35 | D | 1.20 | -11% | 1.47 | +9% |
| NACA 4415 | 2.19e+05 | 8.3e+04 | 1.34 | D | 1.12* | -16% | 1.28 | -5% |
| NACA 6412 | 1.7e+06 | 6.44e+05 | 1.54 | D | 1.71* | +11% | 1.81* | +18% |
| NACA 6412 | 8.82e+05 | 3.34e+05 | 1.48 | D | 1.56* | +5% | 1.76* | +19% |
| NACA 6412 | 4.41e+05 | 1.67e+05 | 1.47 | D | 1.39* | -5% | 1.63* | +11% |
| NACA 6412 | 2.19e+05 | 8.3e+04 | 1.46 | D | 1.31* | -11% | 1.46* | -0% |
