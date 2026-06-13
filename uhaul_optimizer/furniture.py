"""Furniture item model and a catalog of common pieces.

Dimensions are in INCHES (length x width x height) and weights in POUNDS.
The catalog values are typical sizes; always override with your real
measurements when you can, since a few inches decides a tight fit.

Per-item flags:
  keep_upright  - item may only rotate about the vertical axis (e.g. a
                  refrigerator or dresser). When False, the packer may lay it
                  on any face.
  stackable     - other items may be stacked on top of this one. When False
                  (e.g. a glass table top), the space above it stays empty.
  flexible      - item is soft and can bow/compress into a slightly tight gap
                  (mattresses). The packer allows up to a 12% squeeze, which is
                  calibrated so U-Haul's own claims hold: a queen fits a 5x8, a
                  full fits a 4x8, and a king fits a 6x12.
"""

from dataclasses import dataclass
from typing import Iterable


@dataclass
class FurnitureItem:
    """A single piece of furniture (or a stack of identical pieces)."""

    name: str
    length: float
    width: float
    height: float
    weight: float = 0.0
    quantity: int = 1
    keep_upright: bool = False
    stackable: bool = True
    flexible: bool = False

    @property
    def volume_cuft(self) -> float:
        """Volume of ONE unit in cubic feet."""
        return (self.length * self.width * self.height) / 1728.0

    @property
    def total_volume_cuft(self) -> float:
        return self.volume_cuft * self.quantity

    @property
    def total_weight(self) -> float:
        return self.weight * self.quantity

    def dims(self) -> tuple[float, float, float]:
        return (self.length, self.width, self.height)


# A catalog of common household items keyed by a short slug.
# Sizes are typical; users should override with real measurements.
FURNITURE_CATALOG: dict[str, FurnitureItem] = {
    # Bedroom -- mattresses are flexible (they bow into tight gaps); box
    # springs are rigid wooden frames and are not.
    "twin_mattress": FurnitureItem("Twin mattress", 75, 38, 9, 45, flexible=True),
    "full_mattress": FurnitureItem("Full mattress", 75, 54, 10, 60, flexible=True),
    "queen_mattress": FurnitureItem("Queen mattress", 80, 60, 11, 85, flexible=True),
    "king_mattress": FurnitureItem("King mattress", 80, 76, 12, 115, flexible=True),
    "box_spring_queen": FurnitureItem("Queen box spring", 80, 60, 9, 50, keep_upright=False),
    "bed_frame": FurnitureItem("Bed frame (disassembled)", 80, 12, 8, 60),
    "nightstand": FurnitureItem("Nightstand", 24, 18, 26, 30, keep_upright=True),
    "dresser": FurnitureItem("Dresser", 60, 20, 34, 120, keep_upright=True),
    # Taller pieces ride on their backs in a trailer, so they may rotate freely.
    "tall_dresser": FurnitureItem("Tall dresser / armoire", 40, 22, 60, 160),
    # Living room
    "sofa": FurnitureItem("Sofa (3-seat)", 84, 38, 34, 150, keep_upright=True),
    "loveseat": FurnitureItem("Loveseat", 60, 38, 34, 110, keep_upright=True),
    "armchair": FurnitureItem("Armchair / recliner", 35, 38, 40, 90, keep_upright=True),
    "coffee_table": FurnitureItem("Coffee table", 48, 24, 18, 40),
    "tv_stand": FurnitureItem("TV stand", 60, 18, 24, 70, keep_upright=True),
    "tv_55": FurnitureItem('55" flat-screen TV (boxed)', 52, 8, 32, 45, keep_upright=True, stackable=False),
    "bookshelf": FurnitureItem("Bookshelf", 36, 12, 72, 80),  # rides on its back
    "floor_lamp": FurnitureItem("Floor lamp (broken down)", 60, 8, 8, 12),
    # Dining / kitchen
    "dining_table": FurnitureItem("Dining table", 60, 36, 30, 90, stackable=False),
    "dining_chair": FurnitureItem("Dining chair", 18, 20, 36, 15, keep_upright=True),
    "bar_stool": FurnitureItem("Bar stool", 16, 16, 30, 12, keep_upright=True),
    # Appliances
    # Taller than any trailer's ceiling, so it must travel on its side in a
    # trailer (keep_upright=False). Ideally moved upright in a truck — see notes.
    "refrigerator": FurnitureItem("Refrigerator", 36, 33, 70, 300, keep_upright=False, stackable=False),
    "washer": FurnitureItem("Washer", 27, 30, 39, 180, keep_upright=True, stackable=False),
    "dryer": FurnitureItem("Dryer", 27, 30, 39, 130, keep_upright=True, stackable=False),
    "microwave": FurnitureItem("Microwave", 22, 18, 14, 35),
    # Office
    "desk": FurnitureItem("Desk", 55, 28, 30, 90, keep_upright=True),
    "office_chair": FurnitureItem("Office chair", 26, 26, 40, 35, keep_upright=True),
    "filing_cabinet": FurnitureItem("Filing cabinet", 18, 26, 30, 60, keep_upright=True),
    # Boxes
    "box_small": FurnitureItem("Small box", 16, 12, 12, 25),
    "box_medium": FurnitureItem("Medium box", 18, 18, 16, 35),
    "box_large": FurnitureItem("Large box", 18, 18, 24, 45),
}


# Grouping used by the web catalog UI.
_CATEGORY_GROUPS: dict[str, list[str]] = {
    "Bedroom": [
        "twin_mattress", "full_mattress", "queen_mattress", "king_mattress",
        "box_spring_queen", "bed_frame", "nightstand", "dresser", "tall_dresser",
    ],
    "Living Room": [
        "sofa", "loveseat", "armchair", "coffee_table", "tv_stand", "tv_55",
        "bookshelf", "floor_lamp",
    ],
    "Dining": ["dining_table", "dining_chair", "bar_stool"],
    "Appliances": ["refrigerator", "washer", "dryer", "microwave"],
    "Office": ["desk", "office_chair", "filing_cabinet"],
    "Boxes": ["box_small", "box_medium", "box_large"],
}
FURNITURE_CATEGORIES: dict[str, str] = {
    slug: cat for cat, slugs in _CATEGORY_GROUPS.items() for slug in slugs
}


def get_catalog_item(slug: str, quantity: int = 1) -> FurnitureItem:
    """Return a copy of a catalog item with the requested quantity."""
    key = slug.strip().lower()
    if key not in FURNITURE_CATALOG:
        raise KeyError(
            f"No catalog item {slug!r}. Try one of: {', '.join(sorted(FURNITURE_CATALOG))}"
        )
    base = FURNITURE_CATALOG[key]
    return FurnitureItem(
        name=base.name,
        length=base.length,
        width=base.width,
        height=base.height,
        weight=base.weight,
        quantity=quantity,
        keep_upright=base.keep_upright,
        stackable=base.stackable,
        flexible=base.flexible,
    )


def total_volume_cuft(items: Iterable[FurnitureItem]) -> float:
    return sum(i.total_volume_cuft for i in items)


def total_weight(items: Iterable[FurnitureItem]) -> float:
    return sum(i.total_weight for i in items)
