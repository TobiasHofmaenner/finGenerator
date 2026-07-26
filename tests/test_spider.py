"""Spider axes must reproduce the fleet's surf-shop truths (tier-0 backing)."""

import pytest

from fingen.spider import (
    AXES,
    HOLD_R_REF,
    W_REF,
    WORK_FORCE_N,
    hold_score,
    normalized_scores,
    reference_fleet,
    work_force_n,
)


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
    assert scores["hi-aspect"]["drive"] == max(s["drive"] for s in scores.values())
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
