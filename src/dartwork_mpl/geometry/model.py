"""matplotlib's names for a title and a projection, read once into types.

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


# ------------------------------------------------------------ projections
@dataclass(frozen=True)
class Rectilinear:
    """matplotlib's plain 2D Axes."""


@dataclass(frozen=True)
class ThreeD:
    """A 3D Axes (``projection="3d"``)."""


@dataclass(frozen=True)
class Curved:
    """Any other projection: polar, geographic, a registered one."""


Projection: TypeAlias = Rectilinear | ThreeD | Curved


def parse_projection(name: str) -> Projection:
    """The projection matplotlib names ``name`` (``Axes.name``)."""
    if name == "rectilinear":
        return Rectilinear()
    if name == "3d":
        return ThreeD()
    return Curved()
