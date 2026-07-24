"""Command-line interface: `fingen`."""

from __future__ import annotations

import argparse
from pathlib import Path

from fingen import __version__


def _add_geometry_args(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--family", choices=["symmetric", "flat", "cambered"],
                     default="flat", help="foil family (default: flat side fin)")
    sub.add_argument("--depth", type=float, default=115.0)
    sub.add_argument("--base", type=float, default=110.0)
    sub.add_argument("--sweep", type=float, default=33.0)
    sub.add_argument("--tip-ratio", type=float, default=0.35, dest="tip_ratio")
    sub.add_argument("--le-fullness", type=float, default=0.6, dest="le_fullness")
    sub.add_argument("--te-fullness", type=float, default=0.6, dest="te_fullness")
    sub.add_argument("--thickness", type=float, default=0.09,
                     help="section thickness ratio t/c")
    sub.add_argument("--camber", type=float, default=0.0)
    sub.add_argument("--camber-pos", type=float, default=0.4, dest="camber_pos")
    sub.add_argument("--te-thickness", type=float, default=0.7, dest="te_thickness")
    sub.add_argument("--tip-factor", type=float, default=0.85, dest="tip_factor")


def _fin_from_args(args: argparse.Namespace):
    from fingen.params import FinParams, FoilFamily, FoilParams, OutlineParams

    family = {"symmetric": FoilFamily.SYMMETRIC, "flat": FoilFamily.FLAT_INSIDE,
              "cambered": FoilFamily.CAMBERED}[args.family]
    return FinParams(
        outline=OutlineParams(depth=args.depth, base=args.base, sweep=args.sweep,
                              tip_chord_ratio=args.tip_ratio,
                              le_fullness=args.le_fullness,
                              te_fullness=args.te_fullness),
        foil=FoilParams(family=family, thickness_ratio=args.thickness,
                        camber_ratio=args.camber, camber_position=args.camber_pos,
                        te_thickness=args.te_thickness),
        thickness_tip_factor=args.tip_factor,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fingen", description="Parametric surfboard fin generator"
    )
    parser.add_argument("--version", action="version", version=f"fingen {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    make = sub.add_parser("make", help="generate a fin blade and export STEP/STL")
    make.add_argument("output", type=Path, nargs="?", default=Path("out/fin.step"),
                      help="output file; suffix selects STEP or STL")
    _add_geometry_args(make)
    make.add_argument("--force", action="store_true",
                      help="export even if the geometry check fails")

    preview = sub.add_parser("preview", help="render a PNG preview of a fin blade")
    preview.add_argument("output", type=Path, nargs="?", default=Path("out/fin.png"))
    _add_geometry_args(preview)

    args = parser.parse_args(argv)

    # Deferred imports: build123d/OCCT takes seconds to load, keep --help fast.
    fin = _fin_from_args(args)

    if args.command == "preview":
        from fingen.preview import render_preview

        written = render_preview(fin, args.output)
        print(f"wrote {written}")
        return 0

    from fingen.check import check_solid
    from fingen.export import to_step, to_stl
    from fingen.loft import fin_solid

    part = fin_solid(fin)
    report = check_solid(part, fin)
    print(f"planform area {report.area:.0f} mm² | aspect ratio {report.aspect_ratio:.2f} "
          f"| volume {report.volume / 1000.0:.1f} cm³")
    if not report.ok:
        for issue in report.issues:
            print(f"GEOMETRY CHECK FAILED: {issue}")
        if not args.force:
            return 1
        print("exporting anyway (--force)")

    writer = to_stl if args.output.suffix.lower() == ".stl" else to_step
    written = writer(part, args.output)
    print(f"wrote {written} ({written.stat().st_size} bytes)")
    return 0
