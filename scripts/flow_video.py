"""Marketing flow-visualisation video for a fingen fin CFD case.

Renders the fin surface (coloured by kinematic pressure) with a bundle of
glowing streamline "comets" advecting through the velocity field and a
rolled-up tip vortex, all under a slow cinematic camera orbit. Produces an
H.264 mp4 plus a short looping preview GIF, in the T-FINS house style
(near-black background, cyan / white flow, orange pressure highlights).

The input must be a reconstructed OpenFOAM case exposed through a ``.foam``
stub file that sits next to ``constant/polyMesh`` and a latest time directory
holding ``U`` and ``p``.

Usage::

    uv run --with pyvista --with 'imageio[ffmpeg]' --with matplotlib \
        --with pillow python scripts/flow_video.py CASE.foam [options]

Off-screen software rendering works under ``xvfb-run`` on hosts without a GPU.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
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
    [
        (0.00, "#ffffff"),
        (0.15, "#c9f2f8"),
        (0.32, CYAN),
        (0.45, "#1f5560"),
        (0.50, "#0e2129"),
        (0.58, "#3a2f28"),
        (0.78, "#b0703c"),
        (1.00, ORANGE),
    ],
)
VEL_CMAP = LinearSegmentedColormap.from_list(
    "tfins_vel",
    [
        (0.00, "#123a63"),
        (0.30, "#1f6f9c"),
        (0.58, CYAN),
        (0.82, "#d7f4fa"),
        (1.00, "#ffffff"),
    ],
)
PRESS_CLIM = (-40.0, 20.0)
VEL_CLIM = (3.0, 10.5)


def smoothstep(t: np.ndarray | float) -> np.ndarray | float:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# --- case loading ----------------------------------------------------------
def load_case(foam: Path) -> tuple[pv.PolyData, pv.PolyData]:
    reader = pv.POpenFOAMReader(str(foam))
    reader.set_active_time_value(reader.time_values[-1])
    reader.cell_to_point_creation = True
    mb = reader.read()
    internal = mb["internalMesh"]
    fin = mb["boundary"]["fin"]
    fin.set_active_scalars("p", preference="point")
    return internal, fin


def suction_sign(fin: pv.PolyData) -> int:
    """Return +1 if the low-pressure (suction) face points to +y, else -1."""
    y = fin.points[:, 1]
    ymid = 0.5 * (y.min() + y.max())
    p = fin.point_data["p"]
    hi = p[y > ymid].mean()
    lo = p[y <= ymid].mean()
    return 1 if hi < lo else -1


# --- streamline seeding (geometry-relative) --------------------------------
def make_seeds(bounds: tuple[float, ...], sign: int) -> tuple[np.ndarray, np.ndarray]:
    fx0, fx1, fy0, fy1, _fz0, fz1 = bounds
    chord = fx1 - fx0
    span = fz1
    ymid = 0.5 * (fy0 + fy1)
    xs = fx0 - 0.95 * chord

    def y_prs(f: float) -> float:  # pressure side (opposite suction)
        return ymid - sign * f * chord

    def y_suc(f: float) -> float:
        return ymid + sign * f * chord

    ctx = [(xs, y_prs(0.37), fz * span) for fz in (0.64, 0.83, 1.02)]
    ctx += [(xs, y_suc(0.01), 1.27 * span), (xs, y_suc(0.01), 1.12 * span)]
    ctx += [(xs, y_prs(0.33), 0.38 * span)]

    tip: list[tuple[float, float, float]] = []
    xc, yc, zc = fx0 + 0.07 * chord, y_suc(0.06), 0.98 * span
    for rr in (0.029, 0.058, 0.087):
        r = rr * chord
        for ang in np.linspace(0, 2 * np.pi, 20, endpoint=False):
            tip.append((xc + 0.03 * chord * np.cos(ang),
                        yc + r * np.cos(ang), zc + r * np.sin(ang)))
    for xx in np.linspace(fx0 - 0.16 * chord, fx0 + 0.51 * chord, 10):
        tip.append((xx, y_suc(0.03), zc))
    return np.array(ctx), np.array(tip)


def integrate(internal: pv.PolyData, seeds: np.ndarray, max_steps: int,
              step: float) -> pv.PolyData:
    return internal.streamlines_from_source(
        pv.PolyData(seeds), vectors="U", integration_direction="forward",
        initial_step_length=step, max_steps=max_steps, terminal_speed=1e-4)


def annotate(strl: pv.PolyData, seed: int) -> np.ndarray:
    """Attach per-line arc length + random phase; return base velocity RGB."""
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
    vmag = np.linalg.norm(strl["U"], axis=1)
    strl["vmag"] = vmag
    t = np.clip((vmag - VEL_CLIM[0]) / (VEL_CLIM[1] - VEL_CLIM[0]), 0, 1)
    return VEL_CMAP(t)[:, :3]


def comet_rgba(strl: pv.PolyData, base_rgb: np.ndarray, tt: float,
               trav: float, amp: float, nc: int = 3, tail: float = 0.33,
               ) -> np.ndarray:
    """Bright travelling heads with fading tails advected along each line."""
    q = np.mod((strl["arc"] - trav * tt - strl["phase"]) * nc, 1.0)
    glow = np.exp(-q / tail)
    w = glow[:, None]
    rgb = base_rgb * (1 - 0.8 * w) + 0.8 * w
    rgba = np.empty((strl.n_points, 4), np.uint8)
    rgba[:, :3] = np.clip(rgb * 255, 0, 255).astype(np.uint8)
    rgba[:, 3] = np.clip(glow * amp * 255, 0, 255).astype(np.uint8)
    return rgba


# --- camera ----------------------------------------------------------------
def camera_pose(focal: tuple[float, float, float], radius: float,
                az_deg: float, el_deg: float, sign: int) -> list:
    a, e = np.radians(az_deg), np.radians(el_deg)
    cx, cy, cz = focal
    pos = (
        cx + radius * np.cos(e) * np.cos(a),
        cy + sign * radius * np.cos(e) * np.sin(a),
        cz + radius * np.sin(e),
    )
    return [pos, focal, (0, 0, 1)]


# --- title overlay ---------------------------------------------------------
def load_font(px: int) -> ImageFont.FreeTypeFont:
    path = findfont(FontProperties(family="DejaVu Sans"))
    return ImageFont.truetype(path, px)


def composite_title(arr: np.ndarray, alpha: float,
                    font: ImageFont.FreeTypeFont) -> np.ndarray:
    if alpha <= 0.003:
        return arr
    img = Image.fromarray(arr).convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    h = img.size[1]
    x, y = int(h * 0.055), int(h - h * 0.093)
    a = int(np.clip(alpha, 0, 1) * 255)
    head = "T-FINS"
    tail = "  —  parametric fin engineering"
    d.text((x, y), head, font=font, fill=(150, 226, 236, a))
    hw = d.textlength(head, font=font)
    d.text((x + hw, y), tail, font=font, fill=(214, 224, 230, int(a * 0.72)))
    out = Image.alpha_composite(img, layer).convert("RGB")
    return np.asarray(out)


# --- rendering -------------------------------------------------------------
def render_frame(size: tuple[int, int], fin: pv.PolyData, ctx: pv.PolyData,
                 tip: pv.PolyData, ctx_rgba: np.ndarray, tip_rgba: np.ndarray,
                 campos: list, view_angle: float) -> np.ndarray:
    """Render one frame on a fresh plotter (VTK direct-scalar mappers cache,
    so the comet colours must be bound at add-time each frame)."""
    ctx["rgba"] = ctx_rgba
    tip["rgba"] = tip_rgba
    pl = pv.Plotter(off_screen=True, window_size=list(size))
    pl.set_background(BG)
    pl.enable_anti_aliasing("ssaa")
    pl.add_mesh(fin, scalars="p", cmap=PRESS_CMAP, clim=PRESS_CLIM,
                smooth_shading=True, specular=0.3, specular_power=20,
                ambient=0.30, diffuse=0.72, show_scalar_bar=False)
    # faint always-on filaments give the flow its skeleton
    pl.add_mesh(ctx, scalars="vmag", cmap=VEL_CMAP, clim=VEL_CLIM,
                line_width=1.6, render_lines_as_tubes=True, opacity=0.10,
                lighting=False, show_scalar_bar=False)
    pl.add_mesh(tip, scalars="vmag", cmap=VEL_CMAP, clim=VEL_CLIM,
                line_width=2.2, render_lines_as_tubes=True, opacity=0.11,
                lighting=False, show_scalar_bar=False)
    # bright travelling comets
    pl.add_mesh(ctx, scalars="rgba", rgb=True, line_width=2.8,
                render_lines_as_tubes=True, lighting=False, show_scalar_bar=False)
    pl.add_mesh(tip, scalars="rgba", rgb=True, line_width=3.6,
                render_lines_as_tubes=True, lighting=False, show_scalar_bar=False)
    pl.camera_position = campos
    pl.camera.view_angle = view_angle
    arr = pl.screenshot(return_img=True)
    pl.close()
    return arr


def encode_mp4(frame_glob: str, out: Path, fps: int) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
         "-i", frame_glob, "-c:v", "libx264", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
        check=True)


def encode_gif(frame_glob: str, out: Path, fps: int, width: int) -> None:
    pal = out.with_suffix(".pal.png")
    vf = f"scale={width}:-1:flags=lanczos"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
         "-i", frame_glob, "-vf", f"{vf},palettegen=stats_mode=full", str(pal)],
        check=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
         "-i", frame_glob, "-i", str(pal),
         "-lavfi", f"{vf} [x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3",
         "-loop", "0", str(out)], check=True)
    pal.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case", type=Path, help="path to the .foam stub file")
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--work", type=Path, default=None,
                    help="scratch dir for PNG frames (default: <out>/_frames)")
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--az0", type=float, default=100.0)
    ap.add_argument("--az1", type=float, default=158.0)
    ap.add_argument("--el0", type=float, default=18.0)
    ap.add_argument("--el1", type=float, default=26.0)
    ap.add_argument("--no-video", action="store_true",
                    help="only emit the still frame")
    ap.add_argument("--keep-frames", action="store_true",
                    help="do not delete the intermediate PNG frame dir")
    args = ap.parse_args()

    pv.OFF_SCREEN = True
    args.out.mkdir(parents=True, exist_ok=True)
    work = args.work or (args.out / "_frames")
    work.mkdir(parents=True, exist_ok=True)

    internal, fin = load_case(args.case)
    sign = suction_sign(fin)
    ctx_seeds, tip_seeds = make_seeds(fin.bounds, sign)
    ctx = integrate(internal, ctx_seeds, max_steps=1700, step=0.25)
    tip = integrate(internal, tip_seeds, max_steps=14000, step=0.10)
    ctx_rgb = annotate(ctx, 1)
    tip_rgb = annotate(tip, 2)

    fx0, fx1, fy0, fy1, _fz0, fz1 = fin.bounds
    chord, span = fx1 - fx0, fz1
    focal = (fx0 + 1.0 * chord, 0.5 * (fy0 + fy1), 0.47 * span)
    radius = 6.0 * chord
    size = (args.width, args.height)

    font = load_font(int(args.height * 0.028))
    az_mid = 0.5 * (args.az0 + args.az1)
    el_mid = 0.5 * (args.el0 + args.el1)

    # hero still: mid-orbit, lively comet phase, no title
    still = render_frame(
        size, fin, ctx, tip,
        comet_rgba(ctx, ctx_rgb, 0.4, trav=3.0, amp=0.9),
        comet_rgba(tip, tip_rgb, 0.4, trav=3.0, amp=1.0),
        camera_pose(focal, radius, az_mid, el_mid, sign), 26)
    Image.fromarray(still).save(args.out / "flow-still.png")
    print("wrote", args.out / "flow-still.png")

    if args.no_video:
        return

    nframes = int(round(args.seconds * args.fps))
    title_start = args.seconds - 3.0
    for k in range(nframes):
        t = k / nframes
        s = smoothstep(t)
        az = args.az0 + (args.az1 - args.az0) * s
        el = args.el0 + (args.el1 - args.el0) * s
        arr = render_frame(
            size, fin, ctx, tip,
            comet_rgba(ctx, ctx_rgb, t, trav=3.0, amp=0.9),
            comet_rgba(tip, tip_rgb, t, trav=3.0, amp=1.0),
            camera_pose(focal, radius, az, el, sign), 26)
        talpha = smoothstep((k / args.fps - title_start) / 0.6)
        arr = composite_title(arr, float(talpha), font)
        Image.fromarray(arr).save(work / f"f{k:04d}.png")
        if k % 30 == 0:
            print(f"frame {k}/{nframes}", flush=True)

    encode_mp4(str(work / "f%04d.png"), args.out / "flow-video.mp4", args.fps)
    print("wrote", args.out / "flow-video.mp4")

    # seamless looping preview: fixed camera, comets loop an integer count
    gwork = work / "gif"
    gwork.mkdir(parents=True, exist_ok=True)
    gframes = 56  # 56 / 16 fps = 3.5 s loop; trav=2 -> integer comet cycles
    gcam = camera_pose(focal, radius, az_mid, el_mid, sign)
    for k in range(gframes):
        tt = k / gframes
        arr = render_frame(
            (1280, 720), fin, ctx, tip,
            comet_rgba(ctx, ctx_rgb, tt, trav=2.0, amp=0.9),
            comet_rgba(tip, tip_rgb, tt, trav=2.0, amp=1.0), gcam, 26)
        Image.fromarray(arr).save(gwork / f"g{k:04d}.png")
    encode_gif(str(gwork / "g%04d.png"), args.out / "flow-preview.gif", 16, 1280)
    print("wrote", args.out / "flow-preview.gif")

    if not args.keep_frames:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    if os.environ.get("PYVISTA_OFF_SCREEN") is None:
        pv.OFF_SCREEN = True
    sys.exit(main())
