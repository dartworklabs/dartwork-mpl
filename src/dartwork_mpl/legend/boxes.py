"""A legend's geometry in display pixels of the figure being placed.

A :class:`Box` is a window extent, a :class:`Size` a legend's width and
height, a :class:`Span` a stretch along one axis; :class:`Entries` and
:class:`Width` say what a legend holds and how wide its names draw, and
:class:`Hits` how much data ink a box meets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .sides import Loc, Side


@dataclass(frozen=True)
class Box:
    """A display-px rectangle."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        """The box's width."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """The box's height."""
        return self.y1 - self.y0

    def along(self, side: Side) -> tuple[float, float]:
        """The box's extent along ``side`` (x across, y right and left)."""
        return (self.x0, self.x1) if side.across else (self.y0, self.y1)

    def normal(self, side: Side) -> tuple[float, float]:
        """The box's extent towards ``side`` (y above and below, x beside)."""
        return (self.y0, self.y1) if side.across else (self.x0, self.x1)

    def padded(self, pad: float) -> Box:
        """This box grown by ``pad`` on every side."""
        return Box(self.x0 - pad, self.y0 - pad, self.x1 + pad, self.y1 + pad)

    def overlaps(self, other: Box) -> bool:
        """Whether the boxes share some area."""
        return min(self.x1, other.x1) > max(self.x0, other.x0) and min(
            self.y1, other.y1
        ) > max(self.y0, other.y0)

    def outside_share(self, outer: Box) -> float:
        """The share of this box's area that lies outside ``outer``."""
        w = max(min(self.x1, outer.x1) - max(self.x0, outer.x0), 0.0)
        h = max(min(self.y1, outer.y1) - max(self.y0, outer.y0), 0.0)
        area = max(self.width * self.height, 1.0)
        return (self.width * self.height - w * h) / area

    def reach_past(self, side: Side, ext: Box) -> float:
        """How far ``ext`` reaches past ``side`` (0 when its centre is not beyond)."""
        low, high = self.normal(side)
        e0, e1 = ext.normal(side)
        centre = (e0 + e1) / 2
        past = centre > high + 0.5 if side.far else centre < low - 0.5
        return self.beyond(side, ext) if past else 0.0

    def beyond(self, side: Side, ext: Box) -> float:
        """How far ``ext`` reaches past ``side``, wherever its centre is."""
        low, high = self.normal(side)
        e0, e1 = ext.normal(side)
        return e1 - high if side.far else low - e0

    def behind(self, side: Side, other: Box, eps: float) -> bool:
        """Whether ``other`` sits beyond ``side`` of this box, facing it."""
        low, high = self.normal(side)
        o0, o1 = other.normal(side)
        a0, a1 = self.along(side)
        b0, b1 = other.along(side)
        facing = min(a1, b1) - max(a0, b0) > eps
        beyond = o0 >= high - eps if side.far else o1 <= low + eps
        return facing and beyond


@dataclass(frozen=True)
class Size:
    """A legend's width and height, display px."""

    width: float
    height: float

    def placed(self, loc: Loc, parent: Box, pad: float) -> Box:
        """Where matplotlib draws a legend of this size at ``loc`` in ``parent``."""
        inner = parent.padded(-pad)
        fx, fy = loc.anchor
        x0 = inner.x0 + fx * (inner.width - self.width)
        y0 = inner.y0 + fy * (inner.height - self.height)
        return Box(x0, y0, x0 + self.width, y0 + self.height)

    def along(self, side: Side) -> float:
        """The legend's length along ``side``."""
        return self.width if side.across else self.height

    @property
    def finite(self) -> bool:
        """Both sides finite (a trial legend that measured)."""
        return math.isfinite(self.width) and math.isfinite(self.height)


@dataclass(frozen=True)
class Span:
    """Where a legend outside a side may lie along it, display px."""

    low: float
    high: float

    @property
    def length(self) -> float:
        """The span's length."""
        return self.high - self.low


@dataclass(frozen=True)
class Entries:
    """The entry names of a legend, in order."""

    labels: tuple[str, ...]

    @property
    def count(self) -> int:
        """How many entries."""
        return len(self.labels)


@dataclass(frozen=True)
class Width:
    """A width in display px a name is broken to."""

    px: float


@dataclass(frozen=True)
class Hits:
    """How many artists' ink a box meets."""

    n: int
