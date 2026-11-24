#!/bin/sh
# Every run's strip loads into strip-loads.json, then the tables into strip-loads.txt.
# The surface files (a+NN.N/postProcessing/surfaces/*/fin.vtk) are not in the repository:
# V, W and S are where they were pulled to (or run) on the machine this was run on. TABLES_ONLY=1 skips the extraction.
V=${V:-/home/kali/bench-results/sym-series/vtk}
W=${W:-/home/kali/bench-results/nose7/vtk}
S=${S:-/home/kali/bench-results/levers10}
R=$(cd "$(dirname "$0")" && pwd)
cd "$R/../../.." || exit 1
SYM=$R/fin-gen2-planform-sym
G3=bench/design-points/cfd/fin-sliders.json
G2=bench/mount/fins/side-shipped-gen2.json
x() { [ -n "$TABLES_ONLY" ] || uv run python $R/strip_loads.py extract $1 $2 $3 $R/strip-loads.json; }
x $SYM-tc050.json $V/tc050/L5/sym-tc050-gen2-planform-L5 sym-tc050-gen2-planform-L5
x $SYM-tc050.json $V/tc050/L6/sym-tc050-gen2-planform-L6 sym-tc050-gen2-planform-L6
x $SYM-tc066.json $V/tc066-L5/sym-tc066-gen2-planform-L5 sym-tc066-gen2-planform-L5
x $SYM-tc066.json $V/tc066-5ms-L5/sym-tc066-gen2-planform-5ms-L5 sym-tc066-gen2-planform-5ms-L5
x $SYM-tc080.json $V/tc080-L5/sym-tc080-gen2-planform-L5 sym-tc080-gen2-planform-L5
x $SYM-tc080.json $V/tc080-L6/sym-tc080-gen2-planform-L6 sym-tc080-gen2-planform-L6
x $SYM-tc080.json $V/tc080-L7/sym-tc080-gen2-planform-L7 sym-tc080-gen2-planform-L7
x $SYM-tc080.json $W/tc080-L6x/sym-tc080-gen2-planform-L6x sym-tc080-gen2-planform-exact-L6
x $SYM-tc080.json $W/tc080-L7x/sym-tc080-gen2-planform-L7x sym-tc080-gen2-planform-exact-L7
x $G3 $W/epyc/sliders-L6x/gen3-side-sliders-L6x gen3-side-sliders-L6x
x $G2 $W/epyc/flat-L6x/flat-inside-L6x flat-inside-L6x
x $R/fin-bw04-replica.json ${L:-/home/kali/bench-results/nose7}/bw04-L6x/bw04-L6x bw04-L6x-laptop
x $R/fin-gen2-planform-gen3-section.json $S/g2p-g3s/gen2-planform-gen3-section-L6x gen2-planform-gen3-section-L6x
x $R/fin-gen3-planform-gen2-section.json $S/g3p-g2s/gen3-planform-gen2-section-L6x gen3-planform-gen2-section-L6x
x $R/fin-gen3-tip035.json $S/tip035/gen3-side-tip035-L6x gen3-side-tip035-L6x
t() { uv run python $R/strip_loads.py table $1 $2 $3 $R/strip-loads.json 2>/dev/null; echo; }
{
t $SYM-tc050.json 8.5 sym-tc050-gen2-planform-L5
t $SYM-tc050.json 8.5 sym-tc050-gen2-planform-L6
t $SYM-tc066.json 8.5 sym-tc066-gen2-planform-L5
t $SYM-tc066.json 5.0 sym-tc066-gen2-planform-5ms-L5
t $SYM-tc080.json 8.5 sym-tc080-gen2-planform-L5
t $SYM-tc080.json 8.5 sym-tc080-gen2-planform-L6
t $SYM-tc080.json 8.5 sym-tc080-gen2-planform-L7
t $SYM-tc080.json 8.5 sym-tc080-gen2-planform-exact-L6
t $SYM-tc080.json 8.5 sym-tc080-gen2-planform-exact-L7
t $G3 8.5 gen3-side-sliders-L6x
t $G2 8.5 flat-inside-L6x
t $R/fin-bw04-replica.json 7.0 bw04-L6x-laptop
t $R/fin-gen2-planform-gen3-section.json 8.5 gen2-planform-gen3-section-L6x
t $R/fin-gen3-planform-gen2-section.json 8.5 gen3-planform-gen2-section-L6x
t $R/fin-gen3-tip035.json 8.5 gen3-side-tip035-L6x
} > $R/strip-loads.txt
grep -c "" $R/strip-loads.txt
