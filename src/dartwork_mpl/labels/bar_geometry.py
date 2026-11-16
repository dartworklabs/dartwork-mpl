"""A bar label's kind and geometry: where it sits on its bar, the way its bar
grows, spans along an axis, crowding and headroom, as the layout measures
them in pixels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar, TypeAlias

import numpy as np

from ..vocab import (
    AlignBottom,
    AlignLeft,
    AlignRight,
    AlignTop,
    HAlign,
    Span,
    VAlign,
)


# ------------------------------------------------------------ label kinds
@dataclass(frozen=True)
class BeyondEnd:
    """A plain bar's value, or a stack's net on the bar ending the stack:
    beyond the bar's end, in the room the value axis gives."""

    centred: ClassVar[bool] = False


@dataclass(frozen=True)
class Segment:
    """One bar of a stack: at the bar's middle, shown while the bar holds it."""

    centred: ClassVar[bool] = True


Kind: TypeAlias = BeyondEnd | Segment
"""What a bar label labels."""


@dataclass(frozen=True)
class Higher:
    """Towards higher display coordinates (up, right): text beyond an
    anchor there stands on it or starts at it."""

    sign: ClassVar[float] = 1.0
    ha: ClassVar[HAlign] = AlignLeft()
    va: ClassVar[VAlign] = AlignBottom()

    def reach(self, low: float, high: float) -> float:
        """The end of ``[low, high]`` this way."""
        return high


@dataclass(frozen=True)
class Lower:
    """Towards lower display coordinates (down, left)."""

    sign: ClassVar[float] = -1.0
    ha: ClassVar[HAlign] = AlignRight()
    va: ClassVar[VAlign] = AlignTop()

    def reach(self, low: float, high: float) -> float:
        """The end of ``[low, high]`` this way."""
        return low


Toward: TypeAlias = Higher | Lower
"""The way a bar grows on screen, and so the way its end label points."""


# ------------------------------------------------------------ bar geometry
@dataclass(frozen=True)
class Pixels:
    """A display length in pixels."""

    px: float


@dataclass(frozen=True)
class Spot:
    """One drawn bar label: its bar's middle across the bars, and its own
    extent there (pixels)."""

    centre: float
    span: Span


@dataclass(frozen=True)
class Position:
    """The drawn labels at one bar position: middle, union of extents,
    widest label, and which spots."""

    centre: float
    span: Span
    widest: float
    members: tuple[int, ...]


# Two bar middles closer than this (display pixels) are one position.
SAME_PX = 0.5


@dataclass(frozen=True)
class CrowdFacts:
    """One call's drawn labels, every bar middle of the plot area, the gap."""

    spots: tuple[Spot, ...]
    bar_centres: tuple[float, ...]
    gap: Pixels

    def positions(self) -> tuple[Position, ...]:
        """The spots grouped by bar position, in screen order."""
        order = sorted(
            range(len(self.spots)), key=lambda i: self.spots[i].centre
        )
        out: list[Position] = []
        for i in order:
            spot = self.spots[i]
            if out and spot.centre - out[-1].centre <= SAME_PX:
                last = out[-1]
                out[-1] = Position(
                    last.centre,
                    Span(
                        min(last.span.low, spot.span.low),
                        max(last.span.high, spot.span.high),
                    ),
                    max(last.widest, spot.span.length),
                    (*last.members, i),
                )
            else:
                out.append(
                    Position(spot.centre, spot.span, spot.span.length, (i,))
                )
        return tuple(out)

    def pitch(self, centre: float) -> float:
        """The distance from ``centre`` to the nearest other bar middle."""
        away = np.abs(np.asarray(self.bar_centres, dtype=float) - centre)
        away = away[away > SAME_PX]  # NaN bars drop out too
        return float(away.min()) if away.size else math.inf


@dataclass(frozen=True)
class Shown:
    """Which of the spots handed in stay drawn, in the order given."""

    flags: tuple[bool, ...]


@dataclass(frozen=True)
class Room:
    """A label beyond its bar end: anchor, room it needs to the axes edge it
    points to (pixels), and which way that edge is."""

    anchor: float
    need: float
    toward: Toward


@dataclass(frozen=True)
class HeadroomFacts:
    """An autoscaled value axis on screen and the labels that need room."""

    view: Span
    rooms: tuple[Room, ...]


@dataclass(frozen=True)
class Headroom:
    """The view widened so every label fits, or ``None``: it already does."""

    view: Span | None
