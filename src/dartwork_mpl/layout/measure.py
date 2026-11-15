"""Read the layout's facts from a drawn figure. Nothing here changes it."""

from __future__ import annotations

import contextlib
import math
from typing import TYPE_CHECKING

from matplotlib.axis import Axis
from matplotlib.gridspec import (
    GridSpec,
    GridSpecBase,
    GridSpecFromSubplotSpec,
    SubplotSpec,
)
from matplotlib.text import Text

from ..edgecase import settle
from ..geometry import (
    BBOX_ERRORS,
    axes_titles,
    iter_figure_level_extents,
    projection,
)
from ..vocab import Bottom, Edge, Left, Top
from . import decide
from .edges import FIT_EDGES
from .model import (
    ArtistId,
    AxesContent,
    Box,
    Canvas,
    ContentFacts,
    Edges,
    FigureArtist,
    Piece,
    PlotSize,
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


def root_grid(
    fig: Figure, gs: GridSpecBase | SubplotSpec | None
) -> GridSpec | None:
    """The root GridSpec under ``gs`` (default: the first Axes')."""
    if gs is None and not fig.axes:
        return None
    found: GridSpecBase | SubplotSpec | None
    if gs is not None:
        found = gs.get_gridspec() if isinstance(gs, SubplotSpec) else gs
    else:
        found = fig.axes[0].get_gridspec()
    if isinstance(found, GridSpecFromSubplotSpec):
        found = found.get_topmost_subplotspec().get_gridspec()
    return found if isinstance(found, GridSpec) else None


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


def cartesian(ax: Axes) -> bool:
    """A visible rectilinear Axes with its axes on: the only kind fitted."""
    return ax.get_visible() and ax.axison and projection(ax).flat


# -- one step -----------------------------------------------------------------


def box_of(ext: Bbox) -> Box:
    """A matplotlib extent as the layout's :class:`Box`."""
    return Box(float(ext.x0), float(ext.y0), float(ext.x1), float(ext.y1))


def _measurable(ext: Bbox) -> bool:
    """A finite, non-empty extent (text at infinity has a NaN width)."""
    finite = all(math.isfinite(v) for v in ext.extents)
    return finite and ext.width > 0 and ext.height > 0


def _across(owner: Axes, value: float, box: Bbox, along_x: bool) -> bool:
    """Whether a tick sits across ``box`` (0.5 px slack): a reciprocal
    secondary axis puts ticks in view but far off the canvas."""
    if along_x:
        place = owner.get_xaxis_transform().transform([(value, 0.0)])[0][0]
        return bool(box.x0 - 0.5 <= place <= box.x1 + 0.5)
    place = owner.get_yaxis_transform().transform([(0.0, value)])[0][1]
    return bool(box.y0 - 0.5 <= place <= box.y1 + 0.5)


def _texts(owner: Axes, renderer: RendererBase) -> list[Piece]:
    """Texts, the three titles and both axis names."""
    pieces: list[Piece] = []
    labels = (owner.xaxis.label, owner.yaxis.label)
    for text in (*owner.texts, *axes_titles(owner).values(), *labels):
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            ext = text.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if _measurable(ext):
            pieces.append(Piece(box_of(ext)))
    return pieces


def _ticks(owner: Axes, renderer: RendererBase) -> list[Piece]:
    """Labels of ticks in view and across the plot; offset texts."""
    pieces: list[Piece] = []
    for axis in (owner.xaxis, owner.yaxis):
        vmin, vmax = sorted(axis.get_view_interval())
        tol = abs(vmax - vmin) * 1e-5
        along_x = axis is owner.xaxis
        try:
            box = owner.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        for tick in axis.get_ticklabels():
            if not tick.get_visible() or not tick.get_text().strip():
                continue
            try:
                ext = tick.get_window_extent(renderer)
                pos = tick.get_position()
            except BBOX_ERRORS:
                continue
            value = pos[0] if along_x else pos[1]
            if value < vmin - tol or value > vmax + tol:
                continue
            if _measurable(ext) and _across(owner, value, box, along_x):
                pieces.append(Piece(box_of(ext)))
        offset = axis.get_offset_text()
        if offset.get_visible() and offset.get_text().strip():
            with contextlib.suppress(*BBOX_ERRORS):
                ext = offset.get_window_extent(renderer)
                if _measurable(ext):
                    pieces.append(Piece(box_of(ext)))
    return pieces


def _tight_3d(ax: Axes, renderer: RendererBase) -> tuple[Piece, ...]:
    """A 3-D Axes' axes, legend, titles and 2-D texts by their tight boxes
    (a ``Text3D`` has none, as matplotlib's own layouts find)."""
    pieces: list[Piece] = []
    # Its x, y and z axes: a 3-D Axes lists the z axis among its children.
    axes = {id(c): c for c in ax.get_children() if isinstance(c, Axis)}
    for artist in (*axes.values(), ax.get_legend()):
        if artist is None or not artist.get_visible():
            continue
        with contextlib.suppress(*BBOX_ERRORS):
            bb = artist.get_tightbbox(renderer)
            if bb is not None and bb.width > 0 and bb.height > 0:
                pieces.append(Piece(box_of(bb)))
    for text in (*axes_titles(ax).values(), *ax.texts):
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            ext = text.get_tightbbox(renderer)
        except BBOX_ERRORS:
            continue
        if ext is not None and ext.width > 0 and ext.height > 0:
            pieces.append(Piece(box_of(ext)))
    return tuple(pieces)


def axes_content(
    ax: Axes, renderer: RendererBase, given: Neighbours
) -> AxesContent | None:
    """What of ``ax`` must stay on the canvas; ``None`` for a hidden Axes."""
    if not ax.get_visible():
        return None
    p = ax.get_position()
    position = Sides(float(p.x0), float(p.x1), float(p.y0), float(p.y1))
    try:
        window = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        window = None
    plot = None
    if window is not None and window.width > 0 and window.height > 0:
        plot = box_of(window)
    if projection(ax).spatial:
        if window is None:
            return None
        return AxesContent(plot, position, (), _tight_3d(ax, renderer))
    pieces = [*_texts(ax, renderer), *_ticks(ax, renderer)]
    legend = ax.get_legend()
    if legend is not None and legend.get_visible():
        with contextlib.suppress(*BBOX_ERRORS):
            ext = legend.get_window_extent(renderer)
            if ext.width > 0 and ext.height > 0:
                pieces.append(Piece(box_of(ext), given.outside_edge(legend)))
    return AxesContent(plot, position, tuple(pieces))


def _roles(fig: Figure) -> dict[int, Edge]:
    """The edge each of ``fig``'s suptitle, supxlabel and supylabel holds,
    by ``id`` of the text in ``fig.texts`` that writes it.

    matplotlib names these texts only by what they write
    (``get_suptitle`` and so on); the first text writing it is taken.
    """
    roles: dict[int, Edge] = {}
    for written, edge in (
        (fig.get_suptitle(), Top()),
        (fig.get_supxlabel(), Bottom()),
        (fig.get_supylabel(), Left()),
    ):
        found = next((t for t in fig.texts if t.get_text() == written), None)
        if written and found is not None:
            roles.setdefault(id(found), edge)
    return roles


def _figure_artist(
    fig: Figure,
    roles: dict[int, Edge],
    art: Artist,
    ext: Bbox,
    given: Neighbours,
) -> FigureArtist:
    vertical = (
        45 <= art.get_rotation() % 180 <= 135 if isinstance(art, Text) else None
    )
    reserve = given.figure_reserve(art)
    if reserve is not None:
        side, gap_pt = reserve.edge, reserve.gap_pt
    else:
        side, gap_pt = None, given.note_gap_pt(art) or 0.0
    return FigureArtist(
        box_of(ext),
        roles.get(id(art)),
        vertical,
        side,
        Px(gap_pt * fig.dpi / 72.0),
    )


def canvas(fig: Figure) -> Canvas:
    """The canvas size in display pixels."""
    return Canvas(Px(float(fig.bbox.width)), Px(float(fig.bbox.height)))


def content_facts(
    fig: Figure,
    renderer: RendererBase,
    margins: Sides,
    last: Edges | None,
    given: Neighbours,
) -> ContentFacts:
    """Every Axes' content and the figure-level artists, as drawn now."""
    contents = [axes_content(ax, renderer, given) for ax in fig.axes]
    roles = _roles(fig)
    artists = tuple(
        _figure_artist(fig, roles, art, ext, given)
        for art, ext in iter_figure_level_extents(
            fig, renderer, subfigures=False
        )
        if art.get_in_layout()
    )
    axes = tuple(c for c in contents if c is not None)
    return ContentFacts(axes, artists, canvas(fig), margins, last)


def content_boxes(
    fig: Figure, renderer: RendererBase, given: Neighbours
) -> dict[int, Box]:
    """Each visible Axes' content as the margins see it (``id(ax)`` keys)."""
    boxes: dict[int, Box] = {}
    for ax in fig.axes:
        content = axes_content(ax, renderer, given)
        if content is None:
            continue
        nil = Sides(0.0, 0.0, 0.0, 0.0)
        facts = ContentFacts((content,), (), canvas(fig), nil, None)
        fit = settle(facts, decide.fit(facts), FIT_EDGES).plan
        box = decide.content_box(fit.axes[0])
        if box is not None:
            boxes[id(ax)] = box
    return boxes


def plot_sizes(fig: Figure, renderer: RendererBase) -> dict[ArtistId, PlotSize]:
    """Each visible Axes' plot box size."""
    sizes: dict[ArtistId, PlotSize] = {}
    for ax in fig.axes:
        if ax.get_visible():
            box = ax.get_window_extent(renderer)
            size = PlotSize(Px(float(box.width)), Px(float(box.height)))
            sizes[ArtistId(id(ax))] = size
    return sizes
