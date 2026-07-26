"""Parameter schema for fin generation.

Design principle (docs/PHYSICS.md, discussion in docs/FIN-PRIMER.md): every
parameter is independent, geometry-generating and bounded; composite quantities
(area, aspect ratio) are derived and reported, never inputs. Defaults anchor to
cited values — dimensions to a medium thruster side fin [FCS26], section
thickness to the measured baseline fin [BW04], placement to production
conventions [Gre26, Falk20]. Keys refer to docs/SOURCES.md.

Units: millimetres and degrees throughout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FoilFamily(Enum):
    """Cross-section family (docs/FIN-PRIMER.md §4)."""

    SYMMETRIC = "symmetric"  # 50/50 center-fin foil [FCS26]
    FLAT_INSIDE = "flat_inside"  # classic flat-foil side fin [BW04, Fut26]
    CAMBERED = "cambered"  # 70/30-style intermediate

class TabSystem(Enum):
    """Mounting system (docs/TAB-SYSTEMS.md; generic names are deliberate —
    descriptive compatibility only, no brand styling)."""

    NONE = "none"  # flat base, no mounting tabs
    DUAL_TAB = "dual_tab"  # FCS-compatible twin tabs
    SINGLE_TAB = "single_tab"  # Futures-compatible full-base tab
    CLICK_TAB = "click_tab"  # FCS II-compatible tool-less tabs


class FinConfig(Enum):
    SINGLE = "single"
    TWIN = "twin"
    THRUSTER = "thruster"
    QUAD = "quad"
    TWO_PLUS_ONE = "two_plus_one"


class GrooveSurface(Enum):
    """Which foil face carries the thinning grooves [Els22]."""

    OUTER = "outer"  # G1 variant: convex face only
    BOTH = "both"  # G2 variant: both faces (not buildable on flat-inside foils)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class FoilParams:
    """Section (hydrofoil profile) parameters.

    thickness_ratio: max section thickness / chord at the base station [BW04].
    camber_ratio / camber_position: NACA m and p [Jac33]; camber_ratio is
        ignored for SYMMETRIC and implied by construction for FLAT_INSIDE.
    te_thickness: printability truncation of the trailing edge in mm, applied
        after the analytic section is generated.
    """

    family: FoilFamily = FoilFamily.SYMMETRIC
    thickness_ratio: float = 0.09
    camber_ratio: float = 0.0
    camber_position: float = 0.4
    te_thickness: float = 0.7

    def __post_init__(self) -> None:
        _require(0.04 <= self.thickness_ratio <= 0.15,
                 f"thickness_ratio {self.thickness_ratio} outside 0.04–0.15")
        # Upper bound is the demonstrated buildable limit of the NACA
        # perpendicular construction through the loft (higher cambers fold at
        # the LE and defeat spanwise skinning), and already exceeds realistic
        # fin-section cambers (~2-4%). Pinned by test_geometry.
        _require(0.0 <= self.camber_ratio <= 0.05,
                 f"camber_ratio {self.camber_ratio} outside 0–0.05")
        _require(0.2 <= self.camber_position <= 0.6,
                 f"camber_position {self.camber_position} outside 0.2–0.6")
        _require(0.4 <= self.te_thickness <= 1.2,
                 f"te_thickness {self.te_thickness} mm outside 0.4–1.2 mm")


@dataclass(frozen=True)
class OutlineParams:
    """Planform parameters (docs/PHYSICS.md §3).

    sweep: angle between the base-normal and the line from base-LE to the tip
        lobe's endpoint; positions the lobe at x = depth·tan(sweep). On real
        templates the tip sits above/behind the TE base corner, i.e. geometric
        sweep ≈ atan(base/depth) or more — larger than the number printed on
        commercial fins, whose "sweep" is measured differently.
    tip_width_ratio: width of the rounded tip lobe as a fraction of base (the
        chord where the elliptical tip rounding begins).
    le_fullness: 0 = straight leading edge, 1 = maximum forward fullness
        (edge hugs the vertical low on the span).
    te_shape: −1 = maximum concave cutaway (the common commercial look),
        0 = straight, +1 = maximum convex fullness (keel-like).
    le_dx / te_dx: LEVEL-2 (optimizer-facing) streamwise offsets in mm for
        the six interior Bézier control points of each edge, applied on top
        of the slider-generated polygon. The sliders above are the level-1
        human/template interface; the offsets give an optimizer the full
        degree-7 Bézier family (Bernstein basis completeness [Kul08]), so it
        can converge to the template defaults, commercial-like shapes, or
        something else entirely. Bounded to ±0.3·base; invalid combinations
        are rejected by the planform edge-crossing check.
    """

    depth: float = 115.0
    base: float = 110.0
    sweep: float = 33.0
    tip_width_ratio: float = 0.40
    le_fullness: float = 0.65
    te_shape: float = -0.3
    le_dx: tuple[float, ...] = (0.0,) * 6
    te_dx: tuple[float, ...] = (0.0,) * 6

    def __post_init__(self) -> None:
        _require(40.0 <= self.depth <= 300.0, f"depth {self.depth} mm outside 40–300 mm")
        _require(40.0 <= self.base <= 250.0, f"base {self.base} mm outside 40–250 mm")
        _require(0.0 <= self.sweep <= 60.0, f"sweep {self.sweep}° outside 0–60°")
        _require(0.05 <= self.tip_width_ratio <= 0.6,
                 f"tip_width_ratio {self.tip_width_ratio} outside 0.05–0.6")
        _require(0.0 <= self.le_fullness <= 1.0,
                 f"le_fullness {self.le_fullness} outside 0–1")
        _require(-1.0 <= self.te_shape <= 1.0,
                 f"te_shape {self.te_shape} outside −1–1")
        for name, dx in (("le_dx", self.le_dx), ("te_dx", self.te_dx)):
            _require(len(dx) == 6, f"{name} needs exactly 6 offsets, got {len(dx)}")
            _require(all(abs(v) <= 0.3 * self.base for v in dx),
                     f"{name} offsets exceed ±0.3·base ({0.3 * self.base:.0f} mm)")


@dataclass(frozen=True)
class TabParams:
    """Mounting-tab parameters (docs/TAB-SYSTEMS.md).

    fit_offset: added to the nominal tab thickness, mm. Community print
        practice starts ~0.2 mm undersize; calibrate with `fingen coupon`
        against your actual boxes.
    tab_depth: override the system's insertion depth (None = system default;
        note Futures boxes come in 3/4" side and 1/2" center depths — the
        default fits side boxes).
    click_indent_depth: per-side depth of the click-tab retention indents;
        0 disables them (printed indents deform after some cycles — the
        box's grub screws are the standard fallback).
    x_offset: slides the whole tab set along the base chord, mm (+ = toward
        the trailing edge). Tabs may overhang the base ends — commercial
        click fins align the rear indent with the fin's aft end, and small
        fins need overhang for the set to fit at all — but each tab must
        keep ≥ half its length (min 8 mm) engaged under the base (checked
        at build time with a per-tab message).
    y_offset: shifts the tabs across the section thickness, mm, applied on
        top of the family anchor: FLAT_INSIDE fins anchor the tab's inner
        face flush with the y = 0 flat plane (bed-flat printing, matching
        commercial flat-foiled fins) and accept only y_offset ≥ 0 — a
        negative value would protrude past the flat plane, defeating the
        anchor (rejected at FinParams construction); other families center
        the tab on the base section's mid-thickness and take the full ±3.
    """

    system: TabSystem = TabSystem.NONE
    fit_offset: float = -0.2
    tab_depth: float | None = None
    click_indent_depth: float = 0.9
    x_offset: float = 0.0
    y_offset: float = 0.0

    def __post_init__(self) -> None:
        _require(-0.6 <= self.fit_offset <= 0.4,
                 f"fit_offset {self.fit_offset} mm outside −0.6–0.4 mm")
        _require(self.tab_depth is None or 8.0 <= self.tab_depth <= 20.0,
                 f"tab_depth {self.tab_depth} mm outside 8–20 mm")
        _require(0.0 <= self.click_indent_depth <= 1.5,
                 f"click_indent_depth {self.click_indent_depth} mm outside 0–1.5 mm")
        _require(-40.0 <= self.x_offset <= 40.0,
                 f"tab x_offset {self.x_offset} mm outside ±40 mm")
        _require(-3.0 <= self.y_offset <= 3.0,
                 f"tab y_offset {self.y_offset} mm outside ±3 mm")


@dataclass(frozen=True)
class GrooveParams:
    """Spanwise thinning grooves [Els22, For24]: horizontal channels cut into
    the foil over the upper span, thinning the section locally. Their CFD
    reports +11 % L/D at high incidence (drag −13 %, lift −3.8 % at 30°) and
    their bench test shows the grooved blade is measurably more flexible —
    the channels double as flex hinges. The papers give count/length/spacing
    but not depth, width or profile: those are free parameters here (and for
    the optimizer). count=0 disables the feature entirely.

    count: number of grooves (0 = none).
    length: chordwise extent from the leading edge, mm; each groove fades out
        by 85 % of the local chord so the trailing-edge band stays full
        thickness (printable TE).
    pitch: spanwise center-to-center spacing, mm.
    width: spanwise width of each channel, mm (≤ pitch; equal = contiguous
        scalloping).
    depth_ratio: fraction of the local per-side thickness removed at the
        channel center.
    span_start: first groove center as a fraction of depth.
    surface: OUTER (G1 [Els22]) or BOTH (G2); flat-inside foils only accept
        OUTER (the inner face is the print bed).
    """

    count: int = 0
    length: float = 60.0
    pitch: float = 6.0
    width: float = 3.0
    depth_ratio: float = 0.35
    span_start: float = 0.45
    surface: GrooveSurface = GrooveSurface.OUTER

    def __post_init__(self) -> None:
        _require(0 <= self.count <= 12, f"groove count {self.count} outside 0–12")
        _require(5.0 <= self.length <= 200.0,
                 f"groove length {self.length} mm outside 5–200 mm")
        _require(2.0 <= self.pitch <= 40.0,
                 f"groove pitch {self.pitch} mm outside 2–40 mm")
        _require(1.0 <= self.width <= self.pitch,
                 f"groove width {self.width} mm outside 1 mm – pitch ({self.pitch} mm)")
        _require(0.05 <= self.depth_ratio <= 0.6,
                 f"groove depth_ratio {self.depth_ratio} outside 0.05–0.6")
        _require(0.05 <= self.span_start <= 0.85,
                 f"groove span_start {self.span_start} outside 0.05–0.85")


@dataclass(frozen=True)
class FinParams:
    """A single fin blade: outline × foil × spanwise schedules × mounting.

    thickness_tip_factor: t/c at the tip relative to the base — tip-thinning
        washes out tip loading (softens the tip-first stall of [BW04]).
    """

    outline: OutlineParams = field(default_factory=OutlineParams)
    foil: FoilParams = field(default_factory=FoilParams)
    thickness_tip_factor: float = 0.85
    tabs: TabParams = field(default_factory=TabParams)
    grooves: GrooveParams = field(default_factory=GrooveParams)

    def __post_init__(self) -> None:
        _require(0.5 <= self.thickness_tip_factor <= 1.2,
                 f"thickness_tip_factor {self.thickness_tip_factor} outside 0.5–1.2")
        if (self.tabs.system is not TabSystem.NONE
                and self.foil.family is FoilFamily.FLAT_INSIDE):
            _require(self.tabs.y_offset >= 0.0,
                     f"tab y_offset {self.tabs.y_offset} mm is negative on a "
                     "flat-inside fin: the tab anchors flush with the flat "
                     "face, and a negative offset would protrude past the "
                     "flat plane (defeats bed-flat printing); use ≥ 0")
        if self.grooves.count:
            _require(self.foil.family is not FoilFamily.FLAT_INSIDE
                     or self.grooves.surface is GrooveSurface.OUTER,
                     "flat-inside foils carry the print-bed face inboard; "
                     "grooves there must use surface=OUTER")
            band_top = (self.grooves.span_start * self.outline.depth
                        + (self.grooves.count - 1) * self.grooves.pitch
                        + 0.5 * self.grooves.width)
            _require(band_top <= 0.9 * self.outline.depth,
                     f"groove band reaches {band_top:.1f} mm, beyond 90 % of the "
                     f"{self.outline.depth} mm depth — fewer grooves, tighter "
                     "pitch, or lower span_start")
            band_bottom = (self.grooves.span_start * self.outline.depth
                           - 0.5 * self.grooves.width)
            _require(band_bottom >= 0.12 * self.outline.depth,
                     f"groove band starts {band_bottom:.1f} mm from the base, "
                     f"inside 12 % of the {self.outline.depth} mm depth — the "
                     "root section must stay full thickness (tab junction and "
                     "root bending stress both assume it)")


def _default_side() -> FinParams:
    return FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))


def _default_center() -> FinParams:
    return FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC))


@dataclass(frozen=True)
class FinSetParams:
    """A complete fin set: per-slot blades plus placement angles and positions.

    Toe and cant are placement transforms applied at assembly (fingen.assembly),
    not baked into the blade geometry — one blade solid serves left/right via
    mirroring [export.mirror_hand]. All positions live in the ASSEMBLY FRAME,
    which coincides with each blade's own frame (docs/PHYSICS.md §2b):

        +x  aft, toward the board's tail   (a blade's LE is at local x=0, TE aft)
        +y  toward the RIGHT rail (starboard) = outboard for the right-hand fin
        +z  up, out of the board bottom     (blades hang in z ≥ 0; board = z=0)

    The origin is the center-fin base center. Side positions are that blade's
    base-center offset FROM the origin: side_x is therefore NEGATIVE for the
    forward-of-center thruster/quad fronts [Gre26], and the right fin sits at
    +side_y, the left at −side_y.

    toe/cant are the front (side) fins' toe-in and cant magnitudes; rear_* are
    the quad rear pair's own placement. Defaults follow production conventions
    [Gre26] (thruster fronts 1/4″ ≈ 3–4° toe, 7–9° cant; quad rears 1/8–3/16″ ≈
    1.5–2.5° toe, 3–5° cant) and CFD'd production setups toe 3.5°/cant 8.5°
    [Falk20]. Fore-aft/lateral offsets are representative shortboard cluster
    spacing (front fins ≈ 8″ ahead of the rear box, ≈ 4.6″ off the stringer
    [Gre26]); the true value is board-width dependent, so the lateral bounds
    stay loose and the *minimum safe spacing* — which depends on blade
    thickness, toe and cant — is enforced geometrically at assembly (an
    overlap check), not by a scalar bound.
    """

    config: FinConfig = FinConfig.THRUSTER
    center: FinParams | None = field(default_factory=_default_center)
    side: FinParams | None = field(default_factory=_default_side)
    toe: float = 3.5
    cant: float = 8.0
    side_x: float = -195.0  # side-fin base-center aft-offset (forward = negative)
    side_y: float = 118.0  # side-fin base-center outboard offset (right fin +)
    rear_x: float = -60.0  # quad rear pair aft-offset (aft of the fronts)
    rear_y: float = 95.0  # quad rear pair outboard offset
    rear_toe: float = 2.0  # quad rear toe-in [Gre26: 1/8–3/16″]
    rear_cant: float = 4.0  # quad rear cant [Gre26: 3–5°]

    def __post_init__(self) -> None:
        needs_center = self.config in (FinConfig.SINGLE, FinConfig.THRUSTER,
                                       FinConfig.TWO_PLUS_ONE)
        needs_side = self.config in (FinConfig.TWIN, FinConfig.THRUSTER,
                                     FinConfig.QUAD, FinConfig.TWO_PLUS_ONE)
        _require(not (needs_center and self.center is None),
                 f"{self.config.value} requires a center fin definition")
        _require(not (needs_side and self.side is None),
                 f"{self.config.value} requires a side fin definition")
        _require(0.0 <= self.toe <= 6.0, f"toe {self.toe}° outside 0–6°")
        _require(0.0 <= self.cant <= 12.0, f"cant {self.cant}° outside 0–12°")
        _require(0.0 <= self.rear_toe <= 6.0, f"rear_toe {self.rear_toe}° outside 0–6°")
        _require(0.0 <= self.rear_cant <= 12.0, f"rear_cant {self.rear_cant}° outside 0–12°")
        # Fore-aft: forward (negative) dominant, small aft allowance. Lateral:
        # strictly outboard and bounded only for sanity — the real minimum is
        # the assembly overlap check (blade-thickness/toe/cant dependent).
        for name, vx in (("side_x", self.side_x), ("rear_x", self.rear_x)):
            _require(-300.0 <= vx <= 100.0, f"{name} {vx} mm outside −300–100 mm")
        for name, vy in (("side_y", self.side_y), ("rear_y", self.rear_y)):
            _require(0.0 < vy <= 400.0, f"{name} {vy} mm outside 0–400 mm (must be outboard)")


@dataclass(frozen=True)
class GenSettings:
    """Resolution settings: changing these must leave the design unchanged
    within the tolerances enforced by the resolution-invariance tests (a
    B-spline skin necessarily depends on its stations, but only at the
    sub-percent level)."""

    n_stations: int = 15
    n_foil_points: int = 100  # total contour points per section (~half per surface)
    cap_chord: float = 3.0  # chord of the last lofted section before the tip cap,
    # mm; large caps make OCCT's cone-to-vertex degenerate on squat outlines
    # (found by the hypothesis sweep), so this is numerical, not design

    def __post_init__(self) -> None:
        _require(7 <= self.n_stations <= 60, f"n_stations {self.n_stations} outside 7–60")
        _require(40 <= self.n_foil_points <= 400,
                 f"n_foil_points {self.n_foil_points} outside 40–400")
        _require(1.5 <= self.cap_chord <= 6.0,
                 f"cap_chord {self.cap_chord} mm outside 1.5–6 mm")


DEFAULT_SETTINGS = GenSettings()
