"""The same search without the edge offsets: stage A only (eight sliders and the camber gene), the whole budget.
usage: run_stage_a.py <speed> <lean> <seed> <budget>     (the test rider's gates)"""
import pickle, sys, time
from pathlib import Path

import fingen.optimize as O
from fingen import bladehydro
from fingen.outline import metrics
from fingen.params import FinConfig, TabSystem

if __name__ == "__main__":
    speed, lean, seed, budget = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    rider = O.RiderSpec(weight_kg=60.0, config=FinConfig.THRUSTER, material="ppa-cf", tabs=TabSystem("click_tab"),
                        bank_deg=lean, speed_ms=speed, scoring="frontier", hydro_model="lattice-knee",
                        side_foil="cambered", aspirations={"hold": 0.80}, stress_sf_min=1.5, washout_max=0.015,
                        tab_sf_min=None)
    t0 = time.time()
    x0 = [*O._x0_sliders(rider.config), O._CAMBER_X0]
    xa, fa, hist, na = O._run_cma(rider, x0, O._SIGMA_A, use_offsets=False, use_grooves=False, budget=budget,
                                  seed=seed, workers=1)
    fin = O._decode(xa, rider.config, use_offsets=False, use_grooves=False, tabs=rider.tabs, camber=True)
    e = O.evaluate(fin, rider)
    a_knee, _ = bladehydro.knee(fin, speed, "v1")
    out = {"speed": speed, "lean": lean, "seed": seed, "budget": budget, "gates": "file", "stage": "A only",
           "fin": fin, "objective": e.objective, "penalty": e.penalty, "feasible": e.feasible,
           "margins": dict(e.margins), "penalties": dict(e.penalties), "issues": list(e.issues), "knee_deg": a_knee,
           "seconds": time.time() - t0}
    tag = f"stageA-v{speed:g}-l{lean:g}-s{seed}"
    (Path(__file__).parent / f"{tag}.pkl").write_bytes(pickle.dumps(out))
    o, f = fin.outline, fin.foil
    print(f"{tag}: obj {e.objective:+.3f} {'ok ' if e.feasible else 'INF'} straight {e.margins['trim_drag_n']:.2f} work {e.margins['work_drag_n']:.2f} "
          f"hold {e.margins['hold_ratio']:.3f} | area {metrics(o).area:.0f} depth {o.depth:.0f} base {o.base:.0f} sweep {o.sweep:.0f} tipw {o.tip_width_ratio:.2f} "
          f"lef {o.le_fullness:.2f} te {o.te_shape:.2f} camber {100 * f.camber_ratio:.1f} t/c {f.thickness_ratio:.3f}x{fin.thickness_tip_factor:.2f} knee {a_knee:.1f} "
          f"sf {e.margins['stress_sf_roll']:.2f} yaw {e.margins['yaw_stiffness_nm_rad']:.0f} roll {e.margins['roll_damping_nm_s']:.2f} | {time.time() - t0:.0f}s", flush=True)
