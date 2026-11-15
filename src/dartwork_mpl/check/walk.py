"""Which panels and texts a figure draws, and where a text draws."""

from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib.axes import Axes
from matplotlib.axes._secondary_axes import SecondaryAxis
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from ..axis import Which
from ..geometry import (
    axes_titles,
    draws_axis,
    holders_shown,
    in_view_tick_labels,
    panel_letters,
)
from ..projection import parse_projection

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure


def drawn_axes(fig: Figure) -> list[tuple[int, Axes]]:
    """Each Axes of ``fig.axes`` no hidden SubFigure hides, with its index.

    The index is into ``fig.axes`` (the ``axes_index`` the checks report),
    not into this list. Each Axes' own visibility is left to the caller, as
    it was: without SubFigures this is ``enumerate(fig.axes)``.
    """
    return [(i, ax) for i, ax in enumerate(fig.axes) if holders_shown(ax)]


def panel_labels(fig: Figure | SubFigure) -> list[tuple[Axes, Text]]:
    """The letters ``dm.label_axes`` placed on ``fig``, each with its panel.

    Only the automatic ones (``x="auto"``); a letter at a position the
    caller gave is an ordinary text.
    """
    return [(ax, text) for ax, text in panel_letters(fig)]


def secondary_axes(ax: Axes) -> list[SecondaryAxis]:
    """Return the visible ``secondary_xaxis`` / ``secondary_yaxis`` children of ``ax``.

    Matplotlib keeps them in ``ax.child_axes``, not in ``fig.axes``, so a
    walk over ``fig.axes`` never sees their tick labels or axis label, which
    sit around ``ax``'s box like its own. Inset Axes, also children, are not
    included.
    """
    return [
        child
        for child in ax.child_axes
        if isinstance(child, SecondaryAxis) and child.get_visible()
    ]


def secondary_texts(axis: SecondaryAxis) -> tuple[list[Text], list[Text]]:
    """A secondary axis' drawn axis labels and its drawn major tick labels.

    A ``SecondaryAxis`` has no titles and no ``ax.text``; what it draws is
    its axes while they are on and shown: each one's visible label and the
    visible labels of the ticks in its view (``geometry.in_view_tick_labels``).
    """
    shown = [
        a for a in (axis.xaxis, axis.yaxis) if axis.axison and a.get_visible()
    ]
    labels = [a.label for a in shown if a.label.get_visible()]
    ticks = [label for a in shown for label in in_view_tick_labels(a)]
    return labels, ticks


def sup_labelled(ax: Axes, which: Which) -> bool:
    """The figure (or SubFigure) holding ``ax`` names ``which`` axis in a
    shown ``supxlabel`` / ``supylabel``."""
    fig = ax.get_figure(root=False)
    if fig is None:
        return False
    sup = which.pick(fig.get_supxlabel(), fig.get_supylabel())
    return bool(sup.strip()) and any(
        t.get_visible() and t.get_text() == sup for t in fig.texts
    )


def drawn_axes_texts(ax: Axes) -> list[Text]:
    """``ax.texts``, the three titles and the axis labels matplotlib draws.

    An axis label draws with its axis (:func:`draws_axis`): not
    on a 2D Axes after ``ax.axis("off")`` or with that axis hidden, nor on a
    3D Axes after ``set_axis_off``; there it stays where it was never drawn,
    often past the canvas. The checks read these texts; the layout still
    measures every label.
    """
    labels = [
        axis.label for axis in (ax.xaxis, ax.yaxis) if draws_axis(ax, axis)
    ]
    return [*ax.texts, *axes_titles(ax).values(), *labels]


def extent(text: Text, renderer: RendererBase) -> Bbox:
    """The window extent of ``text`` where it draws.

    A 3D axes' ``ax.text(x, y, z, ...)`` (a ``Text3D``) is placed by
    projection only while it draws; outside a draw ``get_window_extent``
    reads the unprojected ``(x, y)`` through the axes' 2D transform,
    thousands of pixels off. A text of a 3D Axes is therefore drawn once
    more, alone, into a :class:`Placement` that reads its extent as it
    draws (:func:`placed`). Every other text: its ``get_window_extent``.
    """
    axes = text.axes
    if axes is None or not parse_projection(axes.name).spatial:
        return text.get_window_extent(renderer)
    return placed(text)


class Placement(RendererAgg):
    """A renderer that keeps where the one text drawn into it is placed.

    ``Text.draw`` opens its group first, inside ``Text3D.draw``'s projected
    position and angle; the text's extent read there is where it draws.
    Its output lands on a one-pixel canvas and is thrown away.
    """

    def __init__(self, text: Text, dpi: float) -> None:
        """An empty placement for ``text`` at ``dpi``."""
        super().__init__(1, 1, dpi)
        self.text = text
        self.box: Bbox | None = None

    def open_group(self, s: str, gid: str | None = None) -> None:
        """The text's first group: read its extent while it is placed."""
        if self.box is None:
            self.box = Text.get_window_extent(self.text, self)
        super().open_group(s, gid)


def placed(text: Text) -> Bbox:
    """Where ``text`` draws, read by drawing it alone into a :class:`Placement`.

    The draw projects as the figure's last draw did (the 3D Axes keeps its
    projection ``M`` from it). A text that draw hides (at a position its
    scale cannot take, or outside the limits with ``axlim_clip``) has a NaN
    extent; one it does not draw at all (invisible, empty) an empty one.
    Only ``text`` is drawn; no figure-wide state is touched.
    """
    root = text.get_figure(root=True)
    if root is None:
        return Bbox.from_bounds(0, 0, 0, 0)
    placement = Placement(text, root.dpi)
    text.draw(placement)
    return placement.box or Bbox.from_bounds(0, 0, 0, 0)
