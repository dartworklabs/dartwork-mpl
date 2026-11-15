"""A legend's geometry in display pixels of the figure being placed.

A :class:`Box` is a window extent, a :class:`Size` a legend's width and
height, a :class:`Span` a stretch along one axis; :class:`Entries` and
:class:`Width` say what a legend holds and how wide its names draw, and
:class:`Hits` how much data ink a box meets.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..vocab import Box
from .sides import Loc, Side


def along(box: Box, side: Side) -> tuple[float, float]:
    """The box's extent along ``side`` (x across, y right and left)."""
    return (box.x0, box.x1) if side.across else (box.y0, box.y1)


def normal(box: Box, side: Side) -> tuple[float, float]:
    """The box's extent towards ``side`` (y above and below, x beside)."""
    return (box.y0, box.y1) if side.across else (box.x0, box.x1)


def reach_past(box: Box, side: Side, ext: Box) -> float:
    """How far ``ext`` reaches past ``side`` of ``box`` (0 when its centre is
    not beyond)."""
    low, high = normal(box, side)
    e0, e1 = normal(ext, side)
    centre = (e0 + e1) / 2
    past = centre > high + 0.5 if side.far else centre < low - 0.5
    return beyond(box, side, ext) if past else 0.0


def beyond(box: Box, side: Side, ext: Box) -> float:
    """How far ``ext`` reaches past ``side`` of ``box``, wherever its centre is."""
    low, high = normal(box, side)
    e0, e1 = normal(ext, side)
    return e1 - high if side.far else low - e0


def behind(box: Box, side: Side, other: Box, eps: float) -> bool:
    """Whether ``other`` sits beyond ``side`` of ``box``, facing it."""
    low, high = normal(box, side)
    o0, o1 = normal(other, side)
    a0, a1 = along(box, side)
    b0, b1 = along(other, side)
    facing = min(a1, b1) - max(a0, b0) > eps
    past = o0 >= high - eps if side.far else o1 <= low + eps
    return facing and past


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
