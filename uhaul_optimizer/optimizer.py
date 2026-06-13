"""Find the smallest U-Haul trailer that fits a set of furniture."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .furniture import FurnitureItem
from .packer import FLEX_RATIO, PackResult, Unit, pack
from .trailers import Trailer, UHAUL_TRAILERS

# U-Haul advises roughly 60% of cargo weight over the front (hitch) half of the
# trailer for stable towing. We flag loads that fall below this band.
FRONT_WEIGHT_TARGET = 0.60
FRONT_WEIGHT_MIN = 0.50


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
    front_weight_pct: float | None = None    # % of weight over the front half
    balance_advice: str = ""                  # tongue-weight tip when fitting


def _units_for(items: list[FurnitureItem]) -> list[Unit]:
    """Expand items (with quantities) into individual packing units."""
    units: list[Unit] = []
    for item in items:
        for n in range(item.quantity):
            label = item.name if item.quantity == 1 else f"{item.name} #{n + 1}"
            units.append(Unit(
                name=label,
                length=item.length,
                width=item.width,
                height=item.height,
                keep_upright=item.keep_upright,
                stackable=item.stackable,
                weight=item.weight,
                flexible=item.flexible,
            ))
    return units


def _passes_door(item: FurnitureItem, trailer: Trailer) -> bool:
    """Can the item pass through the door opening in some orientation?

    The cross-section perpendicular to travel is the item's two smallest
    dimensions (the longest slides through as depth). That cross-section
    clears the opening either straight-on or tilted: at tilt angle theta its
    bounding box is (w*cos + t*sin) x (w*sin + t*cos), and sweeping theta over
    0-90 degrees also covers the swapped orientation. This is how a 54"-wide
    mattress really does enter a 48"-wide door. Flexible items (mattresses) may
    bow inward, so the cross-section is allowed to shrink by ``FLEX_RATIO``.
    """
    shrink = FLEX_RATIO if item.flexible else 1.0
    t, w = (d * shrink for d in sorted(item.dims())[:2])
    dw, dh = trailer.door_width, trailer.door_height
    for deg in range(0, 91):
        a = math.radians(deg)
        if (w * math.cos(a) + t * math.sin(a) <= dw
                and w * math.sin(a) + t * math.cos(a) <= dh):
            return True
    return False


def _front_weight_fraction(result: PackResult, trailer_length: float) -> float | None:
    """Fraction of packed weight resting over the front (hitch) half.

    Each placed box contributes its weight in proportion to how much of its
    length sits ahead of the trailer's midline.
    """
    mid = trailer_length / 2.0
    total = front = 0.0
    for p in result.placements:
        if p.weight <= 0:
            continue
        total += p.weight
        span = p.box.length
        overlap = max(0.0, min(p.box.x2, mid) - p.box.x)
        front += p.weight * (overlap / span if span else 0.0)
    if total <= 0:
        return None
    return front / total


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
    # Flexible items (mattresses) may bow into a slightly tight space, so their
    # required dimensions shrink by FLEX_RATIO -- mirroring the packer.
    idims = sorted([trailer.length, trailer.width, trailer.height])
    for item in items:
        shrink = FLEX_RATIO if item.flexible else 1.0
        needed = sorted(d * shrink for d in item.dims())
        if any(needed[i] > idims[i] + 1e-6 for i in range(3)):
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

    # Tongue-weight advisory: only meaningful when everything is placed.
    front_pct: float | None = None
    advice = ""
    if fits:
        frac = _front_weight_fraction(result, trailer.length)
        if frac is not None:
            front_pct = round(frac * 100)
            if frac < FRONT_WEIGHT_MIN:
                advice = (
                    f"Only {front_pct}% of the weight is over the front axle — "
                    "shift heavy items toward the hitch (aim for ~60%) to avoid "
                    "trailer sway."
                )
            elif frac < FRONT_WEIGHT_TARGET - 0.05:
                advice = (
                    f"{front_pct}% of the weight is up front; nudge a few heavy "
                    "boxes forward to reach the ~60% U-Haul recommends."
                )
            else:
                advice = f"Well balanced — {front_pct}% of the weight rides over the front half."

    return TrailerFit(
        trailer=trailer,
        fits=fits,
        pack_result=result,
        total_volume_cuft=total_vol,
        total_weight=total_wt,
        utilization=utilization,
        blockers=blockers,
        front_weight_pct=front_pct,
        balance_advice=advice,
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
