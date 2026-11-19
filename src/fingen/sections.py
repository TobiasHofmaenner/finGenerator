"""Section data: lift, drag and moment of fingen's foil families, from a table.

The lattice (lattice.py) knows where a blade is loaded; it does not know what a
section does with that load — how much lift it holds before it lets go, what
it costs in drag, what a flat inside face costs at negative incidence. Those
are two-dimensional, viscous questions, and the cheap way to answer them
inside an optimizer loop is a lookup (docs/MODEL-EXTENSION.md, method B: a
3-D inviscid solve times 2-D viscous sections).

`polar(family, thickness_ratio, reynolds, camber_ratio)` returns a
`SectionPolar` — cl, cd and cm over −16…+24° — interpolated in thickness,
camber and log-Reynolds from `data/sections_v0.npz`. Angles are in the
section's own frame: positive = flow onto the flat (inside) face of a side
foil, the direction it is cambered for. The library needs only numpy; the
table is built offline by `scripts/build_section_table.py`.

Two tables ship (`TABLES`): "v0" below, and "v1" — v0 moved onto the
resolved-wall RANS sections of bench/section-tables/ (both ends of each
section's attached range, the drag level, the lift slope; builder
scripts/build_section_table_v1.py, which records its nodes and fits in the
table's meta). `table=` selects one; "v0" stays the default until v1's
sections are complete.

Status of the data (v0): NeuralFoil with the boundary layer tripped. Checked
against resolved-wall 2-D RANS on our flat-inside section (cl 0.43 / 0.86 /
1.35 at 0 / 4 / 12°, cd 0.042 at −3.5°, Re 5.7e5 — all within a few percent)
and against the −3.5° zero-lift angle of the set CFD and the [BW04] tunnel
fin. Its maximum lift for a conventional section is high (NACA 0012: 1.33
against 1.075 measured), so treat `alpha_break_deg` / `cl_break` as
provisional until the RANS section tables are folded in.
"""

from __future__ import annotations

import functools
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from fingen.hydro import NU_SEAWATER
from fingen.params import FinParams, FoilFamily

# Shipped tables. "v0" is NeuralFoil as built (every lattice result up to
# 2026-11-19); "v1" is v0 moved onto the resolved-wall RANS sections — both
# ends of each section's attached range, drag level, lift slope
# (scripts/build_section_table_v1.py). Same layout, so either reads the same way.
TABLES = ("v0", "v1")
_DATA = Path(__file__).parent / "data"
# The table's cambered block is built at this camber position (NACA p).
CAMBER_POSITION = 0.4


@functools.lru_cache(maxsize=len(TABLES))
def _table(table: str = "v0") -> dict:
    if table not in TABLES:
        raise ValueError(f"section table {table!r} not in {TABLES}")
    with np.load(_DATA / f"sections_{table}.npz") as raw:
        out = {k: np.asarray(raw[k], dtype=float) for k in raw.files if k != "meta"}
        out["meta"] = json.loads(str(raw["meta"]))
    out["log_re"] = np.log10(out["reynolds"])
    return out


def table_meta(table: str = "v0") -> dict:
    """Provenance of a shipped table (source, boundary-layer state, build date;
    for v1 also the RANS nodes and the fitted corrections)."""
    return dict(_table(table)["meta"])


def _bracket(grid: np.ndarray, x: float) -> tuple[int, float, bool]:
    """(lower index, weight of the upper node, clipped?) for linear interpolation."""
    clipped = not (grid[0] <= x <= grid[-1])
    x = min(max(x, float(grid[0])), float(grid[-1]))
    i = int(min(np.searchsorted(grid, x, side="right") - 1, len(grid) - 2))
    return i, float((x - grid[i]) / (grid[i + 1] - grid[i])), clipped


def _lerp(arr: np.ndarray, brackets: list[tuple[int, float, bool]]) -> np.ndarray:
    """Multilinear interpolation over the leading axes of `arr`, one bracket per axis."""
    for i, w, _ in brackets:
        arr = (1.0 - w) * arr[i] + w * arr[i + 1]
    return arr


@dataclass(frozen=True)
class SectionPolar:
    """One section at one Reynolds number. Arrays share `alpha_deg`."""

    family: FoilFamily
    thickness_ratio: float
    camber_ratio: float
    reynolds: float
    alpha_deg: np.ndarray
    cl: np.ndarray
    cd: np.ndarray
    cm: np.ndarray
    clipped: bool           # a requested value lay outside the table and was clamped

    def cl_at(self, alpha_deg):
        return np.interp(alpha_deg, self.alpha_deg, self.cl)

    def cd_at(self, alpha_deg):
        return np.interp(alpha_deg, self.alpha_deg, self.cd)

    def cm_at(self, alpha_deg):
        return np.interp(alpha_deg, self.alpha_deg, self.cm)

    @functools.cached_property
    def _linear(self) -> tuple[float, float, float]:
        """(slope per degree, angle where the linear range ends, cl there).

        The linear range is taken between 25 % and 65 % of the positive lift
        peak inside ±16°: clear of the zero-lift kink a flat inside face has
        and of the roll-off toward the break."""
        a, cl = self.alpha_deg, self.cl
        pos = (a >= -6.0) & (a <= 16.0)
        peak = float(cl[pos].max())
        lo = float(np.interp(0.25 * peak, cl[pos][: int(np.argmax(cl[pos])) + 1],
                             a[pos][: int(np.argmax(cl[pos])) + 1]))
        hi = float(np.interp(0.65 * peak, cl[pos][: int(np.argmax(cl[pos])) + 1],
                             a[pos][: int(np.argmax(cl[pos])) + 1]))
        return 0.40 * peak / max(hi - lo, 1e-6), hi, 0.65 * peak

    @property
    def slope_per_rad(self) -> float:
        """Lift-curve slope of the linear range."""
        return math.degrees(self._linear[0])

    @functools.cached_property
    def alpha0_deg(self) -> float:
        """Zero-lift angle: the linear range extended down to cl = 0. (The actual
        curve of a flat-inside foil bends there — its inside face separates.)"""
        slope, hi, cl_hi = self._linear
        return hi - cl_hi / slope

    @functools.cached_property
    def _break(self) -> tuple[float, float]:
        slope, hi, _ = self._linear
        a, cl = self.alpha_deg, self.cl
        local = np.gradient(cl, a)
        for k in np.nonzero(a > hi)[0]:
            if local[k] < 0.30 * slope:
                return float(a[k]), float(cl[k])
        return float(a[-1]), float(cl[-1])

    @property
    def alpha_break_deg(self) -> float:
        """First angle past the linear range where the local slope has fallen
        below 30 % of the linear slope — the knee, not necessarily a maximum."""
        return self._break[0]

    @property
    def cl_break(self) -> float:
        return self._break[1]

    @functools.cached_property
    def alpha_cd_min_deg(self) -> float:
        """Centre of the low-drag range."""
        return float(self.alpha_deg[int(np.argmin(self.cd))])

    @property
    def cd_min(self) -> float:
        return float(self.cd.min())


@functools.lru_cache(maxsize=8192)
def _polar(family: FoilFamily, tc_key: int, re_key: int, camber_key: int,
           table: str = "v0") -> SectionPolar:
    t = _table(table)
    tc, log_re, camber = tc_key * 1e-4, re_key * 1e-3, camber_key * 1e-4
    b_re = _bracket(t["log_re"], log_re)
    if family is FoilFamily.CAMBERED and camber > 0.0:
        br = [_bracket(t["tc_cambered"], tc), _bracket(t["camber"], camber), b_re]
        key = "cambered"
    else:
        br = [_bracket(t["tc"], tc), b_re]
        key = FoilFamily.FLAT_INSIDE.value if family is FoilFamily.FLAT_INSIDE else "symmetric"
    return SectionPolar(family=family, thickness_ratio=tc, camber_ratio=camber,
                        reynolds=10.0**log_re, alpha_deg=t["alpha"],
                        cl=_lerp(t[f"{key}_cl"], br), cd=_lerp(t[f"{key}_cd"], br),
                        cm=_lerp(t[f"{key}_cm"], br), clipped=any(b[2] for b in br))


def polar(family: FoilFamily, thickness_ratio: float, reynolds: float,
          camber_ratio: float = 0.0, table: str = "v0") -> SectionPolar:
    """Section polar of one of fingen's foil families, from the shipped `table`.

    `camber_ratio` is read for FoilFamily.CAMBERED only (camber at 40 % chord; a
    cambered foil with zero camber is the symmetric one). A FLAT_INSIDE foil's
    camber follows from its thickness. Values outside the table are clamped to
    its edge and flagged in `SectionPolar.clipped`. Cached on rounded inputs."""
    if reynolds <= 0.0:
        raise ValueError(f"reynolds {reynolds} must be positive")
    camber = camber_ratio if family is FoilFamily.CAMBERED else 0.0
    return _polar(family, round(thickness_ratio * 1e4), round(math.log10(reynolds) * 1e3),
                  round(camber * 1e4), table)


def for_station(fin: FinParams, speed: float, chord_mm: float, z_frac: float,
                table: str = "v0") -> SectionPolar:
    """The section a blade presents at span fraction `z_frac`, where its chord is
    `chord_mm`, at board speed `speed` [m/s]: local thickness from the spanwise
    schedule, Reynolds number on the local chord."""
    f = fin.foil
    tc = f.thickness_ratio * (1.0 + (fin.thickness_tip_factor - 1.0) * z_frac)
    return polar(f.family, tc, speed * chord_mm * 1e-3 / NU_SEAWATER, f.camber_ratio, table)
