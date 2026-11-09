"""TICK_CORNER_OVERLAP: an x tick label on a y tick label at a plot corner.

When both axes end on a tick, the first bottom label and the lowest left
label meet at the corner (the ``-3`` and ``-3`` of a -3..3 square); a first
category name wide enough reaches under the y labels the same way. Any
corner counts, labels on top or on the right too, and the right labels of
a ``twinx``. ``TICK_OVERLAP`` compares neighbours along one axis and
``CROSS_AXES_OVERLAP`` other plots, so neither sees such a pair. Rectilinear
Axes only; the measure is ``_figure_geometry.corner_tick_overlaps``, which
the layout's ``pad`` step also uses.

``dm.simple_layout`` moves the labels of one axis out by the overlap plus a
hair space (the axis whose labels move less, through its tick pad); what
this check reports after a layout is what is left: both pads set by hand,
or a change the layout took back. The fix grows that pad by hand; it
never hides a label, makes text smaller or moves the axis limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from ..._figure_geometry import (
    CORNER_GAP_EM,
    corner_tick_overlaps,
    same_position_axes,
    tick_pad,
)
from .._types import Severity, VisualWarning
from ._detail import AXES, Axis, choice, number, wire
from ._registry import register_check, register_fix

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_tick_corner_overlap"]


class TickCornerOverlapDetail(TypedDict):
    """``pairs`` x / y tick label pairs of one plot box overlap, by up to ``px``.

    ``corner`` and ``x_label`` / ``y_label`` name the deepest pair;
    ``axis`` is the axis whose labels move less to clear every pair and
    ``pad`` the label pad (pt) that clears them.
    """

    axes_index: int
    corner: str
    x_label: str
    y_label: str
    pairs: int
    px: float
    axis: Axis
    pad: float


@register_check("TICK_CORNER_OVERLAP", order=53)
def check_tick_corner_overlap(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Report x tick labels that overlap a y tick label of the same plot box."""
    warnings: list[VisualWarning] = []
    seen: set[int] = set()
    for index, ax in enumerate(fig.axes):
        if id(ax) in seen or not _rectilinear(ax):
            continue
        group = [m for m in same_position_axes(ax) if _rectilinear(m)]
        seen.update(id(m) for m in group)
        pairs = corner_tick_overlaps(group, renderer)
        if not pairs:
            continue
        deepest = max(pairs, key=lambda pair: pair.depth)
        to_pt = 72.0 / fig.dpi
        # what the x labels (down / up) or the y labels (left / right) move
        need_x = max(
            pair.down * to_pt
            + CORNER_GAP_EM * float(pair.x_label.get_fontsize())
            for pair in pairs
        )
        need_y = max(
            pair.across * to_pt
            + CORNER_GAP_EM * float(pair.y_label.get_fontsize())
            for pair in pairs
        )
        axis_name: Axis = "x" if need_x <= need_y else "y"
        moved = (
            deepest.x_axes.xaxis if axis_name == "x" else deepest.y_axes.yaxis
        )
        pad = tick_pad(moved.get_major_ticks()[0]) + min(need_x, need_y)
        warnings.append(
            VisualWarning(
                severity=Severity.WARNING,
                check_id="TICK_CORNER_OVERLAP",
                message=(
                    f"Axes[{index}]: x tick label "
                    f"{deepest.x_label.get_text()!r} overlaps y tick label "
                    f"{deepest.y_label.get_text()!r} at the {deepest.corner} "
                    f"corner ({len(pairs)} pair(s), up to "
                    f"{deepest.depth:.1f}px)"
                ),
                detail=wire(
                    TickCornerOverlapDetail(
                        axes_index=index,
                        corner=deepest.corner,
                        x_label=deepest.x_label.get_text(),
                        y_label=deepest.y_label.get_text(),
                        pairs=len(pairs),
                        px=round(deepest.depth, 1),
                        axis=axis_name,
                        pad=round(pad, 1),
                    )
                ),
            )
        )
    return warnings


def _rectilinear(ax: Axes) -> bool:
    return ax.get_visible() and getattr(ax, "name", None) == "rectilinear"


@register_fix("TICK_CORNER_OVERLAP")
def _fix_tick_corner_overlap(warning: VisualWarning) -> list[str]:
    """The layout's move first, then the same pad by hand; never hide or shrink."""
    axis = choice(warning.detail, "axis", AXES) or "x"
    pad = number(warning.detail, "pad", 0)
    return [
        "# The layout moves the labels of one axis out (its tick pad)\n"
        "dm.simple_layout(fig)",
        "# Pads you set stay as set: grow the one that moves less\n"
        f"ax.tick_params(axis={axis!r}, pad={pad:g})",
    ]
