"""Draw the legends the decisions plan, and the layout's legend hooks.

A legend ``place_legend`` built has a :class:`Record` in this module's
registry: what it was placed from and where. The layout places it again at
the size it settles on only while it still sits where the library put it; a
legend the caller moved (``set_loc``, ``set_bbox_to_anchor``) is the
caller's. A figure legend ``figure_legend`` placed has a :class:`Reserve`:
the figure edge it holds and the room the layout keeps from it.

The registries hold their legends weakly, and a record names its handles
by identity (found again on the Axes when the legend is rebuilt), so a
closed figure is freed with its legends.
"""

from __future__ import annotations

import weakref
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Unpack, assert_never

import matplotlib as mpl
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.legend import Legend
from matplotlib.transforms import Bbox, ScaledTranslation

from ..edgecase import settle as settle_edges
from ..geometry import (
    BBOX_ERRORS,
    axes_titles,
    figure_axes,
    figure_legends,
    get_renderer,
    same_position_axes,
)
from . import decide, measure
from .edges import ENTRY_EDGES, TITLE_EDGES
from .measure import LegendKeywords
from .model import (
    Anchor,
    AskedLoc,
    Best,
    Columns,
    Entries,
    Inside,
    Keywords,
    LegendPlan,
    Loc,
    MatplotlibLoc,
    Outside,
    Passed,
    Request,
    Reserve,
    Side,
    parse_keywords,
    parse_loc,
)

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.legend_handler import HandlerBase
    from matplotlib.transforms import BboxBase


#: How far (px) a legend may sit from its spot and still be where it was put.
SPOT_PX = 0.01


@dataclass
class Record:
    """What a ``place_legend`` legend was placed from, and where it was put.

    ``plan`` is ``None`` for a matplotlib ``loc`` passed through; ``size``
    the Axes size (half px) and span it was last decided at; ``box`` the
    anchor box the library left the legend on; ``outside`` the
    side the library anchored it outside of. ``handles`` are the ``id`` of
    each handle, in entry order: a record holding the artists themselves
    would keep its legend, and with it the figure, alive.
    """

    request: Request
    handles: tuple[int, ...]
    entries: Entries
    kw: LegendKeywords
    plan: LegendPlan | None
    size: tuple[int, ...] = ()
    pad: float = 0.0
    box: BboxBase | None = None
    anchor: Anchor | None = None
    outside: Side | None = None


def _record(
    request: Request,
    handles: Sequence[Artist],
    entries: Entries,
    kw: LegendKeywords,
    plan: LegendPlan | None,
) -> Record:
    ids = tuple(id(h) for h in handles)
    return Record(request, ids, entries, kw, plan)


def handles_of(ax: Axes, record: Record) -> list[Artist] | None:
    """``record``'s handles, as ``ax`` and its twins hold them now.

    ``None`` when one is gone or no longer carries its entry's name.
    """
    found: dict[int, tuple[Artist, str]] = {}
    for owner in same_position_axes(ax):
        hs, labels = owner.get_legend_handles_labels()
        for handle, label in zip(hs, labels, strict=True):
            found[id(handle)] = (handle, label)
    handles: list[Artist] = []
    for key, name in zip(record.handles, record.entries.labels, strict=True):
        handle, label = found.get(key, (None, None))
        if handle is None or label != name:
            return None
        handles.append(handle)
    return handles


_RECORDS: weakref.WeakKeyDictionary[Legend, Record] = (
    weakref.WeakKeyDictionary()
)
_RESERVES: weakref.WeakKeyDictionary[Legend, Reserve] = (
    weakref.WeakKeyDictionary()
)


def record_of(legend: Legend | None, renderer: RendererBase) -> Record | None:
    """The record of a legend the library placed and the caller has not moved."""
    record = None if legend is None else _RECORDS.get(legend)
    if legend is None or record is None:
        return None
    return record if _still_at(legend, record, renderer) else None


def _spot(plan: LegendPlan) -> Loc:
    """The spot of its anchor box a plan puts the legend at."""
    match plan:
        case Inside(loc=spot):
            return spot
        case Outside(side=side):
            return side.legend_loc
        case _:
            assert_never(plan)


def _still_at(legend: Legend, record: Record, renderer: RendererBase) -> bool:
    """Whether ``legend`` keeps the anchor box and spot the library gave it.

    A caller's ``set_loc``, ``set_bbox_to_anchor`` or drag moves it off
    the spot, which is read from where it draws: matplotlib keeps the
    ``loc`` itself private. A ``loc`` passed through is followed by its
    anchor box only.
    """
    box = legend.get_bbox_to_anchor()
    if box is not record.box:
        return False
    if record.plan is None:
        return True
    # The stub types ``points_to_pixels`` as any array; it scales a number.
    size_px = np.asarray(
        renderer.points_to_pixels(legend.prop.get_size_in_points()),
        dtype=np.float64,
    )
    pad = legend.borderaxespad * float(size_px)
    drawn = legend.get_window_extent(renderer)
    spot = Bbox.from_bounds(0.0, 0.0, drawn.width, drawn.height).anchored(
        _spot(record.plan).anchor, container=box.padded(-pad)
    )
    return (
        abs(drawn.x0 - spot.x0) <= SPOT_PX
        and abs(drawn.y0 - spot.y0) <= SPOT_PX
    )


def _remember(legend: Legend, record: Record) -> Legend:
    record.box = legend.get_bbox_to_anchor()
    _RECORDS[legend] = record
    return legend


def _new_legend(
    owner: Axes | Figure | SubFigure,
    handles: Sequence[Artist],
    labels: Sequence[str],
    *,
    loc: MatplotlibLoc,
    ncols: int = 1,
    **kw: Unpack[LegendKeywords],
) -> Legend:
    """``owner.legend(...)`` with the keywords :class:`LegendKeywords` types."""
    return owner.legend(handles, labels, loc=loc, ncols=ncols, **kw)  # pyright: ignore[reportUnknownMemberType]


# ----------------------------------------------------------------- anchor
def anchor_outside(
    legend: Legend, ax: Axes, side: Side, renderer: RendererBase
) -> bool:
    """Anchor ``legend`` at the middle of ``side`` of ``ax``, past its labels.

    The offset is physical, so the legend keeps its distance when the Axes
    is resized. Returns whether the anchor moved by more than 0.01 pt.
    """
    root = ax.get_figure(root=True)
    if root is None:
        return False
    try:
        facts = measure.anchor_facts(ax, side, renderer)
    except BBOX_ERRORS:
        return False
    plan = Anchor(decide.anchor(facts).clearance * 72.0 / root.dpi)
    record = _RECORDS.get(legend)
    if record is None:
        return False
    previous = record.anchor
    if (
        previous is not None
        and record.outside == side
        and abs(previous.clearance - plan.clearance) <= 0.01
    ):
        return False
    (dx, dy), out = side.outward, plan.clearance / 72.0
    offset = ScaledTranslation(dx * out, dy * out, root.dpi_scale_trans)
    legend.set_bbox_to_anchor(side.middle, ax.transAxes + offset)
    record.anchor, record.outside = plan, side
    _remember(legend, record)
    return True


# ------------------------------------------------------------------ draw
def _half_px(
    ax: Axes, renderer: RendererBase, plan: LegendPlan, pad: float
) -> tuple[int, ...]:
    """The Axes' size (and an outside legend's span) in half-px steps."""
    box = ax.get_window_extent(renderer)
    key = [round(box.width * 2), round(box.height * 2)]
    if isinstance(plan, Outside):
        key.append(round(measure.span(ax, plan.side, renderer, pad).length * 2))
    return tuple(key)


def draw(
    ax: Axes,
    record: Record,
    handles: list[Artist],
    plan: LegendPlan,
    renderer: RendererBase,
) -> Legend:
    """Draw ``record``'s legend on ``ax`` as ``plan`` says and record it."""
    match plan:
        case Inside(loc=spot):
            loc, labels = spot, record.entries.labels
        case Outside(side=side, entries=entries):
            loc, labels = side.legend_loc, entries.labels
        case _:
            assert_never(plan)
    legend = _new_legend(
        ax,
        handles,
        list(labels),
        loc=loc.code,
        ncols=plan.columns.n,
        **record.kw,
    )
    record = replace(record, plan=plan, anchor=None, outside=None)
    _remember(legend, record)
    if isinstance(plan, Outside):
        anchor_outside(legend, ax, plan.side, renderer)
    return legend


def decide_for(
    ax: Axes,
    record: Record,
    handles: list[Artist],
    renderer: RendererBase,
    current: LegendPlan | None = None,
) -> LegendPlan:
    """Decide where ``record``'s legend of ``handles`` goes on ``ax``."""
    facts = measure.legend_facts(
        ax,
        handles,
        record.entries,
        record.request,
        record.kw,
        renderer,
        current,
    )
    record.pad = facts.pad
    return decide.place(facts)


def _same_place(a: LegendPlan, b: LegendPlan) -> bool:
    if isinstance(a, Inside) and isinstance(b, Inside):
        return (a.loc, a.columns) == (b.loc, b.columns)
    if isinstance(a, Outside) and isinstance(b, Outside):
        return (a.side, a.columns, a.entries) == (b.side, b.columns, b.entries)
    return False


def _kept_settings(legend: Legend | None) -> LegendKeywords:
    """The title, frame, font size and handlers a rebuilt legend repeats."""
    kept = LegendKeywords()
    if legend is None:
        return kept
    if legend.get_title().get_text():
        kept["title"] = legend.get_title().get_text()
    if legend.get_frame_on() != mpl.rcParams["legend.frameon"]:
        kept["frameon"] = legend.get_frame_on()
    size = legend.prop.get_size_in_points()
    if (
        size
        != FontProperties(
            size=mpl.rcParams["legend.fontsize"]
        ).get_size_in_points()
    ):
        kept["fontsize"] = size
    defaults = Legend.get_default_handler_map()
    custom: dict[Artist | type, HandlerBase] = {
        k: h
        for k, h in legend.get_legend_handler_map().items()
        if defaults.get(k) is not h
    }
    if custom:
        kept["handler_map"] = custom
    return kept


def place_legend(
    ax: Axes, loc: AskedLoc, columns: Columns | None, kw: LegendKeywords
) -> Legend | None:
    """Place the legend of ``ax`` (:func:`dartwork_mpl.legend.place_legend`)."""
    owners = same_position_axes(ax)
    facts, handles = measure.entry_facts(owners, ax)
    plan = settle_edges(facts, decide.entries(facts), ENTRY_EDGES).plan
    host = owners[plan.host]
    old = host.get_legend()
    if not plan.picks:
        if old is not None and old in _RECORDS:
            old.remove()
        return None
    picked = [handles[i][j] for i, j in plan.picks]
    entries = Entries(
        tuple(facts.owners[i].entries.labels[j] for i, j in plan.picks)
    )
    source = old or next(
        (o.get_legend() for o in owners if o.get_legend()), None
    )
    keywords = parse_keywords(kw, _kept_settings(source), columns)
    placement = parse_loc(loc)
    if isinstance(placement, Side):
        _refuse_anchor("place_legend", loc, keywords)
    for i in plan.remove:
        if (partner := owners[i].get_legend()) is not None:
            partner.remove()
    if old is not None:
        old.remove()
    anchored = keywords.anchored
    match placement:
        case Passed(loc=raw):
            legend = _new_legend(
                host,
                picked,
                list(entries.labels),
                loc=raw,
                ncols=1 if columns is None else columns.n,
                **keywords.rest,
            )
            request = Request(None, columns, anchored)
            return _remember(
                legend, _record(request, picked, entries, keywords.rest, None)
            )
        case Best():
            request = Request(None, columns, anchored)
        case Side():
            request = Request(placement, columns, anchored)
        case _:
            assert_never(placement)
    record = _record(request, picked, entries, keywords.rest, None)
    root = host.get_figure(root=True)
    if root is None:
        raise ValueError("place_legend needs an Axes on a Figure")
    root.canvas.draw()  # pyright: ignore[reportUnknownMemberType]
    renderer = get_renderer(root)
    spot = decide_for(host, record, picked, renderer)
    return draw(host, record, picked, spot, renderer)


def _refuse_anchor(
    name: str, loc: AskedLoc, keywords: Keywords[LegendKeywords]
) -> None:
    """A named side anchors the legend itself: a caller anchor is an error."""
    if keywords.anchor is not None:
        raise ValueError(
            f"{name}(loc={loc!r}) anchors the legend itself; "
            f"remove {keywords.anchor}= or pass a matplotlib loc instead"
        )


# ------------------------------------------------------------ layout hooks
def _again(
    ax: Axes, legend: Legend, record: Record, renderer: RendererBase
) -> bool:
    """Place a legend again at the size its Axes has now; whether it moved."""
    plan = record.plan
    if plan is None:
        return False
    try:
        size = _half_px(ax, renderer, plan, record.pad)
    except BBOX_ERRORS:
        return False
    if size == record.size:
        return False
    record.size = size
    handles = handles_of(ax, record)
    if handles is None:
        return False
    new = decide_for(ax, record, handles, renderer, current=plan)
    if _same_place(new, plan):
        return False
    rebuilt = record_of(draw(ax, record, handles, new, renderer), renderer)
    if rebuilt is not None:
        rebuilt.size = _half_px(ax, renderer, new, record.pad)
    return True


def _lift_titles(ax: Axes, renderer: RendererBase) -> bool:
    facts = measure.title_facts(ax, renderer)
    if facts is None:
        return False
    plan = settle_edges(facts, decide.title_pad(facts), TITLE_EDGES).plan
    root = ax.get_figure(root=True)
    if plan.px is None or root is None:
        return False
    offset = ScaledTranslation(0.0, plan.px / root.dpi, root.dpi_scale_trans)
    for title in axes_titles(ax).values():
        title.set_transform(ax.transAxes + offset)
    return True


def settle(
    fig: Figure, renderer: RendererBase, axes: Sequence[Axes] | None = None
) -> bool:
    """Legends at the Axes size now, then titles lifted over legends above them.

    ``dm.place_legend``'s legends on ``axes`` (every Axes when ``None``) are
    placed again at the size those Axes have now (inwards only); one anchored
    outside a side moves past that side's labels; a title never sits on a
    legend above its Axes. Returns whether anything moved.
    """
    moved = False
    for ax in list(fig.axes if axes is None else axes):
        legend = ax.get_legend()
        record = record_of(legend, renderer)
        if (
            legend is not None
            and record is not None
            and _again(ax, legend, record, renderer)
        ):
            moved = True
    for ax in fig.axes:
        legend = ax.get_legend()
        side = outside_side(legend)
        if (
            legend is not None
            and side is not None
            and record_of(legend, renderer) is not None
            and anchor_outside(legend, ax, side, renderer)
        ):
            moved = True
    for ax in fig.axes:
        if _lift_titles(ax, renderer):
            moved = True
    return moved


def outside_side(legend: Legend | None) -> Side | None:
    """The side the library anchored ``legend`` outside of, or ``None``."""
    record = None if legend is None else _RECORDS.get(legend)
    return None if record is None else record.outside


def figure_reserve(artist: Artist) -> Reserve | None:
    """The edge a ``figure_legend`` legend holds and its gap, else ``None``."""
    return _RESERVES.get(artist) if isinstance(artist, Legend) else None


# ---------------------------------------------------------- figure legends
def figure_legend(
    fig: Figure | SubFigure,
    loc: AskedLoc,
    columns: Columns | None,
    kw: LegendKeywords,
) -> Legend | None:
    """One legend for ``fig``'s panels (:func:`dartwork_mpl.legend.figure_legend`)."""
    handles: list[Artist] = []
    labels: list[str] = []
    for ax in figure_axes(fig):
        for handle, label in zip(*ax.get_legend_handles_labels(), strict=True):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    names = set(labels)
    replaced = [
        legend
        for ax in figure_axes(fig)
        if (legend := ax.get_legend()) is not None
        and set(_names(legend)) <= names
    ]
    replaced += [lg for lg in figure_legends(fig) if lg in _RESERVES]
    if not handles:
        for legend in replaced:
            legend.remove()
        return None
    placement = parse_loc(loc)
    match placement:
        case Passed(loc=raw):
            legend = _new_legend(
                fig,
                handles,
                labels,
                loc=raw,
                ncols=1 if columns is None else columns.n,
                **kw,
            )
        case Best():
            legend = _placed_figure_legend(
                fig, handles, labels, None, loc, columns, kw
            )
        case Side():
            legend = _placed_figure_legend(
                fig, handles, labels, placement, loc, columns, kw
            )
        case _:
            assert_never(placement)
    for old in replaced:
        old.remove()
    return legend


def _placed_figure_legend(
    fig: Figure | SubFigure,
    handles: list[Artist],
    labels: list[str],
    side: Side | None,
    loc: AskedLoc,
    columns: Columns | None,
    kw: LegendKeywords,
) -> Legend:
    """The figure legend on ``side`` (``None``: the side that fits)."""
    keywords = parse_keywords(kw, LegendKeywords(), columns)
    _refuse_anchor("figure_legend", loc, keywords)
    renderer = get_renderer(fig)
    entries = Entries(tuple(labels))
    request = Request(side, keywords.columns)
    facts = measure.figure_facts(
        fig, handles, entries, request, keywords.rest, renderer
    )
    plan = decide.figure_place(facts)
    legend = _new_legend(
        fig,
        handles,
        labels,
        loc=plan.side.figure_loc.code,
        ncols=plan.columns.n,
        **(
            keywords.rest
            | LegendKeywords(
                bbox_to_anchor=plan.anchor, bbox_transform=fig.transSubfigure
            )
        ),
    )
    # simple_layout keeps this gap between the legend and the panels.
    gap = float(legend.borderaxespad) * float(legend.prop.get_size_in_points())
    _RESERVES[legend] = Reserve(plan.side, gap)
    return legend


def _names(legend: Legend) -> tuple[str, ...]:
    record = _RECORDS.get(legend)
    if record is not None:
        return record.entries.labels
    return tuple(t.get_text() for t in legend.get_texts())
