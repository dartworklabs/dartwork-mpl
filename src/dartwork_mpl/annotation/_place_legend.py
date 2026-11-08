"""place_legend: the ``loc="best"`` ladder (a free inside spot, else outside, else the least covering spot) and named sides."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from matplotlib.axes import Axes
from matplotlib.legend import Legend
from matplotlib.transforms import Bbox

from .._figure_geometry import BBOX_ERRORS, OutsideSide
from ._legend_entries import (
    _caller_wins,
    _mark_placed,
    _merge_twin_legends,
    _placed_as_built,
)
from ._legend_fit import (
    CLEARANCE_PT,
    INSIDE_LOCS,
    TALL_SHARE,
    InsideSpot,
    anchored_box,
    legend_pad,
    legend_size,
    measure_ink,
    outside_area,
    points_px,
    probe,
)
from ._legend_outside import (
    Sizes,
    choose,
    draw_outside,
    outside_fallback,
    side_plans,
    split_ncols,
)
from ._placement_geometry import _renderer_for_axes

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.typing import LegendLocType


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


def _parse_outside_side(loc: str) -> OutsideSide | None:
    """Return ``loc`` as an outside side, or ``None`` for a matplotlib ``loc``."""
    match loc:
        case "above" | "below" | "right" | "left":
            return loc
        case _:
            return None


@dataclass(frozen=True)
class BestSource:
    """What a ``loc="best"`` legend was placed from, for ``settle_legends``."""

    handles: list[Any]
    labels: list[str]
    kw: dict[str, Any]


def inside_spots(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    kw: dict[str, Any],
    renderer: RendererBase,
) -> list[InsideSpot]:
    """Every inside spot for one to three columns, measured without drawing.

    A trial legend per column count gives the size; each spot's box is
    where matplotlib anchors that size (:func:`anchored_box`), and it is
    free when it stays inside the Axes and no data ink of the Axes or its
    twins comes within :data:`CLEARANCE_PT` of it. The order is column
    count, then :data:`INSIDE_LOCS`. ``ncol`` / ``ncols`` in ``kw`` is the
    only count tried.
    """
    legend_kw, explicit = split_ncols(kw)
    ncols = (
        [explicit]
        if explicit is not None
        else list(range(1, min(3, max(len(labels), 1)) + 1))
    )
    ink = measure_ink(ax, renderer)
    clearance = points_px(renderer, CLEARANCE_PT)
    try:
        axes_box = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return []
    spots: list[InsideSpot] = []
    for ncol in ncols:
        trial = probe(
            ax, handles, labels, loc="upper right", ncols=ncol, **legend_kw
        )
        try:
            size = legend_size(trial, renderer)
            parent = Bbox(trial.get_bbox_to_anchor().get_points())
            pad = legend_pad(trial, renderer)
        except BBOX_ERRORS:
            continue
        tall = 0.0
        if ncol == 1:
            tall = max(0.0, size[1] / max(axes_box.height, 1.0) - TALL_SHARE)
        area = max(size[0] * size[1], 1.0)
        for loc in INSIDE_LOCS:
            box = anchored_box(loc, size, parent, pad)
            spots.append(
                InsideSpot(
                    loc,
                    ncol,
                    met=len(ink.met(box, clearance)),
                    overflow=outside_area(box, axes_box) / area,
                    tall=tall,
                )
            )
    return spots


def first_free(spots: list[InsideSpot]) -> InsideSpot | None:
    """The first free spot, a one-column legend taller than :data:`TALL_SHARE` last."""
    free = [spot for spot in spots if spot.free]
    return min(free, key=lambda spot: spot.tall) if free else None


def draw_inside(
    ax: Axes,
    handles: list[Any],
    labels: list[str],
    spot: InsideSpot,
    kw: dict[str, Any],
) -> Legend:
    """Draw the legend of ``ax`` at a free inside ``spot``."""
    legend_kw, _explicit = split_ncols(kw)
    legend = _legend_for_loc(
        ax, handles, labels, spot.loc, {**legend_kw, "ncols": spot.ncol}
    )
    legend._dm_collision_free = True  # type: ignore[attr-defined]
    legend._dm_collision_score = spot.tall  # type: ignore[attr-defined]
    legend._dm_inside_spot = (spot.loc, spot.ncol)  # type: ignore[attr-defined]
    return legend


def _may_go_outside(kw: dict[str, Any]) -> bool:
    """Whether a ``best`` legend may fall back outside (no caller anchor)."""
    return "bbox_to_anchor" not in kw and "bbox_transform" not in kw


def _climb(
    ax: Axes, handles: list[Any], labels: list[str], kw: dict[str, Any]
) -> Legend:
    """The ``loc="best"`` ladder: a free inside spot, else outside, else the least covering spot.

    1. Inside: :func:`first_free` of :func:`inside_spots`.
    2. Outside, with no caller anchor and ``dm.config.legend_fallback``
       not ``"inside"``: :func:`~._legend_outside.outside_fallback`.
    3. The inside spot that meets the fewest artists;
       ``_dm_collision_free`` is then False and ``dm.validate_figure``
       reports ``LEGEND_ON_DATA``.
    """
    _fig, renderer = _renderer_for_axes(ax)
    old = ax.get_legend()
    if old is not None:
        old.remove()
    spots = inside_spots(ax, handles, labels, kw, renderer)
    spot = first_free(spots)
    if spot is not None:
        return draw_inside(ax, handles, labels, spot, kw)
    if _may_go_outside(kw):
        outside = outside_fallback(ax, handles, labels, kw, renderer)
        if outside is not None:
            return outside
    if not spots:  # nothing could be measured
        legend = _legend_for_loc(ax, handles, labels, "upper right", kw)
        legend._dm_collision_free = False  # type: ignore[attr-defined]
        legend._dm_collision_score = float("inf")  # type: ignore[attr-defined]
        return legend
    least = min(spots, key=InsideSpot.rank)
    legend_kw, _explicit = split_ncols(kw)
    legend = _legend_for_loc(
        ax, handles, labels, least.loc, {**legend_kw, "ncols": least.ncol}
    )
    legend._dm_collision_free = False  # type: ignore[attr-defined]
    legend._dm_collision_score = float(least.met)  # type: ignore[attr-defined]
    return legend


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
    _fig, renderer = _renderer_for_axes(ax)
    sizes: Sizes = {}
    plans = side_plans(
        ax, handles, labels, side, kw, renderer, named=True, sizes=sizes
    )
    return draw_outside(ax, handles, labels, choose(plans), kw, renderer, sizes)


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


def place_legend(ax: Axes, *, loc: str = "best", **kw: Any) -> Legend | None:
    """Place or reposition an axes legend.

    ``loc="best"`` climbs a ladder and stops at the first step that covers
    no data:

    1. Inside: four corners, upper and lower centre, then centre right and
       left, for one to three columns (fewest columns first). A spot is free
       when its box stays inside the axes and no data ink of the axes or its
       twins comes within 2 pt of it: lines at their width, markers and
       scatter points at their size, bars and other patches, filled areas,
       and the axes' texts such as value labels. Spots are measured where
       matplotlib anchors them, without redrawing the figure. A one-column
       legend taller than 55 % of the axes goes last.
    2. Outside, when no spot is free and no ``bbox_to_anchor`` /
       ``bbox_transform`` is given: above, right or below, among the sides
       no other panel sits beyond, whichever takes the smaller share of the
       plot. Above is the default; another side wins only when it takes at
       least 10 % less and 5 % of the plot less. A side another panel's
       legend already took wins when it fits as well, so the panels of one
       figure agree. Long entry names are broken at spaces only when the
       legend would otherwise not fit (``dm.config.legend_wrap``).
       ``dm.config.legend_fallback`` fixes the side (``"above"``,
       ``"right"``, ``"below"``) or keeps the legend inside (``"inside"``).
    3. Otherwise the inside spot that meets the fewest artists;
       ``dm.validate_figure`` then reports ``LEGEND_ON_DATA``.

    :func:`dartwork_mpl.simple_layout` places such a legend again at the
    size it gives the axes: an inside legend takes an earlier free spot and
    an outside one comes inside when a spot is free now (never the other
    way), and an outside one keeps its side with its rows chosen again.

    The returned Legend receives ``_dm_collision_free`` and
    ``_dm_collision_score`` attributes; ``_dm_outside_fallback`` is True when
    the legend went outside for that reason.

    ``loc="above"``, ``"below"``, ``"right"`` or ``"left"`` puts the legend
    outside the axes, centred on that side, past the side's tick labels and
    axis label (and a ``twinx`` / ``twiny`` partner's) by the preset's
    ``legend.borderaxespad`` gap. Above and below it takes one row when that
    row fits the axes width, otherwise the fewest rows that fit; right and
    left it is one column, or the fewest columns no taller than the axes.
    Names wider than the axes above or below, or a right or left legend
    wider than 40 % of the axes, are broken at spaces, a trailing bracketed
    unit such as ``(2019 = 100)`` kept whole (``dm.config.legend_wrap``).
    :func:`dartwork_mpl.simple_layout` chooses the rows (right and left: the
    columns) again for the axes size it settles on, re-anchors the legend to
    the labels present when it runs (and past the ``dm.label_bars`` values
    beyond that limit it would cover), makes room for it, and raises the
    axes titles above an ``"above"`` legend. ``ncol`` / ``ncols`` in ``kw``
    overrides the count, and ``bbox_to_anchor`` / ``bbox_transform`` raise
    ``ValueError`` because the side sets the anchor.
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
    ``ax.legend`` unchanged, and the layout leaves it where matplotlib puts
    it.

    A legend this function built is the library's (``_dm_placed_legend`` is
    True on it): the next call rebuilds it from the artists drawn then, so
    series added or removed since appear or go, with the settings above
    kept; with no labelled artist left it is removed and ``None`` returned.
    An entry text set on it since makes it the caller's, under the rule
    above, and the layout no longer moves it.
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
    legend = _climb(ax, list(handles), list(labels), kw)
    legend._dm_best_source = BestSource(list(handles), list(labels), dict(kw))  # type: ignore[attr-defined]
    return legend


__all__ = [
    "BestSource",
    "draw_inside",
    "first_free",
    "inside_spots",
    "place_legend",
]
