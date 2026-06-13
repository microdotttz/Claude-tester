"""Serialization helpers shared by the desktop app, web app, and any UI.

Keeps a single source of truth for: the catalog payload sent to the UI, parsing
the UI's item list back into :class:`FurnitureItem` objects, and turning a
:class:`Recommendation` into a JSON-serializable dict (including the 3D
placement coordinates that drive the load-plan diagram).
"""

from __future__ import annotations

from .furniture import (
    FURNITURE_CATALOG,
    FURNITURE_CATEGORIES,
    FurnitureItem,
    get_catalog_item,
)
from .optimizer import Recommendation, TrailerFit, find_minimum_trailer


def catalog_payload() -> list[dict]:
    """The furniture catalog as plain dicts for the UI to render."""
    return [
        {
            "slug": slug,
            "name": item.name,
            "category": FURNITURE_CATEGORIES.get(slug, "Other"),
            "length": item.length,
            "width": item.width,
            "height": item.height,
            "weight": item.weight,
            "volume": round(item.volume_cuft, 1),
            "keep_upright": item.keep_upright,
            "stackable": item.stackable,
        }
        for slug, item in FURNITURE_CATALOG.items()
    ]


def items_from_payload(payload: list[dict]) -> list[FurnitureItem]:
    """Turn the UI's item list into :class:`FurnitureItem` objects.

    Items with a known ``slug`` come from the catalog; everything else is a
    custom item and must carry ``length``/``width``/``height``.
    """
    items: list[FurnitureItem] = []
    for obj in payload:
        qty = int(obj.get("quantity", 1))
        if qty <= 0:
            continue
        if obj.get("slug") in FURNITURE_CATALOG:
            items.append(get_catalog_item(obj["slug"], qty))
        else:
            items.append(FurnitureItem(
                name=str(obj.get("name", "Custom item")),
                length=float(obj["length"]),
                width=float(obj["width"]),
                height=float(obj["height"]),
                weight=float(obj.get("weight", 0) or 0),
                quantity=qty,
                keep_upright=bool(obj.get("keep_upright", False)),
                stackable=bool(obj.get("stackable", True)),
            ))
    return items


def _fit_to_dict(ev: TrailerFit) -> dict:
    return {
        "trailer": ev.trailer.name,
        "fits": ev.fits,
        "enclosed": ev.trailer.enclosed,
        "volume_cuft": ev.trailer.volume_cuft,
        "max_load": ev.trailer.max_load,
        "utilization": round(ev.utilization * 100),
        "summary": ev.trailer.summary(),
        "note": ev.trailer.note,
        "blockers": ev.blockers,
        "front_weight_pct": ev.front_weight_pct,
        "balance_advice": ev.balance_advice,
        "container": {
            "length": ev.trailer.length,
            "width": ev.trailer.width,
            "height": ev.trailer.height,
        },
        # Placement coordinates power the load-plan diagram; only fitting
        # trailers have a complete (and therefore meaningful) arrangement.
        "placements": [
            {
                "name": p.name,
                "x": p.box.x, "y": p.box.y, "z": p.box.z,
                "l": p.box.length, "w": p.box.width, "h": p.box.height,
                "weight": p.weight,
            }
            for p in ev.pack_result.placements
        ] if ev.fits else [],
    }


def recommendation_to_dict(rec: Recommendation) -> dict:
    """Serialize a :class:`Recommendation` for the UI."""
    return {
        "total_volume": round(rec.total_volume_cuft),
        "total_weight": round(rec.total_weight),
        "fits_any": rec.fits_any,
        "recommended": _fit_to_dict(rec.recommended) if rec.recommended else None,
        "evaluations": [_fit_to_dict(e) for e in rec.evaluations],
    }


def optimize_payload(payload: list[dict], enclosed_only: bool = False) -> dict:
    """Full pipeline: UI item list -> recommendation dict.

    Raises ``ValueError`` if the payload is empty or has no usable items, so
    callers can surface a clean message.
    """
    if not payload:
        raise ValueError("Add at least one item.")
    items = items_from_payload(payload)
    if not items:
        raise ValueError("Add at least one item.")
    rec = find_minimum_trailer(items, enclosed_only=enclosed_only)
    return recommendation_to_dict(rec)
