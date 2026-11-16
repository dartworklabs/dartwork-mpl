"""Legend placement: inside where it covers no data, or outside a side.

``dm.place_legend(ax)`` places an Axes legend, ``dm.figure_legend(fig)`` one
legend for every panel. ``settle``, ``stack_under_texts``, ``outside_edge`` and
``figure_reserve`` are what ``dm.simple_layout`` is given
(``compose.layout``): the first two place legends again at the fitted size
(a figure legend under a figure title), the others name the edge a legend
sits outside of or holds.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from . import apply, figure
from .apply import outside_edge, report_legends, settle
from .figure import figure_reserve, stack_under_texts
from .measure import Given, Handle
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
    "report_legends",
    "settle",
    "stack_under_texts",
]


def place_legend(
    ax: Axes,
    *,
    loc: AskedLoc = "best",
    handles: Sequence[Handle] | None = None,
    labels: Sequence[str] | None = None,
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
    (``set_bbox_to_anchor``) or moved (``set_loc``) since stays where it
    is, and so does a title the caller gave another transform.

    A ``twinx`` / ``twiny`` pair gets one legend with every twin's entries,
    on the twin drawn last. ``handles`` and ``labels`` are shown as given,
    as ``ax.legend`` shows them; ``labels`` alone names the drawn artists of
    the Axes and its twins in order. A rebuilt legend keeps its title, frame
    and font size; other keywords go to ``ax.legend``.
    """
    given = _given(handles, labels)
    return apply.place_legend(ax, loc, parse_columns(ncols, ncol), given, kw)


def figure_legend(
    fig: Figure | SubFigure,
    *,
    loc: AskedLoc = "best",
    handles: Sequence[Handle] | None = None,
    labels: Sequence[str] | None = None,
    ncols: int | None = None,
    ncol: int | None = None,
    **kw: object,
) -> Legend | None:
    """One legend for every panel of ``fig``, outside the panels.

    The entries are every Axes' labelled artists, each name once, in figure
    order, or the ``handles`` and ``labels`` given, as ``fig.legend`` reads
    them; the panel legends holding only those entries, and one an earlier
    call drew, are removed. ``loc="best"`` and ``"above"`` put it above the
    panels, under a figure title (``dm.simple_layout`` stacks the two);
    ``"below"``, ``"right"`` or ``"left"`` that side, with the
    fewest rows (columns) that fit the figure. ``dm.simple_layout`` keeps
    the panels clear of it. Returns ``None`` when no Axes has a labelled
    artist.
    """
    given = _given(handles, labels)
    return figure.figure_legend(fig, loc, parse_columns(ncols, ncol), given, kw)


def _given(
    handles: Sequence[Handle] | None, labels: Sequence[str] | None
) -> Given:
    return Given(
        None if handles is None else tuple(handles),
        None if labels is None else tuple(labels),
    )
