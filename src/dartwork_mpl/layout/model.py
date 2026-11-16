"""The layout's types, and the one place ``simple_layout``'s margin is parsed.

Two kinds of number cross this slice. A :data:`Px` is a display pixel, as
matplotlib measures a drawn artist; a :class:`Sides` / :class:`Sides` value is
a share of the figure's width (left, right) or height (bottom, top), as a
GridSpec takes it. Every measured fact arrives as one of the types below; the
decisions never see a matplotlib object.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Literal, NewType, TypeAlias

from ..length import Length, written_zero
from ..vocab import Box, Edge, Which

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
# Least a parted panel keeps along the spacing, in ems of the body text: two
# tick labels, the fewest that show a scale.
MIN_CELL_EM = 2.0
ANGLES = (Degrees(30.0), Degrees(45.0), Degrees(90.0))
MAX_TICK_LINES = 3
MAX_NAME_LINES = 4
FIT_ROUNDS = 3
# Figure text centred in this outer band of the canvas reserves that edge.
EDGE_BAND = 0.15
EDGE_BAND_TOL = 1e-9


@dataclass(frozen=True)
class WSpace:
    """A GridSpec's spacing between columns (``wspace``)."""


@dataclass(frozen=True)
class HSpace:
    """A GridSpec's spacing between rows (``hspace``)."""


Gap: TypeAlias = WSpace | HSpace


# -- what matplotlib writes, read once ----------------------------------------

#: The mode a layout turns tick labels with: their ends stay at their ticks.
TURN_MODE: Literal["xtick"] = "xtick"


def turned_here(rotation: float, mode: str) -> bool:
    """A tick label as a layout turned it: one of ``ANGLES``, ``TURN_MODE``
    (``ax.tick_params(rotation=...)`` and ``autofmt_xdate`` keep matplotlib's
    default mode)."""
    return mode == TURN_MODE and rotation in ANGLES


#: A rectilinear Axes' spine, as ``ax.spines`` names it.
Spine: TypeAlias = Literal["left", "right", "bottom", "top"]
FACING: Mapping[Spine, Spine] = {
    "left": "right",
    "right": "left",
    "bottom": "top",
    "top": "bottom",
}


def tick_spine(position: str) -> Spine | None:
    """The one side an axis ticks on (``Axis.get_ticks_position``);
    ``None`` for both, neither or unknown."""
    return next((side for side in FACING if side == position), None)


def authored(text: str) -> bool:
    """Text its author broke into lines or wrote as mathtext."""
    return "\n" in text or "$" in text


def centred(align: str) -> bool:
    """A horizontal alignment (``Text.get_horizontalalignment``) of centre."""
    return align == "center"


def tokens(text: Line) -> tuple[Line, ...]:
    """Words split at spaces outside brackets: ``(MWh per year)`` stays whole."""
    out: list[Line] = []
    depth = 0
    word = ""
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]" and depth:
            depth -= 1
        if ch.isspace() and depth == 0:
            if word:
                out.append(Line(word))
            word = ""
        else:
            word += ch
    if word:
        out.append(Line(word))
    return tuple(out)


# -- margins ------------------------------------------------------------------


@dataclass(frozen=True)
class Sides:
    """One figure fraction per edge: a margin, a reservation, an Axes'
    position or a GridSpec's ``left, right, bottom, top``."""

    left: float
    right: float
    bottom: float
    top: float


#: ``margin=0``: the content flush with the canvas edge.
Flush: TypeAlias = Literal[0]


def parse_margin(
    margin: Length | str | Flush, size_in: tuple[float, float]
) -> Sides:
    """``margin`` (a :class:`Length`, a unit string or zero) as figure
    fractions."""
    if written_zero(margin):
        return Sides(left=0.0, right=0.0, bottom=0.0, top=0.0)
    length = Length.parse(margin, "margin")
    width, height = size_in
    x, y = length.inch / width, length.inch / height
    return Sides(left=x, right=x, bottom=y, top=y)


# -- one measuring step -------------------------------------------------------


@dataclass(frozen=True)
class AxesContent:
    """An Axes' position (figure fractions) and its drawn content box.

    ``widest``: its widest title or x name (px), text centred on the plot
    whose width no plot width changes; ``narrow``: the content with those
    texts one pixel wide, as matplotlib's own layouts count them;
    ``titled``: it shows a title.
    """

    position: Sides
    box: Box
    widest: Px
    narrow: Box
    titled: bool


@dataclass(frozen=True)
class FigureArtist:
    """A figure-level text or legend: it reserves one edge of the canvas.

    ``vertical`` is ``None`` for an artist without a rotation (a legend);
    ``gap`` the room it keeps from the panels (px).
    """

    box: Box
    vertical: bool | None
    gap: Px


@dataclass(frozen=True)
class Canvas:
    """The canvas size (px)."""

    width: Px
    height: Px


@dataclass(frozen=True)
class ContentFacts:
    """What one step measures, and the edges it starts from.

    ``title_pad``: the preset's room between a title and what it titles
    (``axes.titlepad``, px).
    """

    axes: tuple[AxesContent, ...]
    artists: tuple[FigureArtist, ...]
    canvas: Canvas
    margins: Sides
    last: Sides | None
    title_pad: Px


Reserves: TypeAlias = tuple[Edge, ...]
"""The canvas edge each figure artist reserves, in order."""


@dataclass(frozen=True)
class Step:
    """New grid edges and the largest edge move since the last step (px)."""

    edges: Sides
    delta: Px

    @property
    def converged(self) -> bool:
        """No edge moved by ``CONVERGE_PX``."""
        return self.delta < CONVERGE_PX


# -- fitting text once the margins hold ---------------------------------------


Width: TypeAlias = Callable[[Line], Px]
"""A label's drawn width (px) of any text in its font."""


@dataclass(frozen=True)
class TickRow:
    """The bottom tick labels of one Axes, left to right.

    ``texts`` as the axis' formatter writes them (before any wrap of ours),
    ``widths`` one line each, ``gaps`` between neighbouring centres.
    ``authored``: rotated, not centred, multi-line or mathtext.
    """

    axis: ArtistId
    texts: tuple[Line, ...]
    widths: tuple[Px, ...]
    gaps: tuple[Px, ...]
    clearance: Px
    line_height: Px
    authored: bool
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
    """An axis name that may wrap: one line, no mathtext.

    ``span``: its plot's side (px); ``group``: the grid and axis (x / y) it
    names, for one form per name; ``box`` where it is drawn; ``others``
    the content of the panels not at its position.
    """

    label: ArtistId
    text: Line
    span: Px
    group: tuple[ArtistId, Which]
    width: Width
    box: Box
    others: tuple[Box, ...]


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
    """One spacing (``wspace`` / ``hspace``) nobody set, of a grid of
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
    """What text fitting reads from the drawn figure."""

    groups: tuple[TickGroup, ...]
    names: tuple[AxisName, ...]
    spacings: tuple[Spacing, ...]
    canvas: Canvas


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
