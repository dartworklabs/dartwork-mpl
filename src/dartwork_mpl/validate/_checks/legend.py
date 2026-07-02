"""LEGEND_OVERFLOW: legend that occupies too much of its axes area."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._registry import register_check

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_legend_overflow"]

_THRESHOLD = 0.30  # 30% of axes area


@register_check("LEGEND_OVERFLOW", order=40)
def check_legend_overflow(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect legends that dominate their axes or spill past the figure.

    Two failure modes: (1) an in-axes legend covering too large a
    fraction of the axes; (2) a legend anchored outside the axes
    (``bbox_to_anchor``) or a figure-level ``fig.legend`` that runs off
    the canvas — the area ratio can't see the latter (its overlap with
    the axes is ~0), so it is caught by a separate figure-bounds test.
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
                    detail={
                        "axes_index": i,
                        "ratio": round(ratio, 3),
                        "threshold": _THRESHOLD,
                    },
                )
            )
        else:
            spill = _overflows_figure(leg_ext)
            if spill > 2.0:
                warnings.append(
                    VisualWarning(
                        severity=Severity.WARNING,
                        check_id="LEGEND_OVERFLOW",
                        message=(
                            f"Legend on axes[{i}] extends {spill:.0f}px "
                            f"past the figure edge (anchored outside "
                            f"the axes)"
                        ),
                        detail={
                            "axes_index": i,
                            "overflow_px": round(spill, 1),
                        },
                    )
                )

    # Figure-level legends (``fig.legend``) never appear via
    # ``ax.get_legend()``; flag them when they run off the canvas.
    for legend in fig.legends:
        if not legend.get_visible():
            continue
        try:
            leg_ext = legend.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        spill = _overflows_figure(leg_ext)
        if spill > 2.0:
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="LEGEND_OVERFLOW",
                    message=(
                        f"Figure legend extends {spill:.0f}px past the "
                        f"figure edge"
                    ),
                    detail={"axes_index": None, "overflow_px": round(spill, 1)},
                )
            )

    return warnings
