"""settle_legends: the layout's pass that places ``place_legend``'s legends again at the Axes size it settles on."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._legend_entries import _mark_placed, _placed_as_built
from ._legend_outside import (
    OutsidePlan,
    OutsideSource,
    choose,
    draw_outside,
    plan_side,
    side_plans,
    split_ncols,
    trial_pad,
)
from ._place_legend import BestSource, draw_inside, first_free, inside_spots

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.legend import Legend

#: Attributes a rebuilt legend carries over from the one it replaces.
_KEPT = (
    "_dm_collision_free",
    "_dm_collision_score",
    "_dm_outside_fallback",
    "_dm_best_source",
    "_dm_settled_size",
)


def _half_px(ax: Axes, renderer: RendererBase) -> tuple[int, int]:
    """The Axes' size in half-px steps: a size that moved less is the same."""
    box = ax.get_window_extent(renderer)
    return round(box.width * 2), round(box.height * 2)


def _settle_inside(ax: Axes, legend: Legend, renderer: RendererBase) -> bool:
    """Move a ``loc="best"`` legend to the first inside spot free at the size now.

    Only towards the inside: a legend inside takes a free spot earlier in
    the ladder's order, and one outside comes in when a spot is free now.
    Coming in gives the Axes room, so the spot stays free; a legend is
    never sent out here (``dm.validate_figure`` reports one that now
    covers data). Returns whether the legend was rebuilt.
    """
    source = getattr(legend, "_dm_best_source", None)
    if not isinstance(source, BestSource):
        return False
    size = _half_px(ax, renderer)
    if getattr(legend, "_dm_settled_size", None) == size:
        return False
    legend._dm_settled_size = size  # type: ignore[attr-defined]
    spot = first_free(
        inside_spots(ax, source.handles, source.labels, source.kw, renderer)
    )
    if spot is None:
        return False
    if getattr(legend, "_dm_inside_spot", None) == (spot.loc, spot.ncol):
        return False
    rebuilt = draw_inside(ax, source.handles, source.labels, spot, source.kw)
    rebuilt._dm_best_source = source  # type: ignore[attr-defined]
    rebuilt._dm_settled_size = size  # type: ignore[attr-defined]
    _mark_placed(rebuilt)
    return True


def _replan(
    ax: Axes, legend: Legend, source: OutsideSource, renderer: RendererBase
) -> OutsidePlan:
    """The plan for the legend's side at the Axes size now.

    Above and below: rows and wrapping chosen again (the width does not
    depend on such a legend, so this settles). Right and left: only the
    column count for the height now, with the names kept as they are.
    """
    side = source.plan.side
    if side in ("above", "below"):
        return choose(
            side_plans(
                ax,
                source.handles,
                source.labels,
                side,
                source.kw,
                renderer,
                named=not getattr(legend, "_dm_outside_fallback", False),
                sizes=source.sizes,
            )
        )
    legend_kw, explicit = split_ncols(source.kw)
    pad = trial_pad(
        ax, source.handles, source.labels, legend_kw, renderer, source.sizes
    )
    return plan_side(
        ax,
        source.handles,
        source.plan.labels,
        side,
        legend_kw,
        explicit,
        renderer,
        ax.get_window_extent(renderer),
        pad,
        source.sizes,
    )


def _settle_outside(ax: Axes, legend: Legend, renderer: RendererBase) -> bool:
    """Choose an outside legend's rows (or columns) again at the Axes size now.

    The side never changes. Returns whether the legend was rebuilt.
    """
    source = getattr(legend, "_dm_outside_source", None)
    if not isinstance(source, OutsideSource):
        return False
    box = ax.get_window_extent(renderer)
    if (
        abs(box.width - source.size[0]) <= 0.5
        and abs(box.height - source.size[1]) <= 0.5
    ):
        return False
    plan = _replan(ax, legend, source, renderer)
    if (plan.ncols, plan.labels) == (source.plan.ncols, source.plan.labels):
        legend._dm_outside_source = OutsideSource(  # type: ignore[attr-defined]
            source.handles,
            source.labels,
            source.kw,
            source.plan,
            (box.width, box.height),
            source.sizes,
        )
        return False
    kept: dict[str, Any] = {
        name: getattr(legend, name) for name in _KEPT if hasattr(legend, name)
    }
    rebuilt = draw_outside(
        ax,
        source.handles,
        source.labels,
        plan,
        source.kw,
        renderer,
        source.sizes,
    )
    for name, value in kept.items():
        setattr(rebuilt, name, value)
    _mark_placed(rebuilt)
    return True


def settle_legends(fig: Figure | SubFigure, renderer: RendererBase) -> bool:
    """Place ``place_legend``'s legends again at the size the Axes have now.

    ``dm.place_legend`` decides at the size the Axes has when it is called;
    ``dm.simple_layout`` then resizes the Axes and runs this before it
    measures. A ``loc="best"`` legend takes the first inside spot free now
    (inwards only); an outside legend keeps its side, with its rows (right
    and left: its columns) chosen again. A legend whose entries were edited
    since is the caller's and is left alone, and so is any legend
    ``place_legend`` did not build. Returns whether a legend changed.
    """
    changed = False
    for ax in list(fig.axes):
        legend = ax.get_legend()
        if legend is None or not _placed_as_built(legend):
            continue
        if _settle_inside(ax, legend, renderer):
            changed = True
            continue
        if _settle_outside(ax, legend, renderer):
            changed = True
    return changed


__all__ = ["settle_legends"]
