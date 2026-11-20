# Section table v1 at the referee's nodes

| section | lower end °: RANS / v0 / v1 | upper end °: RANS / v0 / v1 | drag level v1 / v0 | lift slope v1 / v0 | lift retention | cd v1 / RANS over the settled rows: min … max | largest cl difference |
|---|---|---|---|---|---|---|---|
| flat-tc092-re570k | -1.38 / -0.81 / -1.48 | +11.00 / +11.51 / +11.00 | 1.244 | 0.967 | 0.79 | 0.95 … 1.10 | 0.020 |
| camb3-tc092-re570k | -6.09 / -7.23 / -5.94 | +10.17 / +12.44 / +10.18 | 1.039 | 0.975 | 0.57 | 0.96 … 1.19 | 0.005 |
| camb45-tc070-re570k | -3.67 / -4.47 / -3.66 | +8.33 / +10.03 / +8.33 | 1.097 | 0.972 | 0.50 | 0.93 … 1.30 | 0.003 |
| camb3-tc070-re570k | -3.77 / -5.06 / -3.95 | +8.09 / +9.59 / +8.10 | 1.065 | 0.971 | 0.71 | 0.90 … 1.11 | 0.006 |
| camb45-tc092-re570k | -6.07 / -6.20 / -5.89 | +11.21 / +12.14 / +11.21 | 1.128 | 0.978 | 0.66 | 0.87 … 1.25 | 0.008 |
| camb2-tc070-re570k | -4.65 / -5.47 / -4.62 | +6.68 / +9.00 / +6.69 | 1.044 | 0.967 | 0.30 | 0.95 … 1.41 | 0.003 |

cambered: 5 nodes, plane over ['t/c', 'camber']; the plane alone misses a node by at most d_lower 0.384, d_upper 0.406, log_level 0.019, log_level_below 0.122, slope 0.001, d_alpha0 0.017, retention 0.213 (spread back in around each node)

flat_inside: 1 nodes, plane over a constant; the plane alone misses a node by at most d_lower 0.000, d_upper 0.000, log_level 0.000, log_level_below 0.000, slope 0.000, d_alpha0 0.000, retention 0.000 (spread back in around each node)
