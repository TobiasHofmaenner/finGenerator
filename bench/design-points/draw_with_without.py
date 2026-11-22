"""Outlines: the searches without edge offsets beside the ones with, and the shipped gen-2 side fin."""
import glob, json, pickle, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from fingen.optimize import fin_from_dict
from fingen.outline import metrics, planform

here = Path(__file__).parent
gen2 = fin_from_dict(json.loads(Path("bench/foil-family/fins/side-shipped-gen2.json").read_text())["fin"])
def best(pattern):
    rs = sorted((pickle.loads(open(p, "rb").read()) for p in glob.glob(str(here / pattern))), key=lambda r: r["objective"])
    return rs[0]
rows = [(8.5, 55), (7.5, 48), (6.5, 48)]
fig, axes = plt.subplots(3, 3, figsize=(13.5, 13))
def draw(ax, fin, title, colour):
    z, x_le, chord = planform(fin.outline)
    ax.fill_betweenx(z, x_le, x_le + chord, color=colour, alpha=0.25)
    ax.plot(x_le, z, color=colour, lw=2); ax.plot(x_le + chord, z, color=colour, lw=2)
    ax.plot([x_le[0], x_le[0] + chord[0]], [0, 0], "k-", lw=3)
    ax.set_aspect("equal"); ax.set_xlim(-30, 170); ax.set_ylim(-5, 150); ax.grid(alpha=0.3)
    ax.set_title(title, fontsize=10.5)
def label(r):
    m = r["margins"]; o = r["fin"].outline; f = r["fin"].foil
    return (f"{metrics(o).area:.0f} mm², camber {100 * f.camber_ratio:.1f} %, t/c {f.thickness_ratio:.3f}\n"
            f"hold {m['hold_ratio']:.2f}, {m['trim_drag_n']:.2f} N straight, {m['work_drag_n']:.2f} N working, score {r['objective']:+.2f}")
for i, (v, lean) in enumerate(rows):
    a = best(f"stageA-v{v:g}-l{lean:g}-s*.pkl"); b = best(f"dp-file-v{v:g}-l{lean:g}-h0.8-s*.pkl")
    draw(axes[i, 0], a["fin"], f"{v:g} m/s, {lean}°: eight sliders and camber only\n" + label(a), "#2d7d46")
    draw(axes[i, 1], b["fin"], f"{v:g} m/s, {lean}°: with the twelve edge offsets\n" + label(b), "#1f6f8b")
    if i == 0:
        draw(axes[i, 2], gen2, f"for comparison: gen-2 side as shipped\n{metrics(gen2.outline).area:.0f} mm², flat inside, t/c 0.092", "#555555")
    else:
        axes[i, 2].axis("off")
fig.suptitle("Generation 3 side fin, 60 kg rider: the search with and without the edge offsets (model output). Leading edge to the left; mm.", fontsize=12)
fig.tight_layout(); fig.savefig(sys.argv[1], dpi=75); print("ok")
