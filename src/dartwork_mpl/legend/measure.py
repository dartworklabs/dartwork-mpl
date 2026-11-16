"""What the legend decisions read from a drawn figure.

The entries of an Axes and its twins, the labels beyond each side of it,
and where its titles sit.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import matplotlib as mpl
from matplotlib.artist import Artist
from matplotlib.container import Container
from matplotlib.legend import Legend

from ..geometry import BBOX_ERRORS, axes_titles, same_position_axes
from ..vocab import Box
from .ink import box_of, px
from .model import TitleFacts, listed

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.text import Text


#: What a legend entry draws: an artist, or a container (bars, error bars).
Handle = Artist | Container


@dataclass(frozen=True)
class Given:
    """The entries a caller passed, read as ``ax.legend`` reads them.

    ``handles`` and ``labels`` are ``None`` when not passed: handles alone
    take their own labels, labels alone name the drawn artists in order.
    """

    handles: tuple[Handle, ...] | None = None
    labels: tuple[str, ...] | None = None


def entries(ax: Axes, given: Given) -> tuple[Axes, list[Handle], list[str]]:
    """The Axes a legend of ``ax`` goes on and its handles and names.

    With twins, the entries of every twin in figure order, on the twin
    drawn last, so no twin's data is drawn over the legend.
    """
    owners = same_position_axes(ax)
    parent = ax.get_figure(root=False)
    order = list(parent.axes) if parent is not None else owners
    host = max(owners, key=lambda o: (o.get_zorder(), order.index(o)))
    handles, labels = gather(sorted(owners, key=order.index), given)
    return host, handles, labels


def gather(
    owners: Sequence[Axes], given: Given
) -> tuple[list[Handle], list[str]]:
    """The handles and names a legend of ``owners`` shows.

    Nothing given: every labelled artist, each name once. What the caller
    gave is shown as given, the way ``ax.legend`` shows it.
    """
    match given.handles, given.labels:
        case None, None:
            handles: list[Handle] = []
            labels: list[str] = []
            for owner in owners:
                for handle, label in zip(
                    *owner.get_legend_handles_labels(), strict=True
                ):
                    if label not in labels:
                        handles.append(handle)
                        labels.append(label)
            return handles, labels
        case tuple() as shown, None:
            return list(shown), [str(h.get_label()) for h in shown]
        case None, tuple() as names:
            pairs = list(zip(_drawn(owners), names, strict=False))
            return [h for h, _ in pairs], [n for _, n in pairs]
        case tuple() as shown, tuple() as names:
            if len(shown) != len(names):
                warnings.warn(
                    f"{len(shown)} handles and {len(names)} labels were "
                    "given; the legend shows the first "
                    f"{min(len(shown), len(names))} pairs",
                    stacklevel=2,
                )
            pairs = list(zip(shown, names, strict=False))
            return [h for h, _ in pairs], [n for _, n in pairs]


def _drawn(owners: Sequence[Axes]) -> Iterator[Handle]:
    """The artists of ``owners`` a legend can show, in the order drawn."""
    handlers = Legend.get_default_handler_map()
    for owner in owners:
        added: set[Artist] = {
            *owner.lines,
            *owner.patches,
            *owner.collections,
            *owner.texts,
        }
        for artist in (
            *(a for a in owner.get_children() if a in added),
            *owner.containers,
        ):
            if listed(artist.get_label()) and (
                Legend.get_legend_handler(handlers, artist) is not None
            ):
                yield artist


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
