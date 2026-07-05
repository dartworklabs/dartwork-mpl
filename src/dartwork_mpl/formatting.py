"""Enhanced formatting utilities for dartwork-mpl.

This module provides additional formatting functions for axes,
tick labels, and other matplotlib elements.
"""

from __future__ import annotations

from typing import Literal

import matplotlib.ticker as ticker
from matplotlib.axes import Axes

_MYRIAD_UNIT_LADDERS: dict[str, tuple[tuple[int, str], ...]] = {
    "ko": ((10**4, "만"), (10**8, "억"), (10**12, "조"), (10**16, "경")),
    "zh": ((10**4, "万"), (10**8, "亿"), (10**12, "兆"), (10**16, "京")),
    "ja": ((10**4, "万"), (10**8, "億"), (10**12, "兆"), (10**16, "京")),
}


def format_axis_myriad(
    ax: Axes,
    axis: str = "y",
    *,
    locale: str = "ko",
    decimals: int = 1,
    currency: str = "",
) -> None:
    """Format axis ticks using East-Asian myriad units.

    Parameters
    ----------
    ax:
        Matplotlib axes to format.
    axis:
        Which axis to format: "x", "y", or "both".
    locale:
        Unit ladder locale: "ko", "zh", or "ja".
    decimals:
        Number of decimal places before trailing zero trimming.
    currency:
        Optional currency prefix inserted after the sign.
    """
    if locale not in _MYRIAD_UNIT_LADDERS:
        raise ValueError(
            f"locale must be one of 'ko', 'zh', or 'ja' (got {locale!r})"
        )
    if axis not in {"x", "y", "both"}:
        raise ValueError("axis must be one of 'x', 'y', or 'both'")
    if decimals < 0:
        raise ValueError("decimals must be non-negative")

    unit_ladder = _MYRIAD_UNIT_LADDERS[locale]

    def _format_myriad(value: float, _pos: int | None = None) -> str:
        if value == 0:
            return "0"

        sign = "-" if value < 0 else ""
        prefix = f"{sign}{currency}"
        abs_value = abs(value)

        if abs_value < 10_000:
            return f"{prefix}{abs_value:,.0f}"

        threshold, unit = max(
            item for item in unit_ladder if item[0] <= abs_value
        )
        scaled = abs_value / threshold
        formatted = f"{scaled:,.{decimals}f}"
        if decimals > 0:
            formatted = formatted.rstrip("0").rstrip(".")
        return f"{prefix}{formatted}{unit}"

    formatter = ticker.FuncFormatter(_format_myriad)
    if axis in {"x", "both"}:
        ax.xaxis.set_major_formatter(formatter)
    if axis in {"y", "both"}:
        ax.yaxis.set_major_formatter(formatter)


def format_axis_millions(
    ax: Axes,
    axis: Literal["x", "y", "both"] = "y",
    suffix: str = "M",
    decimals: int = 1,
) -> None:
    """Format axis tick labels in millions.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    axis : Literal["x", "y", "both"]
        Which axis to format
    suffix : str
        Suffix to add (default: "M")
    decimals : int
        Number of decimal places

    Examples
    --------
    >>> format_axis_millions(ax)  # Show as 1.5M instead of 1500000
    """

    def millions_formatter(x: float, pos: int) -> str:
        """Internal formatter function for millions scale.

        Parameters
        ----------
        x : float
            The tick value to format
        pos : int
            The tick position (unused but required by matplotlib)

        Returns
        -------
        str
            Formatted string with millions suffix
        """
        # Any value that rounds to zero at the requested precision (0, or
        # a small negative like -40 000 → -0.04 → -0.0) renders as the
        # bare zero tick — suffix-less and never "-0.0M".
        scaled = x / 1e6
        if round(scaled, decimals) == 0:
            return f"{0:.{decimals}f}"
        return f"{scaled:.{decimals}f}{suffix}"

    formatter = ticker.FuncFormatter(millions_formatter)

    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(formatter)
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(formatter)


def format_axis_billions(
    ax: Axes,
    axis: Literal["x", "y", "both"] = "y",
    suffix: str = "B",
    decimals: int = 1,
) -> None:
    """Format axis tick labels in billions.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    axis : Literal["x", "y", "both"]
        Which axis to format
    suffix : str
        Suffix to add (default: "B")
    decimals : int
        Number of decimal places

    Examples
    --------
    >>> format_axis_billions(ax)  # Show as 1.5B instead of 1500000000
    """

    def billions_formatter(x: float, pos: int) -> str:
        """Internal formatter function for billions scale.

        Parameters
        ----------
        x : float
            The tick value to format
        pos : int
            The tick position (unused but required by matplotlib)

        Returns
        -------
        str
            Formatted string with billions suffix
        """
        # Any value that rounds to zero at the requested precision
        # renders as the bare zero tick — suffix-less and never "-0.0B".
        scaled = x / 1e9
        if round(scaled, decimals) == 0:
            return f"{0:.{decimals}f}"
        return f"{scaled:.{decimals}f}{suffix}"

    formatter = ticker.FuncFormatter(billions_formatter)

    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(formatter)
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(formatter)


def format_axis_currency(
    ax: Axes,
    axis: Literal["x", "y", "both"] = "y",
    symbol: str = "$",
    position: Literal["prefix", "suffix"] = "prefix",
    decimals: int = 0,
) -> None:
    """Format axis tick labels as currency.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    axis : Literal["x", "y", "both"]
        Which axis to format
    symbol : str
        Currency symbol
    position : Literal["prefix", "suffix"], optional
        Position of currency symbol
    decimals : int
        Number of decimal places

    Examples
    --------
    >>> format_axis_currency(ax)  # Format as $1,000
    >>> format_axis_currency(ax, symbol="€", position="suffix")  # Format as 1,000€
    """

    def currency_formatter(x: float, pos: int) -> str:
        """Internal formatter function for currency values.

        Parameters
        ----------
        x : float
            The tick value to format
        pos : int
            The tick position (unused but required by matplotlib)

        Returns
        -------
        str
            Formatted string with currency symbol
        """
        # Format the magnitude (always positive) so the minus sign can
        # be placed outside the currency symbol — convention is
        # ``-$1,000``, not ``$-1,000``.
        abs_formatted = f"{abs(x):,.{decimals}f}"
        # Suppress the sign when the magnitude rounds to exactly zero
        # at the requested decimals (e.g. ``x=-0.0`` or ``x=-0.4``
        # with ``decimals=0`` would otherwise render as ``"-$0"``).
        zero_form = f"{0:,.{decimals}f}"
        sign = "-" if (x < 0 and abs_formatted != zero_form) else ""
        if position == "prefix":
            return f"{sign}{symbol}{abs_formatted}"
        return f"{sign}{abs_formatted}{symbol}"

    formatter = ticker.FuncFormatter(currency_formatter)

    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(formatter)
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(formatter)


def format_axis_si(
    ax: Axes, axis: Literal["x", "y", "both"] = "y", decimals: int = 1
) -> None:
    """Format axis tick labels with SI prefixes (k, M, G, etc.).

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    axis : Literal["x", "y", "both"]
        Which axis to format
    decimals : int
        Number of decimal places

    Examples
    --------
    >>> format_axis_si(ax)  # Show as 1.5k, 2.3M, etc.
    """

    def si_formatter(x: float, pos: int) -> str:
        """Internal formatter function for SI prefix notation.

        Parameters
        ----------
        x : float
            The tick value to format
        pos : int
            The tick position (unused but required by matplotlib)

        Returns
        -------
        str
            Formatted string with SI prefix (k, M, G, T)
        """
        if x == 0:
            return f"{0:.{decimals}f}"

        abs_x = abs(x)
        sign = "-" if x < 0 else ""

        if abs_x >= 1e12:
            return f"{sign}{abs_x / 1e12:.{decimals}f}T"
        if abs_x >= 1e9:
            return f"{sign}{abs_x / 1e9:.{decimals}f}G"
        if abs_x >= 1e6:
            return f"{sign}{abs_x / 1e6:.{decimals}f}M"
        if abs_x >= 1e3:
            return f"{sign}{abs_x / 1e3:.{decimals}f}k"
        # Sub-1000: no SI prefix. Normalise ``-0.0`` to ``0.0``.
        return f"{round(x, decimals) or 0.0:.{decimals}f}"

    formatter = ticker.FuncFormatter(si_formatter)

    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(formatter)
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(formatter)


def rotate_tick_labels(
    ax: Axes,
    axis: Literal["x", "y", "both"] = "x",
    rotation: float = 45,
    ha: Literal["left", "center", "right"] | None = None,
) -> None:
    """Rotate tick labels for better readability.

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    axis : Literal["x", "y", "both"]
        Which axis to rotate
    rotation : float
        Rotation angle in degrees
    ha : Literal["left", "center", "right"] | None
        Horizontal alignment. If None, automatically set based on rotation

    Examples
    --------
    >>> rotate_tick_labels(ax)  # Rotate x-axis labels 45 degrees
    >>> rotate_tick_labels(ax, rotation=90, axis="both")
    """
    resolved_ha: Literal["left", "center", "right"]
    if ha is None:
        # Auto-determine alignment based on rotation
        if rotation > 0:
            resolved_ha = "right"
        elif rotation < 0:
            resolved_ha = "left"
        else:
            resolved_ha = "center"
    else:
        resolved_ha = ha

    # Apply rotation and alignment per-label rather than calling
    # set_xticklabels(get_xticklabels(), ...) — that pattern emits
    # matplotlib's "set_ticklabels() should only be used with a
    # fixed number of ticks" warning since the locator may not be
    # a FixedLocator. Iterating preserves the existing locator and
    # mutates the existing Text artists in place.
    if axis in ("x", "both"):
        for label in ax.get_xticklabels():
            label.set_rotation(rotation)
            label.set_horizontalalignment(resolved_ha)
    if axis in ("y", "both"):
        for label in ax.get_yticklabels():
            label.set_rotation(rotation)
            label.set_horizontalalignment(resolved_ha)
