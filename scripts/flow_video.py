"""Marketing flow-visualisation video for a fingen fin.

Renders a hero fin as a near-orthographic swept side profile with a bundle of
glowing streamline "comets" advecting through a CFD velocity field and a
rolled-up tip vortex, under a slow camera orbit that sweeps through the clean
profile mid-clip. The fin surface is coloured either by CFD kinematic pressure
(default) or, with ``--fem-surface``, by FEM von Mises stress on a gmsh mesh —
and in stress mode the blade can gently flex under an oscillating deflection
factor (the displacement field rides along in the .npz). House style: near-black
background, cyan/white flow, orange stress highlights.

The velocity field comes from a reconstructed OpenFOAM case exposed through a
``.foam`` stub next to ``constant/polyMesh`` with U and p in the latest time.
The stress surface is a plain ``.npz`` from ``scripts/fin_fem_stress.py`` — so
this stays a pyvista-only render with no fingen/OCCT import. It is a glamour
shot: the stress fin and the flow need not be the same geometry.

Usage::

    uv run --with pyvista --with 'imageio[ffmpeg]' --with matplotlib \
        --with pillow python scripts/flow_video.py CASE.foam \
        [--fem-surface stress-surface.npz] [options]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pyvista as pv
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.font_manager import FontProperties, findfont
from PIL import Image, ImageDraw, ImageFont

# --- house style -----------------------------------------------------------
BG = "#0b0e11"
CYAN = "#7fd4e0"
ORANGE = "#f2a154"

PRESS_CMAP = LinearSegmentedColormap.from_list(
    "tfins_press",
    [(0.00, "#ffffff"), (0.15, "#c9f2f8"), (0.32, CYAN), (0.45, "#1f5560"),
     (0.50, "#0e2129"), (0.58, "#3a2f28"), (0.78, "#b0703c"), (1.00, ORANGE)],
)
VEL_CMAP = LinearSegmentedColormap.from_list(
    "tfins_vel",
    [(0.00, "#123a63"), (0.30, "#1f6f9c"), (0.58, CYAN), (0.82, "#d7f4fa"),
     (1.00, "#ffffff")],
)
STRESS_CMAP = LinearSegmentedColormap.from_list(
    "tfins_stress",
    [(0.00, "#141a2e"), (0.28, "#4a2a6b"), (0.52, "#9a3b55"), (0.72, "#e07a3c"),
     (0.88, ORANGE), (1.00, "#ffe9c2")],
)
PRESS_CLIM = (-40.0, 20.0)
VEL_CLIM = (3.0, 10.5)


def smoothstep(t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


# --- CFD case + streamlines ------------------------------------------------
def load_case(foam: Path) -> tuple[pv.PolyData, pv.PolyData]:
    reader = pv.POpenFOAMReader(str(foam))
    reader.set_active_time_value(reader.time_values[-1])
    reader.cell_to_point_creation = True
    mb = reader.read()
    fin = mb["boundary"]["fin"]
    fin.set_active_scalars("p", preference="point")
    return mb["internalMesh"], fin


def suction_sign(fin: pv.PolyData) -> int:
    """+1 if the low-pressure (suction) face points to +y, else -1."""
    y = fin.points[:, 1]
    ymid = 0.5 * (y.min() + y.max())
    p = fin.point_data["p"]
    return 1 if p[y > ymid].mean() < p[y <= ymid].mean() else -1


def make_seeds(bounds: tuple[float, ...], sign: int) -> tuple[np.ndarray, np.ndarray]:
    fx0, fx1, fy0, fy1, _fz0, fz1 = bounds
    chord, span, ymid = fx1 - fx0, fz1, 0.5 * (fy0 + fy1)

    def yp(f: float) -> float:
        return ymid - sign * f * chord

    def ysuc(f: float) -> float:
        return ymid + sign * f * chord

    def rake(z0: float, z1: float, n: int,
             ylayers: tuple[float, ...]) -> list[tuple[float, float, float]]:
        """Suction-side seeds over a span band. Origins are FANNED in x — higher
        span and outer-thickness layers begin progressively further upstream — so
        the starts spread diagonally instead of stacking on one seed wall."""
        pts = []
        for i, z in enumerate(np.linspace(z0, z1, n)):
            for j, yf in enumerate(ylayers):
                xf = -0.05 - 0.55 * (z / span) - 0.18 * j + 0.05 * (i % 3)
                pts.append((fx0 + xf * chord, ysuc(yf), z))
        return pts

    # Full 3D field -> seed the whole span, not just the tip. The suction-side
    # layers approach at many heights, wrap the leading edge and accelerate over
    # the suction face (they flow AROUND the blade, never through it — the solid
    # is excluded from the domain). ctx = lower/mid span (thinner) + a few
    # pressure-side accents; tip = upper span rolling into the tip vortex.
    ctx = rake(0.14 * span, 0.74 * span, 11, (0.02, 0.055))
    ctx += [(fx0 - 0.7 * chord, yp(0.06), z * span) for z in (0.35, 0.6, 0.85)]
    tip = rake(0.80 * span, 1.16 * span, 10, (0.02, 0.06))
    return np.array(ctx), np.array(tip)


def integrate(internal: pv.PolyData, seeds: np.ndarray, max_steps: int,
              step: float) -> pv.PolyData:
    return internal.streamlines_from_source(
        pv.PolyData(seeds), vectors="U", integration_direction="forward",
        initial_step_length=step, max_steps=max_steps, terminal_speed=1e-4)


def annotate(strl: pv.PolyData, seed: int) -> np.ndarray:
    """Per-line arc length + random phase; return base velocity RGB."""
    lines, pts = strl.lines, strl.points
    arc = np.zeros(strl.n_points)
    phase = np.zeros(strl.n_points)
    rng = np.random.default_rng(seed)
    i = 0
    while i < len(lines):
        n = lines[i]
        ids = lines[i + 1: i + 1 + n]
        seg = np.linalg.norm(np.diff(pts[ids], axis=0), axis=1)
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        arc[ids] = cum / (cum[-1] if cum[-1] > 0 else 1.0)
        phase[ids] = rng.random()
        i += n + 1
    strl["arc"] = arc
    strl["phase"] = phase
    strl["vmag"] = np.linalg.norm(strl["U"], axis=1)
    t = np.clip((strl["vmag"] - VEL_CLIM[0]) / (VEL_CLIM[1] - VEL_CLIM[0]), 0, 1)
    return VEL_CMAP(t)[:, :3]


def comet_rgba(strl: pv.PolyData, base_rgb: np.ndarray, tt: float, trav: float,
               amp: float, nc: int = 3, tail: float = 0.33) -> np.ndarray:
    """Bright travelling heads with fading tails advected along each line."""
    q = np.mod((strl["arc"] - trav * tt - strl["phase"]) * nc, 1.0)
    glow = np.exp(-q / tail)
    w = glow[:, None]
    rgb = base_rgb * (1 - 0.8 * w) + 0.8 * w
    rgba = np.empty((strl.n_points, 4), np.uint8)
    rgba[:, :3] = np.clip(rgb * 255, 0, 255).astype(np.uint8)
    rgba[:, 3] = np.clip(glow * amp * 255, 0, 255).astype(np.uint8)
    return rgba


# --- stress (FEM) hero surface ---------------------------------------------
def load_stress(npz: Path, zshift: float = 0.0) -> dict:
    d = np.load(npz)
    faces = d["faces"]
    cells = np.hstack([np.full((len(faces), 1), 3, np.int64), faces]).ravel()
    vm = d["vm"]
    pts = d["points"].astype(float).copy()
    pts[:, 2] += zshift  # align the FEM base to the CFD fin's 2 mm domain sink
    return {"points": pts, "cells": cells, "vm": vm,
            "disp": d["disp"].astype(float),
            "clim": (0.0, float(np.percentile(vm, 98.5)))}


def stress_polydata(st: dict, factor: float) -> pv.PolyData:
    surf = pv.PolyData(st["points"] + factor * st["disp"], st["cells"])
    surf.point_data["vm"] = st["vm"]
    return surf.compute_normals(auto_orient_normals=True, feature_angle=45,
                                split_vertices=False)


# --- camera ----------------------------------------------------------------
def camera_pose(focal: tuple[float, float, float], radius: float, az_deg: float,
                el_deg: float, sign: int) -> list:
    a, e = np.radians(az_deg), np.radians(el_deg)
    cx, cy, cz = focal
    return [(cx + radius * np.cos(e) * np.cos(a),
             cy + sign * radius * np.cos(e) * np.sin(a),
             cz + radius * np.sin(e)), focal, (0, 0, 1)]


# --- title overlay ---------------------------------------------------------
def load_font(px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(findfont(FontProperties(family="DejaVu Sans")), px)


def composite_title(arr: np.ndarray, alpha: float,
                    font: ImageFont.FreeTypeFont) -> np.ndarray:
    if alpha <= 0.003:
        return arr
    img = Image.fromarray(arr).convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    h = img.size[1]
    x, y = int(h * 0.055), int(h - h * 0.093)
    a = int(min(max(alpha, 0), 1) * 255)
    d.text((x, y), "T-FINS", font=font, fill=(150, 226, 236, a))
    hw = d.textlength("T-FINS", font=font)
    d.text((x + hw, y), "  —  parametric fin engineering", font=font,
           fill=(214, 224, 230, int(a * 0.72)))
    return np.asarray(Image.alpha_composite(img, layer).convert("RGB"))


# --- rendering -------------------------------------------------------------
def render_frame(size: tuple[int, int], hero: pv.PolyData, hscalar: str, hcmap,
                 hclim, ctx: pv.PolyData, tip: pv.PolyData, ctx_rgba: np.ndarray,
                 tip_rgba: np.ndarray, campos: list, va: float, flip: bool,
                 mesh: bool = False, flow: bool = True) -> np.ndarray:
    """One frame on a fresh plotter (VTK direct-scalar mappers cache, so comet
    colours and the deformed hero must be bound at add-time each frame)."""
    ctx["rgba"] = ctx_rgba
    tip["rgba"] = tip_rgba
    pl = pv.Plotter(off_screen=True, window_size=list(size))
    pl.set_background(BG)
    pl.enable_anti_aliasing("ssaa")
    if mesh:
        # dark occluding shell (depth + hides filaments behind the blade) with
        # the triangulation drawn as glowing scalar-coloured edges on top: a fat
        # translucent halo under a crisp bright core gives the wireframe a bloom.
        edges = hero.extract_all_edges()
        pl.add_mesh(hero, color="#05070a", smooth_shading=True, show_scalar_bar=False)
        pl.add_mesh(edges, scalars=hscalar, cmap=hcmap, clim=hclim, line_width=5.5,
                    render_lines_as_tubes=True, opacity=0.16, lighting=False,
                    show_scalar_bar=False)
        pl.add_mesh(edges, scalars=hscalar, cmap=hcmap, clim=hclim, line_width=2.1,
                    render_lines_as_tubes=True, lighting=False, show_scalar_bar=False)
    else:
        pl.add_mesh(hero, scalars=hscalar, cmap=hcmap, clim=hclim, smooth_shading=True,
                    interpolate_before_map=True, n_colors=1024, specular=0.28,
                    specular_power=22, ambient=0.30, diffuse=0.72, show_scalar_bar=False)
    if flow:
        for m, w in ((ctx, 1.6), (tip, 2.2)):
            pl.add_mesh(m, scalars="vmag", cmap=VEL_CMAP, clim=VEL_CLIM, line_width=w,
                        render_lines_as_tubes=True, opacity=0.10, lighting=False,
                        show_scalar_bar=False)
        pl.add_mesh(ctx, scalars="rgba", rgb=True, line_width=2.8,
                    render_lines_as_tubes=True, lighting=False, show_scalar_bar=False)
        pl.add_mesh(tip, scalars="rgba", rgb=True, line_width=3.6,
                    render_lines_as_tubes=True, lighting=False, show_scalar_bar=False)
    pl.camera_position = campos
    pl.camera.view_angle = va
    arr = pl.screenshot(return_img=True)
    pl.close()
    return np.ascontiguousarray(arr[:, ::-1]) if flip else arr


def encode_mp4(glob: str, out: Path, fps: int) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", glob,
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", str(out)], check=True)


def encode_gif(glob: str, out: Path, fps: int, width: int) -> None:
    pal = out.with_suffix(".pal.png")
    vf = f"scale={width}:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
                    "-i", glob, "-vf", f"{vf},palettegen=stats_mode=full", str(pal)],
                   check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
                    "-i", glob, "-i", str(pal), "-lavfi",
                    f"{vf} [x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3",
                    "-loop", "0", str(out)], check=True)
    pal.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case", type=Path, help="path to the .foam stub (velocity field)")
    ap.add_argument("--fem-surface", type=Path, default=None,
                    help="stress-surface.npz -> stress-mapped, flexing hero fin")
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--work", type=Path, default=None)
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    # Open near the side profile and sweep (increasing az, ~70°) up over the
    # front — leading edge rotating toward camera — into the front quarter.
    ap.add_argument("--az0", type=float, default=78.0)
    ap.add_argument("--az1", type=float, default=148.0)
    ap.add_argument("--el0", type=float, default=6.0)
    ap.add_argument("--el1", type=float, default=13.0)
    ap.add_argument("--mesh", action="store_true",
                    help="draw the fin as a glowing triangulation (shell + edges)")
    ap.add_argument("--fem-zshift", type=float, default=-0.002,
                    help="shift the FEM surface in z to match the CFD domain sink")
    ap.add_argument("--flex-amp", type=float, default=0.0,
                    help="peak deflection exaggeration (stress mode; 0 = rigid)")
    ap.add_argument("--flex-cycles", type=float, default=2.0)
    ap.add_argument("--flex-symmetric", action="store_true",
                    help="flex both ways (±amp·sin) for a back-and-forth wobble "
                         "instead of load-direction-only (0..amp)")
    ap.add_argument("--no-flow", action="store_true",
                    help="omit the streamlines (e.g. a pure structural flex shot)")
    ap.add_argument("--hero-fxrel", type=float, default=1.15,
                    help="focal x as a fraction of chord from the LE; 1.15 frames "
                         "the fin left-third (for flow), ~0.55 centres it")
    ap.add_argument("--zoom", type=float, default=1.0,
                    help="zoom factor (>1 = closer / fin larger in frame)")
    ap.add_argument("--focal-center", action="store_true",
                    help="aim at the fin's own centre so it stays centred when "
                         "zoomed (overrides --hero-fxrel; use for centred shots)")
    ap.add_argument("--no-flip", action="store_true")
    ap.add_argument("--loop", action="store_true",
                    help="seamless loop: camera rocks az0<->az1 (extremes) about "
                         "their midpoint (start), easing to a smooth stop at each "
                         "end; comets keep flowing forward, title breathes in/out")
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--keep-frames", action="store_true")
    args = ap.parse_args()

    pv.OFF_SCREEN = True
    flip = not args.no_flip
    args.out.mkdir(parents=True, exist_ok=True)
    work = args.work or (args.out / "_frames")
    work.mkdir(parents=True, exist_ok=True)

    internal, fin = load_case(args.case)
    sign = suction_sign(fin)
    cseeds, tseeds = make_seeds(fin.bounds, sign)
    ctx = integrate(internal, cseeds, 1700, 0.25)
    tip = integrate(internal, tseeds, 14000, 0.10)
    ctx_rgb, tip_rgb = annotate(ctx, 1), annotate(tip, 2)

    if args.fem_surface:
        st = load_stress(args.fem_surface, args.fem_zshift)
        hscalar, hcmap, hclim = "vm", STRESS_CMAP, st["clim"]
        b = pv.PolyData(st["points"]).bounds
        flex_amp = args.flex_amp
        _hero_cache: dict[float, pv.PolyData] = {}

        def hero_at(factor: float) -> pv.PolyData:
            key = round(factor, 4)  # rigid clips rebuild the blade once, not per frame
            if key not in _hero_cache:
                _hero_cache[key] = stress_polydata(st, factor)
            return _hero_cache[key]
    else:
        hscalar, hcmap, hclim = "p", PRESS_CMAP, PRESS_CLIM
        b = fin.bounds
        flex_amp = 0.0

        def hero_at(factor: float) -> pv.PolyData:  # noqa: ARG001
            return fin

    chord, span = b[1] - b[0], b[5]
    if args.focal_center:
        focal = (0.5 * (b[0] + b[1]), 0.5 * (b[2] + b[3]), 0.5 * (b[4] + b[5]))
    else:
        focal = (b[0] + args.hero_fxrel * chord, 0.5 * (b[2] + b[3]), 0.52 * span)
    radius, va = 5.9 * span / args.zoom, 17.0

    def flex(t: float, cycles: float) -> float:
        if args.flex_symmetric:
            return flex_amp * np.sin(2 * np.pi * cycles * t)
        return flex_amp * (0.5 - 0.5 * np.cos(2 * np.pi * cycles * t))

    font = load_font(int(args.height * 0.028))
    size = (args.width, args.height)
    az_mid, el_mid = 0.5 * (args.az0 + args.az1), 0.5 * (args.el0 + args.el1)

    still_factor = flex_amp * (0.0 if args.flex_symmetric else 0.6)
    still = render_frame(
        size, hero_at(still_factor), hscalar, hcmap, hclim, ctx, tip,
        comet_rgba(ctx, ctx_rgb, 0.4, 3.0, 0.9), comet_rgba(tip, tip_rgb, 0.4, 3.0, 1.0),
        camera_pose(focal, radius, az_mid, el_mid, sign), va, flip, mesh=args.mesh,
        flow=not args.no_flow)
    Image.fromarray(still).save(args.out / "flow-still.png")
    print("wrote", args.out / "flow-still.png", flush=True)
    if args.no_video:
        return

    nframes = int(round(args.seconds * args.fps))
    title_start = args.seconds - 3.0
    trav = 0.25 * args.seconds  # constant comet pace (~1 line-length / 4 s)
    azc, azr = 0.5 * (args.az0 + args.az1), 0.5 * (args.az1 - args.az0)
    if args.loop:
        trav = float(round(trav))  # integer traversals -> seamless comet loop
    for k in range(nframes):
        t = k / nframes
        if args.loop:
            # rock about the midpoint: start there, sweep to az1, back through to
            # az0, and return — smooth (zero-velocity) reversals at both extremes,
            # continuous across the loop seam. Comets never reverse.
            az = azc + azr * np.sin(2 * np.pi * t)
            el = 0.5 * (args.el0 + args.el1)
            talpha = smoothstep(t / 0.15) * smoothstep((1.0 - t) / 0.15)
        else:
            s = smoothstep(t)
            az = args.az0 + (args.az1 - args.az0) * s
            el = args.el0 + (args.el1 - args.el0) * s
            talpha = smoothstep((k / args.fps - title_start) / 0.6)
        arr = render_frame(
            size, hero_at(flex(t, args.flex_cycles)), hscalar, hcmap, hclim, ctx, tip,
            comet_rgba(ctx, ctx_rgb, t, trav, 0.9), comet_rgba(tip, tip_rgb, t, trav, 1.0),
            camera_pose(focal, radius, az, el, sign), va, flip, mesh=args.mesh,
            flow=not args.no_flow)
        arr = composite_title(arr, float(talpha), font)
        Image.fromarray(arr).save(work / f"f{k:04d}.png")
        if k % 30 == 0:
            print(f"frame {k}/{nframes}", flush=True)
    encode_mp4(str(work / "f%04d.png"), args.out / "flow-video.mp4", args.fps)
    print("wrote", args.out / "flow-video.mp4", flush=True)

    # seamless preview: fixed camera, comets + flex complete integer cycles
    gwork = work / "gif"
    gwork.mkdir(parents=True, exist_ok=True)
    gcam = camera_pose(focal, radius, az_mid, el_mid, sign)
    gframes = 56
    for k in range(gframes):
        tt = k / gframes
        arr = render_frame(
            (1280, 720), hero_at(flex(tt, 1.0)), hscalar, hcmap, hclim, ctx, tip,
            comet_rgba(ctx, ctx_rgb, tt, 2.0, 0.9), comet_rgba(tip, tip_rgb, tt, 2.0, 1.0),
            gcam, va, flip, mesh=args.mesh, flow=not args.no_flow)
        Image.fromarray(arr).save(gwork / f"g{k:04d}.png")
    encode_gif(str(gwork / "g%04d.png"), args.out / "flow-preview.gif", 16, 1280)
    print("wrote", args.out / "flow-preview.gif", flush=True)

    if not args.keep_frames:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
