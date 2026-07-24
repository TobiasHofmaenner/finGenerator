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

class FinConfig(Enum):
    SINGLE = "single"
    TWIN = "twin"
    THRUSTER = "thruster"
    QUAD = "quad"
    TWO_PLUS_ONE = "two_plus_one"


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
    """

    depth: float = 115.0
    base: float = 110.0
    sweep: float = 42.0
    tip_width_ratio: float = 0.28
    le_fullness: float = 0.65
    te_shape: float = -0.2

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


@dataclass(frozen=True)
class FinParams:
    """A single fin blade: outline × foil × spanwise schedules.

    thickness_tip_factor: t/c at the tip relative to the base — tip-thinning
        washes out tip loading (softens the tip-first stall of [BW04]).
    """

    outline: OutlineParams = field(default_factory=OutlineParams)
    foil: FoilParams = field(default_factory=FoilParams)
    thickness_tip_factor: float = 0.85

    def __post_init__(self) -> None:
        _require(0.5 <= self.thickness_tip_factor <= 1.2,
                 f"thickness_tip_factor {self.thickness_tip_factor} outside 0.5–1.2")


def _default_side() -> FinParams:
    return FinParams(foil=FoilParams(family=FoilFamily.FLAT_INSIDE))


def _default_center() -> FinParams:
    return FinParams(foil=FoilParams(family=FoilFamily.SYMMETRIC))


@dataclass(frozen=True)
class FinSetParams:
    """A complete fin set: per-slot blades plus placement angles.

    Toe and cant are placement transforms applied at assembly, not baked into
    the blade geometry — one blade solid serves left/right via mirroring.
    """

    config: FinConfig = FinConfig.THRUSTER
    center: FinParams | None = field(default_factory=_default_center)
    side: FinParams | None = field(default_factory=_default_side)
    toe: float = 3.5
    cant: float = 8.0

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
