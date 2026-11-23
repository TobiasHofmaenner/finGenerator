# Section table v1 against measured sections of its own families [SDF89]

Written by `scripts/section_measured_check.py`. Measured: smooth models, low-turbulence tunnel, no trip. Table: fully turbulent, on the held stream. "5 % below" is against each polar's own line through its rows nearest 2° and 4°. The measured highest lift is the highest tabulated row, marked `+` where that is the last row (the drag survey ends where the wake gets too wide).

| section | Re | c_l at 4° / 6° / 8° / 9°: measured | table | 5 % below its line: measured | table | highest lift: measured | table's limit, end of attached range | c_d at 4°: measured / table |
|---|---|---|---|---|---|---|---|---|
| NACA 0009 | 1e+05 | 0.424 / 0.581 / 0.713 / – | 0.418 / 0.619 / 0.791 / (past its end) | 6.7°, 0.63 | 8.0°, 0.79 | 0.73+ at 8.2° | 0.80, 8.4° | 0.0134 / 0.0187 |
| NACA 0009 | 1.51e+05 | 0.419 / 0.584 / 0.720 / 0.763 | 0.422 / 0.624 / 0.807 / (past its end) | 7.8°, 0.71 | 8.3°, 0.82 | 0.77+ at 9.2° | 0.84, 8.6° | 0.0125 / 0.0168 |
| NACA 0009 | 1.99e+05 | 0.422 / 0.592 / 0.733 / 0.777 | 0.426 / 0.632 / 0.823 / 0.901 | 7.5°, 0.70 | 8.8°, 0.89 | 0.79+ at 9.2° | 0.91, 9.3° | 0.0115 / 0.0158 |
| NACA 0009 | 3.03e+05 | 0.421 / 0.594 / 0.737 / 0.782 | 0.432 / 0.641 / 0.837 / 0.926 | 6.9°, 0.67 | 9.4°, 0.96 | 0.79+ at 9.3° | 1.00, 10.2° | 0.0110 / 0.0150 |
| NACA 2.5411 | 1.02e+05 | 0.576 / 0.743 / 0.859 / 0.910 | 0.661 / 0.842 / 0.993 / 1.062 | 7.1°, 0.81 | 7.5°, 0.96 | 0.97+ at 10.3° | 1.15, 10.7° | 0.0153 / 0.0210 |
| NACA 2.5411 | 2.01e+05 | 0.610 / 0.767 / 0.896 / 0.953 | 0.688 / 0.879 / 1.044 / 1.112 | 6.4°, 0.79 | 8.1°, 1.05 | 1.04+ at 11.3° | 1.24, 11.3° | 0.0119 / 0.0179 |
| NACA 2.5411 | 3.03e+05 | 0.606 / – / – / – | 0.701 / 0.899 / 1.078 / 1.154 | beyond 5.2° | 8.7°, 1.14 | 0.70+ at 5.2° | 1.33, 12.0° | 0.0104 / 0.0171 |
| NACA 6409 (table read at its edge, 5 % camber) | 1.03e+05 | 0.900 / 1.071 / 1.226 / 1.291 | 0.906 / 1.076 / 1.224 / 1.291 | 9.4°, 1.31 | 8.0°, 1.23 | 1.37 at 11.3° | 1.41, 11.8° (clipped) | 0.0192 / 0.0233 |
| NACA 6409 (table read at its edge, 5 % camber) | 1.47e+05 | 0.953 / 1.130 / 1.281 / 1.341 | 0.923 / 1.098 / 1.253 / 1.321 | 8.4°, 1.31 | 8.4°, 1.29 | 1.38 at 10.3° | 1.44, 11.8° (clipped) | 0.0146 / 0.0213 |
| NACA 6409 (table read at its edge, 5 % camber) | 2e+05 | 0.987 / 1.157 / 1.298 / 1.334 | 0.941 / 1.123 / 1.288 / 1.361 | 8.4°, 1.32 | 8.9°, 1.36 | 1.34 at 9.3° | 1.49, 12.1° (clipped) | 0.0132 / 0.0202 |
