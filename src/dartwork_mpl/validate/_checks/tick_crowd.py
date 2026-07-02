"""TICK_CROWD: too many tick labels for the axis length to comfortably hold.

Measures each visible label's real rendered extent (so it scales with
font size, weight, rotation and text length) instead of a fixed
ticks-per-inch density.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._types import BBOX_ERRORS, Severity, VisualWarning

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.text import Text

__all__ = ["check_tick_crowding"]

# Minimum inter-label gap, as a fraction of the summed label footprint,
# below which ticks read as crowded. 0.15 ⇒ labels must leave ≥15% of the
# axis dimension as breathing room collectively.
_TICK_CROWD_MIN_GAP_FRAC = 0.15

# Fallback density (ticks per inch) used only when label extents cannot be
# measured (e.g. a renderer that refuses get_window_extent). The measured
# path is font- and label-length-aware and is preferred.
_TICK_CROWD_FALLBACK_DENSITY = 4.0


def _tick_in_view(
    tick: Text, ax_ext: Any, *, horizontal: bool, renderer: RendererBase
) -> bool:
    """True when the tick label's anchor lies inside the axes view.

    matplotlib keeps out-of-range ticks on the artist tree (visible but
    clipped from the render). Their phantom extents inflate the crowding
    footprint and produce false TICK_CROWD warnings, so exclude them.
    """
    try:
        ext = tick.get_window_extent(renderer)
    except BBOX_ERRORS:
        return False
    if ext.width <= 0 or ext.height <= 0:
        return False
    if horizontal:
        anchor = (ext.x0 + ext.x1) / 2
        return bool(ax_ext.x0 - 0.5 <= anchor <= ax_ext.x1 + 0.5)
    anchor = (ext.y0 + ext.y1) / 2
    return bool(ax_ext.y0 - 0.5 <= anchor <= ax_ext.y1 + 0.5)


def _tick_crowd_for_axis(
    labels: list[Text],
    axis_span_px: float,
    *,
    horizontal: bool,
    renderer: RendererBase,
) -> tuple[float | None, bool] | None:
    """Return ``(occupancy, measured)`` for one axis, or ``None`` to skip.

    ``occupancy`` is the fraction of the axis dimension consumed by the
    tick labels plus the required minimum gap. ``occupancy > 1`` means the
    labels (at their *actual* rendered size — font, weight, rotation and
    text length all baked in) cannot fit without touching, i.e. crowded.

    Falls back to a fixed ticks-per-inch density only when a label extent
    cannot be measured, so the common path stays font-aware.
    """
    if axis_span_px <= 0 or len(labels) < 2:
        return None
    sizes: list[float] = []
    for label in labels:
        try:
            bb = label.get_window_extent(renderer)
        except BBOX_ERRORS:
            sizes = []
            break
        sizes.append(bb.width if horizontal else bb.height)
    if sizes:
        footprint = sum(sizes) * (1.0 + _TICK_CROWD_MIN_GAP_FRAC)
        return footprint / axis_span_px, True
    # Unmeasurable → density fallback (dpi folded into axis_span_px by caller)
    return None, False


def check_tick_crowding(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect overcrowded tick labels on axes."""
    warnings: list[VisualWarning] = []
    dpi = fig.get_dpi()

    for i, ax in enumerate(fig.axes):
        try:
            ax_ext = ax.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue

        for axis_name, getter, span_px, horizontal in (
            ("x", ax.xaxis.get_ticklabels, ax_ext.width, True),
            ("y", ax.yaxis.get_ticklabels, ax_ext.height, False),
        ):
            ticks = [
                t
                for t in getter()
                if t.get_visible()
                and t.get_text().strip()
                and _tick_in_view(
                    t, ax_ext, horizontal=horizontal, renderer=renderer
                )
            ]
            result = _tick_crowd_for_axis(
                ticks, span_px, horizontal=horizontal, renderer=renderer
            )
            crowded = False
            occupancy: float | None = None
            measured = False
            if result is not None:
                occupancy, measured = result
                crowded = occupancy is not None and occupancy > 1.0
            if not measured and len(ticks) > 1:
                # Density fallback (extents unmeasurable).
                span_in = span_px / dpi
                if span_in > 0:
                    density = len(ticks) / span_in
                    crowded = density > _TICK_CROWD_FALLBACK_DENSITY

            if not crowded:
                continue

            span_in = span_px / dpi
            if measured and occupancy is not None:
                detail_extra = f"labels fill {occupancy:.0%} of the axis"
            else:
                detail_extra = (
                    f"density {len(ticks) / span_in:.1f} ticks/in "
                    f"> {_TICK_CROWD_FALLBACK_DENSITY:.1f}"
                )
            warnings.append(
                VisualWarning(
                    severity=Severity.INFO,
                    check_id="TICK_CROWD",
                    message=(
                        f"{axis_name.upper()}-axis[{i}] has {len(ticks)} "
                        f"ticks in {span_in:.2f}in ({detail_extra})"
                    ),
                    detail={
                        "axis": axis_name,
                        "axes_index": i,
                        "count": len(ticks),
                        "occupancy": (
                            round(occupancy, 2)
                            if measured and occupancy is not None
                            else None
                        ),
                    },
                )
            )

    return warnings
