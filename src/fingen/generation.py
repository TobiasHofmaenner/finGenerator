"""Model generation: which version of the PHYSICS produced a result.

A result JSON records the fin and its scores, but until 2026-10-27 nothing
recorded which model scored it. That mattered the day the model changed: the
camber term and the peak-load axes re-score every fin ever shipped, so "hold
73" on a file from September and "hold 50" on one from October can be the
SAME blade. Package version does not capture this (0.13.2 spanned both), and
a git SHA is too fine (most commits change no physics). MODEL_GENERATION is
the coarse, hand-bumped integer that means "the numbers are comparable".

RULE: bump it when a change alters what evaluate() returns for an unchanged
fin and rider — scoring, gates, lift/drag/structural models, normalization
basis. Do NOT bump for tooling, export, UI, tests, or refactors. Describe the
change in GENERATIONS so a reader of an old file can learn what it predates.
"""
from __future__ import annotations

import functools
import subprocess
from pathlib import Path

MODEL_GENERATION = 3

GENERATIONS: dict[int, str] = {
    1: ("Everything before 2026-10-27, stamped retroactively (no file carried a "
        "generation). Handling axes read at the SUSTAINED cruise load; lift model "
        "with no camber term (CL = 0 at alpha = 0). Sub-history by git date: "
        "area ceiling removed, t/c ceiling 0.22, 3D torsional anchor (Aug-Sep); "
        "injury constraints, FCS II tab fixes (Sep-Oct). All first-contact sets "
        "ridden in Bali are generation 1."),
    2: ("2026-10-27. (i) Thin-airfoil camber term: alpha_0 integrated from the "
        "section's own camber line (hydro.zero_lift_alpha_deg), validated against "
        "the first production CFD polar to within 10 %. (ii) hold and forgiveness "
        "scored at the PEAK turn load (sizing force_peak_n) instead of the "
        "sustained cruise load; the sustained value still drives the capacity "
        "gate. Motivated by the first field complaint: a pro's \"feels sliding, "
        "top turn lose the control\" on a gen-1 blade scored hold 73 / "
        "forgiveness 36, which gen 2 scores hold 50 with a NEGATIVE peak margin. "
        "Also adds the opt-in RiderSpec.peak_margin_min_deg gate (default None, so "
        "no existing rider's numbers move)."),
    3: ("2026-11-19, IN DEVELOPMENT (docs/GEN3-PLAN.md) — this entry grows until "
        "the first generation-3 set ships. So far, three model defects found by "
        "the reach audit (docs/MODEL-REACH.md): (i) pivot: the yaw arm was "
        "|x_cp - base/2| + c/4, a distance inside the fin with an absolute "
        "value, so rake up to ~45 deg scored as MORE pivoty; now the signed arm "
        "from the board's yaw centre to the blade's CP (spider.YAW_ARM_REF_MM). "
        "(ii) speed: every blade was read isolated at +1 deg; a toed side fin "
        "is now read at its own incidence, pair-averaged, so a toe-matched "
        "cambered blade trims like a symmetric one (spider.trim_drag_n). "
        "(iii) camber credit: alpha_0 was converted 1:1 into max lift at any "
        "thickness; beyond flat-inside t/c 0.10 the break angle now drops degree "
        "for degree (hydro.break_alpha_deg). Symmetric blades change on pivot "
        "only; flat-inside blades up to t/c 0.10 change on pivot and speed."),
}


@functools.lru_cache(maxsize=1)
def _git() -> tuple[str | None, bool | None]:
    """(short SHA, dirty) of the checkout this package runs from, or (None,
    None) when it is an installed wheel / container image with no .git."""
    root = Path(__file__).resolve().parents[2]
    try:
        sha = subprocess.run(["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        if sha.returncode != 0:
            return None, None
        st = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                            capture_output=True, text=True, timeout=5)
        return sha.stdout.strip(), bool(st.stdout.strip()) if st.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None, None


def stamp() -> dict:
    """The provenance block written into every result JSON."""
    from fingen import __version__
    sha, dirty = _git()
    return {"model": MODEL_GENERATION, "fingen": __version__, "git": sha, "dirty": dirty}
