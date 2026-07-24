"""Planform outline: the fin's silhouette viewed from the side.

Planned implementation (after docs/PHYSICS.md): leading and trailing edge as
Bézier curves controlled by depth, base, sweep and tip fullness, from which the
spanwise chord/offset schedule is sampled for lofting.
"""

from __future__ import annotations

from fingen.params import FinParams


def chord_schedule(
    fin: FinParams, n_stations: int = 12
) -> list[tuple[float, float, float]]:
    """Return (z, leading_edge_x, chord) at each spanwise station [mm]."""
    raise NotImplementedError("implemented once the outline math is pinned down in docs/PHYSICS.md")
