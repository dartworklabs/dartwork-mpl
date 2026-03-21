"""Agent utility functions for dartwork-mpl.

Helper functions to assist AI agents in creating consistent,
high-quality visualizations.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

import dartwork_mpl as dm


def validate_data(
    x: Any,
    y: Any | None = None,
    require_same_length: bool = True,
    allow_nan: bool = False,
    min_points: int = 2,
) -> tuple[np.ndarray, np.ndarray | None]:
    """Validate and clean input data for plotting.

    Parameters
    ----------
    x : Any
        X-axis data
    y : Any | None
        Y-axis data (optional for histograms, etc.)
    require_same_length : bool
        Whether x and y must have the same length
    allow_nan : bool
        Whether to allow NaN values
    min_points : int
        Minimum number of data points required

    Returns
    -------
    tuple[np.ndarray, np.ndarray | None]
        Cleaned x and y arrays

    Raises
    ------
    ValueError
        If validation fails

    Examples
    --------
    >>> x, y = validate_data([1, 2, 3], [4, 5, 6])
    >>> x_clean, _ = validate_data([1, 2, np.nan, 4], allow_nan=False)
    """
    # Convert to numpy arrays
    x = np.asarray(x)
    if y is not None:
        y = np.asarray(y)

    # Check minimum points
    if len(x) < min_points:
        raise ValueError(f"Need at least {min_points} data points, got {len(x)}")

    # Check length matching
    if y is not None and require_same_length:
        if len(x) != len(y):
            raise ValueError(f"Data length mismatch: x({len(x)}) != y({len(y)})")

    # Handle NaN/Inf values
    if not allow_nan:
        if np.any(np.isnan(x)) or np.any(np.isinf(x)):
            # Remove NaN/Inf
            mask = ~(np.isnan(x) | np.isinf(x))
            x = x[mask]
            if y is not None:
                y = y[mask]
            warnings.warn(f"Removed {(~mask).sum()} NaN/Inf values from data")

        if y is not None:
            if np.any(np.isnan(y)) or np.any(np.isinf(y)):
                mask = ~(np.isnan(y) | np.isinf(y))
                x = x[mask]
                y = y[mask]
                warnings.warn(f"Removed {(~mask).sum()} NaN/Inf values from data")

    # Final check
    if len(x) < min_points:
        raise ValueError(f"After cleaning, only {len(x)} points remain (need {min_points})")

    return x, y


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

    for xi, yi in zip(x, y):
        ax.text(xi, yi + offset, f"{yi:{format_str}}",
               ha="center", va="bottom",
               fontsize=fontsize, color=color)


def save_figure(
    fig: Figure,
    filename: str | Path,
    formats: tuple[str, ...] = ("png",),
    dpi: int = 300,
    create_dir: bool = True,
    verbose: bool = True,
) -> None:
    """Save figure with consistent settings.

    Parameters
    ----------
    fig : Figure
        Matplotlib figure
    filename : str | Path
        Output filename (without extension)
    formats : tuple[str, ...]
        Output formats
    dpi : int
        Resolution for raster formats
    create_dir : bool
        Whether to create output directory if missing
    verbose : bool
        Whether to print confirmation

    Examples
    --------
    >>> save_figure(fig, "output/chart", formats=("png", "svg"))
    """
    path = Path(filename)

    if create_dir:
        path.parent.mkdir(parents=True, exist_ok=True)

    # Save in all formats
    dm.save_formats(fig, str(path), formats=formats, dpi=dpi)

    if verbose:
        for fmt in formats:
            print(f"✓ Saved: {path.stem}.{fmt}")


def create_figure_with_style(
    style: str = "report-kr",
    figsize: tuple[float, float] | None = None,
    dpi: int = 200,
) -> Figure:
    """Create a figure with dartwork style pre-applied.

    Parameters
    ----------
    style : str
        Style preset name
    figsize : tuple[float, float] | None
        Figure size (defaults to DW x DW*0.6)
    dpi : int
        Figure DPI

    Returns
    -------
    Figure
        Configured figure

    Examples
    --------
    >>> fig = create_figure_with_style("scientific")
    """
    # Apply style
    dm.style.use(style)

    # Default size
    if figsize is None:
        figsize = (dm.DW, dm.DW * 0.6)

    # Create figure
    fig = plt.figure(figsize=figsize, dpi=dpi)

    return fig


def suggest_chart_type(
    x_type: str,
    y_type: str | None,
    n_points: int,
    n_series: int = 1,
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
        elif x_type == "categorical":
            return "count_bar"
        else:
            return "line"

    # Two variables
    if x_type == "categorical":
        if n_series == 1:
            return "bar"
        else:
            return "grouped_bar"

    elif x_type == "temporal":
        if n_series == 1:
            if n_points < 20:
                return "bar_line"  # Bar with line overlay
            else:
                return "line"
        else:
            return "multi_line"

    elif x_type == "continuous":
        if y_type == "continuous":
            if n_points < 50:
                return "scatter"
            elif n_points < 500:
                return "scatter_density"
            else:
                return "hexbin"
        else:
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
            if hasattr(artist, 'get_data') or hasattr(artist, 'get_offsets'):
                has_data = True
                break
        if not has_data:
            issues.append(f"Axes {idx}: No data plotted")

    return issues