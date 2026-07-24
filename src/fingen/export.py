"""Geometry export: STEP for CAD interchange, STL for slicing/3D printing."""

from __future__ import annotations

from pathlib import Path

from build123d import Part
from build123d import export_step as _export_step
from build123d import export_stl as _export_stl


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
