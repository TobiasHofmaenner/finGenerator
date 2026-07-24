"""fingen — parametric surfboard fin geometry generator.

Pipeline: FinParams -> outline + foil sections -> loft -> check -> STEP/STL.
All dimensions are millimetres, all angles degrees, unless stated otherwise.
The math is specified in docs/PHYSICS.md with citations in docs/SOURCES.md.
"""

from fingen.params import (
    FinConfig,
    FinParams,
    FinSetParams,
    FoilFamily,
    FoilParams,
    GenSettings,
    OutlineParams,
    TabParams,
    TabSystem,
)

__version__ = "0.1.0"

__all__ = [
    "FinConfig",
    "FinParams",
    "FinSetParams",
    "FoilFamily",
    "FoilParams",
    "GenSettings",
    "OutlineParams",
    "TabParams",
    "TabSystem",
    "__version__",
]
