"""Submit an optimizer winner to the tier-1 CFD service for validation.

Reads a result JSON (optimize.write_result_json), posts a production polar per
designed blade to the fin-cfd-manager, and prints the job ids. The worker on the
EPYC runs OpenFOAM and posts back; the manager forwards each completed sample to
the findata corpus, so this doubles as corpus growth.

Usage:
    python scripts/submit_cfd_validation.py out/fin-....json [--smoke]

Env: CFD_URL (default the manager's LAN VIP), CFD_CLIENT_TOKEN.
NOTE: run this from a host on the cluster LAN (e.g. the EPYC itself) — the
manager is reachable at its MetalLB VIP, not from off-network.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

CFD_URL = os.environ.get("CFD_URL", "http://192.168.80.54:8080").rstrip("/")
TOKEN = os.environ.get("CFD_CLIENT_TOKEN", "")
# The frozen production polar: level-2 mesh, the measured stall band bracketed.
PROD_ANGLES = [0.0, 4.0, 8.0, 12.0, 16.0]


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{CFD_URL}{path}", method="POST",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> None:
    if not TOKEN:
        raise SystemExit("set CFD_CLIENT_TOKEN")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    smoke = "--smoke" in sys.argv
    result = json.loads(Path(args[0]).read_text())

    speed = result["rider"]["speed_ms"]
    config = result["rider"]["config"]
    common = {"speed": speed, "config": config, "angles": PROD_ANGLES,
              "mesh_level": 0 if smoke else 2, "smoke": False}
    if smoke:
        common["end_time"] = 200

    jobs: list[tuple[str, dict]] = []
    # 1. Each DESIGNED blade on its own — validates that blade's polar against
    #    the tier-0 prediction. Placement-independent, so always meaningful.
    jobs.append(("side", {**common, "fin": result["fin"]}))
    if result.get("center_fin"):
        jobs.append(("center", {**common, "fin": result["center_fin"]}))
    # 2. The whole placed SET — the only run that RESOLVES interference
    #    (per-slot forces from one coupled solution). Conditioned on the
    #    cluster geometry in fin_set: with production-default placements this
    #    speaks about a generic thruster, not a specific board.
    fin_set = (result.get("set") or {}).get("fin_set")
    if fin_set and "--no-set" not in sys.argv:
        jobs.append(("set", {**common, "fin_set": fin_set}))

    for label, job in jobs:
        out = post("/jobs", job)
        print(f"{label:7} -> job {out['job_id']} ({out['status']})")


if __name__ == "__main__":
    main()
