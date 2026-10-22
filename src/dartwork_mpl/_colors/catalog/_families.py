"""Model B color family taxonomy.

Each public ``dc.*`` family has exactly one kind, and each kind is its own
frozen type holding only the data that kind has: sequential, diverging and
qualitative families carry the size of their designed discrete form;
multi-hue and cyclic families have no fixed form size. Whether a family
ships a continuous colormap follows from its kind (every kind except
qualitative does), so it is not stored.

Continuous membership is derived from the generated colormap catalog;
qualitative/discrete membership is derived from the curated and cycle SSOTs.
Callers branch on the family's type with ``match``; ``kind`` is the
family's public label (``list_colors`` records, error messages) and is the
same for every value of a type.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Literal, TypeAlias

from .. import _curated, _generated

FamilyKind = Literal[
    "sequential", "multi-hue", "diverging", "cyclic", "qualitative"
]


def _require_form_size(discrete_size: int) -> None:
    """Reject a designed discrete form with no colours."""
    if isinstance(discrete_size, bool) or discrete_size < 1:
        raise ValueError(
            f"discrete_size must be a positive integer, got {discrete_size!r}"
        )


@dataclass(frozen=True)
class SequentialFamily:
    """A one-hue lightness ladder with a continuous colormap.

    ``discrete_size`` is the number of stops in the designed ladder; it is
    positive.
    """

    kind: ClassVar[Literal["sequential"]] = "sequential"
    discrete_size: int

    def __post_init__(self) -> None:
        """Reject a non-positive ladder size."""
        _require_form_size(self.discrete_size)


@dataclass(frozen=True)
class MultiHueFamily:
    """A multi-hue continuous colormap; discrete forms are frozen indices."""

    kind: ClassVar[Literal["multi-hue"]] = "multi-hue"


@dataclass(frozen=True)
class DivergingFamily:
    """A two-sided colormap with a designed canonical row.

    ``discrete_size`` is the number of canonical stops (the odd forms add
    the colormap midpoint); it is positive.
    """

    kind: ClassVar[Literal["diverging"]] = "diverging"
    discrete_size: int

    def __post_init__(self) -> None:
        """Reject a non-positive canonical size."""
        _require_form_size(self.discrete_size)


@dataclass(frozen=True)
class CyclicFamily:
    """A cyclic continuous colormap; discrete forms sample it evenly."""

    kind: ClassVar[Literal["cyclic"]] = "cyclic"


@dataclass(frozen=True)
class QualitativeFamily:
    """A categorical colour set with no continuous colormap.

    ``discrete_size`` is the number of colours in the set; it is positive.
    """

    kind: ClassVar[Literal["qualitative"]] = "qualitative"
    discrete_size: int

    def __post_init__(self) -> None:
        """Reject an empty colour set."""
        _require_form_size(self.discrete_size)


Family: TypeAlias = (
    SequentialFamily
    | MultiHueFamily
    | DivergingFamily
    | CyclicFamily
    | QualitativeFamily
)


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

FAMILIES: Mapping[str, Family] = MappingProxyType(
    {
        **{name: SequentialFamily(discrete_size=10) for name in SEQUENTIAL},
        **{name: MultiHueFamily() for name in MULTI_HUE},
        **{name: DivergingFamily(discrete_size=8) for name in DIVERGING},
        **{name: CyclicFamily() for name in CYCLIC},
        **{name: QualitativeFamily(discrete_size=8) for name in QUALITATIVE},
    }
)

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
    "CyclicFamily",
    "DivergingFamily",
    "Family",
    "FamilyKind",
    "MultiHueFamily",
    "QualitativeFamily",
    "SequentialFamily",
]
