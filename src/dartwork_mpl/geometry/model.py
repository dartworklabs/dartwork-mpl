"""matplotlib's names for an Axes' three titles, read once into types.

Each variant here carries the string matplotlib takes for it, written once. A
string from matplotlib becomes a variant here and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal, TypeAlias

MathMode: TypeAlias = bool | Literal["TeX"]
"""How a renderer reads a text: plain, mathtext (``True``) or TeX."""


# ------------------------------------------------------------ titles
@dataclass(frozen=True)
class CentreTitle:
    """``ax.set_title(...)``: the title over the middle of the Axes."""

    loc: ClassVar[Literal["center"]] = "center"


@dataclass(frozen=True)
class LeftTitle:
    """``ax.set_title(..., loc="left")``: a headline over the left edge."""

    loc: ClassVar[Literal["left"]] = "left"


@dataclass(frozen=True)
class RightTitle:
    """``ax.set_title(..., loc="right")``: a note over the right edge."""

    loc: ClassVar[Literal["right"]] = "right"


TitleLoc: TypeAlias = CentreTitle | LeftTitle | RightTitle
"""One of an Axes' three titles."""


def coordinate_follows_data(coords: str) -> bool:
    """The named coordinate frame whose horizontal position follows data."""
    return coords == "data"


@dataclass(frozen=True)
class GlyphGroup:
    """The renderer group matplotlib opens around a text: what is drawn
    directly inside it is the text's glyphs."""


@dataclass(frozen=True)
class OtherGroup:
    """Any other renderer group: a figure, an Axes, a patch, a line."""


#: What a renderer is drawing, by the group its artist opened.
Group = GlyphGroup | OtherGroup


def parse_group(name: str) -> Group:
    """Matplotlib's name for a renderer group (``"text"``, ``"patch"``,
    ``"axes"`` ...) as a :data:`Group`."""
    return GlyphGroup() if name == "text" else OtherGroup()
