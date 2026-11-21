# The sections on the converged recipe: where each attached range ends

Written by the collector of the rerun (`~/bench-results/sections2/collect.py`). A row is past an end when it did not settle in 3000 iterations or has more than four times the section's lowest drag. Each end lies between the last row inside and the first row past it.

| section | t/c | camber % | Re | rows | lowest c_d | lower end between ° | c_l, c_d at the last row inside | upper end between ° | c_l, c_d at the last row inside | state |
|---|---|---|---|---|---|---|---|---|---|---|
| camb3-tc070-re140k | 0.070 | 3.0 | 1.4e+05 | 22 | 0.0158 | -4.50 and -4.75 | -0.166, 0.0242 | +8.00 and +8.50 | +1.054, 0.0336 | running (laptop) |
| flat-tc092-r050-re570k | 0.092 | 0.0 | 5.7e+05 | 17 | 0.0155 | -5.25 and -5.50 | -0.146, 0.0597 | beyond +10.00 | +1.441, 0.0299 | running (laptop) |
| camb45-tc092-re140k | 0.092 | 4.5 | 1.4e+05 | 23 | 0.0176 | -5.00 and -5.25 | -0.054, 0.0217 | +11.00 and +11.25 | +1.351, 0.0484 | complete (laptop) |
| camb3-tc070-re570k | 0.070 | 3.0 | 5.7e+05 | 24 | 0.0126 | -6.25 and -6.50 | -0.341, 0.0180 | +10.00 and +10.25 | +1.324, 0.0329 | complete (laptop) |
| camb45-tc092-re570k | 0.092 | 4.5 | 5.7e+05 | 25 | 0.0137 | -7.50 and -7.75 | -0.306, 0.0194 | +13.75 and +14.00 | +1.657, 0.0496 | complete (laptop) |
| camb3-tc050-re570k | 0.050 | 3.0 | 5.7e+05 | 18 | 0.0122 | -4.00 and -4.25 | -0.113, 0.0297 | +7.25 and +7.50 | +0.988, 0.0477 | complete (laptop) |
| camb3-tc120-re570k | 0.120 | 3.0 | 5.7e+05 | 26 | 0.0140 | -10.75 and -11.00 | -0.791, 0.0260 | +14.00 and +14.25 | +1.567, 0.0449 | complete (laptop) |
| camb45-tc070-re570k | 0.070 | 4.5 | 5.7e+05 | 13 | 0.0133 | -5.50 and -6.00 | -0.094, 0.0171 | beyond +8.00 | +1.320, 0.0259 | running (laptop) |
| camb3-tc092-re570k | 0.092 | 3.0 | 5.7e+05 | 5 | 0.0131 | beyond -3.50 | -0.041, 0.0136 | beyond +2.00 | +0.563, 0.0146 | running (laptop) |
| camb3-tc070-re280k | 0.070 | 3.0 | 2.8e+05 | 19 | 0.0139 | -5.00 and -5.25 | -0.206, 0.0187 | +8.50 and +8.75 | +1.150, 0.0327 | complete (EPYC) |
| camb45-tc092-re970k | 0.092 | 4.5 | 9.7e+05 | 27 | 0.0128 | -8.25 and -8.50 | -0.387, 0.0190 | +14.50 and +14.75 | +1.737, 0.0503 | complete (EPYC) |
| sym-tc066-re570k | 0.066 | 0.0 | 5.7e+05 | 11 | 0.0119 | mirror of the upper |  | +7.25 and +7.50 | +0.772, 0.0214 | complete (EPYC) |
| sym-tc080-re570k | 0.080 | 0.0 | 5.7e+05 | 16 | 0.0123 | mirror of the upper |  | +10.50 and +10.75 | +1.017, 0.0370 | complete (EPYC) |
| sym-tc120-re570k | 0.120 | 0.0 | 5.7e+05 | 17 | 0.0135 | mirror of the upper |  | +13.00 and +13.25 | +1.278, 0.0353 | complete (EPYC) |
| flat-tc050-r050-re570k | 0.050 | 0.0 | 5.7e+05 | 9 | 0.0126 | -4.50 and -5.00 | -0.300, 0.0466 | beyond +4.00 | +0.653, 0.0149 | running (EPYC) |
| flat-tc120-r050-re570k | 0.120 | 0.0 | 5.7e+05 | 5 | 0.0176 | beyond -3.50 | +0.185, 0.0382 | beyond +2.00 | +0.782, 0.0176 | running (EPYC) |
