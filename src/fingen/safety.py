"""Third-party injury constraints: shapes a fin may not have, whatever it scores.

Every other gate in fingen protects the fin (stress, divergence, flutter) or the
rider's own feel (washout). Nothing protected the person a fin HITS, and the
optimizer duly found shapes no commercial fin has: a leading edge that curls
FORWARD near the tip (a hook, which catches skin instead of glancing off it)
and tips sharper than any template. Fin lacerations are among the commonest
surf injuries even with conventional fins; a search that is free to invent
geometry must not be free to invent worse ones.

WHAT IS DELIBERATELY NOT CONSTRAINED. The 0.7 mm printed trailing edge stays:
every commercial fin is effectively a blade there, and carbon-laminate fins are
harder and sharper still than PPA-CF. A concave trailing edge whose tip lobe
sweeps aft also stays — that is the standard raked-fin outline, not a defect.
The line drawn is: no worse than the commercial baseline riders already accept.

TWO METRICS, BOTH PURE FUNCTIONS OF OutlineParams (no OCCT, sub-millisecond),
computed on the FINAL planform — the same dense outline the loft is built from,
tip rounding included — so what is checked is what gets printed:

  hook_depth(outline)  forward-hook depth, mm. Follow the LE up from the base;
                       once it first starts moving aft, the furthest it ever
                       comes back forward. A monotone rake scores 0.
                       Forbidden above HOOK_MAX_MM.

  tip_radius(outline)  apex radius, mm: the largest R for which the tip is at
                       least as blunt as a coin of radius R, i.e. at every
                       distance h below the apex the planform is at least as
                       wide as that circle. min over h of (c(h)^2/4 + h^2)/(2h).
                       Forbidden below TIP_RADIUS_MIN_MM.

HOW A HOOK ARISES, in parameter terms. `sweep` pins the tip point at
depth*tan(sweep); the level-2 `le_dx` offsets move the six interior LE control
points. When the upper ones sit AFT of the tip point, the Bezier edge has to
swing forward to reach it. The first one found: tip at x = 74.9 mm, control
points at 80 % and 92 % span at 97.7 and 107.2 mm -> a 10.9 mm hook.

WHY NOT BOUNDS ON THE PARAMETERS THEMSELVES. A hook is a COMBINATION (low sweep
x aft upper offsets), so no per-parameter box excludes it. The strict
parameter-level rule — LE control points may not step forward after stepping
aft — is guaranteed by Bezier variation-diminishing to exclude every hook, and
did catch 1334 of 1335 hooks in 3581 random search-box outlines; it also
forbade 75 % of outlines with NO hook, including real winners. The metrics
below forbid exactly the shapes that are wrong.

THRESHOLDS, calibrated against spider.reference_fleet() (the commercial-
template prior) and 144 archived optimizer blades:
  * HOOK_MAX_MM = 1.0. Every template scores <= 0.69 mm (fish-keel, a small
    tip-rounding effect, not a catch). Only 1 % of archived blades fall in
    0.5-1 mm, a natural gap between numerical noise and real hooks.
  * TIP_RADIUS_MIN_MM = 8.0. Templates span 9.03 mm (hi-aspect) to 90 mm; 8
    keeps every one with a 1 mm margin. Archived blades went as low as 2.5 mm.

ENFORCED IN TWO PLACES THAT READ THE SAME FUNCTIONS: optimize.evaluate() as a
graded penalty (infeasible while violated, steering the search back), and
sizing.check_anchor() as a hard issue, which the exporter refuses to write. A
safety interlock, not advisory output — these protect people who never chose
the risk, which is exactly the case where gating is right.
"""
from __future__ import annotations

import numpy as np

from fingen.outline import planform
from fingen.params import OutlineParams

HOOK_MAX_MM = 1.0
TIP_RADIUS_MIN_MM = 8.0
# Penalty scale for a hook: the order of the hooks actually produced (the first
# exported one was 10.9 mm), so a real hook costs a penalty of order one, like
# the fractional-margin gates beside it.
HOOK_PENALTY_SCALE_MM = 10.0


def hook_depth(outline: OutlineParams) -> float:
    """Forward-hook depth of the leading edge, mm (0 for a monotone rake)."""
    _z, x_le, _c = planform(outline)
    steps = np.diff(x_le)
    aft = np.nonzero(steps > 0.0)[0]
    if len(aft) == 0:
        return 0.0
    # An initial FORWARD bulge (le_fullness) closes against the board and is
    # not a hook; measure only after the edge first starts moving aft.
    edge = x_le[aft[0]:]
    return float(np.max(np.maximum.accumulate(edge) - edge))


def tip_radius(outline: OutlineParams) -> float:
    """Apex radius, mm: the tip is at least as blunt as a circle of this radius."""
    z, _x_le, chord = planform(outline)
    h = outline.depth - z
    m = h > 1e-6
    return float(np.min((chord[m] ** 2 / 4.0 + h[m] ** 2) / (2.0 * h[m])))


def safety_penalties(outline: OutlineParams) -> dict[str, float]:
    """Graded penalties for optimize.evaluate(); empty when the outline is safe."""
    out = {}
    hook = hook_depth(outline)
    if hook > HOOK_MAX_MM:
        out["forward_hook"] = (hook - HOOK_MAX_MM) / HOOK_PENALTY_SCALE_MM
    r = tip_radius(outline)
    if r < TIP_RADIUS_MIN_MM:
        out["tip_radius"] = (TIP_RADIUS_MIN_MM - r) / TIP_RADIUS_MIN_MM
    return out


def safety_issues(outline: OutlineParams) -> list[str]:
    """Human-readable violations for check_anchor(); empty when safe."""
    issues = []
    hook = hook_depth(outline)
    if hook > HOOK_MAX_MM:
        issues.append(f"leading edge hooks forward {hook:.1f} mm near the tip "
                      f"(max {HOOK_MAX_MM:g} mm) — catches instead of glancing "
                      "off in a collision")
    r = tip_radius(outline)
    if r < TIP_RADIUS_MIN_MM:
        issues.append(f"tip radius {r:.1f} mm below the {TIP_RADIUS_MIN_MM:g} mm "
                      "minimum — sharper than any commercial template")
    return issues
