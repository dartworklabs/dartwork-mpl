"""Axes-based annotation helper module.

Provides ``label_axes`` for adding standard alphabetic sub-labels to figure
panels, ``annotate_value`` / ``annotate_corner`` / ``label_hline`` for compact
in-axes labels, ``label_bars`` for value labels on bars, ``place_legend`` for
axes legends, and ``arrow_axis`` for drawing bidirectional Low-High arrow
axes. ``settle_bar_labels`` is the layout's pass over the bar labels
(crowding, headroom); ``dm.simple_layout`` runs it, then
``warn_hidden_bar_labels`` once its fit is done.
"""

from __future__ import annotations

__all__ = [
    "add_note",
    "annotate_corner",
    "annotate_value",
    "arrow_axis",
    "bar_values_past_limits",
    "clear_bar_labels",
    "label_axes",
    "label_bars",
    "label_hline",
    "label_line_ends",
    "make_offset",
    "optimize_legend",
    "place_legend",
    "settle_bar_labels",
    "warn_hidden_bar_labels",
    "wrap_axis_label",
    "wrap_axis_labels",
]

import re
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, cast

import matplotlib as mpl
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import to_hex, to_rgba
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.offsetbox import DrawingArea, TextArea
from matplotlib.text import Text
from matplotlib.transforms import Bbox, ScaledTranslation

from .._figure_geometry import (
    BBOX_ERRORS,
    OutsideSide,
    anchor_outside,
    get_renderer,
    same_position_axes,
)
from ..scale import fs
from ._bar_label_geometry import host_axes
from ._bar_label_settle import (
    bar_values_past_limits,
    clear_bar_labels,
    settle_bar_labels,
    warn_hidden_bar_labels,
)
from ._bar_labels import label_bars
from ._line_end_labels import label_line_ends
from ._optimize_legend import optimize_legend
from ._panel_labels import label_axes
from ._placement_geometry import (
    _collision_area,
    _data_occupancy_bboxes,
    _outside_area,
    _overlap_area,
    _renderer_for_axes,
)
from ._point_labels import HorizontalAlign as HorizontalAlign
from ._point_labels import VerticalAlign as VerticalAlign
from ._point_labels import annotate_corner, annotate_value, label_hline

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import SubFigure
    from matplotlib.typing import LegendLocType


_Axis = Literal["x", "y"]

_LegendCandidate = Literal[
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "upper center",
    "lower center",
]


def _parse_axis(axis: str, message: str) -> _Axis:
    """Return ``"x"`` or ``"y"``; raise ``ValueError(message)`` for anything else."""
    match axis:
        case "x" | "y":
            return axis
        case _:
            raise ValueError(message)


def add_note(fig: Figure, text: str, **kw: Any) -> Text:
    """Add a source or note line under the plot, in the preset's note style.

    One call for "add a source note" / "그림 아래에 출처를 적어줘", so every
    agent draws the same line: the figure's lower-left corner, left-aligned,
    one step below the preset font (``dm.fs(-1)``) in the preset text colour.
    :func:`dartwork_mpl.simple_layout` keeps the axes, tick labels and axis
    labels above it with the preset's ``axes.labelpad`` between them. A
    ``fontsize=``, ``color=`` or other ``Text`` keyword the user names wins::

        dm.add_note(fig, "Source: internal web logs")
        dm.simple_layout(fig)

    Returns the :class:`~matplotlib.text.Text`.
    """

    style: dict[str, Any] = {"ha": "left", "va": "bottom", "fontsize": fs(-1)}
    style.update(kw)
    note = fig.text(0.0, 0.0, text, **style)
    # simple_layout reserves this gap above the note (layout slice reads it).
    note._dm_layout_gap_pt = float(mpl.rcParams["axes.labelpad"])  # type: ignore[attr-defined]
    return note


def _legend_for_loc(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    loc: str,
    legend_kw: dict[str, Any],
) -> Legend:
    """Draw (replacing any existing) the axes legend at matplotlib location ``loc``."""
    # A caller's loc is passed through unchanged; Matplotlib validates it.
    return ax.legend(
        handles, labels, loc=cast("LegendLocType", loc), **legend_kw
    )


@dataclass(frozen=True)
class _MeasuredLegend:
    """A trial legend placement whose rendered box was measured.

    ``score`` is the overlap/outside penalty (lower is better) and
    ``collision_free`` says the box touches no data and stays inside the axes.
    """

    loc: _LegendCandidate
    ncol: int
    score: float
    collision_free: bool


@dataclass(frozen=True)
class _UnmeasuredLegend:
    """A trial legend placement whose rendered box could not be measured."""

    loc: _LegendCandidate
    ncol: int


_LegendTrial: TypeAlias = _MeasuredLegend | _UnmeasuredLegend


def _trial_score(trial: _LegendTrial) -> float:
    """Return the trial's penalty; an unmeasured trial ranks last (``inf``)."""
    match trial:
        case _MeasuredLegend(score=score):
            return score
        case _UnmeasuredLegend():
            return float("inf")


def _best_trial(trials: list[_LegendTrial]) -> _LegendTrial:
    """Return the lowest-penalty trial, the earliest one on a tie.

    ``trials`` must be non-empty (``ValueError`` otherwise).
    """
    return min(trials, key=_trial_score)


def _mark_placement(legend: Legend, trial: _LegendTrial) -> None:
    """Set the documented ``_dm_collision_free`` / ``_dm_collision_score`` attributes.

    An unmeasured placement reports ``False`` and ``inf``.
    """
    match trial:
        case _MeasuredLegend(score=score, collision_free=collision_free):
            pass
        case _UnmeasuredLegend():
            score, collision_free = float("inf"), False
    legend._dm_collision_free = collision_free  # type: ignore[attr-defined]
    legend._dm_collision_score = score  # type: ignore[attr-defined]


def _score_legend_candidate(
    legend_bbox: Bbox, data_bboxes: list[Bbox], axes_bbox: Bbox, ncol: int
) -> float:
    area = max(float(legend_bbox.width * legend_bbox.height), 1.0)
    overlap = sum(_overlap_area(legend_bbox, bbox) for bbox in data_bboxes)
    outside = _outside_area(legend_bbox, axes_bbox)
    height_ratio = float(legend_bbox.height / max(axes_bbox.height, 1.0))
    tall_penalty = 0.0
    if ncol == 1 and height_ratio > 0.55:
        tall_penalty = height_ratio - 0.55
    return (overlap / area) + 4.0 * (outside / area) + tall_penalty


def _legend_candidate_ncols(
    labels: list[str], legend_kw: dict[str, Any]
) -> list[int]:
    explicit = legend_kw.get("ncol", legend_kw.get("ncols"))
    if explicit is not None:
        return [int(explicit)]
    max_ncol = min(3, max(len(labels), 1))
    return list(range(1, max_ncol + 1))


# The legend's own anchor point (matplotlib ``loc``) for each outside side:
# the legend edge that faces the Axes touches the anchor.
_OUTSIDE_LEGEND_LOCS: dict[OutsideSide, LegendLocType] = {
    "above": "lower center",
    "below": "upper center",
    "right": "center left",
    "left": "center right",
}


def _parse_outside_side(loc: str) -> OutsideSide | None:
    """Return ``loc`` as an outside side, or ``None`` for a matplotlib ``loc``."""
    match loc:
        case "above" | "below" | "right" | "left":
            return loc
        case _:
            return None


def _outside_ncols(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    side: OutsideSide,
    legend_kw: dict[str, Any],
    renderer: RendererBase,
) -> int:
    """Return the column count for an outside legend on ``side`` of ``ax``.

    Right and left legends are one column. Above and below, the fewest
    rows whose rendered legend is no wider than the Axes win: one row when
    it fits, otherwise two, and so on; a single column when nothing fits.
    ``legend_kw`` must not hold ``ncol`` / ``ncols``.
    """
    if side in ("right", "left"):
        return 1
    try:
        axes_width = ax.get_window_extent(renderer).width
    except BBOX_ERRORS:
        return 1
    count = len(labels)
    tried: set[int] = set()
    for rows in range(1, count + 1):
        ncols = -(-count // rows)  # ceil(count / rows)
        if ncols in tried:
            continue
        tried.add(ncols)
        legend = ax.legend(
            handles,
            labels,
            loc=_OUTSIDE_LEGEND_LOCS[side],
            ncols=ncols,
            **legend_kw,
        )
        try:
            width = legend.get_window_extent(renderer).width
        except BBOX_ERRORS:
            continue
        if width <= axes_width:
            return ncols
    return 1


def _place_outside_legend(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    side: OutsideSide,
    kw: dict[str, Any],
) -> Legend:
    """Draw the legend of ``ax`` outside ``side``, past its tick and axis labels."""
    for key in ("bbox_to_anchor", "bbox_transform"):
        if key in kw:
            raise ValueError(
                f"place_legend(loc={side!r}) anchors the legend itself; "
                f"remove {key}= or pass a matplotlib loc instead"
            )
    legend_kw = dict(kw)
    explicit = legend_kw.pop("ncols", None)
    explicit = legend_kw.pop("ncol", explicit)
    _fig, renderer = _renderer_for_axes(ax)
    ncols = (
        int(explicit)
        if explicit is not None
        else _outside_ncols(ax, handles, labels, side, legend_kw, renderer)
    )
    legend = ax.legend(
        handles,
        labels,
        loc=_OUTSIDE_LEGEND_LOCS[side],
        ncols=ncols,
        **legend_kw,
    )
    anchor_outside(legend, ax, side, renderer)
    return legend


def _may_go_outside(kw: dict[str, Any]) -> bool:
    """Whether a ``best`` legend may fall back outside (no caller anchor)."""
    return "bbox_to_anchor" not in kw and "bbox_transform" not in kw


def _covers_data(ax: Axes, legend: Legend, renderer: Any) -> bool:
    """Whether the drawn ``legend`` box overlaps data of ``ax`` or its twins."""
    ax.figure.canvas.draw()
    try:
        bbox = legend.get_window_extent(renderer)
    except BBOX_ERRORS:
        return False
    return _collision_area(bbox, _pair_occupancy_bboxes(ax, renderer)) > 0


def _pair_occupancy_bboxes(ax: Axes, renderer: Any) -> list[Bbox]:
    """Data occupancy of ``ax`` and every twin drawn in the same box."""
    return [
        bbox
        for owner in same_position_axes(ax)
        for bbox in _data_occupancy_bboxes(owner, renderer)
    ]


def _legend_entries(ax: Axes) -> tuple[list[Any], list[str]]:
    """The labelled artists of ``ax`` as legend handles and labels."""
    handles, labels = ax.get_legend_handles_labels()
    return list(handles), list(labels)


_EntrySignature: TypeAlias = tuple[str, tuple[type, ...]]
"""One legend entry: its text and the artist types its handle draws."""

# What reading a legend's offset boxes or building a probe legend can raise on
# a handle or handler matplotlib lays out unexpectedly: a missing attribute or
# child (AttributeError, IndexError) or a rejected argument (TypeError,
# ValueError). Anything else is a bug and propagates.
_UNREADABLE = (AttributeError, IndexError, TypeError, ValueError)


def _entry_signatures(legend: Legend) -> list[_EntrySignature]:
    """Each drawn entry of ``legend``, in legend order: text and handle artist types.

    Read through the public ``get_children`` of the legend's offset boxes:
    an entry is the box that holds a handle area and a text. A tuple handle
    draws several artists where a plain one draws one, and a custom handler
    draws its own types, so the signature tells a rebuildable entry from one
    that is not. A legend with no readable entry gives ``[]``.
    """
    found: list[_EntrySignature] = []

    def walk(node: Any) -> None:
        children = node.get_children()
        areas = [c for c in children if isinstance(c, DrawingArea)]
        texts = [c for c in children if isinstance(c, TextArea)]
        if areas and texts:
            found.append(
                (
                    texts[0].get_text(),
                    tuple(type(a) for a in areas[0].get_children()),
                )
            )
            return
        for child in children:
            if child.__class__.__module__ == "matplotlib.offsetbox":
                walk(child)

    walk(legend.get_children()[0])
    return found


def _probe_signatures(
    host: Axes,
    handles: list[Any],
    labels: list[str],
    handler_map: dict[Any, Any],
) -> list[_EntrySignature]:
    """What plain ``handles`` draw through ``handler_map``, via a detached legend."""
    probe = Legend(host, handles, labels, handler_map=handler_map)
    return _entry_signatures(probe)


def _rebuildable(
    legend: Legend, host: Axes, candidates: list[tuple[list[Any], list[str]]]
) -> bool:
    """Whether ``legend`` is what plain artists would draw, entry for entry.

    ``candidates`` are the (handles, labels) the legend may have been built
    from: the whole pair's artists (a hand merge, or the merged legend) or one
    Axes' own. The legend is rebuildable when its entries equal, position by
    position and in count, what some candidate draws through the legend's own
    ``handler_map``. Fails safe: an empty or unreadable legend, or any
    ``_UNREADABLE`` error while reading it or the probe, is not rebuildable.
    """
    handler_map: dict[Any, Any] = dict(legend.get_legend_handler_map())

    def read(
        signatures: Callable[[], list[_EntrySignature]],
    ) -> list[_EntrySignature] | None:
        # Only matplotlib's legend layout and a detached Legend are read
        # under the guard; the comparison below stays outside it, so a
        # defect there surfaces instead of reading as "leave it".
        try:
            return signatures()
        except _UNREADABLE:
            return None

    drawn = read(lambda: _entry_signatures(legend))
    if not drawn:
        return False
    for handles, labels in candidates:
        if not handles:
            continue
        probe = read(
            partial(_probe_signatures, host, handles, labels, handler_map)
        )
        if probe is not None and drawn == probe:
            return True
    return False


def _mark_placed(legend: Legend) -> None:
    """Mark ``legend`` as built by ``place_legend``, with its entries as built.

    ``_dm_placed_legend`` (documented) says the legend is the library's;
    ``_dm_placed_entries`` holds what its entries read now, so a later call
    can tell an entry the caller edited since (``[]`` when unreadable).
    """
    try:
        entries = _entry_signatures(legend)
    except _UNREADABLE:
        entries = []
    legend._dm_placed_legend = True  # type: ignore[attr-defined]
    legend._dm_placed_entries = entries  # type: ignore[attr-defined]


def _placed_as_built(legend: Legend) -> bool:
    """Whether ``place_legend`` built ``legend`` and its entries read as built.

    Such a legend is the library's: the next call rebuilds it from the
    artists drawn then (series added or removed since). One whose entries
    changed since (a text set by the caller) or cannot be read is not, and
    meets the structure rule of a caller's legend (:func:`_rebuildable`).
    """
    if getattr(legend, "_dm_placed_legend", False) is not True:
        return False
    built = getattr(legend, "_dm_placed_entries", None)
    if not built:
        return False
    try:
        now = _entry_signatures(legend)
    except _UNREADABLE:
        return False
    return bool(now == built)


def _legend_settings(
    legend: Legend | None, default: Legend | None
) -> dict[str, Any]:
    """The settings of ``legend`` a rebuilt legend repeats, as ``Legend`` keywords.

    Only what the public ``Legend`` API reads, and only what differs from
    ``default`` (a fresh legend of the same entries under the current
    preset), so an untouched default stays a default and follows a later
    style change. ``ncols`` has no public getter: pass it to ``place_legend``
    to keep it.
    """
    if legend is None or default is None:
        return {}
    kept: dict[str, Any] = {}
    title = legend.get_title()
    if title.get_text():
        kept["title"] = title.get_text()
    if title.get_fontproperties() != default.get_title().get_fontproperties():
        kept["title_fontproperties"] = title.get_fontproperties().copy()
    default_map = Legend.get_default_handler_map()
    custom = {
        key: handler
        for key, handler in legend.get_legend_handler_map().items()
        if default_map.get(key) is not handler
    }
    if custom:
        kept["handler_map"] = custom
    if legend.get_frame_on() != default.get_frame_on():
        kept["frameon"] = legend.get_frame_on()
    if legend.get_alignment() != default.get_alignment():
        kept["alignment"] = legend.get_alignment()
    if legend.markerscale != default.markerscale:
        kept["markerscale"] = legend.markerscale
    if legend.get_draggable():
        kept["draggable"] = True
    texts, defaults = legend.get_texts(), default.get_texts()
    if texts and defaults:
        if texts[0].get_fontproperties() != defaults[0].get_fontproperties():
            kept["prop"] = texts[0].get_fontproperties().copy()
        colors = {to_rgba(t.get_color()) for t in texts}
        if len(colors) == 1 and colors != {to_rgba(defaults[0].get_color())}:
            kept["labelcolor"] = to_hex(texts[0].get_color(), keep_alpha=True)
    return kept


def _caller_wins(kept: dict[str, Any], kw: dict[str, Any]) -> dict[str, Any]:
    """Kept settings under the caller's keywords; a caller size drops the kept font."""
    merged = {**kept, **kw}
    if "fontsize" in kw and "prop" not in kw:
        merged.pop("prop", None)
    if "title_fontsize" in kw and "title_fontproperties" not in kw:
        merged.pop("title_fontproperties", None)
    return merged


def _merge_twin_legends(
    ax: Axes,
) -> tuple[Axes, list[Any], list[str], dict[str, Any], Legend | None]:
    """One legend for a twin pair: every partner's entries, on the top axes.

    The legend goes on the top twin (the Axes drawn last), so no partner's
    data is drawn over it; the partners' own legends are removed after their
    settings (title, ``handler_map`` and so on) are read for the rebuild. A
    single Axes returns itself and its own entries.

    The last item is a legend to leave untouched: one that is not what the
    pair's own artists would draw (tuple handles, custom handlers, explicit
    labels). The explicit legend wins and nothing is removed. A legend an
    earlier ``place_legend`` built, its entries as built, is the library's
    and is always rebuilt from the artists now (:func:`_placed_as_built`).
    """
    owners = same_position_axes(ax)
    host = host_axes(ax)
    parent = host.get_figure(root=False)
    order = parent.axes if parent is not None else owners
    handles: list[Any] = []
    labels: list[str] = []
    seen: set[str] = set()
    for owner in sorted(owners, key=order.index):
        for handle, label in zip(*_legend_entries(owner), strict=True):
            if label not in seen:
                seen.add(label)
                handles.append(handle)
                labels.append(label)
    existing = [
        legend for o in owners if (legend := o.get_legend()) is not None
    ]
    for owner in owners:
        legend = owner.get_legend()
        if legend is None or _placed_as_built(legend):
            continue
        own = _legend_entries(owner)
        if not _rebuildable(legend, host, [(handles, labels), own]):
            return host, handles, labels, {}, legend
    source = host.get_legend() or next(iter(existing), None)
    default = Legend(host, handles, labels) if handles else None
    settings = _legend_settings(source, default)
    for owner in owners:
        legend = owner.get_legend()
        if owner is not host and legend is not None:
            legend.remove()
    return host, handles, labels, settings, None


def _place_untouched(legend: Legend, loc: str, kw: dict[str, Any]) -> Legend:
    """Follow an explicit placement on a legend that cannot be rebuilt.

    A matplotlib ``loc`` and ``bbox_to_anchor`` move it through ``set_loc`` /
    ``set_bbox_to_anchor``. A side (``"above"``...) and any other keyword
    need a rebuild: warn and leave the legend as it is.
    """
    ignored = sorted(
        k for k in kw if k not in {"bbox_to_anchor", "bbox_transform"}
    )
    if _parse_outside_side(loc) is not None:
        warnings.warn(
            f"place_legend(loc={loc!r}) needs to rebuild the legend, but its "
            "handles cannot be rebuilt faithfully (tuple handles, a custom "
            "handler or explicit labels); the legend is left as it is",
            UserWarning,
            stacklevel=3,
        )
        return legend
    if ignored:
        warnings.warn(
            f"place_legend left an explicit legend untouched; ignored {ignored}",
            UserWarning,
            stacklevel=3,
        )
    if loc != "best":
        legend.set_loc(cast("LegendLocType", loc))
    if "bbox_to_anchor" in kw:
        legend.set_bbox_to_anchor(
            kw["bbox_to_anchor"], kw.get("bbox_transform")
        )
    return legend


def _outside_fallback(
    ax: Axes, handles: list[Any], labels: list[str], kw: dict[str, Any]
) -> Legend:
    """Put the legend above ``ax`` because every in-axes spot covers data."""
    legend = _place_outside_legend(ax, handles, labels, "above", kw)
    legend._dm_collision_free = True  # type: ignore[attr-defined]
    legend._dm_collision_score = 0.0  # type: ignore[attr-defined]
    legend._dm_outside_fallback = True  # type: ignore[attr-defined]
    return legend


def place_legend(ax: Axes, *, loc: str = "best", **kw: Any) -> Legend | None:
    """Place or reposition an axes legend.

    ``loc="best"`` delegates to matplotlib for simple line-only axes. When the
    axes contains bars/collections/text obstacles or a tall legend, it scores
    four corners plus upper/lower center across one to three columns and
    selects the least obstructed in-axes location. When every in-axes
    location would cover data, the legend goes outside, above the axes (the
    ``loc="above"`` placement below), so no caller has to pick a side; a
    ``bbox_to_anchor`` / ``bbox_transform`` in ``kw`` keeps it inside. The
    returned Legend receives ``_dm_collision_free`` and
    ``_dm_collision_score`` attributes; ``_dm_outside_fallback`` is True when
    the legend went outside for that reason.

    ``loc="above"``, ``"below"``, ``"right"`` or ``"left"`` puts the legend
    outside the axes, centred on that side, past the side's tick labels and
    axis label (and a ``twinx`` / ``twiny`` partner's) by the preset's
    ``legend.borderaxespad`` gap. Above and below it takes one row when that
    row fits the axes width, otherwise the fewest rows that fit (rows are
    chosen for the axes width at call time); right and left it is one
    column. ``ncol`` / ``ncols`` in ``kw`` overrides the count, and
    ``bbox_to_anchor`` / ``bbox_transform`` raise ``ValueError`` because the
    side sets the anchor. :func:`dartwork_mpl.simple_layout` re-anchors such
    a legend to the labels present when it runs (and past the
    ``dm.label_bars`` values beyond that limit it would cover), makes room
    for it, and raises the axes titles above an ``"above"`` legend.
    ``dm.optimize_legend(ax, outside=True)`` also places a legend outside,
    at the top of the right side with its own font size and frame; prefer
    ``loc="right"`` here, which keeps the preset's legend style.

    A ``twinx`` / ``twiny`` pair gets one legend: the entries of every twin,
    on the twin drawn last (so no partner's data covers it), and the
    partners' own legends are removed. "Last" is by Axes zorder, then figure
    order, so the ``ax.set_zorder(twin.get_zorder() + 1)`` idiom puts the
    legend on ``ax``.

    The rebuilt legend keeps what the existing legend's public API reads: its
    title, ``handler_map``, ``frameon``, ``alignment``, ``markerscale``,
    ``draggable``, and the font properties (size, weight, family) of its title
    and entries and their colour, each only where it differs from the preset;
    keywords passed here win (a ``fontsize`` replaces the kept entry font).
    ``ncols`` cannot be read back, so pass it again.

    A legend that is not what the pair's own artists would draw (tuple
    handles, a custom handler, explicit labels) cannot be rebuilt faithfully
    and is returned untouched: the explicit legend wins, decided by the
    artist types each entry draws, not by its label. An explicit matplotlib
    ``loc`` or ``bbox_to_anchor`` still moves it (``set_loc`` /
    ``set_bbox_to_anchor``); ``loc="above"`` and the other sides, or any
    other keyword, need a rebuild, so they raise a ``UserWarning`` and the
    legend stays as it is. Any other ``loc`` is passed to
    ``ax.legend`` unchanged.

    A legend this function built is the library's (``_dm_placed_legend`` is
    True on it): the next call rebuilds it from the artists drawn then, so
    series added or removed since appear or go, with the settings above
    kept; with no labelled artist left it is removed and ``None`` returned.
    An entry text set on it since makes it the caller's, under the rule
    above.
    """
    ax, handles, labels, kept, untouched = _merge_twin_legends(ax)
    if untouched is not None:
        return _place_untouched(untouched, loc, kw)
    if not handles:
        if (legend := ax.get_legend()) is not None and _placed_as_built(legend):
            legend.remove()
        return None
    legend = _place_rebuilt(ax, handles, labels, loc, _caller_wins(kept, kw))
    _mark_placed(legend)
    return legend


def _place_rebuilt(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    loc: str,
    kw: dict[str, Any],
) -> Legend:
    """Draw the legend of ``ax`` from ``handles`` at ``loc`` (:func:`place_legend`)."""
    side = _parse_outside_side(loc)
    if side is not None:
        return _place_outside_legend(ax, list(handles), list(labels), side, kw)
    if loc != "best":
        return _legend_for_loc(ax, list(handles), list(labels), loc, kw)

    fig, renderer = _renderer_for_axes(ax)
    twins = len(same_position_axes(ax)) > 1
    has_obstacles = twins or bool(ax.patches or ax.collections or ax.texts)
    ncols = _legend_candidate_ncols(list(labels), kw)
    if not has_obstacles and len(labels) < 5 and ncols == [1]:
        legend = _legend_for_loc(ax, list(handles), list(labels), "best", kw)
        if not _may_go_outside(kw) or not _covers_data(ax, legend, renderer):
            return legend
        legend.remove()
        return _outside_fallback(ax, list(handles), list(labels), kw)

    old_legend = ax.get_legend()
    if old_legend is not None:
        old_legend.remove()

    data_bboxes = _pair_occupancy_bboxes(ax, renderer)
    try:
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        axes_bbox = Bbox.null()
    candidates: tuple[_LegendCandidate, ...] = (
        "upper right",
        "upper left",
        "lower left",
        "lower right",
        "upper center",
        "lower center",
    )
    trials: list[_LegendTrial] = []
    for ncol in ncols:
        legend_kw = dict(kw)
        legend_kw["ncol"] = ncol
        for candidate in candidates:
            legend = _legend_for_loc(
                ax, list(handles), list(labels), candidate, legend_kw
            )
            fig.canvas.draw()
            try:
                bbox = legend.get_window_extent(renderer)
            except BBOX_ERRORS:
                trials.append(_UnmeasuredLegend(candidate, ncol))
            else:
                trials.append(
                    _MeasuredLegend(
                        candidate,
                        ncol,
                        score=_score_legend_candidate(
                            bbox, data_bboxes, axes_bbox, ncol
                        ),
                        collision_free=(
                            _collision_area(bbox, data_bboxes) <= 0
                            and _outside_area(bbox, axes_bbox) <= 0
                        ),
                    )
                )
            legend.remove()

    best = _best_trial(trials)
    if _may_go_outside(kw) and not (
        isinstance(best, _MeasuredLegend) and best.collision_free
    ):
        return _outside_fallback(ax, list(handles), list(labels), kw)
    legend_kw = dict(kw)
    legend_kw["ncol"] = best.ncol
    legend = _legend_for_loc(
        ax, list(handles), list(labels), best.loc, legend_kw
    )
    _mark_placement(legend, best)
    return legend


_UNIT_SUFFIX_RE = re.compile(r"\s*([([][^)\]]{1,32}[)\]])\s*$")


def _split_label_two_lines(label: str) -> str | None:
    stripped = label.strip()
    if not stripped or "\n" in stripped:
        return None

    unit = ""
    body = stripped
    match = _UNIT_SUFFIX_RE.search(stripped)
    if match:
        unit = match.group(1)
        body = stripped[: match.start()].strip()

    words = body.split()
    if unit and len(words) == 1:
        return f"{body}\n{unit}"
    if len(words) < 2:
        return None

    target = len(body) / 2.0
    split_index = min(
        range(1, len(words)),
        key=lambda index: abs(len(" ".join(words[:index])) - target),
    )
    first = " ".join(words[:split_index])
    second = " ".join(words[split_index:])
    if unit:
        second = f"{second} {unit}" if second else unit
    if not first or not second:
        return None
    return f"{first}\n{second}"


def wrap_axis_label(ax: Axes, axis: str = "y", max_frac: float = 1.0) -> bool:
    """Wrap an overlong x/y-axis label to two lines at word boundaries.

    The rendered label length is compared with the corresponding axes spine
    length. Parenthesized or bracketed unit suffixes stay intact and are moved
    to the second line when wrapping is needed. Returns ``True`` only when the
    label text changed.
    """
    which = _parse_axis(axis, "axis must be 'x' or 'y'")
    if max_frac <= 0:
        raise ValueError("max_frac must be positive")

    label = ax.xaxis.label if which == "x" else ax.yaxis.label
    raw_text = label.get_text()
    wrapped = _split_label_two_lines(raw_text)
    if wrapped is None:
        return False

    _fig, renderer = _renderer_for_axes(ax)
    try:
        text_bbox = label.get_window_extent(renderer)
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return False
    rendered_length = text_bbox.width if which == "x" else text_bbox.height
    axis_length = axes_bbox.width if which == "x" else axes_bbox.height
    if rendered_length <= axis_length * float(max_frac):
        return False

    label.set_text(wrapped)
    return True


def wrap_axis_labels(
    fig: Figure | SubFigure, axis: str = "both", max_frac: float = 1.0
) -> list[Text]:
    """Wrap overlong axis labels for every axes in a figure.

    ``axis`` may be ``"x"``, ``"y"``, or ``"both"``. The returned list
    contains the label Text objects that were changed.
    """
    axes_to_wrap: tuple[_Axis, ...] = (
        ("x", "y")
        if axis == "both"
        else (_parse_axis(axis, "axis must be 'x', 'y', or 'both'"),)
    )
    changed: list[Text] = []
    for ax in fig.axes:
        for axis_name in axes_to_wrap:
            if wrap_axis_label(ax, axis_name, max_frac=max_frac):
                label = ax.xaxis.label if axis_name == "x" else ax.yaxis.label
                changed.append(label)
    return changed


def arrow_axis(
    ax: Axes,
    direction: str,
    label: str,
    *,
    offset: float = -0.10,
    low: str = "Low",
    high: str = "High",
    fontsize: float | None = None,
    fontsize_label: float | None = None,
    pad: float = -0.005,
    weight: str = "normal",
    color: str = "black",
    arrow_kw: dict[str, Any] | None = None,
) -> None:
    """Draw a bidirectional Low-High arrow axis along the edge of a plot.

    Produces a visual like ``Low ◄── label ──► High`` near the spine exterior.

    Parameters
    ----------
    ax : Axes
        Target Axes object for the annotation.
    direction : {'x', 'y'}
        "x": insert a horizontal arrow axis below the x-axis spine.
        "y": insert a vertical arrow axis to the left of the y-axis spine.
    label : str
        Center label text placed at the midpoint of the axis.
    offset : float, optional
        Offset from the spine in Axes-fraction units. Default is -0.10
        (sufficiently outside to avoid overlap with tick labels).
    low : str, optional
        Text for the low end (bottom/left) of the axis. Default is "Low".
    high : str, optional
        Text for the high end (top/right) of the axis. Default is "High".
    fontsize : float | None, optional
        Font size for the Low/High endpoint labels. Default is fs(-1).
    fontsize_label : float | None, optional
        Font size for the center label. Default is fs(0).
    pad : float, optional
        Fractional gap between text and arrowheads. Default is -0.005.
    weight : str, optional
        Font weight applied to all text elements.
    color : str, optional
        Color for both text and arrows. Default is "black".
    arrow_kw : dict | None, optional
        Override the arrowprops passed to the internal ``ax.annotate`` calls.
    """
    if fontsize is None:
        fontsize = fs(-1)
    along = _parse_axis(
        direction,
        f"direction must be 'x' or 'y', got {direction!r}. "
        "(Any other value would silently draw a y-axis arrow.)",
    )
    if fontsize_label is None:
        fontsize_label = fs(0)
    if arrow_kw is None:
        arrow_kw = {
            "arrowstyle": "-|>,head_width=0.1",
            "color": color,
            "lw": 0.25,
        }

    fig = ax.get_figure()
    if fig is None or fig.canvas is None:
        raise ValueError("Axes must be part of a Figure with a canvas")
    renderer = get_renderer(fig)
    inv = ax.transAxes.inverted()
    rot_kw: dict[str, Any] = (
        {"rotation": 90, "rotation_mode": "anchor"} if along == "y" else {}
    )

    # ── place texts ──────────────────────────────────────────
    if along == "x":
        p_lo: tuple[float, float] = (0.0, float(offset))
        p_hi: tuple[float, float] = (1.0, float(offset))
        p_lb: tuple[float, float] = (0.5, float(offset))
    else:
        p_lo = (float(offset), 0.0)
        p_hi = (float(offset), 1.0)
        p_lb = (float(offset), 0.5)

    t_lo = ax.text(
        *p_lo,
        low,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=weight,
        color=color,
        ha="left",
        va="center",
        clip_on=False,
        **rot_kw,
    )
    t_hi = ax.text(
        *p_hi,
        high,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=weight,
        color=color,
        ha="right",
        va="center",
        clip_on=False,
        **rot_kw,
    )
    t_lb = ax.text(
        *p_lb,
        label,
        transform=ax.transAxes,
        fontsize=fontsize_label,
        fontweight=weight,
        color=color,
        ha="center",
        va="center",
        clip_on=False,
        **rot_kw,
    )

    # ── measure extents in axes fraction ─────────────────────
    fig.canvas.draw()

    def _edges(t: Text) -> np.ndarray[Any, Any]:
        bb = t.get_window_extent(renderer)
        return inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])

    i = 0 if along == "x" else 1
    lo_end = _edges(t_lo)[1][i]
    hi_start = _edges(t_hi)[0][i]
    lb_lo = _edges(t_lb)[0][i]
    lb_hi = _edges(t_lb)[1][i]

    # ── draw arrows ──────────────────────────────────────────
    def _arrow(tip: float, tail: float) -> None:
        if along == "x":
            ax.annotate(
                "",
                xy=(tip, offset),
                xytext=(tail, offset),
                xycoords="axes fraction",
                arrowprops=arrow_kw,
                annotation_clip=False,
            )
        else:
            ax.annotate(
                "",
                xy=(offset, tip),
                xytext=(offset, tail),
                xycoords="axes fraction",
                arrowprops=arrow_kw,
                annotation_clip=False,
            )

    _arrow(lo_end + pad, lb_lo - pad)
    _arrow(hi_start - pad, lb_hi + pad)


def make_offset(x: float, y: float, fig: Figure) -> ScaledTranslation:
    """Return a point-unit offset transform for the figure's DPI.

    ``ScaledTranslation(x / 72, y / 72, fig.dpi_scale_trans)``: the offset is
    given in points and converted to pixels by the Figure's
    ``dpi_scale_trans``, so it keeps its physical size at any DPI. Add it to
    another transform (``ax.transData + dm.make_offset(0, 4, fig)``) to nudge
    text or markers.

    Parameters
    ----------
    x : float
        Horizontal offset in points.
    y : float
        Vertical offset in points.
    fig : matplotlib.figure.Figure
        The Figure whose DPI scale is used.

    Returns
    -------
    matplotlib.transforms.ScaledTranslation
        A translation transform that can be added to other transforms.
    """
    dx, dy = x / 72, y / 72
    return ScaledTranslation(dx, dy, fig.dpi_scale_trans)
