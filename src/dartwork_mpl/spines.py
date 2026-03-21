"""Spine and grid utilities for dartwork-mpl.

This module provides utilities for customizing plot spines and grids.
"""

from __future__ import annotations

from typing import Literal

from matplotlib.axes import Axes


def hide_spines(
    ax: Axes,
    which: list[str] | None = None,
) -> None:
    """Hide specified spines from the axes.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    which : list[str] | None
        List of spines to hide: ["top", "right", "bottom", "left"]
        If None, defaults to ["top", "right"]

    Examples
    --------
    >>> hide_spines(ax)  # Hide top and right spines (default)
    >>> hide_spines(ax, ["top", "right", "bottom"])  # Keep only left spine
    """
    if which is None:
        which = ["top", "right"]

    for spine in which:
        if spine in ax.spines:
            ax.spines[spine].set_visible(False)


def hide_all_spines(ax: Axes) -> None:
    """Hide all spines from the axes.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes

    Examples
    --------
    >>> hide_all_spines(ax)  # Remove all borders
    """
    for spine in ax.spines.values():
        spine.set_visible(False)


def show_only_spines(
    ax: Axes,
    which: list[str],
) -> None:
    """Show only specified spines, hide others.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    which : list[str]
        List of spines to show: ["top", "right", "bottom", "left"]

    Examples
    --------
    >>> show_only_spines(ax, ["bottom", "left"])  # Classic axes style
    """
    all_spines = ["top", "right", "bottom", "left"]
    for spine_name in all_spines:
        if spine_name in ax.spines:
            ax.spines[spine_name].set_visible(spine_name in which)


def style_spines(
    ax: Axes,
    color: str | None = None,
    linewidth: float | None = None,
    which: list[str] | None = None,
) -> None:
    """Style the spines with custom color and linewidth.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    color : str | None
        Color for spines (e.g., "oc.gray5")
    linewidth : float | None
        Line width for spines
    which : list[str] | None
        Which spines to style. If None, styles all visible spines

    Examples
    --------
    >>> style_spines(ax, color="oc.gray3", linewidth=0.5)
    >>> style_spines(ax, color="oc.blue5", which=["bottom", "left"])
    """
    if which is None:
        spines_to_style = [name for name, spine in ax.spines.items() if spine.get_visible()]
    else:
        spines_to_style = which

    for spine_name in spines_to_style:
        if spine_name in ax.spines:
            spine = ax.spines[spine_name]
            if color is not None:
                spine.set_color(color)
            if linewidth is not None:
                spine.set_linewidth(linewidth)


def add_grid(
    ax: Axes,
    which: Literal["major", "minor", "both"] = "major",
    axis: Literal["x", "y", "both"] = "both",
    alpha: float = 0.3,
    color: str = "oc.gray3",
    linestyle: str = "-",
    linewidth: float = 0.5,
    **kwargs,
) -> None:
    """Add a customized grid to the axes.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    which : {"major", "minor", "both"}
        Which tick marks to use for grid
    axis : {"x", "y", "both"}
        Which axis to add grid lines
    alpha : float
        Transparency of grid lines
    color : str
        Color of grid lines
    linestyle : str
        Line style ("-", "--", ":", "-.")
    linewidth : float
        Width of grid lines
    **kwargs
        Additional keyword arguments passed to ax.grid()

    Examples
    --------
    >>> add_grid(ax)  # Add default grid
    >>> add_grid(ax, which="both", alpha=0.2, linestyle=":")
    >>> add_grid(ax, axis="y", color="oc.blue2")
    """
    ax.grid(
        visible=True,
        which=which,
        axis=axis,
        alpha=alpha,
        color=color,
        linestyle=linestyle,
        linewidth=linewidth,
        **kwargs
    )
    ax.set_axisbelow(True)  # Ensure grid is behind plot elements


def remove_grid(ax: Axes) -> None:
    """Remove grid from the axes.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes

    Examples
    --------
    >>> remove_grid(ax)
    """
    ax.grid(False)


def add_frame(
    ax: Axes,
    color: str = "oc.gray5",
    linewidth: float = 1.0,
) -> None:
    """Add a frame (all spines) with consistent styling.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    color : str
        Frame color
    linewidth : float
        Frame line width

    Examples
    --------
    >>> add_frame(ax)  # Add default frame
    >>> add_frame(ax, color="oc.blue5", linewidth=2)
    """
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(color)
        spine.set_linewidth(linewidth)


def minimal_axes(ax: Axes) -> None:
    """Apply minimal axes style (only bottom and left spines, light grid).

    Parameters
    ----------
    ax : Axes
        Matplotlib axes

    Examples
    --------
    >>> minimal_axes(ax)
    """
    # Keep only bottom and left spines
    show_only_spines(ax, ["bottom", "left"])

    # Add light grid
    add_grid(ax, axis="y", alpha=0.2, linestyle="--")

    # Style remaining spines
    style_spines(ax, color="oc.gray6", linewidth=0.5)