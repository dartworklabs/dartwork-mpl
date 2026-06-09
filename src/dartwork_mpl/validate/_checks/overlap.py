"""OVERLAP: pairs of text labels in the same axes whose bboxes intersect."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._types import BBOX_ERRORS, Severity, VisualWarning

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_overlap"]


def check_overlap(fig: Figure, renderer: RendererBase) -> list[VisualWarning]:
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
            except BBOX_ERRORS:
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
