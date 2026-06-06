"""Catalog of U-Haul trailers.

All dimensions are in INCHES and weights in POUNDS. Interior dimensions are
the *usable* cargo space; door dimensions are the opening an item must pass
through to get inside.

NOTE: These are approximate published interior dimensions and are provided for
estimation only. U-Haul specs vary by manufacturer and model year, so confirm
the exact trailer you reserve at uhaul.com before you rely on a tight fit.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Trailer:
    """A U-Haul trailer and its usable cargo space."""

    name: str
    length: float        # interior length, inches (front-to-back)
    width: float         # interior width, inches (side-to-side)
    height: float        # interior height, inches (floor-to-ceiling)
    door_width: float    # door opening width, inches
    door_height: float   # door opening height, inches
    max_load: float      # maximum payload, pounds
    enclosed: bool        # True = walls + roof (weatherproof); False = open utility
    volume_cuft: float    # advertised usable volume, cubic feet
    note: str = ""

    @property
    def interior_volume_cuft(self) -> float:
        """Geometric interior volume (L x W x H) in cubic feet."""
        return (self.length * self.width * self.height) / 1728.0

    def summary(self) -> str:
        kind = "enclosed cargo" if self.enclosed else "open utility"
        return (
            f"{self.name} ({kind}): "
            f"{self.length/12:.1f}' L x {self.width/12:.1f}' W x {self.height/12:.1f}' H, "
            f"~{self.volume_cuft:.0f} cu ft, up to {self.max_load:,.0f} lbs"
        )


# Ordered roughly small -> large. The optimizer sorts by volume regardless, so
# order here is only for display convenience.
UHAUL_TRAILERS = [
    Trailer(
        name="4x8 Cargo Trailer",
        length=94, width=51, height=49,
        door_width=45, door_height=46,
        max_load=1620, enclosed=True, volume_cuft=145,
        note="Smallest enclosed trailer. Tows behind most vehicles.",
    ),
    Trailer(
        name="5x8 Cargo Trailer",
        length=96, width=57, height=54,
        door_width=48, door_height=51,
        max_load=1800, enclosed=True, volume_cuft=171,
        note="A studio / small one-bedroom of furniture.",
    ),
    Trailer(
        name="5x10 Cargo Trailer",
        length=118, width=57, height=54,
        door_width=48, door_height=51,
        max_load=1950, enclosed=True, volume_cuft=210,
        note="Longer floor for couches and mattresses.",
    ),
    Trailer(
        name="6x12 Cargo Trailer",
        length=137, width=67, height=64,
        door_width=60, door_height=57,
        max_load=2500, enclosed=True, volume_cuft=340,
        note="Largest enclosed U-Haul trailer. A one-bedroom apartment.",
    ),
    # Open utility trailers: no roof, so 'height' is a practical, tie-down-safe
    # stacking height rather than a hard ceiling. Loads must be strapped and are
    # exposed to weather. Useful mainly for a few large/sturdy pieces.
    Trailer(
        name="5x8 Utility Trailer (open)",
        length=96, width=55, height=48,
        door_width=55, door_height=48,
        max_load=1890, enclosed=False, volume_cuft=107,
        note="Open bed. Strap everything down; not weatherproof.",
    ),
    Trailer(
        name="6x12 Utility Trailer (open)",
        length=139, width=67, height=54,
        door_width=67, door_height=54,
        max_load=2480, enclosed=False, volume_cuft=233,
        note="Large open bed with ramp. Strap everything down.",
    ),
]


def get_trailer(name: str) -> Trailer:
    """Look up a trailer by (case-insensitive) name."""
    key = name.strip().lower()
    for t in UHAUL_TRAILERS:
        if t.name.lower() == key:
            return t
    raise KeyError(f"No trailer named {name!r}. Options: {[t.name for t in UHAUL_TRAILERS]}")
