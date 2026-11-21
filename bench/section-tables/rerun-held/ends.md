# The sections on the held stream: where each attached range ends

Written by the collector of the rerun (`~/bench-results/sections3/collect.py`). A row is past an end when it did not settle in 3000 iterations or has more than four times the section's lowest drag. Each end lies between the last row inside and the first row past it.

| section | t/c | camber % | Re | rows | lowest c_d | lower end between ° | c_l, c_d at the last row inside | upper end between ° | c_l, c_d at the last row inside | state |
|---|---|---|---|---|---|---|---|---|---|---|
| camb3-tc070-re140k | 0.070 | 3.0 | 1.4e+05 | 18 | 0.0150 | -4.50 and -4.75 | -0.149, 0.0233 | beyond +7.00 | +1.010, 0.0256 | running (EPYC) |
| camb3-tc070-re570k | 0.070 | 3.0 | 5.7e+05 | 15 | 0.0120 | -6.00 and -6.50 | -0.312, 0.0163 | beyond +6.00 | +0.978, 0.0186 | running (EPYC) |
