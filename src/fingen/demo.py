"""Placeholder geometry proving the CAD pipeline end to end.

This is NOT a real fin — it lofts crude elliptical sections along a swept span
purely to validate that build123d/OCCT, lofting and STEP/STL export all work on
this machine. It gets replaced by outline.py + foil.py + loft.py.
"""

from __future__ import annotations

from build123d import Ellipse, Part, Plane, Pos, loft


def demo_solid() -> Part:
    """Loft a swept, tapering stack of elliptical sections (a fin-shaped blob)."""
    stations = [
        # (z along span, sweep offset x, chord) in mm
        (0.0, 0.0, 110.0),
        (50.0, 15.0, 90.0),
        (90.0, 35.0, 60.0),
        (115.0, 55.0, 25.0),
    ]
    sections = [
        Plane.XY.offset(z) * Pos(x + chord / 2.0, 0.0) * Ellipse(chord / 2.0, chord * 0.04)
        for z, x, chord in stations
    ]
    return loft(sections)
