"""The spiderweb: seven surfer-language axes summarizing a fin's tradeoffs.

This is the optimizer's target and the user's mental model. Each axis
is a normalized 0–100 score derived from hidden physics metrics; today they
are backed by the tier-0 analytic model plus two labeled geometry proxies,
and the CFD polar card replaces the backing numbers later WITHOUT changing
the axes (docs/PHYSICS.md §6, the metrics discussion).

Axes and their hidden metrics (at the 7 m/s reference point):
  speed        1 / total drag at trim (friction+form CD0 [Hoe75] + induced)
  drive        L/D at the rider's working side force (weight-scaled, below)
  hold         side-force headroom RELATIVE TO the rider's requirement:
               100·r/(r+r_ref), r = f_max / F_req (see `hold_score`)
  pivot        1 / yaw stiffness (slope · area · CP arm from the base center)
  release      PROXY: sweep + tip-unloading (elliptic deviation) — replaced
               by the post-peak lift gradient once URANS points exist
  forgiveness  degrees of margin from the working angle to the [BW04] break
  stability    lift-based roll damping |L_p| (fingen.roll, KAPPA_FS-corrected,
               at the rider speed) — high = damped/planted, low = agile

EXTENSIVE vs INTENSIVE axes (docs/PHYSICS.md §9b). Five of the seven axes are
INTENSIVE — ratios (L/D, 1/stiffness, degrees of margin, shape proxies) that a
big or a small fin can score equally, so ranking them against the fixed adult
reference fleet is meaningful. Hold was the exception: its raw metric is
maximum side force in NEWTONS, an EXTENSIVE quantity that scales with area.
Ranking Newtons against an adult fleet makes a light rider's weight-capped fin
structurally unable to reach a mid score no matter its shape. Hold is therefore
scored REQUIREMENT-RELATIVE (`hold_score`): headroom over F_req, the same force
the sizing capacity gate demands.

`stability` (the roll axis, added last) is EXTENSIVE-ish too — roll damping
|L_p| ∝ S·s² grows with size — but unlike hold it IS the felt quantity relative
to fleet norms (planted vs agile is judged against the fins people actually
ride), and its rider dependence enters through the TARGET, not the metric: a
heavier/less-aggressive rider WANTS more damping, but the metric of any given
blade is rider-independent, and rank invariance means the rider's target scale
cancels in the ranking. So stability is fleet-ranked exactly like the other
five non-hold axes; 50 means "mid-fleet", not an absolute grade.
"""

from __future__ import annotations

import math
from pathlib import Path

from fingen.hydro import (
    RHO_SEAWATER,
    estimate,
    lift_curve_slope,
    stall_alpha_deg,
    stall_drag_cd,
)
from fingen.outline import metrics, planform
from fingen.params import FinParams, FoilFamily, FoilParams, OutlineParams
from fingen.roll import roll_report
from fingen.sizing import anchor, required_side_force_n

# Order matters: "stability" is APPENDED LAST so the radar/sheet layouts of the
# original six axes stay put and only gain a seventh vertex.
AXES = ("speed", "drive", "hold", "pivot", "release", "forgiveness", "stability")
REF_SPEED = 7.0
# The DRIVE/FORGIVENESS working point is a fixed side FORCE, not a fixed CL: a
# surfer loads the fin with the turn's force budget [Knies25], and a big keel
# delivers it at tiny CL (efficiently) while a small blade must work near its
# break. That budget scales with rider mass, so the reference force is a
# function of weight, not a constant: 120 N was implicitly calibrated on the
# adult reference band, so `work_force_n` re-centers it at W_REF and scales it
# linearly. A 45 kg rider works a lighter budget; a 95 kg rider a heavier one,
# and drive's CL_work / forgiveness's alpha_work follow per rider.
W_REF = 77.5  # kg — mid of the 75/80 kg adult reference band at which the
# original constant 120 N was calibrated (no other documented basis in the
# code/docs; the sizing anchor's calibration target is the 75 kg intermediate).


def work_force_n(weight_kg: float) -> float:
    """Rider-scaled reference side force (N) for the drive working point and the
    forgiveness margin: 120 N at W_REF, linear in rider weight."""
    return 120.0 * (weight_kg / W_REF)


# Rider-agnostic alias = work_force_n(W_REF) = 120.0, kept so plotting defaults
# and any weight-agnostic caller keep the original working point unchanged.
WORK_FORCE_N = work_force_n(W_REF)

# Requirement-relative hold saturation constant. hold_score = 100·r/(r+r_ref)
# with r = f_max/F_req. r_ref is calibrated ONCE for backward compatibility: at
# the committed 75 kg intermediate winner (out/before-after-2.json) the adult
# hold anchor is 57.69293 at 6.4 m/s, where that fin's washed f_max/F_req =
# 1.2175548; solving 100·r/(r+r_ref) = 57.69293 gives r_ref = 0.89285, which
# reproduces the anchor to <1e-4 pt (2.1e-5 actual). The former 4-dp 0.8929 was
# over-rounded — with the true r it landed 1.3e-3 pt off, past the claimed <1e-3.
# A fin exactly meeting its requirement (r = 1) then scores ~52.8; twice the
# required force (r = 2) scores ~69.1.
HOLD_R_REF = 0.89285
# Normalization is by interpolated rank within the reference fleet — robust
# to outlier templates (a longboard single otherwise crushes every shortboard
# fin to ~0 on the extensive axes).


def hold_score(f_max_n: float, f_req_n: float) -> float:
    """Requirement-relative hold: 100·r/(r+r_ref), r = f_max/F_req.

    Saturating (0..100), strictly monotone in f_max, and smooth — CMA-friendly,
    with none of the flat/cliff regions a clipped ratio would have. F_req is the
    sizing capacity gate's threshold (sizing.required_side_force_n): hold thus
    measures headroom over what THIS rider needs, not Newtons ranked against an
    adult fleet, so a weight-capped light-rider fin can still reach mid-scale.
    Doubling F_req halves r (halves the headroom) at fixed f_max."""
    r = f_max_n / max(f_req_n, 1e-9)
    return 100.0 * r / (r + HOLD_R_REF)


# Re-aware profile-drag calibration factor (task #22). The 0.074/Re^0.2
# friction line with the Hoerner form factor sits only ~10 % LOW of the
# fair transition-tier CFD at fin Re — NOT a fully-turbulent rewrite. Both
# 2026 transition polars agree: the needle reads cd0 ×1.24 at α=0, Re 3.5e5
# and the thin-foil section ×1.11 zero-lift at Re 6.25e5, but the ×1.24 is
# mostly the α=0 camber lift-drag; the FAIR like-for-like (zero-lift, drag-
# bucket intercept) is only ×1.11 [bench/freerun-thinfoil/section-polar.md
# §"task #22", pts 1–2; bench/freerun-needle/adjudication.md verdict (b)].
# The Re-trend over 2–7e5 is flat (both ~×1.24 at α=0), so this is a single
# calibration factor anchored to the fair +11 %, NOT a new Re exponent.
CD0_CAL = 1.10


def _cd0(fin: FinParams, speed: float) -> float:
    """Profile drag: turbulent flat-plate friction with a thickness form
    factor [Hoe75], both sides of the fin, times the fin-Re calibration
    factor CD0_CAL (task #22)."""
    est = estimate(fin, speed, 0.0)
    cf = 0.074 / est.reynolds**0.2
    t = fin.foil.thickness_ratio
    form = 1.0 + 2.0 * t + 60.0 * t**4
    return CD0_CAL * 2.0 * cf * form


def raw_scores(fin: FinParams, speed: float = REF_SPEED,
               weight_kg: float = W_REF) -> dict[str, float]:
    """Unnormalized physical values per axis (bigger = more of the quality).

    `weight_kg` sets the rider's working side force (`work_force_n`) that fixes
    drive's CL_work and forgiveness's alpha_work; it defaults to W_REF so the
    fleet-normalization basis and the viz path stay adult-calibrated. `hold`
    stays the raw maximum side force in N — `hold_score` turns it into the
    requirement-relative axis at scoring time."""
    m = metrics(fin.outline)
    area_m2 = m.area * 1e-6
    q = 0.5 * RHO_SEAWATER * speed**2
    slope, ar_eff = lift_curve_slope(fin)
    cd0 = _cd0(fin, speed)

    # speed: inverse total drag at trim (α = 1°) in N. α=1 sits far below the
    # stall knee for every real fin, so the stall term is ~0 here and the speed
    # axis just carries the uniform +CD0_CAL profile-drag bump (task #22).
    est_trim = estimate(fin, speed, 1.0)
    drag_trim = q * area_m2 * (cd0 + est_trim.cdi
                               + stall_drag_cd(est_trim.cl, slope, ar_eff))
    # hold: max side force in N (linear to the AR-dependent break)
    a_break = stall_alpha_deg(ar_eff)
    f_max = q * area_m2 * slope * math.radians(a_break)
    # drive: L/D delivering the rider's reference force (capped near the break
    # for fins too small to deliver it at all). CL_work CAN exceed the stall
    # knee for small fins / light q, so the post-knee stall drag (task #22)
    # bites here — repricing small blades that must work hard.
    cl_work = min(work_force_n(weight_kg) / (q * area_m2),
                  0.95 * slope * math.radians(a_break))
    cdi_work = cl_work**2 / (math.pi * 0.9 * ar_eff)
    ld_work = cl_work / (cd0 + cdi_work + stall_drag_cd(cl_work, slope, ar_eff))
    # pivot: inverse yaw stiffness — CP arm measured from the base center
    z, x_le, chord = planform(fin.outline)
    import numpy as np

    x_cp = float(np.trapezoid((x_le + 0.25 * chord) * chord, z)
                 / max(np.trapezoid(chord, z), 1e-9))
    arm_m = abs(x_cp - fin.outline.base / 2.0) * 1e-3 + 0.25 * (m.area / fin.outline.depth) * 1e-3
    yaw_stiffness = q * area_m2 * slope * arm_m
    # release (PROXY): raked, tip-unloaded planforms shed load gradually
    release = 0.6 * (m.sweep / 50.0) + 0.4 * min(m.elliptic_deviation / 0.30, 1.0)
    # forgiveness: margin from the working angle to the break
    alpha_work = math.degrees(cl_work / slope)
    margin = a_break - alpha_work
    # stability: the blade's own lift-based roll damping |L_p| (fingen.roll at
    # the rider speed), the KAPPA_FS-CORRECTED value the module reports — the
    # felt "planted vs agile" quantity. Rider-independent metric (weight enters
    # only the target); fleet-ranked with the other non-hold axes.
    stability = roll_report(fin, speed).roll_damping_nm_s

    return {
        "speed": 1.0 / max(drag_trim, 1e-9),
        "drive": ld_work,
        "hold": f_max,
        "pivot": 1.0 / max(yaw_stiffness, 1e-9),
        "release": release,
        "forgiveness": margin,
        "stability": stability,
    }


def reference_fleet() -> dict[str, FinParams]:
    """Template presets spanning the design space — the normalization basis."""
    flat = FoilParams(family=FoilFamily.FLAT_INSIDE)
    return {
        "thruster-side": FinParams(foil=flat),
        "quad-rear": FinParams(outline=OutlineParams(depth=100, base=95, sweep=36,
                                                     tip_width_ratio=0.38), foil=flat),
        "fish-keel": FinParams(outline=OutlineParams(depth=95, base=180, sweep=14,
                                                     tip_width_ratio=0.55,
                                                     le_fullness=0.9, te_shape=0.8),
                               foil=FoilParams(family=FoilFamily.FLAT_INSIDE,
                                               thickness_ratio=0.10)),
        "hi-aspect": FinParams(outline=OutlineParams(depth=130, base=90, sweep=25,
                                                     tip_width_ratio=0.3,
                                                     le_fullness=0.5,
                                                     te_shape=-0.15),
                               foil=FoilParams(family=FoilFamily.FLAT_INSIDE,
                                               thickness_ratio=0.075)),
        "gun-rake": FinParams(outline=OutlineParams(depth=128, base=112, sweep=50,
                                                    tip_width_ratio=0.2,
                                                    le_fullness=0.65,
                                                    te_shape=-0.4),
                              foil=FoilParams(family=FoilFamily.FLAT_INSIDE,
                                              thickness_ratio=0.08)),
        "longboard-single": FinParams(outline=OutlineParams(depth=240, base=160,
                                                            sweep=45,
                                                            tip_width_ratio=0.28,
                                                            le_fullness=0.7,
                                                            te_shape=-0.4),
                                      foil=FoilParams(family=FoilFamily.SYMMETRIC,
                                                      thickness_ratio=0.08)),
    }


def normalized_scores(fin: FinParams, speed: float = REF_SPEED,
                      weight_kg: float = W_REF) -> dict[str, float]:
    """0–100 per axis. The five intensive axes are rank-scaled against the
    reference fleet (clipped; a genuinely out-of-fleet fin can pin at 0 or 100);
    `hold` is requirement-relative (`hold_score`) against the rider's F_req.

    `weight_kg` defaults to W_REF, keeping this viz/back-compat entry adult-
    calibrated: drive/forgiveness use the W_REF working force and hold is scored
    against a W_REF thruster requirement, so callers that never pass a weight
    (spider_chart, test_spider) see the original adult basis on every axis."""
    fleet = [raw_scores(f, speed, weight_kg) for f in reference_fleet().values()]
    raw = raw_scores(fin, speed, weight_kg)
    f_req = required_side_force_n(anchor(weight_kg, design_speed=speed))
    import numpy as np

    out = {}
    for axis in AXES:
        if axis == "hold":
            out[axis] = hold_score(raw["hold"], f_req)
            continue
        values = np.sort([f[axis] for f in fleet])
        ranks = np.linspace(0.0, 100.0, len(values))
        out[axis] = float(np.interp(raw[axis], values, ranks))
    return out


def spider_chart(fins: dict[str, FinParams], out_png: str | Path,
                 speed: float = REF_SPEED) -> Path:
    """Dark-styled radar chart for one or more fins (T-FINS palette)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    bg, text, muted = "#0a0a0a", "#e8e8e8", "#8f8f8f"
    colors = ["#a7e0ea", "#f0a9a9", "#d8c48a", "#9fd8a7"]
    line2 = (1.0, 1.0, 1.0, 0.14)

    angles = np.linspace(0, 2 * np.pi, len(AXES), endpoint=False)
    fig, ax = plt.subplots(figsize=(6.4, 6.4), facecolor=bg,
                           subplot_kw={"projection": "polar"})
    ax.set_facecolor(bg)
    for i, (name, fin) in enumerate(fins.items()):
        scores = normalized_scores(fin, speed)
        values = [scores[a] for a in AXES]
        vals = np.concatenate((values, [values[0]]))
        angs = np.concatenate((angles, [angles[0]]))
        color = colors[i % len(colors)]
        ax.plot(angs, vals, color=color, lw=2, label=name)
        ax.fill(angs, vals, color=color, alpha=0.10)
    ax.set_xticks(angles)
    ax.set_xticklabels([a.upper() for a in AXES], color=text, fontsize=10,
                       family="monospace")
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75])
    ax.set_yticklabels(["25", "50", "75"], color=muted, fontsize=7)
    ax.grid(color=line2, linewidth=0.8)
    ax.spines["polar"].set_color(line2)
    legend = ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.12),
                       facecolor=bg, edgecolor=line2, labelcolor=text,
                       fontsize=9)
    legend.get_frame().set_linewidth(0.8)
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=120, facecolor=bg, bbox_inches="tight")
    plt.close(fig)
    return out_png
