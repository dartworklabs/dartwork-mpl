"""Where a legend sits: an inside spot (:data:`Loc`) or a side outside
(:data:`Side`), each carrying matplotlib's ``loc`` for it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from .model import LocName


@dataclass(frozen=True)
class UpperRight:
    """``loc="upper right"``."""

    code: ClassVar[LocName] = "upper right"
    anchor: ClassVar[tuple[float, float]] = (1.0, 1.0)


@dataclass(frozen=True)
class UpperLeft:
    """``loc="upper left"``."""

    code: ClassVar[LocName] = "upper left"
    anchor: ClassVar[tuple[float, float]] = (0.0, 1.0)


@dataclass(frozen=True)
class LowerLeft:
    """``loc="lower left"``."""

    code: ClassVar[LocName] = "lower left"
    anchor: ClassVar[tuple[float, float]] = (0.0, 0.0)


@dataclass(frozen=True)
class LowerRight:
    """``loc="lower right"``."""

    code: ClassVar[LocName] = "lower right"
    anchor: ClassVar[tuple[float, float]] = (1.0, 0.0)


@dataclass(frozen=True)
class UpperCenter:
    """``loc="upper center"``."""

    code: ClassVar[LocName] = "upper center"
    anchor: ClassVar[tuple[float, float]] = (0.5, 1.0)


@dataclass(frozen=True)
class LowerCenter:
    """``loc="lower center"``."""

    code: ClassVar[LocName] = "lower center"
    anchor: ClassVar[tuple[float, float]] = (0.5, 0.0)


@dataclass(frozen=True)
class CenterRight:
    """``loc="center right"``."""

    code: ClassVar[LocName] = "center right"
    anchor: ClassVar[tuple[float, float]] = (1.0, 0.5)


@dataclass(frozen=True)
class CenterLeft:
    """``loc="center left"``."""

    code: ClassVar[LocName] = "center left"
    anchor: ClassVar[tuple[float, float]] = (0.0, 0.5)


#: An inside spot: matplotlib's ``loc`` for it (``code``) and where it sits
#: in its container, as fractions (``anchor``). The spots, in the order they
#: are tried, are :data:`INSIDE_SPOTS`.
Loc = (
    UpperRight
    | UpperLeft
    | LowerLeft
    | LowerRight
    | UpperCenter
    | LowerCenter
    | CenterRight
    | CenterLeft
)

#: Every inside spot, in the order it is tried.
INSIDE_SPOTS: tuple[Loc, ...] = (
    UpperRight(),
    UpperLeft(),
    LowerLeft(),
    LowerRight(),
    UpperCenter(),
    LowerCenter(),
    CenterRight(),
    CenterLeft(),
)


@dataclass(frozen=True)
class Above:
    """Above the container. ``loc="above"``."""

    word: ClassVar[str] = "above"
    across: ClassVar[bool] = True
    far: ClassVar[bool] = True
    legend_loc: ClassVar[Loc] = LowerCenter()
    figure_loc: ClassVar[Loc] = UpperCenter()


@dataclass(frozen=True)
class Below:
    """Below the container. ``loc="below"``."""

    word: ClassVar[str] = "below"
    across: ClassVar[bool] = True
    far: ClassVar[bool] = False
    legend_loc: ClassVar[Loc] = UpperCenter()
    figure_loc: ClassVar[Loc] = LowerCenter()


@dataclass(frozen=True)
class Right:
    """Right of the container. ``loc="right"``."""

    word: ClassVar[str] = "right"
    across: ClassVar[bool] = False
    far: ClassVar[bool] = True
    legend_loc: ClassVar[Loc] = CenterLeft()
    figure_loc: ClassVar[Loc] = CenterRight()


@dataclass(frozen=True)
class Left:
    """Left of the container. ``loc="left"``."""

    word: ClassVar[str] = "left"
    across: ClassVar[bool] = False
    far: ClassVar[bool] = False
    legend_loc: ClassVar[Loc] = CenterRight()
    figure_loc: ClassVar[Loc] = CenterLeft()


#: A side of an Axes or figure a legend sits outside of. ``word`` is how a
#: caller names it (``loc="above"``); ``across``: the legend lies across the
#: width (above, below); ``far``: the side is the high end of its axis (above,
#: right). ``legend_loc`` is the legend's own edge that faces the Axes,
#: ``figure_loc`` a figure legend's edge that faces the figure's edge; that
#: spot is also the middle of the side.
Side = Above | Below | Right | Left

SIDES: tuple[Side, ...] = (Above(), Below(), Right(), Left())


def middle(side: Side) -> tuple[float, float]:
    """The middle of ``side``, as fractions of its container."""
    return side.figure_loc.anchor


def outward(side: Side) -> tuple[float, float]:
    """The unit step away from the container, past ``side``."""
    step = 1.0 if side.far else -1.0
    return (0.0, step) if side.across else (step, 0.0)


#: Where a legend may go when no inside spot is free, in order.
FALLBACK_SIDES: tuple[Side, ...] = (Above(), Below(), Right())
