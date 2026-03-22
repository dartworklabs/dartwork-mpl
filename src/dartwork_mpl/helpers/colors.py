"""Color selection and management utilities for dartwork-mpl agents.

This module provides functions for automatic color selection and
color scheme management.
"""

from __future__ import annotations

from typing import Literal


def auto_select_colors(
    n_series: int,
    color_type: Literal["categorical", "sequential", "diverging"] = "categorical",
    highlight_index: int | None = None,
) -> list[str]:
    """Automatically select appropriate colors for data series.

    Parameters
    ----------
    n_series : int
        Number of data series
    color_type : str
        Type of color scheme to use
    highlight_index : int | None
        Index of series to highlight

    Returns
    -------
    list[str]
        List of dartwork color names

    Examples
    --------
    >>> colors = auto_select_colors(5, "categorical")
    >>> colors = auto_select_colors(3, highlight_index=0)
    """
    if color_type == "categorical":
        # Distinct colors for categorical data
        base_colors = [
            "oc.blue5", "oc.red5", "oc.green5", "oc.orange5",
            "oc.purple5", "oc.teal5", "oc.pink5", "oc.yellow5"
        ]
    elif color_type == "sequential":
        # Gradient from light to dark
        if n_series <= 5:
            base_colors = [f"oc.blue{i}" for i in range(3, 8)]
        else:
            base_colors = [f"oc.blue{i}" for i in range(1, 10)]
    elif color_type == "diverging":
        # Red to blue through gray
        if n_series <= 5:
            base_colors = ["oc.red6", "oc.red4", "oc.gray5", "oc.blue4", "oc.blue6"]
        else:
            base_colors = ["oc.red7", "oc.red5", "oc.red3",
                          "oc.gray5",
                          "oc.blue3", "oc.blue5", "oc.blue7"]
    else:
        raise ValueError(f"Unknown color_type: {color_type}")

    # Select colors
    if n_series <= len(base_colors):
        colors = base_colors[:n_series]
    else:
        # Repeat colors if needed
        colors = base_colors * (n_series // len(base_colors) + 1)
        colors = colors[:n_series]

    # Apply highlighting
    if highlight_index is not None and 0 <= highlight_index < n_series:
        # Make highlighted series darker, others lighter
        new_colors = []
        for i, color in enumerate(colors):
            if i == highlight_index:
                # Keep original or make darker
                new_colors.append(color.replace("5", "7"))
            else:
                # Make lighter
                new_colors.append(color.replace("5", "3"))
        colors = new_colors

    return colors
