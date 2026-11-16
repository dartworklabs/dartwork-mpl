"""Draw the Axes legends the decisions plan, and the layout's legend hooks.

A legend ``place_legend`` built has a :class:`Placed` in this module's
registry. The layout places it again at the size it settles on while it
keeps the anchor box the library gave it; a legend the caller anchored
elsewhere (``set_bbox_to_anchor``) or rebuilt (``ax.legend``) is the
caller's. The registry holds its legends weakly.
"""

from __future__ import annotations

import logging
import weakref
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, assert_never

import matplotlib as mpl
from matplotlib.font_manager import FontProperties
from matplotlib.legend import Legend
from matplotlib.transforms import ScaledTranslation

from ..geometry import (
    BBOX_ERRORS,
    axes_titles,
    get_renderer,
    same_position_axes,
)
from ..hidden import axes_name
from ..vocab import Edge, edge_of
from . import decide, measure
from .ink import box_of, data_ink, px
from .measure import Given, Handle
from .model import (
    INSIDE,
    Above,
    Below,
    Best,
    Clearance,
    Columns,
    InsideFacts,
    Left,
    Right,
    Side,
    SideFacts,
    Size,
    Spot,
    parse_loc,
    refuse_anchor,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.transforms import BboxBase


@dataclass
class Placed:
    """What a ``place_legend`` legend was placed from, and where it went.

    ``given`` holds the entries the caller passed. ``box`` is the anchor
    box the library left it on, ``size`` the Axes
    size (half px) an outside legend was last fitted at. ``chosen`` is the
    spot ``place_legend`` gave an inside legend, ``spot`` the one it has
    now; ``lift`` how far a layout last raised the titles (pt).
    """

    where: Best | Side
    asked: Columns | None
    given: Given
    kw: dict[str, object]
    box: BboxBase
    size: tuple[int, int] = (0, 0)
    columns: Columns | None = None
    clearance: Clearance | None = None
    chosen: Spot | None = None
    spot: Spot | None = None
    lift: float | None = None


LOG = logging.getLogger("dartwork_mpl.legend")

_PLACED: weakref.WeakKeyDictionary[Legend, Placed] = weakref.WeakKeyDictionary()


def pad_px(legend: Legend, renderer: RendererBase) -> float:
    """The legend's ``borderaxespad`` in display px."""
    return legend.borderaxespad * px(renderer, legend.prop.get_size_in_points())


def size_of(legend: Legend, renderer: RendererBase) -> Size:
    """The drawn size of ``legend``, display px."""
    bb = legend.get_window_extent(renderer)
    return Size(float(bb.width), float(bb.height))


def fit(
    size: Callable[[Columns], Size],
    side: Side,
    count: int,
    length: float,
    asked: Columns | None,
) -> Columns:
    """The column count a legend outside ``side`` takes along ``length``."""
    return decide.columns(SideFacts(side, count, length, asked, size))


def _kept(legend: Legend | None) -> dict[str, object]:
    """The title, frame and font size a rebuilt legend repeats."""
    kept: dict[str, object] = {}
    if legend is None:
        return kept
    if legend.get_title().get_text():
        kept["title"] = legend.get_title().get_text()
    if legend.get_frame_on() != mpl.rcParams["legend.frameon"]:
        kept["frameon"] = legend.get_frame_on()
    size = legend.prop.get_size_in_points()
    default = FontProperties(size=mpl.rcParams["legend.fontsize"])
    if size != default.get_size_in_points():
        kept["fontsize"] = size
    return kept


def place_legend(
    ax: Axes,
    loc: str,
    asked: Columns | None,
    given: Given,
    kw: dict[str, object],
) -> Legend | None:
    """Place the legend of ``ax`` (:func:`dartwork_mpl.legend.place_legend`)."""
    where = parse_loc(loc)
    refuse_anchor(where, kw)
    host, handles, labels = measure.entries(ax, given)
    olds = [o.get_legend() for o in same_position_axes(ax)]
    kept = _kept(host.get_legend() or next((o for o in olds if o), None))
    for old in olds:
        if old is not None and (handles or old in _PLACED):
            old.remove()
    if not handles:
        return None
    root = host.get_figure(root=True)
    if root is None:
        raise ValueError("place_legend needs an Axes on a Figure")
    root.canvas.draw()  # pyright: ignore[reportUnknownMemberType]
    renderer = get_renderer(root)
    placed = Placed(where, asked, given, kept | kw, host.bbox)
    legend = _draw(host, handles, labels, placed, renderer)
    placed.chosen = placed.spot
    _say_gathered(host)
    return legend


def _say_gathered(host: Axes) -> None:
    """Say so when the legend took the entries of more than one twin."""
    if not LOG.isEnabledFor(logging.INFO):
        return
    twins = same_position_axes(host)
    parent = host.get_figure(root=False)
    order = list(parent.axes) if parent is not None else twins
    owners = [
        o for o in order if o in twins and o.get_legend_handles_labels()[1]
    ]
    if len(owners) < 2:
        return
    LOG.info(
        "gathered the entries of %s into one legend on %s: twins share one "
        "box, and a legend on the lower twin is drawn under the other's "
        "data; call ax.legend() on each twin to keep one legend each",
        " and ".join(axes_name(o) for o in owners),
        axes_name(host),
    )


def _draw(
    ax: Axes,
    handles: Sequence[Handle],
    labels: Sequence[str],
    placed: Placed,
    renderer: RendererBase,
) -> Legend:
    """Build the legend ``placed`` describes on ``ax`` and record it."""

    def build(spot: Spot, columns: Columns) -> Legend:
        return ax.legend(  # pyright: ignore[reportUnknownMemberType]
            handles, labels, loc=spot.code, ncols=columns.n, **placed.kw
        )

    match placed.where:
        case Best():
            legend = build(INSIDE[0], placed.asked or Columns(1))
            _settle_inside(ax, legend, placed, renderer)
        case Above() | Below() | Right() | Left() as side:
            columns = fit(
                lambda c: size_of(build(side.legend_loc, c), renderer),
                side,
                len(labels),
                _length(ax, side, renderer),
                placed.asked,
            )
            legend = build(side.legend_loc, columns)
            placed.columns = columns
            placed.size = _size_key(ax, renderer)
            placed.clearance = None
            _anchor(legend, ax, side, placed, renderer)
        case _:
            assert_never(placed.where)
    placed.box = legend.get_bbox_to_anchor()
    _PLACED[legend] = placed
    return legend


def _length(ax: Axes, side: Side, renderer: RendererBase) -> float:
    box = ax.get_window_extent(renderer)
    return float(box.width if side.across else box.height)


def _size_key(ax: Axes, renderer: RendererBase) -> tuple[int, int]:
    box = ax.get_window_extent(renderer)
    return (round(box.width * 2), round(box.height * 2))


def _settle_inside(
    ax: Axes, legend: Legend, placed: Placed, renderer: RendererBase
) -> bool:
    """Put ``legend`` at the first spot clear of the data; whether it moved."""
    before = legend.get_window_extent(renderer)
    facts = InsideFacts(
        size=size_of(legend, renderer),
        parent=box_of(legend.get_bbox_to_anchor()),
        axes=box_of(ax.get_window_extent(renderer)),
        pad=pad_px(legend, renderer),
        meets=data_ink(ax, renderer).meets,
    )
    placed.spot = decide.inside(facts)
    legend.set_loc(placed.spot.code)
    after = legend.get_window_extent(renderer)
    return abs(after.x0 - before.x0) + abs(after.y0 - before.y0) > 0.01


def _anchor(
    legend: Legend, ax: Axes, side: Side, placed: Placed, renderer: RendererBase
) -> bool:
    """Anchor ``legend`` at the middle of ``side``, past the labels there.

    The offset is physical, so it holds when the Axes is resized. Returns
    whether it moved by more than 0.01 pt.
    """
    root = ax.get_figure(root=True)
    if root is None:
        return False
    try:
        labels = measure.decorations(ax, renderer)
        axes = box_of(ax.get_window_extent(renderer))
    except BBOX_ERRORS:
        return False
    pt = decide.clearance(axes, side, labels).px * 72.0 / root.dpi
    if placed.clearance is not None and abs(placed.clearance.px - pt) <= 0.01:
        return False
    out = pt / 72.0
    step = (0.0, out) if side.across else (out, 0.0)
    sign = 1.0 if side.far else -1.0
    offset = ScaledTranslation(
        sign * step[0], sign * step[1], root.dpi_scale_trans
    )
    legend.set_bbox_to_anchor(side.figure_loc.anchor, ax.transAxes + offset)
    placed.clearance = Clearance(pt)
    placed.box = legend.get_bbox_to_anchor()
    return True


def _left_there(legend: Legend, spot: Spot, renderer: RendererBase) -> bool:
    """Whether ``legend`` sits at ``spot`` in its anchor box, where matplotlib
    puts a ``loc`` of that name: not moved since (``set_loc``)."""
    box = legend.get_window_extent(renderer)
    container = legend.get_bbox_to_anchor().padded(-pad_px(legend, renderer))
    fx, fy = spot.anchor
    x0 = container.x0 + fx * (container.width - box.width)
    y0 = container.y0 + fy * (container.height - box.height)
    return abs(box.x0 - x0) + abs(box.y0 - y0) < 1.0


def _lift_titles(
    ax: Axes, legend: Legend, placed: Placed, renderer: RendererBase
) -> bool:
    """Raise the titles of ``ax`` over a legend above it; whether they moved."""
    root = ax.get_figure(root=True)
    facts = measure.titles(ax, renderer)
    if root is None or facts is None:
        return False
    lift = decide.title_lift(box_of(legend.get_window_extent(renderer)), facts)
    if lift is None:
        return False
    placed.lift = lift.px * 72.0 / root.dpi
    offset = ScaledTranslation(0.0, lift.px / root.dpi, root.dpi_scale_trans)
    for title in axes_titles(ax).values():
        title.set_transform(ax.transAxes + offset)
    return True


def _again(
    ax: Axes, legend: Legend, placed: Placed, renderer: RendererBase
) -> bool:
    """Place ``legend`` again at the size ``ax`` has now; whether it moved."""
    match placed.where:
        case Best():
            if placed.spot is not None and not _left_there(
                legend, placed.spot, renderer
            ):
                return False  # the caller moved it (set_loc)
            return _settle_inside(ax, legend, placed, renderer)
        case Above() | Below() | Right() | Left() as side:
            if _size_key(ax, renderer) == placed.size:
                return _anchor(legend, ax, side, placed, renderer)
            host, handles, labels = measure.entries(ax, placed.given)
            if host is not ax or not handles:
                return False
            before = (placed.columns, placed.clearance)
            _draw(ax, handles, labels, placed, renderer)
            return (placed.columns, placed.clearance) != before
        case _:
            assert_never(placed.where)


def settle(
    fig: Figure, renderer: RendererBase, axes: Sequence[Axes] | None = None
) -> bool:
    """``dm.place_legend``'s legends at the size their Axes have now.

    An inside legend takes the spot clear of the data now; one outside a
    side refits its rows and sits past that side's labels; titles rise over
    a legend above their Axes. Returns whether anything moved.
    """
    moved = False
    for ax in list(fig.axes if axes is None else axes):
        legend = ax.get_legend()
        placed = None if legend is None else _PLACED.get(legend)
        if legend is None or placed is None:
            continue
        if legend.get_bbox_to_anchor() is not placed.box:
            continue  # the caller anchored it elsewhere
        moved = _again(ax, legend, placed, renderer) or moved
        legend = ax.get_legend()
        if legend is not None and isinstance(placed.where, Above):
            moved = _lift_titles(ax, legend, placed, renderer) or moved
    return moved


def report_legends(fig: Figure) -> None:
    """Say what the last :func:`settle` changed: an inside legend on another
    spot than ``place_legend`` chose, titles raised over a legend above."""
    if not LOG.isEnabledFor(logging.INFO):
        return
    for ax in fig.axes:
        legend = ax.get_legend()
        placed = None if legend is None else _PLACED.get(legend)
        if placed is None:
            continue
        if placed.spot != placed.chosen:
            LOG.info(
                "moved the legend of %s from the %s to the %s: at the size "
                "the layout gave the Axes it covered data there; place it "
                "with ax.legend(loc=...) instead of dm.place_legend to keep "
                "it where you put it",
                axes_name(ax),
                placed.chosen.code if placed.chosen else "-",
                placed.spot.code if placed.spot else "-",
            )
        if placed.lift is not None:
            LOG.info(
                "raised the titles of %s %.1f pt over its legend above: the "
                'legend sat on them; use loc="below" or a figure legend to '
                "keep the titles where they are",
                axes_name(ax),
                placed.lift,
            )


def outside_edge(legend: Legend) -> Edge | None:
    """The edge of its Axes the library anchored ``legend`` outside of."""
    placed = _PLACED.get(legend)
    if placed is None or isinstance(placed.where, Best):
        return None
    return edge_of(across=placed.where.across, far=placed.where.far)
