"""The labels' domain types outside the bars: a point label's sides and the
tries among them, panel letters and line-end columns, as the layout measures
them in display pixels or points, and the one place ``label_bars``'s
``bars=`` is read. The bar types are in ``bar_geometry`` and ``stacks``.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import (
    ClassVar,
    Generic,
    Literal,
    Protocol,
    TypeAlias,
    TypeVar,
    runtime_checkable,
)

from ..vocab import (
    AlignBottom,
    AlignCentre,
    AlignLeft,
    AlignRight,
    AlignTop,
    HAlign,
    VAlign,
    VCentre,
    parse_halign,
)


# ------------------------------------------------------------ point labels
@dataclass(frozen=True)
class Above:
    """Above the point."""

    offset: ClassVar[tuple[float, float]] = (0.0, 1.0)
    ha: ClassVar[HAlign] = AlignCentre()
    va: ClassVar[VAlign] = AlignBottom()


@dataclass(frozen=True)
class Below:
    """Below the point."""

    offset: ClassVar[tuple[float, float]] = (0.0, -1.0)
    ha: ClassVar[HAlign] = AlignCentre()
    va: ClassVar[VAlign] = AlignTop()


@dataclass(frozen=True)
class Right:
    """Right of the point."""

    offset: ClassVar[tuple[float, float]] = (1.0, 0.0)
    ha: ClassVar[HAlign] = AlignLeft()
    va: ClassVar[VAlign] = VCentre()


@dataclass(frozen=True)
class Left:
    """Left of the point."""

    offset: ClassVar[tuple[float, float]] = (-1.0, 0.0)
    ha: ClassVar[HAlign] = AlignRight()
    va: ClassVar[VAlign] = VCentre()


Side: TypeAlias = Above | Below | Right | Left
"""Where ``annotate_value`` puts a label from its point."""

#: The sides ``annotate_value`` tries, in order.
SIDES: tuple[Side, ...] = (Above(), Below(), Right(), Left())


@dataclass(frozen=True)
class Try:
    """A candidate place, measured: how much of the label leaves the axes
    and how much it covers data or text (square pixels)."""

    outside: float
    collision: float

    @property
    def clear(self) -> bool:
        """Inside the axes and covering nothing."""
        return self.outside <= 0 and self.collision <= 0


@dataclass(frozen=True)
class Tries:
    """The candidates in the order tried."""

    tries: tuple[Try, ...]


@dataclass(frozen=True)
class Choice:
    """The index of the candidate taken."""

    index: int


# ------------------------------------------------------------ panel letters
@dataclass(frozen=True)
class Run:
    """Each letter at its plot's left spine, its title right after it on
    the same baseline, left-aligned: one run (``a  Open office``)."""


@dataclass(frozen=True)
class Inside:
    """Each letter inside its plot at the top left, the titles as they
    were: the run of ``panel`` (an index into the panels) was wider than
    its plot."""

    panel: int


#: Where one figure's letters go: the same in every panel.
Placement = Run | Inside


@dataclass(frozen=True)
class Title:
    """A shown title of a panel: its baseline (px)."""

    baseline: float


@dataclass(frozen=True)
class Panel:
    """What one panel draws around its top-left corner, in display pixels.

    ``width`` / ``height`` / ``descent``: its letter's box, ``size`` its
    font size. ``cell`` is the (row, column) key of its own grid cell.
    ``top``: its top decoration; ``decos``: y name and tick boxes as
    ``(x0, x1, y1)``. ``plot_width``: its plot; ``joined``: the width of
    the title that follows the letter in a run (the centre title, else a
    left one); ``apart``: the width of a right title, which stays.
    """

    corner: tuple[float, float]
    width: float
    height: float
    descent: float
    size: float
    cell: tuple[tuple[int, int], tuple[int, int]] | None
    titles: tuple[Title, ...]
    top: float
    decos: tuple[tuple[float, float, float], ...]
    plot_width: float
    joined: float | None
    apart: float | None

    @property
    def gap(self) -> float:
        """Between the letter and its title in a run: half its size."""
        return RUN_GAP_EM * self.size

    @property
    def run(self) -> float:
        """The width of the letter and the titles on its line, in a run."""
        return self.width + sum(
            self.gap + w for w in (self.joined, self.apart) if w
        )


#: Letter to title in a run, and a letter inside a plot from its corner,
#: in letter sizes; how far (px) a run may pass its plot and still fit.
RUN_GAP_EM, INSET_EM, TOUCH_PX = 0.5, 0.4, 0.5


@dataclass(frozen=True)
class PanelsFacts:
    """The panels of one figure's ``label_axes`` calls and its scale."""

    panels: tuple[Panel, ...]
    px_per_pt: float

    def groups(self, axis: int) -> dict[tuple[int, int], list[int]]:
        """Panel indices by grid row (``axis`` 0) or column (1)."""
        out: dict[tuple[int, int], list[int]] = {}
        for i, panel in enumerate(self.panels):
            if panel.cell is not None:
                out.setdefault(panel.cell[axis], []).append(i)
        return out


@dataclass(frozen=True)
class Letters:
    """Each letter's left edge and baseline, and where the title that
    follows it starts (``None``: its titles stay), display pixels."""

    lefts: tuple[float, ...]
    baselines: tuple[float, ...]
    titles: tuple[float | None, ...]


# ------------------------------------------------------------ line ends
@dataclass(frozen=True)
class Column:
    """Label centres along one display axis (points), and the spacing."""

    centres: tuple[float, ...]
    height: float


# ------------------------------------------------------------ bars=
BARS_TAKES = (
    "bars= takes what one ax.bar / ax.barh call returned (bars), a list of "
    "those, or some of its bars (bars[:2], [bars[1]])"
)


class Drawn(Protocol):
    """The bars one ``ax.bar`` / ``ax.barh`` call drew (a ``BarContainer``)."""

    @property
    def patches(self) -> Sequence[object]:
        """Its bars, in order."""
        ...


@runtime_checkable
class Items(Protocol):
    """A value read for its items, in order (a list, a slice of bars)."""

    def __iter__(self) -> Iterator[object]:
        """The items."""
        ...


D = TypeVar("D", bound=Drawn)


@dataclass(frozen=True)
class Chosen(Generic[D]):
    """A drawn container and which of its bars a call labels, by index."""

    bars: D
    indices: frozenset[int]


def choose_bars(request: object, drawn: Sequence[D]) -> tuple[Chosen[D], ...]:
    """``bars=`` read against the containers the figure drew, in order.

    A container chooses all its bars; a bar chooses itself and keeps the
    orientation and value of the container that drew it. ``TypeError``
    naming what ``bars=`` takes for anything else.
    """
    whole = {id(c): c for c in drawn}
    owner = {id(b): (c, i) for c in drawn for i, b in enumerate(c.patches)}
    items = (request,) if id(request) in whole else request
    if not isinstance(items, Items) or isinstance(items, str):
        raise TypeError(f"{BARS_TAKES}; got {type(request).__name__}")
    chosen: dict[int, tuple[D, set[int]]] = {}
    for item in items:
        if id(item) in whole:
            container, indices = (
                whole[id(item)],
                range(len(whole[id(item)].patches)),
            )
        elif id(item) in owner:
            container, index = owner[id(item)]
            indices = range(index, index + 1)
        else:
            raise TypeError(f"{BARS_TAKES}; got {type(item).__name__}")
        chosen.setdefault(id(container), (container, set()))[1].update(indices)
    return tuple(Chosen(c, frozenset(i)) for c, i in chosen.values())


# ------------------------------------------------------------ text alignment
TextAlignment = Literal["left", "right", "center", "decimal"]


@dataclass(frozen=True)
class DecimalAlign:
    """Align each number at its own decimal stop."""


def text_alignment(how: TextAlignment) -> HAlign | DecimalAlign:
    """Parse the public alignment spelling."""
    if how == "decimal":
        return DecimalAlign()
    try:
        return parse_halign(how)
    except ValueError:
        raise ValueError(
            "how must be one of: left, right, center, decimal"
        ) from None
