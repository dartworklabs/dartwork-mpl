"""Native figure-quality diagnostics and shared raster-output advice threshold."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from .._figure_geometry import drawn_axes

#: Minimum DPI dartwork recommends for raster output. The one source for this
#: check's threshold and advice text and for the ``high_dpi`` requirement of
#: ``validate_fixes.check_agent_requirements`` (they once drifted to 150 vs 200).
MIN_RECOMMENDED_DPI = 200


def check_figure_quality(fig: Figure) -> list[str]:
    """Check figure for common quality issues.

    Parameters
    ----------
    fig : Figure
        Figure to check

    Returns
    -------
    list[str]
        List of issues found

    Examples
    --------
    >>> issues = check_figure_quality(fig)
    >>> if issues:
    ...     print("Quality issues found:")
    ...     for issue in issues:
    ...         print(f"  - {issue}")
    """
    issues = []

    # Check DPI
    if fig.dpi < MIN_RECOMMENDED_DPI:
        issues.append(
            f"Low DPI ({fig.dpi}), should be at least {MIN_RECOMMENDED_DPI}"
        )

    # Check if style was applied
    if plt.rcParams["font.size"] == 10.0:  # matplotlib default
        issues.append("Style may not be applied (using default font size)")

    # Check axes
    for idx, ax in drawn_axes(fig):
        if not ax.get_visible():
            continue

        # Check labels
        if ax.xaxis.get_visible() and not ax.get_xlabel():
            issues.append(f"Axes {idx}: Missing x-axis label")
        if ax.yaxis.get_visible() and not ax.get_ylabel():
            issues.append(f"Axes {idx}: Missing y-axis label")

        # Check for crowded ticks
        n_xticks = len(ax.get_xticks())
        n_yticks = len(ax.get_yticks())
        if n_xticks > 20:
            issues.append(f"Axes {idx}: Too many x-ticks ({n_xticks})")
        if n_yticks > 20:
            issues.append(f"Axes {idx}: Too many y-ticks ({n_yticks})")

        # Check for missing data. Cover every artist family a plot can
        # produce — not just Line2D (``get_data``) and scatter
        # (``get_offsets``): bars/histograms are patches, pie wedges are
        # patches, and imshow/heatmaps are images. Checking only the
        # first two falsely flagged bar/hist/pie/imshow figures.
        has_data = any(
            artist.get_visible()
            for group in (
                ax.lines,
                ax.patches,
                ax.collections,
                ax.images,
                ax.tables,
            )
            for artist in group
        )
        if not has_data:
            issues.append(f"Axes {idx}: No data plotted")

    return issues


check_figure_quality.__module__ = "dartwork_mpl.helpers.quality"
