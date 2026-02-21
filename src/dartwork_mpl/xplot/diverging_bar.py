"""Diverging bar graph visualization.

This module provides a function to create diverging bar graphs that display
positive and negative values on opposite sides of a central axis.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.transforms import blended_transform_factory

import dartwork_mpl as dm


def plot_diverging_bar(
    labels: list[str] | None = None,
    neg_values: np.ndarray | None = None,
    pos_values: np.ndarray | None = None,
    add_total: bool = True,
    figsize: tuple[float, float] | None = None,
    dpi: int = 300,
    title: str | None = None,
    neg_label: str = "Review & Refactoring overhead",
    pos_label: str = "Code Generation savings",
    colors: dict[str, str] | None = None,
    hbar_height: float = 0.5,
    hbar_spacing_factor: float = 1.6,
    left_margin: float = 0.35,
    right_margin: float = 0.95,
    figure_bottom: float = 0.03,
    base_x: float = 0.02,
    title_y: float = 0.95,
    title_to_legend_gap: float = 0.05,
    legend_to_figure_gap: float = 0.06,
) -> tuple[Figure, Axes]:
    """
    Create a diverging bar graph with positive and negative values.

    This function creates a horizontal bar graph where negative values
    extend to the left and positive values extend to the right from a
    central axis. The layout uses a cascading design with title, legend,
    and figure positioned vertically.

    Parameters
    ----------
    labels : list[str] | None, optional
        List of category labels to display on the left side of the plot.
        Labels are displayed from top to bottom in reverse order. If None,
        uses default sample data. Default is None.
    neg_values : np.ndarray | None, optional
        Array of negative values (one per label). Values should be
        negative numbers. If None, uses default sample data. Default is
        None.
    pos_values : np.ndarray | None, optional
        Array of positive values (one per label). Values should be
        positive numbers. If None, uses default sample data. Default is
        None.
    add_total : bool, optional
        If True, adds a "Total" row with average values. Default is True.
    figsize : tuple[float, float] | None, optional
        Figure size in inches (width, height). If None, uses (12cm, 12cm).
        Default is None.
    dpi : int, optional
        Figure resolution in dots per inch. Default is 300.
    title : str | None, optional
        Title text displayed at the top. If None, uses default title.
        Default is None.
    neg_label : str, optional
        Label for negative bars in the legend. Default is
        "Review & Refactoring overhead".
    pos_label : str, optional
        Label for positive bars in the legend. Default is
        "Code Generation savings".
    colors : dict[str, str] | None, optional
        Color dictionary with keys 'neg' and 'pos'. If None, uses
        default colors (MidnightBlue-like for negative, CornflowerBlue-like
        for positive). Default is None.
    hbar_height : float, optional
        Height of each horizontal bar. Default is 0.5.
    hbar_spacing_factor : float, optional
        Spacing between bars as a multiple of hbar_height. Default is 1.6.
    left_margin : float, optional
        Left margin for the axes in figure coordinates (0-1). Default is
        0.35.
    right_margin : float, optional
        Right margin for the axes in figure coordinates (0-1). Default is
        0.95.
    figure_bottom : float, optional
        Bottom margin for the axes in figure coordinates (0-1). Default is
        0.03.
    base_x : float, optional
        Common x-coordinate for title, legend, and labels in figure
        coordinates (0-1). Default is 0.02.
    title_y : float, optional
        Starting y-coordinate for title in figure coordinates (0-1).
        Default is 0.95.
    title_to_legend_gap : float, optional
        Gap between title and legend in figure coordinates (0-1). Default is
        0.05.
    legend_to_figure_gap : float, optional
        Gap between legend and figure in figure coordinates (0-1). Default
        is 0.06.

    Returns
    ----------
    fig : matplotlib.figure.Figure
        The created figure object.
    ax : matplotlib.axes.Axes
        The axes containing the plot.

    Examples
    ----------
    >>> import numpy as np
    >>> import dartwork_mpl as dm
    >>> dm.style.use('scientific')
    >>>
    >>> # Minimal usage - uses default sample data
    >>> fig, ax = plot_diverging_bar()
    >>> dm.save_and_show(fig)
    >>>
    >>> # Custom data usage
    >>> labels = [
    ...     "Frontend Development",
    ...     "Backend Architecture",
    ...     "Data Engineering",
    ...     "API Integration",
    ...     "Quality Assurance",
    ...     "DevOps & Infrastructure",
    ...     "Security Compliance",
    ...     "Technical Documentation",
    ... ]
    >>> neg_values = np.array([-5, -8, -10, -10, -8, -9, -10, -7])
    >>> pos_values = np.array([20, 35, 32, 40, 20, 28, 38, 30])
    >>> fig, ax = plot_diverging_bar(
    ...     labels,
    ...     neg_values,
    ...     pos_values
    ... )
    >>> dm.save_and_show(fig)
    >>>
    >>> # Customized plot without Total row
    >>> fig, ax = plot_diverging_bar(
    ...     labels,
    ...     neg_values,
    ...     pos_values,
    ...     add_total=False,
    ...     title="Custom Title",
    ...     colors={'neg': 'oc.red5', 'pos': 'oc.green5'}
    ... )
    >>> dm.save_and_show(fig)

    Notes
    ----------
    - The function uses a cascading layout where title, legend, and figure
      are positioned vertically with automatic spacing.
    - Labels are positioned using blended_transform_factory to combine
      figure x-coordinates with data y-coordinates.
    - The "Total" row (if enabled) is automatically bolded using dm.fw(1).
    - Value labels are positioned inside the bars (left for negative,
      right for positive).

    See Also
    ----------
    dartwork_mpl.style.use : Apply dartwork-mpl style presets
    dartwork_mpl.simple_layout : Optimize figure layout
    matplotlib.transforms.blended_transform_factory : Create mixed
        coordinate transforms
    """
    # Use default sample data if not provided
    if labels is None:
        labels = [
            "Frontend Development",
            "Backend Architecture",
            "Data Engineering",
            "API Integration",
            "Quality Assurance",
            "DevOps & Infrastructure",
            "Security Compliance",
            "Technical Documentation",
        ]
    if neg_values is None:
        neg_values = np.array([-5, -8, -10, -10, -8, -9, -10, -7])
    if pos_values is None:
        pos_values = np.array([20, 35, 32, 40, 20, 28, 38, 30])

    # Prepare data: copy to avoid modifying input
    labels_list = labels.copy()
    neg_vals = neg_values.copy()
    pos_vals = pos_values.copy()

    # Add Total row if requested
    if add_total:
        labels_list.append("Total")
        neg_vals = np.append(neg_vals, np.mean(neg_vals))
        pos_vals = np.append(pos_vals, np.mean(pos_vals))

    # Reverse order for barh (top to bottom display)
    labels_list = labels_list[::-1]
    neg_vals = neg_vals[::-1]
    pos_vals = pos_vals[::-1]

    # Set default figure size using cm2in for unit conversion
    if figsize is None:
        figsize = (dm.cm2in(12), dm.cm2in(12))

    # Set default colors
    if colors is None:
        colors = {
            "neg": "#191970",  # MidnightBlue-like
            "pos": "#6495ED",  # CornflowerBlue-like
        }

    # Set default title
    if title is None:
        title = (
            "Engineering hours shifted by AI assistants, % of sprint capacity"
        )

    # Create figure with publication-ready settings
    fig = plt.figure(figsize=figsize, dpi=dpi)

    # Cascading layout calculation
    # Vertical positioning from top to bottom:
    # title_y -> legend_y -> figure_top
    legend_y = title_y - title_to_legend_gap
    figure_top = legend_y - legend_to_figure_gap

    # Set up GridSpec for precise layout control
    # left_margin reserves space for labels on the left
    # Labels are drawn at figure x=base_x (0.02)
    gs = fig.add_gridspec(
        nrows=1,
        ncols=1,
        left=left_margin,
        right=right_margin,
        top=figure_top,
        bottom=figure_bottom,
    )
    ax = fig.add_subplot(gs[0, 0])

    # Calculate y positions for bars
    # Spacing between bars = hbar_height * hbar_spacing_factor
    y_pos = np.arange(len(labels_list)) * hbar_height * hbar_spacing_factor

    # Plot horizontal bars
    # Negative values extend to the left
    bars_neg = ax.barh(
        y_pos,
        neg_vals,
        height=hbar_height,
        color=colors["neg"],
        label=neg_label,
    )
    # Positive values extend to the right
    bars_pos = ax.barh(
        y_pos,
        pos_vals,
        height=hbar_height,
        color=colors["pos"],
        label=pos_label,
    )

    # Styling: remove all spines and ticks
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)

    # Remove x and y ticks
    ax.set_xticks([])
    ax.set_yticks([])

    # Add vertical grid line at x=0 for reference
    ax.axvline(0, color="lightgray", linewidth=0.8)

    # Create blended transform for labels
    # x-coordinate in figure space, y-coordinate in data space
    # This allows labels to be positioned at base_x (figure) while
    # aligning with bar positions (data)
    transform = blended_transform_factory(fig.transFigure, ax.transData)

    # Add text labels on the left side
    # Labels are positioned at base_x (figure x-coord) and y_pos (data
    # y-coord)
    for i, label in enumerate(labels_list):
        # Bold 'Total' label using dm.fw
        weight = dm.fw(1) if label == "Total" else dm.fw(0)

        ax.text(
            base_x,
            y_pos[i],
            label,
            ha="left",
            va="center",
            transform=transform,
            fontsize=dm.fs(0),
            fontweight=weight,
            wrap=True,
        )

    # Add value labels on bars
    # Negative values: label on the left side of the bar
    for rect in bars_neg:
        width = rect.get_width()
        ax.text(
            width - 1,  # Offset 1 unit to the left
            rect.get_y() + rect.get_height() / 2,  # Center vertically
            f"{int(width)}",
            ha="right",
            va="center",
            fontsize=dm.fs(-1),
        )

    # Positive values: label on the right side of the bar
    for rect in bars_pos:
        width = rect.get_width()
        ax.text(
            width + 1,  # Offset 1 unit to the right
            rect.get_y() + rect.get_height() / 2,  # Center vertically
            f"{int(width)}",
            ha="left",
            va="center",
            fontsize=dm.fs(-1),
        )

    # Add title at the top
    # Positioned at base_x (figure x-coord) and title_y (figure y-coord)
    fig.text(
        base_x,
        title_y,
        title,
        fontsize=dm.fs(2),
        fontweight=dm.fw(1),
        ha="left",
    )

    # Add custom legend
    # Positioned below title at base_x (figure x-coord) and legend_y
    # (figure y-coord)
    fig.legend(
        loc="upper left",
        bbox_to_anchor=(base_x, legend_y),
        ncol=2,
        frameon=False,
        fontsize=dm.fs(0),
        borderaxespad=0,
        columnspacing=1.5,
    )

    # Apply simple_layout for automatic margin optimization
    # Use bbox to optimize only the axes area, protecting title/legend
    # bbox format: (left, right, bottom, top) in figure coordinates
    # This ensures title (at title_y) and legend (at legend_y) are not
    # affected by the optimization
    # Use minimal settings to preserve original layout as much as possible:
    # - Zero margins to match original exactly
    # - Very low importance weights to minimize optimization
    # - Very small bound_margin to limit GridSpec parameter changes
    # - High gtol to allow early convergence
    dm.simple_layout(
        fig,
        gs=gs,
        bbox=(left_margin, right_margin, figure_bottom, figure_top),
        margins=(
            0.0,
            0.0,
            0.0,
            0.0,
        ),  # Zero margins to preserve original# Extremely low weights to minimize changes
        bound_margin=0.001,  # Very small bound margin to limit changes
        gtol=1e-1,  # Higher tolerance for early convergence
        use_all_axes=False,  # Only optimize axes in this GridSpec
    )

    return fig, ax


def get_source_code() -> str:
    """
    Return the source code of this module as a string.

    This function is used to provide the source code to coding agents
    as input for further development or modification.

    Returns
    ----------
    str
        The complete source code of this module.

    Examples
    ----------
    >>> source = get_source_code()
    >>> print(source)
    """
    import importlib
    import inspect

    # Get the current module
    module_name = __name__
    module = importlib.import_module(module_name)

    # Get the source file path
    source_file = inspect.getfile(module)

    # Read and return the source code
    with open(source_file, encoding="utf-8") as f:
        return f.read()
