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

import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.figure import Figure


# ───────────────────────────────────────────────────────
__all__ = ["validate_figure", "VisualWarning", "Severity"]

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
    detail: dict = field(default_factory=dict)

    # Icons per severity for structured log output.
    _ICONS = {Severity.WARNING: "⚠️ ", Severity.INFO: "💡"}

    def __str__(self) -> str:
        icon = self._ICONS.get(self.severity, "")
        return f"[VISUAL] {icon} {self.check_id}: {self.message}"


# ───────────────────────────────────────────────────────
# Individual checks
# ───────────────────────────────────────────────────────


def _check_overflow(fig: Figure, renderer) -> list[VisualWarning]:
    """Detect elements whose bounding boxes extend beyond the figure canvas."""
    warnings: list[VisualWarning] = []
    fig_bbox = fig.bbox  # pixel coords

    for ax in fig.axes:
        # --- text objects (titles, labels, annotations) ---
        for txt in ax.texts + [ax.title, ax.xaxis.label, ax.yaxis.label]:
            if (
                txt is None
                or not txt.get_visible()
                or txt.get_text().strip() == ""
            ):
                continue
            try:
                ext = txt.get_window_extent(renderer)
            except Exception:
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
        for axis in (ax.xaxis, ax.yaxis):
            for tick in axis.get_ticklabels():
                if not tick.get_visible() or tick.get_text().strip() == "":
                    continue
                try:
                    ext = tick.get_window_extent(renderer)
                except Exception:
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
                            message=f"Tick label {repr(tick.get_text()[:20])} overflows figure by {overflow:.1f}px",
                            detail={
                                "text": tick.get_text(),
                                "px": round(overflow, 1),
                            },
                        )
                    )
                    break  # one per axis is enough

    return warnings


def _check_overlap(fig: Figure, renderer) -> list[VisualWarning]:
    """Detect overlapping text labels within each Axes."""
    warnings: list[VisualWarning] = []

    for ax in fig.axes:
        texts = []
        for txt in ax.texts + [ax.title, ax.xaxis.label, ax.yaxis.label]:
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
            except Exception:
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
                            message=f"Labels {repr(name_a)} and {repr(name_b)} overlap (IoU={iou:.2f})",
                            detail={
                                "label_a": name_a,
                                "label_b": name_b,
                                "iou": round(iou, 2),
                            },
                        )
                    )

    return warnings


def _check_legend_overflow(fig: Figure, renderer) -> list[VisualWarning]:
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
        except Exception:
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


def _check_tick_crowding(fig: Figure, renderer) -> list[VisualWarning]:
    """Detect overcrowded tick labels on axes."""
    warnings: list[VisualWarning] = []
    MAX_DENSITY = 4.0  # ticks per inch

    for i, ax in enumerate(fig.axes):
        try:
            ax_ext = ax.get_window_extent(renderer)
        except Exception:
            continue

        dpi = fig.get_dpi()

        # X-axis
        xticks = [
            t
            for t in ax.xaxis.get_ticklabels()
            if t.get_visible() and t.get_text().strip()
        ]
        width_in = ax_ext.width / dpi
        if width_in > 0 and len(xticks) > 1:
            density = len(xticks) / width_in
            if density > MAX_DENSITY:
                warnings.append(
                    VisualWarning(
                        severity=Severity.INFO,
                        check_id="TICK_CROWD",
                        message=(
                            f"X-axis[{i}] has {len(xticks)} ticks in {width_in:.2f}in "
                            f"(density: {density:.1f} ticks/in, threshold: {MAX_DENSITY:.1f})"
                        ),
                        detail={
                            "axis": "x",
                            "axes_index": i,
                            "count": len(xticks),
                            "density": round(density, 1),
                        },
                    )
                )

        # Y-axis
        yticks = [
            t
            for t in ax.yaxis.get_ticklabels()
            if t.get_visible() and t.get_text().strip()
        ]
        height_in = ax_ext.height / dpi
        if height_in > 0 and len(yticks) > 1:
            density = len(yticks) / height_in
            if density > MAX_DENSITY:
                warnings.append(
                    VisualWarning(
                        severity=Severity.INFO,
                        check_id="TICK_CROWD",
                        message=(
                            f"Y-axis[{i}] has {len(yticks)} ticks in {height_in:.2f}in "
                            f"(density: {density:.1f} ticks/in, threshold: {MAX_DENSITY:.1f})"
                        ),
                        detail={
                            "axis": "y",
                            "axes_index": i,
                            "count": len(yticks),
                            "density": round(density, 1),
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
        Supported IDs: ``OVERFLOW``, ``OVERLAP``, ``LEGEND_OVERFLOW``,
        ``TICK_CROWD``, ``EMPTY_AXES``.
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

    all_checks = {
        "OVERFLOW": lambda: _check_overflow(fig, renderer),
        "OVERLAP": lambda: _check_overlap(fig, renderer),
        "LEGEND_OVERFLOW": lambda: _check_legend_overflow(fig, renderer),
        "TICK_CROWD": lambda: _check_tick_crowding(fig, renderer),
        "EMPTY_AXES": lambda: _check_empty_axes(fig),
    }

    if checks is not None:
        selected = {k: v for k, v in all_checks.items() if k in checks}
    else:
        selected = all_checks

    warnings: list[VisualWarning] = []
    for check_fn in selected.values():
        try:
            warnings.extend(check_fn())
        except Exception:
            pass  # never crash the save pipeline

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
