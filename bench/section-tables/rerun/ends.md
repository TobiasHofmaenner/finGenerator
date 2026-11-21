# The sections on the converged recipe: where each attached range ends

Written by the collector of the rerun (`~/bench-results/sections2/collect.py`). A row is past an end when it did not settle in 3000 iterations or has more than four times the section's lowest drag. Each end lies between the last row inside and the first row past it.

| section | t/c | camber % | Re | rows | lowest c_d | lower end between ° | c_l, c_d at the last row inside | upper end between ° | c_l, c_d at the last row inside | state |
|---|---|---|---|---|---|---|---|---|---|---|
| camb3-tc070-re140k | 0.070 | 3.0 | 1.4e+05 | 23 | 0.0158 | -4.50 and -4.75 | -0.166, 0.0242 | +8.25 and +8.50 | +1.066, 0.0367 | complete (laptop) |
| flat-tc092-r050-re570k | 0.092 | 0.0 | 5.7e+05 | 26 | 0.0155 | -5.25 and -5.50 | -0.146, 0.0597 | +13.25 and +13.50 | +1.617, 0.0448 | complete (laptop) |
| camb3-tc070-re570k | 0.070 | 3.0 | 5.7e+05 | 24 | 0.0126 | -6.25 and -6.50 | -0.341, 0.0180 | +10.00 and +10.25 | +1.324, 0.0329 | complete (laptop) |
| camb45-tc092-re570k | 0.092 | 4.5 | 5.7e+05 | 25 | 0.0137 | -7.50 and -7.75 | -0.306, 0.0194 | +13.75 and +14.00 | +1.657, 0.0496 | complete (laptop) |
| camb3-tc050-re570k | 0.050 | 3.0 | 5.7e+05 | 18 | 0.0122 | -4.00 and -4.25 | -0.113, 0.0297 | +7.25 and +7.50 | +0.988, 0.0477 | complete (laptop) |
| camb3-tc120-re570k | 0.120 | 3.0 | 5.7e+05 | 26 | 0.0140 | -10.75 and -11.00 | -0.791, 0.0260 | +14.00 and +14.25 | +1.567, 0.0449 | complete (laptop) |
| camb45-tc070-re570k | 0.070 | 4.5 | 5.7e+05 | 24 | 0.0133 | -5.50 and -5.75 | -0.094, 0.0171 | +11.00 and +11.25 | +1.520, 0.0390 | complete (laptop) |
| camb3-tc092-re570k | 0.092 | 3.0 | 5.7e+05 | 30 | 0.0131 | -8.75 and -9.00 | -0.601, 0.0225 | +14.25 and +14.50 | +1.567, 0.0509 | complete (laptop) |
| sym-tc046-re570k | 0.046 | 0.0 | 5.7e+05 | 9 | 0.0115 | mirror of the upper |  | +5.50 and +5.75 | +0.561, 0.0410 | complete (laptop) |
| sym-tc090-re570k | 0.090 | 0.0 | 5.7e+05 | 17 | 0.0126 | mirror of the upper |  | +11.75 and +12.00 | +1.164, 0.0360 | complete (laptop) |
| camb2-tc070-re570k | 0.070 | 2.0 | 5.7e+05 | 26 | 0.0123 | -7.00 and -7.25 | -0.531, 0.0204 | +9.50 and +9.75 | +1.184, 0.0310 | complete (laptop) |
| camb45-tc080-re570k | 0.080 | 4.5 | 5.7e+05 | 19 | 0.0135 | -6.50 and -6.75 | -0.200, 0.0182 | beyond +10.00 | +1.482, 0.0319 | running (laptop) |
| camb3-tc070-re280k | 0.070 | 3.0 | 2.8e+05 | 19 | 0.0139 | -5.00 and -5.25 | -0.206, 0.0187 | +8.50 and +8.75 | +1.150, 0.0327 | complete (EPYC) |
| camb45-tc092-re970k | 0.092 | 4.5 | 9.7e+05 | 27 | 0.0128 | -8.25 and -8.50 | -0.387, 0.0190 | +14.50 and +14.75 | +1.737, 0.0503 | complete (EPYC) |
| sym-tc066-re570k | 0.066 | 0.0 | 5.7e+05 | 11 | 0.0119 | mirror of the upper |  | +7.25 and +7.50 | +0.772, 0.0214 | complete (EPYC) |
| sym-tc080-re570k | 0.080 | 0.0 | 5.7e+05 | 16 | 0.0123 | mirror of the upper |  | +10.50 and +10.75 | +1.017, 0.0370 | complete (EPYC) |
| sym-tc120-re570k | 0.120 | 0.0 | 5.7e+05 | 17 | 0.0135 | mirror of the upper |  | +13.00 and +13.25 | +1.278, 0.0353 | complete (EPYC) |
| flat-tc050-r050-re570k | 0.050 | 0.0 | 5.7e+05 | 24 | 0.0126 | -4.50 and -4.75 | -0.300, 0.0466 | +9.25 and +9.50 | +1.169, 0.0297 | complete (EPYC) |
| flat-tc120-r050-re570k | 0.120 | 0.0 | 5.7e+05 | 24 | 0.0176 | -5.25 and -5.50 | +0.017, 0.0600 | +13.00 and +13.25 | +1.664, 0.0472 | complete (EPYC) |
| flat-tc092-r050-re280k | 0.092 | 0.0 | 2.8e+05 | 27 | 0.0170 | -5.50 and -5.75 | -0.166, 0.0642 | +12.50 and +12.75 | +1.525, 0.0448 | complete (EPYC) |
| flat-tc092-r050-re140k | 0.092 | 0.0 | 1.4e+05 | 28 | 0.0187 | -5.25 and -5.50 | -0.150, 0.0613 | +12.00 and +12.25 | +1.441, 0.0461 | complete (EPYC) |
| camb45-tc120-re570k | 0.120 | 4.5 | 5.7e+05 | 25 | 0.0144 | -10.25 and -10.50 | -0.585, 0.0251 | +13.75 and +14.00 | +1.663, 0.0475 | complete (EPYC) |
| camb3-tc150-re570k | 0.150 | 3.0 | 5.7e+05 | 9 | 0.0149 | beyond -8.00 | -0.521, 0.0191 | beyond +6.00 | +0.958, 0.0210 | running (EPYC) |
| camb45-tc150-re570k | 0.150 | 4.5 | 5.7e+05 | 23 | 0.0154 | -11.25 and -11.50 | -0.671, 0.0256 | +13.00 and +13.25 | +1.586, 0.0445 | complete (EPYC) |
| sym-tc150-re570k | 0.150 | 0.0 | 5.7e+05 | 7 | 0.0145 | mirror of the upper |  | beyond +12.00 | +1.177, 0.0305 | running (EPYC) |
| camb45-tc092-re140k | 0.092 | 4.5 | 1.4e+05 | 23 | 0.0176 | -5.00 and -5.25 | -0.054, 0.0217 | +11.00 and +11.25 | +1.351, 0.0484 | complete (laptop) |
