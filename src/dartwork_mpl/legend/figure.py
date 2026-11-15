"""One legend for every panel: ``figure_legend``, and the edge it reserves.

A figure legend the library placed has a :class:`~dartwork_mpl.vocab.Reserve`
in this module's registry: the figure edge it holds and the room the layout
keeps from it. The registry holds its legends weakly.
"""

from __future__ import annotations

import weakref
from typing import TYPE_CHECKING, assert_never

from matplotlib.legend import Legend

from ..geometry import figure_axes, figure_legends, get_renderer
from ..vocab import Reserve, edge_of
from . import decide, measure
from .apply import entry_names, new_legend, refuse_anchor
from .boxes import Entries
from .measure import LegendKeywords
from .model import (
    AskedLoc,
    Best,
    Columns,
    Passed,
    Request,
    parse_keywords,
    parse_loc,
)
from .sides import Above, Below, Left, Right, Side

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.figure import Figure, SubFigure


_RESERVES: weakref.WeakKeyDictionary[Legend, Reserve] = (
    weakref.WeakKeyDictionary()
)


def figure_reserve(artist: Artist) -> Reserve | None:
    """The edge a ``figure_legend`` legend holds and its gap, else ``None``."""
    return _RESERVES.get(artist) if isinstance(artist, Legend) else None


def figure_legend(
    fig: Figure | SubFigure,
    loc: AskedLoc,
    columns: Columns | None,
    kw: LegendKeywords,
) -> Legend | None:
    """One legend for ``fig``'s panels (:func:`dartwork_mpl.legend.figure_legend`)."""
    handles: list[Artist] = []
    labels: list[str] = []
    for ax in figure_axes(fig):
        for handle, label in zip(*ax.get_legend_handles_labels(), strict=True):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    names = set(labels)
    replaced = [
        legend
        for ax in figure_axes(fig)
        if (legend := ax.get_legend()) is not None
        and set(entry_names(legend)) <= names
    ]
    replaced += [lg for lg in figure_legends(fig) if lg in _RESERVES]
    if not handles:
        for legend in replaced:
            legend.remove()
        return None
    placement = parse_loc(loc)
    match placement:
        case Passed(loc=raw):
            legend = new_legend(
                fig,
                handles,
                labels,
                loc=raw,
                ncols=1 if columns is None else columns.n,
                **kw,
            )
        case Best():
            legend = _placed_figure_legend(
                fig, handles, labels, None, loc, columns, kw
            )
        case Above() | Below() | Right() | Left():
            legend = _placed_figure_legend(
                fig, handles, labels, placement, loc, columns, kw
            )
        case _:
            assert_never(placement)
    for old in replaced:
        old.remove()
    return legend


def _placed_figure_legend(
    fig: Figure | SubFigure,
    handles: list[Artist],
    labels: list[str],
    side: Side | None,
    loc: AskedLoc,
    columns: Columns | None,
    kw: LegendKeywords,
) -> Legend:
    """The figure legend on ``side`` (``None``: the side that fits)."""
    keywords = parse_keywords(kw, LegendKeywords(), columns)
    refuse_anchor("figure_legend", loc, keywords)
    renderer = get_renderer(fig)
    entries = Entries(tuple(labels))
    request = Request(side, keywords.columns)
    facts = measure.figure_facts(
        fig, handles, entries, request, keywords.rest, renderer
    )
    plan = decide.figure_place(facts)
    legend = new_legend(
        fig,
        handles,
        labels,
        loc=plan.side.figure_loc.code,
        ncols=plan.columns.n,
        **(
            keywords.rest
            | LegendKeywords(
                bbox_to_anchor=plan.anchor, bbox_transform=fig.transSubfigure
            )
        ),
    )
    # simple_layout keeps this gap between the legend and the panels.
    gap = float(legend.borderaxespad) * float(legend.prop.get_size_in_points())
    _RESERVES[legend] = Reserve(
        edge_of(across=plan.side.across, far=plan.side.far), gap
    )
    return legend
