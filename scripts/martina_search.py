"""Long multistart search for Martina's thruster set (46 kg, advanced).

Usage: martina_search.py [budget] [seeds] [material]   (default paht-cf)

Deliberately over-budgeted: many independent CMA restarts at a large per-run
budget, keeping the best feasible set. The tier-0 objective is cheap, so the
only cost is wall time — and a deeper search buys a genuinely better-converged
blade AND center. Writes the winner plus a per-seed ledger for the record.
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

BUDGET = int(sys.argv[1]) if len(sys.argv) > 1 else 60_000
_N_SEEDS = int(sys.argv[2]) if len(sys.argv) > 2 else 12
# MATERIAL IS PART OF THE DESIGN, not a post-hoc substitution. It moves the
# allowable AND the modulus in opposite directions — pet-cf is 7 % stiffer but
# its design allowable is 7 % lower than paht-cf — so the search lands somewhere
# genuinely different, and the results must not share a directory.
MATERIAL = sys.argv[3] if len(sys.argv) > 3 else "paht-cf"
# Seed OFFSET so the run can be split across parallel streams: each optimize()
# call already saturates ~popsize workers, which is half of a 20-core box, so
# two disjoint seed ranges running side by side halve the wall clock without
# oversubscribing.
OFFSET = int(sys.argv[4]) if len(sys.argv) > 4 else 0
# argv[5]: over-finned ceiling as a multiple of area_min. "inf" removes it.
# Every seed of the previous run sat EXACTLY on the default 2.0 ceiling, so
# whether that constant or the objective is setting fin size is now testable.
_AF = sys.argv[5] if len(sys.argv) > 5 else None
AREA_FACTOR = None if _AF is None else float(_AF)
_TAG = "" if AREA_FACTOR is None else (
    "-nocap" if float("inf") == AREA_FACTOR else f"-af{AREA_FACTOR:g}")
SEEDS = list(range(OFFSET, OFFSET + _N_SEEDS))
OUT = Path(f"out/martina/46kg-{MATERIAL}{_TAG}")
NAME = f"fin-martina-46kg-advanced-thruster-{MATERIAL}"

RIDER = RiderSpec(
    weight_kg=46.0,
    skill=Skill.ADVANCED,
    config=FinConfig.THRUSTER,
    material=MATERIAL,
    tabs=TabSystem.CLICK_TAB,   # her board is FCS II: base >= 104 mm to mount
    # Real structural headroom. At the default 1.0 the optimizer thins the blade
    # until the roll-augmented gate binds EXACTLY — zero margin — and the
    # PAHT-CF card is an approximation good to ~±20-30% on modulus, so "SF 1.0"
    # there is not really 1.0. This fin gets surfed; buy the margin.
    stress_sf_min=1.3,
    # Cap the lift the blade sheds to flex. Without it the search buys spider
    # points with floppiness (washout multiplies drive/hold) right up to the
    # strength wall — the opposite of the "locked-in" she asked for.
    washout_max=0.03,
    # Tab REPORTED, not gated. The analytic model is too crude to design
    # against (it cannot see the junction, and S_tab is fixed by the box, so
    # the search can only satisfy it by wrecking the blade). Tier-1 adjudicates:
    # CFD pressure -> FEM fixed at the box interface. Task #24.
    tab_sf_min=None,
    area_max_factor=AREA_FACTOR,
    spider_targets={
        "speed": 0.85,        # her explicit ask: more speed than the Palmbay S
        "drive": 0.85,        # "locked-in and drivey"
        "hold": 0.70,         # punchy 1-2 m reef, must not spin out
        "release": 0.45,      # snaps/airs welcome but secondary
        "pivot": 0.35,
        "forgiveness": 0.30,  # advanced, wants performance not safety
        "stability": 0.50,
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
            "n_evals": r.n_evals,
            "wall_s": round(time.time() - t1, 1),
        }
        # KEEP EVERY SEED. The best-so-far checkpoint answers "what should I
        # print"; it cannot answer "how many independent runs agreed", which is
        # the only evidence we have that a winner is a real optimum rather than
        # one basin the search happened to fall into. Cheap to store, impossible
        # to recover later.
        seeds_dir = OUT / "seeds"
        seeds_dir.mkdir(parents=True, exist_ok=True)
        write_result_json(r, seeds_dir / f"seed-{seed:03d}.json")
        ledger.append(row)
        print(f"seed {seed:2d}  set_obj {set_obj:.5f}  feasible {row['feasible']}  "
              f"side {row['side_area_mm2']:.0f}  center {row['center_area_mm2']:.0f}  "
              f"{row['wall_s']:.0f}s", flush=True)
        if row["feasible"] and (best is None or set_obj < best[0]):
            best = (set_obj, r)
            # CHECKPOINT the best-so-far after every seed. Writing only at the
            # end means an interrupted run loses everything — which it did.
            write_result_json(r, OUT / f"{NAME}.json")
            print(f"          ^ new best, checkpointed (seed {seed})", flush=True)
        (OUT / f"{NAME}-ledger-{OFFSET:03d}.json").write_text(
            json.dumps({"budget": BUDGET, "seeds": SEEDS,
                        "complete": len(ledger) == len(SEEDS),
                        "runs": ledger}, indent=2) + "\n")

    if best is None:
        raise SystemExit("no feasible set found")
    print(f"\nBEST set_objective {best[0]:.5f} (seed {best[1].seed}) "
          f"in {time.time() - t0:.0f}s total")


if __name__ == "__main__":
    main()
