"""Lovesac Sactional component sizing.

Sactionals are modular: when you move one you carry a pile of Seats (the bases
you sit on), Sides (the arms/backrests), and the soft Cushions and Pillows.
This module turns "how many of each" into packable :class:`FurnitureItem`s.

Dimensions are in inches, weights in pounds. The soft pieces are flagged
``flexible`` so the packer lets them bow into gaps -- which is exactly how you
cram couch cushions into a trailer. Values are typical published Sactional
sizes; override in code if your set differs.
"""

from __future__ import annotations

from dataclasses import dataclass

from .furniture import FurnitureItem


@dataclass(frozen=True)
class LovesacComponent:
    key: str
    name: str
    length: float
    width: float
    height: float
    weight: float
    flexible: bool = False
    stackable: bool = True

    @property
    def volume_cuft(self) -> float:
        return (self.length * self.width * self.height) / 1728.0


# Keyed by the user-facing term; ordered for display in the configurator.
LOVESAC_COMPONENTS: dict[str, LovesacComponent] = {
    "sides": LovesacComponent("sides", "Lovesac Side (arm/back)", 33.5, 13, 26, 28),
    "bottoms": LovesacComponent("bottoms", "Lovesac Seat (base)", 33.5, 33.5, 7, 38),
    "cushions": LovesacComponent("cushions", "Lovesac Cushion", 33, 24, 6, 9, flexible=True),
    "pillows": LovesacComponent("pillows", "Lovesac Throw Pillow", 20, 20, 7, 2, flexible=True),
}

LOVESAC_ORDER = ["sides", "bottoms", "cushions", "pillows"]


def lovesac_items(
    sides: int = 0, bottoms: int = 0, cushions: int = 0, pillows: int = 0
) -> list[FurnitureItem]:
    """Build packable items for a Sactional made of the given component counts.

    One :class:`FurnitureItem` per non-zero component (with its quantity set);
    the packer expands quantities into individual pieces.
    """
    counts = {"sides": sides, "bottoms": bottoms, "cushions": cushions, "pillows": pillows}
    items: list[FurnitureItem] = []
    for key in LOVESAC_ORDER:
        qty = int(counts.get(key, 0) or 0)
        if qty <= 0:
            continue
        c = LOVESAC_COMPONENTS[key]
        items.append(FurnitureItem(
            name=c.name,
            length=c.length, width=c.width, height=c.height, weight=c.weight,
            quantity=qty, flexible=c.flexible, stackable=c.stackable,
        ))
    return items


def lovesac_components_payload() -> list[dict]:
    """Component specs as plain dicts for the configurator UI."""
    return [
        {
            "key": c.key,
            "name": c.name,
            "label": label,
            "length": c.length,
            "width": c.width,
            "height": c.height,
            "weight": c.weight,
            "flexible": c.flexible,
            "stackable": c.stackable,
            "volume": round(c.volume_cuft, 1),
        }
        for key, label in [
            ("sides", "Sides"),
            ("bottoms", "Bottoms (seats)"),
            ("cushions", "Cushions"),
            ("pillows", "Pillows"),
        ]
        for c in [LOVESAC_COMPONENTS[key]]
    ]
