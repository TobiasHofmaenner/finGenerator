# Section table v1 at the referee's nodes

v1 is read here the way fingen reads it (`sections.polar` on the shipped file). "Left out" is the end predicted for a node by a table built without it: how well the table is known between its nodes.

| section | lower end °: RANS / v0 / v1 / left out | upper end °: RANS / v0 / v1 / left out | drag level v1 / v0 | lift slope v1 / v0 | lift retention | cd v1 / RANS over the settled rows: min … max | largest cl difference |
|---|---|---|---|---|---|---|---|
| flat-tc092-re570k | -1.38 / -0.79 / -1.38 / +nan | +11.00 / +11.48 / +11.00 / +nan | 1.243 | 0.966 | 0.79 | 0.95 … 1.09 | 0.017 |
| camb3-tc092-re570k | -6.09 / -7.49 / -6.01 / -6.20 | +10.17 / +12.50 / +10.18 / +10.13 | 1.039 | 0.975 | 0.56 | 0.96 … 1.20 | 0.005 |
| camb45-tc070-re570k | -3.81 / -4.61 / -3.79 / -3.69 | +9.04 / +10.18 / +9.04 / +9.04 | 1.098 | 0.972 | 0.68 | 0.91 … 1.09 | 0.009 |
| camb3-tc070-re570k | -4.30 / -5.17 / -4.26 / -4.07 | +8.05 / +9.85 / +8.06 / +8.16 | 1.055 | 0.972 | 0.63 | 0.91 … 1.14 | 0.006 |
| camb45-tc092-re570k | -6.66 / -6.72 / -6.45 / -5.55 | +11.21 / +12.15 / +11.20 / +11.02 | 1.128 | 0.978 | 0.66 | 0.86 … 1.55 | 0.011 |
| camb2-tc070-re570k | -4.57 / -5.61 / -4.53 / -4.59 | +7.40 / +9.20 / +7.41 / +7.40 | 1.045 | 0.967 | 0.49 | 0.93 … 1.22 | 0.053 |
| camb45-tc080-re570k | -4.58 / -5.57 / -4.53 / -4.96 | +9.78 / +11.13 / +9.78 / +10.06 | 1.085 | 0.973 | 0.63 | 0.90 … 1.19 | 0.010 |
| camb3-tc080-re570k | -5.04 / -6.26 / -5.01 / -5.12 | +9.13 / +11.12 / +9.14 / +8.99 | 1.058 | 0.972 | 0.49 | 0.94 … 1.20 | 0.006 |
| camb2-tc050-re570k | -3.11 / -3.59 / -3.12 / -2.70 | +6.06 / +6.15 / +6.06 / +5.48 | 1.069 | 0.965 | 1.00 | 0.89 … 1.02 | 0.011 |
| camb3-tc050-re570k | -2.80 / -3.24 / -2.81 / -2.58 | +6.29 / +6.57 / +6.30 / +6.41 | 1.119 | 0.968 | 1.00 | 0.92 … 1.08 | 0.013 |
| camb3-tc070-re280k | -4.12 / -4.59 / -4.09 / -4.07 | +8.15 / +8.92 / +8.16 / +8.05 | 1.014 | 0.962 | 1.01 | 0.89 … 1.16 | 0.007 |
| camb3-tc120-re570k | -8.63 / -9.60 / -8.63 / -8.16 | +12.81 / +13.87 / +12.81 / +11.55 | 1.118 | 0.968 | 0.72 | 0.87 … 1.04 | 0.027 |
| camb1-tc070-re570k | -5.06 / -6.00 / -5.02 / -4.90 | +6.39 / +8.57 / +6.40 / +6.78 | 1.044 | 0.966 | 0.33 | 0.95 … 1.51 | 0.002 |

cambered: 12 nodes at 11 sections, Reynolds number 2.8e+05 … 5.7e+05 (1 section(s) at more than one); plane over ['t/c', 'camber']; the plane alone misses a section by at most lower 0.757, upper 0.435, step 1.253, log_level 0.041, log_level_below 0.325, slope 0.004, d_alpha0 0.022, retention 0.287 (spread back in around each section).
  Per octave of Reynolds number (mean over those sections): lower -0.173, upper -0.101, step -0.259, log_level +0.038, log_level_below -0.281, slope +0.009, d_alpha0 +0.026, retention -0.366.
  Left out, lower end: rms 0.40 deg, largest 1.11 deg over 12 nodes.
  Left out, upper end: rms 0.43 deg, largest 1.26 deg over 12 nodes.

flat_inside: 1 nodes at 1 sections, Reynolds number 5.7e+05 … 5.7e+05 (0 section(s) at more than one); plane over a constant; the plane alone misses a section by at most lower 0.000, upper 0.000, step 0.000, log_level 0.000, log_level_below 0.000, slope 0.000, d_alpha0 0.000, retention 0.000 (spread back in around each section).
