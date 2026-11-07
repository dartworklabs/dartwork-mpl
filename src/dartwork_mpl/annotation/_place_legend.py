"""place_legend: candidate scoring, outside placement and the fallback that moves a legend outside the Axes."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, cast

from matplotlib.axes import Axes
from matplotlib.legend import Legend
from matplotlib.transforms import Bbox

from .._figure_geometry import (
    BBOX_ERRORS,
    OutsideSide,
    anchor_outside,
    same_position_axes,
)
from ._legend_entries import (
    _caller_wins,
    _mark_placed,
    _merge_twin_legends,
    _placed_as_built,
)
from ._placement_geometry import (
    _collision_area,
    _data_occupancy_bboxes,
    _outside_area,
    _overlap_area,
    _renderer_for_axes,
)

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.typing import LegendLocType


_LegendCandidate = Literal[
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "upper center",
    "lower center",
]


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
