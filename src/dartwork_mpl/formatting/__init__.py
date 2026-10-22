"""Enhanced formatting utilities for dartwork-mpl.

This module provides additional formatting functions for axes,
tick labels, and other matplotlib elements.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from itertools import pairwise
from typing import Any, Literal

import matplotlib.ticker as ticker
from matplotlib.axes import Axes

from ._axis_wide import AxisUnitFormatter, Unit
from ._decimals import recommend_tick_decimals

__all__ = [
    "avoid_tick_overlap",
    "format_axis_billions",
    "format_axis_currency",
    "format_axis_millions",
    "format_axis_myriad",
    "format_axis_si",
    "format_axis_year",
    "recommend_tick_decimals",
    "rotate_tick_labels",
    "set_decimal",
]

_YEAR_SUFFIX = {"ko": "년", "ja": "年", "zh": "年", "en": ""}

_SI_LADDER = (
    Unit(1.0, ""),
    Unit(1e3, "k"),
    Unit(1e6, "M"),
    Unit(1e9, "G"),
    Unit(1e12, "T"),
)


def _set_formatter(
    ax: Axes, axis: str, make: Callable[[], ticker.Formatter]
) -> None:
    # Axis-wide formatters keep per-axis state, so each axis gets its own.
    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(make())
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(make())


def format_axis_year(
    ax: Axes,
    axis: Literal["x", "y", "both"] = "x",
    locale: Literal["ko", "ja", "zh", "en"] = "ko",
    digits: Literal[2, 4] = 2,
) -> None:
    """Format numeric year ticks with a locale suffix.

    Tick years use the last two digits by default (``2025`` -> ``25년``):
    four-digit years double the tick width and crowd neighbouring labels.
    Pass ``digits=4`` only when an axis spans a century or more, where two
    digits cannot tell ``1965`` from ``2065``.

    Parameters
    ----------
    ax:
        Matplotlib axes to format.
    axis:
        Axis to format: ``"x"``, ``"y"``, or ``"both"``.
    locale:
        Locale suffix to apply. Korean uses ``년``, Japanese and Chinese use
        ``年``, and English uses no suffix.
    digits:
        ``2`` (default) prints ``25``; ``4`` prints ``2025``.
    """
    if locale not in _YEAR_SUFFIX:
        valid = ", ".join(_YEAR_SUFFIX)
        raise ValueError(f"Unknown locale {locale!r}; valid locales: {valid}")
    if digits not in (2, 4):
        raise ValueError(f"digits must be 2 or 4, got {digits!r}")

    suffix = _YEAR_SUFFIX[locale]

    def formatter(value: float, _pos: int | None = None) -> str:
        year = round(value)
        if digits == 2:
            return f"{year % 100:02d}{suffix}"
        return f"{year}{suffix}"

    year_formatter = ticker.FuncFormatter(formatter)

    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(year_formatter)
    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(year_formatter)


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
    decimals: int | None = None,
    currency: str = "",
    unit: str = "max",
) -> None:
    """Format axis ticks using East-Asian myriad units.

    The whole axis shares one unit from the ladder none/만/억/조/경
    (zh: 万/亿/兆/京, ja: 万/億/兆/京) and one decimal count, settled from
    the visible ticks on every draw, so an axis never mixes ``7,500만``
    with ``1.25억`` and digit counts read at a glance:

    - ``unit="max"`` (default): the unit of the largest visible
      ``|tick|`` — ``0, 0.25억 … 1.75억``. Below 10,000 the ticks are plain
      numbers with thousands separators (``0, 2,000 … 8,000``).
    - ``unit="whole"``: a unit in which every visible tick is a whole
      number, and of those the one whose longest label is shortest
      (``0, 2,500만 … 17,500만``); with no such unit, the fewest decimals.
    - A ladder label (``""``, ``"만"``, ``"억"``, ``"조"``, ``"경"`` or the
      locale's equivalents) fixes that unit.

    Decimals are the fewest that render every visible tick exactly in the
    chosen unit (none on a whole-number axis, ``0.25억, 0.50억`` on a
    quarter step). Zero prints as ``0``; scaled values of 1000 and more
    carry thousands separators. On a log axis the ticks span decades, which
    cannot share one unit, so each tick takes its own.

    Parameters
    ----------
    ax:
        Matplotlib axes to format.
    axis:
        Which axis to format: "x", "y", or "both".
    locale:
        Unit ladder locale: "ko", "zh", or "ja".
    decimals:
        ``None`` (default) chooses decimals as above. An integer with the
        default ``unit`` keeps the previous per-tick output: each tick takes
        its own unit, is rounded to that many places and trims trailing
        zeros. With another ``unit`` an integer fixes the decimal count.
    currency:
        Optional currency prefix inserted after the sign.
    unit:
        ``"max"`` (default), ``"whole"`` or a ladder label, as above.
    """
    if locale not in _MYRIAD_UNIT_LADDERS:
        raise ValueError(
            f"locale must be one of 'ko', 'zh', or 'ja' (got {locale!r})"
        )
    if axis not in {"x", "y", "both"}:
        raise ValueError("axis must be one of 'x', 'y', or 'both'")
    if decimals is not None and decimals < 0:
        raise ValueError("decimals must be non-negative")

    unit_ladder = _MYRIAD_UNIT_LADDERS[locale]
    ladder = [Unit(1.0, ""), *(Unit(float(t), u) for t, u in unit_ladder)]
    # Validate ``unit`` before touching the axes.
    AxisUnitFormatter(ladder, unit)

    if decimals is not None and unit == "max":
        legacy_decimals = decimals
    else:
        _set_formatter(
            ax,
            axis,
            lambda: AxisUnitFormatter(
                ladder, unit, decimals=decimals, currency=currency
            ),
        )
        return

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
        formatted = f"{scaled:,.{legacy_decimals}f}"
        if legacy_decimals > 0:
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
    decimals: int | None = None,
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
    decimals : int | None
        ``None`` (default) chooses one decimal count per axis from the
        visible ticks after dividing by 10^6: the fewest that render every
        tick exactly, so ``1M, 2M`` print no decimals and ``0.5M, 1.0M``
        keep one on every tick. Zero prints as ``0``; scaled values of 1000
        and more carry thousands separators. An integer fixes the decimal
        places (previous output).

    Examples
    --------
    >>> format_axis_millions(ax)  # Show as 1.5M instead of 1500000
    """
    if decimals is None:
        _set_formatter(
            ax, axis, lambda: AxisUnitFormatter([Unit(1e6, suffix)], suffix)
        )
        return

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
    decimals: int | None = None,
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
    decimals : int | None
        ``None`` (default) chooses one decimal count per axis from the
        visible ticks after dividing by 10^9, as in
        :func:`format_axis_millions`. An integer fixes the decimal places.

    Examples
    --------
    >>> format_axis_billions(ax)  # Show as 1.5B instead of 1500000000
    """
    if decimals is None:
        _set_formatter(
            ax, axis, lambda: AxisUnitFormatter([Unit(1e9, suffix)], suffix)
        )
        return

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
    ax: Axes,
    axis: Literal["x", "y", "both"] = "y",
    decimals: int | None = None,
    unit: str = "max",
) -> None:
    """Format axis tick labels with SI prefixes (k, M, G, T).

    The whole axis shares one unit from the ladder none/k/M/G/T and one
    decimal count, settled from the ticks inside the view on every draw, so
    an axis never mixes ``800`` with ``1.2k`` and digit counts read at a
    glance:

    - ``unit="max"`` (default): the unit of the largest visible ``|tick|``
      — ``0, 0.2k … 1.2k``; ``-1.0M, -0.5M, 0, 0.5M, 1.0M``. Below 1000 the
      ticks are plain numbers (``0, 200 … 800``).
    - ``unit="whole"``: a unit in which every visible tick is a whole
      number, and of those the one whose longest label is shortest
      (``0, 200 … 1,200``; ``-1,000k … 1,000k``); with no such unit, the
      fewest decimals.
    - ``""``, ``"k"``, ``"M"``, ``"G"`` or ``"T"`` fixes that unit.

    Decimals are the fewest that render every visible tick exactly in the
    chosen unit: none on a whole-number axis (``0, 1k … 5k``), and the same
    count on every tick of a fractional step (``0.25k, 0.50k``). Zero prints
    as ``0``; scaled values of 1000 and more carry thousands separators
    (``1,200``, ``1,000k``). Log and other non-linear scales span decades,
    which cannot share one unit, so there each tick takes its own prefix
    and decimals (``0.1, 1, 10, 1k``).

    Parameters
    ----------
    ax : Axes
        Matplotlib axes
    axis : Literal["x", "y", "both"]
        Which axis to format
    decimals : int | None
        ``None`` (default) chooses decimals as above. An integer with the
        default ``unit`` keeps the previous output: each tick on its own
        with that many decimals and a per-tick prefix (``800.0``, ``1.2k``).
        With another ``unit`` an integer fixes the decimal count.
    unit : str
        ``"max"`` (default), ``"whole"``, or a fixed prefix, as above.

    Examples
    --------
    >>> format_axis_si(ax)  # 0, 0.2k … 1.2k  or  0, 1M, 2M
    >>> format_axis_si(ax, unit="whole")  # 0, 200 … 1,200
    >>> format_axis_si(ax, unit="k")  # 0, 500k, 1,000k
    """
    # Validate ``unit`` before touching the axes.
    AxisUnitFormatter(_SI_LADDER, unit)
    if decimals is None or unit != "max":
        _set_formatter(
            ax,
            axis,
            lambda: AxisUnitFormatter(_SI_LADDER, unit, decimals=decimals),
        )
        return

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


def avoid_tick_overlap(
    ax: Axes,
    axis: Literal["x", "y"] = "x",
    *,
    max_visible: int = 8,
    rotation: float = 30,
) -> None:
    """Reduce dense tick-label collisions before layout is computed.

    If an axis has too many visible labels, hide evenly spaced intermediate
    labels while keeping the first and last visible. If the remaining labels
    still overlap after a draw, rotate them in place. Call this after
    setting ticks/labels and before ``simple_layout``.
    """
    fig = ax.get_figure()
    if fig is None or fig.canvas is None:
        return

    labels = ax.get_xticklabels() if axis == "x" else ax.get_yticklabels()
    visible = [
        label for label in labels if label.get_visible() and label.get_text()
    ]
    if len(visible) <= 1:
        return

    if max_visible > 0 and len(visible) > max_visible:
        step = max(1, math.ceil(len(visible) / max_visible))
        last_idx = len(visible) - 1
        for idx, label in enumerate(visible):
            label.set_visible(idx == 0 or idx == last_idx or idx % step == 0)

    canvas: Any = fig.canvas
    canvas.draw()
    renderer = canvas.get_renderer()
    visible = [
        label for label in labels if label.get_visible() and label.get_text()
    ]
    if len(visible) <= 1:
        return
    boxes = [label.get_window_extent(renderer) for label in visible]
    if axis == "x":
        boxes = sorted(boxes, key=lambda box: box.x0)
        overlaps = any(a.x1 > b.x0 - 1 for a, b in pairwise(boxes))
        if overlaps:
            for label in visible:
                label.set_rotation(rotation)
                label.set_horizontalalignment("right")
    else:
        boxes = sorted(boxes, key=lambda box: box.y0)
        overlaps = any(a.y1 > b.y0 - 1 for a, b in pairwise(boxes))
        if overlaps:
            for label in visible:
                label.set_rotation(rotation)
                label.set_verticalalignment("center")


def set_decimal(ax: Axes, xn: int | None = None, yn: int | None = None) -> None:
    """Format current and future ticks with Python fixed-point precision.

    Keep each axis's locator and view limits, including after data changes.
    Half-even rounding and negative zero follow Python float formatting.
    Invalid precision raises immediately before installing that axis's formatter;
    an axis requested as None is untouched. Return None.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The Axes to modify.
    xn : int | None, optional
        Number of decimal places for x-axis tick labels.
        If None, the x-axis is left unchanged.
    yn : int | None, optional
        Number of decimal places for y-axis tick labels.
        If None, the y-axis is left unchanged.
    """
    if xn is not None:
        format(0.0, f".{xn}f")  # Validate before changing this axis.
        ax.xaxis.set_major_formatter(
            ticker.FuncFormatter(lambda value, _position: f"{value:.{xn}f}")
        )

    if yn is not None:
        format(0.0, f".{yn}f")
        ax.yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda value, _position: f"{value:.{yn}f}")
        )
