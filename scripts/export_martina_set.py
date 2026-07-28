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
              else "out/fin-martina-46kg-advanced-thruster.json")
OUT = Path("out/martina/stl")
TABS = TabSystem.CLICK_TAB          # FCS II
FIT_OFFSET = -0.2                   # mm on tab thickness: undersize, sand to fit


def main() -> None:
    result = json.loads(RESULT.read_text())
    rider = result["rider"]
    tabs = TabParams(system=TABS, fit_offset=FIT_OFFSET)

    sheet = anchor(rider["weight_kg"], Skill[rider["skill"]],
                   design_speed=rider["speed_ms"],
                   config=FinConfig(rider["config"]), material=rider["material"],
                   tabs=TABS)

    blades = [("side", result["fin"])]
    if result.get("center_fin"):
        blades.append(("center", result["center_fin"]))

    OUT.mkdir(parents=True, exist_ok=True)
    for slot, fin_dict in blades:
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
