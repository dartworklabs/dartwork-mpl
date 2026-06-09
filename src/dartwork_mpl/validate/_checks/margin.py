"""MARGIN_ASYMMETRY: one side of the figure carries much more whitespace."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from .._types import BBOX_ERRORS, Severity, VisualWarning

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_margin_asymmetry"]

_RATIO_THRESHOLD = 3.0
_MIN_MARGIN_PX = 30  # ignore sides with very small margins


def check_margin_asymmetry(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect asymmetric whitespace — one side much emptier than its opposite."""
    warnings: list[VisualWarning] = []
    fig_bbox = fig.bbox

    # Collect tight bounding boxes of all visual content.
    all_extents = []
    for ax in fig.axes:
        try:
            tb = ax.get_tightbbox(renderer)
            if tb is not None:
                all_extents.append(tb)
        except BBOX_ERRORS:
            continue
        # Include text objects outside axes (annotations, pie labels).
        for txt in ax.texts:
            if txt.get_visible() and txt.get_text().strip():
                with contextlib.suppress(*BBOX_ERRORS):
                    all_extents.append(txt.get_window_extent(renderer))

    if not all_extents:
        return warnings

    content_x0 = min(e.x0 for e in all_extents)
    content_x1 = max(e.x1 for e in all_extents)
    content_y0 = min(e.y0 for e in all_extents)
    content_y1 = max(e.y1 for e in all_extents)

    left_margin = max(0.0, content_x0 - fig_bbox.x0)
    right_margin = max(0.0, fig_bbox.x1 - content_x1)
    bottom_margin = max(0.0, content_y0 - fig_bbox.y0)
    top_margin = max(0.0, fig_bbox.y1 - content_y1)

    # Horizontal comparison
    if left_margin > _MIN_MARGIN_PX and right_margin > _MIN_MARGIN_PX:
        ratio = max(left_margin, right_margin) / min(left_margin, right_margin)
        if ratio > _RATIO_THRESHOLD:
            side = "right" if right_margin > left_margin else "left"
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="MARGIN_ASYMMETRY",
                    message=(
                        f"Horizontal margin asymmetry: {side} has {ratio:.1f}x "
                        f"more space (L={left_margin:.0f}px, R={right_margin:.0f}px)"
                    ),
                    detail={
                        "axis": "horizontal",
                        "side": side,
                        "ratio": round(ratio, 1),
                        "left_px": round(left_margin),
                        "right_px": round(right_margin),
                    },
                )
            )

    # Vertical comparison
    if top_margin > _MIN_MARGIN_PX and bottom_margin > _MIN_MARGIN_PX:
        ratio = max(top_margin, bottom_margin) / min(top_margin, bottom_margin)
        if ratio > _RATIO_THRESHOLD:
            side = "top" if top_margin > bottom_margin else "bottom"
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="MARGIN_ASYMMETRY",
                    message=(
                        f"Vertical margin asymmetry: {side} has {ratio:.1f}x "
                        f"more space (B={bottom_margin:.0f}px, T={top_margin:.0f}px)"
                    ),
                    detail={
                        "axis": "vertical",
                        "side": side,
                        "ratio": round(ratio, 1),
                        "bottom_px": round(bottom_margin),
                        "top_px": round(top_margin),
                    },
                )
            )

    return warnings
