"""Quality checks and chart type suggestions for dartwork-mpl agents.

This module provides functions for checking figure quality and
suggesting appropriate chart types based on data characteristics.
Native quality diagnostics are compatibility aliases of the validate owner.
"""

from __future__ import annotations

from ..validate import MIN_RECOMMENDED_DPI, check_figure_quality

__all__ = ["MIN_RECOMMENDED_DPI", "check_figure_quality", "suggest_chart_type"]


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
