"""What the legend decisions read from a drawn figure.

The entries of an Axes and its twins, the labels beyond each side of it,
and where its titles sit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib as mpl

from ..geometry import BBOX_ERRORS, axes_titles, same_position_axes
from ..vocab import Box
from .ink import box_of, px
from .model import TitleFacts

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.text import Text


def entries(ax: Axes) -> tuple[Axes, list[Artist], list[str]]:
    """The Axes a legend of ``ax`` goes on and its handles and names.

    With twins, every twin's labelled artists once, in figure order, on the
    twin drawn last, so no twin's data is drawn over the legend.
    """
    owners = same_position_axes(ax)
    parent = ax.get_figure(root=False)
    order = list(parent.axes) if parent is not None else owners
    host = max(owners, key=lambda o: (o.get_zorder(), order.index(o)))
    handles: list[Artist] = []
    labels: list[str] = []
    for owner in sorted(owners, key=order.index):
        for handle, label in zip(
            *owner.get_legend_handles_labels(), strict=True
        ):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    return host, handles, labels


def decorations(ax: Axes, renderer: RendererBase) -> tuple[Box, ...]:
    """In-view tick labels, axis labels and offset texts of ``ax`` and twins."""
    texts: list[Text] = []
    for owner in same_position_axes(ax):
        for axis, index in ((owner.xaxis, 0), (owner.yaxis, 1)):
            if not axis.get_visible():
                continue
            vmin, vmax = sorted(axis.get_view_interval())
            tol = abs(vmax - vmin) * 1e-5
            texts.extend(
                tick
                for tick in axis.get_ticklabels(which="both")
                if vmin - tol <= tick.get_position()[index] <= vmax + tol
            )
            texts.extend((axis.label, axis.get_offset_text()))
    boxes: list[Box] = []
    for text in texts:
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            ext = text.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if ext.width > 0 and ext.height > 0:
            boxes.append(box_of(ext))
    return tuple(boxes)


def titles(ax: Axes, renderer: RendererBase) -> TitleFacts | None:
    """Where the shown titles of ``ax`` sit unpadded, and their pad."""
    found = [
        t
        for t in axes_titles(ax).values()
        if t.get_visible() and t.get_text().strip()
    ]
    if not found:
        return None
    pos = found[0].get_position()
    base = float(ax.transAxes.transform(pos)[1])
    pad = float(found[0].get_transform().transform(pos)[1]) - base
    gap = px(renderer, float(mpl.rcParams["axes.titlepad"]))
    return TitleFacts(base, pad, gap)
