"""EMPTY_AXES: axes that carry no plotted artist or annotation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._types import Severity, VisualWarning

if TYPE_CHECKING:
    from matplotlib.figure import Figure

__all__ = ["check_empty_axes"]


def check_empty_axes(fig: Figure) -> list[VisualWarning]:
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
