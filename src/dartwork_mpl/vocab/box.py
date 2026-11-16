"""A rectangle and an extent in display pixels, as every slice measures them."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    """A display-px rectangle: left, bottom, right, top."""

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

    @property
    def area(self) -> float:
        """Width times height, never negative."""
        return max(self.width, 0.0) * max(self.height, 0.0)

    def padded(self, pad: float) -> Box:
        """This box grown by ``pad`` on every side."""
        return Box(self.x0 - pad, self.y0 - pad, self.x1 + pad, self.y1 + pad)

    def overlap(self, other: Box) -> Box:
        """The intersection (empty boxes have no area)."""
        return Box(
            max(self.x0, other.x0),
            max(self.y0, other.y0),
            min(self.x1, other.x1),
            min(self.y1, other.y1),
        )

    def overlaps(self, other: Box) -> bool:
        """Whether the boxes share some area."""
        return self.gap(other) < 0

    def gap(self, other: Box) -> float:
        """How far apart the boxes are (negative: by how much they overlap)."""
        dx = max(self.x0, other.x0) - min(self.x1, other.x1)
        dy = max(self.y0, other.y0) - min(self.y1, other.y1)
        return max(dx, dy)

    def cover(self, other: Box) -> float:
        """The shared area as a share of the smaller box's area."""
        inter = self.overlap(other)
        if inter.width <= 0 or inter.height <= 0:
            return 0.0
        return inter.area / max(min(self.area, other.area), 1e-9)

    def outside_share(self, outer: Box) -> float:
        """The share of this box's area that lies outside ``outer``."""
        inside = self.overlap(outer)
        shared = max(inside.width, 0.0) * max(inside.height, 0.0)
        area = max(self.width * self.height, 1.0)
        return (self.width * self.height - shared) / area


@dataclass(frozen=True)
class Span:
    """A ``[low, high]`` extent along one display axis, pixels."""

    low: float
    high: float

    @property
    def length(self) -> float:
        """``high - low``."""
        return self.high - self.low
