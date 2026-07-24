"""Geometry validation: is the generated shape actually a closed manifold solid
that matches its own math?

A random-but-in-range parameter vector is not guaranteed to survive OCCT
lofting as a watertight solid, so every generated blade goes through
check_solid() before export. Checks, in order of increasing subtlety:

1. topology — exactly one solid, OCCT-valid (BRepCheck), manifold/watertight;
2. size — bounding box matches depth/base/thickness expectations;
3. self-consistency — the solid's volume agrees with the analytic volume
   integral of the section areas over the chord schedule (catches silent loft
   distortion, the failure mode of incompatible skinning [PT02]).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from build123d import Part, Solid
from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCP.TopoDS import TopoDS_Iterator

from fingen.foil import section_points
from fingen.outline import chord_schedule, metrics
from fingen.params import DEFAULT_SETTINGS, FinParams, FoilFamily, GenSettings

_VOLUME_TOLERANCE = 0.20  # tip-cap region is approximated; see docstring
_BBOX_TOLERANCE = 1.0  # mm


@dataclass
class CheckReport:
    ok: bool = True
    issues: list[str] = field(default_factory=list)
    volume: float = 0.0  # mm³
    expected_volume: float = 0.0  # mm³
    area: float = 0.0  # planform mm² (from the outline math)
    aspect_ratio: float = 0.0

    def fail(self, message: str) -> None:
        self.ok = False
        self.issues.append(message)


def _section_area(fin: FinParams, z: float, chord: float,
                  settings: GenSettings) -> float:
    from fingen.loft import _thickness_at

    upper, lower = section_points(fin.foil, chord, thickness_ratio=_thickness_at(fin, z),
                                  n_points=settings.n_foil_points)
    lo = np.interp(upper[:, 0], lower[:, 0], lower[:, 1])
    return float(np.trapezoid(upper[:, 1] - lo, upper[:, 0]))


def expected_volume(fin: FinParams, settings: GenSettings = DEFAULT_SETTINGS) -> float:
    """Analytic volume estimate: ∫ A_section(z) dz over the chord schedule."""
    fine = GenSettings(n_stations=40, n_foil_points=settings.n_foil_points)
    stations = chord_schedule(fin.outline, fine, tip_chord_min=settings.cap_chord)
    zs = np.array([st.z for st in stations])
    areas = np.array([_section_area(fin, st.z, st.chord, fine) for st in stations])
    return float(np.trapezoid(areas, zs))


def _free_bound_count(solid: Solid) -> int:
    """Number of free (unshared) boundary wires — 0 for a watertight shell.

    build123d's is_manifold is not usable here: it false-positives on legal
    apex/seam topology (it reports even a primitive cone or sphere as
    non-manifold), which a vertex-capped loft naturally contains.
    """
    bounds = ShapeAnalysis_FreeBounds(solid.wrapped)
    count = 0
    for compound in (bounds.GetOpenWires(), bounds.GetClosedWires()):
        it = TopoDS_Iterator(compound)
        while it.More():
            count += 1
            it.Next()
    return count


def check_solid(part: Part, fin: FinParams,
                settings: GenSettings = DEFAULT_SETTINGS) -> CheckReport:
    """Validate a lofted blade against topology, size and its own math."""
    report = CheckReport()

    solids = part.solids()
    if len(solids) != 1:
        report.fail(f"expected exactly 1 solid, got {len(solids)}")
        return report
    solid = solids[0]
    if not part.is_valid:
        report.fail("OCCT BRepCheck reports an invalid shape")
    shells = solid.shells()
    if len(shells) != 1:
        report.fail(f"expected exactly 1 shell, got {len(shells)} (internal voids?)")
    elif not shells[0].wrapped.Closed():
        report.fail("shell is not closed (not watertight)")
    free_bounds = _free_bound_count(solid)
    if free_bounds:
        report.fail(f"{free_bounds} free boundary wire(s) — surface has open seams")

    bbox = part.bounding_box()
    out = fin.outline
    if abs(bbox.max.Z - out.depth) > _BBOX_TOLERANCE or abs(bbox.min.Z) > _BBOX_TOLERANCE:
        report.fail(f"span extent [{bbox.min.Z:.2f}, {bbox.max.Z:.2f}] mm does not "
                    f"match depth {out.depth} mm")
    max_t = fin.foil.thickness_ratio * out.base + fin.foil.te_thickness
    y_extent = bbox.max.Y - bbox.min.Y
    if y_extent > max_t + _BBOX_TOLERANCE:
        report.fail(f"thickness extent {y_extent:.2f} mm exceeds section maximum "
                    f"{max_t:.2f} mm")
    if fin.foil.family is FoilFamily.FLAT_INSIDE and bbox.min.Y < -_BBOX_TOLERANCE:
        report.fail(f"flat face should lie at y = 0 but bbox reaches y = {bbox.min.Y:.2f}")

    report.volume = part.volume
    report.expected_volume = expected_volume(fin, settings)
    if report.volume <= 0.0:
        report.fail("non-positive volume")
    elif abs(report.volume - report.expected_volume) > _VOLUME_TOLERANCE * report.expected_volume:
        report.fail(f"solid volume {report.volume:.0f} mm³ deviates from analytic "
                    f"estimate {report.expected_volume:.0f} mm³ by more than "
                    f"{_VOLUME_TOLERANCE:.0%}")

    m = metrics(out)
    report.area = m.area
    report.aspect_ratio = m.aspect_ratio
    return report
