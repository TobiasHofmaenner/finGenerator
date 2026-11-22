"""One slider at a time around the fin found without offsets for 8.5 m/s and 55 deg: what the model pays for
tip width, depth and base (the three it parks on a bound)."""
import dataclasses, json
from pathlib import Path
import fingen.optimize as O
from fingen import bladehydro
from fingen.outline import metrics
from fingen.params import FinConfig, TabSystem

rider = O.RiderSpec(weight_kg=60.0, config=FinConfig.THRUSTER, material="ppa-cf", tabs=TabSystem("click_tab"),
                    bank_deg=55.0, speed_ms=8.5, scoring="frontier", hydro_model="lattice-knee",
                    side_foil="cambered", aspirations={"hold": 0.80}, stress_sf_min=1.5, washout_max=0.015, tab_sf_min=None)
fin = O.fin_from_dict(json.loads(Path("bench/design-points/fins/sliders-v8.5-lean55.json").read_text())["fin"])
o = fin.outline
print(f"start: depth {o.depth:.0f} base {o.base:.0f} sweep {o.sweep:.0f} tip width {o.tip_width_ratio:.2f} le_fullness {o.le_fullness:.2f} te_shape {o.te_shape:.2f}")
def show(label, f):
    try:
        e = O.evaluate(f, rider); m = e.margins; a, _ = bladehydro.knee(f, 8.5, "v1")
    except ValueError as err:
        print(f"  {label:22s} rejected: {str(err)[:80]}"); return
    pen = {k: round(v, 3) for k, v in e.penalties.items() if v > 1e-6}
    sh = {k[10:]: round(v, 2) for k, v in m.items() if k.startswith("shortfall_")}
    print(f"  {label:22s} obj {e.objective:+7.3f} area {metrics(f.outline).area:6.0f} straight {m['trim_drag_n']:.2f} work {m['work_drag_n']:.2f} hold {m['hold_ratio']:.3f} knee {a:4.1f} "
          f"sf_roll {m['stress_sf_roll']:.2f} tab_sf {m['tab_sf']:.2f} yaw {m['yaw_stiffness_nm_rad']:.0f} roll {m['roll_damping_nm_s']:.2f} shortfalls {sh} {pen or ''}")
for name, values in (("tip_width_ratio", (0.25, 0.35, 0.45, 0.55, 0.60, 0.70, 0.80)), ("depth", (110, 120, 130, 140, 150, 160, 175)),
                     ("base", (95, 104, 112, 120, 130)), ("sweep", (10, 20, 26, 32, 40))):
    print(name)
    for v in values:
        try:
            f = dataclasses.replace(fin, outline=dataclasses.replace(o, **{name: float(v)}))
        except ValueError as err:
            print(f"  {name} {v}: not a fin ({str(err)[:70]})"); continue
        show(f"{name} {v:g}", f)
