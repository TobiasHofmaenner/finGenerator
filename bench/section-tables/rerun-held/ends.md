# The sections on the held stream: where each attached range ends

Written by the collector of the rerun (`~/bench-results/sections3/collect.py`). A row is past an end when it did not settle in 3000 iterations or has more than four times the section's lowest drag. Each end lies between the last row inside and the first row past it.

| section | t/c | camber % | Re | rows | lowest c_d | lower end between ° | c_l, c_d at the last row inside | upper end between ° | c_l, c_d at the last row inside | state |
|---|---|---|---|---|---|---|---|---|---|---|
| camb3-tc070-re140k | 0.070 | 3.0 | 1.4e+05 | 22 | 0.0150 | -4.50 and -4.75 | -0.149, 0.0233 | +7.75 and +8.00 | +1.059, 0.0304 | complete (EPYC) |
| flat-tc092-r050-re570k | 0.092 | 0.0 | 5.7e+05 | 24 | 0.0146 | -4.75 and -5.00 | -0.098, 0.0515 | +12.75 and +13.00 | +1.603, 0.0401 | complete (EPYC) |
| camb3-tc070-re570k | 0.070 | 3.0 | 5.7e+05 | 24 | 0.0120 | -6.00 and -6.25 | -0.312, 0.0163 | +10.00 and +10.25 | +1.323, 0.0318 | complete (EPYC) |
| camb45-tc092-re570k | 0.092 | 4.5 | 5.7e+05 | 23 | 0.0129 | -7.25 and -7.50 | -0.276, 0.0177 | +13.25 and +13.50 | +1.647, 0.0447 | complete (EPYC) |
| camb3-tc050-re570k | 0.050 | 3.0 | 5.7e+05 | 16 | 0.0116 | -3.75 and -4.00 | -0.075, 0.0229 | +6.50 and +6.75 | +0.964, 0.0338 | complete (laptop) |
| camb3-tc092-re570k | 0.092 | 3.0 | 5.7e+05 | 28 | 0.0124 | -8.50 and -8.75 | -0.574, 0.0205 | +13.25 and +13.50 | +1.547, 0.0419 | complete (EPYC) |
| camb45-tc080-re570k | 0.080 | 4.5 | 5.7e+05 | 12 | 0.0128 | beyond -6.00 | -0.142, 0.0159 | beyond +8.00 | +1.321, 0.0248 | running (EPYC) |
| camb2-tc050-re570k | 0.050 | 2.0 | 5.7e+05 | 16 | 0.0113 | -4.25 and -4.50 | -0.236, 0.0266 | +6.25 and +6.50 | +0.833, 0.0358 | complete (laptop) |
| camb3-tc070-re280k | 0.070 | 3.0 | 2.8e+05 | 13 | 0.0133 | -4.75 and -5.00 | -0.178, 0.0166 | beyond +6.00 | +0.955, 0.0205 | running (laptop) |
| camb45-tc092-re970k | 0.092 | 4.5 | 9.7e+05 | 26 | 0.0120 | -8.00 and -8.25 | -0.358, 0.0173 | +14.00 and +14.25 | +1.731, 0.0453 | complete (EPYC) |
| camb3-tc150-re570k | 0.150 | 3.0 | 5.7e+05 | 19 | 0.0138 | -10.75 and -11.00 | -0.787, 0.0230 | beyond +13.00 | +1.489, 0.0382 | running (EPYC) |
| camb3-tc080-re570k | 0.080 | 3.0 | 5.7e+05 | 29 | 0.0122 | -7.25 and -7.50 | -0.446, 0.0184 | +13.00 and +13.25 | +1.498, 0.0468 | complete (laptop) |
| camb1-tc070-re570k | 0.070 | 1.0 | 5.7e+05 | 25 | 0.0116 | -7.50 and -7.75 | -0.688, 0.0207 | +8.50 and +8.75 | +1.002, 0.0240 | complete (laptop) |
| camb3-tc050-re280k | 0.050 | 3.0 | 2.8e+05 | 13 | 0.0129 | -3.25 and -3.50 | -0.021, 0.0166 | beyond +5.50 | +0.895, 0.0214 | running (laptop) |
| camb3-tc050-re140k | 0.050 | 3.0 | 1.4e+05 | 9 | 0.0144 | beyond -3.50 | -0.055, 0.0248 | beyond +2.00 | +0.536, 0.0157 | running (laptop) |
