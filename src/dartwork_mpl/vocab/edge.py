"""The four edges of a box (the canvas, a plot), and what holds one.

``across``: the edge lies across the width (top, bottom); ``far``: it is the
high end of its axis (top, right). A figure legend holds an edge of the
figure and keeps a gap from the panels: a :class:`Reserve`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeAlias


@dataclass(frozen=True)
class Left:
    """The left edge of the canvas or of a plot."""

    across: ClassVar[bool] = False
    far: ClassVar[bool] = False


@dataclass(frozen=True)
class Right:
    """The right edge of the canvas or of a plot."""

    across: ClassVar[bool] = False
    far: ClassVar[bool] = True


@dataclass(frozen=True)
class Bottom:
    """The bottom edge of the canvas or of a plot."""

    across: ClassVar[bool] = True
    far: ClassVar[bool] = False


@dataclass(frozen=True)
class Top:
    """The top edge of the canvas or of a plot."""

    across: ClassVar[bool] = True
    far: ClassVar[bool] = True


Edge: TypeAlias = Left | Right | Bottom | Top
#: Every edge, left, right, bottom, top.
EDGES: tuple[Edge, ...] = (Left(), Right(), Bottom(), Top())


def edge_of(*, across: bool, far: bool) -> Edge:
    """The edge across (top, bottom) or along the height, at the far end
    (top, right) or the near one."""
    if across:
        return Top() if far else Bottom()
    return Right() if far else Left()


@dataclass(frozen=True)
class Reserve:
    """The figure edge a figure legend holds and the room it keeps, pt."""

    edge: Edge
    gap_pt: float
