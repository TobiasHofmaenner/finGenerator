"""Tier-0 roll dynamics: the physics that prices fin depth (docs/PHYSICS.md §5c).

A surfboard fin is, for roll, a damping vane. When the board rolls (rate p about
the fore-aft x axis — the rail-to-rail motion) a blade element at height z above
the roll axis is swept sideways at p·z_eff, which the forward speed U turns into a
local incidence change Δα = p·z_eff/U; the extra lift opposes the roll. That is
lift-based **roll damping**, the exact roll analogue of the damping-in-roll of a
wing [Pol49]. The blade also carries a **roll added inertia** — the 2D flat-plate
apparent mass πρ_w(c/2)² per unit span [BAH96], moment-weighted by z_eff² like any
mass moment of inertia. Both are station-array integrals, milliseconds per call,
the same numeric spirit as `flex.py`.

Two regimes (documented in §5c):

- **z² regime (at speed).** Lift damping ∝ ∫c(z)·z_eff² dz — the arm enters
  squared (once for the induced incidence, once for the moment arm), so damping
  grows with span **cubed** at fixed chord. This is the dominant fin contribution
  to roll feel while the board is moving.
- **z³ regime (near zero speed).** With no forward flow there is no lift; the
  swept element instead pushes water broadside as a flat plate (normal-force
  coefficient C_d ≈ 1.1 [Hoe75]), a drag moment ∝ ∫c(z)·z_eff³ dz that is
  quadratic in p. Reported separately as the low-speed number.

Set level (`FinSetParams`): a side blade at lateral offset y_f is not on the roll
axis, so rolling both **sweeps** it (the z-component, as for the center fin) and
**heaves** it (a vertical velocity p·y_f from the offset). On an upright blade the
heave is pure spanwise flow and makes no lift; **cant** tilts the blade normal so
part of the heave projects into local incidence. The per-blade geometry is derived
in `roll_solve` — the center fin is the pure-sweep special case (y_f = cant = 0).

Scope. `I_total` for the roll time constant is the fins' added inertia only — the
board+rider rotational inertia (which actually sets the maneuver timescale) and the
board's own hydrostatic/rail roll stiffness are **out of scope** here: the board
dominates static roll stiffness, the fins dominate roll *damping* at speed, and
this module is the fin-damping half. τ = I_add/|L_p| is therefore the fin's own
roll-rate decay time (milliseconds — the fin arrests roll rate almost instantly on
its own), reported as a relative feel index, not an absolute maneuver time.

Geometry in mm like the rest of fingen (`z` spanwise from the root, chord across);
the solve converts to SI internally and reports SI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from fingen.hydro import RHO_SEAWATER, lift_curve_slope
from fingen.outline import chord_schedule
from fingen.params import FinConfig, FinParams, FinSetParams, GenSettings

# Roll-axis height above the board plane (z0). The board+rider system rolls about
# a line whose height is set by the rider's mass distribution — well above the
# board for a standing surfer — but the fin's damping about that line is what we
# price, and referencing it to the board plane (fin root, z0 = 0) is the simplest
# defensible tier-0 choice: it makes z_eff = z (the spanwise coordinate) and keeps
# the depth-pricing clean. Exposed as `z0_mm` so a measured roll-axis height can be
# fed in later without touching the physics.
ROLL_AXIS_OFFSET_MM = 0.0
# Flat-plate normal-force coefficient for the zero-forward-speed drag form — the
# broadside bluff-plate value [Hoe75]. A finite plate sits ~1.1–1.2; the 2D value
# is ~1.98. Used only for the low-speed number, never for the at-speed damping.
FLAT_PLATE_CD = 1.1
# Station resolution for the FinParams/FinSetParams wrappers. The roll integrands
# are smooth low-order polynomials in z against the chord schedule, so the
# trapezoid converges far below the model error at this count (well under 0.1 %
# against the closed forms — see test_roll), still sub-millisecond.
_N_STATIONS = 41
_N_FOIL_POINTS = 60  # unused by roll (no sections) — a valid GenSettings filler


@dataclass(frozen=True)
class RollReport:
    """Tier-0 roll answers for one blade at one operating point.

    l_p is the signed roll-damping derivative ∂(roll moment)/∂p [N·m·s], negative
    (a restoring/damping moment); roll_damping_nm_s is its magnitude. clp is the
    dimensionless form, normalized by q·S·s²/U (S the strip planform area, s the
    span) — it folds in the lift slope and lands at −a/3 for a rectangular blade.
    added_inertia_kgm2 is the roll added inertia I_add; drag_damping_kgm2 is the
    low-speed coefficient B in M_drag = −B·p·|p|. sweep_/heave_damping_nm_s are the
    diagonal (self) contributions of the two mechanisms — for a center fin the
    damping is all sweep; cant moves weight from sweep into heave (their sum omits
    the cross term, which the total keeps). moment_arm_int_m4 = ∫c·z_eff² dz and
    drag_arm_int_m5 = ∫c·z_eff³ dz are the raw integrals (closed-form handles).
    """

    z_mm: np.ndarray
    chord_mm: np.ndarray
    speed_ms: float
    lift_slope: float
    l_p: float  # signed roll-damping derivative, N·m·s (< 0)
    clp: float  # dimensionless, normalized by q·S·s²/U (< 0)
    added_inertia_kgm2: float
    drag_damping_kgm2: float  # B in M_drag = −B·p·|p|
    sweep_damping_nm_s: float
    heave_damping_nm_s: float
    moment_arm_int_m4: float  # ∫ c·z_eff² dz
    drag_arm_int_m5: float  # ∫ c·z_eff³ dz

    @property
    def roll_damping_nm_s(self) -> float:
        """Magnitude of the lift-based roll-damping derivative |L_p| [N·m·s]."""
        return abs(self.l_p)

    @property
    def tau_ms(self) -> float:
        """Fin-only roll time constant I_add/|L_p| in ms (board+rider excluded —
        see the module scope note): the fin's own roll-rate decay time."""
        return 1e3 * self.added_inertia_kgm2 / max(self.roll_damping_nm_s, 1e-15)

    @property
    def agility_proxy(self) -> float:
        """Rail-to-rail agility index: roll rate reached per unit driving moment,
        1/|L_p| [rad/(s·N·m)]. HIGHER = looser/quicker rail-to-rail (a shallow
        blade adds little roll resistance); LOWER = more planted (a deep blade
        damps hard). Fin-only — board+rider inertia sets the absolute timescale;
        this ranks blades by the roll resistance they add at speed."""
        return 1.0 / max(self.roll_damping_nm_s, 1e-15)


def roll_solve(z_mm: np.ndarray, chord_mm: np.ndarray, lift_slope: float,
               speed: float, *, z0_mm: float = ROLL_AXIS_OFFSET_MM,
               y_offset_mm: float = 0.0, cant_deg: float = 0.0,
               rho_fluid: float = RHO_SEAWATER) -> RollReport:
    """Core roll solve on station arrays (root at z_mm[0], tip at z_mm[-1]).

    lift_slope is the strip lift response dCl/dα per radian (the FinParams wrapper
    passes hydro's DATCOM 3D slope — a tier-0 choice: strictly the strips want the
    2D sectional slope shaped by the spanwise loading, but the 3D slope is the
    consistent, available number and ties the roll model to the same lift physics
    as `hydro`/`flex`). speed is the forward speed U [m/s].

    Placement (assembly-frame, `assembly.py`): y_offset_mm is the blade's lateral
    base offset from the stringer (|side_y|), cant_deg its outward tip lean, z0_mm
    the roll-axis height above the board. A center blade takes the defaults
    (y = cant = 0) and reduces to the pure-sweep case.

    Derivation of the effective roll arm ℓ(z). Roll p about x through the axis at
    height z0 gives an element at lateral offset Y and depth D below the axis the
    velocity p×r = (0, p·D, p·Y): a lateral sweep p·D and a vertical heave p·Y. A
    blade canted by γ carries its element to D(z) = z·cosγ + z0 and Y(z) = y_f +
    z·sinγ, and tilts its lift normal to n̂ = (0, cosγ, sinγ). The incidence-driving
    normal-wash is v·n̂ = p·(D·cosγ + Y·sinγ), and the roll moment of the resulting
    side force uses the *same* arm (r×F)_x/|F| = D·cosγ + Y·sinγ — reciprocity — so

        ℓ(z) = D·cosγ + Y·sinγ = z + z0·cosγ + y_f·sinγ.

    The z0·cosγ and y_f·sinγ terms are the roll-axis offset and the cant-projected
    heave; without cant the y_f heave is pure spanwise flow and drops out (sinγ=0).
    Damping is q·a/U·∫c·ℓ² dz; the sweep/heave split reports the diagonal parts
    (D·cosγ)² and (Y·sinγ)² separately — note the sweep part carries a cosγ that
    the mirror-symmetric left blade shares, so both a right and a left side blade
    add the *same* positive damping.
    """
    z_mm = np.asarray(z_mm, dtype=float)
    chord_mm = np.asarray(chord_mm, dtype=float)
    if len(z_mm) != len(chord_mm):
        raise ValueError("z and chord arrays must have equal length")
    if len(z_mm) < 5:
        raise ValueError(f"need at least 5 stations, got {len(z_mm)}")
    if np.any(np.diff(z_mm) <= 0.0):
        raise ValueError("z stations must be strictly increasing (root to tip)")
    if speed <= 0.0:
        raise ValueError(f"speed {speed} must be positive")

    z = z_mm * 1e-3
    chord = chord_mm * 1e-3
    z0 = z0_mm * 1e-3
    y_f = y_offset_mm * 1e-3
    gamma = math.radians(cant_deg)
    cg, sg = math.cos(gamma), math.sin(gamma)

    depth_below = z * cg + z0  # D(z): perpendicular depth below the roll axis
    lateral = y_f + z * sg  # Y(z): lateral offset from the stringer
    arm_sweep = depth_below * cg  # sweep mechanism's arm (∝ cosγ)
    arm_heave = lateral * sg  # heave mechanism's arm (cant-projected, ∝ sinγ)
    arm = arm_sweep + arm_heave  # ℓ(z), the effective roll arm

    q = 0.5 * rho_fluid * speed**2
    # Lift-based damping (z² regime): each strip's rolled incidence p·ℓ/U makes
    # side force q·a·(p·ℓ/U)·c dz, reacted at arm ℓ — moment ∝ ℓ². Negative =
    # damping (opposes p). L_p = ∂M/∂p [Pol49].
    arm2_int = float(np.trapezoid(chord * arm**2, z))
    l_p = -q * lift_slope / speed * arm2_int
    sweep_damp = q * lift_slope / speed * float(np.trapezoid(chord * arm_sweep**2, z))
    heave_damp = q * lift_slope / speed * float(np.trapezoid(chord * arm_heave**2, z))

    # Roll added inertia: 2D flat-plate added mass πρ_w(c/2)² per span [BAH96],
    # weighted by ℓ² like any mass moment of inertia.
    added_inertia = rho_fluid * float(np.trapezoid(math.pi * chord**2 / 4.0 * arm**2, z))

    # Zero-speed drag form (z³ regime): broadside flat-plate drag ½ρC_d·c·(p·ℓ)²
    # per span [Hoe75], reacted at ℓ — moment quadratic in p, M_drag = −B·p·|p|.
    # ℓ²·|ℓ| (not ℓ³) so the moment stays a damper if the arm ever goes negative.
    arm3_int = float(np.trapezoid(chord * arm**2 * np.abs(arm), z))
    drag_damping = 0.5 * rho_fluid * FLAT_PLATE_CD * arm3_int

    # Dimensionless damping: normalize by q·S·s²/U with S the strip planform area
    # and s the span — folds in the lift slope, → −a/3 for a rectangular blade.
    area = float(np.trapezoid(chord, z))
    span = float(z[-1] - z[0])
    clp = l_p * speed / max(q * area * span**2, 1e-30)

    return RollReport(
        z_mm=z_mm,
        chord_mm=chord_mm,
        speed_ms=speed,
        lift_slope=lift_slope,
        l_p=l_p,
        clp=clp,
        added_inertia_kgm2=added_inertia,
        drag_damping_kgm2=drag_damping,
        sweep_damping_nm_s=sweep_damp,
        heave_damping_nm_s=heave_damp,
        moment_arm_int_m4=arm2_int,
        drag_arm_int_m5=arm3_int,
    )


def roll_report(fin: FinParams, speed: float, *, z0_mm: float = ROLL_AXIS_OFFSET_MM,
                y_offset_mm: float = 0.0, cant_deg: float = 0.0,
                n_stations: int = _N_STATIONS) -> RollReport:
    """Tier-0 roll of a fingen blade at forward speed `speed` [m/s].

    Stations and chord come from the outline's chord schedule; the strip lift
    response is hydro's DATCOM lift-curve slope for this blade. With the default
    placement (y_offset = cant = 0) this is the blade's intrinsic, on-the-stringer
    roll damping — the number that prices depth. Pass y_offset_mm/cant_deg to place
    it as a side blade.
    """
    settings = GenSettings(n_stations=n_stations, n_foil_points=_N_FOIL_POINTS)
    stations = chord_schedule(fin.outline, settings, tip_chord_min=settings.cap_chord)
    z_mm = np.array([st.z for st in stations])
    chord_mm = np.array([st.chord for st in stations])
    slope, _ = lift_curve_slope(fin)
    return roll_solve(z_mm, chord_mm, slope, speed, z0_mm=z0_mm,
                      y_offset_mm=y_offset_mm, cant_deg=cant_deg)


@dataclass(frozen=True)
class RollSetReport:
    """Tier-0 roll answers for a whole placed set, composed from its slots.

    per_slot maps each placed blade (assembly slot name) to its RollReport. The
    set totals sum the physical quantities across slots: roll_damping_nm_s = Σ|L_p|,
    added_inertia_kgm2 = ΣI_add, and so on. tau_ms and agility_proxy use the set
    totals. sweep_/heave_damping_nm_s sum the two mechanisms across the side blades
    (the center fin is all sweep) — the handle for the cant sign/monotonicity pin.
    """

    config: FinConfig
    speed_ms: float
    per_slot: dict[str, RollReport]
    roll_damping_nm_s: float
    added_inertia_kgm2: float
    drag_damping_kgm2: float
    sweep_damping_nm_s: float
    heave_damping_nm_s: float

    @property
    def tau_ms(self) -> float:
        """Set roll time constant I_total/|L_p_total| in ms (fin-only)."""
        return 1e3 * self.added_inertia_kgm2 / max(self.roll_damping_nm_s, 1e-15)

    @property
    def agility_proxy(self) -> float:
        """Set rail-to-rail agility index 1/|L_p_total| (see RollReport)."""
        return 1.0 / max(self.roll_damping_nm_s, 1e-15)


def _set_placements(sp: FinSetParams) -> list[tuple[str, FinParams, float, float]]:
    """(slot, blade, |y_offset_mm|, cant_deg) for every placed blade of the set.

    Mirrors the config→slot logic of `assembly.fin_set` but WITHOUT lofting any
    solid (roll is tier-0 numeric): only the placement fields that enter the roll
    geometry — lateral offset and cant — are needed. A right and a left side blade
    contribute identical roll damping (the derivation's ℓ(z) is mirror-symmetric),
    so both are enumerated for a faithful per-slot summary. The center/rear-center
    fin rides the stringer (y = cant = 0).
    """
    cfg = sp.config

    def pair(prefix: str, blade: FinParams, y: float, cant: float):
        return [(f"{prefix}right", blade, y, cant), (f"{prefix}left", blade, y, cant)]

    if cfg is FinConfig.SINGLE:
        return [("center", sp.center, 0.0, 0.0)]
    if cfg is FinConfig.TWIN:
        return pair("", sp.side, sp.side_y, sp.cant)
    if cfg in (FinConfig.THRUSTER, FinConfig.TWO_PLUS_ONE):
        return [("center", sp.center, 0.0, 0.0)] + pair("", sp.side, sp.side_y, sp.cant)
    if cfg is FinConfig.QUAD:
        return (pair("front_", sp.side, sp.side_y, sp.cant)
                + pair("rear_", sp.side, sp.rear_y, sp.rear_cant))
    raise ValueError(f"unhandled config {cfg}")  # pragma: no cover


def roll_set_report(set_params: FinSetParams, speed: float, *,
                    z0_mm: float = ROLL_AXIS_OFFSET_MM,
                    n_stations: int = _N_STATIONS) -> RollSetReport:
    """Compose a set's roll damping and added inertia from its placed blades.

    Each slot's blade is rolled at its own lateral offset and cant (`roll_report`);
    the totals sum across slots. A thruster's side pair adds to the center fin, so
    the set damping exceeds the center-only value; cant trades a side blade's sweep
    contribution (∝ cosγ) for heave (∝ sinγ) per the `roll_solve` geometry.
    """
    per_slot: dict[str, RollReport] = {}
    for slot, blade, y, cant in _set_placements(set_params):
        per_slot[slot] = roll_report(blade, speed, z0_mm=z0_mm, y_offset_mm=y,
                                     cant_deg=cant, n_stations=n_stations)
    reports = per_slot.values()
    return RollSetReport(
        config=set_params.config,
        speed_ms=speed,
        per_slot=per_slot,
        roll_damping_nm_s=sum(r.roll_damping_nm_s for r in reports),
        added_inertia_kgm2=sum(r.added_inertia_kgm2 for r in reports),
        drag_damping_kgm2=sum(r.drag_damping_kgm2 for r in reports),
        sweep_damping_nm_s=sum(r.sweep_damping_nm_s for r in reports),
        heave_damping_nm_s=sum(r.heave_damping_nm_s for r in reports),
    )
