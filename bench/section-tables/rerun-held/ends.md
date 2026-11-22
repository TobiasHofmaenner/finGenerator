# The sections on the held stream: where each attached range ends

Written by the collector of the rerun (`~/bench-results/sections3/collect.py`). A row is past an end when it did not settle in 3000 iterations or has more than four times the section's lowest drag (a row marked `cycle` in `results.json` swings about a steady mean and counts as settled). Each end lies between the last row inside and the first row past it.

| section | t/c | camber % | Re | rows | lowest c_d | lower end between ° | c_l, c_d at the last row inside | upper end between ° | c_l, c_d at the last row inside | state |
|---|---|---|---|---|---|---|---|---|---|---|
| camb3-tc070-re140k | 0.070 | 3.0 | 1.4e+05 | 22 | 0.0150 | -4.50 and -4.75 | -0.149, 0.0233 | +7.75 and +8.00 | +1.059, 0.0304 | complete (EPYC) |
| flat-tc092-r050-re570k | 0.092 | 0.0 | 5.7e+05 | 24 | 0.0146 | -4.75 and -5.00 | -0.098, 0.0515 | +12.75 and +13.00 | +1.603, 0.0401 | complete (EPYC) |
| camb3-tc070-re570k | 0.070 | 3.0 | 5.7e+05 | 24 | 0.0120 | -6.00 and -6.25 | -0.312, 0.0163 | +10.00 and +10.25 | +1.323, 0.0318 | complete (EPYC) |
| camb45-tc092-re570k | 0.092 | 4.5 | 5.7e+05 | 23 | 0.0129 | -7.25 and -7.50 | -0.276, 0.0177 | +13.25 and +13.50 | +1.647, 0.0447 | complete (EPYC) |
| camb3-tc050-re570k | 0.050 | 3.0 | 5.7e+05 | 16 | 0.0116 | -3.75 and -4.00 | -0.075, 0.0229 | +6.50 and +6.75 | +0.964, 0.0338 | complete (laptop) |
| camb3-tc120-re570k | 0.120 | 3.0 | 5.7e+05 | 22 | 0.0131 | -10.25 and -10.50 | -0.744, 0.0231 | +12.75 and +13.00 | +1.514, 0.0370 | complete (EPYC) |
| camb45-tc070-re570k | 0.070 | 4.5 | 5.7e+05 | 23 | 0.0126 | -5.25 and -5.50 | -0.063, 0.0154 | +11.00 and +11.25 | +1.519, 0.0378 | complete (EPYC) |
| camb3-tc092-re570k | 0.092 | 3.0 | 5.7e+05 | 28 | 0.0124 | -8.50 and -8.75 | -0.574, 0.0205 | +13.25 and +13.50 | +1.547, 0.0419 | complete (EPYC) |
| camb2-tc070-re570k | 0.070 | 2.0 | 5.7e+05 | 13 | 0.0117 | -6.50 and -7.00 | -0.479, 0.0173 | beyond +6.00 | +0.868, 0.0176 | running (EPYC) |
| camb45-tc080-re570k | 0.080 | 4.5 | 5.7e+05 | 28 | 0.0128 | -6.25 and -6.50 | -0.169, 0.0165 | +13.50 and +13.75 | +1.615, 0.0509 | complete (EPYC) |
| camb2-tc050-re570k | 0.050 | 2.0 | 5.7e+05 | 16 | 0.0113 | -4.25 and -4.50 | -0.236, 0.0266 | +6.25 and +6.50 | +0.833, 0.0358 | complete (laptop) |
| camb3-tc070-re280k | 0.070 | 3.0 | 2.8e+05 | 17 | 0.0133 | -4.75 and -5.00 | -0.178, 0.0166 | +8.25 and +8.50 | +1.144, 0.0286 | complete (laptop) |
| camb45-tc092-re970k | 0.092 | 4.5 | 9.7e+05 | 26 | 0.0120 | -8.00 and -8.25 | -0.358, 0.0173 | +14.00 and +14.25 | +1.731, 0.0453 | complete (EPYC) |
| flat-tc050-r050-re570k | 0.050 | 0.0 | 5.7e+05 | 24 | 0.0122 | -4.50 and -4.75 | -0.300, 0.0463 | +9.25 and +9.50 | +1.166, 0.0290 | complete (laptop) |
| flat-tc120-r050-re570k | 0.120 | 0.0 | 5.7e+05 | 22 | 0.0166 | -4.50 and -4.75 | +0.083, 0.0490 | +12.50 and +12.75 | +1.656, 0.0423 | complete (EPYC) |
| flat-tc092-r050-re280k | 0.092 | 0.0 | 2.8e+05 | 23 | 0.0161 | -4.50 and -4.75 | -0.077, 0.0489 | +11.75 and +12.00 | +1.496, 0.0385 | complete (EPYC) |
| flat-tc092-r050-re140k | 0.092 | 0.0 | 1.4e+05 | 25 | 0.0179 | -4.25 and -4.50 | -0.058, 0.0467 | +11.25 and +11.50 | +1.404, 0.0403 | complete (EPYC) |
| camb45-tc120-re570k | 0.120 | 4.5 | 5.7e+05 | 21 | 0.0135 | -8.75 and -9.00 | -0.437, 0.0193 | +12.75 and +13.00 | +1.630, 0.0403 | complete (EPYC) |
| camb3-tc150-re570k | 0.150 | 3.0 | 5.7e+05 | 22 | 0.0138 | -10.75 and -11.00 | -0.787, 0.0230 | +13.00 and +13.25 | +1.489, 0.0382 | complete (EPYC) |
| camb45-tc150-re570k | 0.150 | 4.5 | 5.7e+05 | 21 | 0.0143 | -10.00 and -10.25 | -0.556, 0.0208 | +12.75 and +13.00 | +1.573, 0.0419 | complete (EPYC) |
| camb3-tc080-re570k | 0.080 | 3.0 | 5.7e+05 | 29 | 0.0122 | -7.25 and -7.50 | -0.446, 0.0184 | +13.00 and +13.25 | +1.498, 0.0468 | complete (laptop) |
| camb1-tc070-re570k | 0.070 | 1.0 | 5.7e+05 | 25 | 0.0116 | -7.50 and -7.75 | -0.688, 0.0207 | +8.50 and +8.75 | +1.002, 0.0240 | complete (laptop) |
| flat-tc065-r050-re570k | 0.065 | 0.0 | 5.7e+05 | 30 | 0.0130 | -4.75 and -5.00 | -0.250, 0.0509 | +13.00 and +13.25 | +1.502, 0.0457 | complete (laptop) |
| camb3-tc050-re280k | 0.050 | 3.0 | 2.8e+05 | 17 | 0.0129 | -3.25 and -3.50 | -0.021, 0.0166 | +6.25 and +6.50 | +0.933, 0.0310 | complete (laptop) |
| camb3-tc050-re140k | 0.050 | 3.0 | 1.4e+05 | 22 | 0.0144 | -3.50 and -3.75 | -0.055, 0.0248 | +5.75 and +6.00 | +0.885, 0.0259 | complete (laptop) |
| camb45-tc092-re140k | 0.092 | 4.5 | 1.4e+05 | 23 | 0.0164 | -4.75 and -5.00 | -0.030, 0.0195 | +11.75 and +12.00 | +1.409, 0.0495 | complete (EPYC) |
