"""Read the layout's facts from a drawn figure. Nothing here changes it.

An Axes' content is its tight box as matplotlib draws it: tick labels, axis
names, titles, texts, legends, secondary and twin axes, a 3-D cube.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib as mpl
from matplotlib.gridspec import GridSpec
from matplotlib.text import Text

from ..geometry import (
    axes_titles,
    iter_figure_level_extents,
    projection,
    shared_axes,
)
from ..vocab import X, Y
from .model import (
    AxesContent,
    Box,
    Canvas,
    ContentFacts,
    FigureArtist,
    Px,
    Sides,
)

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.transforms import Bbox

    from .given import Neighbours


def grid_of(ax: Axes) -> GridSpec | None:
    """The root GridSpec ``ax`` sits on, if any."""
    spec = ax.get_subplotspec()
    if spec is None:
        return None
    gs = spec.get_topmost_subplotspec().get_gridspec()
    return gs if isinstance(gs, GridSpec) else None


def grid_axes(fig: Figure, gs: GridSpec) -> list[Axes]:
    """Every Axes of ``fig`` on the root GridSpec ``gs``."""
    return [ax for ax in fig.axes if grid_of(ax) is gs]


def unlisted_twin_hosts(fig: Figure) -> list[Axes]:
    """The Axes of ``fig`` with a twin the figure does not list.

    An ``mpl_toolkits`` host (``host_subplot``) keeps its ``twinx`` there,
    as a parasite: it shares an axis and the box, but stays where it was
    made when the host moves, and the host's content box measures it there.
    """
    return [
        ax
        for ax in fig.axes
        if any(
            other not in fig.axes
            and other.get_visible()
            and _same_box(other, ax)
            for which in (X(), Y())
            for other in shared_axes(ax, which)
        )
    ]


def _same_box(a: Axes, b: Axes) -> bool:
    return all(
        abs(p - q) <= 1e-9
        for p, q in zip(
            a.get_position().bounds, b.get_position().bounds, strict=True
        )
    )


def cartesian(ax: Axes) -> bool:
    """A visible rectilinear Axes with its axes on: the only kind fitted."""
    return ax.get_visible() and ax.axison and projection(ax).flat


def box_of(ext: Bbox) -> Box:
    """A matplotlib extent as the layout's :class:`Box`."""
    return Box(float(ext.x0), float(ext.y0), float(ext.x1), float(ext.y1))


def content_box(ax: Axes, renderer: RendererBase) -> Box | None:
    """What of ``ax`` must stay on the canvas; ``None`` for a hidden Axes."""
    tight = ax.get_tightbbox(renderer)
    return None if tight is None else box_of(tight)


def widest_text(ax: Axes, renderer: RendererBase) -> Px:
    """The widest of the titles and the x name of ``ax`` (px)."""
    texts = [*axes_titles(ax).values(), ax.xaxis.label]
    widths = [
        float(t.get_window_extent(renderer).width)
        for t in texts
        if t.get_visible() and t.get_text()
    ]
    return Px(max(widths, default=0.0))


def narrow_box(ax: Axes, renderer: RendererBase) -> Box | None:
    """The content of ``ax`` with its titles and x name one pixel wide."""
    try:
        tight = ax.get_tightbbox(renderer, for_layout_only=True)
    except TypeError:  # mpl_toolkits' host Axes, as matplotlib's own layouts
        tight = ax.get_tightbbox(renderer)
    return None if tight is None else box_of(tight)


def _figure_artist(
    fig: Figure, art: Artist, ext: Bbox, given: Neighbours
) -> FigureArtist:
    vertical = (
        45 <= art.get_rotation() % 180 <= 135 if isinstance(art, Text) else None
    )
    reserve = given.figure_reserve(art)
    gap_pt = reserve.gap_pt if reserve is not None else given.note_gap_pt(art)
    return FigureArtist(
        box_of(ext), vertical, Px((gap_pt or 0.0) * fig.dpi / 72.0)
    )


def canvas(fig: Figure) -> Canvas:
    """The canvas size in display pixels."""
    return Canvas(Px(float(fig.bbox.width)), Px(float(fig.bbox.height)))


def content_facts(
    fig: Figure,
    renderer: RendererBase,
    margins: Sides,
    last: Sides | None,
    given: Neighbours,
) -> ContentFacts:
    """Every Axes' content and the figure-level artists, as drawn now."""
    axes: list[AxesContent] = []
    for ax in fig.axes:
        box = content_box(ax, renderer)
        if box is not None:
            p = ax.get_position()
            position = Sides(float(p.x0), float(p.x1), float(p.y0), float(p.y1))
            widest = widest_text(ax, renderer)
            narrow = narrow_box(ax, renderer) or box
            titled = any(
                t.get_visible() and t.get_text()
                for t in axes_titles(ax).values()
            )
            axes.append(AxesContent(position, box, widest, narrow, titled))
    artists = tuple(
        _figure_artist(fig, art, ext, given)
        for art, ext in iter_figure_level_extents(
            fig, renderer, subfigures=False
        )
        if art.get_in_layout()
    )
    pad = Px(float(mpl.rcParams["axes.titlepad"]) * fig.dpi / 72.0)
    return ContentFacts(tuple(axes), artists, canvas(fig), margins, last, pad)


def content_boxes(fig: Figure, renderer: RendererBase) -> dict[int, Box]:
    """Each visible Axes' content (``id(ax)`` keys)."""
    boxes = {id(ax): content_box(ax, renderer) for ax in fig.axes}
    return {k: b for k, b in boxes.items() if b is not None}
