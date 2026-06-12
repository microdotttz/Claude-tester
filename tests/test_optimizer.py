"""Tests for the U-Haul space optimizer."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uhaul_optimizer.furniture import FurnitureItem, get_catalog_item
from uhaul_optimizer.optimizer import evaluate_trailer, find_minimum_trailer
from uhaul_optimizer.packer import Box, pack
from uhaul_optimizer.trailers import UHAUL_TRAILERS, get_trailer


# --- packer primitives ---------------------------------------------------

def test_single_item_fits_exactly():
    res = pack((100, 50, 50), [("box", 100, 50, 50, False, True)])
    assert res.success
    assert len(res.placements) == 1
    assert abs(res.utilization - 1.0) < 1e-6


def test_item_too_big_in_every_orientation():
    res = pack((50, 50, 50), [("huge", 60, 55, 52, False, True)])
    assert not res.success
    assert res.unplaced == ["huge"]


def test_rotation_allows_fit():
    # 90 long won't fit a 60-long bin unless rotated to lie down.
    res = pack((60, 60, 60), [("plank", 90, 10, 10, False, True)])
    assert not res.success  # 90 exceeds every interior dimension
    res2 = pack((100, 60, 60), [("plank", 90, 10, 10, False, True)])
    assert res2.success


def test_keep_upright_blocks_lay_down():
    # Item is 70 tall; bin is only 50 tall. Laying it down would fit, but
    # keep_upright forbids that, so it must fail.
    res = pack((100, 100, 50), [("fridge", 36, 33, 70, True, False)])
    assert not res.success
    # Same item allowed to rotate freely fits lying on its side.
    res2 = pack((100, 100, 50), [("fridge", 36, 33, 70, False, True)])
    assert res2.success


def test_packs_multiple_units_side_by_side():
    # Four 25-wide boxes across a 100-wide floor.
    units = [(f"b{i}", 40, 25, 40, False, True) for i in range(4)]
    res = pack((40, 100, 40), units)
    assert res.success
    assert len(res.placements) == 4
    # No two placements overlap.
    boxes = [p.box for p in res.placements]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            overlap = (a.x < b.x2 and a.x2 > b.x and
                       a.y < b.y2 and a.y2 > b.y and
                       a.z < b.z2 and a.z2 > b.z)
            assert not overlap


def test_non_stackable_keeps_space_above_clear():
    # A flat non-stackable item on the floor; a second tall item must not be
    # placed on top of it, so it has to go beside it (needs the extra width).
    flat = ("table_top", 40, 40, 4, False, False)
    tall = ("box", 40, 40, 40, False, True)
    # Floor is exactly two footprints wide -> both fit side by side, none stacked.
    res = pack((40, 80, 44), [flat, tall])
    assert res.success
    placements = {p.name: p.box for p in res.placements}
    # The tall box must not sit on top of the flat one (its base z must be 0).
    assert abs(placements["box"].z) < 1e-6


# --- trailer evaluation --------------------------------------------------

def test_small_load_fits_smallest_trailer():
    items = [get_catalog_item("queen_mattress"), get_catalog_item("box_large", 4)]
    rec = find_minimum_trailer(items)
    assert rec.fits_any
    # Smallest trailer by volume should be the recommendation.
    assert rec.recommended.trailer.volume_cuft == min(
        e.trailer.volume_cuft for e in rec.evaluations if e.fits
    )


def test_weight_limit_blocks():
    # 30 large appliances are light on volume but crush the weight limit.
    heavy = FurnitureItem("Anvil", 12, 12, 12, weight=2000, quantity=3)
    fit = evaluate_trailer([heavy], get_trailer("4x8 Cargo Trailer"))
    assert not fit.fits
    assert any("weight" in b.lower() for b in fit.blockers)


def test_oversized_item_blocks_with_message():
    # 9 ft sofa won't fit a trailer with a < 9 ft interior.
    big = FurnitureItem("Sectional", 110, 40, 40)
    fit = evaluate_trailer([big], get_trailer("4x8 Cargo Trailer"))
    assert not fit.fits


def test_door_clearance_blocks():
    # A chunky 40x50 cross-section can't pass a 45x46 door at any tilt angle.
    item = FurnitureItem("Crate", 40, 50, 50)
    trailer = get_trailer("4x8 Cargo Trailer")  # door 45x46
    fit = evaluate_trailer([item], trailer)
    assert not fit.fits
    assert any("door" in b.lower() for b in fit.blockers)


def test_thin_item_tilts_through_door():
    # A full mattress (54" wide, 10" thick) clears a 48"x51" door tilted at
    # ~40 degrees, just like in real life.
    item = get_catalog_item("full_mattress")
    fit = evaluate_trailer([item], get_trailer("5x8 Cargo Trailer"))
    assert fit.fits, fit.blockers


def test_huge_load_fits_nothing():
    items = [get_catalog_item("refrigerator", 30)]
    rec = find_minimum_trailer(items)
    assert not rec.fits_any
    assert rec.recommended is None


def test_enclosed_only_filter():
    items = [get_catalog_item("box_medium", 2)]
    rec = find_minimum_trailer(items, enclosed_only=True)
    assert rec.fits_any
    assert rec.recommended.trailer.enclosed


def test_all_catalog_items_are_well_formed():
    for slug in ("sofa", "refrigerator", "dining_table", "king_mattress"):
        it = get_catalog_item(slug)
        assert it.length > 0 and it.width > 0 and it.height > 0
        assert it.total_volume_cuft > 0


if __name__ == "__main__":
    import traceback

    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failures += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(funcs) - failures}/{len(funcs)} passed")
    sys.exit(1 if failures else 0)
