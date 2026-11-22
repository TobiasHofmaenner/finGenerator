"""One blade's hydrodynamics AS MOUNTED, from the viscous lattice.

The generation-3 path for the lift curve and the drag of a blade
(`RiderSpec.hydro_model = "lattice"`, or `"lattice-v1"` for the same lattice on
section table v1 — spider.SECTION_TABLE). Tier-0's closed forms (hydro.py,
spider._cd0) stay the default until a before/after on every rider spec says
otherwise; this module answers the same questions from `lattice.solve_viscous`
and the section table:

  lift_curve       slope and zero-lift angle of the blade's working range, and
                   where its centre of pressure sits;
  trim_drag_n      drag going straight, the blade toed in as it is mounted;
  drag_at_force_n  drag while it makes a given side force;
  knee             where the blade leaves its lift line (`"lattice-knee"` only).

What changes against tier-0, and why it matters (docs/MODEL-EXTENSION.md):
profile drag follows the section at the incidence each strip really works at,
so a flat inside face at its toe angle costs what the CFD says it costs
(13–15 N per gen-2 side going straight; tier-0 reads ~5 N), and a cambered
foil does not; the lift slope and zero-lift angle carry the planform, the tip
thickness and the section instead of a formula in four numbers.

The knee. The strip coupling has no three-dimensional separation onset: run
to its sections' own breaks it carries the tunnel fin's lift line to 22 deg,
where the tunnel has it bend at 12-14. Under `"lattice"` and `"lattice-v1"`
the break angle therefore stays tier-0's (hydro.break_alpha_deg) and every
solve here is kept on the attached side of it. `"lattice-knee"` reads the
knee off the strips instead (`knee`, KNEE_FRACTION): the blade leaves its
line when its most loaded strip reaches a fixed share of the most lift its
section carries attached (`SectionPolar.cl_limit`).

The board is not a perfect mirror. BOARD_MIRROR_STRENGTH weakens the image so
the lift slope loses about 8–9 %, which is tier-0's reflection factor 1.7 and
sits between the lattice's own estimates for a finite board under a free
surface (scripts/board_edge_probe.py: centre fin ≈ 0.90, side fin ≈ 0.84).
"""

from __future__ import annotations

import functools
import math

import numpy as np

from fingen import lattice
from fingen.hydro import RHO_SEAWATER
from fingen.lattice import ViscousLoads
from fingen.outline import metrics
from fingen.params import FinParams

BOARD_MIRROR_STRENGTH = 0.85
# Lattice resolution inside the optimizer loop: 10 strips x 2 chordwise panels
# carry the fine lattice's lift and far-wake drag within half a percent
# (tests/test_lattice.py).
NZ, NX = 10, 2
# Two own-incidences that bracket the working range of every blade and stay
# clear of the zero-lift kink of a flat inside face.
_LIN_LO_DEG, _LIN_HI_DEG = 2.0, 6.0
TRIM_LEEWAY_DEG = 1.0
# The knee of a blade (`knee`): its most loaded strip at this share of the most
# lift its section carries attached (`SectionPolar.cl_limit`; until 2026-11-22
# the lift at the break by slope, which is the same number on a table whose
# sections hold their lift to the end and a jumpy one where they round over).
# One fitted number. 0.606 puts the
# knee of the [BW04] tunnel fin at 12.0 deg on the board mirror — the last
# tunnel point on its lift line (14 deg is 6 % below it) and tier-0's own
# anchor. Checked, not fitted, against the 3-D polars with a fin file
# (scripts/knee_survey.py): side fins sit 1.5–2 deg before where their one-degree
# polars leave the line, thin symmetric blades 4–5 deg before (their sections'
# lift keeps rising behind the end of the attached range; Phase 2).
# The number belongs to the section table it was fitted on (v1 of 2026-11-22,
# the 39 sections on the held stream; 0.715 on the table of 2026-11-20, whose
# flat-inside sections ended 2–3 deg earlier and carried less lift): refit it
# with scripts/knee_survey.py --fraction= when the table is rebuilt.
KNEE_FRACTION = 0.606


@functools.lru_cache(maxsize=256)
def _context(fin: FinParams, speed_key: int, table: str):
    speed = speed_key * 1e-3
    blade = lattice.blade_from_fin("blade", fin, nz=NZ, nx=NX)
    return blade, {"blade": lattice.strip_sections(fin, blade, speed, table)}


@functools.lru_cache(maxsize=4096)
def _point(fin: FinParams, speed_key: int, alpha_key: int,
           table: str) -> tuple[ViscousLoads, bool]:
    blade, polars = _context(fin, speed_key, table)
    sol = lattice.solve_viscous([blade], polars, speed_key * 1e-3, alpha_key * 1e-3,
                                mirror_strength=BOARD_MIRROR_STRENGTH)
    return sol.loads["blade"], sol.converged


def point(fin: FinParams, speed: float, alpha_deg: float,
          table: str = "v0") -> tuple[ViscousLoads, bool]:
    """Loads on the blade alone at its OWN incidence `alpha_deg` (positive = flow
    onto the flat inside face), and whether the strip iteration converged.
    `table` is the shipped section table the strips read (sections.TABLES)."""
    return _point(fin, round(speed * 1e3), round(alpha_deg * 1e3), table)


def lift_curve(fin: FinParams, speed: float, table: str = "v0") -> tuple[float, float, float]:
    """(CL per radian, zero-lift angle in degrees, chordwise CP in mm from the
    base centre, + aft) of the blade's working range.

    The zero-lift angle is the working range extended down to zero lift — the
    quantity a toe angle has to match — not the bent curve a flat-inside foil
    actually follows there."""
    lo, _ = point(fin, speed, _LIN_LO_DEG, table)
    hi, _ = point(fin, speed, _LIN_HI_DEG, table)
    slope_deg = (hi.cl - lo.cl) / (_LIN_HI_DEG - _LIN_LO_DEG)
    if not math.isfinite(slope_deg) or slope_deg <= 0.0:
        raise ValueError("lattice lift curve is not usable for this blade")
    return math.degrees(slope_deg), _LIN_LO_DEG - lo.cl / slope_deg, hi.x_cp_m * 1e3


def knee(fin: FinParams, speed: float, table: str = "v0") -> tuple[float, float]:
    """(own incidence in degrees, CL) at which the blade leaves its lift line.

    Every strip's lift is followed along its own line through the working
    range; the knee is the first angle at which one of them reaches
    KNEE_FRACTION of the most lift its section carries attached
    (`SectionPolar.cl_limit`). A blade that loads its tip reaches that
    earlier than one that spreads its load, a high aspect ratio earlier than a
    low one (each degree of incidence loads its strips more), a section with
    more maximum lift later. What it stands for: on a real blade the line ends
    before the fully turbulent 2-D section does — transition, spanwise flow on
    a swept blade, the tip. The share is fitted on one tunnel fin."""
    lo, _ = point(fin, speed, _LIN_LO_DEG, table)
    hi, _ = point(fin, speed, _LIN_HI_DEG, table)
    _, polars = _context(fin, round(speed * 1e3), table)
    cl_limit = np.array([p.cl_limit for p in polars["blade"]])
    span = _LIN_HI_DEG - _LIN_LO_DEG
    rate = (hi.cl_local - lo.cl_local) / span
    reach = np.full(len(rate), np.inf)
    rising = rate > 1e-6
    reach[rising] = _LIN_LO_DEG + ((KNEE_FRACTION * cl_limit[rising] - lo.cl_local[rising])
                                   / rate[rising])
    alpha = float(reach.min())
    if not math.isfinite(alpha):
        raise ValueError("lattice lift curve is not usable for this blade")
    return alpha, lo.cl + (hi.cl - lo.cl) / span * (alpha - _LIN_LO_DEG)


def _q_area(fin: FinParams, speed: float) -> float:
    return 0.5 * RHO_SEAWATER * speed**2 * metrics(fin.outline).area * 1e-6


def trim_drag_n(fin: FinParams, speed: float, toe_deg: float, table: str = "v0") -> float:
    """Drag in N of one blade going straight, toed in by `toe_deg`: the mean of
    the two blades of a pair at the trim leeway, own incidences ±leeway − toe."""
    qa = _q_area(fin, speed)
    return 0.5 * qa * (point(fin, speed, TRIM_LEEWAY_DEG - toe_deg, table)[0].cd
                       + point(fin, speed, -TRIM_LEEWAY_DEG - toe_deg, table)[0].cd)


def drag_at_force_n(fin: FinParams, speed: float, force_n: float,
                    alpha_max_deg: float, table: str = "v0") -> tuple[float, float]:
    """(drag N, side force N actually made) with the blade making `force_n`, its
    own incidence capped at `alpha_max_deg` (the caller's break angle, so the
    strip model is never asked about separated flow)."""
    qa = _q_area(fin, speed)
    slope, a0, _ = lift_curve(fin, speed, table)
    cl_req = force_n / qa
    alpha = min(a0 + math.degrees(cl_req / slope), alpha_max_deg)
    loads, _ = point(fin, speed, alpha, table)
    if alpha < alpha_max_deg and abs(loads.cl - cl_req) > 0.02 * max(cl_req, 0.05):
        alpha = min(alpha + math.degrees((cl_req - loads.cl) / slope), alpha_max_deg)
        loads, _ = point(fin, speed, alpha, table)   # one secant step onto the target
    return loads.cd * qa, loads.cl * qa
