"""Assembly of the 3D fin solid: foil sections placed along the outline, lofted.

Planned implementation (after docs/PHYSICS.md): sample the outline's chord
schedule, generate a foil section per station, place each on its spanwise plane,
loft to a solid, then close the base flat (tab systems come later).
"""

from __future__ import annotations

from build123d import Part

from fingen.params import FinParams


def fin_solid(fin: FinParams) -> Part:
    """Build the solid for a single fin, base plane at Z=0, tip at Z=depth."""
    raise NotImplementedError("implemented once outline + foil generation land")
