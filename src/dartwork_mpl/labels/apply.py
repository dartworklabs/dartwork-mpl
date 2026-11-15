"""The layout's label hooks, delegating to ``annotation`` until ``labels`` is rebuilt.

Order inside one layout step: :func:`settle_bars`, then (with the legends,
in rounds) :func:`space_line_ends`, then :func:`settle_panels`, then
:func:`hide_covered`; :func:`warn_hidden` once after the fit. Each
``bool`` answer means "the figure must be redrawn before measuring".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure


def settle_bars(fig: Figure, renderer: RendererBase) -> bool:
    """``dm.label_bars`` labels at the Axes size now; whether a view limit moved.

    Only a limit change needs a redraw: tick labels follow limits at draw,
    and the bar labels themselves are measured afresh.
    """
    from ..annotation import settle_bar_labels

    before = [(ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]
    if not settle_bar_labels(fig, renderer):
        return False
    return before != [(ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]


def space_line_ends(fig: Figure, renderer: RendererBase) -> bool:
    """``dm.label_line_ends`` names spaced again at each Axes' size now; whether one moved."""
    from .._figure_geometry import respread_line_end_labels

    moved = False
    for ax in fig.axes:
        if respread_line_end_labels(ax, renderer):
            moved = True
    return moved


def settle_panels(fig: Figure, renderer: RendererBase) -> bool:
    """``dm.label_axes`` letters from the panels as drawn now; whether one moved."""
    from ..annotation import settle_panel_labels

    return settle_panel_labels(fig, renderer)


def hide_covered(fig: Figure, renderer: RendererBase) -> None:
    """Hide the bar labels a legend or other text covers where they are drawn now."""
    from ..annotation import clear_bar_labels

    clear_bar_labels(fig, renderer)


def warn_hidden(fig: Figure, *, stacklevel: int = 1) -> None:
    """Warn once about bar labels the fitted size left no room for.

    ``stacklevel`` as in ``warnings.warn``, counted from the caller of this
    function (1: the line calling it).
    """
    from ..annotation import warn_hidden_bar_labels

    warn_hidden_bar_labels(fig, stacklevel=stacklevel + 1)
