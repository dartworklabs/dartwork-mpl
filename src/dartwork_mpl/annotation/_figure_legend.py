"""figure_legend: one legend for every panel of a figure, outside the panels."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import numpy as np
from matplotlib.transforms import Bbox, BboxBase

from .._figure_geometry import (
    BBOX_ERRORS,
    OutsideSide,
    figure_axes,
    figure_legends,
    get_renderer,
    iter_figure_level_extents,
)
from ._legend_entries import _placed_as_built
from ._legend_fit import ceil_div, legend_pad, legend_size, probe
from ._legend_look import SPOT_TOLERANCE_PX, sits_at
from ._legend_outside import OutsidePlan, choose, split_ncols

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.legend import Legend
    from matplotlib.typing import LegendLocType

# Each side's legend ``loc`` and its anchor on the (sub)figure, in figure fraction.
_FIGURE_LOCS: dict[OutsideSide, tuple[LegendLocType, tuple[float, float]]] = {
    "above": ("upper center", (0.5, 1.0)),
    "below": ("lower center", (0.5, 0.0)),
    "right": ("center right", (1.0, 0.5)),
    "left": ("center left", (0.0, 0.5)),
}

_SIDES: dict[str, OutsideSide] = {
    "above": "above",
    "below": "below",
    "right": "right",
    "left": "left",
}


def _entry_names(legend: Legend) -> set[str]:
    """The entry names a legend shows, as given before any wrapping.

    A ``place_legend`` legend whose entries read as built keeps the names
    it was built from (a wrapped name is one name); once the caller has
    changed an entry's text, the texts it shows now are its names.
    """
    if _placed_as_built(legend):
        for name in ("_dm_outside_source", "_dm_best_source"):
            source = getattr(legend, name, None)
            labels = getattr(source, "labels", None)
            if isinstance(labels, list):
                return {str(label) for label in labels}
    return {text.get_text() for text in legend.get_texts()}


def _figure_entries(fig: Figure | SubFigure) -> tuple[list[Any], list[str]]:
    """Every Axes' labelled artists once, by label, in figure order.

    The Axes are those drawn in ``fig``, its nested SubFigures' included
    (:func:`~dartwork_mpl._figure_geometry.figure_axes`).
    """
    handles: list[Any] = []
    labels: list[str] = []
    seen: set[str] = set()
    for ax in figure_axes(fig):
        for handle, label in zip(*ax.get_legend_handles_labels(), strict=True):
            if label not in seen:
                seen.add(label)
                handles.append(handle)
                labels.append(label)
    return handles, labels


def _figure_plan(
    fig: Figure | SubFigure,
    handles: list[Any],
    labels: list[str],
    side: OutsideSide,
    legend_kw: dict[str, Any],
    explicit: int | None,
    renderer: RendererBase,
    panels: Bbox,
) -> OutsidePlan:
    """Columns and cost of the figure legend on ``side`` of the panels.

    Above and below: the fewest rows that fit the (sub)figure's width;
    right and left: the fewest columns that fit its height. The legend is
    centred on that edge and fits when it stays on the (sub)figure, its pad
    from each end: the rule ``place_legend``'s outside legends follow,
    with no neighbouring panel, since this one spans them all. The loss is
    the legend's height (above, below) or width (right, left) as a share
    of the panels'.
    """
    count = max(len(labels), 1)
    along_width = side in ("above", "below")
    edge = fig.bbox.width if along_width else fig.bbox.height
    limit: float | None = None
    if explicit is not None:
        steps = [explicit]
    elif along_width:
        steps = list(
            dict.fromkeys(ceil_div(count, r) for r in range(1, count + 1))
        )
    else:
        steps = list(range(1, count + 1))
    loc, _anchor = _FIGURE_LOCS[side]
    width = height = float("inf")
    ncols = steps[-1]
    fits = False
    for ncols in steps:
        trial = probe(fig, handles, labels, loc=loc, ncols=ncols, **legend_kw)
        if limit is None:
            limit = edge - 2 * legend_pad(trial, renderer)
        try:
            width, height = legend_size(trial, renderer)
        except BBOX_ERRORS:
            width = height = float("inf")
        fits = (width if along_width else height) <= limit + 0.5
        if fits:
            break
    loss = (
        height / max(panels.height, 1.0)
        if along_width
        else width / max(panels.width, 1.0)
    )
    return OutsidePlan(side, ncols, tuple(labels), width, height, loss, fits)


#: The figure's own label on each side a figure legend would share.
_SHARED_LABELS: dict[OutsideSide, str] = {
    "above": "_suptitle",
    "below": "_supxlabel",
    "left": "_supylabel",
}


def _past_shared_label(
    fig: Figure | SubFigure, side: OutsideSide, renderer: RendererBase
) -> tuple[float, float]:
    """The legend's anchor on ``side``, moved past the figure's label there.

    Under a ``fig.suptitle`` above, over a ``fig.supxlabel`` below, right
    of a ``fig.supylabel`` on the left, in (sub)figure fraction; the edge
    of the (sub)figure when there is none.
    """
    anchor = _FIGURE_LOCS[side][1]
    attr = _SHARED_LABELS.get(side)
    label = getattr(fig, attr, None) if attr is not None else None
    if label is None:
        return anchor
    box = fig.bbox
    for art, ext in iter_figure_level_extents(
        cast("Figure", fig), renderer, legends=False
    ):
        if art is not label:
            continue
        match side:
            case "above":
                return (anchor[0], float((ext.y0 - box.y0) / box.height))
            case "below":
                return (anchor[0], float((ext.y1 - box.y0) / box.height))
            case _:
                return (float((ext.x1 - box.x0) / box.width), anchor[1])
    return anchor


#: How often a SubFigure's figure legend moves past the text it meets, at most.
_SETTLE_TRIES = 8
#: Anchors closer than this (figure fraction) are the same place.
_SAME_ANCHOR = 1e-9


def _texts_above(
    holder: Figure | SubFigure, renderer: RendererBase
) -> list[Bbox]:
    """The figure-level texts and legends of the (Sub)Figures above ``holder``.

    Those its legend has to clear, as :func:`dartwork_mpl.layout` puts a
    SubFigure title under them: a root suptitle over a SubFigure, a parent
    SubFigure's title or legend. The root figure has none above it.
    """
    found: list[Bbox] = []
    owner: Figure | SubFigure | None = holder.get_figure(root=False)
    if owner is holder:  # the root figure is its own figure
        owner = None
    while owner is not None:
        found += [
            ext
            for _art, ext in iter_figure_level_extents(
                cast("Figure", owner), renderer, subfigures=False
            )
        ]
        parent = owner.get_figure(root=False)
        owner = None if parent is owner else parent
    return found


def _past(
    side: OutsideSide, own: Bbox, met: list[Bbox], box: BboxBase
) -> float | None:
    """Where the legend's anchor goes on its side, past the boxes it meets.

    In ``box`` fraction, the coordinate across the side (y above and below,
    x right and left); ``None`` when ``own`` meets none of ``met``.
    """
    hit = [
        b
        for b in met
        if b.x0 < own.x1 and b.x1 > own.x0 and b.y0 < own.y1 and b.y1 > own.y0
    ]
    if not hit:
        return None
    match side:
        case "above":
            return float((min(b.y0 for b in hit) - box.y0) / box.height)
        case "below":
            return float((max(b.y1 for b in hit) - box.y0) / box.height)
        case "left":
            return float((max(b.x1 for b in hit) - box.x0) / box.width)
        case _:
            return float((min(b.x0 for b in hit) - box.x0) / box.width)


def settle_figure_legends(fig: Figure, holder: Figure | SubFigure) -> bool:
    """Anchor ``holder``'s figure legends past what is now drawn on their side.

    ``figure_legend`` anchors a legend on a side of a (Sub)Figure past its
    own label there (its suptitle above, supxlabel below, supylabel on the
    left) as it stands when called. The layout runs this once ``holder``'s
    title is placed (a SubFigure title the library places moves under the
    figure-level text above it), so the legend sits past the label as it
    ends up, a label set after the call too, and past the figure-level
    texts and legends of the (Sub)Figures above that it meets (a root
    suptitle over a SubFigure without a title of its own): on one edge, the
    title, then the legend, then the panels, on the root figure (``holder``
    is ``fig``) and in each SubFigure alike. Only a legend ``figure_legend``
    placed on a side moves, and only while it sits as the library last
    placed it (:func:`_as_placed`): one the caller moved since
    (``set_bbox_to_anchor``, ``set_loc``), like one the caller placed or
    anchored, stays, and LEGEND_OVERLAP reports what it covers. Returns
    whether a legend moved (the caller redraws).
    """
    moved = False
    box = holder.bbox
    for legend in holder.legends:
        side = getattr(legend, "_dm_figure_side", None)
        if (
            not getattr(legend, "_dm_figure_legend", False)
            or side not in _FIGURE_LOCS
            or not legend.get_visible()
        ):
            continue
        renderer = get_renderer(fig)
        if not _as_placed(legend, holder, renderer):
            continue  # the caller's from now on
        anchor = _past_shared_label(holder, side, renderer)
        for _ in range(_SETTLE_TRIES):
            if _place(legend, holder, anchor):
                moved = True
                fig.canvas.draw()
                renderer = get_renderer(fig)
            try:
                own = legend.get_window_extent(renderer)
            except BBOX_ERRORS:
                break
            past = _past(side, own, _texts_above(holder, renderer), box)
            if past is None:
                break
            anchor = (
                (anchor[0], past)
                if side in ("above", "below")
                else (past, anchor[1])
            )
    return moved


def _as_placed(
    legend: Legend, holder: Figure | SubFigure, renderer: RendererBase
) -> bool:
    """Whether ``legend`` sits as the library last placed it.

    The rule ``place_legend``'s legends follow, read through the public
    ``get_bbox_to_anchor`` and ``get_window_extent``: its anchor is still
    the point the library set (compared in display px through
    ``holder.transSubfigure``, so the same numbers in another transform are
    a move) and its box sits where the library's ``loc`` puts it against
    that point (:func:`~._legend_look.sits_at`; a ``set_loc`` since moves
    it off). The record changes only when the library moves the legend.
    """
    anchor = getattr(legend, "_dm_figure_anchor", None)
    loc = getattr(legend, "_dm_figure_loc", None)
    if anchor is None or not isinstance(loc, str):
        return False
    try:
        now = np.asarray(legend.get_bbox_to_anchor().get_points(), dtype=float)
        want = np.asarray(
            holder.transSubfigure.transform([anchor, anchor]), dtype=float
        )
    except BBOX_ERRORS:
        return False
    if (
        now.shape != want.shape
        or np.max(np.abs(now - want)) > SPOT_TOLERANCE_PX
    ):
        return False
    return sits_at(legend, renderer, loc)


def _place(
    legend: Legend, holder: Figure | SubFigure, anchor: tuple[float, float]
) -> bool:
    """Anchor ``legend`` at ``anchor`` (``holder`` fraction) unless it is there."""
    was = getattr(legend, "_dm_figure_anchor", None)
    if was is not None and all(
        abs(a - b) <= _SAME_ANCHOR for a, b in zip(was, anchor, strict=True)
    ):
        return False
    legend.set_bbox_to_anchor(anchor, transform=holder.transSubfigure)
    legend._dm_figure_anchor = anchor  # type: ignore[attr-defined]
    return True


def _replaced(fig: Figure | SubFigure, names: set[str]) -> list[Legend]:
    """The legends a new figure legend of ``names`` replaces.

    The Axes legends holding only ``names`` and the figure legend an earlier
    call drew. Taken before the new legend exists, removed only once it
    does, so a call that fails leaves every legend as it was.
    """
    found: list[Legend] = []
    for ax in figure_axes(fig):
        legend = ax.get_legend()
        if legend is not None and _entry_names(legend) <= names:
            found.append(legend)
    found.extend(
        legend
        for legend in figure_legends(fig)
        if getattr(legend, "_dm_figure_legend", False)
    )
    return found


def _remove(legends: list[Legend]) -> None:
    for legend in legends:
        legend.remove()


def figure_legend(
    fig: Figure | SubFigure, *, loc: str = "best", **kw: Any
) -> Legend | None:
    """One legend for every panel of ``fig``, outside the panels.

    The entries are every Axes' labelled artists, each label once, in
    figure order; on a SubFigure, its nested SubFigures' panels are its
    panels too. The Axes legends that hold only those entries (one per
    panel, a twin pair's, ``dm.place_legend``'s) and a legend an earlier
    call drew are removed once the new legend is drawn; any other legend
    stays, and a call that raises (``bbox_to_anchor`` with a side, say)
    leaves every legend as it was.

    ``loc="best"`` puts the legend above the panels, or right of them when
    that takes clearly less of the panels (at least 10 % and 5 % of their
    size less; the rule of :func:`dartwork_mpl.place_legend`). Above and
    below take the fewest rows that fit the figure's width, right and left
    the fewest columns that fit its height, the legend's pad from each end
    (it may be longer than the panels); ``ncol`` / ``ncols`` in
    ``kw`` overrides the count. ``loc="above"``, ``"below"``, ``"right"``
    or ``"left"`` is that side; any other ``loc`` (with ``kw``) goes to
    ``fig.legend`` unchanged. The legend clears the figure's own label on
    its side: under a ``fig.suptitle`` above, over a ``fig.supxlabel``
    below, right of a ``fig.supylabel`` on the left. Names are not wrapped.

    :func:`dartwork_mpl.simple_layout` keeps the panels clear of the legend,
    with the preset's ``legend.borderaxespad`` between them. Returns the
    legend, or ``None`` when no Axes has a labelled artist.

    Experimental: the side rule and which panel legends are removed may
    still change.
    """
    handles, labels = _figure_entries(fig)
    replaced = _replaced(fig, set(labels))
    if not handles:
        _remove(replaced)
        return None
    side = _SIDES.get(loc)
    if side is None and loc != "best":
        legend = fig.legend(
            handles, labels, loc=cast("LegendLocType", loc), **kw
        )
        legend._dm_figure_legend = True  # type: ignore[attr-defined]
        _remove(replaced)
        return legend
    legend_kw, explicit = split_ncols(kw)
    for key in ("bbox_to_anchor", "bbox_transform"):
        if key in legend_kw:
            raise ValueError(
                f"figure_legend(loc={loc!r}) anchors the legend itself; "
                f"remove {key}= or pass a matplotlib loc instead"
            )
    renderer = get_renderer(fig)
    boxes = [
        ax.get_window_extent(renderer)
        for ax in figure_axes(fig)
        if ax.get_visible()
    ]
    panels = Bbox.union(boxes) if boxes else Bbox(fig.bbox.get_points())
    sides: list[OutsideSide] = (
        [side] if side is not None else ["above", "right"]
    )
    plan = choose(
        [
            _figure_plan(
                fig, handles, labels, s, legend_kw, explicit, renderer, panels
            )
            for s in sides
        ]
    )
    where = _FIGURE_LOCS[plan.side][0]
    anchor = _past_shared_label(fig, plan.side, renderer)
    legend = fig.legend(
        handles,
        labels,
        loc=where,
        ncols=plan.ncols,
        bbox_to_anchor=anchor,
        bbox_transform=fig.transSubfigure,
        **legend_kw,
    )
    # simple_layout keeps this gap between the legend and the panels.
    legend._dm_layout_gap_pt = float(legend.borderaxespad) * float(  # type: ignore[attr-defined]
        legend.prop.get_size_in_points()
    )
    legend._dm_figure_legend = True  # type: ignore[attr-defined]
    legend._dm_figure_side = plan.side  # type: ignore[attr-defined]
    # Where the library put it: the loc and the anchor point (fraction of
    # ``fig``), so the layout tells a legend the caller moved since.
    legend._dm_figure_loc = where  # type: ignore[attr-defined]
    legend._dm_figure_anchor = anchor  # type: ignore[attr-defined]
    _remove(replaced)
    return legend


__all__ = ["figure_legend", "settle_figure_legends"]
