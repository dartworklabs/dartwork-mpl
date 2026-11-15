"""matplotlib's names for an axis and a projection, read once into types.

matplotlib says ``"x"`` / ``"y"`` for an Axes' two axes; here an axis is
:class:`X` or :class:`Y` (:data:`Which`), matched exhaustively, and
``.letter`` gives matplotlib's name back. A projection is read by name only
to ask whether it is the plain 2D one or the 3D one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal, TypeAlias

Letter: TypeAlias = Literal["x", "y"]
"""matplotlib's name for one axis of an Axes."""

TitleLoc: TypeAlias = Literal["center", "left", "right"]
"""``ax.set_title``'s ``loc``."""


@dataclass(frozen=True)
class X:
    """The horizontal axis, ``ax.xaxis``: column 0 of an ``(x, y)`` pair."""

    letter: ClassVar[Letter] = "x"
    column: ClassVar[int] = 0
    horizontal: ClassVar[bool] = True

    @property
    def other(self) -> Y:
        """The axis across this one."""
        return Y()


@dataclass(frozen=True)
class Y:
    """The vertical axis, ``ax.yaxis``: column 1 of an ``(x, y)`` pair."""

    letter: ClassVar[Letter] = "y"
    column: ClassVar[int] = 1
    horizontal: ClassVar[bool] = False

    @property
    def other(self) -> X:
        """The axis across this one."""
        return X()


Which: TypeAlias = X | Y


def which(letter: Letter) -> Which:
    """The axis matplotlib names ``letter``."""
    return X() if letter == "x" else Y()


Letters: TypeAlias = Literal["x", "y", "both"]
"""matplotlib's name for one axis of an Axes, or both."""


def parse_which(value: object) -> Which:
    """``"x"`` or ``"y"`` from a caller; ``ValueError`` otherwise."""
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


def rectilinear(name: str) -> bool:
    """Whether a projection name is matplotlib's plain 2D Axes."""
    return name == "rectilinear"


def three_d(name: object) -> bool:
    """Whether a projection name is matplotlib's 3D Axes."""
    return name == "3d"
