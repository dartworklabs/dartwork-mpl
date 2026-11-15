"""Where text sits across its anchor: matplotlib's horizontal alignment.

Each variant carries the name matplotlib takes for it (``.mpl``), written
once; a caller's ``ha="left"`` becomes a variant here and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal, TypeAlias

HAlignName: TypeAlias = Literal["left", "center", "right"]
"""A horizontal alignment as a caller or matplotlib writes it."""


@dataclass(frozen=True)
class AlignLeft:
    """Text starting at its anchor (``ha="left"``)."""

    mpl: ClassVar[Literal["left"]] = "left"


@dataclass(frozen=True)
class AlignCentre:
    """Text centred on its anchor (``ha="center"``)."""

    mpl: ClassVar[Literal["center"]] = "center"


@dataclass(frozen=True)
class AlignRight:
    """Text ending at its anchor (``ha="right"``)."""

    mpl: ClassVar[Literal["right"]] = "right"


HAlign: TypeAlias = AlignLeft | AlignCentre | AlignRight


def parse_halign(value: object) -> HAlign:
    """``ha``; ``ValueError`` otherwise."""
    if value == "left":
        return AlignLeft()
    if value == "center":
        return AlignCentre()
    if value == "right":
        return AlignRight()
    raise ValueError(f"ha must be 'left', 'center' or 'right', got {value!r}")
