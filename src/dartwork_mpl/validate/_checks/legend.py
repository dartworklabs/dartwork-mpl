"""LEGEND_OVERFLOW: a legend too large for its plot, or one off the canvas."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from ..._figure_geometry import same_position_axes
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import wire
from ._registry import register_check, register_fix

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_legend_overflow"]


class LegendAreaDetail(TypedDict):
    """An Axes legend covers ``ratio`` of its Axes, above ``threshold``."""

    axes_index: int
    ratio: float
    threshold: float


class LegendSpillDetail(TypedDict):
    """An Axes legend spills ``overflow_px`` past the figure."""

    axes_index: int
    overflow_px: float


class FigureLegendSpillDetail(TypedDict):
    """A figure legend spills past the figure; it belongs to no Axes."""

    axes_index: None
    overflow_px: float


class LegendSizeDetail(TypedDict):
    """A legend outside its plot is ``ratio`` of that plot's area, above ``threshold``.

    ``axes_index`` is ``None`` for a figure legend, measured against the
    plot boxes of the figure's visible Axes (twins counted once).
    """

    axes_index: int | None
    outside_ratio: float
    threshold: float


_THRESHOLD = 0.30  # 30% of axes area
_OUTSIDE_THRESHOLD = 0.50  # an outside legend half the size of its plot
_SPILL_PX = 2.0


@register_check("LEGEND_OVERFLOW", order=40)
def check_legend_overflow(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect legends that dominate their axes or spill past the figure.

    Three failure modes: (1) an in-axes legend covering too large a
    fraction of the axes; (2) a legend anchored outside the axes
    (``bbox_to_anchor``) or a figure-level ``fig.legend`` that runs off
    the canvas — the area ratio can't see the latter (its overlap with
    the axes is ~0), so it is caught by a separate figure-bounds test;
    (3) a legend outside the axes that stays on the canvas but is more
    than half the size of its plot (a figure legend: of the panels), so
    the layout that makes room for it squeezes the plot.
    """
    warnings: list[VisualWarning] = []
    fig_bbox = fig.bbox

    def _overflows_figure(leg_ext: Any) -> float:
        return float(
            max(
                fig_bbox.x0 - leg_ext.x0,
                leg_ext.x1 - fig_bbox.x1,
                fig_bbox.y0 - leg_ext.y0,
                leg_ext.y1 - fig_bbox.y1,
            )
        )

    for i, ax in enumerate(fig.axes):
        legend = ax.get_legend()
        if legend is None or not legend.get_visible():
            continue
        try:
            leg_ext = legend.get_window_extent(renderer)
            ax_ext = ax.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue

        ax_area = ax_ext.width * ax_ext.height
        if ax_area <= 0:
            continue

        # Intersection of legend bbox with axes bbox
        x0 = max(leg_ext.x0, ax_ext.x0)
        y0 = max(leg_ext.y0, ax_ext.y0)
        x1 = min(leg_ext.x1, ax_ext.x1)
        y1 = min(leg_ext.y1, ax_ext.y1)
        overlap_area = max(0, x1 - x0) * max(0, y1 - y0)
        ratio = overlap_area / ax_area

        if ratio > _THRESHOLD:
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="LEGEND_OVERFLOW",
                    message=(
                        f"Legend occupies {ratio:.1%} of axes[{i}] area "
                        f"(threshold: {_THRESHOLD:.0%})"
                    ),
                    detail=wire(
                        LegendAreaDetail(
                            axes_index=i,
                            ratio=round(ratio, 3),
                            threshold=_THRESHOLD,
                        )
                    ),
                )
            )
            continue
        spill = _overflows_figure(leg_ext)
        legend_area = leg_ext.width * leg_ext.height
        if spill <= _SPILL_PX and legend_area > _OUTSIDE_THRESHOLD * ax_area:
            outside_ratio = legend_area / ax_area
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="LEGEND_OVERFLOW",
                    message=(
                        f"Legend of axes[{i}] is {outside_ratio:.0%} the size "
                        f"of its plot (threshold: {_OUTSIDE_THRESHOLD:.0%}); "
                        "name the lines at their ends, shorten the names or "
                        "use a larger canvas"
                    ),
                    detail=wire(
                        LegendSizeDetail(
                            axes_index=i,
                            outside_ratio=round(float(outside_ratio), 3),
                            threshold=_OUTSIDE_THRESHOLD,
                        )
                    ),
                )
            )
        elif spill > _SPILL_PX:
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="LEGEND_OVERFLOW",
                    message=(
                        f"Legend on axes[{i}] extends {spill:.0f}px "
                        f"past the figure edge (anchored outside "
                        f"the axes)"
                    ),
                    detail=wire(
                        LegendSpillDetail(
                            axes_index=i, overflow_px=round(spill, 1)
                        )
                    ),
                )
            )

    # Figure-level legends (``fig.legend``) never appear via
    # ``ax.get_legend()``; flag them when they run off the canvas, or when
    # they are more than half the size of the panels they serve.
    panel_area = _panel_area(fig, renderer)
    for legend in fig.legends:
        if not legend.get_visible():
            continue
        try:
            leg_ext = legend.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        spill = _overflows_figure(leg_ext)
        legend_area = leg_ext.width * leg_ext.height
        if (
            spill <= _SPILL_PX
            and panel_area > 0
            and legend_area > _OUTSIDE_THRESHOLD * panel_area
        ):
            ratio = legend_area / panel_area
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="LEGEND_OVERFLOW",
                    message=(
                        f"Figure legend is {ratio:.0%} the size of the "
                        f"panels (threshold: {_OUTSIDE_THRESHOLD:.0%}); "
                        "name the lines at their ends, shorten the names or "
                        "use a larger canvas"
                    ),
                    detail=wire(
                        LegendSizeDetail(
                            axes_index=None,
                            outside_ratio=round(float(ratio), 3),
                            threshold=_OUTSIDE_THRESHOLD,
                        )
                    ),
                )
            )
        if spill > _SPILL_PX:
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="LEGEND_OVERFLOW",
                    message=(
                        f"Figure legend extends {spill:.0f}px past the "
                        f"figure edge"
                    ),
                    detail=wire(
                        FigureLegendSpillDetail(
                            axes_index=None, overflow_px=round(spill, 1)
                        )
                    ),
                )
            )

    return warnings


def _panel_area(fig: Figure, renderer: RendererBase) -> float:
    """Summed plot-box area of the visible Axes, each twin group once."""
    seen: set[int] = set()
    area = 0.0
    for ax in fig.axes:
        if not ax.get_visible() or id(ax) in seen:
            continue
        seen.update(id(owner) for owner in same_position_axes(ax))
        try:
            box = ax.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        area += box.width * box.height
    return area


@register_fix("LEGEND_OVERFLOW")
def _fix_legend_overflow(_warning: VisualWarning) -> list[str]:
    return [
        "# Many lines: name them at their ends instead of a legend\n"
        "dm.label_line_ends(ax)\ndm.simple_layout(fig)",
        "# Move legend outside\nax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')",
        "# Reduce legend columns\nax.legend(ncol=1)",
        "# Reduce legend font\nax.legend(fontsize=dm.fs(-2))",
    ]
