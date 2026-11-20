"""Where known fins sit on the hold measure: what could anchor it (decision D11).

    uv run python scripts/hold_anchor.py [--md=bench/knee/hold-anchor.md]

Hold is the force a blade makes at its knee (`bladehydro.knee`, model
"lattice-knee") over the peak turn force of the rider's design turn. The
number has no meaning of its own: the peak force rests on an assumed lean and
speed, and a blade keeps lifting past its knee. What can anchor it is where
fins of known behaviour land on it:

  * the two fins one rider has ridden (gen 1 slid, gen 2 does not), and
  * a commercial medium thruster fin on the riders a size chart puts on it
    (medium: about 14-15.5 sq in, sold for about 65-80 kg). The [BW04] tunnel
    fin is such a fin (9 566 mm2 = 14.8 sq in).

Every blade is evaluated for every rider with the same rider file; only weight
and level change (level sets lean and speed of the design turn).
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from knee_survey import bw04

import fingen.optimize as O
from fingen.optimize import fin_from_dict
from fingen.outline import metrics
from fingen.params import FinConfig, TabSystem
from fingen.sizing import Skill

REPO = Path(__file__).resolve().parent.parent
RIDER = REPO / "riders/omar-60kg-pro-thruster-ppa-cf-big-gen2-m2.json"
RIDERS = ((60, Skill.PRO), (65, Skill.INTERMEDIATE), (65, Skill.PRO), (75, Skill.INTERMEDIATE),
          (75, Skill.PRO), (80, Skill.INTERMEDIATE), (80, Skill.PRO), (90, Skill.PRO))


def _fin(rel: str):
    raw = json.loads((REPO / "bench" / rel).read_text())
    return fin_from_dict(raw.get("fin", raw))


def main() -> None:
    opt = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    raw = json.loads(RIDER.read_text())
    raw.pop("name")
    enums = {"skill": lambda v: Skill[v], "config": FinConfig, "tabs": TabSystem}
    base = O.RiderSpec(**{**{k: (enums[k](v) if k in enums else v) for k, v in raw.items()},
                          "hydro_model": "lattice-knee"})
    fins = {"commercial medium (tunnel fin [BW04], flat inside)": bw04(),
            "gen-2 side as shipped": _fin("mount/fins/side-shipped-gen2.json"),
            "gen-1 side as ridden": _fin("mount/fins/side-asridden-gen1.json")}
    lines = ["# Hold of known fins, read off the strips", "",
             "Force at the knee over the peak force of the design turn "
             "(`scripts/hold_anchor.py`).", "",
             "| fin | area mm² | "
             + " | ".join(f"{w} kg {s.name.lower()}" for w, s in RIDERS) + " |",
             "|---|---|" + "---|" * len(RIDERS)]
    for name, fin in fins.items():
        row = []
        for w, s in RIDERS:
            rider = dataclasses.replace(base, weight_kg=float(w), skill=s)
            row.append(f"{O.evaluate(fin, rider).margins['hold_ratio']:.2f}")
        lines.append(f"| {name} | {metrics(fin.outline).area:.0f} | " + " | ".join(row) + " |")
    text = "\n".join(lines)
    print(text)
    if "md" in opt:
        Path(opt["md"]).write_text(text + "\n")


if __name__ == "__main__":
    main()
