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
# The aft/CENTER member's share, for the configs whose center is co-designed.
# The rear fin carries LESS than the dominant front: the measured Falk split
# puts it at (1 − rear deficit) of the loaded front at working leeway, so
# 0.6 · (1 − 0.26) ≈ 0.45. Sizing the center against the DOMINANT share would
# demand it out-produce the front through the same downwash — systematically
# oversizing it. Load allocation (this share) and in-situ capability (the
# interference derate on produced force, optimize.evaluate) are DIFFERENT
# terms and both apply: capacity_isolated · env ≥ share_center · F_total.
CONFIG_CENTER_SHARE = {
    FinConfig.THRUSTER: 0.45,
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

# Material design allowables: datasheet strength, moisture-conditioned, times an
# ORIENTATION-DEPENDENT as-printed knockdown, over a structural SF of 2.
#
# WHY ORIENTATION-DEPENDENT. The old blanket 0.5 was, in effect, the material's
# own Z/XY anisotropy ratio (the card's 67/138 = 0.49) — so applying it to an
# X-Y strength double-counted anisotropy on a part deliberately printed FLAT so
# that its bending tension runs IN-PLANE (see scripts/export_martina_set.py:
# layer planes parallel to the blade faces). Measured 4x4 mm as-printed Elegoo
# PAHT-CF coupons [ELPAHT-COUPON]: 121.8 kgf X-Y and 19.0 kgf Z, i.e.
#   X-Y 74.7 MPa tensile = 0.86 of Elegoo's published 87 MPa tensile
#   Z    11.7 MPa tensile -> Z/XY = 0.156, THREE TIMES worse than the card's
#                            analogy-derived 0.49 assumption
# So in-plane loading loses ~15% to as-printed reality, not 50%; through-layer
# loading loses ~84%. Both directions of that correction matter: the first
# unblocks the mounting gate, the second says printing a fin UPRIGHT would be
# far more dangerous than the model previously believed.
#
# These are single-source coupon numbers, not yet a controlled series — Test E/G
# (docs/BENCH-PROTOCOL.md), printed in the fin's own orientation, is what makes
# them decision-grade. Rounded DOWN from the measurement for that reason.
PRINT_KNOCKDOWN_INPLANE = 0.85       # X-Y: load within the layer plane
PRINT_KNOCKDOWN_INTERLAMINAR = 0.16  # Z: load across layer boundaries
STRUCTURAL_SF = 2.0
#   pet-cf = Polymaker Fiberon PET-CF17 [FibPET26], X-Y bending strength 109.3
#     MPa (annealed coupon).
#   paht-cf = Elegoo PAHT-CF (PA12-CF) [ELPAHT26]: X-Y flexural 138 MPa, times
#     the 0.85 PA12 wet retention [3DXPA] -> 117 MPa conditioned. (The former
#     125 MPa was the Bambu analog's ANNEALED coupon — a strength this filament
#     does not have as printed.)
# NOTE the allowable below assumes the FLAT print orientation the exporter
# enforces. A blade printed upright carries its root tension ACROSS layers and
# must use PRINT_KNOCKDOWN_INTERLAMINAR instead — a ~5x lower allowable.
# In-service moisture factor on STRENGTH, per material. PA12 absorbs water and
# softens (0.85 retention [3DXPA]); PET-CF's equilibrium uptake is ~0.53% so it
# is carried dry. Derived from the CARD rather than re-typed here: a literal
# would silently drift the day a measured card is registered.
_MOISTURE_RETENTION = {"pet-cf": 1.0, "paht-cf": 0.85}


def _design_allowable_mpa(material: str) -> float:
    """Design allowable = card X-Y strength · moisture · in-plane as-printed
    knockdown / structural SF. See the block comment above for why the knockdown
    is orientation-specific."""
    from fingen.materials import get_card

    card = get_card(material)
    return (card.strength_xy_mpa * _MOISTURE_RETENTION.get(material, 1.0)
            * PRINT_KNOCKDOWN_INPLANE / STRUCTURAL_SF)


_MATERIAL_ALLOW_MPA = {m: _design_allowable_mpa(m)
                       for m in ("pet-cf", "paht-cf")}

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
# nominal constants fingen.tabs lofts. Each entry: (insertion depth below the
# base plane, per-tab CHORDWISE lengths). The lengths set the tabs' combined
# section modulus at the base plane, which is what carries the root moment (see
# tab_neck_stress_mpa). The depth is retained for reference — it does NOT enter
# the base-plane section; the retired bearing-couple model used it as a lever
# and that was the bug. Tier-0: the box's own reaction distribution (cam-screw
# preload, sidewall friction, base bearing) is a bench/tier-1 refinement.
#   DUAL_TAB : two 20 mm tabs, 14 mm insertion depth [FCS-compatible].
#   CLICK_TAB: 45 + 33 mm tabs, 14 mm insertion depth [FCS II].
# SINGLE_TAB is handled in the function (its length tracks the base; the Futures
# 3/4" side-box channel is _SINGLE_TAB_DEPTH deep).
_TAB_NECK_GEOM = {
    TabSystem.DUAL_TAB: (14.0, (20.0, 20.0)),
    TabSystem.CLICK_TAB: (14.0, (45.0, 33.0)),
}
_SINGLE_TAB_DEPTH = 17.5
# Tab THICKNESSES as lofted by fingen.tabs (kept in sync with the literals
# there: _DUAL_THICK / _CLICK_THICK / _SINGLE_THICK). The tab section — not the
# blade's t/c·base — is what carries the root moment at the base plane.
_DUAL_TAB_THICK = 6.35
_CLICK_TAB_THICK = 6.35
_SINGLE_TAB_THICK = 7.19


def tab_neck_stress_mpa(fin: FinParams, moment_nm: float, shear_n: float
                        ) -> float | None:
    """Peak tab stress (MPa) at the base plane under a root bending `moment_nm`
    and root `shear_n`, or None when the fin carries no tabs (TabSystem.NONE /
    glass-on — the gate is then inactive). docs/TAB-SYSTEMS.md; [Roa01].

    THE SECTION THAT CARRIES IT. Cut the fin at the base plane (z = 0). Every
    box reaction — bearing on the slot walls, the cam screw, the retention
    indents — acts BELOW that cut, so by statics the material crossing z = 0
    transmits the ENTIRE root moment. Below z = 0 the only material is the tabs.
    So the tabs are loaded in BENDING about their own weak axis, through their
    own section modulus, at the fused step where the blade ends:

        S_tab = Σ L_eff · t_tab² / 6        (coplanar bars, common neutral axis)
        σ     = KT_TAB · M_root / S_tab  +  V / A_tab

    t_tab is the TAB's thickness (`fingen.tabs` lofts _CLICK_THICK/_DUAL_THICK/
    _SINGLE_THICK + fit_offset), NOT the blade's t/c·base — the two differ by
    2-3x and the tab is the thinner. For an FCS II side blade S_tab ≈ 492 mm³,
    BELOW the blade root's own ≈ 533 mm³: the tab is the smallest section in the
    load path and carries the largest moment. That is why printed fins snap
    flush at the deck.

    (The previous model divided a bearing-couple FORCE by the blade's fused
    footprint — a bearing/shear stress compared against a BENDING allowable. Its
    implied section modulus was ~8x the real one, reporting SF 4.7 where the
    bending number is 1.4, so the optimizer never felt this constraint.)

    The moment is split between tabs by their bending stiffness, which for
    equal-thickness coplanar bars is their length share — so both tabs reach the
    same σ and the section-modulus sum above is exact. `shear_n` is carried on
    the FUSED footprint (blade-to-tab overlap), which is where it is actually
    transferred; that term is small but reported honestly rather than dropped.
    """
    system = fin.tabs.system
    if system is TabSystem.NONE:
        return None
    # Tab thickness as lofted (mm -> m). fit_offset is the printed undersize.
    t_tab_mm = {
        TabSystem.DUAL_TAB: _DUAL_TAB_THICK,
        TabSystem.CLICK_TAB: _CLICK_TAB_THICK,
        TabSystem.SINGLE_TAB: _SINGLE_TAB_THICK,
    }[system] + fin.tabs.fit_offset
    if system is TabSystem.SINGLE_TAB:
        lengths_mm = (min(fin.outline.base - 12.0, 110.0),)
    else:
        _depth_mm, lengths_mm = _TAB_NECK_GEOM[system]
    # Bending through the tabs' own section at z = 0.
    s_tab_m3 = sum(length * t_tab_mm**2 / 6.0 for length in lengths_mm) * 1e-9
    sigma_bend = KT_TAB * moment_nm / max(s_tab_m3, 1e-15) / 1e6
    # Direct shear over the fused footprint, capped by the tab's own thickness:
    # the blade can be thinner than the tab under part of the tab (then the weld
    # is only as thick as the blade), never effectively thicker than the tab.
    t_blade_mm = fin.foil.thickness_ratio * fin.outline.base
    t_weld_mm = min(t_blade_mm, t_tab_mm)
    a_tab_m2 = sum(lengths_mm) * t_weld_mm * 1e-6
    sigma_shear = shear_n / max(a_tab_m2, 1e-12) / 1e6
    return sigma_bend + sigma_shear


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
           tabs: TabSystem = TabSystem.NONE,
           member: str = "dominant") -> AnchorSheet:
    """Answer the absolute questions first (design_speed default: measured
    mean riding speed [Forsyth24]).

    `member` selects whose load share sizes the sheet: "dominant" (the default,
    the side/front blade the optimizer designs) or "center" (the aft member of a
    co-designed set — a smaller share, see CONFIG_CENTER_SHARE). Configs with no
    center share fall back to the dominant share."""
    if material not in _MATERIAL_ALLOW_MPA:
        raise ValueError(f"material {material!r} not in {sorted(_MATERIAL_ALLOW_MPA)}")
    if member not in ("dominant", "center"):
        raise ValueError(f"member {member!r} not in ('dominant', 'center')")
    m_total = rider_mass_kg + BOARD_MASS_KG
    f_lateral = m_total * G * math.tan(math.radians(skill.value))
    share = (CONFIG_CENTER_SHARE.get(config, CONFIG_DOMINANT_SHARE[config])
             if member == "center" else CONFIG_DOMINANT_SHARE[config])
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
