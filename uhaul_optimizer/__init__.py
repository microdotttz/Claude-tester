"""U-Haul space optimizer.

Find the smallest U-Haul trailer that fits a list of furniture, using a
3D bin-packing heuristic plus volume, dimension, door-clearance, and weight
checks.
"""

from .trailers import Trailer, UHAUL_TRAILERS, get_trailer
from .furniture import FurnitureItem, FURNITURE_CATALOG, get_catalog_item
from .optimizer import TrailerFit, evaluate_trailer, find_minimum_trailer

__all__ = [
    "Trailer",
    "UHAUL_TRAILERS",
    "get_trailer",
    "FurnitureItem",
    "FURNITURE_CATALOG",
    "get_catalog_item",
    "TrailerFit",
    "evaluate_trailer",
    "find_minimum_trailer",
]
