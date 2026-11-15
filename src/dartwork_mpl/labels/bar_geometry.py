"""A bar label's geometry: spans along an axis, label positions, crowding and
headroom, as the layout measures them in pixels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .bar_options import Toward


# ------------------------------------------------------------ bar geometry
@dataclass(frozen=True)
class Span:
    """A ``[low, high]`` extent along one display axis, pixels."""

    low: float
    high: float

    @property
    def width(self) -> float:
        """``high - low``."""
        return self.high - self.low


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
                    max(last.widest, spot.span.width),
                    (*last.members, i),
                )
            else:
                out.append(
                    Position(spot.centre, spot.span, spot.span.width, (i,))
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
