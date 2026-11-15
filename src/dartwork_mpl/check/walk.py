"""Which panels and texts a figure draws, and where a text draws."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from matplotlib.axes import Axes
from matplotlib.axes._secondary_axes import SecondaryAxis
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from ..geometry import axes_titles, draws_axis, holders_shown, panel_letters
from .model import Axis, spatial

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


def secondary_texts(
    axis: SecondaryAxis, drawn: Drawn
) -> tuple[list[Text], list[Text]]:
    """A secondary axis' drawn axis labels and its drawn major tick labels.

    A ``SecondaryAxis`` has no titles and no ``ax.text``; what it draws is
    one axis: its label and its tick labels, as ``drawn`` recorded them.
    """
    labels = [a.label for a in (axis.xaxis, axis.yaxis)]
    ticks = [
        label
        for a in (axis.xaxis, axis.yaxis)
        for tick in a.get_major_ticks()
        for label in (tick.label1, tick.label2)
    ]
    return (
        [t for t in labels if t in drawn.texts],
        [t for t in ticks if t in drawn.texts],
    )


def sup_labelled(ax: Axes, which: Axis) -> bool:
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


@dataclass(frozen=True)
class Drawn:
    """What one draw of a figure drew: every visible text it drew, and where
    each text of a 3D Axes drew."""

    texts: set[Text] = field(default_factory=set[Text])
    spatial: dict[Text, Bbox] = field(default_factory=dict[Text, Bbox])

    def extent(self, text: Text, renderer: RendererBase) -> Bbox:
        """The window extent of ``text`` where it draws.

        A 3D axes' ``ax.text(x, y, z, ...)`` (a ``Text3D``) is placed by
        projection only while it draws; outside a draw ``get_window_extent``
        reads the unprojected ``(x, y)`` through the axes' 2D transform,
        thousands of pixels off. A text of a 3D Axes is therefore measured
        as the draw placed it (a text the draw hid, at a position its scale
        cannot take or outside the limits with ``axlim_clip``, has a NaN
        extent; one the draw never reached an empty one). Every other text:
        its ``get_window_extent``.
        """
        axes = text.axes
        if axes is None or not spatial(axes.name):
            return text.get_window_extent(renderer)
        return self.spatial.get(text, Bbox.from_bounds(0, 0, 0, 0))


@contextmanager
def recording() -> Generator[Drawn, None, None]:
    """Record, while the block draws, each text matplotlib draws.

    ``Text3D.draw`` projects its position and angle and calls ``Text.draw``
    with them set; read there, a text's extent is where it draws. The
    original ``Text.draw`` is back when the block ends.
    """
    drawn = Drawn()
    original = Text.draw

    def draw(self: Text, renderer: RendererBase) -> None:
        if self.get_visible():
            drawn.texts.add(self)
            axes = self.axes
            if axes is not None and spatial(axes.name):
                drawn.spatial[self] = Text.get_window_extent(self, renderer)
        original(self, renderer)

    Text.draw = draw
    try:
        yield drawn
    finally:
        Text.draw = original
