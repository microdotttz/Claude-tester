"""A 3D bin-packing heuristic for fitting furniture into a trailer.

Items are placed one at a time into the lowest/back-most free space that can
hold them (a greedy "maximal empty spaces" placer). Several loading orders are
tried -- biggest-first, longest-first, heaviest-first, and a few seeded
shuffles -- and the first order that packs everything wins (otherwise the best
partial attempt is reported, so blocker messages stay meaningful).

Physical realism rules:

- **No floating furniture.** An item placed off the floor must have at least
  ``MIN_SUPPORT`` of its base area resting on stackable items whose tops are
  exactly at its base height.
- **Flexible items bend.** Units flagged ``flexible`` (mattresses) may be
  squeezed/bowed down to ``FLEX_RATIO`` of any dimension when a space is
  slightly too small, occupying only what the space allows. The 12% allowance
  is calibrated against U-Haul's published claims: a queen mattress fits a
  5x8, a full fits a 4x8, and a king fits a 6x12 -- and nothing smaller.

Bin packing in 3D is NP-hard, so this remains a heuristic. Treat a successful
pack as "this should fit with careful loading" and a failure near the volume
limit as "borderline" rather than a hard guarantee.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import NamedTuple

FLEX_RATIO = 0.88    # flexible items may be squeezed/bowed to 88% per dimension
MIN_SUPPORT = 0.70   # off-floor placements need 70% of their base held up
SHELF_WALL = 0.75    # panel thickness used to carve a shelf's inner cavity
_EPS = 1e-6
_SHUFFLE_SEED = 1234  # deterministic restarts so results are reproducible
_N_SHUFFLES = 4


@dataclass(frozen=True)
class Box:
    """An axis-aligned box positioned with its corner at (x, y, z), inches.

    x runs front-to-back (length, hitch end at x=0), y side-to-side (width),
    z vertical (height).
    """

    x: float
    y: float
    z: float
    length: float
    width: float
    height: float

    @property
    def x2(self) -> float:
        return self.x + self.length

    @property
    def y2(self) -> float:
        return self.y + self.width

    @property
    def z2(self) -> float:
        return self.z + self.height

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass
class Placement:
    """Where a single furniture unit ended up."""

    name: str
    box: Box
    weight: float = 0.0
    inside_shelf: bool = False   # placed within another item's (a shelf's) cavity


@dataclass
class PackResult:
    """Outcome of trying to pack a set of units into one container."""

    success: bool
    placements: list[Placement] = field(default_factory=list)
    unplaced: list[str] = field(default_factory=list)
    container_volume_cuft: float = 0.0

    @property
    def used_volume_cuft(self) -> float:
        return sum(p.box.volume for p in self.placements) / 1728.0

    @property
    def effective_used_volume_cuft(self) -> float:
        """Used volume counting shelf-nested items as free (they reuse the
        shelf's already-counted outer box), so utilization stays meaningful."""
        return sum(p.box.volume for p in self.placements if not p.inside_shelf) / 1728.0

    @property
    def utilization(self) -> float:
        """Fraction of container volume occupied by placed items (0..1)."""
        if self.container_volume_cuft <= 0:
            return 0.0
        return self.effective_used_volume_cuft / self.container_volume_cuft


class Unit(NamedTuple):
    """One indivisible piece to place. Plain tuples coerce positionally."""

    name: str
    length: float
    width: float
    height: float
    keep_upright: bool = False
    stackable: bool = True
    weight: float = 0.0
    flexible: bool = False
    fillable: bool = False   # a shelf: hollow, so smaller items pack inside it


def _orientations(l: float, w: float, h: float, keep_upright: bool) -> list[tuple[float, float, float]]:
    """Distinct (length, width, height) orientations for an item."""
    if keep_upright:
        # Only rotate about the vertical axis: swap footprint length/width.
        cands = [(l, w, h), (w, l, h)]
    else:
        cands = [
            (l, w, h), (l, h, w),
            (w, l, h), (w, h, l),
            (h, l, w), (h, w, l),
        ]
    seen: list[tuple[float, float, float]] = []
    for c in cands:
        if c not in seen:
            seen.append(c)
    return seen


def _clamp_to_space(
    ol: float, ow: float, oh: float, space: Box, flexible: bool
) -> tuple[float, float, float] | None:
    """Dimensions the item would occupy in ``space``, or None if it can't fit.

    Rigid items must fit as-is. Flexible items fit if every dimension can
    squeeze to within the space at ``FLEX_RATIO``, and then occupy only what
    the space allows (the squeeze presses against real walls/items, since
    maximal spaces are bounded by them).
    """
    if flexible:
        if (ol * FLEX_RATIO <= space.length + _EPS
                and ow * FLEX_RATIO <= space.width + _EPS
                and oh * FLEX_RATIO <= space.height + _EPS):
            return (min(ol, space.length), min(ow, space.width), min(oh, space.height))
        return None
    if ol <= space.length + _EPS and ow <= space.width + _EPS and oh <= space.height + _EPS:
        return (ol, ow, oh)
    return None


def _inside_cavity(x: float, y: float, l: float, w: float, z: float, cavities) -> bool:
    """True if an l x w base at height z sits within a shelf cavity (which holds
    it up via the shelf's panels/walls at any internal level)."""
    for c in cavities:
        if (c.x - _EPS <= x and x + l <= c.x2 + _EPS
                and c.y - _EPS <= y and y + w <= c.y2 + _EPS
                and c.z - _EPS <= z < c.z2 - _EPS):
            return True
    return False


def _support_fraction(
    x: float, y: float, l: float, w: float, z: float,
    placed: list[tuple[Box, bool]],
    cavities=(),
) -> float:
    """Fraction of an l x w base at height z resting on stackable tops.

    Returns 1.0 if the base sits inside a shelf cavity — the shelf's structure
    holds items at any internal level."""
    if z <= _EPS:
        return 1.0  # the floor supports everything
    if _inside_cavity(x, y, l, w, z, cavities):
        return 1.0
    area = 0.0
    for box, stackable in placed:
        if not stackable or abs(box.z2 - z) > _EPS:
            continue
        dx = min(x + l, box.x2) - max(x, box.x)
        dy = min(y + w, box.y2) - max(y, box.y)
        if dx > 0 and dy > 0:
            area += dx * dy
    return area / (l * w)


def _split_space(free: Box, placed: Box, allow_top: bool) -> list[Box]:
    """Return the maximal empty sub-boxes of ``free`` after removing ``placed``.

    ``placed`` is assumed to overlap ``free``. Generated sub-boxes overlap each
    other on purpose — that is what keeps each one maximal.
    """
    out: list[Box] = []
    # Slab in front of / behind the item (x axis)
    if placed.x > free.x + _EPS:
        out.append(Box(free.x, free.y, free.z, placed.x - free.x, free.width, free.height))
    if placed.x2 < free.x2 - _EPS:
        out.append(Box(placed.x2, free.y, free.z, free.x2 - placed.x2, free.width, free.height))
    # Slab to either side (y axis)
    if placed.y > free.y + _EPS:
        out.append(Box(free.x, free.y, free.z, free.length, placed.y - free.y, free.height))
    if placed.y2 < free.y2 - _EPS:
        out.append(Box(free.x, placed.y2, free.z, free.length, free.y2 - placed.y2, free.height))
    # Slab below the item (z axis) — rarely used since we pack bottom-up.
    if placed.z > free.z + _EPS:
        out.append(Box(free.x, free.y, free.z, free.length, free.width, placed.z - free.z))
    # Slab above the item (z axis) — only if the item can be stacked upon.
    if allow_top and placed.z2 < free.z2 - _EPS:
        out.append(Box(free.x, free.y, placed.z2, free.length, free.width, free.z2 - placed.z2))
    return out


def _contained(a: Box, b: Box) -> bool:
    """True if box ``a`` is fully inside box ``b``."""
    return (b.x - _EPS <= a.x and a.x2 <= b.x2 + _EPS
            and b.y - _EPS <= a.y and a.y2 <= b.y2 + _EPS
            and b.z - _EPS <= a.z and a.z2 <= b.z2 + _EPS)


def _prune(spaces: list[Box]) -> list[Box]:
    """Drop zero-volume spaces and any space fully contained within another.

    Two identical (mutually contained) spaces are de-duplicated by keeping only
    the earlier one.
    """
    kept: list[Box] = []
    for i, s in enumerate(spaces):
        if s.length <= _EPS or s.width <= _EPS or s.height <= _EPS:
            continue
        redundant = False
        for j, o in enumerate(spaces):
            if i == j or not _contained(s, o):
                continue
            if _contained(o, s):
                # Identical boxes: keep only the first occurrence.
                if j < i:
                    redundant = True
                    break
            else:
                # s is strictly inside o.
                redundant = True
                break
        if not redundant:
            kept.append(s)
    return kept


def _overlaps(a: Box, b: Box) -> bool:
    return (a.x < b.x2 - _EPS and a.x2 > b.x + _EPS
            and a.y < b.y2 - _EPS and a.y2 > b.y + _EPS
            and a.z < b.z2 - _EPS and a.z2 > b.z + _EPS)


def _pack_once(container: tuple[float, float, float], order: list[Unit]) -> PackResult:
    """Greedily pack units in the given order; one attempt, no reordering."""
    cl, cw, ch = container
    result = PackResult(success=False, container_volume_cuft=(cl * cw * ch) / 1728.0)

    free_spaces: list[Box] = [Box(0, 0, 0, cl, cw, ch)]
    placed_solid: list[tuple[Box, bool]] = []  # (box, stackable) for support checks
    cavities: list[Box] = []                    # interior spaces of fillable shelves

    for u in order:
        best: tuple[tuple[float, float, float], Box] | None = None
        best_score: tuple[float, float, float, float, float] | None = None

        for space in free_spaces:
            for (ol, ow, oh) in _orientations(u.length, u.width, u.height, u.keep_upright):
                dims = _clamp_to_space(ol, ow, oh, space, u.flexible)
                if dims is None:
                    continue
                col, cow, coh = dims
                # No floating: off-floor bases need real support underneath (or
                # to be sitting inside a shelf, which holds them up).
                if (space.z > _EPS
                        and _support_fraction(space.x, space.y, col, cow, space.z,
                                              placed_solid, cavities) < MIN_SUPPORT - _EPS):
                    continue
                # Prefer the lowest space (z), then back (x), then left (y) to
                # pack bottom-up and dense. Within a space, prefer the
                # orientation with the smallest footprint so we conserve floor
                # area, then the shortest height.
                score = (space.z, space.x, space.y, col * cow, coh)
                if best_score is None or score < best_score:
                    best_score = score
                    best = ((col, cow, coh), space)

        if best is None:
            result.unplaced.append(u.name)
            continue

        (col, cow, coh), space = best
        placed = Box(space.x, space.y, space.z, col, cow, coh)
        inside = _inside_cavity(placed.x, placed.y, placed.length, placed.width, placed.z, cavities)
        result.placements.append(Placement(u.name, placed, u.weight, inside_shelf=inside))
        placed_solid.append((placed, u.stackable))

        # Re-split every free space the item intrudes upon.
        new_spaces: list[Box] = []
        for s in free_spaces:
            if _overlaps(s, placed):
                new_spaces.extend(_split_space(s, placed, allow_top=u.stackable))
            else:
                new_spaces.append(s)

        # A fillable shelf is hollow: re-open its interior cavity as usable space
        # so smaller items can be packed inside it.
        if u.fillable:
            cav = Box(placed.x + SHELF_WALL, placed.y + SHELF_WALL, placed.z + SHELF_WALL,
                      max(0.0, col - 2 * SHELF_WALL), max(0.0, cow - 2 * SHELF_WALL),
                      max(0.0, coh - 2 * SHELF_WALL))
            if cav.length > _EPS and cav.width > _EPS and cav.height > _EPS:
                cavities.append(cav)
                new_spaces.append(cav)
        free_spaces = _prune(new_spaces)

    result.success = not result.unplaced
    return result


def _orderings(units: list[Unit]) -> list[list[Unit]]:
    """Candidate loading orders to try, de-duplicated, deterministic."""
    def vol(u: Unit) -> float:
        return u.length * u.width * u.height

    def maxdim(u: Unit) -> float:
        return max(u.length, u.width, u.height)

    def footprint(u: Unit) -> float:
        d = sorted((u.length, u.width, u.height))
        return d[1] * d[2]  # largest face

    candidates = [
        sorted(units, key=lambda u: (vol(u), maxdim(u)), reverse=True),      # biggest first
        sorted(units, key=lambda u: (maxdim(u), vol(u)), reverse=True),      # longest first
        sorted(units, key=lambda u: (footprint(u), vol(u)), reverse=True),   # widest face first
        sorted(units, key=lambda u: (u.weight, vol(u)), reverse=True),       # heaviest first
    ]
    rng = random.Random(_SHUFFLE_SEED)
    for _ in range(_N_SHUFFLES):
        shuffled = list(units)
        rng.shuffle(shuffled)
        candidates.append(shuffled)

    out: list[list[Unit]] = []
    seen: set[tuple[str, ...]] = set()
    for c in candidates:
        key = tuple(u.name for u in c)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def pack(container: tuple[float, float, float], units: list) -> PackResult:
    """Pack ``units`` into a (length, width, height)-inch container.

    Tries several loading orders and returns the first complete pack, or the
    best partial attempt (fewest unplaced items, then most volume placed).
    ``units`` may be :class:`Unit` instances or plain positional tuples.
    """
    coerced = [u if isinstance(u, Unit) else Unit(*u) for u in units]

    best: PackResult | None = None
    for order in _orderings(coerced):
        result = _pack_once(container, order)
        if result.success:
            return result
        if best is None or (len(result.unplaced), -result.used_volume_cuft) < \
                (len(best.unplaced), -best.used_volume_cuft):
            best = result
    return best if best is not None else _pack_once(container, [])
