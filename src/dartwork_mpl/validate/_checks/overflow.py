"""OVERFLOW: text or tick label whose bbox exits the figure canvas."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from ..._figure_geometry import iter_figure_level_extents
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import SIDES, Side, choice, number, wire
from ._registry import register_check, register_fix

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_overflow"]


class OverflowTextDetail(TypedDict):
    """A text artist past one figure edge, by ``px`` pixels."""

    text: str
    side: Side
    px: float


class OverflowTickDetail(TypedDict):
    """A tick label past the figure; no single edge is reported."""

    text: str
    px: float


OverflowDetail = OverflowTextDetail | OverflowTickDetail


@register_check("OVERFLOW", order=10)
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
                side: Side = (
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
                        detail=wire(
                            OverflowTextDetail(
                                text=txt.get_text(),
                                side=side,
                                px=round(overflow, 1),
                            )
                        ),
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
                            detail=wire(
                                OverflowTickDetail(
                                    text=tick.get_text(), px=round(overflow, 1)
                                )
                            ),
                        )
                    )
                    break  # one per axis is enough

    # --- figure-level text (suptitle / supxlabel / supylabel / fig.text)
    #
    # These live on the Figure, not on any Axes, so the per-axes loop
    # above never sees them. A suptitle nudged off the top edge or a
    # footnote running past the bottom would otherwise validate clean.
    # ``legends=False``: figure legends are the LEGEND_OVERFLOW check's job.
    for txt, ext in iter_figure_level_extents(fig, renderer, legends=False):
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
                    detail=wire(
                        OverflowTextDetail(
                            text=txt.get_text(),
                            side=side,
                            px=round(overflow, 1),
                        )
                    ),
                )
            )

    return warnings


@register_fix("OVERFLOW")
def _fix_overflow(warning: VisualWarning) -> list[str]:
    """Margin or layout suggestions for the overflowing edge, if one is known."""
    suggestions: list[str] = []
    # A tick-label variant has no ``side``; it gets no edge suggestion.
    side = choice(warning.detail, "side", SIDES)
    if side is None:
        return suggestions
    px = number(warning.detail, "px", 0)
    # Clamp the suggested fractions into a valid band: matplotlib
    # requires left/bottom < right/top, all within [0, 1]. Unclamped,
    # a large overflow (px ≈ 90 on a small figure) produced
    # copy-paste suggestions like ``subplots_adjust(left=1.05)`` that
    # raise ValueError when applied.
    grow = min(0.45, 0.15 + px / 100)
    shrink_right = max(0.55, 0.95 - px / 100)
    shrink_top = max(0.55, 0.9 - px / 100)
    if side == "left":
        suggestions.append(
            f"# Increase left margin\nfig.subplots_adjust(left={grow:.2f})"
        )
        suggestions.append("# Or use simple_layout\ndm.simple_layout(fig)")
    elif side == "right":
        suggestions.append(
            "# Increase right margin\n"
            f"fig.subplots_adjust(right={shrink_right:.2f})"
        )
        suggestions.append("# Or use simple_layout\ndm.simple_layout(fig)")
    elif side == "bottom":
        suggestions.append(
            f"# Increase bottom margin\nfig.subplots_adjust(bottom={grow:.2f})"
        )
        suggestions.append(
            "# Rotate x-tick labels\nax.tick_params(axis='x', rotation=45)"
        )
    elif side == "top":
        suggestions.append(
            f"# Increase top margin\nfig.subplots_adjust(top={shrink_top:.2f})"
        )
    return suggestions
