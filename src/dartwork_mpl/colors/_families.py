"""Model B color family taxonomy.

Each public ``dc.*`` family has exactly one kind. Continuous membership is
derived from the generated colormap catalog; qualitative/discrete membership is
derived from the curated and cycle SSOTs.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from . import _curated, _generated

FamilyKind = Literal[
    "sequential", "multi-hue", "diverging", "cyclic", "qualitative"
]


@dataclass(frozen=True)
class Family:
    kind: FamilyKind
    has_continuous: bool
    discrete_size: int | None


SEQUENTIAL: tuple[str, ...] = tuple(_generated.PALETTE)
CYCLIC: tuple[str, ...] = ("hue", "halo", "corona")
DIVERGING: tuple[str, ...] = tuple(
    name for name in _generated.CMAPS_256 if "_" in name
)
MULTI_HUE: tuple[str, ...] = tuple(
    name
    for name in _generated.CMAPS_256
    if name not in set(SEQUENTIAL) | set(DIVERGING) | set(CYCLIC)
)
QUALITATIVE: tuple[str, ...] = tuple(
    _curated.CURATED_QUALITATIVE_ORDER
) + tuple(_generated.CYCLES)

FAMILIES: dict[str, Family] = {
    **{
        name: Family("sequential", has_continuous=True, discrete_size=10)
        for name in SEQUENTIAL
    },
    **{
        name: Family("multi-hue", has_continuous=True, discrete_size=None)
        for name in MULTI_HUE
    },
    **{
        name: Family("diverging", has_continuous=True, discrete_size=8)
        for name in DIVERGING
    },
    **{
        name: Family("cyclic", has_continuous=True, discrete_size=None)
        for name in CYCLIC
    },
    **{
        name: Family("qualitative", has_continuous=False, discrete_size=8)
        for name in QUALITATIVE
    },
}

_EXPECTED_COUNTS = {
    "sequential": 20,
    "multi-hue": 9,
    "diverging": 11,
    "cyclic": 3,
    "qualitative": 13,
}
_COUNTS = Counter(family.kind for family in FAMILIES.values())
assert _COUNTS == _EXPECTED_COUNTS, dict(_COUNTS)
assert len(FAMILIES) == sum(_EXPECTED_COUNTS.values())

__all__ = [
    "CYCLIC",
    "DIVERGING",
    "FAMILIES",
    "MULTI_HUE",
    "QUALITATIVE",
    "SEQUENTIAL",
    "Family",
    "FamilyKind",
]
