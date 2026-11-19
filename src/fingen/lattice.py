"""Vortex-lattice layer: what the planform and the placement do to the loading.

Tier-0's closed forms (hydro.py) see a blade through four numbers — area,
aspect ratio, half-chord sweep, section thickness — so outline shape, tip
thickness, toe, cant and the wash of one fin on another are invisible to them
(docs/MODEL-REACH.md). This module is the next layer of the fast model
(docs/MODEL-EXTENSION.md): a linear, inviscid lifting-surface solve on the
blade's ACTUAL planform, cheap enough for the optimizer loop (≈ 3 ms per blade
at 36 panels, ≈ 7 ms for a three-fin set at 60, plain numpy).

Method. Horseshoe vortices on a spanwise-by-chordwise panel grid: the bound leg
on each panel's quarter chord, the two legs running in the blade plane to the
trailing edge and from there downstream along the freestream; flow tangency at
the panel three-quarter-chord points; Kutta–Joukowski forces on the bound legs
[KP01]. The board is a mirror plane at z = 0 (every vortex has an image), which
is exactly what our CFD does (symmetryPlane) — tier-0's softer factor 1.7 for a
real, finite board is NOT applied here (see `scripts/board_edge_probe.py`:
≈ 5–7 % on a centre fin, 7–12 % on a side fin). Section camber enters as a
per-strip incidence offset: thin-airfoil alpha_0 of the root section, scaled
along the span with the local thickness on a FLAT_INSIDE foil (camber = t/2
there, so a thinner tip is a less cambered one). Blades are placed exactly as
`fingen.assembly.place_fin` places the solids — toe about z, cant about x,
right and left hands — so one code path solves a single fin or a whole set,
each blade in the others' wash.

Validated (scripts/vlm_probe.py, tests/test_lattice.py):
  * rectangular wings AR 2 / 4 / 6: lift slope within 2 % of lifting-surface
    theory;
  * isolated lift slope against our CFD polars: 1.00 and 1.02 on the two side
    fins, 1.13 on the 4.6 % centre (the method is inviscid; thin sections lose
    more than it knows);
  * the 48-point set CFD of bench/mount: per-fin correlation 0.91–1.00 at 5°,
    level 9–17 % high; centre interference 0.64 against 0.67 and its trends
    with side offset and side blade; zero-net-force toe 3.68° against 3.65°.

Limits, by construction: linear and attached — no stall, no viscous drag, no
thickness. `peak_ratio` says WHERE a blade is loaded hardest, hence where it
separates first; how much lift that allows needs section data, which this
module does not have.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from fingen import sections
from fingen.hydro import RHO_SEAWATER, zero_lift_alpha_deg
from fingen.outline import metrics, planform
from fingen.params import FinConfig, FinParams, FinSetParams, FoilFamily
from fingen.sections import SectionPolar

_FOUR_PI = 4.0 * math.pi
_CORE = 1e-14          # m²: regularises the Biot–Savart kernel on a vortex line
_TIP_CHORD_MIN = 2.0   # mm: the lattice stops where the rounded tip gets thinner than this
_MIRROR = np.array([1.0, 1.0, -1.0])


# --------------------------------------------------------------- Biot–Savart
def _seg(P: np.ndarray, P1: np.ndarray, P2: np.ndarray) -> np.ndarray:
    """Velocity at P (N,1,3) of unit-strength straight vortex segments P1→P2 (1,M,3)."""
    r1, r2, r0 = P - P1, P - P2, P2 - P1
    cr = np.cross(r1, r2)
    k = ((r0 * r1).sum(-1) / (np.linalg.norm(r1, axis=-1) + 1e-12)
         - (r0 * r2).sum(-1) / (np.linalg.norm(r2, axis=-1) + 1e-12))
    k = k / (_FOUR_PI * ((cr**2).sum(-1) + _CORE))
    return cr * k[..., None]


def _semi(P: np.ndarray, P1: np.ndarray, d: np.ndarray) -> np.ndarray:
    """Unit-strength semi-infinite vortex from P1 to infinity along the unit vector d."""
    r1 = P - P1
    cr = np.cross(np.broadcast_to(d, r1.shape), r1)
    k = 1.0 + (r1 * d).sum(-1) / (np.linalg.norm(r1, axis=-1) + 1e-12)
    k = k / (_FOUR_PI * ((cr**2).sum(-1) + _CORE))
    return cr * k[..., None]


def _horseshoe(P, A, B, ATE, BTE, d) -> np.ndarray:
    """∞ → ATE → A → B → BTE → ∞: bound leg A→B, in-plane legs to the trailing
    edge, wake along d."""
    return (-_semi(P, ATE, d) + _seg(P, ATE, A) + _seg(P, A, B) + _seg(P, B, BTE)
            + _semi(P, BTE, d))


# -------------------------------------------------------------------- blades
@dataclass(frozen=True)
class Blade:
    """One blade's lattice, in metres, already placed in the set frame
    (x aft, y to the right, z from the board into the water)."""

    name: str
    A: np.ndarray           # (n,3) inboard end of each bound leg
    B: np.ndarray           # (n,3) outboard end
    ATE: np.ndarray         # (n,3) trailing-edge points the legs run to
    BTE: np.ndarray
    CP: np.ndarray          # (n,3) control points
    normal: np.ndarray      # (n,3) panel normal; outboard for a side blade
    camber: np.ndarray      # (n,) |alpha_0| of the panel's strip, rad
    strip: np.ndarray       # (n,) strip index of each panel
    z_mid: np.ndarray       # (nz,) local span station of each strip
    dz: np.ndarray          # (nz,) strip width
    chord: np.ndarray       # (nz,) mean strip chord
    area: float             # reference (planform) area, m²
    xq_local: np.ndarray    # (n,) chordwise position of each bound-leg midpoint, blade frame
    depth: float            # blade depth, m

    @property
    def n_panels(self) -> int:
        return len(self.strip)


def _rot(toe_deg: float, cant_deg: float) -> np.ndarray:
    """`assembly.place_fin` for the right hand: rotate about z by +toe, then about x by −cant."""
    t, c = math.radians(toe_deg), math.radians(-cant_deg)
    ct, st, cc, sc = math.cos(t), math.sin(t), math.cos(c), math.sin(c)
    rz = np.array([[ct, -st, 0.0], [st, ct, 0.0], [0.0, 0.0, 1.0]])
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cc, -sc], [0.0, sc, cc]])
    return rx @ rz


def blade_from_planform(name: str, z_mm: np.ndarray, x_le_mm: np.ndarray,
                        chord_mm: np.ndarray, *, alpha0_deg: float = 0.0,
                        alpha0_tip_scale: float = 1.0, x_ref_mm: float = 0.0,
                        area_mm2: float | None = None, nz: int = 12, nx: int = 3,
                        hand: str = "right", toe_deg: float = 0.0, cant_deg: float = 0.0,
                        xy_mm: tuple[float, float] = (0.0, 0.0)) -> Blade:
    """Lattice on a planform given as dense (z, x_le, chord) arrays in mm.

    Strips are clustered toward the tip (z = z_tip·sin θ). `x_ref_mm` is the
    chordwise point the blade is placed about (the base centre for a fin).
    `alpha0_deg` is the root section's zero-lift angle; `alpha0_tip_scale` its
    multiplier at the tip (linear in between). hand="left" mirrors the blade
    and reverses toe and cant, as the assembly does."""
    if hand not in ("right", "left"):
        raise ValueError(f"hand must be 'right' or 'left', got {hand!r}")
    if nz < 3 or nx < 1:
        raise ValueError(f"lattice needs nz >= 3 and nx >= 1, got {nz} x {nx}")
    z_mm, x_le_mm, chord_mm = (np.asarray(v, dtype=float)
                               for v in (z_mm, x_le_mm, chord_mm))
    live = chord_mm >= _TIP_CHORD_MIN
    if not live.any():
        raise ValueError("planform has no chord above the lattice minimum")
    z_tip = float(z_mm[live][-1])
    ze = z_tip * np.sin(0.5 * math.pi * np.arange(nz + 1) / nz)
    xle = np.interp(ze, z_mm, x_le_mm) - x_ref_mm
    c = np.interp(ze, z_mm, chord_mm)
    zc = 0.5 * (ze[:-1] + ze[1:])
    zero = np.zeros(nz)
    pts: dict[str, list[np.ndarray]] = {k: [] for k in ("A", "B", "ATE", "BTE", "CP")}
    strip, xq = [], []
    for i in range(nx):
        fb, fc = (i + 0.25) / nx, (i + 0.75) / nx
        pts["A"].append(np.column_stack([xle[:-1] + fb * c[:-1], zero, ze[:-1]]))
        pts["B"].append(np.column_stack([xle[1:] + fb * c[1:], zero, ze[1:]]))
        pts["ATE"].append(np.column_stack([xle[:-1] + c[:-1], zero, ze[:-1]]))
        pts["BTE"].append(np.column_stack([xle[1:] + c[1:], zero, ze[1:]]))
        x_mid, c_mid = 0.5 * (xle[:-1] + xle[1:]), 0.5 * (c[:-1] + c[1:])
        pts["CP"].append(np.column_stack([x_mid + fc * c_mid, zero, zc]))
        strip.append(np.arange(nz))
        xq.append(x_mid + fb * c_mid)
    sgn = 1.0 if hand == "right" else -1.0
    rot = _rot(sgn * toe_deg, sgn * cant_deg)
    shift = np.array([xy_mm[0], xy_mm[1], 0.0]) * 1e-3
    P = {k: np.vstack(v) * 1e-3 @ rot.T + shift for k, v in pts.items()}
    strip_idx = np.concatenate(strip)
    a0 = abs(math.radians(alpha0_deg)) * (1.0 + (alpha0_tip_scale - 1.0) * zc / z_tip)
    area = (float(np.trapezoid(chord_mm, z_mm)) if area_mm2 is None else area_mm2) * 1e-6
    return Blade(name=name, A=P["A"], B=P["B"], ATE=P["ATE"], BTE=P["BTE"], CP=P["CP"],
                 normal=np.tile(rot @ np.array([0.0, sgn, 0.0]), (len(strip_idx), 1)),
                 camber=a0[strip_idx], strip=strip_idx, z_mid=zc * 1e-3,
                 dz=np.diff(ze) * 1e-3, chord=0.5 * (c[:-1] + c[1:]) * 1e-3, area=area,
                 xq_local=np.concatenate(xq) * 1e-3, depth=float(z_mm[-1]) * 1e-3)


def blade_from_fin(name: str, fin: FinParams, **kw) -> Blade:
    """Lattice of a fingen blade, placed about its base centre. Keyword arguments
    are those of `blade_from_planform` (nz, nx, hand, toe_deg, cant_deg, xy_mm)."""
    z, x_le, chord = planform(fin.outline)
    # On a flat-inside foil camber IS half the thickness, so it follows the
    # spanwise thickness schedule; an explicit camber line (CAMBERED) does not.
    flat = fin.foil.family is FoilFamily.FLAT_INSIDE
    return blade_from_planform(name, z, x_le, chord, alpha0_deg=zero_lift_alpha_deg(fin),
                               alpha0_tip_scale=fin.thickness_tip_factor if flat else 1.0,
                               x_ref_mm=fin.outline.base / 2.0,
                               area_mm2=metrics(fin.outline).area, **kw)


def set_blades(set_params: FinSetParams, *, nz: int = 10, nx: int = 2) -> list[Blade]:
    """Every blade of a set, named and placed as `assembly.fin_set` places them
    (slot names: center, right, left, front_right, …)."""
    cfg, sp = set_params.config, set_params
    out: list[Blade] = []

    def pair(prefix: str, toe: float, cant: float, x: float, y: float) -> None:
        for hand, yy in (("right", y), ("left", -y)):
            out.append(blade_from_fin(f"{prefix}{hand}", sp.side, nz=nz, nx=nx, hand=hand,
                                      toe_deg=toe, cant_deg=cant, xy_mm=(x, yy)))

    if cfg in (FinConfig.SINGLE, FinConfig.THRUSTER, FinConfig.TWO_PLUS_ONE):
        out.append(blade_from_fin("center", sp.center, nz=nz, nx=nx))
    if cfg in (FinConfig.TWIN, FinConfig.THRUSTER, FinConfig.TWO_PLUS_ONE):
        pair("", sp.toe, sp.cant, sp.side_x, sp.side_y)
    if cfg is FinConfig.QUAD:
        pair("front_", sp.toe, sp.cant, sp.side_x, sp.side_y)
        pair("rear_", sp.rear_toe, sp.rear_cant, sp.rear_x, sp.rear_y)
    return out


# --------------------------------------------------------------------- solve
@dataclass(frozen=True)
class BladeLoads:
    """Loads on one blade from `solve`. Coefficients use the blade's own area."""

    cl: float                 # force across the flow, in the board plane, / (q·S)
    cdi: float                # near-field force along the flow / (q·S); indicative only
    cl_local: np.ndarray      # (nz,) strip lift / (q · strip chord · strip width)
    z: np.ndarray             # (nz,) strip stations, m
    dz: np.ndarray            # (nz,) strip widths, m
    gamma_strip: np.ndarray   # (nz,) circulation per strip, m²/s
    x_cp_m: float             # chordwise centre of pressure, blade frame (base centre = 0)
    z_cp_m: float             # spanwise centre of pressure


def solve(blades: list[Blade], speed: float, leeway_deg: float, *,
          mirror: bool = True, mirror_strength: float = 1.0) -> dict[str, BladeLoads]:
    """Solve the placed blades together at one speed [m/s] and leeway [deg].

    The freestream is (cos β, sin β, 0); lift is counted along (−sin β, cos β, 0)
    and drag along the flow — the force-coefficient convention of the CFD cases
    (fincfd.setcase). A side blade whose outboard face is to leeward works WITH
    its camber. mirror=False removes the board (a free blade, for checks);
    `mirror_strength` < 1 weakens the image for a real board (BOARD_MIRROR)."""
    if not blades:
        raise ValueError("solve needs at least one blade")
    if speed <= 0.0:
        raise ValueError(f"speed {speed} must be positive")
    cat = lambda k: np.vstack([getattr(b, k) for b in blades])  # noqa: E731
    A, B, ATE, BTE, CP, N = (cat(k) for k in ("A", "B", "ATE", "BTE", "CP", "normal"))
    camber = np.concatenate([b.camber for b in blades])
    beta = math.radians(leeway_deg)
    d = np.array([math.cos(beta), math.sin(beta), 0.0])
    v_inf = speed * d

    def influence(P: np.ndarray) -> np.ndarray:
        P = P[:, None, :]
        v = _horseshoe(P, A[None], B[None], ATE[None], BTE[None], d)
        if mirror:
            # Image in z = 0 with the orientation reversed, so the circulation
            # runs continuously from the image tip through the root to the tip.
            v = v + mirror_strength * _horseshoe(
                P, (B * _MIRROR)[None], (A * _MIRROR)[None],
                (BTE * _MIRROR)[None], (ATE * _MIRROR)[None], d)
        return v

    aic = (influence(CP) * N[:, None, :]).sum(-1)
    gamma = np.linalg.solve(aic, -(N @ v_inf) - speed * camber)
    v_ind = (influence(0.5 * (A + B)) * gamma[None, :, None]).sum(1)
    force = RHO_SEAWATER * gamma[:, None] * np.cross(v_inf + v_ind, B - A)
    q = 0.5 * RHO_SEAWATER * speed**2
    lift_dir = np.array([-math.sin(beta), math.cos(beta), 0.0])
    out: dict[str, BladeLoads] = {}
    i0 = 0
    for b in blades:
        n, nz = b.n_panels, len(b.z_mid)
        f, g = force[i0:i0 + n], gamma[i0:i0 + n]
        lift = f @ lift_dir
        strip_lift = np.bincount(b.strip, weights=lift, minlength=nz)
        total = float(lift.sum())
        ok = abs(total) > 1e-12
        out[b.name] = BladeLoads(
            cl=total / (q * b.area), cdi=float((f @ d).sum()) / (q * b.area),
            cl_local=strip_lift / (q * b.chord * b.dz), z=b.z_mid, dz=b.dz,
            gamma_strip=np.bincount(b.strip, weights=g, minlength=nz),
            x_cp_m=float((lift * b.xq_local).sum() / total) if ok else float("nan"),
            z_cp_m=float((strip_lift * b.z_mid).sum() / total) if ok else float("nan"))
        i0 += n
    return out


def trefftz_cdi(gamma_strip: np.ndarray, dz: np.ndarray, z: np.ndarray, area: float,
                speed: float) -> float:
    """Induced-drag coefficient of ONE planar blade on the mirror, from its far wake.

    The strip circulations are a step function of span; every step sheds a line
    vortex, the image sheds its mirror, and the drag is (ρ/2)·Σ Γ·w·Δz with w the
    wake-plane normal velocity. Exact for the lattice, unlike the near-field
    force sum (`BladeLoads.cdi`), and the right number for a span efficiency."""
    ze = np.cumsum(dz)                    # edges that shed (the root edge carries none)
    jump = np.concatenate([np.diff(gamma_strip), [-gamma_strip[-1]]])
    kern = 1.0 / (z[:, None] - ze[None, :]) - 1.0 / (z[:, None] + ze[None, :])
    w = (jump[None, :] * kern).sum(1) / (2.0 * math.pi)
    drag = 0.5 * RHO_SEAWATER * abs(float((gamma_strip * w * dz).sum()))
    return drag / (0.5 * RHO_SEAWATER * speed**2 * area)


@dataclass(frozen=True)
class Isolated:
    """Linear characteristics of one blade alone on the mirror (`isolated`)."""

    slope: float            # CL per radian
    cl0: float              # CL at zero leeway (camber)
    alpha0_deg: float       # zero-lift angle of the whole blade
    span_efficiency: float  # e of the incidence loading, far-wake, on the full-mirror aspect ratio
    x_cp_mm: float          # chordwise centre of pressure from the base centre, + aft
    z_cp_frac: float        # spanwise centre of pressure / depth
    peak_ratio: float       # max over span of (local cl / blade CL) for the incidence loading
    peak_z_frac: float      # where that peak sits, / depth
    cl_local: np.ndarray    # (nz,) local cl per unit blade CL of the incidence loading
    z_frac: np.ndarray      # (nz,) strip stations / depth


def isolated(fin: FinParams, speed: float = 7.0, *, nz: int = 12, nx: int = 3,
             probe_deg: float = 4.0) -> Isolated:
    """One blade alone: lift slope, zero-lift angle, where it carries its load.

    `peak_ratio` is the planform's stall-onset indicator: the station where the
    local lift coefficient exceeds the blade's own by the most is where the
    section reaches its limit first; a blade with a low peak carries more total
    lift before any station gives up, and the peak's position says whether it
    lets go from the tip or all along the span."""
    b = blade_from_fin("blade", fin, nz=nz, nx=nx)
    r0, r1 = solve([b], speed, 0.0)["blade"], solve([b], speed, probe_deg)["blade"]
    d_cl = r1.cl - r0.cl
    slope = d_cl / math.radians(probe_deg)
    ar_full = 2.0 * fin.outline.depth**2 / metrics(fin.outline).area
    cdi = trefftz_cdi(r1.gamma_strip - r0.gamma_strip, b.dz, b.z_mid, b.area, speed)
    shape = (r1.cl_local - r0.cl_local) / d_cl
    k = int(np.argmax(shape))
    depth = fin.outline.depth * 1e-3
    return Isolated(slope=slope, cl0=r0.cl, alpha0_deg=-math.degrees(r0.cl / slope),
                    span_efficiency=(d_cl**2 / (math.pi * ar_full * cdi) if cdi > 0
                                     else float("nan")),
                    x_cp_mm=r1.x_cp_m * 1e3, z_cp_frac=r1.z_cp_m / depth,
                    peak_ratio=float(shape[k]), peak_z_frac=float(b.z_mid[k] / depth),
                    cl_local=shape, z_frac=b.z_mid / depth)


# ----------------------------------------------------------- viscous coupling
# The linear lattice treats every strip as a flat plate with a camber offset:
# strip lift = 2π · (effective incidence + offset). A real section follows its
# polar instead — its slope is not 2π, it rolls off toward the break, and a
# flat inside face misbehaves at negative incidence. The coupling below is the
# standard "decambering" iteration of nonlinear lifting-surface methods: give
# every strip an extra incidence offset δ, read the effective incidence the
# strip works at off its own circulation (α_eff = cl/2π − δ), look up what the
# section would really lift there, and move δ until the two agree. The lattice
# keeps doing the 3-D part (induced angles, interference, the mirror); the
# table does the 2-D viscous part. Profile drag comes from the same lookup.
#
# What this cannot know: three-dimensional separation (spanwise boundary-layer
# flow, a leading-edge vortex on a low, swept blade). Past the first strip's
# break the result is an estimate, flagged per strip in `separated`.


@dataclass(frozen=True)
class ViscousLoads:
    """Loads on one blade from `solve_viscous`. Coefficients use the blade's own area."""

    cl: float                   # force across the flow, in the board plane, / (q·S)
    cd: float                   # induced + profile, along the flow
    cd_induced: float           # near-field, indicative
    cd_profile: float           # from the section table at each strip's incidence
    cl_local: np.ndarray        # (nz,) strip lift along the blade normal / (q · c · dz)
    alpha_eff_deg: np.ndarray   # (nz,) section incidence each strip works at
    separated: np.ndarray       # (nz,) strip past its section's break
    z: np.ndarray               # (nz,) strip stations, m
    x_cp_m: float
    z_cp_m: float


@dataclass(frozen=True)
class ViscousSolution:
    loads: dict[str, ViscousLoads]
    converged: bool
    iterations: int
    residual: float             # largest |section cl − strip cl| at exit
    decamber: np.ndarray        # (all strips,) converged offsets, rad — a warm start


def strip_sections(fin: FinParams, blade: Blade, speed: float) -> list[SectionPolar]:
    """The section polar of every strip of `blade`: local thickness from the
    spanwise schedule, Reynolds number on the local chord at `speed`."""
    return [sections.for_station(fin, speed, c * 1e3, z / blade.depth)
            for z, c in zip(blade.z_mid, blade.chord, strict=True)]


def solve_viscous(blades: list[Blade], polars: dict[str, list[SectionPolar]], speed: float,
                  leeway_deg: float, *, mirror: bool = True, mirror_strength: float = 1.0,
                  relax: float = 0.5, tol: float = 2e-3, max_iter: int = 120,
                  decamber0: np.ndarray | None = None) -> ViscousSolution:
    """`solve` with every strip following its section polar (see the block above).

    `polars[blade.name]` holds one SectionPolar per strip (`strip_sections`).
    `decamber0` warm-starts the iteration from a neighbouring angle. Not
    converged does not raise: past the break several solutions can exist and
    the iteration may hunt between them; `converged` and `residual` say so."""
    if not blades:
        raise ValueError("solve_viscous needs at least one blade")
    cat = lambda k: np.vstack([getattr(b, k) for b in blades])  # noqa: E731
    A, B, ATE, BTE, CP, N = (cat(k) for k in ("A", "B", "ATE", "BTE", "CP", "normal"))
    offsets = np.cumsum([0] + [len(b.z_mid) for b in blades])
    strip = np.concatenate([b.strip + o for b, o in zip(blades, offsets[:-1], strict=True)])
    chord = np.concatenate([b.chord for b in blades])
    dz = np.concatenate([b.dz for b in blades])
    pol = [p for b in blades for p in polars[b.name]]
    if len(pol) != len(chord):
        raise ValueError("polars must hold one SectionPolar per strip of every blade")
    beta = math.radians(leeway_deg)
    d = np.array([math.cos(beta), math.sin(beta), 0.0])
    v_inf = speed * d
    q = 0.5 * RHO_SEAWATER * speed**2

    def influence(P: np.ndarray) -> np.ndarray:
        P = P[:, None, :]
        v = _horseshoe(P, A[None], B[None], ATE[None], BTE[None], d)
        if mirror:
            v = v + mirror_strength * _horseshoe(
                P, (B * _MIRROR)[None], (A * _MIRROR)[None],
                (BTE * _MIRROR)[None], (ATE * _MIRROR)[None], d)
        return v

    aic_inv = np.linalg.inv((influence(CP) * N[:, None, :]).sum(-1))
    mid = influence(0.5 * (A + B))
    rhs0 = -(N @ v_inf)
    # strip lift along the blade normal per unit circulation (Kutta–Joukowski on the freestream)
    kj_n = RHO_SEAWATER * (np.cross(np.broadcast_to(v_inf, A.shape), B - A) * N).sum(-1)
    n_strip = len(chord)
    delta = (np.array([-math.radians(p.alpha0_deg) for p in pol]) if decamber0 is None
             else np.asarray(decamber0, dtype=float).copy())
    two_pi = 2.0 * math.pi
    a_lo, a_hi = math.radians(float(pol[0].alpha_deg[0])), math.radians(float(pol[0].alpha_deg[-1]))
    step_max = math.radians(1.0)
    # Spanwise smoothing of the update, blade by blade. Past the break a strip
    # method has a saw-tooth mode — one strip stalls, its neighbour is driven
    # the other way by the shed vorticity, and the pair runs away. Spreading a
    # quarter of each strip's correction to its neighbours (a discrete
    # diffusion of the UPDATE, not of the solution) removes it and vanishes at
    # convergence, where the update is zero.
    smooth = np.zeros((n_strip, n_strip))
    for o0, o1 in zip(offsets[:-1], offsets[1:], strict=True):
        for k in range(o0, o1):
            lo_k, hi_k = max(k - 1, o0), min(k + 1, o1 - 1)
            smooth[k, k] += 0.5
            smooth[k, lo_k] += 0.25
            smooth[k, hi_k] += 0.25

    def state(dl: np.ndarray):
        g = aic_inv @ (rhs0 - speed * dl[strip])
        c = np.bincount(strip, weights=kj_n * g, minlength=n_strip) / (q * chord * dz)
        a = np.clip(c / two_pi - dl, a_lo, a_hi)
        cv = np.array([float(p.cl_at(math.degrees(x))) for p, x in zip(pol, a, strict=True)])
        return g, c, a, cv - c

    gamma, cl_k, a_eff, resid = state(delta)
    best = (float(np.abs(resid).max()), delta.copy())
    omega, it = relax, 0
    while it < max_iter and best[0] >= tol:
        it += 1
        trial = delta + np.clip(smooth @ (omega * resid / two_pi), -step_max, step_max)
        g2, c2, a2, r2 = state(trial)
        r_max = float(np.abs(r2).max())
        if r_max < best[0]:
            delta, gamma, cl_k, a_eff, resid = trial, g2, c2, a2, r2
            best = (r_max, trial.copy())
            omega = min(omega * 1.15, relax)
        else:                              # overshoot: keep the iterate, shorten the step
            omega *= 0.5
            if omega < 1e-3:
                break
    resid_max = best[0]
    converged = resid_max < tol

    v_local = v_inf + (mid * gamma[None, :, None]).sum(1)
    force = RHO_SEAWATER * gamma[:, None] * np.cross(v_local, B - A)
    lift_dir = np.array([-math.sin(beta), math.cos(beta), 0.0])
    a_deg = np.degrees(a_eff)
    cd_k = np.array([float(p.cd_at(a)) for p, a in zip(pol, a_deg, strict=True)])
    sep = np.array([a > p.alpha_break_deg for p, a in zip(pol, a_deg, strict=True)])
    out: dict[str, ViscousLoads] = {}
    i0 = 0
    for b, o in zip(blades, offsets[:-1], strict=True):
        n, nz = b.n_panels, len(b.z_mid)
        f = force[i0:i0 + n]
        lift = f @ lift_dir
        strip_lift = np.bincount(b.strip, weights=lift, minlength=nz)
        total = float(lift.sum())
        ok = abs(total) > 1e-12
        cdi = float((f @ d).sum()) / (q * b.area)
        cdp = float((cd_k[o:o + nz] * b.chord * b.dz).sum()) / b.area
        out[b.name] = ViscousLoads(
            cl=total / (q * b.area), cd=cdi + cdp, cd_induced=cdi, cd_profile=cdp,
            cl_local=cl_k[o:o + nz].copy(), alpha_eff_deg=a_deg[o:o + nz].copy(),
            separated=sep[o:o + nz].copy(), z=b.z_mid,
            x_cp_m=float((lift * b.xq_local).sum() / total) if ok else float("nan"),
            z_cp_m=float((strip_lift * b.z_mid).sum() / total) if ok else float("nan"))
        i0 += n
    return ViscousSolution(loads=out, converged=converged, iterations=it, residual=resid_max,
                           decamber=delta)


def viscous_polar(fin: FinParams, speed: float, angles_deg, *, nz: int = 12,
                  nx: int = 3) -> list[tuple[float, ViscousLoads, bool]]:
    """Polar of one blade alone on the mirror: (angle, loads, converged) per angle,
    each angle warm-started from the one before."""
    b = blade_from_fin("blade", fin, nz=nz, nx=nx)
    pol = {"blade": strip_sections(fin, b, speed)}
    rows, warm = [], None
    for a in angles_deg:
        sol = solve_viscous([b], pol, speed, float(a), decamber0=warm)
        warm = sol.decamber
        rows.append((float(a), sol.loads["blade"], sol.converged))
    return rows
