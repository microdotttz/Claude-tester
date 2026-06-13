"""U-Haul space optimizer.

Find the smallest U-Haul trailer that fits a list of furniture, using a
3D bin-packing heuristic plus volume, dimension, door-clearance, and weight
checks.
"""

from .trailers import Trailer, UHAUL_TRAILERS, get_trailer
from .furniture import FurnitureItem, FURNITURE_CATALOG, get_catalog_item
from .optimizer import TrailerFit, evaluate_trailer, find_minimum_trailer
from .serialization import (
    catalog_payload,
    items_from_payload,
    optimize_payload,
    recommendation_to_dict,
)
from .lovesac import lovesac_items, lovesac_components_payload
from .scraper import parse_listing, fetch_listing

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
    "catalog_payload",
    "items_from_payload",
    "optimize_payload",
    "recommendation_to_dict",
    "lovesac_items",
    "lovesac_components_payload",
    "parse_listing",
    "fetch_listing",
]
