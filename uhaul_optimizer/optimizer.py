"""Find the smallest U-Haul trailer that fits a set of furniture."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .furniture import FurnitureItem
from .packer import PackResult, Unit, pack
from .trailers import Trailer, UHAUL_TRAILERS


@dataclass
class TrailerFit:
    """Result of evaluating one trailer against the furniture list."""

    trailer: Trailer
    fits: bool
    pack_result: PackResult
    total_volume_cuft: float
    total_weight: float
    utilization: float                       # 0..1, items volume / trailer volume
    blockers: list[str] = field(default_factory=list)   # reasons it does not fit


def _units_for(items: list[FurnitureItem]) -> list[Unit]:
    """Expand items (with quantities) into individual packing units."""
    units: list[Unit] = []
    for item in items:
        for n in range(item.quantity):
            label = item.name if item.quantity == 1 else f"{item.name} #{n + 1}"
            units.append(
                (label, item.length, item.width, item.height, item.keep_upright, item.stackable)
            )
    return units


def _passes_door(item: FurnitureItem, trailer: Trailer) -> bool:
    """Can the item pass through the door opening in some orientation?

    The cross-section perpendicular to travel is the item's two smallest
    dimensions (the longest slides through as depth). That cross-section
    clears the opening either straight-on or tilted: at tilt angle theta its
    bounding box is (w*cos + t*sin) x (w*sin + t*cos), and sweeping theta over
    0-90 degrees also covers the swapped orientation. This is how a 54"-wide
    mattress really does enter a 48"-wide door.
    """
    t, w = sorted(item.dims())[:2]  # thickness and width of the cross-section
    dw, dh = trailer.door_width, trailer.door_height
    for deg in range(0, 91):
        a = math.radians(deg)
        if (w * math.cos(a) + t * math.sin(a) <= dw
                and w * math.sin(a) + t * math.cos(a) <= dh):
            return True
    return False


def evaluate_trailer(items: list[FurnitureItem], trailer: Trailer) -> TrailerFit:
    """Check whether all ``items`` fit in ``trailer`` and why / why not."""
    total_vol = sum(i.total_volume_cuft for i in items)
    total_wt = sum(i.total_weight for i in items)
    blockers: list[str] = []

    # 1) Weight limit.
    if total_wt > trailer.max_load:
        blockers.append(
            f"Over weight limit by {total_wt - trailer.max_load:,.0f} lbs "
            f"({total_wt:,.0f} lbs of {trailer.max_load:,.0f} lbs)."
        )

    # 2) Each item must physically fit the interior and clear the door.
    for item in items:
        smallest_two = sorted(item.dims())[:2]
        # Must fit interior in some orientation (handled fully by the packer too,
        # but called out here for a clear message).
        idims = sorted([trailer.length, trailer.width, trailer.height])
        if sorted(item.dims())[2] > idims[2] + 1e-6 or smallest_two[1] > idims[1] + 1e-6 or smallest_two[0] > idims[0] + 1e-6:
            blockers.append(f"{item.name} is too big for the interior.")
        elif not _passes_door(item, trailer):
            blockers.append(
                f"{item.name} won't fit through the "
                f"{trailer.door_width:.0f}\"x{trailer.door_height:.0f}\" door, even tilted."
            )

    # 3) Total volume can't exceed the trailer (a hard lower bound).
    if total_vol > trailer.volume_cuft:
        blockers.append(
            f"Furniture volume ({total_vol:.0f} cu ft) exceeds the trailer's "
            f"{trailer.volume_cuft:.0f} cu ft."
        )

    # 4) The geometric packing test (using interior L/W/H).
    container = (trailer.length, trailer.width, trailer.height)
    result = pack(container, _units_for(items))
    if not result.success:
        unique = sorted({u.split(" #")[0] for u in result.unplaced})
        blockers.append("Couldn't arrange everything to fit: " + ", ".join(unique) + ".")

    utilization = total_vol / trailer.volume_cuft if trailer.volume_cuft else 0.0
    fits = not blockers
    return TrailerFit(
        trailer=trailer,
        fits=fits,
        pack_result=result,
        total_volume_cuft=total_vol,
        total_weight=total_wt,
        utilization=utilization,
        blockers=blockers,
    )


@dataclass
class Recommendation:
    """The overall result returned to a caller."""

    recommended: TrailerFit | None        # smallest trailer that fits, if any
    evaluations: list[TrailerFit]          # every trailer, smallest -> largest
    total_volume_cuft: float
    total_weight: float

    @property
    def fits_any(self) -> bool:
        return self.recommended is not None


def find_minimum_trailer(
    items: list[FurnitureItem],
    trailers: list[Trailer] = UHAUL_TRAILERS,
    enclosed_only: bool = False,
) -> Recommendation:
    """Return the smallest trailer (by advertised volume) that fits everything.

    ``enclosed_only`` restricts the search to weatherproof cargo trailers.
    """
    candidates = [t for t in trailers if t.enclosed] if enclosed_only else list(trailers)
    candidates = sorted(candidates, key=lambda t: t.volume_cuft)

    evaluations = [evaluate_trailer(items, t) for t in candidates]
    recommended = next((e for e in evaluations if e.fits), None)

    return Recommendation(
        recommended=recommended,
        evaluations=evaluations,
        total_volume_cuft=sum(i.total_volume_cuft for i in items),
        total_weight=sum(i.total_weight for i in items),
    )
