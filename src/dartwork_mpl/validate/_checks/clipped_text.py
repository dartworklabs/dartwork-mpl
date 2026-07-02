"""CLIPPED_TEXT: text artist sitting within 1 px of the figure edge."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._registry import register_check

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_clipped_text"]

# A label is clipped only when its bbox extends *past* the canvas edge
# (negative margin) by more than this tolerance. A label sitting flush
# at the edge (margin 0) is fully rendered — and is exactly what
# ``dm.simple_layout(margin=0)`` produces — so it must not be flagged.
_CLIP_TOL_PX = 1.0


@register_check("CLIPPED_TEXT", order=90)
def check_clipped_text(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect text artists clipped (or about to be clipped) by the canvas.

    Complementary to OVERFLOW: OVERFLOW fires when a label's bounding
    box exits the canvas, but it has a 2 px tolerance and skips ticks
    outside the data range. CLIPPED_TEXT is stricter — it fires when
    *any* visible Text artist's bbox approaches the edge by less than
    1 px, which is what causes saved PNGs to chop labels.
    """
    warnings: list[VisualWarning] = []
    fig_bbox = fig.bbox

    seen: set[tuple[str, str]] = set()

    # Build a set of tick label artists that are outside the axes data
    # range so we can skip them (matplotlib clips them automatically and
    # they never appear in the rendered PNG).
    # Mirror the same filter used by check_overflow: for x-tick labels
    # check that the bbox x-centre is within the axes x-range; for y-tick
    # labels check the y-centre. Ticks beyond the view limits will fail
    # this test and be excluded.
    def _out_of_range_ticks(ax: Any) -> set[int]:
        """Return id()s of tick labels clipped outside the axes view."""
        oor: set[int] = set()
        ax_bbox = ax.get_window_extent(renderer)
        for axis in (ax.xaxis, ax.yaxis):
            is_x = axis is ax.xaxis
            for tick_label in axis.get_ticklabels():
                if not tick_label.get_visible():
                    continue
                try:
                    ext = tick_label.get_window_extent(renderer)
                except BBOX_ERRORS:
                    continue
                if ext.width <= 0 or ext.height <= 0:
                    continue
                # Check the anchor on the axis dimension (same logic as
                # check_overflow).
                if is_x:
                    anchor = (ext.x0 + ext.x1) / 2
                    in_range = ax_bbox.x0 - 0.5 <= anchor <= ax_bbox.x1 + 0.5
                else:
                    anchor = (ext.y0 + ext.y1) / 2
                    in_range = ax_bbox.y0 - 0.5 <= anchor <= ax_bbox.y1 + 0.5
                if not in_range:
                    oor.add(id(tick_label))
        return oor

    for ax in fig.axes:
        oor_ticks = _out_of_range_ticks(ax)
        candidates: list[Any] = [
            *ax.texts,
            ax.title,
            ax.xaxis.label,
            ax.yaxis.label,
            *ax.xaxis.get_ticklabels(),
            *ax.yaxis.get_ticklabels(),
        ]
        for txt in candidates:
            if (
                txt is None
                or not txt.get_visible()
                or not txt.get_text().strip()
            ):
                continue
            # Skip out-of-range auto-locator ticks — they are clipped
            # by matplotlib's axes renderer and never appear in the PNG.
            if id(txt) in oor_ticks:
                continue
            try:
                ext = txt.get_window_extent(renderer)
            except BBOX_ERRORS:
                continue
            if ext.width <= 0 or ext.height <= 0:
                continue
            margin = min(
                ext.x0 - fig_bbox.x0,
                fig_bbox.x1 - ext.x1,
                ext.y0 - fig_bbox.y0,
                fig_bbox.y1 - ext.y1,
            )
            # Fire only when the label extends *past* the edge (negative
            # margin). Flush-at-edge (margin ≈ 0), the documented
            # ``simple_layout(margin=0)`` result, is fully rendered.
            if margin >= -_CLIP_TOL_PX:
                continue
            label = txt.get_text()[:30]
            key = (label, str(round(margin, 1)))
            if key in seen:
                continue
            seen.add(key)
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="CLIPPED_TEXT",
                    message=(
                        f"Text {label!r} extends past the canvas edge "
                        f"(margin: {margin:.1f}px)"
                    ),
                    detail={
                        "text": txt.get_text(),
                        "margin_px": round(margin, 1),
                    },
                )
            )
    return warnings
