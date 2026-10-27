"""fingen — parametric surfboard fin geometry generator.

Pipeline: FinParams -> outline + foil sections -> loft -> check -> STEP/STL.
All dimensions are millimetres, all angles degrees, unless stated otherwise.
The math is specified in docs/PHYSICS.md with citations in docs/SOURCES.md.
"""

from fingen.materials import (
    CARDS,
    MaterialCard,
    get_card,
    load_measured_card,
    register_card,
)
from fingen.params import (
    FinConfig,
    FinParams,
    FinSetParams,
    FoilFamily,
    FoilParams,
    GenSettings,
    GrooveParams,
    GrooveSurface,
    OutlineParams,
    TabParams,
    TabSystem,
)

# From the installed distribution, so this cannot drift from pyproject again
# (it sat at "0.6.0" while pyproject said 0.13.2). Falls back for a bare
# source tree that was never installed.
try:
    from importlib.metadata import PackageNotFoundError, version as _dist_version
    try:
        __version__ = _dist_version("fingen")
    except PackageNotFoundError:
        __version__ = "0+unknown"
except ImportError:  # pragma: no cover
    __version__ = "0+unknown"

__all__ = [
    "FinConfig",
    "FinParams",
    "GrooveParams",
    "GrooveSurface",
    "FinSetParams",
    "FoilFamily",
    "FoilParams",
    "GenSettings",
    "OutlineParams",
    "TabParams",
    "TabSystem",
    "MaterialCard",
    "CARDS",
    "get_card",
    "register_card",
    "load_measured_card",
    "__version__",
]
