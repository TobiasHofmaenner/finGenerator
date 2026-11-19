"""Spider axes must reproduce the fleet's surf-shop truths (tier-0 backing)."""

import pytest

from fingen.params import (
    FinParams,
    FoilFamily,
    FoilParams,
    OutlineParams,
)
from fingen.roll import roll_report
from fingen.spider import (
    AXES,
    HOLD_R_REF,
    W_REF,
    WORK_FORCE_N,
    hold_score,
    normalized_scores,
    raw_scores,
    reference_fleet,
    work_force_n,
)

# Independent literal for the audit-calibrated finite-span factor (NOT imported
# from roll.KAPPA_FS): the corrected roll damping is 0.73× the bare strip value.
KAPPA_LITERAL = 0.73


def test_fleet_scores_match_surf_intuition():
    fleet = reference_fleet()
    scores = {name: normalized_scores(fin) for name, fin in fleet.items()}
    for s in scores.values():
        assert set(s) == set(AXES)
        assert all(0.0 <= v <= 100.0 for v in s.values())
    # Keels hold and forgive (low-AR vortex lift); high-aspect blades drive.
    # Hold is requirement-relative now, but still monotone in max side force, so
    # the big keel out-holds the thin thruster side fin at the same requirement.
    assert scores["fish-keel"]["hold"] > scores["thruster-side"]["hold"]
    assert scores["fish-keel"]["forgiveness"] >= 80.0
    # Task #22 stall-drag repricing (FINDING 2+3): at the adult W_REF force
    # budget the high-aspect blade works PAST its stall knee (cl_work ≈ 0.70 ≈
    # 0.90·CL_max) and takes a separation-drag hit, while the huge longboard
    # single delivers the same 120 N loafing FAR below its own knee. So the
    # longboard now OUT-drives the hi-aspect blade for top L/D-at-force. Assert
    # the documented swap DIRECTLY — deleting `+ stall_drag_cd(...)` from
    # ld_work lifts hi-aspect back above the longboard and flips both lines —
    # and pin the hi-aspect rank-2 literal (80.0, i.e. 2nd of six fleet fins) so
    # the repricing is locked bidirectionally.
    assert scores["longboard-single"]["drive"] > scores["hi-aspect"]["drive"]
    assert scores["hi-aspect"]["drive"] == pytest.approx(80.0)
    # The raked gun releases; the compact quad-rear pivots and runs clean.
    assert scores["gun-rake"]["release"] >= 80.0
    assert scores["quad-rear"]["speed"] >= 80.0


def test_work_force_scales_with_weight():
    # The drive/forgiveness reference side force is weight-scaled: exactly 120 N
    # at W_REF (the rider-agnostic alias), linear in rider mass either side.
    # W_REF is pinned to a BARE LITERAL (mid of the 75/80 kg adult band) and the
    # off-anchor point is checked against 120·45/77.5 with 77.5 written out — NOT
    # the W_REF symbol — so a changed W_REF (e.g. 75.0) can no longer slip through
    # self-referentially.
    assert W_REF == 77.5
    assert WORK_FORCE_N == 120.0
    assert work_force_n(W_REF) == 120.0
    assert work_force_n(2.0 * W_REF) == pytest.approx(240.0)
    assert work_force_n(45.0) == pytest.approx(120.0 * 45.0 / 77.5)


def test_hold_score_is_requirement_relative():
    # Pinned at the anchor-calibrated r_ref literal: a fin exactly meeting its
    # requirement (r = f_max/F_req = 1) scores 100/(1 + r_ref) ~= 52.8, and
    # twice the required force (r = 2) ~= 69.1. Saturating in [0, 100), zero at
    # zero force, strictly monotone in headroom.
    assert HOLD_R_REF == 0.89285
    assert hold_score(100.0, 100.0) == pytest.approx(100.0 / (1.0 + HOLD_R_REF))
    assert hold_score(100.0, 100.0) == pytest.approx(52.83, abs=0.1)
    assert hold_score(200.0, 100.0) == pytest.approx(69.14, abs=0.1)
    assert hold_score(0.0, 100.0) == 0.0
    assert 0.0 < hold_score(50.0, 100.0) < hold_score(500.0, 100.0) < 100.0


def test_doubled_requirement_halves_r():
    # F_req is the denominator of r = f_max/F_req, so doubling F_req halves r at
    # fixed f_max — pinned via the exact identity hold_score(f, 2*fr) ==
    # hold_score(f/2, fr) (both sides have the same r).
    for f, fr in ((130.0, 100.0), (240.0, 90.0), (55.0, 70.0)):
        assert hold_score(f, 2.0 * fr) == pytest.approx(hold_score(f / 2.0, fr))


def test_stability_axis_present_and_kappa_corrected():
    # The seventh axis. Its raw metric is the blade's KAPPA_FS-CORRECTED roll
    # damping |L_p| (fingen.roll at the scoring speed), appended LAST so the
    # first six axes keep their radar positions.
    assert AXES == ("speed", "drive", "hold", "pivot", "release", "forgiveness",
                    "stability")
    speed = 6.4
    fin = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    rep = roll_report(fin, speed)
    raw = raw_scores(fin, speed)
    assert "stability" in raw
    # Mutation guard "KAPPA path bypassed in the fleet roll values": the raw metric
    # must be the CORRECTED damping, which is 0.73× the bare strip magnitude — NOT
    # l_p_strip. Swapping in l_p_strip fails the first equality; the second shows
    # the two genuinely differ (kappa really is applied).
    assert raw["stability"] == pytest.approx(rep.roll_damping_nm_s, rel=1e-12)
    assert rep.roll_damping_nm_s == pytest.approx(KAPPA_LITERAL * abs(rep.l_p_strip),
                                                  rel=1e-9)
    assert raw["stability"] != pytest.approx(abs(rep.l_p_strip), rel=1e-3)


def test_stability_is_fleet_ranked_and_monotone():
    # Fleet-ranked in [0, 100] like the other non-hold axes; strictly monotone in
    # |L_p|, so a deep, planted blade out-ranks a shallow, agile side fin.
    deep = FinParams(outline=OutlineParams(depth=240, base=160, sweep=45,
                                           tip_width_ratio=0.28),
                     foil=FoilParams(family=FoilFamily.SYMMETRIC))
    shallow = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    sd = normalized_scores(deep)
    ss = normalized_scores(shallow)
    for s in (sd, ss):
        assert set(s) == set(AXES)
        assert 0.0 <= s["stability"] <= 100.0
    assert sd["stability"] > ss["stability"]


# --------------------------------------------------------------------------
# Generation 3 — model defects found by the reach audit (docs/MODEL-REACH.md)
# --------------------------------------------------------------------------

def _side(**outline):
    import dataclasses

    base = FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))
    return dataclasses.replace(base, outline=dataclasses.replace(base.outline, **outline))


def test_pivot_yaw_stiffness_does_not_fall_with_rake():
    # Defect 1: the yaw arm was |x_cp - base/2| + c/4. An upright blade's CP is
    # AHEAD of its base centre and rake moves it aft, so that arm shrank with
    # rake up to ~45 deg and the axis scored a raked fin as MORE pivoty. With
    # the signed board-level arm, rake up to 45 deg can only stiffen yaw — and
    # only modestly: it is an outline detail, not a x3 lever.
    ks = [1.0 / raw_scores(_side(sweep=sw), 7.0)["pivot"] for sw in (0.0, 15.0, 30.0, 45.0)]
    assert ks == sorted(ks)
    assert 1.0 < ks[-1] / ks[0] < 1.5


def test_pivot_composition_signed_board_arm():
    # 1/pivot = q * S * CL_alpha * (L_ref + x_cp - base/2), every literal written
    # out (250 mm, quarter-chord CP). Reverting to the in-fin absolute arm fails
    # this by an order of magnitude.
    import math

    import numpy as np

    from fingen.hydro import RHO_SEAWATER, lift_curve_slope
    from fingen.outline import metrics, planform

    fin = _side()
    speed = 7.0
    z, x_le, chord = planform(fin.outline)
    x_cp = float(np.trapezoid((x_le + 0.25 * chord) * chord, z) / np.trapezoid(chord, z))
    arm_m = (250.0 + (x_cp - fin.outline.base / 2.0)) * 1e-3
    assert x_cp < fin.outline.base / 2.0            # CP ahead of the base centre
    slope, _ = lift_curve_slope(fin)
    k = 0.5 * RHO_SEAWATER * speed**2 * metrics(fin.outline).area * 1e-6 * slope * arm_m
    assert 1.0 / raw_scores(fin, speed)["pivot"] == pytest.approx(k, rel=1e-12)
    assert math.isfinite(k) and k > 0.0


def test_trim_drag_reads_the_blade_as_mounted():
    # Defect 2: every blade was read ISOLATED at +1 deg, charging a cambered side
    # fin the induced drag of a side force its toe-in exists to cancel. A blade
    # toed to its own zero-lift angle must trim exactly like a symmetric one
    # (leeway term only); any mismatch costs; symmetric blades are untouched.
    import math

    from fingen.hydro import RHO_SEAWATER, estimate, lift_curve_slope, zero_lift_alpha_deg
    from fingen.outline import metrics
    from fingen.spider import default_toe_deg, trim_drag_n

    fin, speed = _side(), 7.0
    a0 = zero_lift_alpha_deg(fin)
    assert a0 < -2.0                                 # genuinely cambered
    slope, ar_eff = lift_curve_slope(fin)
    q_s = 0.5 * RHO_SEAWATER * speed**2 * metrics(fin.outline).area * 1e-6
    cf = 0.074 / estimate(fin, speed, 0.0).reynolds ** 0.2
    t = fin.foil.thickness_ratio
    cd0 = 1.10 * 2.0 * cf * (1.0 + 2.0 * t + 60.0 * t**4)
    leeway_only = (slope * math.radians(1.0)) ** 2 / (math.pi * 0.90 * ar_eff)
    matched = trim_drag_n(fin, speed, toe_deg=-a0)
    assert matched == pytest.approx(q_s * (cd0 + leeway_only), rel=1e-9)
    assert trim_drag_n(fin, speed, toe_deg=-a0 + 2.0) > matched
    assert trim_drag_n(fin, speed, toe_deg=-a0 - 2.0) > matched
    assert trim_drag_n(fin, speed, toe_deg=0.0) > 1.2 * matched   # the old reading
    assert default_toe_deg(fin) == 3.5 and default_toe_deg(FinParams()) == 0.0
    assert 1.0 / raw_scores(fin, speed)["speed"] == pytest.approx(trim_drag_n(fin, speed, 3.5))
