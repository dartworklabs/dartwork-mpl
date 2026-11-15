"""The layout's legend hooks, delegating to ``annotation`` until ``legend`` is rebuilt.

The title lift over a legend above its Axes lives here already (moved
verbatim from ``layout``): it is a legend rule the layout only triggers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib as mpl
from matplotlib.transforms import Bbox, ScaledTranslation

from .._figure_geometry import BBOX_ERRORS as _BBOX_ERRORS
from .._figure_geometry import (
    OutsideSide,
    axes_titles,
    reanchor_outside,
    same_position_axes,
)
from .._figure_geometry import outside_side as _anchored_side

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.legend import Legend


def settle(
    fig: Figure, renderer: RendererBase, axes: Sequence[Axes] | None = None
) -> bool:
    """Legends at the Axes size now, then titles lifted over legends above them.

    ``dm.place_legend``'s legends on ``axes`` (every Axes when ``None``) are
    placed again at the size those Axes have now; a legend anchored outside
    a side moves past that side's labels (and past the ``dm.label_bars``
    values beyond that limit it would cover); a title never sits on a
    legend above its Axes. Returns whether anything moved (the caller
    redraws before measuring).
    """
    from ..annotation import bar_values_past_limits, settle_legends

    moved = settle_legends(fig, renderer, axes)
    for ax in fig.axes:
        legend = ax.get_legend()
        if legend is not None and _anchored_side(legend) is not None:
            values = bar_values_past_limits(ax, renderer)
            if reanchor_outside(legend, ax, renderer, values):
                moved = True
    for ax in fig.axes:
        if _lift_titles_over_legends(ax, renderer):
            moved = True
    return moved


def place_figure_legends(fig: Figure, holder: Figure | SubFigure) -> None:
    """``dm.figure_legend``'s legends of ``holder`` past its title and labels."""
    from ..annotation import settle_figure_legends

    settle_figure_legends(fig, holder)


def outside_side(legend: Legend) -> OutsideSide | None:
    """The side a legend is anchored outside of, or ``None`` (inside, by hand)."""
    return _anchored_side(legend)


def _legend_extents_above(ax: Axes, renderer: RendererBase) -> list[Bbox]:
    """Return the extents of the legends of ``ax`` and its twins that sit above it.

    A legend sits above when its vertical centre is above the top of the
    Axes box — a raw ``ax.legend(loc="lower center", bbox_to_anchor=(0.5,
    1.0))`` as well as ``dm.place_legend(ax, loc="above")``. Legends of
    other panels and figure legends are not included.
    """
    try:
        top = ax.get_window_extent(renderer).y1
    except _BBOX_ERRORS:
        return []
    extents: list[Bbox] = []
    for owner in same_position_axes(ax):
        legend = owner.get_legend()
        if legend is None or not legend.get_visible():
            continue
        try:
            ext = legend.get_window_extent(renderer)
        except _BBOX_ERRORS:
            continue
        if ext.width > 0 and ext.height > 0 and (ext.y0 + ext.y1) / 2 > top:
            extents.append(ext)
    return extents


def _lift_titles_over_legends(ax: Axes, renderer: RendererBase) -> bool:
    """Raise the titles of ``ax`` above a legend that sits above it.

    A title that overlaps such a legend horizontally (within the title pad)
    and is not wholly below it gets the pad that puts its baseline
    ``axes.titlepad`` points above the legend's top, the same gap the
    preset leaves between a title and the Axes. All three title slots take
    the new pad so they keep one baseline. Only the title offset changes:
    text, font size and weight stay. A pad already large enough is kept.
    Returns whether a pad changed.
    """
    titles = [
        title
        for title in axes_titles(ax).values()
        if title.get_visible() and title.get_text().strip()
    ]
    root = ax.get_figure(root=True)
    if not titles or root is None:
        return False
    legends = _legend_extents_above(ax, renderer)
    if not legends:
        return False
    gap_px = float(mpl.rcParams["axes.titlepad"]) * root.dpi / 72.0
    pad_px = 0.0
    needed_px = 0.0
    for title in titles:
        try:
            ext = title.get_window_extent(renderer)
        except _BBOX_ERRORS:
            continue
        position = title.get_position()
        base_y = ax.transAxes.transform(position)[1]
        own_pad = title.get_transform().transform(position)[1] - base_y
        pad_px = max(pad_px, own_pad)
        for legend in legends:
            side_by_side = (
                ext.x1 <= legend.x0 - gap_px or ext.x0 >= legend.x1 + gap_px
            )
            if side_by_side or ext.y1 <= legend.y0:
                continue
            needed_px = max(needed_px, legend.y1 + gap_px - base_y)
    if needed_px <= pad_px + 0.5:
        return False
    offset = ScaledTranslation(0.0, needed_px / root.dpi, root.dpi_scale_trans)
    for title in axes_titles(ax).values():
        title.set_transform(ax.transAxes + offset)
    return True
