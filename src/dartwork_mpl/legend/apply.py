"""Draw the legends the decisions plan, and the layout's legend hooks.

A legend ``place_legend`` built carries a :class:`Record` (``_dm_legend``):
what it was placed from and where. The layout places it again at the size
it settles on only while it still sits where the library put it; a legend
the caller moved (``set_loc``, ``set_bbox_to_anchor``) is the caller's.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, cast

import matplotlib as mpl
from matplotlib.font_manager import FontProperties
from matplotlib.legend import Legend
from matplotlib.transforms import ScaledTranslation

from .._figure_geometry import (
    BBOX_ERRORS,
    OutsideSide,
    axes_titles,
    figure_axes,
    figure_legends,
    get_renderer,
    same_position_axes,
)
from .._figure_geometry import outside_side as anchored_side
from ..edgecase import settle as settle_edges
from . import decide, measure
from .edges import EDGES
from .model import (
    Anchor,
    Entries,
    EntryPlan,
    FigurePlan,
    Inside,
    LegendPlan,
    Outside,
    Request,
    Side,
    TitlePad,
    parse_side,
    split_columns,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.typing import LegendLocType

_ANCHORS = {
    Side.ABOVE: ((0.5, 1.0), (0.0, 1.0)),
    Side.BELOW: ((0.5, 0.0), (0.0, -1.0)),
    Side.RIGHT: ((1.0, 0.5), (1.0, 0.0)),
    Side.LEFT: ((0.0, 0.5), (-1.0, 0.0)),
}
_CALLER_ANCHOR = ("bbox_to_anchor", "bbox_transform")


@dataclass
class Record:
    """What a ``place_legend`` legend was placed from, and where it was put.

    ``plan`` is ``None`` for a matplotlib ``loc`` passed through; ``size``
    the Axes size (half px) and span it was last decided at; ``at`` the
    legend's ``loc`` code and anchor box the library set.
    """

    request: Request
    handles: list[Any]
    entries: Entries
    kw: dict[str, Any]
    plan: LegendPlan | None
    size: tuple[int, ...] = ()
    pad: float = 0.0
    at: tuple[Any, Any] = (None, None)
    anchor: Anchor | None = None


def record_of(legend: Legend | None) -> Record | None:
    """The record of a legend the library placed and the caller has not moved."""
    record = getattr(legend, "_dm_legend", None)
    if legend is None or not isinstance(record, Record):
        return None
    return record if _still_at(legend, record.at) else None


def _remember(legend: Legend, record: Record) -> Legend:
    record.at = _at(legend)
    legend._dm_legend = record  # type: ignore[attr-defined]
    # annotation's bar labels tell the library's legends by this mark.
    legend._dm_placed_legend = True  # type: ignore[attr-defined]
    return legend


def _new_legend(
    owner: Axes | Figure | SubFigure, *args: Any, **kw: Any
) -> Legend:
    """``owner.legend(...)``: matplotlib's stub leaves its keywords untyped."""
    legend: Legend = owner.legend(*args, **kw)  # pyright: ignore[reportUnknownMemberType]
    return legend


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
    record = getattr(legend, "_dm_legend", None)
    previous = record.anchor if isinstance(record, Record) else None
    if (
        previous is not None
        and getattr(legend, "_dm_outside_side", None) == side.value
        and abs(previous.clearance - plan.clearance) <= 0.01
    ):
        return False
    (x, y), (dx, dy) = _ANCHORS[side]
    out = plan.clearance / 72.0
    offset = ScaledTranslation(dx * out, dy * out, root.dpi_scale_trans)
    legend.set_bbox_to_anchor((x, y), ax.transAxes + offset)
    legend._dm_outside_side = side.value  # type: ignore[attr-defined]
    if isinstance(record, Record):
        record.anchor = plan
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
    ax: Axes, record: Record, plan: LegendPlan, renderer: RendererBase
) -> Legend:
    """Draw ``record``'s legend on ``ax`` as ``plan`` says and record it."""
    if isinstance(plan, Inside):
        loc, labels = plan.loc.value, record.entries.labels
    else:
        loc, labels = plan.side.legend_loc, plan.entries.labels
    legend = _new_legend(
        ax,
        record.handles,
        list(labels),
        loc=cast("LegendLocType", loc),
        ncols=plan.columns.n,
        **record.kw,
    )
    record = replace(record, plan=plan, anchor=None)
    _remember(legend, record)
    if isinstance(plan, Outside):
        anchor_outside(legend, ax, plan.side, renderer)
    return legend


def decide_for(
    ax: Axes,
    record: Record,
    renderer: RendererBase,
    current: LegendPlan | None = None,
) -> LegendPlan:
    """Decide (with the edge cases) where ``record``'s legend goes on ``ax``."""
    facts = measure.legend_facts(
        ax,
        record.handles,
        record.entries,
        record.request,
        record.kw,
        renderer,
        current,
    )
    record.pad = facts.pad
    plan = settle_edges(facts, decide.place(facts), EDGES).plan
    assert isinstance(plan, Inside | Outside)
    return plan


def _same_place(a: LegendPlan, b: LegendPlan) -> bool:
    if isinstance(a, Inside) and isinstance(b, Inside):
        return (a.loc, a.columns) == (b.loc, b.columns)
    if isinstance(a, Outside) and isinstance(b, Outside):
        return (a.side, a.columns, a.entries) == (b.side, b.columns, b.entries)
    return False


def _kept_settings(legend: Legend | None) -> dict[str, Any]:
    """The title, frame, font size and handlers a rebuilt legend repeats."""
    if legend is None:
        return {}
    kept: dict[str, Any] = {}
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
    custom = {
        k: h
        for k, h in legend.get_legend_handler_map().items()
        if defaults.get(k) is not h
    }
    if custom:
        kept["handler_map"] = custom
    return kept


def place_legend(ax: Axes, loc: str, kw: dict[str, Any]) -> Legend | None:
    """Place the legend of ``ax`` (:func:`dartwork_mpl.legend.place_legend`)."""
    owners = same_position_axes(ax)
    facts, handles = measure.entry_facts(owners, ax)
    plan = settle_edges(facts, decide.entries(facts), EDGES).plan
    assert isinstance(plan, EntryPlan)
    host = owners[plan.host]
    old = host.get_legend()
    if not plan.picks:
        if old is not None and hasattr(old, "_dm_legend"):
            old.remove()
        return None
    picked = [handles[i][j] for i, j in plan.picks]
    entries = Entries(
        tuple(facts.owners[i].entries.labels[j] for i, j in plan.picks)
    )
    source = old or next(
        (o.get_legend() for o in owners if o.get_legend()), None
    )
    kept = _kept_settings(source)
    if "fontsize" in kw or "prop" in kw:
        kept.pop("fontsize", None)
    rest, columns = split_columns({**kept, **kw})
    side = parse_side(loc)
    anchored = any(k in rest for k in _CALLER_ANCHOR)
    if side is not None and anchored:
        key = next(k for k in _CALLER_ANCHOR if k in rest)
        raise ValueError(
            f"place_legend(loc={loc!r}) anchors the legend itself; "
            f"remove {key}= or pass a matplotlib loc instead"
        )
    for i in plan.remove:
        if (partner := owners[i].get_legend()) is not None:
            partner.remove()
    if old is not None:
        old.remove()
    request = Request(side, columns, anchored)
    if side is None and loc != "best":
        if columns is not None:
            rest["ncols"] = columns.n
        legend = _new_legend(
            host,
            picked,
            list(entries.labels),
            loc=cast("LegendLocType", loc),
            **rest,
        )
        return _remember(legend, Record(request, picked, entries, rest, None))
    record = Record(request, picked, entries, rest, None)
    root = host.get_figure(root=True)
    if root is None:
        raise ValueError("place_legend needs an Axes on a Figure")
    root.canvas.draw()  # pyright: ignore[reportUnknownMemberType]
    renderer = get_renderer(root)
    return draw(host, record, decide_for(host, record, renderer), renderer)


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
    new = decide_for(ax, record, renderer, current=plan)
    if _same_place(new, plan):
        return False
    rebuilt = record_of(draw(ax, record, new, renderer))
    if rebuilt is not None:
        rebuilt.size = _half_px(ax, renderer, new, record.pad)
    return True


def _lift_titles(ax: Axes, renderer: RendererBase) -> bool:
    facts = measure.title_facts(ax, renderer)
    if facts is None:
        return False
    plan = settle_edges(facts, decide.title_pad(facts), EDGES).plan
    root = ax.get_figure(root=True)
    if not isinstance(plan, TitlePad) or plan.px is None or root is None:
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
        record = record_of(legend)
        if (
            legend is not None
            and record is not None
            and _again(ax, legend, record, renderer)
        ):
            moved = True
    for ax in fig.axes:
        legend = ax.get_legend()
        side = parse_side(anchored_side(legend) or "")
        if (
            legend is not None
            and side is not None
            and record_of(legend) is not None
            and anchor_outside(legend, ax, side, renderer)
        ):
            moved = True
    for ax in fig.axes:
        if _lift_titles(ax, renderer):
            moved = True
    return moved


def outside_side(legend: Legend) -> OutsideSide | None:
    """The side the library anchored ``legend`` outside of, or ``None``."""
    return anchored_side(legend)


# ---------------------------------------------------------- figure legends
def figure_legend(
    fig: Figure | SubFigure, loc: str, kw: dict[str, Any]
) -> Legend | None:
    """One legend for ``fig``'s panels (:func:`dartwork_mpl.legend.figure_legend`)."""
    handles: list[Any] = []
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
    replaced += [
        lg for lg in figure_legends(fig) if hasattr(lg, "_dm_figure_plan")
    ]
    if not handles:
        for legend in replaced:
            legend.remove()
        return None
    side = parse_side(loc)
    if side is None and loc != "best":
        legend = _new_legend(
            fig, handles, labels, loc=cast("LegendLocType", loc), **kw
        )
    else:
        rest, columns = split_columns(kw)
        for key in _CALLER_ANCHOR:
            if key in rest:
                raise ValueError(
                    f"figure_legend(loc={loc!r}) anchors the legend itself; "
                    f"remove {key}= or pass a matplotlib loc instead"
                )
        renderer = get_renderer(fig)
        entries = Entries(tuple(labels))
        facts = measure.figure_facts(
            fig, handles, entries, Request(side, columns), rest, renderer
        )
        plan = settle_edges(facts, decide.figure_place(facts), EDGES).plan
        assert isinstance(plan, FigurePlan)
        legend = _new_legend(
            fig,
            handles,
            labels,
            loc=cast("LegendLocType", plan.side.figure_loc),
            ncols=plan.columns.n,
            bbox_to_anchor=plan.anchor,
            bbox_transform=fig.transSubfigure,
            **rest,
        )
        # simple_layout keeps this gap between the legend and the panels.
        legend._dm_layout_gap_pt = float(legend.borderaxespad) * float(  # type: ignore[attr-defined]
            legend.prop.get_size_in_points()
        )
        legend._dm_figure_side = plan.side.value  # type: ignore[attr-defined]
        _set_figure_plan(legend, plan)
    for old in replaced:
        old.remove()
    return legend


def _names(legend: Legend) -> tuple[str, ...]:
    record = getattr(legend, "_dm_legend", None)
    if isinstance(record, Record):
        return record.entries.labels
    return tuple(t.get_text() for t in legend.get_texts())


def _at(legend: Legend) -> tuple[Any, Any]:
    """A legend's ``loc`` code and anchor box, which a caller's move changes."""
    return (getattr(legend, "_loc", None), legend.get_bbox_to_anchor())


def _still_at(legend: Legend, at: tuple[Any, Any] | None) -> bool:
    """Whether ``legend`` keeps the ``loc`` and anchor box recorded in ``at``."""
    if at is None:
        return False
    loc, box = _at(legend)
    return loc == at[0] and box is at[1]


def _set_figure_plan(legend: Legend, plan: FigurePlan) -> None:
    legend._dm_figure_plan = plan  # type: ignore[attr-defined]
    legend._dm_figure_at = _at(legend)  # type: ignore[attr-defined]
