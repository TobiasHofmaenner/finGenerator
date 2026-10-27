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

MODEL_GENERATION = 2

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
