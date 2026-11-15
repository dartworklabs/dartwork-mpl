"""Legend placement: inside where it covers no data, else outside a side.

``dm.place_legend(ax)`` places an Axes legend, ``dm.figure_legend(fig)`` one
legend for every panel. ``settle``, ``place_figure_legends`` and
``outside_side`` are the hooks ``dm.simple_layout`` calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from . import apply
from .apply import outside_side, place_figure_legends, settle

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.legend import Legend

__all__ = [
    "figure_legend",
    "outside_side",
    "place_figure_legends",
    "place_legend",
    "settle",
]


def place_legend(ax: Axes, *, loc: str = "best", **kw: Any) -> Legend | None:
    """Place or reposition an Axes legend; returns it (``None``: no entries).

    ``loc="best"``: the first inside spot (four corners, upper and lower
    centre, centre right and left; one to three columns, fewest first) that
    keeps 2 pt from every line, marker, bar, filled area and text of the Axes
    and its twins; a one-column legend taller than 55 % of the Axes is tried
    last. None free and no ``bbox_to_anchor``: outside, above, else right,
    else below, on the first side no other panel sits beyond that the legend
    fits along. Otherwise the inside spot that meets the fewest artists.

    ``loc="above"``, ``"below"``, ``"right"`` or ``"left"`` puts it outside
    that side, centred, past the side's tick and axis labels by the preset's
    ``legend.borderaxespad``: the fewest rows that fit across (above, below)
    or columns that fit along (right, left). Names too long for the side, or
    a right or left legend wider than 40 % of the Axes, break at spaces
    (a trailing bracketed unit kept whole). ``bbox_to_anchor`` raises
    ``ValueError`` there. Any other ``loc`` goes to ``ax.legend`` unchanged.

    ``dm.simple_layout`` places it again at the size it gives the Axes: a
    legend moves only inwards (to a spot free now) or keeps its side, and
    the titles rise above a legend above the Axes. A legend the caller moved
    since (``set_loc``, ``set_bbox_to_anchor``) stays where it is.

    A ``twinx`` / ``twiny`` pair gets one legend with every twin's entries
    on the twin drawn last; the others' legends are removed. A legend that is
    not what the artists draw (tuple handles, explicit labels) is left as it
    is; a matplotlib ``loc`` or ``bbox_to_anchor`` still moves it. A rebuilt
    legend keeps its title, frame, font size and custom handlers; keywords
    here (``ncols``, ``fontsize``, ``frameon`` ...) win.
    """
    return apply.place_legend(ax, loc, kw)


def figure_legend(
    fig: Figure | SubFigure, *, loc: str = "best", **kw: Any
) -> Legend | None:
    """One legend for every panel of ``fig``, outside the panels.

    The entries are every Axes' labelled artists, each name once, in figure
    order; the panel legends holding only those entries, and one an earlier
    call drew, are removed. ``loc="best"`` puts it above the panels (right
    when it does not fit above); ``"above"``, ``"below"``, ``"right"`` or
    ``"left"`` is that side, with the fewest rows (columns) that fit the
    figure. It clears the figure's own label there (suptitle above,
    supxlabel below, supylabel left). Any other ``loc`` goes to
    ``fig.legend``. ``dm.simple_layout`` keeps the panels clear of it.
    Returns ``None`` when no Axes has a labelled artist.
    """
    return apply.figure_legend(fig, loc, kw)
