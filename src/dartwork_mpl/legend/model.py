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
from typing import Any, ClassVar

#: Room kept between a legend box and the nearest data ink, in points.
CLEARANCE_PT = 2.0
#: A one-column legend taller than this share of the Axes is tried last.
TALL_SHARE = 0.55


@dataclass(frozen=True)
class Loc:
    """An inside spot: matplotlib's ``loc`` for it and where it sits.

    ``x`` and ``y`` place the spot in its container, as fractions. The
    spots, in the order they are tried, are :data:`INSIDE_SPOTS`.
    """

    code: str
    x: float
    y: float

    UPPER_RIGHT: ClassVar[Loc]
    UPPER_LEFT: ClassVar[Loc]
    LOWER_LEFT: ClassVar[Loc]
    LOWER_RIGHT: ClassVar[Loc]
    UPPER_CENTER: ClassVar[Loc]
    LOWER_CENTER: ClassVar[Loc]
    CENTER_RIGHT: ClassVar[Loc]
    CENTER_LEFT: ClassVar[Loc]

    @property
    def anchor(self) -> tuple[float, float]:
        """Where the spot sits in its container, as fractions (x, y)."""
        return self.x, self.y


Loc.UPPER_RIGHT = Loc("upper right", 1.0, 1.0)
Loc.UPPER_LEFT = Loc("upper left", 0.0, 1.0)
Loc.LOWER_LEFT = Loc("lower left", 0.0, 0.0)
Loc.LOWER_RIGHT = Loc("lower right", 1.0, 0.0)
Loc.UPPER_CENTER = Loc("upper center", 0.5, 1.0)
Loc.LOWER_CENTER = Loc("lower center", 0.5, 0.0)
Loc.CENTER_RIGHT = Loc("center right", 1.0, 0.5)
Loc.CENTER_LEFT = Loc("center left", 0.0, 0.5)

#: Every inside spot, in the order it is tried.
INSIDE_SPOTS = (
    Loc.UPPER_RIGHT,
    Loc.UPPER_LEFT,
    Loc.LOWER_LEFT,
    Loc.LOWER_RIGHT,
    Loc.UPPER_CENTER,
    Loc.LOWER_CENTER,
    Loc.CENTER_RIGHT,
    Loc.CENTER_LEFT,
)


@dataclass(frozen=True)
class Side:
    """A side of an Axes or figure a legend sits outside of.

    ``word`` is how a caller names it (``loc="above"``); ``across``: the
    legend lies across the width (above, below); ``far``: the side is the
    high end of its axis (above, right). ``legend_loc`` is the legend's own
    edge that faces the Axes, ``figure_loc`` a figure legend's edge that
    faces the figure's edge; that spot is also the middle of the side.
    """

    word: str
    across: bool
    far: bool
    legend_loc: Loc
    figure_loc: Loc

    ABOVE: ClassVar[Side]
    BELOW: ClassVar[Side]
    RIGHT: ClassVar[Side]
    LEFT: ClassVar[Side]

    @property
    def middle(self) -> tuple[float, float]:
        """The middle of the side, as fractions of its container."""
        return self.figure_loc.anchor

    @property
    def outward(self) -> tuple[float, float]:
        """The unit step away from the container, past the side."""
        step = 1.0 if self.far else -1.0
        return (0.0, step) if self.across else (step, 0.0)


Side.ABOVE = Side("above", True, True, Loc.LOWER_CENTER, Loc.UPPER_CENTER)
Side.BELOW = Side("below", True, False, Loc.UPPER_CENTER, Loc.LOWER_CENTER)
Side.RIGHT = Side("right", False, True, Loc.CENTER_LEFT, Loc.CENTER_RIGHT)
Side.LEFT = Side("left", False, False, Loc.CENTER_RIGHT, Loc.CENTER_LEFT)

SIDES = (Side.ABOVE, Side.BELOW, Side.RIGHT, Side.LEFT)

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


@dataclass(frozen=True)
class Best:
    """``loc="best"``: inside where it covers no data, else outside."""


@dataclass(frozen=True)
class Passed:
    """Any other ``loc``: matplotlib's, handed to it unchanged."""

    loc: str


Placement = Best | Side | Passed
"""What a caller's ``loc`` asks for."""


def parse_loc(loc: str) -> Placement:
    """``loc`` as the best spot, an outside side, or matplotlib's own."""
    if loc == "best":
        return Best()
    return next((s for s in SIDES if s.word == loc), Passed(loc))


#: The caller keywords that anchor a legend themselves.
CALLER_ANCHOR = ("bbox_to_anchor", "bbox_transform")


@dataclass(frozen=True)
class Keywords:
    """The caller's legend keywords, read once.

    ``rest`` goes to matplotlib; ``columns`` is an explicit ``ncol`` /
    ``ncols``; ``anchor`` the first caller keyword that anchors the legend
    (``bbox_to_anchor``, ``bbox_transform``), if any.
    """

    rest: dict[str, Any]
    columns: Columns | None
    anchor: str | None

    @property
    def anchored(self) -> bool:
        """The caller anchored the legend."""
        return self.anchor is not None


def parse_keywords(
    kw: Mapping[str, object], kept: Mapping[str, object] | None = None
) -> Keywords:
    """The caller's keywords over the ``kept`` settings of a rebuilt legend.

    A caller ``fontsize`` or ``prop`` replaces the kept font size.
    """
    base = dict(kept or {})
    if "fontsize" in kw or "prop" in kw:
        base.pop("fontsize", None)
    rest, columns = split_columns({**base, **kw})
    anchor = next((k for k in CALLER_ANCHOR if k in rest), None)
    return Keywords(rest, columns, anchor)


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


def trial_keywords(kw: Mapping[str, Any]) -> dict[str, Any]:
    """The keywords a trial legend is built with: not ``draggable``."""
    return {k: v for k, v in kw.items() if k != "draggable"}


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
    """A figure legend's side and columns; it sits at the side's middle."""

    side: Side
    columns: Columns

    @property
    def anchor(self) -> tuple[float, float]:
        """Where its ``loc`` edge sits on the figure, as fractions."""
        return self.side.middle


@dataclass(frozen=True)
class Reserve:
    """The figure edge a figure legend holds and the room it keeps, pt."""

    side: Side
    gap_pt: float


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
