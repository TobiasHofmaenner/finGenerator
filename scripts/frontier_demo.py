"""Frontier scoring demo: one rider, three sets of aspirations — do they give different fins?

    uv run python scripts/frontier_demo.py <rider.json> [--budget=6000] [--seeds=3] [--md=out.md]

The test of "optimize first, then consult the spider for the tradeoffs": with
the goods one-sided, the search should run to the frontier whatever is asked,
and the rider's aspirations should only move it ALONG the frontier — by
amounts a rider would feel. Each profile changes nothing but
`RiderSpec.aspirations`; hydro model lattice, side foil cambered (camber
searched), every gate of the rider file kept.

Every profile is searched from several seeds and every result is scored under
every profile, so the table can tell a preference of the scoring from a search
that stopped in the wrong valley (the first cut of this method did exactly
that: docs/MODEL-EXTENSION.md, "The oversized fin").
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from fingen import bladehydro
from fingen.hydro import break_alpha_deg, lift_curve_slope
from fingen.optimize import DEFAULT_ASPIRATIONS, RiderSpec, board_drag_n, evaluate, optimize
from fingen.outline import metrics
from fingen.params import FinConfig, TabSystem
from fingen.sizing import Skill, anchor

ENUMS = {"skill": lambda v: Skill[v], "config": FinConfig, "tabs": TabSystem}
PROFILES = {
    "neutral": {},
    "speed first": {"trim_drag_frac": 0.03, "work_drag_frac": 0.04, "hold": 1.05},
    "hold first": {"hold": 1.45, "trim_drag_frac": 0.06, "work_drag_frac": 0.07},
}


def peak_drag(fin, rider: RiderSpec) -> str:
    """Drag in N while the blade makes the rider's peak turn force — reported,
    not scored (GEN3-PLAN 1.3). "—" when the blade cannot make that force."""
    sheet = anchor(rider.weight_kg, rider.skill, design_speed=rider.speed, config=rider.config,
                   material=rider.material, tabs=rider.tabs, member="dominant",
                   area_max_factor=rider.area_max_factor)
    a_break = break_alpha_deg(fin, lift_curve_slope(fin)[1])
    drag, made = bladehydro.drag_at_force_n(fin, rider.speed, sheet.force_peak_n, a_break)
    return f"{drag:.0f}" if made >= 0.98 * sheet.force_peak_n else "—"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    raw = json.loads(Path(args[0]).read_text())
    name = raw.pop("name")
    base = {k: (ENUMS[k](v) if k in ENUMS else v) for k, v in raw.items()}
    budget, seeds = int(opt.get("budget", 6000)), int(opt.get("seeds", 3))
    d_board = board_drag_n(base["weight_kg"])
    riders = {label: RiderSpec(**{**base, "hydro_model": "lattice", "side_foil": "cambered",
                                  "scoring": "frontier", "aspirations": asp or None})
              for label, asp in PROFILES.items()}
    found = []                                   # (profile searched, seed, fin)
    for label, rider in riders.items():
        for seed in range(seeds):
            t0 = time.time()
            found.append((label, seed, optimize(rider, budget_evals=budget, seed=seed).fin))
            print(f"  {label}, seed {seed}: {time.time() - t0:.0f} s", flush=True)
    L: list[str] = []
    w = L.append
    w(f"# Frontier scoring demo — {name}\n")
    w(f"Hydro model lattice, side foil cambered, {budget} evaluations per search, {seeds} seeds per profile. Board drag "
      f"yardstick {d_board:.0f} N; one noticeable step = {0.025 * d_board:.1f} N per side fin or 0.20 of the peak force.\n")
    for label, rider in riders.items():
        a = {**DEFAULT_ASPIRATIONS, **PROFILES[label]}
        w(f"\n## {label}: straight ≤ {a['trim_drag_frac'] * d_board:.1f} N, work ≤ {a['work_drag_frac'] * d_board:.1f} N, "
          f"hold ≥ {a['hold']:.2f}\n")
        w("| found by | objective | going straight N | at work load N | at peak force N (not scored) | hold (× peak force) | "
          "peak margin ° | area mm² | depth | "
          "sweep ° | camber % | t/c | yaw stiffness N·m/rad | roll damping N·m·s | feasible |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        rows = []
        for src, seed, fin in found:
            e = evaluate(fin, rider)
            m, f, o = e.margins, fin.foil, fin.outline
            rows.append((e.objective, f"| {src}, seed {seed}{' (own search)' if src == label else ''} | {e.objective:+.2f} | "
                         f"{m['trim_drag_n']:.1f} | {m['work_drag_n']:.1f} | {peak_drag(fin, rider)} | {m['hold_ratio']:.2f} | "
                         f"{m['margin_peak_deg']:+.1f} | "
                         f"{metrics(o).area:.0f} | {o.depth:.0f} | {o.sweep:.0f} | {f.camber_ratio * 100:.1f} | "
                         f"{f.thickness_ratio:.3f} | {m['yaw_stiffness_nm_rad']:.0f} | {m['roll_damping_nm_s']:.2f} | {e.feasible} |"))
        for _, line in sorted(rows)[: seeds + 2]:
            w(line)
    text = "\n".join(L)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
