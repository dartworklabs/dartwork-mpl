"""Visual validation tools for Matplotlib figures.

Detects common rendering issues (label overlap, margin overflow, etc.)
that are invisible in console-only (stdout) environments such as AI
agent pipelines. Every check emits structured ``[VISUAL]`` log lines
so that agents can grep for them and attempt automated fixes.

Usage
-----
>>> import dartwork_mpl as dm
>>> fig, ax = plt.subplots()
>>> ax.plot([1, 2, 3])
>>> warnings = dm.validate_figure(fig)
>>> # Console output: [VISUAL] ✅ No visual issues detected.
"""

from __future__ import annotations

import contextlib
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.text import Text


# ───────────────────────────────────────────────────────
__all__ = ["Severity", "VisualWarning", "validate_figure"]

# Data structures
# ───────────────────────────────────────────────────────


class Severity(str, Enum):
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class VisualWarning:
    """A single visual issue detected in a figure (e.g., overflow, overlap)."""

    severity: Severity
    check_id: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)

    # Icons per severity for structured log output.
    _ICONS: ClassVar[dict[Severity, str]] = {
        Severity.WARNING: "⚠️ ",
        Severity.INFO: "💡",
    }

    def __str__(self) -> str:
        icon = self._ICONS.get(self.severity, "")
        return f"[VISUAL] {icon} {self.check_id}: {self.message}"


# ───────────────────────────────────────────────────────
# Individual checks
# ───────────────────────────────────────────────────────


def _check_overflow(fig: Figure, renderer: RendererBase) -> list[VisualWarning]:
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
            except (RuntimeError, ValueError, AttributeError):
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
                except (RuntimeError, ValueError, AttributeError):
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

    return warnings


def _check_overlap(fig: Figure, renderer: RendererBase) -> list[VisualWarning]:
    """Detect overlapping text labels within each Axes."""
    warnings: list[VisualWarning] = []

    for ax in fig.axes:
        texts: list[tuple[str, Any]] = []
        for txt in [*ax.texts, ax.title, ax.xaxis.label, ax.yaxis.label]:
            if (
                txt is None
                or not txt.get_visible()
                or txt.get_text().strip() == ""
            ):
                continue
            try:
                ext = txt.get_window_extent(renderer)
                if ext.width > 0 and ext.height > 0:
                    texts.append((txt.get_text()[:30], ext))
            except (RuntimeError, ValueError, AttributeError):
                continue

        # Pairwise IoU
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                name_a, bb_a = texts[i]
                name_b, bb_b = texts[j]

                # Intersection
                x0 = max(bb_a.x0, bb_b.x0)
                y0 = max(bb_a.y0, bb_b.y0)
                x1 = min(bb_a.x1, bb_b.x1)
                y1 = min(bb_a.y1, bb_b.y1)
                inter = max(0, x1 - x0) * max(0, y1 - y0)
                if inter == 0:
                    continue

                union = (
                    bb_a.width * bb_a.height + bb_b.width * bb_b.height - inter
                )
                iou = inter / union if union > 0 else 0
                if iou > 0.05:
                    warnings.append(
                        VisualWarning(
                            severity=Severity.WARNING,
                            check_id="OVERLAP",
                            message=f"Labels {name_a!r} and {name_b!r} overlap (IoU={iou:.2f})",
                            detail={
                                "label_a": name_a,
                                "label_b": name_b,
                                "iou": round(iou, 2),
                            },
                        )
                    )

    return warnings


def _check_legend_overflow(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect legends consuming too large a fraction of the Axes area."""
    warnings: list[VisualWarning] = []
    THRESHOLD = 0.30  # 30% of axes area

    for i, ax in enumerate(fig.axes):
        legend = ax.get_legend()
        if legend is None or not legend.get_visible():
            continue
        try:
            leg_ext = legend.get_window_extent(renderer)
            ax_ext = ax.get_window_extent(renderer)
        except (RuntimeError, ValueError, AttributeError):
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

        if ratio > THRESHOLD:
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="LEGEND_OVERFLOW",
                    message=(
                        f"Legend occupies {ratio:.1%} of axes[{i}] area "
                        f"(threshold: {THRESHOLD:.0%})"
                    ),
                    detail={
                        "axes_index": i,
                        "ratio": round(ratio, 3),
                        "threshold": THRESHOLD,
                    },
                )
            )

    return warnings


# Minimum inter-label gap, as a fraction of the summed label footprint,
# below which ticks read as crowded. 0.15 ⇒ labels must leave ≥15% of the
# axis dimension as breathing room collectively.
_TICK_CROWD_MIN_GAP_FRAC = 0.15
# Fallback density (ticks per inch) used only when label extents cannot be
# measured (e.g. a renderer that refuses get_window_extent). The measured
# path is font- and label-length-aware and is preferred.
_TICK_CROWD_FALLBACK_DENSITY = 4.0


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
        except (RuntimeError, ValueError, AttributeError):
            sizes = []
            break
        sizes.append(bb.width if horizontal else bb.height)
    if sizes:
        footprint = sum(sizes) * (1.0 + _TICK_CROWD_MIN_GAP_FRAC)
        return footprint / axis_span_px, True
    # Unmeasurable → density fallback (dpi folded into axis_span_px by caller)
    return None, False


def _check_tick_crowding(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect overcrowded tick labels on axes.

    The crowding test measures each visible label's real rendered extent
    (so it scales with font size, weight, rotation and text length)
    instead of a fixed ticks-per-inch density — a label that doubles in
    point size halves how many fit before they collide.
    """
    warnings: list[VisualWarning] = []
    dpi = fig.get_dpi()

    for i, ax in enumerate(fig.axes):
        try:
            ax_ext = ax.get_window_extent(renderer)
        except (RuntimeError, ValueError, AttributeError):
            continue

        for axis_name, getter, span_px, horizontal in (
            ("x", ax.xaxis.get_ticklabels, ax_ext.width, True),
            ("y", ax.yaxis.get_ticklabels, ax_ext.height, False),
        ):
            ticks = [
                t for t in getter() if t.get_visible() and t.get_text().strip()
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


def _check_empty_axes(fig: Figure) -> list[VisualWarning]:
    """Detect empty Axes that contain no visible data or content."""
    warnings: list[VisualWarning] = []

    for i, ax in enumerate(fig.axes):
        n_artists = (
            len(ax.lines)
            + len(ax.patches)
            + len(ax.collections)
            + len(ax.images)
            + len(ax.tables)
        )
        # Also count texts that look like annotations (not axis labels)
        has_content = n_artists > 0 or any(
            t.get_text().strip() for t in ax.texts
        )
        if not has_content:
            warnings.append(
                VisualWarning(
                    severity=Severity.INFO,
                    check_id="EMPTY_AXES",
                    message=f"Axes[{i}] has no visible data",
                    detail={"axes_index": i},
                )
            )

    return warnings


def _check_margin_asymmetry(
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
        except (RuntimeError, ValueError, AttributeError):
            continue
        # Include text objects outside axes (annotations, pie labels).
        for txt in ax.texts:
            if txt.get_visible() and txt.get_text().strip():
                with contextlib.suppress(
                    RuntimeError, ValueError, AttributeError
                ):
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

    RATIO_THRESHOLD = 3.0
    MIN_MARGIN_PX = 30  # ignore sides with very small margins

    # Horizontal comparison
    if left_margin > MIN_MARGIN_PX and right_margin > MIN_MARGIN_PX:
        ratio = max(left_margin, right_margin) / min(left_margin, right_margin)
        if ratio > RATIO_THRESHOLD:
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
    if top_margin > MIN_MARGIN_PX and bottom_margin > MIN_MARGIN_PX:
        ratio = max(top_margin, bottom_margin) / min(top_margin, bottom_margin)
        if ratio > RATIO_THRESHOLD:
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


def _check_pie_label_offset(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect donut chart labels that aren't centered in the wedge width."""
    warnings: list[VisualWarning] = []

    for ax in fig.axes:
        # Identify pie wedges via theta1/theta2 attributes.
        wedges = [
            p
            for p in ax.patches
            if hasattr(p, "theta1") and hasattr(p, "theta2")
        ]
        if not wedges:
            continue

        # Determine if donut (wedge width < 1.0). matplotlib pie wedges
        # have ``width=None`` for a regular (filled) pie, so coerce to 1.0.
        wedge_widths = [(getattr(w, "width", None) or 1.0) for w in wedges]
        if all(w >= 0.99 for w in wedge_widths):
            continue  # regular pie, not a donut

        avg_width = sum(wedge_widths) / len(wedge_widths)
        # Ideal pctdistance = center of donut ring.
        ideal_r = 1.0 - avg_width / 2.0
        TOLERANCE_RATIO = 0.15  # 15% deviation

        for txt in ax.texts:
            text_str = txt.get_text().strip()
            if not text_str.endswith("%"):
                continue
            x, y = txt.get_position()
            actual_r = (x**2 + y**2) ** 0.5
            if (
                ideal_r > 0
                and abs(actual_r - ideal_r) / ideal_r > TOLERANCE_RATIO
            ):
                warnings.append(
                    VisualWarning(
                        severity=Severity.INFO,
                        check_id="PIE_LABEL_OFFSET",
                        message=(
                            f"Donut label '{text_str}' at r={actual_r:.2f}, "
                            f"ideal center of wedge: r={ideal_r:.2f}"
                        ),
                        detail={
                            "text": text_str,
                            "actual_r": round(actual_r, 2),
                            "ideal_r": round(ideal_r, 2),
                        },
                    )
                )
        break  # only check the first pie axes

    return warnings


def _check_clipped_text(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect text artists clipped (or about to be clipped) by the canvas.

    Complementary to OVERFLOW: OVERFLOW fires when a label's bounding
    box exits the canvas, but it has a 2 px tolerance and skips ticks
    outside the data range. CLIPPED_TEXT is stricter — it fires when
    *any* visible Text artist's bbox approaches the edge by less than
    1 px, which is what causes saved PNGs to chop labels."""
    warnings: list[VisualWarning] = []
    fig_bbox = fig.bbox
    TIGHT_TOL_PX = 1.0

    seen: set[tuple[str, str]] = set()

    # Build a set of tick label artists that are outside the axes data
    # range so we can skip them (matplotlib clips them automatically and
    # they never appear in the rendered PNG).
    # Mirror the same filter used by _check_overflow: for x-tick labels
    # check that the bbox x-centre is within the axes x-range; for y-tick
    # labels check the y-centre.  Ticks beyond the view limits will fail
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
                except (RuntimeError, ValueError, AttributeError):
                    continue
                if ext.width <= 0 or ext.height <= 0:
                    continue
                # Check the anchor on the axis dimension (same logic as
                # _check_overflow).
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
            except (RuntimeError, ValueError, AttributeError):
                continue
            if ext.width <= 0 or ext.height <= 0:
                continue
            margin = min(
                ext.x0 - fig_bbox.x0,
                fig_bbox.x1 - ext.x1,
                ext.y0 - fig_bbox.y0,
                fig_bbox.y1 - ext.y1,
            )
            if margin >= TIGHT_TOL_PX:
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
                        f"Text {label!r} sits within "
                        f"{TIGHT_TOL_PX:.0f}px of the canvas edge "
                        f"(margin: {margin:.1f}px)"
                    ),
                    detail={
                        "text": txt.get_text(),
                        "margin_px": round(margin, 1),
                    },
                )
            )
    return warnings


def _check_cross_axes_overlap(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect text labels from different Axes that overlap each other.

    Catches the most common multi-panel layout regression: an upper
    subplot's xlabel / xtick labels overlapping a lower subplot's
    title (or, symmetrically, a left subplot's right-most ytick
    overlapping a right subplot's ylabel) when ``GridSpec`` ``hspace``
    / ``wspace`` is too tight. ``_check_overlap`` only inspects pairs
    within a single Axes, so it misses these inter-Axes collisions.
    """
    warnings: list[VisualWarning] = []

    # Collect (axes_index, role, text_obj, bbox) for every visible
    # label across all axes.
    entries: list[tuple[int, str, str, Any]] = []
    for idx, ax in enumerate(fig.axes):
        candidates: list[tuple[str, Any]] = [
            ("title", ax.title),
            ("xlabel", ax.xaxis.label),
            ("ylabel", ax.yaxis.label),
        ]
        for role, txt in candidates:
            if (
                txt is None
                or not txt.get_visible()
                or txt.get_text().strip() == ""
            ):
                continue
            try:
                ext = txt.get_window_extent(renderer)
            except (RuntimeError, ValueError, AttributeError):
                continue
            if ext.width <= 0 or ext.height <= 0:
                continue
            entries.append((idx, role, txt.get_text()[:30], ext))
        # Tick labels — only count the ones that have non-empty text
        # and are within the view (matplotlib draws them outside the
        # visible range too).
        for role, ticklabels in (
            ("xtick", ax.get_xticklabels()),
            ("ytick", ax.get_yticklabels()),
        ):
            for tl in ticklabels:
                if not tl.get_visible() or tl.get_text().strip() == "":
                    continue
                try:
                    ext = tl.get_window_extent(renderer)
                except (RuntimeError, ValueError, AttributeError):
                    continue
                if ext.width <= 0 or ext.height <= 0:
                    continue
                entries.append((idx, role, tl.get_text()[:30], ext))

    seen_pairs: set[tuple[int, int, str, str]] = set()
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            idx_a, role_a, name_a, bb_a = entries[i]
            idx_b, role_b, name_b, bb_b = entries[j]
            if idx_a == idx_b:
                continue  # Same axes — handled by _check_overlap.

            x0 = max(bb_a.x0, bb_b.x0)
            y0 = max(bb_a.y0, bb_b.y0)
            x1 = min(bb_a.x1, bb_b.x1)
            y1 = min(bb_a.y1, bb_b.y1)
            inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
            if inter <= 0.0:
                continue

            # Use intersection-over-smaller so a small but full-cover
            # title-vs-xlabel collision is still flagged when the
            # other party's bbox is larger.
            min_area = min(bb_a.width * bb_a.height, bb_b.width * bb_b.height)
            ratio = inter / min_area if min_area > 0 else 0.0
            if ratio < 0.05:
                continue

            # Dedupe by axes pair + role pair so two overlapping tick
            # labels from the same axes pair don't flood the report.
            roles = tuple(sorted((role_a, role_b)))
            key = (min(idx_a, idx_b), max(idx_a, idx_b), roles[0], roles[1])
            if key in seen_pairs:
                continue
            seen_pairs.add(key)

            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="CROSS_AXES_OVERLAP",
                    message=(
                        f"axes[{idx_a}] {role_a} {name_a!r} overlaps "
                        f"axes[{idx_b}] {role_b} {name_b!r} "
                        f"(intersection/min-area={ratio:.2f}). Increase "
                        f"GridSpec hspace/wspace or pass "
                        f"gridspec_kw={{'hspace': ..., 'wspace': ...}}."
                    ),
                    detail={
                        "axes_a": idx_a,
                        "role_a": role_a,
                        "axes_b": idx_b,
                        "role_b": role_b,
                        "ratio": round(ratio, 2),
                    },
                )
            )
    return warnings


# ───────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────


def validate_figure(
    fig: Figure, *, checks: tuple[str, ...] | None = None, quiet: bool = False
) -> list[VisualWarning]:
    """Run comprehensive visual validation on a Matplotlib figure.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The figure to inspect for visual defects.
    checks : tuple[str, ...] | None, optional
        Check IDs to run. If None, all registered checks are executed.
        Supported IDs: ``OVERFLOW``, ``OVERLAP``,
        ``CROSS_AXES_OVERLAP``, ``LEGEND_OVERFLOW``, ``TICK_CROWD``,
        ``EMPTY_AXES``, ``MARGIN_ASYMMETRY``, ``PIE_LABEL_OFFSET``,
        ``CLIPPED_TEXT``.
    quiet : bool, optional
        If True, suppresses stdout output. Default is False.

    Returns
    -------
    list[VisualWarning]
        List of detected visual issues.
    """
    # Render once so all bounding boxes are computed.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]

    all_checks: dict[str, Any] = {
        "OVERFLOW": lambda: _check_overflow(fig, renderer),
        "OVERLAP": lambda: _check_overlap(fig, renderer),
        "CROSS_AXES_OVERLAP": lambda: _check_cross_axes_overlap(fig, renderer),
        "LEGEND_OVERFLOW": lambda: _check_legend_overflow(fig, renderer),
        "TICK_CROWD": lambda: _check_tick_crowding(fig, renderer),
        "EMPTY_AXES": lambda: _check_empty_axes(fig),
        "MARGIN_ASYMMETRY": lambda: _check_margin_asymmetry(fig, renderer),
        "PIE_LABEL_OFFSET": lambda: _check_pie_label_offset(fig, renderer),
        "CLIPPED_TEXT": lambda: _check_clipped_text(fig, renderer),
    }

    selected = (
        {k: v for k, v in all_checks.items() if k in checks}
        if checks is not None
        else all_checks
    )

    warnings: list[VisualWarning] = []
    for check_fn in selected.values():
        # Never crash the save pipeline
        with contextlib.suppress(RuntimeError, ValueError, AttributeError):
            warnings.extend(check_fn())

    # Structured stdout output for agent consumption.
    if not quiet:
        if warnings:
            for w in warnings:
                print(str(w), file=sys.stdout, flush=True)
        else:
            print(
                "[VISUAL] ✅ No visual issues detected.",
                file=sys.stdout,
                flush=True,
            )

    return warnings
