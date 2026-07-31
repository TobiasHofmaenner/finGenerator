"""Export Martina's thruster set as printable STLs with FCS II tabs.

Reads the optimizer result, attaches the rider's tab system (CLICK_TAB) to each
designed blade, and writes:

    side-right.stl     the designed side blade, right hand (as lofted)
    side-left.stl      its mirror — a set needs one of each hand
    center-half-a.stl  the symmetric centre, split at its midplane …
    center-half-b.stl  … so each half prints flat-side-down; glue after

PRINT ORIENTATION (the biggest strength lever — Z strength is ~half of XY):
every part here is meant to lie FLAT ON ITS FLAT FACE, so the layer planes run
parallel to the blade faces. The fin is a cantilever loaded perpendicular to
its own plane, which puts peak tension SPANWISE along those faces — in-plane
for the layers. Standing a blade upright would lay layer lines across the span
and put that tension across layer boundaries: the classic snapped-fin build.
The side blades are FLAT_INSIDE and already have a flat face; the SYMMETRIC
centre has none, hence the midplane split.

Tab thickness carries TabParams.fit_offset (default -0.2 mm, i.e. printed
undersize: it errs LOOSE rather than tight, which the box's cam screw takes up
and sanding cannot undo the other way).

Every blade is verified with check_solid + check_anchor before writing — an STL
that looks right but cannot mount is the failure mode this guards.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

from fingen.check import check_solid
from fingen.export import mirror_hand, split_halves, to_stl
from fingen.loft import fin_solid
from fingen.optimize import fin_from_dict
from fingen.outline import metrics
from fingen.params import (
    DEFAULT_SETTINGS,
    FinConfig,
    FoilFamily,
    TabParams,
    TabSystem,
)
from fingen.sizing import Skill, anchor, check_anchor

RESULT = Path(sys.argv[1] if len(sys.argv) > 1
              else "out/martina/46kg-paht-cf/"
                   "fin-martina-46kg-advanced-thruster-paht-cf.json")
# Both derived from the result rather than hardcoded: the STLs belong beside the
# design they came from, and the tab system is the RIDER's board, not a constant.
OUT = RESULT.parent / "stl"
TABS = TabSystem(json.loads(RESULT.read_text())["rider"]["tabs"])
FIT_OFFSET = -0.2                   # mm on tab thickness: undersize, sand to fit
# The FLAT_INSIDE anchor puts the inner tab face ON the print-bed plane, so the
# inner retention indent becomes a pocket with an unsupported bridge — the ONLY
# overhang in an otherwise support-free part. docs/TAB-SYSTEMS.md says printed
# indents deform after a few insert cycles anyway and the cam screw is the real
# retention, so delete them and print with zero supports.
INDENT_DEPTH = 0.0


def main() -> None:
    result = json.loads(RESULT.read_text())
    rider = result["rider"]
    tabs = TabParams(system=TABS, fit_offset=FIT_OFFSET,
                     click_indent_depth=INDENT_DEPTH)

    # REBUILD THE SHEET THE SEARCH ACTUALLY USED. Constructing a default one
    # here refuses designs the optimizer legitimately produced: a run with the
    # over-finned ceiling lifted (rider.area_max_factor) was rejected by this
    # gate at 7146 mm2 against a 6870 mm2 ceiling the search had been told to
    # ignore. Older result files predate the field, so absent means default.
    sheet_kw = {}
    if rider.get("area_max_factor") is not None:
        sheet_kw["area_max_factor"] = float(rider["area_max_factor"])

    blades = [("side", result["fin"], "dominant")]
    if result.get("center_fin"):
        # The CENTRE is sized against its own, smaller share — building one
        # dominant sheet for both blades over-states the centre's corridor and
        # its design load by ~33 %.
        blades.append(("center", result["center_fin"], "center"))

    OUT.mkdir(parents=True, exist_ok=True)
    for slot, fin_dict, member in blades:
        sheet = anchor(rider["weight_kg"], Skill[rider["skill"]],
                       design_speed=rider["speed_ms"],
                       config=FinConfig(rider["config"]),
                       material=rider["material"], tabs=TABS,
                       member=member, **sheet_kw)
        fin = dataclasses.replace(fin_from_dict(fin_dict), tabs=tabs)
        issues = check_anchor(fin, sheet)
        m = metrics(fin.outline)
        print(f"\n{slot}: base {fin.outline.base:.1f} mm | depth "
              f"{fin.outline.depth:.1f} mm | area {m.area:.0f} mm^2 | "
              f"t/c {fin.foil.thickness_ratio:.3f}")
        if issues:
            raise SystemExit(f"  REFUSING to export {slot}: {issues}")
        print("  anchor: OK (mountable)")

        part = fin_solid(fin, DEFAULT_SETTINGS)
        # Validate the WHOLE solid before any splitting: check_solid's volume and
        # bbox invariants are defined against the complete blade, so running it
        # on a half reports false failures.
        report = check_solid(part, fin, DEFAULT_SETTINGS)
        if not report.ok:
            raise SystemExit(f"  REFUSING to export {slot}: check_solid {report.issues}")
        print("  check_solid: OK")
        bb = part.bounding_box()
        print(f"  solid: z {bb.min.Z:.1f}..{bb.max.Z:.1f} mm "
              f"(tabs {abs(bb.min.Z):.1f} mm below the base plane)")

        if slot == "center":
            # The centre is SYMMETRIC — no flat face to lie on. Split it at the
            # y=0 midplane so each half prints flat-side-down with the layer
            # planes parallel to the faces (spanwise bending tension stays
            # in-plane). The bond plane lands on the NEUTRAL AXIS, where bending
            # stress is zero and the joint carries only shear.
            if fin.foil.family is not FoilFamily.SYMMETRIC:
                raise SystemExit(
                    f"refusing to split a {fin.foil.family.value} centre: only a "
                    "symmetric section has a FLAT midplane to print on")
            upper, lower = split_halves(part)
            for half, half_part in (("a", upper), ("b", lower)):
                p = to_stl(half_part, OUT / f"center-half-{half}.stl")
                print(f"  -> {p} ({p.stat().st_size/1024:.0f} KB)")
        else:
            # A thruster needs one of each hand; the left blade is the mirror.
            pr = to_stl(part, OUT / "side-right.stl")
            pl = to_stl(mirror_hand(part), OUT / "side-left.stl")
            for p in (pr, pl):
                print(f"  -> {p} ({p.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
