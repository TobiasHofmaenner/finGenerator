"""Multistart search for a CRUISER/beginner thruster set, any rider weight.

Usage: cruiser_search.py <weight_kg> [budget] [seeds] [tabs]
       tabs: dual (FCS1, default) | click (FCS II) | single | none

WHAT MAKES THIS RIDER DIFFERENT. Every previous search here has been blade-
limited: the optimizer thins the section until the bending gate binds. At 95 kg
on FCS II it is TAB-limited instead, and the two want opposite things.

    95 kg CRUISER, dominant side blade, tier-0 tab SF:
      geometry            CLICK_TAB (FCS II)   DUAL_TAB (FCS1)
      140 x 115  t/c .09        0.91                0.47
      125 x 110  t/c .085       1.01                0.52
      110 x 105  t/c .08        1.15                0.59
       90 x  95  t/c .08        1.40                0.72

FCS1 IS THE HARDER MOUNT, BY A FACTOR OF TWO. Two 20 mm tabs give S_tab =
252 mm3 against CLICK_TAB's 45+33 mm and 492 mm3. Tab stress scales as 1/S, so
every FCS1 number above is roughly double its FCS II twin, and NO geometry in
the practical range reaches tier-0 SF 1.0 — not even a 90 x 95 mm blade.

The blade has 3-5x margin while the tab sits at unity, and DEEPER blades make it
worse: S_tab is fixed by the box standard (sizing._TAB_NECK_GEOM), so a fin
cannot strengthen its own mount, and every mm of depth adds root moment the tab
must carry through a section it does not control. The search therefore has to
buy character with PLANFORM at modest depth rather than with span.

THE TAB GATE IS OFF, AND THAT IS A DELIBERATE DEFERRAL, NOT A DISMISSAL. Gated
at 1.0 this search returns nothing at all. The tier-0 tab model is too crude to
be the last word at this margin — KT_TAB = 2.5 is a chart value that tier-1
backed out at an effective 1.5-2.1, so the reported numbers carry roughly 1.4x
of unbooked conservatism, which lifts the smallest blades to about unity and
leaves everything else short.

So the set below is produced with the tab REPORTED, and tier-1 is not optional
here the way it was for Martina. There the FEM confirmed a benign junction; this
rider sits outside that validated envelope (docs/FEM-BENCH.md: the 146 um plastic
zone was measured at 46 kg on the LARGEST tab section, and r_p scales as sigma^2).
The honest expectation is MARGINAL, and the FEM may well say no. Read the
tab_sf in the output as an open question, not a pass.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from fingen.optimize import RiderSpec, optimize, result_to_dict, write_result_json
from fingen.outline import metrics
from fingen.params import FinConfig, TabSystem
from fingen.sizing import Skill

WEIGHT = float(sys.argv[1]) if len(sys.argv) > 1 else 95.0
BUDGET = int(sys.argv[2]) if len(sys.argv) > 2 else 25_000
SEEDS = list(range(int(sys.argv[3]) if len(sys.argv) > 3 else 8))
_TABS = {"dual": TabSystem.DUAL_TAB, "click": TabSystem.CLICK_TAB,
         "single": TabSystem.SINGLE_TAB, "none": TabSystem.NONE}
TABS = _TABS[sys.argv[4]] if len(sys.argv) > 4 else TabSystem.DUAL_TAB
_SUFFIX = {"dual_tab": "fcs1", "click_tab": "fcs2",
           "single_tab": "single", "none": "glasson"}[TABS.value]
OUT = Path(f"out/toby/{WEIGHT:.0f}kg")
NAME = f"fin-toby-{WEIGHT:.0f}kg-beginner-thruster-{_SUFFIX}"

RIDER = RiderSpec(
    weight_kg=WEIGHT,
    # No BEGINNER level exists; CRUISER (30 deg design bank, relaxed arcs) is the
    # honest mapping. It also matters structurally: INTERMEDIATE's 40 deg raises
    # the peak load from 200 N to 290 N and takes the tab to SF 0.70 - i.e. this
    # rider outgrows a printed FCS II tab before they outgrow the blade.
    skill=Skill.CRUISER,
    config=FinConfig.THRUSTER,
    material="paht-cf",
    tabs=TABS,
    # Blade margin. Cheap here - the blade is nowhere near binding - so take it.
    stress_sf_min=1.3,
    # A beginner should not be riding a blade that sheds its lift to flex: the
    # board's response would change with how hard they lean, which is precisely
    # the feedback they are trying to learn.
    washout_max=0.02,
    tab_sf_min=None,  # REPORTED, not gated — see the module docstring.
    spider_targets={
        "forgiveness": 0.85,  # the defining beginner need: predictable, hard to spin out
        "stability": 0.80,    # tracks straight, rewards standing still
        "hold": 0.65,         # heavy rider, must not let go under a clumsy load
        "drive": 0.55,        # enough push to trim, not so much it demands input
        "speed": 0.35,        # deliberately low - drag is a beginner's friend
        "pivot": 0.25,        # tracking beats turning at this stage
        "release": 0.15,      # a loose tail is the last thing they want
    },
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ledger = []
    best = None
    t0 = time.time()
    for seed in SEEDS:
        t1 = time.time()
        r = optimize(RIDER, budget_evals=BUDGET, seed=seed)
        d = result_to_dict(r)
        set_obj = d["set"]["objective"]
        row = {
            "seed": seed,
            "set_objective": set_obj,
            "side_objective": r.result.objective,
            "center_objective": r.center_result.objective if r.center_result else None,
            "feasible": d["set"]["feasible"],
            "side_area_mm2": metrics(r.fin.outline).area,
            "center_area_mm2": (metrics(r.center.outline).area if r.center else None),
            "side_depth_mm": r.fin.outline.depth,
            "n_evals": r.n_evals,
            "wall_s": round(time.time() - t1, 1),
        }
        ledger.append(row)
        print(f"seed {seed:2d}  set_obj {set_obj:.5f}  feasible {row['feasible']}  "
              f"side {row['side_area_mm2']:.0f} mm2 @ {row['side_depth_mm']:.0f} mm  "
              f"{row['wall_s']:.0f}s", flush=True)
        if row["feasible"] and (best is None or set_obj < best[0]):
            best = (set_obj, r)
            write_result_json(r, OUT / f"{NAME}.json")
            print(f"          ^ new best, checkpointed (seed {seed})", flush=True)
        (OUT / f"{NAME}-ledger.json").write_text(
            json.dumps({"budget": BUDGET, "seeds": SEEDS,
                        "complete": len(ledger) == len(SEEDS),
                        "runs": ledger}, indent=2) + "\n")

    if best is None:
        raise SystemExit("no feasible set found")
    print(f"\nBEST set_objective {best[0]:.5f} (seed {best[1].seed}) "
          f"in {time.time() - t0:.0f}s total")


if __name__ == "__main__":
    main()
