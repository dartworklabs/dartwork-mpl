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
        # Count only *visible* artists — a plot whose only line is
        # ``set_visible(False)`` renders empty, and an artist toggled off
        # shouldn't count as content.
        n_artists = sum(
            1
            for group in (
                ax.lines,
                ax.patches,
                ax.collections,
                ax.images,
                ax.tables,
            )
            for artist in group
            if artist.get_visible()
        )
        # A dedicated legend panel (``ax.axis("off")`` + ``ax.legend(...)``)
        # is a common small-multiples idiom and is NOT empty — counting the
        # legend prevents a false positive whose suggested fix (ax.remove)
        # would delete the legend.
        legend = ax.get_legend()
        has_legend = legend is not None and legend.get_visible()
        # Also count texts that look like annotations (not axis labels)
        has_content = (
            n_artists > 0
            or has_legend
            or any(t.get_text().strip() for t in ax.texts if t.get_visible())
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
