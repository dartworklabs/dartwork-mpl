"""The layout's types, and the one place ``simple_layout``'s margins are parsed.

Two kinds of number cross this slice. A :data:`Px` is a display pixel, as
matplotlib measures a drawn artist; a :class:`Sides` / :class:`Edges` value is
a share of the figure's width (left, right) or height (bottom, top), as a
GridSpec takes it. Every measured fact arrives as one of the types below; the
decisions never see a matplotlib object.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import NewType, TypeAlias

from ..size import Length

Px = NewType("Px", float)
Degrees = NewType("Degrees", float)
Line = NewType("Line", str)
"""Text as one tick label or axis name writes it (may hold line breaks)."""
Count = NewType("Count", int)
Share = NewType("Share", float)
"""A GridSpec ``wspace`` / ``hspace``: a gap as a share of the mean cell."""
ArtistId = NewType("ArtistId", int)
"""``id()`` of the axis, label or grid a planned change is for."""

# Least slack between opposite grid edges (figure fraction): the grid stays
# a valid rectangle when the margins ask for the whole figure.
EDGE_EPSILON = 1e-3
# The fit has converged when no grid edge moved this far (display px).
CONVERGE_PX = 0.5
MAX_STEPS = 10
# Text overlapping by up to this (display px) only touches.
TOUCH_PX = 0.5
# Room a fitted label keeps from its neighbours, in ems of its own size.
CLEARANCE_EM = 0.5
ANGLES = (Degrees(30.0), Degrees(45.0), Degrees(90.0))
MAX_TICK_LINES = 3
MAX_NAME_LINES = 4
# Largest wspace / hspace the panel spacing grows to (share of a cell).
MAX_GAP_FRACTION = 1.5
# Least share of its width and height a plot keeps when text is fitted.
MIN_PLOT_SHARE = 0.3
FIT_ROUNDS = 3
# Figure text centred in this outer band of the canvas reserves that edge.
EDGE_BAND = 0.15
EDGE_BAND_TOL = 1e-9


class Which(Enum):
    """An Axes' horizontal or vertical axis."""

    X = "x"
    Y = "y"


class Gap(Enum):
    """A GridSpec spacing: between columns or between rows."""

    WSPACE = "wspace"
    HSPACE = "hspace"


class Edge(Enum):
    """An edge of the canvas or of a plot."""

    LEFT = "left"
    RIGHT = "right"
    BOTTOM = "bottom"
    TOP = "top"


# -- margins ------------------------------------------------------------------


@dataclass(frozen=True)
class Sides:
    """One figure fraction per edge: a margin, a reservation or an overhang."""

    left: float
    right: float
    bottom: float
    top: float


@dataclass(frozen=True)
class Percent:
    """A margin written ``"5%"``."""

    percent: float


@dataclass(frozen=True)
class Physical:
    """A margin given as a length."""

    length: Length


@dataclass(frozen=True)
class Fraction:
    """A margin given as a bare number: a figure fraction."""

    fraction: float


Margin: TypeAlias = Percent | Physical | Fraction
MarginInput: TypeAlias = Length | str | float


def parse_margin(value: object) -> Margin:
    """``"5%"``, a unit string or :class:`Length`, or a bare figure fraction."""
    if isinstance(value, Length):
        return Physical(value)
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("%"):
            return Percent(float(text[:-1]))
        return Physical(Length.parse(text, "margin"))
    if isinstance(value, int | float) and not isinstance(value, bool):
        return Fraction(float(value))
    raise TypeError(
        f"margin must be Length, str, or number; got {type(value).__name__}"
    )


def _fraction(margin: Margin, extent_in: float) -> float:
    match margin:
        case Percent(percent=percent):
            return percent / 100.0
        case Physical(length=length):
            return length.inch / extent_in
        case Fraction(fraction=fraction):
            return fraction


def parse_margins(
    margin: MarginInput,
    sides: tuple[MarginInput | None, ...],
    size_in: tuple[float, float],
) -> Sides:
    """The margin of each edge (``ml, mr, mt, mb``, else ``margin``) as fractions.

    Raises ``ValueError`` when one is not finite.
    """
    base = parse_margin(margin)
    left, right, top, bottom = (
        base if value is None else parse_margin(value) for value in sides
    )
    width, height = size_in
    out = Sides(
        left=_fraction(left, width),
        right=_fraction(right, width),
        bottom=_fraction(bottom, height),
        top=_fraction(top, height),
    )
    if not all(
        math.isfinite(v) for v in (out.left, out.right, out.bottom, out.top)
    ):
        raise ValueError("margin must resolve to finite figure fractions")
    return out


# -- the call -----------------------------------------------------------------


@dataclass(frozen=True)
class Request:
    """What the figure offers before anything is measured."""

    has_axes: bool
    has_grid: bool
    has_subfigures: bool


@dataclass(frozen=True)
class Go:
    """Lay the figure out."""


@dataclass(frozen=True)
class Refuse:
    """Leave the figure as it is; ``warning`` (when set) says why."""

    warning: str | None


Answer: TypeAlias = Go | Refuse


# -- one measuring step -------------------------------------------------------


@dataclass(frozen=True)
class Box:
    """A display-pixel rectangle."""

    x0: float
    x1: float
    y0: float
    y1: float

    @property
    def width(self) -> float:
        """Its width (px)."""
        return self.x1 - self.x0

    def overlap(self, other: Box) -> float:
        """How deep two boxes cross (<= 0: apart)."""
        return min(
            min(self.x1, other.x1) - max(self.x0, other.x0),
            min(self.y1, other.y1) - max(self.y0, other.y0),
        )


class Role(Enum):
    """What a piece of an Axes' content is."""

    TEXT = "text"  # texts, titles, axis names
    TICK = "tick"  # tick labels in view, offset text
    LEGEND = "legend"


@dataclass(frozen=True)
class Piece:
    """One drawn thing of an Axes that must stay on the canvas.

    ``anchor_x``: where a text is anchored (px), ``None`` when unknown.
    ``outside``: the side of the plot the library anchored a legend outside.
    ``secondary``: it belongs to a ``secondary_xaxis`` / ``secondary_yaxis``.
    """

    box: Box
    role: Role
    anchor_x: float | None = None
    outside: Edge | None = None
    secondary: bool = False


@dataclass(frozen=True)
class AxesContent:
    """An Axes: its plot box (``None``: empty), position and drawn pieces.

    ``position`` is the Axes box as figure fractions. ``tight`` is set for a
    3-D Axes only: its pieces as matplotlib's tight boxes read them.
    """

    plot: Box | None
    position: Sides
    pieces: tuple[Piece, ...]
    tight: tuple[Piece, ...] | None = None


class FigureRole(Enum):
    """What a figure-level artist is."""

    SUPTITLE = "suptitle"
    SUPXLABEL = "supxlabel"
    SUPYLABEL = "supylabel"
    TEXT = "text"
    LEGEND = "legend"


@dataclass(frozen=True)
class FigureArtist:
    """A figure-level text or legend: it reserves one edge of the canvas.

    ``vertical`` is ``None`` for an artist without a rotation (a legend);
    ``side`` the edge ``dm.figure_legend`` placed it on; ``gap`` the room it
    keeps from the panels (px).
    """

    box: Box
    role: FigureRole
    vertical: bool | None
    side: Edge | None
    gap: Px


@dataclass(frozen=True)
class Canvas:
    """The canvas size (px)."""

    width: Px
    height: Px


@dataclass(frozen=True)
class Edges:
    """A GridSpec's ``left, right, bottom, top`` (figure fractions)."""

    left: float
    right: float
    bottom: float
    top: float


@dataclass(frozen=True)
class ContentFacts:
    """What one step measures, and the edges it starts from."""

    axes: tuple[AxesContent, ...]
    artists: tuple[FigureArtist, ...]
    canvas: Canvas
    margins: Sides
    last: Edges | None


@dataclass(frozen=True)
class Fit:
    """What one step fits: each Axes' pieces, each figure artist's edge."""

    axes: tuple[AxesContent, ...]
    reserves: tuple[Edge, ...]


@dataclass(frozen=True)
class Step:
    """New grid edges and the largest edge move since the last step (px)."""

    edges: Edges
    delta: Px

    @property
    def converged(self) -> bool:
        """No edge moved by ``CONVERGE_PX``."""
        return self.delta < CONVERGE_PX


@dataclass(frozen=True)
class History:
    """Every step's edges so far, the last step's move."""

    answers: tuple[Edges, ...]
    delta: Px


@dataclass(frozen=True)
class Next:
    """The edges to write; ``trial``: try them and keep them if they hold."""

    edges: Edges
    trial: bool = False


# -- fitting text once the margins hold ---------------------------------------


Width: TypeAlias = Callable[[Line], Px]
"""A label's drawn width (px) of any text in its font."""


@dataclass(frozen=True)
class TickRow:
    """The bottom tick labels of one Axes, left to right.

    ``texts`` as the axis' formatter writes them (before any wrap of ours),
    ``widths`` one line each, ``gaps`` between neighbouring centres.
    ``authored``: rotated (not by this layout), not centred, multi-line or
    mathtext; ``turned``: the angle this layout gave them.
    """

    axis: ArtistId
    texts: tuple[Line, ...]
    widths: tuple[Px, ...]
    gaps: tuple[Px, ...]
    clearance: Px
    line_height: Px
    authored: bool
    turned: Degrees | None
    width: Width

    def _apart(self) -> list[float]:
        return [
            gap - (self.widths[i] + self.widths[i + 1]) / 2
            for i, gap in enumerate(self.gaps)
        ]

    @property
    def crowded(self) -> bool:
        """Neighbours closer than ``clearance`` (half a pixel of slack)."""
        return any(a < self.clearance - TOUCH_PX for a in self._apart())

    @property
    def worst_overlap(self) -> Px:
        """How far the closest neighbours overlap (negative: apart)."""
        return Px(-min(self._apart()))


@dataclass(frozen=True)
class TickGroup:
    """Axes sharing one x axis (and so one formatter); ``wrapped`` what our
    wrap writes now (empty: none)."""

    axis: ArtistId
    rows: tuple[TickRow, ...]
    wrapped: Mapping[Line, Line]


@dataclass(frozen=True)
class AxisName:
    """An axis name that may wrap: one line, no mathtext, not wrapped by us.

    ``group``: the grid and axis (x / y) it names, for one form per name;
    ``others``: the content boxes of the other panels.
    """

    label: ArtistId
    text: Line
    span: Px
    box: Box
    group: tuple[ArtistId, Which]
    others: tuple[Box, ...]
    width: Width


@dataclass(frozen=True)
class Reach:
    """How far a panel's content passes its cell, along one direction.

    ``along`` / ``across``: the cell's rows or columns (start, stop);
    ``back`` past its left / top edge, ``ahead`` past its right / bottom (px).
    """

    along: tuple[int, int]
    across: tuple[int, int]
    back: Px
    ahead: Px


@dataclass(frozen=True)
class Spacing:
    """One spacing (``wspace`` / ``hspace``) nobody but us set, of a grid of
    ``cells > 1``: the reaches across it, the gaps (px), its extent."""

    key: Gap
    reaches: tuple[Reach, ...]
    gaps: tuple[Px, ...]
    total: Px
    cells: Count
    now: Share
    em: Px


@dataclass(frozen=True)
class TextFacts:
    """``wrapped_names``: names this layout wrapped, by group and text."""

    groups: tuple[TickGroup, ...]
    names: tuple[AxisName, ...]
    wrapped_names: Mapping[tuple[tuple[ArtistId, Which], Line], Line]
    spacings: tuple[Spacing, ...]
    canvas: Canvas


@dataclass(frozen=True)
class PlotSize:
    """A plot box's size (px)."""

    width: Px
    height: Px


@dataclass(frozen=True)
class TextPlan:
    """What to change: wraps per shared x axis, turns per axis, wrapped
    names, new spacing."""

    wraps: Mapping[ArtistId, Mapping[Line, Line]] = field(
        default_factory=dict[ArtistId, Mapping[Line, Line]]
    )
    turns: Mapping[ArtistId, Degrees] = field(
        default_factory=dict[ArtistId, Degrees]
    )
    names: Mapping[ArtistId, Line] = field(default_factory=dict[ArtistId, Line])
    spacing: Mapping[Gap, Share] = field(default_factory=dict[Gap, Share])

    @property
    def empty(self) -> bool:
        """Nothing to change."""
        return not (self.wraps or self.turns or self.names or self.spacing)


Facts: TypeAlias = Request | ContentFacts | History | TextFacts
Plan: TypeAlias = Answer | Fit | Next | TextPlan
