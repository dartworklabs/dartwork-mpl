"""The legend slice's types, and the one place a caller's ``loc`` becomes one.

Geometry is in display pixels of the figure being placed: a ``Box`` is a
window extent, a :class:`Size` a legend's width and height.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import ClassVar, Literal

from ..vocab import Box

#: Room kept between a legend box and the nearest data ink, in points.
CLEARANCE_PT = 2.0

LocName = Literal[
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "upper center",
    "lower center",
    "center right",
    "center left",
]
"""A ``loc`` matplotlib names, for the spots this slice puts a legend at."""


@dataclass(frozen=True)
class Spot:
    """A legend's ``loc`` and where it sits in its box, as fractions."""

    code: LocName
    anchor: tuple[float, float]


#: The inside spots, in the order they are tried.
INSIDE: tuple[Spot, ...] = (
    Spot("upper right", (1.0, 1.0)),
    Spot("upper left", (0.0, 1.0)),
    Spot("lower left", (0.0, 0.0)),
    Spot("lower right", (1.0, 0.0)),
    Spot("upper center", (0.5, 1.0)),
    Spot("lower center", (0.5, 0.0)),
    Spot("center right", (1.0, 0.5)),
    Spot("center left", (0.0, 0.5)),
)
UPPER_CENTER, LOWER_CENTER, CENTER_RIGHT, CENTER_LEFT = INSIDE[4:]


@dataclass(frozen=True)
class Above:
    """Above the container. ``loc="above"``."""

    across: ClassVar[bool] = True
    far: ClassVar[bool] = True
    legend_loc: ClassVar[Spot] = LOWER_CENTER
    figure_loc: ClassVar[Spot] = UPPER_CENTER


@dataclass(frozen=True)
class Below:
    """Below the container. ``loc="below"``."""

    across: ClassVar[bool] = True
    far: ClassVar[bool] = False
    legend_loc: ClassVar[Spot] = UPPER_CENTER
    figure_loc: ClassVar[Spot] = LOWER_CENTER


@dataclass(frozen=True)
class Right:
    """Right of the container. ``loc="right"``."""

    across: ClassVar[bool] = False
    far: ClassVar[bool] = True
    legend_loc: ClassVar[Spot] = CENTER_LEFT
    figure_loc: ClassVar[Spot] = CENTER_RIGHT


@dataclass(frozen=True)
class Left:
    """Left of the container. ``loc="left"``."""

    across: ClassVar[bool] = False
    far: ClassVar[bool] = False
    legend_loc: ClassVar[Spot] = CENTER_RIGHT
    figure_loc: ClassVar[Spot] = CENTER_LEFT


#: A side an Axes or figure legend sits outside of. ``across``: the legend
#: lies across the width (above, below); ``far``: the high end of its axis
#: (above, right). ``legend_loc`` is the legend's edge facing its Axes,
#: ``figure_loc`` a figure legend's edge facing the figure's edge, which is
#: also the middle of that side.
Side = Above | Below | Right | Left


@dataclass(frozen=True)
class Best:
    """``loc="best"``: the first inside spot clear of the data."""


AskedLoc = Literal["best", "above", "below", "right", "left"]


#: The words a caller names a placement with.
WORDS: dict[str, Best | Side] = {
    "best": Best(),
    "above": Above(),
    "below": Below(),
    "right": Right(),
    "left": Left(),
}


def parse_loc(loc: str) -> Best | Side:
    """``loc`` as the best inside spot or an outside side."""
    found = WORDS.get(loc)
    if found is None:
        raise ValueError(
            "loc must be 'best', 'above', 'below', 'right' or 'left' "
            f"(got {loc!r}); for a fixed spot use ax.legend(loc=...)"
        )
    return found


@dataclass(frozen=True)
class Columns:
    """A legend's column count, at least one."""

    n: int

    def __post_init__(self) -> None:
        """Reject fewer than one column."""
        if self.n < 1:
            raise ValueError(f"a legend has at least one column (got {self.n})")


def parse_columns(ncols: int | None, ncol: int | None) -> Columns | None:
    """An explicit ``ncols`` (``ncol`` wins, as in matplotlib), or ``None``."""
    asked = ncols if ncol is None else ncol
    return None if asked is None else Columns(asked)


def refuse_anchor(side: Best | Side, kw: Mapping[str, object]) -> None:
    """A side anchors the legend itself: a caller anchor is an error."""
    if not isinstance(side, Best) and "bbox_to_anchor" in kw:
        raise ValueError(
            "a legend on a named side anchors itself; remove bbox_to_anchor= "
            "or use ax.legend"
        )


@dataclass(frozen=True)
class Size:
    """A legend's width and height, display px."""

    width: float
    height: float

    def placed(self, spot: Spot, parent: Box, pad: float) -> Box:
        """Where matplotlib draws a legend of this size at ``spot``."""
        inner = parent.padded(-pad)
        fx, fy = spot.anchor
        x0 = inner.x0 + fx * (inner.width - self.width)
        y0 = inner.y0 + fy * (inner.height - self.height)
        return Box(x0, y0, x0 + self.width, y0 + self.height)

    def along(self, side: Side) -> float:
        """The legend's length along ``side``."""
        return self.width if side.across else self.height


@dataclass(frozen=True)
class Hits:
    """How many artists' ink a box meets."""

    n: int


@dataclass(frozen=True)
class InsideFacts:
    """A legend of ``size`` in ``parent`` (its anchor box) over ``axes``."""

    size: Size
    parent: Box
    axes: Box
    pad: float
    meets: Callable[[Box], Hits]


@dataclass(frozen=True)
class SideFacts:
    """A legend outside ``side``: how many entries, how long the side is."""

    side: Side
    count: int
    length: float
    asked: Columns | None
    size_of: Callable[[Columns], Size]


@dataclass(frozen=True)
class Clearance:
    """How far an outside legend sits past its side, px."""

    px: float


@dataclass(frozen=True)
class TitleFacts:
    """An Axes' titles: where they sit unpadded, their pad, the gap they keep."""

    base: float
    pad: float
    gap: float
