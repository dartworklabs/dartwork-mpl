"""matplotlib's names for an axis, a title, a projection and a label side,
read once into types.

matplotlib says ``"x"`` / ``"y"`` for an Axes' two axes; here an axis is
:class:`X` or :class:`Y` (:data:`Which`), matched exhaustively, and
``.letter`` gives matplotlib's name back. Each other variant here carries the
string matplotlib takes for it, written once, the same way. A string from
matplotlib or a caller becomes a variant here and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal, TypeAlias

Letter: TypeAlias = Literal["x", "y"]
"""matplotlib's name for one axis of an Axes, as a caller writes it."""

Letters: TypeAlias = Literal["x", "y", "both"]
"""matplotlib's name for one axis of an Axes, or both."""


@dataclass(frozen=True)
class X:
    """The horizontal axis, ``ax.xaxis``: column 0 of an ``(x, y)`` pair."""

    letter: ClassVar[Literal["x"]] = "x"
    column: ClassVar[int] = 0
    horizontal: ClassVar[bool] = True

    @property
    def other(self) -> Y:
        """The axis across this one."""
        return Y()


@dataclass(frozen=True)
class Y:
    """The vertical axis, ``ax.yaxis``: column 1 of an ``(x, y)`` pair."""

    letter: ClassVar[Literal["y"]] = "y"
    column: ClassVar[int] = 1
    horizontal: ClassVar[bool] = False

    @property
    def other(self) -> X:
        """The axis across this one."""
        return X()


Which: TypeAlias = X | Y


def parse_which(value: object) -> Which:
    """``"x"`` or ``"y"`` from a caller or matplotlib; ``ValueError`` otherwise."""
    if value == "x":
        return X()
    if value == "y":
        return Y()
    raise ValueError(f"axis must be 'x' or 'y', got {value!r}")


def parse_axes(value: object) -> tuple[Which, ...]:
    """``"x"``, ``"y"`` or ``"both"`` from a caller; ``ValueError`` otherwise."""
    if value == "both":
        return (X(), Y())
    if value in ("x", "y"):
        return (parse_which(value),)
    raise ValueError(f"axis must be 'x', 'y' or 'both', got {value!r}")


def bars_along(orientation: object) -> Which | None:
    """The axis bars of a ``BarContainer.orientation`` stand on.

    ``"vertical"`` bars stand along x, ``"horizontal"`` ones along y; a
    container made without an orientation stands on neither.
    """
    if orientation == "vertical":
        return X()
    if orientation == "horizontal":
        return Y()
    return None


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


# ------------------------------------------------------------ label sides
@dataclass(frozen=True)
class Near:
    """An axis label on its axis' own side: left of y, below x."""


@dataclass(frozen=True)
class Far:
    """An axis label across the plot: right of y, above x (a twin's side)."""


AxisSide: TypeAlias = Near | Far


def parse_axis_side(position: str) -> AxisSide:
    """``Axis.get_label_position()``; ``ValueError`` for another name."""
    if position in ("left", "bottom"):
        return Near()
    if position in ("right", "top"):
        return Far()
    raise ValueError(f"not an axis label position: {position!r}")
