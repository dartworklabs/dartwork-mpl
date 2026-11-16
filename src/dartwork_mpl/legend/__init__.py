"""Legend placement: inside where it covers no data, or outside a side.

``dm.place_legend(ax)`` places an Axes legend, ``dm.figure_legend(fig)`` one
legend for every panel. ``settle``, ``outside_edge`` and ``figure_reserve``
are what ``dm.simple_layout`` is given (``compose.layout``): the first places
legends again at the fitted size, the others name the edge a legend sits
outside of or holds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import apply, figure
from .apply import outside_edge, settle
from .figure import figure_reserve
from .model import AskedLoc, parse_columns

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.legend import Legend

__all__ = [
    "figure_legend",
    "figure_reserve",
    "outside_edge",
    "place_legend",
    "settle",
]


def place_legend(
    ax: Axes,
    *,
    loc: AskedLoc = "best",
    ncols: int | None = None,
    ncol: int | None = None,
    **kw: object,
) -> Legend | None:
    """Place or rebuild the legend of ``ax``; returns it (``None``: no entries).

    ``loc="best"``: the first of the four corners, upper and lower centre,
    centre right and left that keeps 2 pt from every line, marker, bar,
    filled area and text of the Axes and its twins; none free, the one
    meeting the fewest.

    ``loc="above"``, ``"below"``, ``"right"`` or ``"left"`` puts it outside
    that side, centred, past the side's tick and axis labels: the fewest
    rows (above, below) or columns (right, left) that fit along the Axes.
    ``bbox_to_anchor`` raises ``ValueError`` there.

    ``dm.simple_layout`` places it again at the size it gives the Axes, and
    raises the titles over a legend above. A legend the caller anchored
    since (``set_bbox_to_anchor``) stays where it is.

    A ``twinx`` / ``twiny`` pair gets one legend with every twin's entries,
    on the twin drawn last. A rebuilt legend keeps its title, frame and font
    size; other keywords go to ``ax.legend``.
    """
    return apply.place_legend(ax, loc, parse_columns(ncols, ncol), kw)


def figure_legend(
    fig: Figure | SubFigure,
    *,
    loc: AskedLoc = "best",
    ncols: int | None = None,
    ncol: int | None = None,
    **kw: object,
) -> Legend | None:
    """One legend for every panel of ``fig``, outside the panels.

    The entries are every Axes' labelled artists, each name once, in figure
    order; the panel legends holding only those entries, and one an earlier
    call drew, are removed. ``loc="best"`` and ``"above"`` put it above the
    panels; ``"below"``, ``"right"`` or ``"left"`` that side, with the
    fewest rows (columns) that fit the figure. ``dm.simple_layout`` keeps
    the panels clear of it. Returns ``None`` when no Axes has a labelled
    artist.
    """
    return figure.figure_legend(fig, loc, parse_columns(ncols, ncol), kw)
