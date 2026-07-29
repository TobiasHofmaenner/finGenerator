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

# Material design allowables: datasheet strength, moisture-conditioned, times
# the card's AS-PRINTED retention, over a provenance-scaled structural SF.
#
# EVERY FACTOR THAT IS A PROPERTY OF THE MATERIAL NOW LIVES ON THE CARD. Three
# used to be module-level constants applied to every material alike:
#
#   * INTERLAMINAR (Z/XY) knockdown — was 0.16, fitted to paht-cf (22/138) and
#     applied to all. Every card already carries strength_z_mpa, so the constant
#     duplicated card data AND disagreed with it: 2.3x-4.9x too pessimistic for
#     the others (PLA is 0.776, nearly isotropic). Now MaterialCard
#     .interlaminar_ratio, derived.
#   * IN-PLANE as-printed retention — was 0.85 globally, but sourced to Elegoo
#     PAHT-CF coupons specifically [ELPAHT-COUPON]: 121.8 kgf X-Y and 19.0 kgf Z
#     on 4x4 mm bars, i.e. X-Y 74.7 MPa = 0.86 of Elegoo's published 87 MPa
#     tensile. It is NOT derivable from a datasheet — it is a property of the
#     PRINT (nozzle, layer height, temperature), not the polymer — so it is a
#     per-card field, MaterialCard.as_printed_retention, measured where we have
#     coupons and inherited where we do not.
# STRUCTURAL_SF STAYS FLAT AT 2.0, and that is a considered decision rather than
# an omission. Scaling it by the card's `provenance` was tried and REVERTED: the
# flag describes the card AS A WHOLE, but this allowable depends on exactly one
# field, strength_xy_mpa, and for the card that flag would have penalised
# (paht-cf, "approximated") that field is Elegoo's OWN published flexural
# strength — datasheet quality. Only e_z_mpa and density are analogised, and
# neither enters here. Derating a measured strength because an unrelated field
# on the same card was estimated is a category error, and it cost 23 % of the
# allowable for nothing. Doing this properly needs per-FIELD provenance, which
# is not worth the machinery until a second card actually needs it.
#
# WHY THE UNCERTAINTY IS BOOKED ONCE. A card we have not coupon-tested inherits
# the measured retention rather than getting an invented lower one: guessing a
# second knockdown for the same unknown would double-count it. The uncertainty
# of an unvalidated card is carried in ONE place, _PROVENANCE_SF, so it is
# visible and adjustable instead of smeared across three factors.
#
# NOTE the allowable assumes the FLAT print orientation the exporter enforces. A
# blade printed upright carries its root tension ACROSS layers and must use the
# card's interlaminar_ratio instead — for paht-cf a ~5x lower allowable, but for
# PLA only ~1.1x, which is exactly the material-specificity the old global
# constant destroyed.
STRUCTURAL_SF = 2.0
_MOISTURE_RETENTION = {"pet-cf": 1.0, "paht-cf": 0.85}


def _design_allowable_mpa(material: str) -> float:
    """Design allowable = card X-Y strength · moisture · the card's as-printed
    retention / the structural SF. Every material-DEPENDENT factor now comes
    from the CARD; only the SF is module policy. See the block comment above."""
    from fingen.materials import get_card

    card = get_card(material)
    return (card.strength_xy_mpa * _MOISTURE_RETENTION.get(material, 1.0)
            * card.as_printed_retention / STRUCTURAL_SF)


def interlaminar_allowable_mpa(material: str) -> float:
    """Allowable for a blade printed UPRIGHT, where bending tension crosses
    layer boundaries. Uses the card's own Z/XY ratio rather than a global
    constant — the anisotropy of PLA (0.78) and paht-cf (0.16) differ by 5x."""
    from fingen.materials import get_card

    return _design_allowable_mpa(material) * get_card(material).interlaminar_ratio


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


def peak_bending_stress_mpa(fin: FinParams, sheet: AnchorSheet,
                            span_stress_mpa: float | None = None) -> float:
    """The stress the gate should use: the ENVELOPE of the root-plane estimate
    and the spanwise station sweep. MPa.

    WHY AN ENVELOPE AND NOT EITHER ONE ALONE. The two models fail in opposite
    halves of the design space, and picking either one is non-conservative on
    the other half:

      * base_bending_stress_mpa reads ONE section (z = 0) with the whole load at
        CP_SPAN_FRACTION = 0.45. Tier-1 FEM (docs/FEM-BENCH.md) shows a tapered
        blade's section modulus falls faster than its moment, so the critical
        station is MID-SPAN — 53 % of span on the anchor fin, 1.44x the root
        band. On those shapes the root-only read misses the peak entirely.
      * flex_report sweeps stations and finds that peak, but distributes the
        load as w ∝ c(z), whose centroid is 0.372 of depth against this
        function's 0.45 arm. On ROOT-CRITICAL fins — where flex's own peak is
        already at z = 0 — that shorter arm makes it read up to 24 % LOWER than
        the root estimate. Measured: flex is the smaller of the two in 227 of
        432 swept geometries.

    Neither dominates: the base IS the peak for ~45 % of the archived corpus,
    and mid-span for the rest. max() of the two keeps the root-plane pad where
    the root governs and catches the mid-span peak where it does not. This is
    the only combination that is conservative across the whole space.

    `span_stress_mpa` lets a caller that has ALREADY solved the flex report pass
    its stress_max_mpa in rather than paying for a second solve —
    optimize.evaluate does exactly that, and it is the hot path.
    """
    root = base_bending_stress_mpa(fin, sheet.force_peak_n)
    if span_stress_mpa is not None:
        return max(root, span_stress_mpa)
    # Deferred: fingen.flex imports _MATERIAL_ALLOW_MPA from this module, so a
    # module-level import here is circular.
    from fingen.flex import flex_report

    try:
        span = flex_report(fin, sheet.force_peak_n, sheet.design_speed,
                           material=sheet.material).stress_max_mpa
    except (ValueError, ZeroDivisionError):
        # chord_schedule's needle-tip / waist guards reject degenerate outlines.
        # A candidate flex cannot section is not thereby SAFE, so fall back to
        # the root estimate rather than silently scoring it as feasible.
        return root
    return max(root, span)


def base_bending_stress_mpa(fin: FinParams, force_n: float) -> float:
    """Bending stress at the BASE SECTION under the peak load applied at the
    spanwise CP — Euler-Bernoulli with the section modulus integrated
    numerically from the true foil section [GT97].

    ROOT-PLANE ONLY. This is one half of the gate; see peak_bending_stress_mpa
    for why it is enveloped with the station sweep rather than used alone. Its
    0.45 arm overstates the distributed load's true 0.372 centroid by ~1.2x,
    which is retained deliberately: it is the pad that keeps a single-section
    estimate from under-reading, and tier-1 measures this function at +12 %
    against the FEM root band (19.40 vs 17.30 MPa).
    """
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


def check_anchor(fin: FinParams, sheet: AnchorSheet,
                 span_stress_mpa: float | None = None) -> list[str]:
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
    stress = peak_bending_stress_mpa(fin, sheet, span_stress_mpa)
    if stress > sheet.allow_mpa:
        issues.append(f"peak bending stress {stress:.0f} MPa exceeds "
                      f"{sheet.material} allowable {sheet.allow_mpa:.0f} MPa "
                      "(thicken the section or widen the base)")
    if fin.outline.base < sheet.base_min_mm:
        issues.append(f"base {fin.outline.base:.0f} mm below the mounting "
                      f"system minimum {sheet.base_min_mm:.0f} mm")
    return issues
