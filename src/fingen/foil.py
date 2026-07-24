"""Foil section generation: 2D hydrofoil profiles for a given chord.

Planned implementation (after docs/PHYSICS.md is written): NACA 4-digit-style
thickness distribution with configurable camber line, plus the flat-inside
variant used on side fins. Output is a closed 2D point loop suitable for a
build123d sketch, with a finite trailing-edge thickness for printability.
"""

from __future__ import annotations

from fingen.params import FoilParams


def section_points(
    foil: FoilParams, chord: float, n_points: int = 80
) -> list[tuple[float, float]]:
    """Return the closed (x, y) loop of the foil section at the given chord [mm]."""
    raise NotImplementedError("implemented once the section math is pinned down in docs/PHYSICS.md")
