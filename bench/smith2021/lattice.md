# The NACA 0012 blades of [Smi21] on the viscous lattice (section table v1)

Written by `scripts/smith_lattice.py`. Perfect mirror at the root, uniform stream: the ceiling's boundary layer (8 % of the long blade's span, 16 % of the short one's) and the tunnel's walls are not in it. Slopes are of the lift over 0…4°. "5 % below" is against the line through the rows at 0° and 4°, as in `bench/knee/one-degree/`. The stall is the last row before the normal force falls by more than 0.05 in half a degree. The most loaded strip is the one nearest the most lift its section carries attached; "margin" is from its incidence to the end of its section's attached range. The strip criterion is `bladehydro.knee`'s rule at its share of 0.606.

| blade | Re on the mean chord | lift slope per degree: measured / lattice | measured: 5 % below at ° | measured stall after °, C_L there | lattice C_L there | most loaded strip: z / span | its lift | share of its section's limit | its incidence ° | margin ° | lattice's own polar: 5 % below at ° | strip criterion ° | measured against its line there | two degrees on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| long, span 240 mm | 0.4e6 | 0.0689 / 0.0688 | 13.2 | 16.0, 0.928 | 1.035 | 0.43 | 1.10 | 0.95 | 11.1 | +0.8 | 14.9 | 9.3 | +4 % | -1 % |
| long, span 240 mm | 0.6e6 | 0.0659 / 0.0693 | 15.8 | 17.5, 0.935 | 1.139 | 0.43 | 1.21 | 0.97 | 11.9 | +0.6 | 16.2 | 10.0 | +7 % | +3 % |
| long, span 240 mm | 0.8e6 | 0.0665 / 0.0696 | 16.6 | 16.5, 1.058 | 1.092 | 0.43 | 1.16 | 0.91 | 11.2 | +1.7 | 16.6 | 10.2 | +8 % | +4 % |
| long, span 240 mm | 1.0e6 | 0.0672 / 0.0697 | 17.1 | 17.0, 1.115 | 1.124 | 0.34 | 1.20 | 0.92 | 11.5 | +1.6 | 16.7 | 10.4 | +7 % | +4 % |
| short, span 120 mm | 1.0e6 | 0.0462 / 0.0492 | 21.4 | 21.0, 1.029 | 0.981 | 0.34 | 1.06 | 0.81 | 9.9 | +3.2 | 20.6 | 14.4 | +10 % | +10 % |
