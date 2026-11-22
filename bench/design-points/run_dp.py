"""One gen-3 side-fin search for the 60 kg test rider at a design point given directly.
usage: run_dp.py <speed m/s> <lean deg> <seed> <budget> [gates=omar|default] [hold=0.80]
The rider is what the web quiz sends (facts, lean, speed, the three model opt-ins, the hold target), with the
gates of the test rider's files ("file": bending safety factor 1.5, washout 1.5 %, no tab gate), the library's
defaults ("default": 1.0, no washout limit, tab gate at 1.0), or his gates with the tab gate on ("omar").""" 
import pickle, sys, time
from pathlib import Path

import fingen.optimize as O
from fingen import bladehydro
from fingen.outline import metrics
from fingen.params import FinConfig, TabSystem

GATES = {"omar": {"stress_sf_min": 1.5, "washout_max": 0.015},            # his gates, tab gate ON (a mix)
         "file": {"stress_sf_min": 1.5, "washout_max": 0.015, "tab_sf_min": None},   # as his rider files
         "default": {}}                                                    # what a quiz job gets today

if __name__ == "__main__":
    speed, lean, seed, budget = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    gates = sys.argv[5] if len(sys.argv) > 5 else "omar"
    hold = float(sys.argv[6]) if len(sys.argv) > 6 else 0.80
    rider = O.RiderSpec(weight_kg=60.0, config=FinConfig.THRUSTER, material="ppa-cf", tabs=TabSystem("click_tab"),
                        bank_deg=lean, speed_ms=speed, scoring="frontier", hydro_model="lattice-knee",
                        side_foil="cambered", aspirations={"hold": hold}, **GATES[gates])
    t0 = time.time()
    res = O.optimize(rider, budget_evals=budget, seed=seed)
    e = O.evaluate(res.fin, rider)
    a_knee, cl_knee = bladehydro.knee(res.fin, speed, "v1")
    out = {"speed": speed, "lean": lean, "seed": seed, "budget": budget, "gates": gates, "hold_target": hold,
           "fin": res.fin, "objective": e.objective, "penalty": e.penalty, "feasible": e.feasible,
           "margins": dict(e.margins), "penalties": dict(e.penalties), "issues": list(e.issues),
           "knee_deg": a_knee, "seconds": time.time() - t0}
    tag = f"dp-{gates}-v{speed:g}-l{lean:g}-h{hold:g}-s{seed}"
    (Path(__file__).parent / f"{tag}.pkl").write_bytes(pickle.dumps(out))
    o, f = res.fin.outline, res.fin.foil
    print(f"{tag}: obj {e.objective:+.3f} {'ok ' if e.feasible else 'INF'} straight {e.margins['trim_drag_n']:.2f} work {e.margins['work_drag_n']:.2f} "
          f"hold {e.margins['hold_ratio']:.3f} | area {metrics(o).area:.0f} depth {o.depth:.0f} base {o.base:.0f} sweep {o.sweep:.0f} "
          f"camber {100 * f.camber_ratio:.1f} t/c {f.thickness_ratio:.3f} knee {a_knee:.1f} | {time.time() - t0:.0f}s", flush=True)
