"""The anchor: absolute rider-derived requirements (docs/PHYSICS.md §9).

The spiderweb (fingen.spider) is a NORMALIZED objective — character and
tradeoffs. Alone it is under-constrained: an optimizer could inflate area to
buy hold or shave the fin to a razor to buy speed. This module produces the
ABSOLUTE layer that must be answered first: how much force the fin must
deliver (rider mass × turn intensity, coordinated-turn closure [SH-turn,
ShormISEA20]), at what speeds [Forsyth24], and what that implies as hard
boundaries — an area corridor, a structural thickness floor for the chosen
print material ([PETCF, PAHTCF] with print-anisotropy knockdown [Fis23]),
and mounting minima. Optimization then runs INSIDE these constraints.

Named assumption constants are deliberate and documented — each is the
honest, citable state of knowledge, and each is a calibration target for
the CFD/field-data stages.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np

from fingen.foil import section_points
from fingen.hydro import RHO_SEAWATER, lift_curve_slope, stall_alpha_deg
from fingen.outline import metrics
from fingen.params import FinConfig, FinParams, TabSystem

G = 9.81
BOARD_MASS_KG = 3.0  # printed-fin-era shortboard ballpark

# PEAK vs SUSTAINED: measured peaks (~300 N on 0.015 m² at 4 m/s [Knies25])
# imply CL ≈ 2.4 — far beyond attached-flow limits. Peaks are transient
# events (speed spikes, dynamic-stall overshoot) and size the STRUCTURE;
# steady hydrodynamics is sized by the sustained carving load.
# Fin share of total lateral force, and the dominant fin's share of that
# per arrangement: a single carries everything, a thruster's outside front
# dominates [Falk19], quads spread across front+rear [Falk20].
FIN_FORCE_SHARE = 0.6
CONFIG_DOMINANT_SHARE = {
    FinConfig.SINGLE: 1.0,
    FinConfig.TWIN: 0.75,
    FinConfig.THRUSTER: 0.6,
    FinConfig.QUAD: 0.45,
    FinConfig.TWO_PLUS_ONE: 0.65,
}
# Sustained per-fin working force as a fraction of system weight, calibrated
# so a 75 kg intermediate lands on the known-good ~8000 mm² fleet medium
# (cross-check: peak/sustained ≈ 3, consistent with peaks near a third of
# body weight [Knies25]).
SUSTAINED_WEIGHT_FRACTION = 0.103

# Usable lift ceiling for sizing (below the break, pre-margin) and the
# sizing safety factor applied to the sustained requirement.
CL_USABLE = 0.65
FORCE_SF = 1.3

# Material design allowables: ISO-178 XY bending strength times a 0.5
# print/layup knockdown [Fis23], over a structural SF of 2. The strength
# literals ARE the datasheet XY bending strengths carried as
# MaterialCard.strength_xy_mpa in fingen.materials (kept in sync there).
#   pet-cf = Polymaker Fiberon PET-CF17 [FibPET26], XY bending strength
#     109.3 MPa (annealed coupon; the 0.5 knockdown covers the as-printed
#     reality). 109.3·0.5/2 = 27.325 MPa — this REPLACES the former Bambu-PET
#     value 32.75 (from 131 MPa): a −16.6% move on switching to the user's
#     actual filament, past the 10% threshold, so re-derived here in step.
#   paht-cf = Elegoo PAHT-CF (PA12-CF, approximated card [ELPAHT26]). The user's
#     filament: Elegoo dry XY flexural strength 138 MPa, wet-derated ~0.85 for
#     PA12 conditioning [3DXPA] -> ~117 MPa; 117·0.5/2 = 29.3 MPa — within ~6%
#     of the retained 31.25 (the Bambu-analog 125·0.5/2), inside the 10% band
#     and well inside the approximation's own ±20-30%, so KEPT as-is (literal
#     stays 125·0.5/2). Test E/G on the real filament is decision-grade.
#     (Default fin sits far under both: base stress ~13 MPa at peak.)
_MATERIAL_ALLOW_MPA = {"pet-cf": 109.3 * 0.5 / 2.0, "paht-cf": 125.0 * 0.5 / 2.0}

# Spanwise center of pressure for the bending arm (fraction of depth) —
# consistent with the measured tip-first loading fin [BW04].
CP_SPAN_FRACTION = 0.45

# Tab-neck stress-concentration factor at the tab-to-blade fillet junction.
# 2.5 is a representative filleted-shoulder value from the stress-concentration
# charts [Roa01] (the Peterson family): printed tabs carry a small root radius,
# so tier-0 takes the mid filleted value rather than a sharp-corner K_t of 3+
# or the unity of a generous radius. Calibration target for the load-cell rig.
KT_TAB = 2.5
# Structural tab geometry (mm), transcribed from docs/TAB-SYSTEMS.md and the
# nominal constants fingen.tabs lofts (_DUAL_DEPTH / _CLICK_DEPTH = 14 mm,
# _SINGLE_DEPTH_SIDE = 17.5 mm). Each entry: (insertion depth below the base
# plane, per-tab fused neck lengths). The blade root SIDE-BENDING moment is
# reacted PER TAB as a bearing couple over the insertion DEPTH (see
# tab_neck_stress_mpa for the free-body); the root shear splits over the tabs;
# the shortest-neck tab sets the stress. Tier-0 — the exact box-engagement
# reaction (clamp screw preload, sidewall friction, base bearing) is a
# bench/tier-1 refinement. The fin's TabParams do NOT parameterize these
# (x_offset only slides the set; fit_offset/tab_depth change thickness/insertion,
# not the neck couple), so the nominal geometry is used; the blade thickness at
# the base IS fin-specific.
#   DUAL_TAB : two 20 mm tabs, 14 mm insertion depth [FCS-compatible].
#   CLICK_TAB: 45 + 33 mm tabs, 14 mm insertion depth [FCS II].
# SINGLE_TAB is handled in the function (its length tracks the base; the Futures
# 3/4" side-box channel is _SINGLE_TAB_DEPTH deep).
_TAB_NECK_GEOM = {
    TabSystem.DUAL_TAB: (14.0, (20.0, 20.0)),
    TabSystem.CLICK_TAB: (14.0, (45.0, 33.0)),
}
_SINGLE_TAB_DEPTH = 17.5


def tab_neck_stress_mpa(fin: FinParams, moment_nm: float, shear_n: float
                        ) -> float | None:
    """Peak tab-neck stress (MPa) under a root bending `moment_nm` and root
    `shear_n`, or None when the fin carries no tabs (TabSystem.NONE / glass-on
    — the gate is then inactive). The worst (highest-stress) tab is returned
    (docs/TAB-SYSTEMS.md; [Roa01]).

    REACTION MODEL (corrected in the bundle-2 physics pass). The root load is a
    SIDE-BENDING moment about the CHORDWISE (fore-aft) axis plus a lateral shear.
    A moment about the fore-aft axis is reacted by forces separated in the
    SPANWISE direction — i.e. over the tab's INSERTION DEPTH into the box — NOT
    by the tabs' chordwise spacing. (A lateral-force couple separated chordwise
    reacts YAW/torsion about the spanwise axis, a different load; flex.py exports
    no torsion moment to this gate — FlexReport carries only the bending moment
    and shear — so the chordwise spacing lever is dropped entirely here.)

    Bearing-couple lever = (2/3)·depth. Free-body: treat each rigid tab as
    rotating with the base about the base plane; the tab tip interferes with the
    slot wall by an amount growing linearly with depth, so the bearing pressure
    is TRIANGULAR — zero at the base plane, peak at the tab tip. Its resultant
    R acts at the centroid of that triangle, 2/3 of the depth below the base
    plane, and forms a couple with the counter-bearing at the base-plane edge:
        M_tab = R · (2/3)·d   =>   R = M_tab / ((2/3)·d).
    The side-bending moment is shared EQUALLY across the (equal-depth) tabs, so
    M_tab = moment_nm / n_tabs (a conservative tier-0 split for the shortest
    tab: a stiffness-proportional split would give the shorter neck a smaller
    share — a tier-1 refinement). The shear splits equally too. Each tab's fused
    neck (chordwise length × blade thickness at the base) carries R_couple +
    R_shear, and the fillet factor KT_TAB amplifies it.
    """
    system = fin.tabs.system
    if system is TabSystem.NONE:
        return None
    # Blade thickness at the base station = t/c · base (the tab's actual fused
    # thickness envelope; foil truncation is a sub-mm second order here).
    t_base_m = fin.foil.thickness_ratio * fin.outline.base * 1e-3
    if system is TabSystem.SINGLE_TAB:
        # Futures-style full-base tab: one neck whose chordwise length tracks the
        # base; the side-bending moment is reacted over the box channel depth.
        length_mm = min(fin.outline.base - 12.0, 110.0)
        depth_mm = _SINGLE_TAB_DEPTH
        necks_m = (length_mm * 1e-3,)
    else:
        depth_mm, necks_mm = _TAB_NECK_GEOM[system]
        necks_m = tuple(n * 1e-3 for n in necks_mm)
    n_tabs = len(necks_m)
    lever_m = (2.0 / 3.0) * depth_mm * 1e-3  # triangular-bearing effective lever
    r_couple = (moment_nm / n_tabs) / max(lever_m, 1e-6)  # per-tab couple (N)
    r_shear = shear_n / n_tabs  # shear share per tab (N)
    peak = 0.0
    for neck_m in necks_m:
        area = neck_m * t_base_m  # fused neck footprint (m²)
        sigma = KT_TAB * (r_couple + r_shear) / max(area, 1e-12) / 1e6
        peak = max(peak, sigma)
    return peak


class Skill(Enum):
    """Turn intensity via design bank angle; durations per [ShormISEA20]."""

    CRUISER = 30.0  # relaxed arcs
    INTERMEDIATE = 40.0
    ADVANCED = 48.0
    PRO = 55.0


@dataclass(frozen=True)
class AnchorSheet:
    """Absolute requirements — the constraint set the optimizer runs inside."""

    total_mass_kg: float
    design_speed: float  # m/s
    force_peak_n: float  # per dominant fin, incl. safety factor
    force_work_n: float  # sustained working load (spider's reference force)
    area_min_mm2: float
    area_max_mm2: float
    base_min_mm: float  # from the mounting system
    material: str
    allow_mpa: float


def anchor(rider_mass_kg: float, skill: Skill = Skill.INTERMEDIATE,
           design_speed: float = 6.4, config: FinConfig = FinConfig.THRUSTER,
           material: str = "pet-cf",
           tabs: TabSystem = TabSystem.NONE) -> AnchorSheet:
    """Answer the absolute questions first (design_speed default: measured
    mean riding speed [Forsyth24])."""
    if material not in _MATERIAL_ALLOW_MPA:
        raise ValueError(f"material {material!r} not in {sorted(_MATERIAL_ALLOW_MPA)}")
    m_total = rider_mass_kg + BOARD_MASS_KG
    f_lateral = m_total * G * math.tan(math.radians(skill.value))
    share = CONFIG_DOMINANT_SHARE[config]
    # Transient peak (structure sizing): coordinated-turn closure, physical.
    f_peak = f_lateral * FIN_FORCE_SHARE * share
    # Sustained working load (hydrodynamic sizing): weight-anchored; the
    # calibration constant is defined at the thruster share (0.6).
    f_work = SUSTAINED_WEIGHT_FRACTION * m_total * G * share / 0.6

    q = 0.5 * RHO_SEAWATER * design_speed**2
    area_min = f_work * FORCE_SF / (q * CL_USABLE) * 1e6  # mm²
    area_max = 2.0 * area_min  # over-finned ceiling — heuristic, CFD-calibrated later

    base_min = {TabSystem.NONE: 0.0, TabSystem.DUAL_TAB: 80.0,
                TabSystem.SINGLE_TAB: 62.0, TabSystem.CLICK_TAB: 104.0}[tabs]
    return AnchorSheet(
        total_mass_kg=m_total,
        design_speed=design_speed,
        force_peak_n=f_peak,
        force_work_n=f_work,
        area_min_mm2=area_min,
        area_max_mm2=area_max,
        base_min_mm=base_min,
        material=material,
        allow_mpa=_MATERIAL_ALLOW_MPA[material],
    )


def required_side_force_n(sheet: AnchorSheet) -> float:
    """F_req: the steady side force the fin must deliver — the sustained working
    load with the sizing safety factor. THE single definition of that threshold:
    the capacity gate (check_anchor / optimize.evaluate) screens against it, and
    the spider hold axis measures a fin's side-force headroom relative to it
    (fingen.spider.hold_score). One constant, no duplicated literals."""
    return sheet.force_work_n * FORCE_SF


def base_bending_stress_mpa(fin: FinParams, force_n: float) -> float:
    """Bending stress at the base section under the peak load applied at the
    spanwise CP — Euler-Bernoulli with the section modulus integrated
    numerically from the true foil section [GT97]."""
    arm_m = CP_SPAN_FRACTION * fin.outline.depth * 1e-3
    moment = force_n * arm_m  # N·m
    upper, lower = section_points(fin.foil, fin.outline.base, n_points=160)
    xs = upper[:, 0] * 1e-3
    y_up = upper[:, 1] * 1e-3
    y_lo = np.interp(upper[:, 0], lower[:, 0], lower[:, 1]) * 1e-3
    # Neutral axis and second moment about it (thin-strip integration).
    a_strip = y_up - y_lo
    area = float(np.trapezoid(a_strip, xs))
    y_bar = float(np.trapezoid(0.5 * (y_up + y_lo) * a_strip, xs) / max(area, 1e-12))
    i_zz = float(np.trapezoid(((y_up - y_bar) ** 3 - (y_lo - y_bar) ** 3) / 3.0, xs))
    y_max = float(max(abs(y_up - y_bar).max(), abs(y_lo - y_bar).max()))
    return moment * y_max / max(i_zz, 1e-15) / 1e6


def check_anchor(fin: FinParams, sheet: AnchorSheet) -> list[str]:
    """Constraint violations for a candidate fin (empty list = feasible).
    This is the optimizer's hard gate; the spiderweb is its objective."""
    issues = []
    m = metrics(fin.outline)
    if m.area < sheet.area_min_mm2:
        issues.append(f"area {m.area:.0f} mm² below anchor minimum "
                      f"{sheet.area_min_mm2:.0f} mm² (cannot sustain "
                      f"{sheet.force_work_n:.0f} N below the break)")
    if m.area > sheet.area_max_mm2:
        issues.append(f"area {m.area:.0f} mm² above anchor ceiling "
                      f"{sheet.area_max_mm2:.0f} mm² (over-finned)")
    slope, ar_eff = lift_curve_slope(fin)
    q = 0.5 * RHO_SEAWATER * sheet.design_speed**2
    f_capacity = (q * m.area * 1e-6 * slope
                  * math.radians(stall_alpha_deg(ar_eff)))
    f_req = required_side_force_n(sheet)
    if f_capacity < f_req:
        issues.append(f"steady side-force capacity {f_capacity:.0f} N below "
                      f"the sustained requirement {f_req:.0f} N")
    stress = base_bending_stress_mpa(fin, sheet.force_peak_n)
    if stress > sheet.allow_mpa:
        issues.append(f"base bending stress {stress:.0f} MPa exceeds "
                      f"{sheet.material} allowable {sheet.allow_mpa:.0f} MPa "
                      "(thicken the section or widen the base)")
    if fin.outline.base < sheet.base_min_mm:
        issues.append(f"base {fin.outline.base:.0f} mm below the mounting "
                      f"system minimum {sheet.base_min_mm:.0f} mm")
    return issues
