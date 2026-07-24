"""Command-line interface: `fingen`."""

from __future__ import annotations

import argparse
from pathlib import Path

from fingen import __version__
from fingen.params import FinParams, FoilParams, OutlineParams, TabParams, TabSystem

# CLI defaults derive from the dataclasses — duplicated literals drifted once
# (CLI sweep stayed 33 when the params default moved to 42) and shall not again.
_OUT = OutlineParams()
_FOIL = FoilParams()
_FIN = FinParams()
_TABS = TabParams()
_TAB_MAP = {"none": TabSystem.NONE, "dual": TabSystem.DUAL_TAB,
            "single": TabSystem.SINGLE_TAB, "click": TabSystem.CLICK_TAB}


def _add_geometry_args(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--family", choices=["symmetric", "flat", "cambered"],
                     default="flat", help="foil family (default: flat side fin)")
    sub.add_argument("--depth", type=float, default=_OUT.depth)
    sub.add_argument("--base", type=float, default=_OUT.base)
    sub.add_argument("--sweep", type=float, default=_OUT.sweep)
    sub.add_argument("--tip-width", type=float, default=_OUT.tip_width_ratio,
                     dest="tip_width", help="tip lobe width as fraction of base")
    sub.add_argument("--le-fullness", type=float, default=_OUT.le_fullness,
                     dest="le_fullness")
    sub.add_argument("--te-shape", type=float, default=_OUT.te_shape, dest="te_shape",
                     help="-1 concave cutaway .. 0 straight .. +1 convex keel")
    sub.add_argument("--thickness", type=float, default=_FOIL.thickness_ratio,
                     help="section thickness ratio t/c")
    sub.add_argument("--camber", type=float, default=_FOIL.camber_ratio)
    sub.add_argument("--camber-pos", type=float, default=_FOIL.camber_position,
                     dest="camber_pos")
    sub.add_argument("--te-thickness", type=float, default=_FOIL.te_thickness,
                     dest="te_thickness")
    sub.add_argument("--tip-factor", type=float, default=_FIN.thickness_tip_factor,
                     dest="tip_factor")
    sub.add_argument("--tabs", choices=["none", "dual", "single", "click"],
                     default="none",
                     help="mounting tabs: dual (FCS-compatible), single "
                          "(Futures-compatible), click (FCS II-compatible); "
                          "see docs/TAB-SYSTEMS.md")
    sub.add_argument("--tab-fit", type=float, default=_TABS.fit_offset, dest="tab_fit",
                     help="tab thickness offset in mm; calibrate with `fingen coupon`")
    sub.add_argument("--tab-depth", type=float, default=None, dest="tab_depth",
                     help="override tab insertion depth in mm (default: system value)")


def _fin_from_args(args: argparse.Namespace):
    from fingen.params import FoilFamily

    family = {"symmetric": FoilFamily.SYMMETRIC, "flat": FoilFamily.FLAT_INSIDE,
              "cambered": FoilFamily.CAMBERED}[args.family]
    if args.camber > 0.0 and family is not FoilFamily.CAMBERED:
        print(f"warning: --camber {args.camber} is ignored for --family {args.family} "
              "(only 'cambered' uses it)")
    return FinParams(
        outline=OutlineParams(depth=args.depth, base=args.base, sweep=args.sweep,
                              tip_width_ratio=args.tip_width,
                              le_fullness=args.le_fullness,
                              te_shape=args.te_shape),
        foil=FoilParams(family=family, thickness_ratio=args.thickness,
                        camber_ratio=args.camber, camber_position=args.camber_pos,
                        te_thickness=args.te_thickness),
        thickness_tip_factor=args.tip_factor,
        tabs=TabParams(system=_TAB_MAP[args.tabs], fit_offset=args.tab_fit,
                       tab_depth=args.tab_depth),
    )


def _build_parser() -> argparse.ArgumentParser:
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

    coupon = sub.add_parser("coupon", help="export a tab test-fit coupon (STEP/STL): "
                                           "a minutes-long print to dial --tab-fit "
                                           "against your actual boxes")
    coupon.add_argument("output", type=Path, nargs="?", default=Path("out/coupon.step"))
    coupon.add_argument("--tabs", choices=["dual", "single", "click"], required=True)
    coupon.add_argument("--tab-fit", type=float, default=_TABS.fit_offset, dest="tab_fit")
    coupon.add_argument("--tab-depth", type=float, default=None, dest="tab_depth")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "coupon":
        from fingen.export import to_step, to_stl
        from fingen.tabs import coupon_solid

        part = coupon_solid(TabParams(system=_TAB_MAP[args.tabs],
                                      fit_offset=args.tab_fit,
                                      tab_depth=args.tab_depth))
        writer = to_stl if args.output.suffix.lower() == ".stl" else to_step
        written = writer(part, args.output)
        print(f"wrote {written} ({written.stat().st_size} bytes) — trial-fit and "
              "adjust --tab-fit in 0.1 mm steps")
        return 0

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
