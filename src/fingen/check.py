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
from build123d import Box, Part, Pos, Solid
from OCP.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCP.TopoDS import TopoDS_Iterator

from fingen.foil import section_points
from fingen.outline import chord_schedule, metrics
from fingen.params import DEFAULT_SETTINGS, FinParams, FoilFamily, GenSettings

_VOLUME_TOLERANCE = 0.15  # tip-cap region is approximated; see docstring
_SLICE_TOLERANCE = 0.15  # per-slab mid-span cross-section agreement
_BBOX_TOLERANCE = 1.5  # mm
_FLAT_FACE_TOLERANCE = 0.15  # mm — a fraction of a print layer height


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
    fine = GenSettings(n_stations=40, n_foil_points=settings.n_foil_points,
                       cap_chord=settings.cap_chord)
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
    fine = GenSettings(n_stations=40, n_foil_points=settings.n_foil_points,
                       cap_chord=settings.cap_chord)
    stations = chord_schedule(fin.outline, fine, tip_chord_min=settings.cap_chord)

    # Two separate span statements: the solid must match ITS SCHEDULE tightly,
    # and the schedule's cap truncation must be small relative to the fin
    # (slim high-AR blades legitimately lose a bit more absolute span).
    z_top = stations[-1].z
    if abs(bbox.max.Z - z_top) > _BBOX_TOLERANCE or abs(bbox.min.Z) > _BBOX_TOLERANCE:
        report.fail(f"span extent [{bbox.min.Z:.2f}, {bbox.max.Z:.2f}] mm does not "
                    f"match schedule top {z_top:.2f} mm")
    if out.depth - z_top > max(_BBOX_TOLERANCE, 0.012 * out.depth):
        report.fail(f"tip cap truncates {out.depth - z_top:.2f} mm of span "
                    f"(depth {out.depth} mm)")

    # Skin interpolation error grows with station spacing squared — coarse
    # lofts get honest slack in the size guards; default-and-finer stays tight.
    res_slack = max(1.0, (15.0 / settings.n_stations) ** 2)

    # Thickness bound from the actual section math at the worst case: the
    # largest chord in the schedule (fullness overshoot pushes chords beyond
    # the base) at the largest spanwise thickness factor, camber included.
    c_max = max(st.chord for st in stations)
    t_max = fin.foil.thickness_ratio * max(1.0, fin.thickness_tip_factor)
    su, sl = section_points(fin.foil, c_max, thickness_ratio=t_max,
                            n_points=settings.n_foil_points)
    y_bound = float(max(su[:, 1].max(), sl[:, 1].max())
                    - min(su[:, 1].min(), sl[:, 1].min()))
    y_extent = bbox.max.Y - bbox.min.Y
    if y_extent > y_bound * (1.0 + 0.05 * res_slack) + _BBOX_TOLERANCE:
        report.fail(f"thickness extent {y_extent:.2f} mm exceeds section maximum "
                    f"{y_bound:.2f} mm")
    if fin.foil.family is FoilFamily.FLAT_INSIDE and bbox.min.Y < -_FLAT_FACE_TOLERANCE:
        report.fail(f"flat face should lie at y = 0 but bbox reaches y = {bbox.min.Y:.3f}")

    # Streamwise extent must match the outline (a sweep-negated or displaced
    # blade would otherwise pass every other check). The tip vertex counts —
    # at high sweep it can be the forward-most point — and the tolerance
    # scales with extent because the skin legitimately overshoots the sampled
    # stations by ~1-2% between them.
    from fingen.outline import tip_point

    tip_x, _ = tip_point(out)
    x_min_exp = min(min(st.x_le for st in stations), tip_x)
    x_max_exp = max(max(st.x_le + st.chord for st in stations), tip_x)
    # The skin's legitimate between-station overshoot scales with local
    # chord (B-spline bulge) and with station spacing squared (interpolation
    # error ~ h²), so the tolerance does too — coarse lofts get honest slack,
    # default-and-finer resolutions stay tight. This guard exists to catch
    # placement/orientation errors (a negated sweep is off by 2·x_tip, an
    # entire fin width); shape fidelity is guarded independently by the
    # slice probes and the volume check.
    x_tol = max(3.0, 0.10 * c_max * res_slack)
    if abs(bbox.min.X - x_min_exp) > x_tol or abs(bbox.max.X - x_max_exp) > x_tol:
        report.fail(f"streamwise extent [{bbox.min.X:.2f}, {bbox.max.X:.2f}] mm does not "
                    f"match outline [{x_min_exp:.2f}, {x_max_exp:.2f}] mm")

    # Mid-span slice probes: thin-slab boolean intersections between stations
    # catch spanwise skinning oscillation (pinches, balloons) that station-
    # plane checks are blind to.
    zs = np.array([st.z for st in stations])
    chords = np.array([st.chord for st in stations])
    z_top = zs[-1]
    slab_t = 0.4
    for frac in (0.3, 0.55, 0.8):
        z_probe = frac * z_top
        chord_probe = float(np.interp(z_probe, zs, chords))
        area_exp = _section_area(fin, z_probe, chord_probe, fine)
        if area_exp < 30.0:
            # Micro-sections (needle tips of extreme corners) carry no usable
            # signal for the slab probe; volume and topology still guard them.
            # The probes exist to catch BODY skinning corruption, where
            # sections are hundreds of mm².
            continue
        slab = (Pos((bbox.min.X + bbox.max.X) / 2.0, 0.0, z_probe)
                * Box(2.0 * (bbox.max.X - bbox.min.X + 10.0), 4.0 * (y_bound + 5.0), slab_t))
        area_got = (part & slab).volume / slab_t
        # Absolute floor: on micro-sections (needle tips of small fins) the
        # slab probe's own error dominates any honest relative comparison.
        if abs(area_got - area_exp) > max(_SLICE_TOLERANCE * area_exp, 5.0):
            report.fail(f"cross-section at z={z_probe:.1f} mm is {area_got:.0f} mm² "
                        f"vs analytic {area_exp:.0f} mm² (>{_SLICE_TOLERANCE:.0%} off) — "
                        "spanwise loft distortion")

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
