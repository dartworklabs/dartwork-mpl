"""One legend for every panel: ``figure_legend``, and the edge it reserves.

A figure legend the library placed has a :class:`~dartwork_mpl.vocab.Reserve`
in this module's registry: the figure edge it holds and the room the layout
keeps from it. The registry holds its legends weakly.
"""

from __future__ import annotations

import logging
import weakref
from typing import TYPE_CHECKING

from matplotlib.legend import Legend

from ..geometry import figure_axes, figure_legends, get_renderer
from ..hidden import axes_name
from ..vocab import Reserve, edge_of
from .apply import fit, pad_px, size_of
from .model import Above, Best, Columns, Size, parse_loc, refuse_anchor

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.figure import Figure, SubFigure


LOG = logging.getLogger("dartwork_mpl.legend")

_RESERVES: weakref.WeakKeyDictionary[Legend, Reserve] = (
    weakref.WeakKeyDictionary()
)


def figure_reserve(artist: Artist) -> Reserve | None:
    """The edge a ``figure_legend`` legend holds and its gap, else ``None``."""
    return _RESERVES.get(artist) if isinstance(artist, Legend) else None


def figure_legend(
    fig: Figure | SubFigure,
    loc: str,
    asked: Columns | None,
    kw: dict[str, object],
) -> Legend | None:
    """One legend for ``fig``'s panels (:func:`dartwork_mpl.legend.figure_legend`)."""
    where = parse_loc(loc)
    refuse_anchor(where, kw)
    side = Above() if isinstance(where, Best) else where
    handles: list[Artist] = []
    labels: list[str] = []
    for ax in figure_axes(fig):
        for handle, label in zip(*ax.get_legend_handles_labels(), strict=True):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    for ax in figure_axes(fig):
        legend = ax.get_legend()
        names = {t.get_text() for t in legend.get_texts()} if legend else None
        if legend is not None and names is not None and names <= set(labels):
            legend.remove()
            LOG.info(
                "removed the legend of %s: the figure legend shows the same "
                "entries; call ax.legend() after dm.figure_legend to keep it",
                axes_name(ax),
            )
    for legend in figure_legends(fig):
        if legend in _RESERVES:
            legend.remove()
    if not handles:
        return None

    def build(columns: Columns) -> Legend:
        return fig.legend(  # pyright: ignore[reportUnknownMemberType]
            handles,
            labels,
            loc=side.figure_loc.code,
            ncols=columns.n,
            bbox_to_anchor=side.figure_loc.anchor,
            bbox_transform=fig.transSubfigure,
            **kw,
        )

    renderer = get_renderer(fig)

    def trial(columns: Columns) -> Size:
        legend = build(columns)
        size = size_of(legend, renderer)
        legend.remove()
        return size

    first = build(Columns(1))
    pad = pad_px(first, renderer)
    first.remove()
    length = (fig.bbox.width if side.across else fig.bbox.height) - 2 * pad
    columns = fit(trial, side, len(labels), length, asked)
    legend = build(columns)
    # simple_layout keeps this gap between the legend and the panels.
    gap = float(legend.borderaxespad) * float(legend.prop.get_size_in_points())
    _RESERVES[legend] = Reserve(edge_of(across=side.across, far=side.far), gap)
    return legend
