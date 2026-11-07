"""CLIPPED_TEXT: text artist sitting within 1 px of the figure edge."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from ..._figure_geometry import (
    axes_text_artists,
    axes_with_secondaries,
    drawn_tick_labels,
)
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import wire
from ._registry import register_check, register_fix

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_clipped_text"]


class ClippedTextDetail(TypedDict):
    """A text artist is clipped by its Axes by ``margin_px`` pixels."""

    text: str
    margin_px: float


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
    1 px, which is what causes saved PNGs to chop labels. The text of
    ``secondary_xaxis`` / ``secondary_yaxis`` children is checked too.
    """
    warnings: list[VisualWarning] = []
    fig_bbox = fig.bbox

    seen: set[tuple[str, str]] = set()

    for ax in axes_with_secondaries(fig):
        # Only the tick labels matplotlib draws (the axis on, the tick in
        # view); the others stay on the artist tree but never reach the PNG.
        candidates: list[Any] = [
            *axes_text_artists(ax),
            *drawn_tick_labels(ax, "x"),
            *drawn_tick_labels(ax, "y"),
        ]
        for txt in candidates:
            if (
                txt is None
                or not txt.get_visible()
                or not txt.get_text().strip()
            ):
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
                    detail=wire(
                        ClippedTextDetail(
                            text=txt.get_text(), margin_px=round(margin, 1)
                        )
                    ),
                )
            )
    return warnings


@register_fix("CLIPPED_TEXT")
def _fix_clipped_text(_warning: VisualWarning) -> list[str]:
    return [
        "# Run the simple_layout pass\ndm.simple_layout(fig)",
        "# Or rotate the offending label\n"
        "dm.rotate_tick_labels(ax, axis='x', rotation=45)",
        "# Or shrink the font\n"
        "ax.tick_params(axis='both', labelsize=dm.fs(-2))",
    ]
