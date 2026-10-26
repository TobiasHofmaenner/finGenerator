"""Multistart search for ANY rider, described by a JSON file.

Usage: rider_search.py <rider.json> [budget=50000] [seeds=8] [offset=0]

martina_search.py and cruiser_search.py each hard-code one rider; a third copy
per customer would triplicate the checkpoint logic, including the two-stream
race that already bit once. This reads the rider instead. Keys mirror RiderSpec
field names; "name" sets the output directory out/riders/<name>/. Unknown keys
are rejected rather than ignored, so a misspelled gate cannot silently fall back
to its default.

Run two offset streams side by side to use a 20-core box (each optimize() call
already saturates ~popsize workers):
    rider_search.py r.json 50000 6 0 &  rider_search.py r.json 50000 6 6 &

Each stream checkpoints its own best to {name}-best-{offset}.json; the unscoped
{name}.json is written ONLY by reconcile(), from every seed file on disk, so the
headline artifact is the global best whichever stream finishes last.
"""
from __future__ import annotations

import dataclasses
import json
import sys
import time
from pathlib import Path

from fingen.optimize import RiderSpec, optimize, write_result_json
from fingen.outline import metrics
from fingen.params import FinConfig, TabSystem
from fingen.sizing import Skill

_ENUMS = {"skill": lambda v: Skill[v], "config": FinConfig, "tabs": TabSystem}


def load_rider(path: Path) -> tuple[str, RiderSpec]:
    raw = json.loads(path.read_text())
    name = raw.pop("name")
    known = {f.name for f in dataclasses.fields(RiderSpec)}
    unknown = set(raw) - known
    if unknown:
        raise SystemExit(f"{path}: unknown RiderSpec keys {sorted(unknown)}")
    kw = {k: (_ENUMS[k](v) if k in _ENUMS else v) for k, v in raw.items()}
    return name, RiderSpec(**kw)


def reconcile(out: Path, name: str) -> None:
    rows = []
    for p in sorted((out / "seeds").glob("seed-*.json")):
        d = json.loads(p.read_text())
        if d.get("set", {}).get("feasible"):
            rows.append((d["set"]["objective"], p, d["search"]["seed"]))
    if not rows:
        print("reconcile: no feasible seed files", flush=True)
        return
    obj, p, seed = min(rows, key=lambda r: r[0])
    (out / f"{name}.json").write_text(p.read_text())
    print(f"reconcile: {name}.json <- seed {seed} (objective {obj:.6f}, "
          f"best of {len(rows)} feasible)", flush=True)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    name, rider = load_rider(Path(sys.argv[1]))
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 50_000
    n_seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    offset = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    out = Path("out/riders") / name
    (out / "seeds").mkdir(parents=True, exist_ok=True)

    best, ledger, t0 = None, [], time.time()
    for seed in range(offset, offset + n_seeds):
        t1 = time.time()
        r = optimize(rider, budget_evals=budget, seed=seed)
        write_result_json(r, out / "seeds" / f"seed-{seed:03d}.json")
        d = json.loads((out / "seeds" / f"seed-{seed:03d}.json").read_text())
        obj, feas = d["set"]["objective"], d["set"]["feasible"]
        ledger.append({"seed": seed, "set_objective": obj, "feasible": feas,
                       "side_area_mm2": metrics(r.fin.outline).area,
                       "center_area_mm2": (metrics(r.center.outline).area
                                           if r.center else None),
                       "wall_s": round(time.time() - t1, 1)})
        print(f"seed {seed:2d}  set_obj {obj:.5f}  feasible {feas}  "
              f"side {ledger[-1]['side_area_mm2']:.0f}  "
              f"center {ledger[-1]['center_area_mm2'] or 0:.0f}  "
              f"{ledger[-1]['wall_s']:.0f}s", flush=True)
        if feas and (best is None or obj < best):
            best = obj
            write_result_json(r, out / f"{name}-best-{offset:03d}.json")
            print(f"          ^ new best (seed {seed})", flush=True)
        (out / f"{name}-ledger-{offset:03d}.json").write_text(json.dumps(
            {"budget": budget, "runs": ledger}, indent=2) + "\n")

    print(f"\nstream {offset}: best {best} in {time.time() - t0:.0f}s", flush=True)
    reconcile(out, name)


if __name__ == "__main__":
    main()
