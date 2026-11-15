"""The legend slice's types, and the one place a caller's ``loc`` becomes one.

Geometry is in display pixels of the figure being placed: a :class:`Box` is a
window extent, a :class:`Size` a legend's width and height. What only the
figure can answer (how big a legend of these entries is, whether a box meets
data ink, where a name breaks) reaches the decisions as a measuring function
in the facts, so ``decide`` and ``edges`` stay free of matplotlib.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum

#: Room kept between a legend box and the nearest data ink, in points.
CLEARANCE_PT = 2.0
#: A one-column legend taller than this share of the Axes is tried last.
TALL_SHARE = 0.55


class Loc(Enum):
    """An inside spot, in the order it is tried; the value is matplotlib's."""

    UPPER_RIGHT = "upper right"
    UPPER_LEFT = "upper left"
    LOWER_LEFT = "lower left"
    LOWER_RIGHT = "lower right"
    UPPER_CENTER = "upper center"
    LOWER_CENTER = "lower center"
    CENTER_RIGHT = "center right"
    CENTER_LEFT = "center left"

    @property
    def anchor(self) -> tuple[float, float]:
        """Where the spot sits in its container, as fractions (x, y)."""
        words = self.value.split()
        x = {"left": 0.0, "right": 1.0}.get(words[-1], 0.5)
        y = {"upper": 1.0, "lower": 0.0}.get(words[0], 0.5)
        return x, y


class Side(Enum):
    """A side of an Axes or figure a legend sits outside of."""

    ABOVE = "above"
    BELOW = "below"
    RIGHT = "right"
    LEFT = "left"

    @property
    def across(self) -> bool:
        """Above and below a legend lies across the width."""
        return self in (Side.ABOVE, Side.BELOW)

    @property
    def legend_loc(self) -> str:
        """The legend's own edge that faces the Axes (matplotlib ``loc``)."""
        return {
            "above": "lower center",
            "below": "upper center",
            "right": "center left",
            "left": "center right",
        }[self.value]

    @property
    def figure_loc(self) -> str:
        """A figure legend's edge that faces the figure's edge."""
        return {
            "above": "upper center",
            "below": "lower center",
            "right": "center right",
            "left": "center left",
        }[self.value]


#: Where a legend may go when no inside spot is free, in order.
FALLBACK_SIDES = (Side.ABOVE, Side.BELOW, Side.RIGHT)


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
        cx, cy = (ext.x0 + ext.x1) / 2, (ext.y0 + ext.y1) / 2
        if side is Side.ABOVE and cy > self.y1 + 0.5:
            return ext.y1 - self.y1
        if side is Side.BELOW and cy < self.y0 - 0.5:
            return self.y0 - ext.y0
        if side is Side.RIGHT and cx > self.x1 + 0.5:
            return ext.x1 - self.x1
        if side is Side.LEFT and cx < self.x0 - 0.5:
            return self.x0 - ext.x0
        return 0.0

    def beyond(self, side: Side, ext: Box) -> float:
        """How far ``ext`` reaches past ``side``, wherever its centre is."""
        return {
            Side.ABOVE: ext.y1 - self.y1,
            Side.BELOW: self.y0 - ext.y0,
            Side.RIGHT: ext.x1 - self.x1,
            Side.LEFT: self.x0 - ext.x0,
        }[side]


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
class Columns:
    """A legend's column count, at least one."""

    n: int

    def __post_init__(self) -> None:
        """Reject fewer than one column."""
        if self.n < 1:
            raise ValueError(f"a legend has at least one column (got {self.n})")


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


@dataclass(frozen=True)
class Request:
    """What the caller asked ``place_legend`` for.

    ``side`` is ``None`` for ``loc="best"``; ``columns`` an explicit
    ``ncol`` / ``ncols``; ``anchored`` a caller ``bbox_to_anchor`` /
    ``bbox_transform``, which keeps a ``best`` legend inside.
    """

    side: Side | None
    columns: Columns | None = None
    anchored: bool = False


def parse_side(loc: str) -> Side | None:
    """``loc`` as an outside side, or ``None`` for any other ``loc``."""
    try:
        return Side(loc)
    except ValueError:
        return None


def split_columns(
    kw: Mapping[str, object],
) -> tuple[dict[str, object], Columns | None]:
    """Legend keywords without ``ncol`` / ``ncols``, and the count they asked for."""
    rest = dict(kw)
    asked = rest.pop("ncols", None)
    asked = rest.pop("ncol", asked)
    if asked is None:
        return rest, None
    if isinstance(asked, bool) or not isinstance(asked, int):
        raise TypeError(f"ncols must be an int (got {type(asked).__name__})")
    return rest, Columns(asked)


# ------------------------------------------------------------------- plans
@dataclass(frozen=True)
class Inside:
    """The legend at an inside spot; ``free`` when it meets no ink."""

    loc: Loc
    columns: Columns
    free: bool = True


@dataclass(frozen=True)
class Outside:
    """The legend outside ``side`` with ``entries`` (names maybe broken)."""

    side: Side
    columns: Columns
    entries: Entries
    size: Size
    fits: bool


LegendPlan = Inside | Outside


@dataclass(frozen=True)
class Anchor:
    """How far an outside legend sits past its side, px."""

    clearance: float


@dataclass(frozen=True)
class TitlePad:
    """The pad the Axes titles get, px; ``None`` keeps theirs."""

    px: float | None = None


@dataclass(frozen=True)
class FigurePlan:
    """A figure legend's side, columns and anchor (fraction of its figure)."""

    side: Side
    columns: Columns
    anchor: tuple[float, float]


@dataclass(frozen=True)
class EntryPlan:
    """Which Axes holds the legend and which entries it shows.

    ``picks`` are (owner, entry) indices into the facts' owners; ``remove``
    the owners whose own legends go.
    """

    host: int
    picks: tuple[tuple[int, int], ...]
    remove: tuple[int, ...] = ()


# ------------------------------------------------------------------- facts
@dataclass(frozen=True)
class LegendFacts:
    """Everything one legend placement reads from the figure.

    ``size_of`` builds a trial legend (nothing drawn); ``meets`` counts the
    artists whose data ink comes within the clearance of a box; ``span_of``
    is where a legend outside a side may lie. ``current`` is the plan the
    legend has, when the layout places it again.
    """

    request: Request
    entries: Entries
    axes: Box
    parent: Box
    pad: float
    free_sides: tuple[Side, ...]
    size_of: Callable[[Entries, Columns], Size]
    meets: Callable[[Box], Hits]
    span_of: Callable[[Side], Span]
    current: LegendPlan | None = None


@dataclass(frozen=True)
class AnchorFacts:
    """An outside legend against its side: decorations of the Axes and twins."""

    side: Side
    axes: Box
    decorations: tuple[Box, ...]


@dataclass(frozen=True)
class TitleBox:
    """A drawn Axes title: its box, the Axes top it is offset from, its pad."""

    box: Box
    base_y: float
    pad: float


@dataclass(frozen=True)
class TitleFacts:
    """The titles of an Axes and the legends that sit above it."""

    titles: tuple[TitleBox, ...]
    legends_above: tuple[Box, ...]
    gap: float


@dataclass(frozen=True)
class FigureFacts:
    """A figure legend: its entries and the figure."""

    side: Side | None
    columns: Columns | None
    entries: Entries
    figure: Box
    pad: float
    size_of: Callable[[Entries, Columns], Size]


@dataclass(frozen=True)
class Owner:
    """One Axes drawn in the legend's box (the Axes itself or a twin).

    ``rank`` is the draw order (zorder, figure index); ``legend`` the texts
    of its current legend.
    """

    entries: Entries
    rank: tuple[float, int]
    legend: Entries | None = None


@dataclass(frozen=True)
class EntryFacts:
    """The Axes ``place_legend`` was called on (``focus``) and its twins."""

    owners: tuple[Owner, ...]
    focus: int = 0


Facts = LegendFacts | AnchorFacts | TitleFacts | FigureFacts | EntryFacts
Plan = LegendPlan | Anchor | TitlePad | FigurePlan | EntryPlan
