"""Panel letters and line-end names as the layout measures them: each panel's
title and decoration, the letters of a call, a column of names.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    """The panels of one ``label_axes`` call, its scale and fixed ``y``."""

    panels: tuple[Panel, ...]
    px_per_pt: float
    fixed_y: bool

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
