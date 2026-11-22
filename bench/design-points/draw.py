"""Outlines of the design-point map's fins: speed down, lean across, references in the last column."""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fingen.optimize import fin_from_dict
from fingen.outline import metrics, planform

D = Path("bench/design-points/fins")
def load(n):
    d = json.loads((D / f"{n}.json").read_text()); return fin_from_dict(d["fin"]), d["margins"]
gen2 = fin_from_dict(json.loads(Path("bench/foil-family/fins/side-shipped-gen2.json").read_text())["fin"])
fig, axes = plt.subplots(3, 4, figsize=(17, 13))
def draw(ax, fin, title, colour="#1f6f8b"):
    z, x_le, chord = planform(fin.outline)
    ax.fill_betweenx(z, x_le, x_le + chord, color=colour, alpha=0.25)
    ax.plot(x_le, z, color=colour, lw=2); ax.plot(x_le + chord, z, color=colour, lw=2)
    ax.plot([x_le[0], x_le[0] + chord[0]], [0, 0], "k-", lw=3)
    ax.set_aspect("equal"); ax.set_xlim(-30, 170); ax.set_ylim(-5, 150); ax.grid(alpha=0.3)
    ax.set_title(title, fontsize=11)
for i, v in enumerate((6.5, 7.5, 8.5)):
    for j, lean in enumerate((40, 48, 55)):
        fin, m = load(f"file-v{v:g}-lean{lean}")
        o, f = fin.outline, fin.foil
        draw(axes[i, j], fin, f"{v:g} m/s, {lean}° lean\n{metrics(o).area:.0f} mm², camber {100 * f.camber_ratio:.1f} %, t/c {f.thickness_ratio:.3f}\n"
                               f"hold {m['hold_ratio']:.2f}, {m['trim_drag_n']:.1f} N straight, {m['work_drag_n']:.1f} N working")
draw(axes[0, 3], gen2, f"for comparison: gen-2 side as shipped\n{metrics(gen2.outline).area:.0f} mm², flat inside, t/c 0.092", "#555555")
fin, m = load("omar-v7.5-lean48")
draw(axes[1, 3], fin, f"tab gate ON: 7.5 m/s, 48°\n{metrics(fin.outline).area:.0f} mm², hold {m['hold_ratio']:.2f}, {m['work_drag_n']:.1f} N working", "#b5532d")
fin, m = load("omar-v8.5-lean55")
draw(axes[2, 3], fin, f"tab gate ON: 8.5 m/s, 55°\n{metrics(fin.outline).area:.0f} mm², hold {m['hold_ratio']:.2f}, {m['work_drag_n']:.1f} N working", "#b5532d")
fig.suptitle("Generation 3 side fin for a 60 kg rider over the design turn (model output, not yet checked in CFD). "
             "Leading edge to the left; mm.", fontsize=13)
fig.tight_layout(); fig.savefig(sys.argv[1], dpi=75)
print("ok")
