"""CROSS_AXES_OVERLAP: text labels from different axes overlapping each other."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._types import BBOX_ERRORS, Severity, VisualWarning

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_cross_axes_overlap"]


def check_cross_axes_overlap(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect text labels from different Axes that overlap each other.

    Catches the most common multi-panel layout regression: an upper
    subplot's xlabel / xtick labels overlapping a lower subplot's
    title (or, symmetrically, a left subplot's right-most ytick
    overlapping a right subplot's ylabel) when ``GridSpec`` ``hspace``
    / ``wspace`` is too tight. ``check_overlap`` only inspects pairs
    within a single Axes, so it misses these inter-Axes collisions.
    """
    warnings: list[VisualWarning] = []

    # Collect (axes_index, role, text_obj, bbox) for every visible
    # label across all axes.
    entries: list[tuple[int, str, str, Any]] = []
    for idx, ax in enumerate(fig.axes):
        try:
            ax_bbox = ax.get_window_extent(renderer)
        except BBOX_ERRORS:
            ax_bbox = None
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
            except BBOX_ERRORS:
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
            is_x = role == "xtick"
            for tl in ticklabels:
                if not tl.get_visible() or tl.get_text().strip() == "":
                    continue
                try:
                    ext = tl.get_window_extent(renderer)
                except BBOX_ERRORS:
                    continue
                if ext.width <= 0 or ext.height <= 0:
                    continue
                # Skip out-of-view ticks: matplotlib keeps ticks outside
                # the data range on the artist tree (visible=True) but
                # clips them from the render, so their bboxes are phantom
                # and must not count as overlaps (mirrors check_overflow).
                if ax_bbox is not None:
                    if is_x:
                        anchor = (ext.x0 + ext.x1) / 2
                        if not (ax_bbox.x0 - 0.5 <= anchor <= ax_bbox.x1 + 0.5):
                            continue
                    else:
                        anchor = (ext.y0 + ext.y1) / 2
                        if not (ax_bbox.y0 - 0.5 <= anchor <= ax_bbox.y1 + 0.5):
                            continue
                entries.append((idx, role, tl.get_text()[:30], ext))

    seen_pairs: set[tuple[int, int, str, str]] = set()
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            idx_a, role_a, name_a, bb_a = entries[i]
            idx_b, role_b, name_b, bb_b = entries[j]
            if idx_a == idx_b:
                continue  # Same axes — handled by check_overlap.

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
