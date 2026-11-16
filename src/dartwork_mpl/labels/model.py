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
class Title:
    """A shown title of a panel: its baseline (px)."""

    baseline: float


@dataclass(frozen=True)
class Panel:
    """What one panel draws around its top-left corner, in display pixels.

    ``cell`` is the (row, column) key of its own grid cell. ``ylabel_x0``
    is the outer edge of its left y-axis name, ``guess_x0`` where one would
    be. ``top``: its top decoration; ``decos``: y name and tick boxes as
    ``(x0, x1, y1)``.
    """

    corner: tuple[float, float]
    width: float
    descent: float
    cell: tuple[tuple[int, int], tuple[int, int]] | None
    ylabel_x0: float | None
    guess_x0: float
    titles: tuple[Title, ...]
    top: float
    decos: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class PanelsFacts:
    """The panels of one ``label_axes`` call and its scale."""

    panels: tuple[Panel, ...]
    px_per_pt: float

    def groups(self, axis: int) -> dict[tuple[int, int], list[int]]:
        """Panel indices by grid row (``axis`` 0) or column (1)."""
        out: dict[tuple[int, int], list[int]] = {}
        for i, panel in enumerate(self.panels):
            if panel.cell is not None:
                out.setdefault(panel.cell[axis], []).append(i)
        return out

    def mates(self, i: int, axis: int) -> list[int]:
        """The panels in the row (0) or column (1) of panel ``i``, or itself."""
        cell = self.panels[i].cell
        return [i] if cell is None else self.groups(axis)[cell[axis]]


@dataclass(frozen=True)
class Letters:
    """Each letter's left edge and baseline, display pixels."""

    lefts: tuple[float, ...]
    baselines: tuple[float, ...]


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
