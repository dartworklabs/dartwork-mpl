"""Figure creation utilities for dartwork-mpl.

This module provides enhanced figure creation functions that integrate
with dartwork-mpl's style system.
"""

from __future__ import annotations

from typing import Any, Literal, cast

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure


def subplots(
    nrows: int = 1,
    ncols: int = 1,
    *,
    width: str | int | float | None = None,
    aspect: str | int | float = "standard",
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

    The 0.4 API takes ``width`` (free-form, e.g. ``"13cm"``,
    ``dm.cm(11.3)``, or a bare number interpreted as cm) plus a
    height/width ratio via ``aspect`` (named token or positive float).

    The legacy ``figsize=``/``dpi=`` parameters still work but emit
    ``DeprecationWarning`` and will be removed in 0.5.0.

    Parameters
    ----------
    nrows, ncols : int, optional
        Subplot grid dimensions.
    width : str | int | float | None, optional
        Figure width. Accepts ``"<num><unit>"`` strings (cm/in/mm),
        the helpers ``dm.cm(x)``/``dm.inch(x)``/``dm.mm(x)``, or a
        raw number (interpreted as cm). If ``None`` and a style is
        provided, the style's default figsize is used.
    aspect : str | int | float, optional
        Height/width ratio. Either a named token in
        ``{"square","portrait","standard","golden","wide","cinema"}``
        or a positive float. Default ``"standard"`` (3:4).
    style : str | list[str] | None, optional
        Style preset(s) to apply. See :func:`dartwork_mpl.style.use`.
    figsize : tuple[float, float] | None, optional
        DEPRECATED. Use ``width`` and ``aspect`` instead. Will be
        removed in 0.5.0.
    dpi : int | None, optional
        DEPRECATED. The active style controls dpi; remove this
        argument. Will be removed in 0.5.0.
    sharex, sharey : bool | str, optional
        Axis sharing flags forwarded to ``plt.subplots``.
    squeeze : bool, optional
        If True (default), single Axes object is returned when
        nrows=ncols=1; otherwise an ndarray of Axes is always returned.
    width_ratios, height_ratios : list[float] | None, optional
        GridSpec ratios.
    subplot_kw, gridspec_kw : dict | None, optional
        Forwarded to matplotlib.
    **fig_kw : Any
        Additional keyword arguments forwarded to ``plt.figure``.

    Returns
    -------
    tuple[Figure, Axes | np.ndarray]
        The created figure and axes.

    Examples
    --------
    Create a 13 cm-wide figure with a wide aspect ratio:

    >>> fig, ax = dm.subplots(width="13cm", aspect="wide")

    Use the academic single-column sugar:

    >>> fig, ax = dm.subplots(width=dm.col1, aspect="standard")

    Stack a style preset alongside width/aspect:

    >>> fig, axes = dm.subplots(2, 1, width="17cm", aspect="cinema",
    ...                         style="scientific")
    """
    from .units import DEFAULT_ASPECT, parse_aspect, parse_width

    # Apply style first so its rcParams are visible to the rest.
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

    # Deprecation handling for figsize / dpi.
    if figsize is not None:
        import warnings as _warnings

        _warnings.warn(
            "figsize= on dm.subplots is deprecated and will be removed "
            "in 0.5.0. Use dm.subplots(width=..., aspect=...) instead "
            '(e.g. width="13cm", aspect="wide").',
            DeprecationWarning,
            stacklevel=2,
        )
    if dpi is not None:
        import warnings as _warnings

        _warnings.warn(
            "dpi= on dm.subplots is deprecated and will be removed in "
            "0.5.0. The active style controls dpi.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Resolve width/aspect → final figsize, unless legacy figsize was
    # supplied (legacy wins for back-compat in 0.4.x).
    resolved_figsize: tuple[float, float] | None = None
    if figsize is not None:
        resolved_figsize = figsize
    elif width is not None:
        w_in = parse_width(width)
        ratio = parse_aspect(aspect if aspect is not None else DEFAULT_ASPECT)
        resolved_figsize = (w_in, w_in * ratio)
    else:
        # Fall back to style's figsize if a style was applied.
        if style is not None:
            style_figsize = plt.rcParams.get("figure.figsize")
            if (
                original_rcParams is not None
                and style_figsize is not None
                and style_figsize != original_rcParams.get("figure.figsize")
            ):
                resolved_figsize = cast(
                    tuple[float, float], tuple(style_figsize)
                )

    # Resolve dpi from style if not explicitly provided.
    resolved_dpi: int | None = dpi
    if resolved_dpi is None and style is not None:
        style_dpi = plt.rcParams.get("figure.dpi")
        if (
            original_rcParams is not None
            and style_dpi is not None
            and style_dpi != original_rcParams.get("figure.dpi")
        ):
            resolved_dpi = int(style_dpi)

    # Build kwargs.
    kwargs: dict[str, Any] = {}
    if resolved_figsize is not None:
        kwargs["figsize"] = resolved_figsize
    if resolved_dpi is not None:
        kwargs["dpi"] = resolved_dpi

    if gridspec_kw is None:
        gridspec_kw = {}
    if width_ratios is not None:
        gridspec_kw["width_ratios"] = width_ratios
    if height_ratios is not None:
        gridspec_kw["height_ratios"] = height_ratios
    if gridspec_kw:
        kwargs["gridspec_kw"] = gridspec_kw
    if subplot_kw is not None:
        kwargs["subplot_kw"] = subplot_kw
    kwargs.update(fig_kw)

    return plt.subplots(
        nrows=nrows,
        ncols=ncols,
        sharex=sharex,
        sharey=sharey,
        squeeze=squeeze,
        **kwargs,
    )


def figure(
    *,
    width: str | int | float | None = None,
    aspect: str | int | float = "standard",
    style: str | list[str] | None = None,
    figsize: tuple[float, float] | None = None,
    dpi: int | None = None,
    **kwargs: Any,
) -> Figure:
    """Create a figure with optional style application.

    Mirrors :func:`subplots`'s width/aspect contract for callers that
    need a bare :class:`~matplotlib.figure.Figure` (e.g. to attach a
    custom GridSpec). Most agent-generated code should reach for
    :func:`subplots` instead.

    Parameters
    ----------
    width : str | int | float | None, optional
        Figure width. Accepts ``"<num><unit>"`` strings (cm/in/mm),
        the inch helpers ``dm.cm/inch/mm``, or a raw number
        (interpreted as cm). If ``None`` and a style is provided,
        the style's default figsize is used.
    aspect : str | int | float, optional
        Height/width ratio. Either a named token in
        ``{"square","portrait","standard","golden","wide","cinema"}``
        or a positive float. Default ``"standard"`` (3:4).
    style : str | list[str] | None, optional
        Style preset(s) to apply.
    figsize : tuple[float, float] | None, optional
        DEPRECATED. Use ``width`` and ``aspect`` instead. Will be
        removed in 0.5.0.
    dpi : int | None, optional
        DEPRECATED. The active style controls dpi. Will be removed
        in 0.5.0.
    **kwargs : Any
        Additional keyword arguments passed to plt.figure().

    Returns
    -------
    Figure
        The created figure.

    Examples
    --------
    >>> fig = dm.figure(width="13cm", aspect="wide", style="report")
    >>> ax = fig.add_subplot(111)
    """
    from .units import DEFAULT_ASPECT, parse_aspect, parse_width

    # Apply style first.
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

    # Deprecation handling.
    if figsize is not None:
        import warnings as _warnings

        _warnings.warn(
            "figsize= on dm.figure is deprecated and will be removed "
            "in 0.5.0. Use dm.figure(width=..., aspect=...) instead "
            '(e.g. width="13cm", aspect="wide").',
            DeprecationWarning,
            stacklevel=2,
        )
    if dpi is not None:
        import warnings as _warnings

        _warnings.warn(
            "dpi= on dm.figure is deprecated and will be removed in "
            "0.5.0. The active style controls dpi.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Resolve final figsize.
    resolved_figsize: tuple[float, float] | None = None
    if figsize is not None:
        resolved_figsize = figsize
    elif width is not None:
        w_in = parse_width(width)
        ratio = parse_aspect(aspect if aspect is not None else DEFAULT_ASPECT)
        resolved_figsize = (w_in, w_in * ratio)
    else:
        if style is not None:
            style_figsize = plt.rcParams.get("figure.figsize")
            if (
                original_rcParams is not None
                and style_figsize is not None
                and style_figsize != original_rcParams.get("figure.figsize")
            ):
                resolved_figsize = cast(
                    tuple[float, float], tuple(style_figsize)
                )

    # Resolve dpi.
    resolved_dpi: int | None = dpi
    if resolved_dpi is None and style is not None:
        style_dpi = plt.rcParams.get("figure.dpi")
        if (
            original_rcParams is not None
            and style_dpi is not None
            and style_dpi != original_rcParams.get("figure.dpi")
        ):
            resolved_dpi = int(style_dpi)

    fig_kwargs: dict[str, Any] = {}
    if resolved_figsize is not None:
        fig_kwargs["figsize"] = resolved_figsize
    if resolved_dpi is not None:
        fig_kwargs["dpi"] = resolved_dpi
    fig_kwargs.update(kwargs)

    return plt.figure(**fig_kwargs)
