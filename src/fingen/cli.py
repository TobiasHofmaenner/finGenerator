"""Command-line interface: `fingen`."""

from __future__ import annotations

import argparse
from pathlib import Path

from fingen import __version__
from fingen.params import (
    FinParams,
    FoilParams,
    GrooveParams,
    GrooveSurface,
    OutlineParams,
    TabParams,
    TabSystem,
)

# CLI defaults derive from the dataclasses — duplicated literals drifted once
# (CLI sweep stayed 33 when the params default moved to 42) and shall not again.
_OUT = OutlineParams()
_FOIL = FoilParams()
_FIN = FinParams()
_TABS = TabParams()
_GROOVES = GrooveParams()
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
    sub.add_argument("--tab-x", type=float, default=_TABS.x_offset, dest="tab_x",
                     help="slide the tab set along the base, mm (+ = toward TE)")
    sub.add_argument("--tab-y", type=float, default=_TABS.y_offset, dest="tab_y",
                     help="shift tabs across the thickness, mm (flat fins anchor "
                          "flush with the flat side and accept only >= 0)")
    sub.add_argument("--grooves", type=int, default=_GROOVES.count, dest="grooves",
                     help="number of spanwise thinning grooves, 0 = none "
                          "([Els22]: +11%% L/D at high incidence, adds tip flex)")
    sub.add_argument("--groove-length", type=float, default=_GROOVES.length,
                     dest="groove_length", help="chordwise groove extent from LE, mm")
    sub.add_argument("--groove-pitch", type=float, default=_GROOVES.pitch,
                     dest="groove_pitch", help="spanwise center spacing, mm")
    sub.add_argument("--groove-width", type=float, default=_GROOVES.width,
                     dest="groove_width", help="channel width, mm (<= pitch)")
    sub.add_argument("--groove-depth", type=float, default=_GROOVES.depth_ratio,
                     dest="groove_depth",
                     help="fraction of local thickness removed at channel center")
    sub.add_argument("--groove-start", type=float, default=_GROOVES.span_start,
                     dest="groove_start",
                     help="first groove center as fraction of depth")
    sub.add_argument("--groove-surface", choices=["outer", "both"],
                     default=_GROOVES.surface.value, dest="groove_surface",
                     help="outer face only (G1) or both faces (G2, not on flat)")


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
                       tab_depth=args.tab_depth, x_offset=args.tab_x,
                       y_offset=args.tab_y),
        grooves=GrooveParams(count=args.grooves, length=args.groove_length,
                             pitch=args.groove_pitch, width=args.groove_width,
                             depth_ratio=args.groove_depth,
                             span_start=args.groove_start,
                             surface=GrooveSurface(args.groove_surface)),
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
    make.add_argument("--hand", choices=["right", "left", "both"], default="right",
                      help="blade handedness: side fins are chiral (flat face "
                           "toward the board) — 'both' writes <stem>-R and "
                           "<stem>-L files for a full set")
    make.add_argument("--halves", action="store_true",
                      help="symmetric fins only: export the blade as two "
                           "flat-faced halves (<stem>-half-A/-B, a mirror "
                           "pair) to print flat and glue at the midplane")

    preview = sub.add_parser("preview", help="render a PNG preview of a fin blade")
    preview.add_argument("output", type=Path, nargs="?", default=Path("out/fin.png"))
    _add_geometry_args(preview)
    preview.add_argument("--solid", action="store_true",
                         help="include the lofted-solid 3D panel (slower; off "
                              "by default — the webapp has a live 3D view)")

    coupon = sub.add_parser("coupon", help="export a tab test-fit coupon (STEP/STL): "
                                           "a minutes-long print to dial --tab-fit "
                                           "against your actual boxes")
    coupon.add_argument("output", type=Path, nargs="?", default=Path("out/coupon.step"))
    coupon.add_argument("--tabs", choices=["dual", "single", "click"], required=True)
    coupon.add_argument("--tab-fit", type=float, default=_TABS.fit_offset, dest="tab_fit")
    coupon.add_argument("--tab-depth", type=float, default=None, dest="tab_depth")

    opt = sub.add_parser("optimize", help="search the design space for the fin "
                                          "closest to a rider's spider targets; "
                                          "writes a result card PNG, a result JSON "
                                          "and STEP exports of the winner")
    opt.add_argument("--weight", type=float, required=True, dest="weight",
                     help="rider weight in kg")
    opt.add_argument("--skill", choices=["cruiser", "intermediate", "advanced", "pro"],
                     default="intermediate", help="rider skill (sets turn intensity "
                     "and default speed)")
    opt.add_argument("--config", choices=["single", "twin", "thruster", "quad",
                                          "two_plus_one"],
                     default="thruster", help="fin configuration (sets the blade "
                     "family and interference environment)")
    opt.add_argument("--material", default="pet-cf",
                     help="print material card (default: pet-cf)")
    opt.add_argument("--speed", type=float, default=None,
                     help="design riding speed in m/s (default: from skill)")
    opt.add_argument("--budget", type=int, default=4000, dest="budget",
                     help="evaluation budget for the CMA-ES search")
    opt.add_argument("--seed", type=int, default=0, help="RNG seed (deterministic)")
    opt.add_argument("--out", type=Path, default=Path("out/optimize"), dest="out",
                     help="output directory for the card, JSON and STEP exports")
    opt.add_argument("--hand", choices=["right", "left", "both"], default="both",
                     help="STEP handedness for side-fin configs (default: both, a "
                          "full set); ignored for the single symmetric center fin")
    return parser


_SKILL_MAP = {"cruiser": "CRUISER", "intermediate": "INTERMEDIATE",
              "advanced": "ADVANCED", "pro": "PRO"}
_CONFIG_MAP = {"single": "SINGLE", "twin": "TWIN", "thruster": "THRUSTER",
               "quad": "QUAD", "two_plus_one": "TWO_PLUS_ONE"}


def _run_optimize(args: argparse.Namespace) -> int:
    from fingen.export import mirror_hand, to_step
    from fingen.loft import fin_solid
    from fingen.optimize import (
        RiderSpec,
        optimize,
        render_result_card,
        write_result_json,
    )
    from fingen.params import FinConfig
    from fingen.sizing import Skill

    config = FinConfig[_CONFIG_MAP[args.config]]
    rider = RiderSpec(weight_kg=args.weight, skill=Skill[_SKILL_MAP[args.skill]],
                      speed_ms=args.speed, config=config, material=args.material)
    print(f"optimizing for {args.weight:.0f} kg {args.skill} · {args.config} · "
          f"{args.material} · {rider.speed:.1f} m/s (budget {args.budget}, "
          f"seed {args.seed})", flush=True)
    result = optimize(rider, budget_evals=args.budget, seed=args.seed)
    r = result.result
    print(f"done: {result.n_evals} evals · objective {r.objective:.3f} "
          f"({'feasible' if r.feasible else 'INFEASIBLE'})", flush=True)
    if not r.feasible:
        for issue in r.issues:
            print(f"  constraint: {issue}", flush=True)

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    card = render_result_card(result, out / "result-card.png")
    js = write_result_json(result, out / "result.json")
    print(f"wrote {card}\nwrote {js}", flush=True)

    # STEP exports of the winning blade. Side-fin configs are chiral (both
    # hands make a set); the single symmetric center fin is one blade.
    part = fin_solid(result.fin)
    if config is FinConfig.SINGLE:
        outputs = [(part, "")]
    elif args.hand == "both":
        outputs = [(part, "-R"), (mirror_hand(part), "-L")]
    elif args.hand == "left":
        outputs = [(mirror_hand(part), "")]
    else:
        outputs = [(part, "")]
    for solid, suffix in outputs:
        written = to_step(solid, out / f"fin{suffix}.step")
        print(f"wrote {written} ({written.stat().st_size} bytes)", flush=True)
    return 0


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

    if args.command == "optimize":
        return _run_optimize(args)

    fin = _fin_from_args(args)

    if args.command == "preview":
        from fingen.preview import render_preview

        written = render_preview(fin, args.output, show_solid=args.solid)
        print(f"wrote {written}")
        return 0

    from fingen.check import check_solid
    from fingen.export import mirror_hand, split_halves, to_step, to_stl
    from fingen.loft import fin_solid
    from fingen.params import FoilFamily, GrooveSurface

    if args.halves:
        if fin.foil.family is not FoilFamily.SYMMETRIC:
            print("--halves needs a symmetric section: flat-inside fins already "
                  "print flat whole, and a cambered midplane is not a flat face")
            return 1
        # The halves promise (a flat-faced MIRROR PAIR) requires y-symmetry
        # of the whole blade: y-shifted tabs leave sub-print-layer sliver
        # flaps on one half, and outer-face grooves put all the grooves in
        # one half — both break the pair.
        if fin.tabs.y_offset != 0.0:
            print("--halves needs tab y_offset 0: a y-shifted tab leaves "
                  "paper-thin slivers on one half at the midplane cut")
            return 1
        if fin.grooves.count and fin.grooves.surface is not GrooveSurface.BOTH:
            print("--halves with grooves needs --groove-surface both: outer-"
                  "face grooves make the halves asymmetric, not a mirror pair")
            return 1
        if args.hand != "right":
            print("--halves is hand-independent (the blade is y-symmetric); "
                  "drop --hand")
            return 1

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
    if args.halves:
        # A mirror PAIR: a physical flip is a rotation and cannot turn one
        # half into its mate — print one of each, glue at the midplane.
        half_a, half_b = split_halves(part)
        outputs = [(half_a, "-half-A"), (half_b, "-half-B")]
    elif args.hand == "both":
        outputs = [(part, "-R"), (mirror_hand(part), "-L")]
    elif args.hand == "left":
        outputs = [(mirror_hand(part), "")]
    else:
        outputs = [(part, "")]
    for solid, suffix in outputs:
        out = (args.output if not suffix else
               args.output.with_stem(args.output.stem + suffix))
        written = writer(solid, out)
        print(f"wrote {written} ({written.stat().st_size} bytes)")
    return 0
