"""Where a legend goes and what the decisions read to choose it.

A plan puts a legend :class:`Inside` its Axes or :class:`Outside` a side,
a figure legend at a figure edge, an Axes' entries on one host. The facts
carry the measured boxes and the measuring functions (how big a legend of
these entries is, whether a box meets data ink), so ``decide`` and
``edges`` stay free of matplotlib.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .boxes import Box, Entries, Hits, Size, Span
from .model import Columns, Request
from .sides import Loc, Side, middle


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
        return middle(self.side)


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
