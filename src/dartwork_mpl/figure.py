"""Figure creation utilities for dartwork-mpl.

This module provides enhanced figure creation functions that integrate
with dartwork-mpl's style system.
"""

from __future__ import annotations

from typing import Any, Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure


def subplots(
    nrows: int = 1,
    ncols: int = 1,
    *,
    style: str | list[str] | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: int | None = None,
    sharex: bool | Literal["none", "all", "row", "col"] = False,
    sharey: bool | Literal["none", "all", "row", "col"] = False,
    squeeze: bool = True,
    width_ratios: list[float] | None = None,
    height_ratios: list[float] | None = None,
    subplot_kw: dict[str, Any] | None = None,
    gridspec_kw: dict[str, Any] | None = None,
    **fig_kw: Any,
) -> tuple[Figure, Axes | np.ndarray]:
    """Create a figure and a set of subplots with optional style application.

    This is a wrapper around matplotlib.pyplot.subplots that integrates with
    dartwork-mpl's style system. It allows applying styles directly when
    creating the figure, following the "Zero-Resize Policy" where figsize
    and dpi can be determined by the style.

    Parameters
    ----------
    nrows : int, optional
        Number of rows of the subplot grid.
    ncols : int, optional
        Number of columns of the subplot grid.
    style : str | list[str] | None, optional
        Style preset(s) to apply. Can be a single style name or a list
        of styles to stack. If None, uses current matplotlib style.
        Examples: 'scientific', 'report-kr', ['font-libertine', 'color-pro']
    figsize : tuple[float, float] | None, optional
        Figure dimension (width, height) in inches. If None and a style
        is specified, uses the style's default figsize.
    dpi : int | None, optional
        Dots per inch. If None and a style is specified, uses the style's
        default dpi.
    sharex : bool | str, optional
        Controls sharing of x-axis among subplots.
    sharey : bool | str, optional
        Controls sharing of y-axis among subplots.
    squeeze : bool, optional
        If True, single Axes object is returned if nrows=ncols=1.
        If False, always returns 2D array of Axes.
    width_ratios : list[float] | None, optional
        Width ratios of the columns. Length must equal ncols.
    height_ratios : list[float] | None, optional
        Height ratios of the rows. Length must equal nrows.
    subplot_kw : dict | None, optional
        Dict with keywords passed to add_subplot for each subplot.
    gridspec_kw : dict | None, optional
        Dict with keywords passed to GridSpec constructor.
    **fig_kw : Any
        Additional keyword arguments passed to plt.figure().

    Returns
    -------
    fig : Figure
        The created figure.
    ax : Axes or array of Axes
        Single Axes object or array of Axes objects. The shape depends on
        nrows, ncols, and squeeze parameters.

    Examples
    --------
    Create a simple figure with scientific style:

    >>> fig, ax = dm.subplots(style='scientific')
    >>> ax.plot(x, y)

    Create a 2x2 grid with custom style stack:

    >>> fig, axes = dm.subplots(2, 2, style=['font-libertine', 'color-pro'])
    >>> for ax in axes.flat:
    ...     ax.plot(x, y)

    Create with specific size overriding style defaults:

    >>> fig, ax = dm.subplots(style='report', figsize=(8, 6), dpi=150)

    Create with shared axes:

    >>> fig, axes = dm.subplots(3, 1, style='scientific', sharex=True)

    Notes
    -----
    This function follows dartwork-mpl's "Zero-Resize Policy": when a style
    is provided, you don't need to specify figsize or dpi unless you want
    to override the style's defaults. This ensures consistent sizing across
    your visualizations.

    The style is applied before creating the figure, so all matplotlib
    elements created within the figure will inherit the style properties.
    """
    # Apply style if provided
    original_rcParams = None
    if style is not None:
        # Store original rcParams to potentially extract figsize/dpi
        original_rcParams = plt.rcParams.copy()

        # Apply the requested style
        from . import style as style_module

        if isinstance(style, str):
            style_module.use(style)
        elif isinstance(style, list):
            style_module.stack(style)
        else:
            raise ValueError(f"style must be str or list, got {type(style)}")

    # Extract figsize and dpi from style if not explicitly provided
    if style is not None:
        if figsize is None:
            # Check if style set a figsize
            style_figsize = plt.rcParams.get("figure.figsize")
            if original_rcParams and style_figsize != original_rcParams.get(
                "figure.figsize"
            ):
                figsize = tuple(style_figsize)

        if dpi is None:
            # Check if style set a dpi
            style_dpi = plt.rcParams.get("figure.dpi")
            if original_rcParams and style_dpi != original_rcParams.get(
                "figure.dpi"
            ):
                dpi = style_dpi

    # Build keyword arguments for plt.subplots
    kwargs = {}
    if figsize is not None:
        kwargs["figsize"] = figsize
    if dpi is not None:
        kwargs["dpi"] = dpi

    # Set up gridspec_kw
    if gridspec_kw is None:
        gridspec_kw = {}

    if width_ratios is not None:
        gridspec_kw["width_ratios"] = width_ratios
    if height_ratios is not None:
        gridspec_kw["height_ratios"] = height_ratios

    # Add gridspec_kw if it has content
    if gridspec_kw:
        kwargs["gridspec_kw"] = gridspec_kw

    # Add subplot_kw if provided
    if subplot_kw is not None:
        kwargs["subplot_kw"] = subplot_kw

    # Add any additional figure kwargs
    kwargs.update(fig_kw)

    # Create the figure and axes using matplotlib's subplots
    fig, ax = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        sharex=sharex,
        sharey=sharey,
        squeeze=squeeze,
        **kwargs,
    )

    return fig, ax


def figure(
    *,
    style: str | list[str] | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: int | None = None,
    **kwargs: Any,
) -> Figure:
    """Create a figure with optional style application.

    This is a wrapper around matplotlib.pyplot.figure that integrates with
    dartwork-mpl's style system.

    Parameters
    ----------
    style : str | list[str] | None, optional
        Style preset(s) to apply.
    figsize : tuple[float, float] | None, optional
        Figure dimension (width, height) in inches.
    dpi : int | None, optional
        Dots per inch.
    **kwargs : Any
        Additional keyword arguments passed to plt.figure().

    Returns
    -------
    Figure
        The created figure.

    Examples
    --------
    >>> fig = dm.figure(style='report')
    >>> ax = fig.add_subplot(111)
    >>> ax.plot(x, y)
    """
    # Apply style if provided
    original_rcParams = None
    if style is not None:
        original_rcParams = plt.rcParams.copy()

        from . import style as style_module

        if isinstance(style, str):
            style_module.use(style)
        elif isinstance(style, list):
            style_module.stack(style)
        else:
            raise ValueError(f"style must be str or list, got {type(style)}")

    # Extract figsize and dpi from style if not explicitly provided
    if style is not None:
        if figsize is None:
            style_figsize = plt.rcParams.get("figure.figsize")
            if original_rcParams and style_figsize != original_rcParams.get(
                "figure.figsize"
            ):
                figsize = tuple(style_figsize)

        if dpi is None:
            style_dpi = plt.rcParams.get("figure.dpi")
            if original_rcParams and style_dpi != original_rcParams.get(
                "figure.dpi"
            ):
                dpi = style_dpi

    # Build kwargs
    fig_kwargs = {}
    if figsize is not None:
        fig_kwargs["figsize"] = figsize
    if dpi is not None:
        fig_kwargs["dpi"] = dpi
    fig_kwargs.update(kwargs)

    # Create the figure
    return plt.figure(**fig_kwargs)
