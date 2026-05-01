"""Figure creation and I/O utilities for dartwork-mpl agents.

This module provides functions for creating and saving figures
with consistent settings.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

import dartwork_mpl as dm

from ..units import cm


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
        Figure size (defaults to 17 cm wide x ~10.2 cm tall, the
        former ``DW`` two-column figure preset).
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

    # Default size: previously ``DW = 17 cm``, height = width * 0.6.
    if figsize is None:
        width = cm(17)
        figsize = (width, width * 0.6)

    # Create figure
    return plt.figure(figsize=figsize, dpi=dpi)
