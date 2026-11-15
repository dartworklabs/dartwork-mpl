"""Where a short label goes: a side of its point, a corner of its Axes, a place
on a horizontal line, a panel letter's left edge, and the tries among them.

Each place carries the offset and alignment it puts text at; the parsers in
``model`` turn a caller's ``side=`` / ``loc=`` / ``x=`` into one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, TypeAlias

from ..vocab import (
    AlignBottom,
    AlignCentre,
    AlignLeft,
    AlignRight,
    AlignTop,
    HAlign,
    Span,
    VAlign,
    VCentre,
)


# ------------------------------------------------------------ notes
@dataclass(frozen=True)
class Above:
    """Above the point (``side="above"``); for a line, above it."""

    offset: ClassVar[tuple[float, float]] = (0.0, 1.0)
    ha: ClassVar[HAlign] = AlignCentre()
    va: ClassVar[VAlign] = AlignBottom()

    @property
    def tries(self) -> tuple[Side, ...]:
        """The one side asked."""
        return (self,)


@dataclass(frozen=True)
class Below:
    """Below the point; for a line, below it."""

    offset: ClassVar[tuple[float, float]] = (0.0, -1.0)
    ha: ClassVar[HAlign] = AlignCentre()
    va: ClassVar[VAlign] = AlignTop()

    @property
    def tries(self) -> tuple[Side, ...]:
        """The one side asked."""
        return (self,)


@dataclass(frozen=True)
class Right:
    """Right of the point."""

    offset: ClassVar[tuple[float, float]] = (1.0, 0.0)
    ha: ClassVar[HAlign] = AlignLeft()
    va: ClassVar[VAlign] = VCentre()

    @property
    def tries(self) -> tuple[Side, ...]:
        """The one side asked."""
        return (self,)


@dataclass(frozen=True)
class Left:
    """Left of the point."""

    offset: ClassVar[tuple[float, float]] = (-1.0, 0.0)
    ha: ClassVar[HAlign] = AlignRight()
    va: ClassVar[VAlign] = VCentre()

    @property
    def tries(self) -> tuple[Side, ...]:
        """The one side asked."""
        return (self,)


Side: TypeAlias = Above | Below | Right | Left
"""Where ``annotate_value`` puts a label from its point."""


SIDES: tuple[Side, ...] = (Above(), Below(), Right(), Left())


@dataclass(frozen=True)
class AnySide:
    """``side="auto"``: the first side that is free, in :data:`SIDES` order."""

    @property
    def tries(self) -> tuple[Side, ...]:
        """Every side, in the order tried."""
        return SIDES


SideChoice: TypeAlias = Side | AnySide


@dataclass(frozen=True)
class UpperLeft:
    """An Axes' upper left corner; ``inward`` points into the Axes."""

    anchor: ClassVar[tuple[float, float]] = (0.0, 1.0)
    inward: ClassVar[tuple[float, float]] = (1.0, -1.0)
    ha: ClassVar[HAlign] = AlignLeft()
    va: ClassVar[VAlign] = AlignTop()


@dataclass(frozen=True)
class UpperRight:
    """An Axes' upper right corner."""

    anchor: ClassVar[tuple[float, float]] = (1.0, 1.0)
    inward: ClassVar[tuple[float, float]] = (-1.0, -1.0)
    ha: ClassVar[HAlign] = AlignRight()
    va: ClassVar[VAlign] = AlignTop()


@dataclass(frozen=True)
class LowerLeft:
    """An Axes' lower left corner."""

    anchor: ClassVar[tuple[float, float]] = (0.0, 0.0)
    inward: ClassVar[tuple[float, float]] = (1.0, 1.0)
    ha: ClassVar[HAlign] = AlignLeft()
    va: ClassVar[VAlign] = AlignBottom()


@dataclass(frozen=True)
class LowerRight:
    """An Axes' lower right corner."""

    anchor: ClassVar[tuple[float, float]] = (1.0, 0.0)
    inward: ClassVar[tuple[float, float]] = (-1.0, 1.0)
    ha: ClassVar[HAlign] = AlignRight()
    va: ClassVar[VAlign] = AlignBottom()


Corner: TypeAlias = UpperLeft | UpperRight | LowerLeft | LowerRight


CORNERS: tuple[Corner, ...] = (
    UpperLeft(),
    UpperRight(),
    LowerLeft(),
    LowerRight(),
)


def corner_order(first: Corner) -> tuple[Corner, ...]:
    """``first``, then the other corners in :data:`CORNERS` order."""
    return (first, *(c for c in CORNERS if c != first))


LineSide: TypeAlias = Above | Below
"""``label_hline``'s side of the line."""


@dataclass(frozen=True)
class LeftEnd:
    """The drawn line's left end; the label starts there."""

    ha: ClassVar[HAlign] = AlignLeft()

    def shown(self, left: float, right: float, frame: Span) -> float:
        """The display x of this place on a line drawn over ``[left, right]``."""
        return left

    @property
    def tries(self) -> tuple[LinePlace, ...]:
        """The one place asked."""
        return (self,)


@dataclass(frozen=True)
class LineMiddle:
    """The middle of the drawn line."""

    ha: ClassVar[HAlign] = AlignCentre()

    def shown(self, left: float, right: float, frame: Span) -> float:
        """The display x of this place on a line drawn over ``[left, right]``."""
        return (left + right) / 2

    @property
    def tries(self) -> tuple[LinePlace, ...]:
        """The one place asked."""
        return (self,)


@dataclass(frozen=True)
class RightEnd:
    """The drawn line's right end; the label ends there."""

    ha: ClassVar[HAlign] = AlignRight()

    def shown(self, left: float, right: float, frame: Span) -> float:
        """The display x of this place on a line drawn over ``[left, right]``."""
        return right

    @property
    def tries(self) -> tuple[LinePlace, ...]:
        """The one place asked."""
        return (self,)


@dataclass(frozen=True)
class AtFraction:
    """A fraction of the Axes' width, the label centred on it."""

    fraction: float
    ha: ClassVar[HAlign] = AlignCentre()

    def shown(self, left: float, right: float, frame: Span) -> float:
        """The display x of this place in the Axes ``frame``."""
        return frame.low + frame.length * self.fraction

    @property
    def tries(self) -> tuple[LinePlace, ...]:
        """The one place asked."""
        return (self,)


LinePlace: TypeAlias = LeftEnd | LineMiddle | RightEnd | AtFraction


LINE_ENDS: tuple[LinePlace, ...] = (RightEnd(), LeftEnd())


@dataclass(frozen=True)
class EitherEnd:
    """``x="auto"``: the clearer end of the drawn line, the right first."""

    @property
    def tries(self) -> tuple[LinePlace, ...]:
        """Both ends, in the order tried."""
        return LINE_ENDS


LineX: TypeAlias = LinePlace | EitherEnd


@dataclass(frozen=True)
class FromPanel:
    """``label_axes(x="auto")``: each letter placed from what its panel draws."""


@dataclass(frozen=True)
class AtLeft:
    """``label_axes(x=0.02)``: every letter's left edge at an Axes fraction."""

    x: float


LetterX: TypeAlias = FromPanel | AtLeft


# ------------------------------------------------------------ point labels
@dataclass(frozen=True)
class Try:
    """A candidate place, measured: how much of the label leaves the axes
    and how much it covers data or text (square pixels)."""

    outside: float
    collision: float

    @property
    def clear(self) -> bool:
        """Inside the axes and covering nothing."""
        return self.outside <= 0 and self.collision <= 0


@dataclass(frozen=True)
class Tries:
    """The candidates in the order the helper tries them."""

    tries: tuple[Try, ...]

    def pick(self, candidates: Sequence[int], *, inside_first: bool) -> int:
        """The first clear candidate; else (``inside_first``) the least
        covered one inside the axes; else the least outside and covered."""
        tries = self.tries
        first = next((i for i in candidates if tries[i].clear), None)
        if first is not None:
            return first
        inside = [i for i in candidates if tries[i].outside <= 0]
        if inside_first and inside:
            return min(inside, key=lambda i: tries[i].collision)
        return min(
            candidates, key=lambda i: tries[i].outside + tries[i].collision
        )


@dataclass(frozen=True)
class Choice:
    """The index of the candidate taken."""

    index: int
