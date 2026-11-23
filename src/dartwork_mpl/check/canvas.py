"""Measure footprints where a subplot slot can exceed its visible content."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.colorizer import ColorizingArtist
from matplotlib.container import BarContainer
from matplotlib.text import Annotation
from matplotlib.text import Text as MplText
from matplotlib.transforms import Bbox

from ..geometry import (
    artist_shown,
    cut_to_clip,
    drawn_patch_box,
    drawn_scatter_discs,
    drawn_tick_labels,
    draws_axis,
    line_draws_markers,
    line_draws_stroke,
    projection,
    text_inks,
)
from ..vocab import X, Y, bars_along

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

    from .model import Text


def scale_slot(plot: Axes, scale: Axes, fig: Figure) -> Bbox | None:
    """The space allocated to a plot's attached colorbar on their grid."""
    if not any(
        artist.colorbar is not None and artist.colorbar.ax is scale
        for artist in plot.get_children()
        if isinstance(artist, ColorizingArtist) and artist_shown(artist)
    ):
        return None
    spec = scale.get_subplotspec()
    plot_spec = plot.get_subplotspec()
    if (
        spec is None
        or plot_spec is None
        or spec.get_gridspec() is not plot_spec.get_gridspec()
    ):
        return None
    return spec.get_position(fig).transformed(fig.transFigure)


def shape_panel(ax: Axes) -> bool:
    """A flat, equal-aspect plot whose data is patches or dots."""
    if (
        not projection(ax).flat
        or ax.get_aspect() != 1
        or ax.images
        or ax.tables
        or ax.artists
        or any(not isinstance(c, PathCollection) for c in ax.collections)
    ):
        return False
    return not ax.axison or (
        not ax.get_frame_on()
        and not (drawn_tick_labels(ax, X()) or drawn_tick_labels(ax, Y()))
        and not (text_inks(ax.xaxis.label) or text_inks(ax.yaxis.label))
    )


def bar_panel_without_x_scale(ax: Axes) -> bool:
    """Unlabelled horizontal space surrounds the marks of a column chart."""
    return (
        projection(ax).flat
        and not (ax.images or ax.tables or ax.artists or ax.collections)
        and bool(ax.containers)
        and all(
            isinstance(container, BarContainer)
            and isinstance(bars_along(container.orientation), X)
            for container in ax.containers
        )
        and not (
            drawn_tick_labels(ax, X())
            or drawn_tick_labels(ax, X(), minor=True)
            or (draws_axis(ax, ax.xaxis) and text_inks(ax.xaxis.label))
        )
    )


def content_box(
    ax: Axes, labels: tuple[Text, ...], renderer: RendererBase, px_per_pt: float
) -> Bbox | None:
    """The union of visible shapes, their lines and their placed text."""
    marks = [
        box
        for p in ax.patches
        if (box := drawn_patch_box(p, renderer)) is not None
    ]
    for collection in ax.collections:
        if isinstance(collection, PathCollection) and artist_shown(collection):
            xy, r = drawn_scatter_discs(collection, px_per_pt)
            if len(r):
                lo = np.min(xy - r[:, None], axis=0)
                hi = np.max(xy + r[:, None], axis=0)
                box = cut_to_clip(Bbox([lo, hi]), collection)
                if box is not None:
                    marks.append(box)
    if not marks:
        return None
    marks.extend(
        box
        for line in ax.lines
        if (line_draws_stroke(line) or line_draws_markers(line))
        and (box := cut_to_clip(line.get_window_extent(renderer), line))
        is not None
    )
    return Bbox.union(
        [
            *marks,
            *(
                Bbox.from_extents(t.box.x0, t.box.y0, t.box.x1, t.box.y1)
                for t in labels
            ),
        ]
    )


def label_fit(
    ax: Axes, labels: tuple[Text, ...], renderer: RendererBase
) -> tuple[float | None, float | None]:
    """The left and right x limits at which the labels written in data
    coordinates would end at the plot's edges (``None``: no such label on
    that side, or the scale is not linear). A text keeps its size when the
    limits move, so the limit is solved, not read off."""
    if ax.get_xscale() != "linear":
        return None, None
    low, high = ax.get_xlim()
    box = ax.bbox
    lefts: list[float] = []
    rights: list[float] = []
    for label in labels:
        text = label.handle
        if not isinstance(text, MplText) or text.axes is not ax:
            continue
        if isinstance(text, Annotation):
            # an offset from a data point: the point is what the limits move
            if text.xycoords != "data" or text.get_anncoords() not in (
                "offset points",
                "offset pixels",
                "offset fontsize",
            ):
                continue
            x = float(text.xy[0])
        elif text.get_transform() == ax.transData:
            x = float(text.get_unitless_position()[0])
        else:
            continue
        anchor = float(ax.transData.transform((x, 0.0))[0])
        extent = MplText.get_window_extent(text, renderer)
        before, after = anchor - extent.x0, extent.x1 - anchor
        if 0 < after < box.width and low < x:
            rights.append(low + (x - low) * box.width / (box.width - after))
        if 0 < before < box.width and x < high:
            lefts.append(high - (high - x) * box.width / (box.width - before))
    return (min(lefts) if lefts else None, max(rights) if rights else None)
