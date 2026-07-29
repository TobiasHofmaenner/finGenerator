"""Long multistart search for Martina's thruster set (46 kg, advanced).

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
SEEDS = list(range(int(sys.argv[2]) if len(sys.argv) > 2 else 12))
OUT = Path("out")

RIDER = RiderSpec(
    weight_kg=46.0,
    skill=Skill.ADVANCED,
    config=FinConfig.THRUSTER,
    material="paht-cf",
    tabs=TabSystem.CLICK_TAB,   # her board is FCS II: base >= 104 mm to mount
    # Real structural headroom. At the default 1.0 the optimizer thins the blade
    # until the roll-augmented gate binds EXACTLY — zero margin — and the
    # PAHT-CF card is an approximation good to ~±20-30% on modulus, so "SF 1.0"
    # there is not really 1.0. This fin gets surfed; buy the margin.
    stress_sf_min=1.3,
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
    OUT.mkdir(exist_ok=True)
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
        ledger.append(row)
        print(f"seed {seed:2d}  set_obj {set_obj:.5f}  feasible {row['feasible']}  "
              f"side {row['side_area_mm2']:.0f}  center {row['center_area_mm2']:.0f}  "
              f"{row['wall_s']:.0f}s", flush=True)
        if row["feasible"] and (best is None or set_obj < best[0]):
            best = (set_obj, r)
            # CHECKPOINT the best-so-far after every seed. Writing only at the
            # end means an interrupted run loses everything — which it did.
            write_result_json(r, OUT / "fin-martina-46kg-advanced-thruster.json")
            print(f"          ^ new best, checkpointed (seed {seed})", flush=True)
        (OUT / "martina-multistart-ledger.json").write_text(
            json.dumps({"budget": BUDGET, "seeds": SEEDS,
                        "complete": len(ledger) == len(SEEDS),
                        "runs": ledger}, indent=2) + "\n")

    if best is None:
        raise SystemExit("no feasible set found")
    print(f"\nBEST set_objective {best[0]:.5f} (seed {best[1].seed}) "
          f"in {time.time() - t0:.0f}s total")


if __name__ == "__main__":
    main()
