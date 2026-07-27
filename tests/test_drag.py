"""Tier-0 drag upgrade (task #22): Re-aware cd0 + post-knee stall drag.

Two changes, both calibrated ONCE against the 2026 transition-tier CFD and
pinned here with INDEPENDENT literals (no symbol borrowed from the module it
checks), so a mutation to the calibration cannot slip through self-referentially:

  1. CD0_CAL = 1.10 profile-drag bump (bench/freerun-thinfoil §"task #22").
  2. K_STALL·max(0, CL - 0.7·CL_max)² post-knee rise, fit on the needle polar
     (bench/freerun-needle/needle-polar.json), cross-checked bw04/zarruk.

The killer is `test_needle_bench_replication`: it loads the committed CFD JSON
and asserts the NEW tier-0 CD tracks it at α 12/14 (was 1.8-2.3× off before).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from fingen.hydro import (
    K_STALL,
    KNEE_FRACTION,
    RHO_SEAWATER,
    SPAN_EFFICIENCY,
    STALL_ALPHA_DEG,
    estimate,
    lift_curve_slope,
    stall_alpha_deg,
    stall_cl_knee,
    stall_drag_cd,
)
from fingen.outline import metrics
from fingen.params import FinParams
from fingen.spider import (
    CD0_CAL,
    REF_SPEED,
    W_REF,
    _cd0,
    raw_scores,
    reference_fleet,
    work_force_n,
)

# --- Needle tier-0 constants as BARE, independent literals (adjudication.md,
# k=1.7 optimizer basis). Not imported from any needle object — the fixture is
# the paper, so a code change cannot move the target with itself. -----------
NEEDLE_SLOPE = 3.670          # /rad, DATCOM @ k=1.7
NEEDLE_AR_EFF = 4.522         # 1.7 · AR_geo 2.66
NEEDLE_BREAK_DEG = 12.0       # stall_alpha_deg(4.522) = 12 (independent value)
NEEDLE_CD0_HOERNER = 0.01334  # thinfoil table
NEEDLE_POLAR = (Path(__file__).resolve().parents[1]
                / "bench" / "freerun-needle" / "needle-polar.json")


def _cdi(cl: float, ar_eff: float, e: float = 0.90) -> float:
    return cl * cl / (math.pi * e * ar_eff)


# --------------------------------------------------------------------------
# 1. Bare-literal calibration pins
# --------------------------------------------------------------------------

def test_calibration_literals_are_bare():
    # Mutating any of these fails immediately; each is the documented value.
    assert CD0_CAL == 1.10
    assert K_STALL == 0.580
    assert KNEE_FRACTION == 0.7


def test_cd0_is_1p10_times_hoerner():
    # Below-knee CD is unchanged vs the OLD formula EXCEPT the 1.10 factor:
    # recompute the pre-#22 Hoerner cd0 with independent arithmetic and assert
    # _cd0 is exactly 1.10× it. Dropping CD0_CAL to 1.0 fails here.
    fin = FinParams()
    speed = 7.0
    from fingen.hydro import estimate
    est = estimate(fin, speed, 0.0)
    cf = 0.074 / est.reynolds**0.2
    t = fin.foil.thickness_ratio
    old_cd0 = 2.0 * cf * (1.0 + 2.0 * t + 60.0 * t**4)   # pre-#22 formula
    assert _cd0(fin, speed) == pytest.approx(1.10 * old_cd0, rel=1e-12)


# --------------------------------------------------------------------------
# 2. Stall-drag term: hand-computed CD, knee placement, below-knee, C1
# --------------------------------------------------------------------------

def test_stall_drag_hand_computed_supra_knee():
    # Independent hand arithmetic at one supra-knee CL. Halving/dropping K_STALL
    # or moving the knee fraction all break this equality.
    cl_max = 3.670 * math.radians(12.0)      # 0.7686430 (independent)
    cl_knee = 0.7 * cl_max                    # 0.5380501
    cl = 0.90
    expected = 0.580 * (cl - cl_knee) ** 2    # 0.0759845
    assert cl_knee == pytest.approx(0.5380501, abs=1e-6)
    assert expected == pytest.approx(0.0759845, abs=1e-6)
    assert stall_cl_knee(NEEDLE_SLOPE, NEEDLE_AR_EFF) == pytest.approx(cl_knee, rel=1e-9)
    assert stall_drag_cd(cl, NEEDLE_SLOPE, NEEDLE_AR_EFF) == pytest.approx(expected, rel=1e-9)


def test_no_stall_drag_below_knee():
    # Below the knee the term is exactly zero — applying K·(CL-CL_knee)² there
    # too (dropping the max(0,·) clamp) would give a positive value and fail.
    cl_knee = stall_cl_knee(NEEDLE_SLOPE, NEEDLE_AR_EFF)
    cl_below = 0.40
    assert cl_below < cl_knee
    assert stall_drag_cd(cl_below, NEEDLE_SLOPE, NEEDLE_AR_EFF) == 0.0
    # And a naive un-clamped term would have been clearly nonzero here:
    assert 0.580 * (cl_below - cl_knee) ** 2 > 1e-3


def test_knee_at_0p7_not_0p9_of_clmax():
    # A CL at 0.8·CL_max is ABOVE the 0.7 knee but BELOW a 0.9·CL_max knee:
    # the stall term must be active here. Moving the knee to 0.9 zeros it → fail.
    cl_max = NEEDLE_SLOPE * math.radians(stall_alpha_deg(NEEDLE_AR_EFF))
    assert stall_drag_cd(0.80 * cl_max, NEEDLE_SLOPE, NEEDLE_AR_EFF) > 0.0
    assert stall_drag_cd(0.65 * cl_max, NEEDLE_SLOPE, NEEDLE_AR_EFF) == 0.0


def test_total_cd_is_c1_continuous_at_knee():
    # Total CD = cd0 + cdi(CL) + stall(CL). cdi is C∞; the stall term is C1 at
    # the knee BY CONSTRUCTION — value AND slope both vanish as CL → CL_knee⁺,
    # and it is identically 0 below — so total CD and dCD/dCL are continuous.
    cd0 = 1.10 * NEEDLE_CD0_HOERNER
    knee = stall_cl_knee(NEEDLE_SLOPE, NEEDLE_AR_EFF)
    h = 1e-6

    def stall(cl: float) -> float:
        return stall_drag_cd(cl, NEEDLE_SLOPE, NEEDLE_AR_EFF)

    def total(cl: float) -> float:
        return cd0 + _cdi(cl, NEEDLE_AR_EFF, SPAN_EFFICIENCY) + stall(cl)

    # Stall-term VALUE continuity at the knee: 0 below, → 0 above.
    assert stall(knee - h) == 0.0
    assert stall(knee) == 0.0
    assert stall(knee + h) == pytest.approx(0.580 * h * h, rel=1e-6)
    # Stall-term SLOPE continuity: 0 below, → 0 above (forward diffs either side).
    assert (stall(knee) - stall(knee - h)) / h == 0.0
    assert (stall(knee + h) - stall(knee)) / h == pytest.approx(0.0, abs=1e-5)
    # Hence TOTAL dCD/dCL matches across the knee (only the smooth cdi slope
    # survives there): left and right finite-difference slopes agree.
    d_lo = (total(knee) - total(knee - h)) / h
    d_hi = (total(knee + h) - total(knee)) / h
    assert d_lo == pytest.approx(d_hi, abs=1e-3)
    assert d_lo == pytest.approx(2.0 * knee / (math.pi * SPAN_EFFICIENCY * NEEDLE_AR_EFF),
                                 abs=1e-3)


def test_below_knee_total_unchanged_except_cal():
    # Pin one below-knee point: NEW total = 1.10·Hoerner + cdi, with NO stall
    # term. Compare to the OLD formula (Hoerner + cdi) — the only change is ×1.10.
    fin = FinParams()
    speed = 7.0
    from fingen.hydro import estimate, lift_curve_slope
    slope, ar_eff = lift_curve_slope(fin)
    est = estimate(fin, speed, 1.0)          # α=1°, far below any knee
    assert est.cl < stall_cl_knee(slope, ar_eff)
    cf = 0.074 / estimate(fin, speed, 0.0).reynolds**0.2
    t = fin.foil.thickness_ratio
    old_cd0 = 2.0 * cf * (1.0 + 2.0 * t + 60.0 * t**4)
    new_total = _cd0(fin, speed) + est.cdi \
        + stall_drag_cd(est.cl, slope, ar_eff)
    old_total = old_cd0 + est.cdi
    assert stall_drag_cd(est.cl, slope, ar_eff) == 0.0
    assert new_total == pytest.approx(1.10 * old_cd0 + est.cdi, rel=1e-12)
    assert new_total / old_total == pytest.approx(
        (1.10 * old_cd0 + est.cdi) / old_total, rel=1e-12)


# --------------------------------------------------------------------------
# 3. Bench replication — the killer (fast: reads committed JSON, no CFD)
# --------------------------------------------------------------------------

def test_needle_bench_replication():
    # Load the needle transition-CFD polar and assert the NEW tier-0 CD lands
    # within ±30 % of the CFD at α 12 and 14 — the points that were 1.8-2.3×
    # (k=2 basis) off BEFORE the stall term. This pins K_STALL to the data it
    # claims to match: gut K_STALL and these α blow past the band.
    rows = {r["alpha"]: r for r in json.loads(NEEDLE_POLAR.read_text())}
    cd0 = CD0_CAL * NEEDLE_CD0_HOERNER
    for alpha in (12.0, 14.0):
        cl = rows[alpha]["cl"]
        cd_cfd = rows[alpha]["cd"]
        cd_model = cd0 + _cdi(cl, NEEDLE_AR_EFF) \
            + stall_drag_cd(cl, NEEDLE_SLOPE, NEEDLE_AR_EFF)
        assert cd_model == pytest.approx(cd_cfd, rel=0.30), (
            f"α={alpha}: model {cd_model:.5f} vs CFD {cd_cfd:.5f}")

    # Sanity: the OLD attached-only model (no CD0_CAL, no stall) badly
    # under-predicts at α=14 — proving the stall term is what closes the gap.
    cl14 = rows[14.0]["cl"]
    old = NEEDLE_CD0_HOERNER + _cdi(cl14, NEEDLE_AR_EFF)
    assert rows[14.0]["cd"] / old > 1.8


def test_stall_term_off_in_attached_range():
    # The stall term must be OFF at the deep-attached α=2 point (CL well below
    # the knee): the speed axis (trim, α=1) inherits only the +10 % cd0 bump.
    rows = {r["alpha"]: r for r in json.loads(NEEDLE_POLAR.read_text())}
    assert stall_drag_cd(rows[2.0]["cl"], NEEDLE_SLOPE, NEEDLE_AR_EFF) == 0.0


# --------------------------------------------------------------------------
# 4. raw_scores COMPOSITION pins (FINDING 4) — the drag axes are assembled
#    from cd0 + cdi + stall by hand and matched to what spider.raw_scores
#    returns, with every literal written out. These kill: CD0_CAL applied a
#    second time at either site, the stall term dropped from either site, and
#    the cdi term dropped — mutations that otherwise pass the whole suite
#    because the pieces are never composed against an independent expectation.
# --------------------------------------------------------------------------

def test_raw_scores_speed_composition():
    # Hand-compose the trim drag from its parts and match 1/raw["speed"].
    #   drag_trim = q·area·(1.10·2·cf·FF + cdi + stall),  cf = 0.074/Re^0.2
    # CD0_CAL is written as the bare 1.10 and applied EXACTLY ONCE, so a second
    # application at the site doubles spider's drag and breaks the equality;
    # dropping cdi drops a large term and breaks it too.
    fin = FinParams()
    speed = REF_SPEED
    m = metrics(fin.outline)
    area_m2 = m.area * 1e-6
    q = 0.5 * RHO_SEAWATER * speed ** 2
    slope, ar_eff = lift_curve_slope(fin)
    est0 = estimate(fin, speed, 0.0)
    est1 = estimate(fin, speed, 1.0)         # trim, α = 1°
    cf = 0.074 / est0.reynolds ** 0.2
    t = fin.foil.thickness_ratio
    form = 1.0 + 2.0 * t + 60.0 * t ** 4
    cd0 = 1.10 * 2.0 * cf * form             # 1.10 written out, applied ONCE
    stall = stall_drag_cd(est1.cl, slope, ar_eff)
    assert stall == 0.0                       # trim sits far below any knee
    drag_trim = q * area_m2 * (cd0 + est1.cdi + stall)
    raw = raw_scores(fin, speed, W_REF)
    assert 1.0 / raw["speed"] == pytest.approx(drag_trim, rel=1e-12)


def test_raw_scores_drive_composition_supra_knee():
    # Hand-compose ld_work for a fin whose CL_work is ABOVE the stall knee, so
    # every term (cd0, cdi_work, stall) participates. hi-aspect at the adult
    # W_REF budget works past its knee (see test_fleet_scores). This kills:
    # stall dropped from ld_work, cdi dropped from ld_work, CD0_CAL doubled.
    fin = reference_fleet()["hi-aspect"]
    speed = REF_SPEED
    weight = W_REF
    m = metrics(fin.outline)
    area_m2 = m.area * 1e-6
    q = 0.5 * RHO_SEAWATER * speed ** 2
    slope, ar_eff = lift_curve_slope(fin)
    a_break = stall_alpha_deg(ar_eff)
    cf = 0.074 / estimate(fin, speed, 0.0).reynolds ** 0.2
    t = fin.foil.thickness_ratio
    cd0 = 1.10 * 2.0 * cf * (1.0 + 2.0 * t + 60.0 * t ** 4)
    cl_work = min(work_force_n(weight) / (q * area_m2),
                  0.95 * slope * math.radians(a_break))
    assert cl_work > stall_cl_knee(slope, ar_eff)      # genuinely supra-knee
    cdi_work = cl_work ** 2 / (math.pi * 0.9 * ar_eff)
    stall = stall_drag_cd(cl_work, slope, ar_eff)
    assert stall > 0.0                                  # the term is active
    ld_work = cl_work / (cd0 + cdi_work + stall)
    raw = raw_scores(fin, speed, weight)
    assert raw["drive"] == pytest.approx(ld_work, rel=1e-12)


# --------------------------------------------------------------------------
# 5. Knee CAP (FINDING 1) — the DRAG knee angle is capped at the 12° base even
#    though the LIFT break extends at low AR. Pinned with independent literals
#    for a sub-2.5-AR_eff blade; reverting stall_cl_knee to the uncapped
#    stall_alpha_deg raises the knee and fails this test.
# --------------------------------------------------------------------------

def test_stall_knee_capped_at_base_for_low_ar():
    ar_eff = 1.90           # a pancake: sub-2.5 AR_eff (the exploit regime)
    slope = 3.40            # arbitrary independent slope literal
    # The LIFT break still extends (vortex lift): 12 + 8·(2.5 − 1.90) = 16.8°.
    assert stall_alpha_deg(ar_eff) == pytest.approx(16.8, abs=1e-9)
    assert STALL_ALPHA_DEG == 12.0
    # The DRAG knee, however, is pinned to the 12° base, NOT 16.8°.
    knee_capped = 0.7 * slope * math.radians(12.0)          # independent literal
    knee_uncapped = 0.7 * slope * math.radians(16.8)        # the removed windfall
    assert stall_cl_knee(slope, ar_eff) == pytest.approx(knee_capped, rel=1e-12)
    assert knee_uncapped > 1.35 * knee_capped               # a real gap to catch
    assert stall_cl_knee(slope, ar_eff) != pytest.approx(knee_uncapped, rel=1e-3)
    # And at a CL between the two knees the capped model already charges stall
    # drag while the uncapped one would still read zero — the exploit in one line.
    cl_between = 0.5 * (knee_capped + knee_uncapped)
    assert stall_drag_cd(cl_between, slope, ar_eff) > 0.0
