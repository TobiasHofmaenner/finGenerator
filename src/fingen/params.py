"""Parameter schema for fin generation.

Defaults and sane ranges follow docs/PHYSICS.md §2 (citation keys refer to
docs/SOURCES.md): dimensions anchor to a medium thruster side fin [FCS26],
section thickness to the measured baseline fin [BW04], placement angles to
production conventions and CFD-studied setups [Gre26, Falk20].

Geometry conventions (industry-standard fin measurements):
  depth  — distance from the base plane to the tip ("height" in aero terms, the span)
  base   — chord length where the fin meets the board
  sweep  — rake angle of the leading edge relative to the base-normal
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FoilParams:
    """Cross-section (hydrofoil profile) parameters.

    thickness_ratio: max thickness as a fraction of chord (t/c).
    camber_ratio: max camber as a fraction of chord; 0 for a symmetric section
        (center fins). Side fins are traditionally cambered with a flat inner face.
    flat_inside: if True, the section is flat on the board-side face and all
        thickness/camber goes to the outer face (classic side-fin foil).
    """

    thickness_ratio: float = 0.09
    camber_ratio: float = 0.0
    flat_inside: bool = False

    def __post_init__(self) -> None:
        if not 0.02 <= self.thickness_ratio <= 0.25:
            raise ValueError(f"thickness_ratio {self.thickness_ratio} outside sane range 0.02–0.25")
        if not 0.0 <= self.camber_ratio <= 0.12:
            raise ValueError(f"camber_ratio {self.camber_ratio} outside sane range 0–0.12")


@dataclass(frozen=True)
class FinParams:
    """A single fin blade. Flat base for now; tab systems (FCS II, Futures) later."""

    depth: float = 115.0
    base: float = 110.0
    sweep: float = 33.0
    tip_chord_ratio: float = 0.35
    foil: FoilParams = field(default_factory=FoilParams)

    def __post_init__(self) -> None:
        if not 40.0 <= self.depth <= 300.0:
            raise ValueError(f"depth {self.depth} mm outside sane range 40–300 mm")
        if not 40.0 <= self.base <= 250.0:
            raise ValueError(f"base {self.base} mm outside sane range 40–250 mm")
        if not 0.0 <= self.sweep <= 60.0:
            raise ValueError(f"sweep {self.sweep}° outside sane range 0–60°")
        if not 0.05 <= self.tip_chord_ratio <= 0.9:
            raise ValueError(f"tip_chord_ratio {self.tip_chord_ratio} outside sane range 0.05–0.9")


@dataclass(frozen=True)
class FinSetParams:
    """A complete fin set: per-position blades plus set-level placement angles.

    toe: toe-in of the side fins relative to the board centerline.
    cant: outward lean of the side fins from vertical.
    """

    center: FinParams | None = None
    side: FinParams | None = None
    toe: float = 3.5
    cant: float = 8.0

    def __post_init__(self) -> None:
        if self.center is None and self.side is None:
            raise ValueError("fin set needs at least a center or side fin definition")
        if not 0.0 <= self.toe <= 6.0:
            raise ValueError(f"toe {self.toe}° outside sane range 0–6°")
        if not 0.0 <= self.cant <= 12.0:
            raise ValueError(f"cant {self.cant}° outside sane range 0–12°")
