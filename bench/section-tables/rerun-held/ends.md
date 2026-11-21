# The sections on the held stream: where each attached range ends

Written by the collector of the rerun (`~/bench-results/sections3/collect.py`). A row is past an end when it did not settle in 3000 iterations or has more than four times the section's lowest drag. Each end lies between the last row inside and the first row past it.

| section | t/c | camber % | Re | rows | lowest c_d | lower end between ° | c_l, c_d at the last row inside | upper end between ° | c_l, c_d at the last row inside | state |
|---|---|---|---|---|---|---|---|---|---|---|
| camb3-tc070-re140k | 0.070 | 3.0 | 1.4e+05 | 22 | 0.0150 | -4.50 and -4.75 | -0.149, 0.0233 | +7.75 and +8.00 | +1.059, 0.0304 | complete (EPYC) |
| camb3-tc070-re570k | 0.070 | 3.0 | 5.7e+05 | 24 | 0.0120 | -6.00 and -6.25 | -0.312, 0.0163 | +10.00 and +10.25 | +1.323, 0.0318 | complete (EPYC) |
| camb45-tc092-re570k | 0.092 | 4.5 | 5.7e+05 | 5 | 0.0129 | beyond -3.50 | +0.129, 0.0131 | beyond +2.00 | +0.728, 0.0150 | running (EPYC) |
