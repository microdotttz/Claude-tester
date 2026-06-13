"""Tests for the U-Haul space optimizer."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uhaul_optimizer.furniture import FurnitureItem, get_catalog_item
from uhaul_optimizer.optimizer import evaluate_trailer, find_minimum_trailer
from uhaul_optimizer.packer import Box, Unit, pack, _orderings, _support_fraction
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


def test_mattress_footprints_match_industry_standard_sizes():
    # Locks the audited mattress sizes (W x L) to the standard mattress sizes.
    expected = {
        "twin_mattress": (38, 75),
        "full_mattress": (54, 75),
        "queen_mattress": (60, 80),
        "king_mattress": (76, 80),
    }
    for slug, (w, l) in expected.items():
        it = get_catalog_item(slug)
        assert (it.width, it.length) == (w, l), f"{slug} footprint drifted"


def test_moving_boxes_match_standard_box_volumes():
    # Standard moving-box sizes: small 1.5, medium 3.0, large 4.5 cu ft.
    assert abs(get_catalog_item("box_medium").volume_cuft - 3.0) < 0.05
    assert abs(get_catalog_item("box_large").volume_cuft - 4.5) < 0.05


def test_kallax_and_litter_robot_are_in_the_catalog():
    from uhaul_optimizer.furniture import FURNITURE_CATEGORIES

    kallax = get_catalog_item("kallax")
    assert "Kallax" in kallax.name
    assert FURNITURE_CATEGORIES["kallax"] == "Living Room"
    assert not kallax.keep_upright   # reversible unit, may lie down to pack

    robot = get_catalog_item("litter_robot")
    assert "Litter-Robot" in robot.name
    assert FURNITURE_CATEGORIES["litter_robot"] == "Appliances"
    assert robot.keep_upright and not robot.stackable   # motorized; don't crush

    # Both should fit somewhere.
    for slug in ("kallax", "litter_robot"):
        assert find_minimum_trailer([get_catalog_item(slug)]).fits_any


# --- flexible (bendable) items -------------------------------------------

def test_flexible_item_squeezes_into_a_tight_space():
    # 60" wide into a 57" space: a rigid item fails, a flexible one bows in.
    rigid = pack((96, 57, 54), [Unit("m", 80, 60, 11, flexible=False)])
    assert not rigid.success
    flex = pack((96, 57, 54), [Unit("m", 80, 60, 11, flexible=True)])
    assert flex.success
    # It occupies only the space available, not its full 60" width.
    assert flex.placements[0].box.width <= 57 + 1e-6


def test_mattress_claims_match_uhaul(  ):
    # U-Haul's own published claims: full->4x8, queen->5x8, king->6x12.
    for slug, expected in [("full_mattress", "4x8 Cargo Trailer"),
                           ("queen_mattress", "5x8 Cargo Trailer"),
                           ("king_mattress", "6x12 Cargo Trailer")]:
        rec = find_minimum_trailer([get_catalog_item(slug)], enclosed_only=True)
        assert rec.recommended is not None, f"{slug} should fit some enclosed trailer"
        assert rec.recommended.trailer.name == expected, \
            f"{slug} -> {rec.recommended.trailer.name}, expected {expected}"


def test_rigid_box_spring_needs_a_bigger_trailer_than_the_mattress():
    # A queen mattress flexes into a 5x8; the rigid box spring of the same
    # footprint does not, so it needs the 6x12.
    mattress = find_minimum_trailer([get_catalog_item("queen_mattress")], enclosed_only=True)
    boxspring = find_minimum_trailer([get_catalog_item("box_spring_queen")], enclosed_only=True)
    assert mattress.recommended.trailer.name == "5x8 Cargo Trailer"
    assert boxspring.recommended.trailer.volume_cuft > mattress.recommended.trailer.volume_cuft


# --- no floating furniture (support rule) --------------------------------

def test_support_fraction_counts_only_stackable_tops_at_the_right_height():
    assert _support_fraction(0, 0, 10, 10, 0, []) == 1.0  # floor holds everything
    support = [(Box(0, 0, 0, 10, 10, 10), True)]
    assert abs(_support_fraction(0, 0, 10, 10, 10, support) - 1.0) < 1e-6  # fully held
    assert abs(_support_fraction(5, 0, 10, 10, 10, support) - 0.5) < 1e-6  # half overhang
    # A non-stackable item underneath provides no support.
    nostack = [(Box(0, 0, 0, 10, 10, 10), False)]
    assert _support_fraction(0, 0, 10, 10, 10, nostack) == 0.0
    # Wrong height (gap) provides no support.
    assert _support_fraction(0, 0, 10, 10, 20, support) == 0.0


def test_no_item_is_placed_without_enough_support():
    # A floor of small boxes plus larger boxes; verify every off-floor box is
    # at least 70% supported by stackable tops directly beneath it.
    units = [Unit(f"b{i}", 24, 24, 24, weight=20) for i in range(12)]
    res = pack((48, 48, 72), units)
    placed = [(p.box, True) for p in res.placements]
    for p in res.placements:
        if p.box.z > 1e-6:
            frac = _support_fraction(p.box.x, p.box.y, p.box.length, p.box.width,
                                     p.box.z, placed)
            assert frac >= 0.70 - 1e-6, f"{p.name} floats with only {frac:.0%} support"


# --- multiple loading orders ---------------------------------------------

def test_orderings_are_distinct_and_lead_with_biggest_first():
    units = [Unit("a", 40, 30, 20, weight=5), Unit("b", 50, 10, 10, weight=50),
             Unit("c", 30, 30, 30, weight=10)]
    orders = _orderings(units)
    assert len(orders) >= 4
    # First ordering is biggest-volume-first (c=27000, a=24000, b=5000).
    assert [u.name for u in orders[0]][:2] == ["c", "a"]
    # All orderings are permutations of the same set.
    for o in orders:
        assert sorted(u.name for u in o) == ["a", "b", "c"]


# --- tongue weight / balance ---------------------------------------------

def test_balance_advice_present_and_flags_tail_heavy_load():
    # A few heavy pieces plus light boxes: there should be a front-weight number
    # and some balance advice on the recommended trailer.
    items = [get_catalog_item("refrigerator"), get_catalog_item("washer"),
             get_catalog_item("box_large", 6)]
    rec = find_minimum_trailer(items)
    assert rec.recommended is not None
    fit = rec.recommended
    assert fit.front_weight_pct is not None
    assert 0 <= fit.front_weight_pct <= 100
    assert fit.balance_advice  # non-empty


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
