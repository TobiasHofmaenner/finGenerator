# The sections on the held stream: where each attached range ends

Written by the collector of the rerun (`~/bench-results/sections3/collect.py`). A row is past an end when it did not settle in 3000 iterations or has more than four times the section's lowest drag. Each end lies between the last row inside and the first row past it.

| section | t/c | camber % | Re | rows | lowest c_d | lower end between ° | c_l, c_d at the last row inside | upper end between ° | c_l, c_d at the last row inside | state |
|---|---|---|---|---|---|---|---|---|---|---|
| camb3-tc070-re140k | 0.070 | 3.0 | 1.4e+05 | 6 | 0.0150 | beyond -3.00 | +0.006, 0.0158 | beyond +4.00 | +0.737, 0.0187 | running (EPYC) |
| camb3-tc070-re570k | 0.070 | 3.0 | 5.7e+05 | 6 | 0.0120 | beyond -3.50 | -0.042, 0.0126 | beyond +4.00 | +0.773, 0.0154 | running (EPYC) |
