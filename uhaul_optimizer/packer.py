"""A 3D bin-packing heuristic for fitting furniture into a trailer.

This uses a greedy "maximal empty spaces" placer: items are placed largest
first, each into the lowest/back-most free space that can hold it, and the
remaining free space is re-split after every placement.

Bin packing in 3D is NP-hard, so this is a heuristic. It can occasionally fail
to find a packing that a patient human (or a smarter solver) would manage. Treat
a successful pack as "this should fit with careful loading" and a failure near
the volume limit as "borderline" rather than a hard guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Box:
    """An axis-aligned box positioned with its corner at (x, y, z), inches.

    x runs front-to-back (length), y side-to-side (width), z vertical (height).
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
    def utilization(self) -> float:
        """Fraction of container volume occupied by placed items (0..1)."""
        if self.container_volume_cuft <= 0:
            return 0.0
        return self.used_volume_cuft / self.container_volume_cuft


# A unit is one indivisible piece to place: (name, l, w, h, keep_upright, stackable).
Unit = tuple[str, float, float, float, bool, bool]

_EPS = 1e-6


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


def _fits(ol: float, ow: float, oh: float, space: Box) -> bool:
    return (ol <= space.length + _EPS
            and ow <= space.width + _EPS
            and oh <= space.height + _EPS)


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


def pack(container: tuple[float, float, float], units: list[Unit]) -> PackResult:
    """Greedily pack ``units`` into a container of (length, width, height) inches."""
    cl, cw, ch = container
    result = PackResult(success=False, container_volume_cuft=(cl * cw * ch) / 1728.0)

    # Hardest pieces first: largest volume, then longest single dimension.
    order = sorted(
        units,
        key=lambda u: (u[1] * u[2] * u[3], max(u[1], u[2], u[3])),
        reverse=True,
    )

    free_spaces: list[Box] = [Box(0, 0, 0, cl, cw, ch)]

    for name, l, w, h, keep_upright, stackable in order:
        best: tuple[tuple[float, float, float], int, Box] | None = None
        best_score: tuple[float, float, float, float] | None = None

        for idx, space in enumerate(free_spaces):
            for (ol, ow, oh) in _orientations(l, w, h, keep_upright):
                if not _fits(ol, ow, oh, space):
                    continue
                # Prefer the lowest space (z), then back (x), then left (y) to
                # pack bottom-up and dense. Within a space, prefer the
                # orientation with the smallest footprint so we conserve floor
                # area, then the shortest height.
                score = (space.z, space.x, space.y, ol * ow, oh)
                if best_score is None or score < best_score:
                    best_score = score
                    best = ((ol, ow, oh), idx, space)

        if best is None:
            result.unplaced.append(name)
            continue

        (ol, ow, oh), _idx, space = best
        placed = Box(space.x, space.y, space.z, ol, ow, oh)
        result.placements.append(Placement(name, placed))

        # Re-split every free space the item intrudes upon.
        new_spaces: list[Box] = []
        for s in free_spaces:
            if _overlaps(s, placed):
                new_spaces.extend(_split_space(s, placed, allow_top=stackable))
            else:
                new_spaces.append(s)
        free_spaces = _prune(new_spaces)

    result.success = not result.unplaced
    return result
