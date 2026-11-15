"""Where text sits on its anchor: matplotlib's horizontal and vertical alignment.

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


VAlignName: TypeAlias = Literal[
    "baseline", "bottom", "center", "center_baseline", "top"
]
"""A vertical alignment as a caller or matplotlib writes it."""


@dataclass(frozen=True)
class AlignBottom:
    """Text standing on its anchor."""

    mpl: ClassVar[Literal["bottom"]] = "bottom"


@dataclass(frozen=True)
class AlignTop:
    """Text hanging from its anchor."""

    mpl: ClassVar[Literal["top"]] = "top"


@dataclass(frozen=True)
class VCentre:
    """Text centred on its anchor, top to bottom."""

    mpl: ClassVar[Literal["center"]] = "center"


@dataclass(frozen=True)
class Baseline:
    """Text whose baseline runs through its anchor."""

    mpl: ClassVar[Literal["baseline"]] = "baseline"


@dataclass(frozen=True)
class VCentreBaseline:
    """Text whose baseline is centred on its anchor."""

    mpl: ClassVar[Literal["center_baseline"]] = "center_baseline"


VAlign: TypeAlias = (
    AlignBottom | AlignTop | VCentre | Baseline | VCentreBaseline
)


def parse_valign(name: str) -> VAlign:
    """``Text.get_verticalalignment()``; ``ValueError`` for another name."""
    for align in (
        AlignBottom(),
        AlignTop(),
        VCentre(),
        Baseline(),
        VCentreBaseline(),
    ):
        if name == align.mpl:
            return align
    raise ValueError(f"not a vertical alignment: {name!r}")
