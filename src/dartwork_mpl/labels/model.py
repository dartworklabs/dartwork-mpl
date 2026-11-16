"""The labels' domain types outside the bars: a point label's sides and the
tries among them, panel letters and line-end columns, as the layout measures
them in display pixels or points. The bar types are in ``bar_geometry`` and
``stacks``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeAlias

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
