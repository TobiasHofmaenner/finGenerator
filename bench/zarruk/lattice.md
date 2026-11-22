# The hydrofoil of [Zar14] on the viscous lattice (section table v1)

Written by `scripts/zarruk_lattice.py`. Perfect mirror at the root, no other wall. Slopes are of the line through the origin over 4…8° (measured: clean markers only; the paper gives 4.82 per rad for Type I at Re 1.0e6). The most loaded strip is the one nearest the most lift its section carries attached; "margin" is from its incidence to the end of its section's attached range. The strip criterion is `bladehydro.knee`'s rule at its share of 0.606.

| foil | Re on the mean chord | lift slope per rad: measured / lattice | measured stall: ° , C_L | lattice C_L there | most loaded strip: z / span | its lift | share of the most lift its section carries attached | its incidence ° | margin ° | lattice's own polar: 5 % below its line at ° | strip criterion ° | measured against its own line there | two degrees on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Type II | 0.4e6 | – / 4.46 | 11.0, 0.776 | 0.837 | 0.59 | 0.88 | 0.84 | 8.4 | +2.2 | 14.5 | 7.6 | – | – |
| Type II | 0.6e6 | 4.67 / 4.48 | 10.5, 0.837 | 0.808 | 0.59 | 0.86 | 0.76 | 8.0 | +3.1 | 15.5 | 8.2 | -0 % | -2 % |
| Type II | 0.8e6 | 4.77 / 4.49 | not reached (to 10.0°, 0.820) | – | – | – | – | – | – | 15.0 | 8.4 | -0 % | – |
| Type II | 1.0e6 | 4.87 / 4.50 | not reached (to 6.0°, 0.509) | – | – | – | – | – | – | 15.0 | 8.6 | – | – |
| Type I | 0.4e6 | – / 4.46 | 11.0, 0.761 | 0.837 | 0.59 | 0.88 | 0.84 | 8.4 | +2.2 | 14.5 | 7.6 | -1 % | -5 % |
| Type I | 0.6e6 | 4.60 / 4.48 | 10.5, 0.804 | 0.808 | 0.59 | 0.86 | 0.76 | 8.0 | +3.1 | 15.5 | 8.2 | -2 % | -4 % |
| Type I | 0.8e6 | 4.66 / 4.49 | not reached (to 9.0°, 0.720) | – | – | – | – | – | – | 15.0 | 8.4 | -1 % | – |
| Type I | 1.0e6 | 4.78 / 4.50 | not reached (to 6.0°, 0.502) | – | – | – | – | – | – | 15.0 | 8.6 | – | – |
