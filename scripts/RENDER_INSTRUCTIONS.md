# Flow-video render — instructions for the next agent

How to (re)create the T-FINS marketing "glamour" flow video: a fin rendered as a
glowing FEM von-Mises stress **mesh** (or a shaded pressure/stress surface), with
velocity **streamlines advecting as bright comets**, under a slow camera orbit.

Outputs land in `out/`: `flow-video.mp4` (H.264 1080p), `flow-preview.gif` (720p
seamless), `flow-still.png` (hero frame), and `fem-stress-still.png` (a
solid-surface engineering still). House style: near-black bg `#0b0e11`, cyan
`#7fd4e0`, orange `#f2a154`. It is a **glamour** shot — looks first, physics
second (the stress fin and the flow need not be the same case — but read gotcha #1).

## The two keeper scripts
- `scripts/fin_fem_stress.py` — builds a fin from slider params, meshes it
  (gmsh, second-order tets C3D10), solves a CalculiX static case, and writes
  `stress-surface.npz` (points + nodal displacement in **metres**, triangle
  faces, nodal von Mises in MPa). Runs in the **project venv** (`uv run python`)
  — it imports fingen + build123d and shells out to gmsh/ccx. ~15 s.
- `scripts/flow_video.py` — the renderer, **pyvista only**. Reads a CFD `.foam`
  stub (velocity field) + optional `--fem-surface *.npz` (stress fin). Run in an
  **ephemeral** env; do NOT add these to pyproject/uv.lock:
  `uv run --with pyvista --with 'imageio[ffmpeg]' --with matplotlib --with pillow python scripts/flow_video.py ...`

## Full pipeline from scratch (~15 min total)

1. **FEM stress surface** (the hero fin geometry + von Mises):
   ```
   uv run python scripts/fin_fem_stress.py WORK/stressfin
   ```
   Defaults = the hero fin (depth 115, base 110, **sweep 42**, tip-lobe 0.6,
   LE-fullness 0.57, TE −0.32, t/c 0.09, tip-factor 0.85, **3 grooves**). Every
   slider is a CLI flag (`--sweep`, `--grooves`, ...).

2. **The fin's OWN CFD field** (see gotcha #1 — do not skip):
   ```python
   from fingen.cfd import CaseSpec, write_case, run_case
   from fingen.params import (FinParams, OutlineParams, FoilParams, FoilFamily,
                              GrooveParams, TabParams, TabSystem)
   hero = FinParams(
       outline=OutlineParams(depth=115, base=110, sweep=42, tip_width_ratio=0.6,
                             le_fullness=0.57, te_shape=-0.32),
       foil=FoilParams(family=FoilFamily.FLAT_INSIDE, thickness_ratio=0.09,
                       camber_ratio=0.0, camber_position=0.4, te_thickness=0.7),
       thickness_tip_factor=0.85, grooves=GrooveParams(count=0),  # grooves off for CFD
       tabs=TabParams(system=TabSystem.NONE))
   write_case(CaseSpec(fin=hero, speed=7.0, leeway_deg=10.0, mesh_level=2, end_time=600),
              "WORK/herocfd")
   run_case("WORK/herocfd", procs=8)          # ~2 min, level-2 OpenFOAM RANS
   ```
   Then `touch WORK/herocfd/case.foam`. Use grooves=0 for the CFD (robust
   snappyHexMesh); the grooves recede INTO the blade so the grooved FEM surface
   still sits at/inside the flow boundary — nothing pierces.

3. **Render** (the delivered seamless-loop variant):
   ```
   xvfb-run -a uv run --with pyvista --with 'imageio[ffmpeg]' --with matplotlib \
     --with pillow python scripts/flow_video.py WORK/herocfd/case.foam \
     --fem-surface WORK/stressfin/stress-surface.npz \
     --mesh --loop --az0 58 --az1 158 --el0 8 --el1 12 --seconds 24 \
     --out out --work WORK/frames
   ```
   ~10 min at 1920×1080. Afterwards `chown kali:kali out/flow-*.{mp4,gif,png}`.

## Variant: static-cam structural flex shot
A frontal shot of just the fin flexing back and forth (no flow), same glowing mesh:
```
xvfb-run -a uv run --with pyvista --with 'imageio[ffmpeg]' --with matplotlib \
  --with pillow python scripts/flow_video.py WORK/herocfd/case.foam \
  --fem-surface WORK/stressfin/stress-surface.npz \
  --mesh --no-flow --loop --flex-symmetric --flex-amp 8 --flex-cycles 1 \
  --az0 150 --az1 150 --el0 8 --el1 8 --focal-center --zoom 1.5 \
  --width 2560 --height 1440 --seconds 10 --out WORK/flexout
```
Then copy `WORK/flexout/flow-{video.mp4,preview.gif,still.png}` to
`out/flex-{loop.mp4,preview.gif,still.png}`. Notes: `--loop` with `az0 == az1`
gives a **static** camera (rock amplitude 0); `--flex-symmetric` bends both ways
(±amp·sin) for a wobble; `--focal-center` aims at the fin's centre so it stays
centred under `--zoom` (>1 = closer); the blade bends in y, so a ~az150
frontal-quarter shows the flex best while staying recognisable (az>170 is too
edge-on/thin). Flex amp 8 ≈ ±15 mm tip sweep (swings sideways into the black
margins, so it never clips even zoomed). At az150 the fin is tall-narrow — black
side margins are expected; render 2K+ (mesh detail pops on a hi-res screen).

## Key flags
- `--fem-surface P.npz` → stress hero (else the CFD fin patch coloured by pressure).
- `--mesh` → fin as a glowing triangulation (dark shell + fat glowing edges) vs a shaded surface.
- `--loop` → seamless loop: camera **rocks** between `--az0` and `--az1` (the two
  extremes) about their midpoint (= the first frame), easing to a smooth stop at
  each extreme; comets keep flowing forward; the title breathes in/out (α=0 at the
  seam). Non-loop mode instead does a one-directional smoothstep sweep az0→az1.
- `--no-flow` → omit streamlines (structural flex shot). `--flex-symmetric` →
  ±amp·sin wobble vs load-direction-only. `--hero-fxrel` → focal x (1.15 = fin
  left-third, for flow). `--focal-center` → aim at the fin centre (centred, stays
  centred when zoomed). `--zoom` → >1 = closer / larger in frame.
- `--el0/--el1`, `--seconds/--fps/--width/--height`, `--flex-amp` (0 = rigid;
  >0 flexes the blade by the FEM displacement — omitted from the FLOW primary
  because steady flow + a wobbling blade reads as a glitch, but it's the whole
  point of the flex shot), `--no-flip`, `--fem-zshift` (default −0.002).

## Hard-won gotchas — READ THESE
1. **Streamlines must come from the fin's OWN 3D field.** We have the full 3D
   volume (not a 2D sheet); seed at any span height and lines wrap AROUND the
   blade. Reusing a *different* fin's CFD makes streamlines pierce the displayed
   fin ("through-blade") — an instant disqualifier. Running the own case is cheap.
2. **VTK direct-scalar (`rgb=True`) mappers CACHE their array.** Updating
   `mesh['rgba']` on a shared Plotter does NOT refresh — comets freeze and only
   the camera moves. `render_frame` builds a FRESH plotter every frame on purpose.
3. **Stagger the seed origins.** One upstream seed plane makes all filament
   left-ends stack into a visible wall / starburst. `make_seeds` fans the start-x
   diagonally (higher span + outer layers begin further upstream).
4. **The frame is horizontally flipped** (`np.fliplr`) to put the fin left /
   vortex right. The flip **reverses apparent rotation** — to change spin
   direction, reverse the az sweep (or the sine), NOT the flip.
5. **FEM surface sits 2 mm above the CFD fin** (`write_case` sinks the fin 2 mm so
   the symmetry plane cuts the base). `--fem-zshift -0.002` re-aligns them.
6. **Front-quarter azimuths > ~158° go edge-on** (fin becomes a thin sliver).
   Keep orbit extremes within ~[55, 158].
7. **Geometry-relative + auto-detected**: suction side is detected from surface
   pressure; seeds are fractions of chord/span, so the pipeline adapts to other fins.
8. **Off-screen** needs `xvfb-run -a` (software GL / llvmpipe). Be polite: `nice -n 15`.
9. **Loop seamlessness**: comet `trav` must be an integer in loop mode (handled).

## Palette (defined in flow_video.py)
- `STRESS_CMAP` (von Mises): dark indigo → magenta → orange `#f2a154` → warm white.
- `VEL_CMAP` (streamlines): dark blue → cyan `#7fd4e0` → white.
- `PRESS_CMAP` (kinematic pressure): white/cyan suction → dark → orange pressure.

## Notes
- Scratch dirs (`stressfin/`, `herocfd/`) live in the session scratchpad and are
  **ephemeral** — regenerate via steps 1–2. The two scripts in `scripts/` are the
  durable artifacts.
- CFD sanity for the hero fin: cl ≈ 0.78, cd ≈ 0.087 at 10° (level 2). FEM: max
  von Mises ≈ 8–9 MPa, tip deflection ≈ 1.9 mm at the 10 kPa demo load.
