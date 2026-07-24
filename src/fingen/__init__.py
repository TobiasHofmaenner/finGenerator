"""fingen — parametric surfboard fin geometry generator.

Pipeline: FinParams -> outline + foil sections -> loft -> STEP/STL.
All dimensions are millimetres, all angles degrees, unless stated otherwise.
"""

from fingen.params import FinParams, FinSetParams, FoilParams

__version__ = "0.1.0"

__all__ = ["FinParams", "FinSetParams", "FoilParams", "__version__"]
