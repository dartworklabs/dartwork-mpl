"""Set columns of existing texts beside a plot, one text size apart."""

from __future__ import annotations

from statistics import median
from typing import TYPE_CHECKING

from matplotlib.transforms import Bbox

from ..geometry import get_renderer
from ..vocab import BESIDE_PLOT, BESIDE_TEXT
from .alignment import LOG, extent_anchor, pin_x, visible_row

if TYPE_CHECKING:
    from collections.abc import Iterable

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.text import Text


def beyond(
    ax: Axes, renderer: RendererBase, outward: float, low: float, high: float
) -> float:
    """How far (px) the Axes' own tick labels and y label reach past the
    plot's edge on that side, at the columns' height."""
    labels = [ax.yaxis.label]
    for tick in ax.yaxis.get_major_ticks():
        labels += [tick.label1, tick.label2]
    reach = 0.0
    for label in labels:
        if not label.get_visible() or not label.get_text().strip():
            continue
        box = label.get_window_extent(renderer)
        if box.y1 > low and box.y0 < high:
            past = box.x1 - ax.bbox.x1 if outward > 0 else ax.bbox.x0 - box.x0
            near = box.x0 - ax.bbox.x1 if outward > 0 else ax.bbox.x0 - box.x1
            if near > -1.0:
                reach = max(reach, float(past))
    return reach


def block(texts: list[Text], renderer: RendererBase) -> Bbox:
    """The box the texts of one column take together."""
    return Bbox.union([t.get_window_extent(renderer) for t in texts])


def place_columns(ax: Axes, *columns: Iterable[Text]) -> None:
    """Set columns of texts beside ``ax``'s plot, one text size apart.

    Each column is the texts of one column, its heading included, in
    reading order from left to right. They go to the side of the plot they
    are on now: the nearest one text size from the plot's edge, each next a
    text size and a half after the text before it (tick labels on that
    side count as the text before the first). A column moves
    as one block, so its rows keep their heights and the edge they share;
    from then on it follows the plot's edge when the layout moves it. Call
    it after ``dm.align_texts`` and before ``dm.simple_layout``, which
    makes room for the columns.
    """
    fig = ax.get_figure(root=True)
    groups = [
        [visible_row(t) for t in dict.fromkeys(column)] for column in columns
    ]
    groups = [group for group in groups if group]
    if fig is None or not groups:
        LOG.info("left the columns in place because there are no texts")
        return
    if any(
        t.get_figure(root=True) is not fig or not t.get_visible()
        for group in groups
        for t in group
    ):
        LOG.info(
            "left the columns in place because a text is hidden or on "
            "another figure"
        )
        return
    fig.draw_without_rendering()  # tick labels exist only once drawn
    renderer = get_renderer(fig)
    boxes = [block(group, renderer) for group in groups]
    centre = median((box.x0 + box.x1) / 2 for box in boxes)
    outward = 1.0 if centre > (ax.bbox.x0 + ax.bbox.x1) / 2 else -1.0
    px = fig.dpi / 72
    low = min(box.y0 for box in boxes)
    high = max(box.y1 for box in boxes)
    cursor = beyond(ax, renderer, outward, low, high) / px
    room = BESIDE_TEXT if cursor > 0 else BESIDE_PLOT
    order = list(zip(groups, boxes, strict=True))
    for group, box in order if outward > 0 else reversed(order):
        cursor += room.near * median(
            t.get_fontproperties().get_size_in_points() for t in group
        )
        near = box.x0 if outward > 0 else box.x1
        for text in group:
            offset = (
                outward * cursor + (extent_anchor(text, renderer) - near) / px
            )
            pin_x(text, ax, outward, offset)
        cursor += box.width / px
        room = BESIDE_TEXT
    LOG.info(
        "set %d column%s of text beside the plot",
        len(groups),
        "s" * (len(groups) != 1),
    )
