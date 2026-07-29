"""Fillets at the tab junction and the tab tip.

The tabs are fused onto the blade with a plain boolean union, which leaves a
SHARP RE-ENTRANT CORNER at the base plane (z = 0). That corner is the worst
possible detail in the worst possible place: z = 0 is the max-moment station in
the tab (every box reaction acts below it, so the tabs transmit the whole root
moment there), and a printed fin's classic failure is snapping flush at the
deck. `fingen.sizing.KT_TAB` = 2.5 is explicitly a FILLETED-shoulder value from
the stress-concentration charts — so without a fillet the geometry did not match
the stress model it was being checked against, and a sharp corner is WORSE than
2.5, not better.

Two blends, with different budgets:

  * ROOT (z = 0, tab -> blade): tightly bounded. The box slot has to accept the
    tab, so the blend can only use the step between the blade's local thickness
    and the tab's — on a FLAT_INSIDE fin one side is flush (no step, no blend
    possible) and the other has the whole difference. Clamped to what is there.
  * TIP (tab bottom edges): free. That end sits deep inside the box with
    clearance around it, so a generous radius costs nothing and also eases the
    insertion rotation.

Filleting a boolean result is the fragile step in any CAD kernel. Every blend
here is attempted independently and skipped if OCCT declines, so a fillet
failure degrades to the previous (sharp) geometry instead of failing the build.
`fillet_report` says which blends actually landed — do not assume.
"""
from __future__ import annotations

from dataclasses import dataclass

from build123d import Part, fillet

from fingen.params import FinParams, TabSystem


@dataclass
class FilletReport:
    """Which blends were applied, and why any were not."""

    root_applied: int = 0
    tip_applied: int = 0
    root_radius: float = 0.0
    skipped: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.skipped


def _edges_near_z(part: Part, z_lo: float, z_hi: float) -> list:
    """Edges whose whole extent sits in the z band — the blend candidates.

    Selecting by POSITION rather than by topological query keeps this robust to
    however OCCT happened to structure the boolean result.
    """
    out = []
    for e in part.edges():
        bb = e.bounding_box()
        if z_lo <= bb.min.Z and z_hi >= bb.max.Z:
            out.append(e)
    return out


def _tab_step_mm(fin: FinParams) -> float:
    """Material available for the root blend, mm.

    A FLAT_INSIDE fin anchors the tab FLUSH with the y=0 face, so the whole
    thickness difference sits on one side and is available there (the flush side
    has no step at all — nothing to blend, and nothing to gain). Other families
    centre the tab, splitting the difference between the two sides.
    """
    from fingen.params import FoilFamily
    from fingen.tabs import system_thickness

    diff = fin.foil.thickness_ratio * fin.outline.base - system_thickness(fin.tabs)
    if diff <= 0.0:
        return 0.0
    return diff if fin.foil.family is FoilFamily.FLAT_INSIDE else diff / 2.0


def _junction_edges(part: Part, fin: FinParams) -> list:
    """The tab-to-blade step at z = 0 — NOT the blade's own base outline.

    Both lie in the z = 0 plane, and an earlier version told them apart by the
    edge's x-midpoint, which fails: the base outline spans the whole chord, so
    its midpoint sits inside the tab span and it got blended too — rounding the
    face that seats on the board while leaving the real step sharp.

    They separate cleanly on TYPE and HEIGHT instead. The tabs are boxes, so
    every junction edge is a straight LINE lying at or below the tab's own
    thickness; the blade's outline is a BSPLINE tracing the foil and reaches
    past it (7.93 vs 6.15 mm on the reference fin). The flush y = 0 boundary is
    a spline too and is excluded for free — correctly, since a flush face has
    no step to blend.
    """
    from fingen.tabs import system_thickness

    t_tab = system_thickness(fin.tabs)
    if t_tab <= 0.0:
        return []
    out = []
    for e in _edges_near_z(part, -0.01, 0.01):
        # EXACT match: "BSPLINE" contains "LINE", so a substring test lets the
        # blade's own spline outline through — which is precisely the edge this
        # function exists to exclude.
        if str(e.geom_type).rsplit(".", 1)[-1].upper() != "LINE":
            continue
        if t_tab + 0.05 >= e.bounding_box().max.Y:
            out.append(e)
    return out


def _fillet_each(solid: Part, edges: list, radius: float) -> tuple[Part, int]:
    """Blend `edges` at `radius`, all at once if OCCT allows, else one at a
    time keeping whatever lands. A boolean result often has a few edges the
    kernel will not blend (degenerate at a flush face, or meeting at a vertex);
    losing those should not cost the rest."""
    try:
        return fillet(edges, radius=radius), len(edges)
    except Exception:  # noqa: BLE001 — fall back to per-edge
        pass
    applied = 0
    for i in range(len(edges)):
        # Re-select each time: every successful fillet rebuilds the topology,
        # so edge handles from before are stale.
        cand = _junction_edges_cache.get("fn", lambda p: [])(solid)
        if i >= len(cand):
            break
        try:
            solid = fillet([cand[i]], radius=radius)
            applied += 1
        except Exception:  # noqa: BLE001
            continue
    return solid, applied


_junction_edges_cache: dict = {}


def apply_tab_fillets(solid: Part, fin: FinParams, settings=None) -> tuple[Part, FilletReport]:
    """Blend the tab junction and tab tip. Returns (solid, report).

    Never raises on a fillet failure: the un-filleted solid is a valid fin, just
    a worse one, and refusing to build it would be the wrong trade.
    """
    rep = FilletReport()
    tabs = fin.tabs
    if tabs.system is TabSystem.NONE:
        return solid, rep

    from fingen.tabs import system_depth

    depth = system_depth(tabs)

    # --- tip: the free end, deep in the box -------------------------------
    if tabs.tip_fillet > 0.0:
        cand = _edges_near_z(solid, -depth - 0.01, -depth + 0.01)
        if cand:
            try:
                solid = fillet(cand, radius=tabs.tip_fillet)
                rep.tip_applied = len(cand)
            except Exception:  # noqa: BLE001 — OCCT declines; keep the sharp tip
                rep.skipped += (f"tip ({len(cand)} edges, r={tabs.tip_fillet})",)
        else:
            rep.skipped += ("tip (no edges found at the tab bottom)",)

    # --- root: the z = 0 junction, the one that matters -------------------
    if tabs.root_fillet > 0.0:
        budget = _tab_step_mm(fin)
        r = min(tabs.root_fillet, max(budget - 0.05, 0.0))
        if r < 0.05:
            rep.skipped += (
                f"root (only {budget:.2f} mm of step available — the tab is "
                "flush with the blade face here, so there is nothing to blend)",)
        else:
            _junction_edges_cache["fn"] = lambda p: _junction_edges(p, fin)
            cand = _junction_edges(solid, fin)
            if cand:
                solid, n = _fillet_each(solid, cand, r)
                rep.root_applied = n
                rep.root_radius = r if n else 0.0
                if n == 0:
                    rep.skipped += (f"root (OCCT declined all {len(cand)} edges "
                                    f"at r={r:.2f})",)
            else:
                rep.skipped += ("root (no junction edges inside the tab span)",)
    return solid, rep
