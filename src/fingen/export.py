"""Geometry export: STEP for CAD interchange, STL for slicing/3D printing.

Handedness: side fins are chiral (the flat/inner face looks toward the
board's centerline), so a twin or thruster set needs one fin of each hand.
The generator builds the RIGHT-hand blade (foil bulging toward +y);
`mirror_hand` returns its left-hand mirror image. Build and CHECK the
canonical right-hand solid first — the checker's flat-face conventions
assume it — then mirror for export.

Split halves: a symmetric center fin can be printed as two flat-faced
halves (each lies flat on the bed, no supports, clean surfaces) glued at
the section midplane. The two halves are a MIRROR PAIR, not two copies:
a physical flip is a rotation, and no rotation of one half produces its
mate. `split_halves` therefore returns both.
"""

from __future__ import annotations

from pathlib import Path

from build123d import Box, Part, Plane, Pos, mirror
from build123d import export_step as _export_step
from build123d import export_stl as _export_stl

_HALF = 3000.0  # half-space box size, mm — safely beyond any buildable fin


def mirror_hand(part: Part) -> Part:
    """The opposite-hand blade: mirror across the XZ plane (y → −y)."""
    return Part() + mirror(part, about=Plane.XZ)


def split_halves(part: Part) -> tuple[Part, Part]:
    """Cut the solid at the y = 0 midplane into (y ≥ 0 half, y ≤ 0 half).

    Meaningful for symmetric sections, where both cut faces are flat
    print-bed planes; the caller enforces the family restriction (flat-
    inside fins already print flat whole, cambered midplanes aren't flat).
    """
    upper = Pos(0.0, _HALF / 2.0, 0.0) * Box(2 * _HALF, _HALF, 2 * _HALF)
    lower = Pos(0.0, -_HALF / 2.0, 0.0) * Box(2 * _HALF, _HALF, 2 * _HALF)
    return Part() + (part & upper), Part() + (part & lower)


def to_step(part: Part, path: str | Path) -> Path:
    """Write the part to a STEP file (AP214), creating parent dirs as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _export_step(part, str(path))
    return path


def to_stl(part: Part, path: str | Path) -> Path:
    """Write the part to a binary STL, creating parent dirs as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _export_stl(part, str(path))
    return path
