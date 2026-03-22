"""Formatting utilities for axes, legends, and annotations.

This module provides functions for formatting matplotlib elements
to maintain consistency in visualizations.
"""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes

import dartwork_mpl as dm


def format_axis_labels(
    ax: Axes,
    x_label: str | None = None,
    y_label: str | None = None,
    x_unit: str | None = None,
    y_unit: str | None = None,
    title: str | None = None,
) -> None:
    """Apply consistent formatting to axis labels.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    x_label : str | None
        X-axis label
    y_label : str | None
        Y-axis label
    x_unit : str | None
        Unit for x-axis (will be appended in parentheses)
    y_unit : str | None
        Unit for y-axis (will be appended in parentheses)
    title : str | None
        Axes title

    Examples
    --------
    >>> format_axis_labels(ax, "Time", "Revenue", x_unit="Quarter", y_unit="억원")
    """
    if x_label:
        if x_unit:
            x_label = f"{x_label} ({x_unit})"
        ax.set_xlabel(x_label, fontsize=dm.fs(0))

    if y_label:
        if y_unit:
            y_label = f"{y_label} ({y_unit})"
        ax.set_ylabel(y_label, fontsize=dm.fs(0))

    if title:
        ax.set_title(title, fontsize=dm.fs(1), pad=10)


def optimize_legend(
    ax: Axes,
    preferred_loc: str = "best",
    max_cols: int = 3,
    outside: bool = False,
) -> None:
    """Optimize legend placement and formatting.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    preferred_loc : str
        Preferred location if space permits
    max_cols : int
        Maximum number of columns for legend
    outside : bool
        Whether to place legend outside plot area

    Examples
    --------
    >>> optimize_legend(ax, preferred_loc="upper right")
    >>> optimize_legend(ax, outside=True)
    """
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return

    n_items = len(handles)

    # Determine number of columns
    if n_items <= 3:
        ncol = 1
    elif n_items <= 6:
        ncol = min(2, max_cols)
    else:
        ncol = min(3, max_cols)

    # Legend parameters
    legend_params = {
        "fontsize": dm.fs(-1),
        "framealpha": 0.95,
        "edgecolor": "oc.gray3",
        "ncol": ncol,
    }

    if outside:
        # Place outside plot area
        legend_params["bbox_to_anchor"] = (1.02, 1)
        legend_params["loc"] = "upper left"
    else:
        # Inside plot area
        legend_params["loc"] = preferred_loc

    ax.legend(**legend_params)


def add_value_labels(
    ax: Axes,
    x: np.ndarray,
    y: np.ndarray,
    format_str: str = ".1f",
    offset_y: float = 0.02,
    color: str | None = None,
    fontsize: int | None = None,
) -> None:
    """Add value labels to data points.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    x : np.ndarray
        X coordinates
    y : np.ndarray
        Y values to label
    format_str : str
        Format string for values
    offset_y : float
        Vertical offset as fraction of y-range
    color : str | None
        Text color (defaults to "oc.gray7")
    fontsize : int | None
        Font size (defaults to fs(-1))

    Examples
    --------
    >>> add_value_labels(ax, quarters, revenue, format_str=".0f")
    """
    if color is None:
        color = "oc.gray7"
    if fontsize is None:
        fontsize = dm.fs(-1)

    y_range = ax.get_ylim()[1] - ax.get_ylim()[0]
    offset = y_range * offset_y

    for xi, yi in zip(x, y, strict=False):
        ax.text(xi, yi + offset, f"{yi:{format_str}}",
               ha="center", va="bottom",
               fontsize=fontsize, color=color)
