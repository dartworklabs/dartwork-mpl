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
    sharex: bool | Literal["none", "all", "row", "col"] = False,
    sharey: bool | Literal["none", "all", "row", "col"] = False,
    squeeze: bool = True,
    width_ratios: list[float] | None = None,
    height_ratios: list[float] | None = None,
    subplot_kw: dict[str, Any] | None = None,
    gridspec_kw: dict[str, Any] | None = None,
    **fig_kw: Any,
) -> tuple[Figure, Axes | np.ndarray[Any, Any]]:
    """Create a figure and a set of subplots with optional style application.

    The 0.4 API takes ``width`` (free-form, e.g. ``"13cm"``,
    ``dm.cm(11.3)``, or a bare number interpreted as cm) plus a
    height/width ratio via ``aspect`` (named token or positive float).

    The legacy ``figsize=``/``dpi=`` parameters were deprecated in
    0.4.0 and removed in 0.4.x. Passing them now raises ``TypeError``.

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

    # Reject legacy 0.3 args BEFORE applying any style. Style application
    # mutates global plt.rcParams; if we apply style first and raise
    # afterward, the failed call leaves rcParams permanently changed for
    # every subsequent figure in the same process. Validate forbidden
    # kwargs first so failed dm.subplots calls are side-effect free.
    if "figsize" in fig_kw:
        raise TypeError(
            "figsize= is no longer accepted by dm.subplots; use "
            'dm.subplots(width="13cm", aspect="wide") (or any other '
            "width/aspect combination). See docs/migration.md."
        )
    if "dpi" in fig_kw:
        raise TypeError(
            "dpi= is no longer accepted by dm.subplots; the active "
            "dartwork-mpl style controls dpi. See docs/migration.md."
        )

    # Apply style after the kwarg-validation gate so its rcParams are
    # visible to the rest of the function.
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

    # Resolve width/aspect → final figsize.
    resolved_figsize: tuple[float, float] | None = None
    if width is not None:
        w_in = parse_width(width)
        ratio = parse_aspect(aspect if aspect is not None else DEFAULT_ASPECT)
        resolved_figsize = (w_in, w_in * ratio)
    elif style is not None:
        # Fall back to style's figsize if a style was applied.
        style_figsize = plt.rcParams.get("figure.figsize")
        if (
            original_rcParams is not None
            and style_figsize is not None
            and style_figsize != original_rcParams.get("figure.figsize")
        ):
            resolved_figsize = cast(tuple[float, float], tuple(style_figsize))

    # Resolve dpi from style if a style was applied.
    resolved_dpi: int | None = None
    if style is not None:
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
    **kwargs : Any
        Additional keyword arguments passed to plt.figure().
        ``figsize=``/``dpi=`` were deprecated in 0.4.0 and removed in
        0.4.x — passing them now raises ``TypeError``.

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

    # Same ordering invariant as dm.subplots: validate forbidden kwargs
    # BEFORE style application, so a failed call doesn't leave global
    # plt.rcParams permanently mutated.
    if "figsize" in kwargs:
        raise TypeError(
            "figsize= is no longer accepted by dm.figure; use "
            'dm.figure(width="13cm", aspect="wide") (or any other '
            "width/aspect combination). See docs/migration.md."
        )
    if "dpi" in kwargs:
        raise TypeError(
            "dpi= is no longer accepted by dm.figure; the active "
            "dartwork-mpl style controls dpi. See docs/migration.md."
        )

    # Apply style after the kwarg-validation gate.
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

    # Resolve final figsize.
    resolved_figsize: tuple[float, float] | None = None
    if width is not None:
        w_in = parse_width(width)
        ratio = parse_aspect(aspect if aspect is not None else DEFAULT_ASPECT)
        resolved_figsize = (w_in, w_in * ratio)
    elif style is not None:
        style_figsize = plt.rcParams.get("figure.figsize")
        if (
            original_rcParams is not None
            and style_figsize is not None
            and style_figsize != original_rcParams.get("figure.figsize")
        ):
            resolved_figsize = cast(tuple[float, float], tuple(style_figsize))

    # Resolve dpi.
    resolved_dpi: int | None = None
    if style is not None:
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
