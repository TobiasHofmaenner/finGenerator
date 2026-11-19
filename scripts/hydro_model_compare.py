"""Before/after of the hydro-model switch (gen-3 step B2): tier-0 vs lattice.

    uv run python scripts/hydro_model_compare.py [--search=<rider name>] [--budget=6000] [--md=out.md]

For every rider spec in riders/ with an archived winner in out/riders/<name>/,
the winner's side blade (and centre, as the rear member) is scored twice with
the SAME rider: once with hydro_model "tier0" (how it was designed), once with
"lattice" (lift curve, centre of pressure and drag from the viscous lattice and
the section table, the blade read as mounted). Reported: the seven scores, the
gates, and the physical quantities behind speed and drive in Newtons.

--search re-optimises one rider under the lattice model (single seed, small
budget: a first look at where the optimum moves, NOT a design) and prints the
winner next to the archived one.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import time
from pathlib import Path

from fingen import bladehydro, spider
from fingen.hydro import RHO_SEAWATER
from fingen.optimize import RiderSpec, evaluate, fin_from_dict, optimize
from fingen.outline import metrics
from fingen.params import FinConfig, TabSystem
from fingen.sizing import Skill

ENUMS = {"skill": lambda v: Skill[v], "config": FinConfig, "tabs": TabSystem}


def load_rider(path: Path, **override) -> tuple[str, RiderSpec]:
    raw = json.loads(path.read_text())
    name = raw.pop("name")
    return name, RiderSpec(**{**{k: (ENUMS[k](v) if k in ENUMS else v) for k, v in raw.items()}, **override})


def archived(name: str) -> dict | None:
    d = Path("out/riders") / name
    for cand in [d / f"{name}.json", *sorted(d.glob(f"{name}-best-*.json"), reverse=True)]:
        if cand.exists():
            return json.loads(cand.read_text())
    return None


def physical(fin, rider: RiderSpec) -> dict:
    qa = 0.5 * RHO_SEAWATER * rider.speed**2 * metrics(fin.outline).area * 1e-6
    toe = spider.default_toe_deg(fin)
    slope, a0, _ = bladehydro.lift_curve(fin, rider.speed)
    f_work = spider.work_force_n(rider.weight_kg)
    t0 = spider.raw_scores(fin, rider.speed, rider.weight_kg)
    drag_w, lift_w = bladehydro.drag_at_force_n(fin, rider.speed, f_work, a0 + 10.0)
    return {"trim_t0": 1.0 / t0["speed"], "trim_lat": bladehydro.trim_drag_n(fin, rider.speed, toe),
            "ld_t0": t0["drive"], "ld_lat": lift_w / drag_w, "work_drag_t0": f_work / t0["drive"],
            "work_drag_lat": drag_w, "slope_lat": slope, "a0_lat": a0, "f_work": f_work, "qa": qa}


def geom(fin) -> str:
    o, m = fin.outline, metrics(fin.outline)
    return (f"depth {o.depth:.0f} base {o.base:.0f} sweep {o.sweep:.0f}° tip {o.tip_width_ratio:.2f} "
            f"area {m.area:.0f} mm² AR {m.aspect_ratio:.2f} t/c {fin.foil.thickness_ratio:.3f} "
            f"tip-factor {fin.thickness_tip_factor:.2f}")


def main() -> None:
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    L: list[str] = []
    w = L.append
    w("# Hydro model before/after — tier-0 vs lattice\n")
    w("Same blade, same rider, two hydro models. `lattice` reads the blade as mounted (toe 3.5° for a side blade, "
      f"board mirror strength {bladehydro.BOARD_MIRROR_STRENGTH}) and takes its drag from the section table; the break "
      "angle, the structure and the release / stability axes are tier-0's in both.\n")
    for path in sorted(Path("riders").glob("*.json")):
        name, rider = load_rider(path)
        arch = archived(name)
        if arch is None:
            continue
        _, rider_lat = load_rider(path, hydro_model="lattice")
        w(f"\n## {name}\n")
        blades = [("side", arch["fin"], False)]
        if arch.get("center_fin"):
            blades.append(("centre", arch["center_fin"], True))
        for label, fd, rear in blades:
            fin = fin_from_dict(fd)
            e0, e1 = evaluate(fin, rider, rear_member=rear), evaluate(fin, rider_lat, rear_member=rear)
            ph = physical(fin, rider)
            w(f"**{label}** — {geom(fin)}\n")
            w("| | " + " | ".join(spider.AXES) + " | feasible | penalties | peak margin ° | capacity N |")
            w("|---|" + "---|" * (len(spider.AXES) + 4))
            tg = rider.resolved_targets(rear_member=rear)
            w("| target | " + " | ".join(f"{100 * tg[a]:.0f}" for a in spider.AXES) + " | | | | |")
            for tag, e in (("tier-0", e0), ("lattice", e1)):
                pen = ", ".join(f"{k} {v:.2f}" for k, v in e.penalties.items()) or "none"
                w(f"| {tag} | " + " | ".join(f"{e.spider_predicted[a]:.0f}" for a in spider.AXES)
                  + f" | {e.feasible} | {pen} | {e.margins['margin_peak_deg']:+.2f} | {e.margins['capacity_n']:.0f} |")
            w(f"\nIn Newtons at {rider.speed:.1f} m/s: going straight {ph['trim_t0']:.1f} (tier-0) → {ph['trim_lat']:.1f} (lattice); "
              f"at the {ph['f_work']:.0f} N working load {ph['work_drag_t0']:.1f} → {ph['work_drag_lat']:.1f} "
              f"(L/D {ph['ld_t0']:.1f} → {ph['ld_lat']:.1f}); lattice lift slope {ph['slope_lat']:.2f}/rad, zero-lift {ph['a0_lat']:+.2f}°.\n")
    if "search" in opt:
        path = Path("riders") / f"{opt['search']}.json"
        name, rider_lat = load_rider(path, hydro_model="lattice")
        _, rider = load_rider(path)
        budget = int(opt.get("budget", 6000))
        t0 = time.time()
        res = optimize(rider_lat, budget_evals=budget, seed=0)
        e = evaluate(res.fin, rider_lat)
        w(f"\n## Re-search under the lattice model — {name} (seed 0, {budget} evaluations, {time.time() - t0:.0f} s)\n")
        w("A first look at where the optimum moves, not a design.\n")
        arch = archived(name)
        w("| blade | geometry | lattice scores (" + ", ".join(spider.AXES) + ") | feasible | going straight N | at work load N |")
        w("|---|---|---|---|---|---|")
        rows = [("lattice-model winner", res.fin)]
        if arch:
            rows.insert(0, ("archived (tier-0) winner", fin_from_dict(arch["fin"])))
        for tag, fin in rows:
            ev = evaluate(fin, rider_lat)
            ph = physical(fin, rider_lat)
            w(f"| {tag} | {geom(fin)} | " + " / ".join(f"{ev.spider_predicted[a]:.0f}" for a in spider.AXES)
              + f" | {ev.feasible} | {ph['trim_lat']:.1f} | {ph['work_drag_lat']:.1f} |")
        w(f"\nWinner objective {e.objective:.3f}, penalties {e.penalties or 'none'}.")
        out = Path("out") / f"hydro-compare-{name}-lattice.json"
        out.write_text(json.dumps({"rider": name, "budget": budget, "fin": json.loads(json.dumps(
            dataclasses.asdict(res.fin), default=lambda o: getattr(o, "value", str(o))))}, indent=1))
    text = "\n".join(L)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
