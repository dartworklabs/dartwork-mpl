"""Measure the visible footprint of a single, frameless equal-aspect plot."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.transforms import Bbox

from ..geometry import (
    artist_shown,
    cut_to_clip,
    drawn_patch_box,
    drawn_scatter_discs,
    drawn_tick_labels,
    line_draws_markers,
    line_draws_stroke,
    projection,
    text_inks,
)
from ..vocab import X, Y

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase

    from .model import Text


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
