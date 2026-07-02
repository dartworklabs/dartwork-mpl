"""OVERFLOW: text or tick label whose bbox exits the figure canvas."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._types import BBOX_ERRORS, Severity, VisualWarning

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_overflow"]


def check_overflow(fig: Figure, renderer: RendererBase) -> list[VisualWarning]:
    """Detect elements whose bounding boxes extend beyond the figure canvas."""
    warnings: list[VisualWarning] = []
    fig_bbox = fig.bbox  # pixel coords

    for ax in fig.axes:
        # --- text objects (titles, labels, annotations) ---
        for txt in [*ax.texts, ax.title, ax.xaxis.label, ax.yaxis.label]:
            if (
                txt is None
                or not txt.get_visible()
                or txt.get_text().strip() == ""
            ):
                continue
            try:
                ext = txt.get_window_extent(renderer)
            except BBOX_ERRORS:
                continue
            # Skip zero-area extents — they appear when matplotlib
            # builds a Text for an artist with NaN/Inf-only data or a
            # fontsize=0 label. Such extents are uninformative and the
            # subsequent overflow comparison would compare against
            # garbage coordinates.
            if ext.width <= 0 or ext.height <= 0:
                continue

            dx_left = fig_bbox.x0 - ext.x0
            dx_right = ext.x1 - fig_bbox.x1
            dy_bottom = fig_bbox.y0 - ext.y0
            dy_top = ext.y1 - fig_bbox.y1

            overflow = max(dx_left, dx_right, dy_bottom, dy_top)
            if overflow > 2.0:  # > 2 px tolerance
                label = repr(txt.get_text()[:40])
                side = (
                    "left"
                    if dx_left == overflow
                    else "right"
                    if dx_right == overflow
                    else "bottom"
                    if dy_bottom == overflow
                    else "top"
                )
                warnings.append(
                    VisualWarning(
                        severity=Severity.WARNING,
                        check_id="OVERFLOW",
                        message=f"Text {label} exceeds figure bounds ({side} by {overflow:.1f}px)",
                        detail={
                            "text": txt.get_text(),
                            "side": side,
                            "px": round(overflow, 1),
                        },
                    )
                )

        # --- tick labels ---
        #
        # matplotlib's default tick locators emit ticks at "nice" round
        # values (e.g. y = 0, 10, ..., 90 for an axis whose data range is
        # 0 - 82). The extra ticks past the axis limits are still
        # registered on the artist tree even though they are clipped
        # away from the rendered axes — calling `get_window_extent` on
        # them therefore returns coordinates outside the axes patch
        # (and frequently outside the figure canvas).
        #
        # Only flag ticks whose anchor lies inside the visible axes
        # data range; ticks at out-of-range positions are visually
        # absent and not a layout problem.
        ax_bbox = ax.get_window_extent(renderer)
        for axis in (ax.xaxis, ax.yaxis):
            is_x = axis is ax.xaxis
            for tick in axis.get_ticklabels():
                if not tick.get_visible() or tick.get_text().strip() == "":
                    continue
                try:
                    ext = tick.get_window_extent(renderer)
                except BBOX_ERRORS:
                    continue
                if ext.width <= 0 or ext.height <= 0:
                    continue
                # Tick label center on the axis-perpendicular dimension.
                if is_x:
                    anchor = (ext.x0 + ext.x1) / 2
                    if not (ax_bbox.x0 - 0.5 <= anchor <= ax_bbox.x1 + 0.5):
                        continue
                else:
                    anchor = (ext.y0 + ext.y1) / 2
                    if not (ax_bbox.y0 - 0.5 <= anchor <= ax_bbox.y1 + 0.5):
                        continue
                overflow = max(
                    fig_bbox.x0 - ext.x0,
                    ext.x1 - fig_bbox.x1,
                    fig_bbox.y0 - ext.y0,
                    ext.y1 - fig_bbox.y1,
                )
                if overflow > 2.0:
                    warnings.append(
                        VisualWarning(
                            severity=Severity.WARNING,
                            check_id="OVERFLOW",
                            message=f"Tick label {tick.get_text()[:20]!r} overflows figure by {overflow:.1f}px",
                            detail={
                                "text": tick.get_text(),
                                "px": round(overflow, 1),
                            },
                        )
                    )
                    break  # one per axis is enough

    # --- figure-level text (suptitle / supxlabel / supylabel / fig.text)
    #
    # These live on the Figure, not on any Axes, so the per-axes loop
    # above never sees them. A suptitle nudged off the top edge or a
    # footnote running past the bottom would otherwise validate clean.
    fig_texts: list[Any] = [
        getattr(fig, "_suptitle", None),
        getattr(fig, "_supxlabel", None),
        getattr(fig, "_supylabel", None),
        *fig.texts,
    ]
    for txt in fig_texts:
        if txt is None or not txt.get_visible() or txt.get_text().strip() == "":
            continue
        try:
            ext = txt.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if ext.width <= 0 or ext.height <= 0:
            continue
        dx_left = fig_bbox.x0 - ext.x0
        dx_right = ext.x1 - fig_bbox.x1
        dy_bottom = fig_bbox.y0 - ext.y0
        dy_top = ext.y1 - fig_bbox.y1
        overflow = max(dx_left, dx_right, dy_bottom, dy_top)
        if overflow > 2.0:
            label = repr(txt.get_text()[:40])
            side = (
                "left"
                if dx_left == overflow
                else "right"
                if dx_right == overflow
                else "bottom"
                if dy_bottom == overflow
                else "top"
            )
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="OVERFLOW",
                    message=(
                        f"Figure text {label} exceeds figure bounds "
                        f"({side} by {overflow:.1f}px)"
                    ),
                    detail={
                        "text": txt.get_text(),
                        "side": side,
                        "px": round(overflow, 1),
                    },
                )
            )

    return warnings
