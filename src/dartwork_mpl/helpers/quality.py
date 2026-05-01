"""Quality checks and chart type suggestions for dartwork-mpl agents.

This module provides functions for checking figure quality and
suggesting appropriate chart types based on data characteristics.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def suggest_chart_type(
    x_type: str, y_type: str | None, n_points: int, n_series: int = 1
) -> str:
    """Suggest appropriate chart type based on data characteristics.

    Parameters
    ----------
    x_type : str
        Type of x data: "continuous", "categorical", "temporal"
    y_type : str | None
        Type of y data: "continuous", "categorical", "count", None
    n_points : int
        Number of data points
    n_series : int
        Number of data series

    Returns
    -------
    str
        Suggested chart type

    Examples
    --------
    >>> chart_type = suggest_chart_type("categorical", "continuous", 5, 1)
    >>> print(chart_type)  # "bar"
    """
    if y_type is None:
        # Single variable
        if x_type == "continuous":
            return "histogram"
        if x_type == "categorical":
            return "count_bar"
        return "line"

    # Two variables
    if x_type == "categorical":
        if n_series == 1:
            return "bar"
        return "grouped_bar"

    if x_type == "temporal":
        if n_series == 1:
            if n_points < 20:
                return "bar_line"  # Bar with line overlay
            return "line"
        return "multi_line"

    if x_type == "continuous":
        if y_type == "continuous":
            if n_points < 50:
                return "scatter"
            if n_points < 500:
                return "scatter_density"
            return "hexbin"
        return "line"

    return "scatter"  # Default


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
    if fig.dpi < 150:
        issues.append(f"Low DPI ({fig.dpi}), should be at least 200")

    # Check if style was applied
    if plt.rcParams["font.size"] == 10.0:  # matplotlib default
        issues.append("Style may not be applied (using default font size)")

    # Check axes
    for idx, ax in enumerate(fig.axes):
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

        # Check for missing data
        has_data = False
        for artist in ax.get_children():
            if hasattr(artist, "get_data") or hasattr(artist, "get_offsets"):
                has_data = True
                break
        if not has_data:
            issues.append(f"Axes {idx}: No data plotted")

    return issues
