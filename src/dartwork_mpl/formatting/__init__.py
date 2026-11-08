"""Enhanced formatting utilities for dartwork-mpl.

This module provides additional formatting functions for axes,
tick labels, and other matplotlib elements.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from itertools import pairwise
from typing import Any, Literal

import matplotlib.ticker as ticker
from matplotlib.axes import Axes

from .._figure_geometry import get_renderer
from ._axis_wide import (
    SI_LADDER,
    AxisUnitFormatter,
    TickScale,
    TickText,
    Unit,
    number_text,
    tick_scale_of,
)
from ._decimals import recommend_tick_decimals, value_label_decimals
from ._defaults import (
    CategoryDateFormatter,
    _category_locator,
    apply_default_tick_format,
    category_dates,
    thin_crowded_date_ticks,
)
from ._label_unit import axis_unit, axis_unit_of
from ._twin_colors import apply_twin_colors
from ._twin_spines import drawn_like_twin, settled_twin_spines, show_twin_spines
from ._years import WholeYearLocator, YearTickFormatter, requested_params

__all__ = [
    "TickScale",
    "apply_default_tick_format",
    "apply_twin_colors",
    "avoid_tick_overlap",
    "axis_unit",
    "axis_unit_of",
    "drawn_like_twin",
    "format_axis_billions",
    "format_axis_currency",
    "format_axis_dates",
    "format_axis_millions",
    "format_axis_myriad",
    "format_axis_si",
    "format_axis_year",
    "number_text",
    "recommend_tick_decimals",
    "rotate_tick_labels",
    "set_decimal",
    "settled_twin_spines",
    "show_twin_spines",
    "thin_crowded_date_ticks",
    "tick_scale_of",
    "value_label_decimals",
]

_YEAR_SUFFIX = {"ko": "년", "ja": "年", "zh": "年", "en": ""}

# Defined beside the other ladders in ``_axis_wide``; ``_defaults`` reads
# this name.
_SI_LADDER = SI_LADDER

# What the fixed-decimal paths print, each value alone (``per_tick``):
# ``decimals=n`` of millions / billions / si (``1000.0k``, ``-1.5M``, ``0.0``),
# ``format_axis_currency`` (``-$1,500``, ``$0``) and ``decimals=n`` of myriad
# (``1.5억``, ``7,500``, ``-$0``).
_FIXED_TEXT = TickText(separators=False)
_CURRENCY_TEXT = TickText(zero="affixed")
_MYRIAD_TEXT = TickText(zero="exact", compact=True)


def _set_formatter(
    ax: Axes, axis: str, make: Callable[[], ticker.Formatter]
) -> None:
    # Axis-wide formatters keep per-axis state, so each axis gets its own.
    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(make())
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(make())


def _one_unit(unit: Unit, decimals: int | None) -> AxisUnitFormatter:
    """``unit`` on every tick: decimals per axis, or ``decimals`` per value.

    An integer keeps the fixed-decimal output: no thousands separators, the
    hyphen-minus, and a value that rounds to zero as a bare ``0.0`` (never
    ``-0.0M``).
    """
    if decimals is None:
        return AxisUnitFormatter([unit], unit.label)
    return AxisUnitFormatter(
        [unit], unit.label, decimals=decimals, per_tick=_FIXED_TEXT
    )


def format_axis_year(
    ax: Axes,
    axis: Literal["x", "y", "both"] = "x",
    locale: Literal["ko", "ja", "zh", "en"] = "ko",
    digits: Literal[2, 4] = 2,
) -> None:
    """Format numeric year ticks with a locale suffix.

    Tick years use the last two digits by default (``2025`` -> ``25년``):
    four-digit years double the tick width and crowd neighbouring labels.
    Two digits that would repeat (``1965`` and ``2065`` in view) print four;
    ``digits=4`` prints four always. Unless someone set the axis's locator,
    it ticks whole years (a tick count asked with ``ax.locator_params`` is
    kept), so fractional-year data such as months read ``05년, 06년``. When a
    tick in view still falls between years (a zoom under two years, a
    locator someone set), every tick prints its value (``2019.2 …
    2019.7``), never a rounded year. The formatter is the library's year
    formatter, matplotlib's ``ScalarFormatter`` underneath, so
    ``ax.ticklabel_format`` works on it.

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
    for name, target in (("x", ax.xaxis), ("y", ax.yaxis)):
        if axis not in (name, "both"):
            continue
        if target.isDefault_majloc:  # a locator someone set stays
            asked = requested_params(target.get_major_locator())
            target.set_major_locator(WholeYearLocator(**asked))
        target.set_major_formatter(YearTickFormatter(digits, suffix))


def format_axis_dates(
    ax: Axes,
    dates: Sequence[Any] | Any,
    axis: Literal["x", "y"] = "x",
    *,
    years: Literal[2, 4] | None = None,
    style: Literal["period", "concise"] | None = None,
) -> None:
    """Label category positions with the dates they stand for.

    For bars (or any chart drawn at positions ``0, 1, ... n-1``) whose
    categories are dates, such as twelve monthly bars over ``"2024-01" …
    "2024-12"``. The labels become the library's date words, the ones a
    real date axis gets: ``24.01, 24.02 …`` by default; quarterly dates
    read ``23.Q1, 23.Q2 …``. :func:`dm.simple_layout
    <dartwork_mpl.simple_layout>` thins a crowded axis to every 2nd, 3rd,
    4th, 6th or 12th month (quarters: every 2nd, 4th or 8th, keeping Q1;
    other spacings: 2, 3, 4, 5 …) until the labels are one em apart, with
    ticks only under labelled positions. Use it instead of rotating date
    labels; rotation stays the last resort.

    ``style="concise"`` gives matplotlib's concise words with two-digit
    years (``24, Feb, Mar …``; ``24년, 2월, 3월 …`` when the figure's labels
    are Korean; quarters ``23, Q2, Q3 …``), and ``years=4, style="concise"``
    matplotlib's own concise words (``2024, Feb, Mar …``, quarters as
    months).

    Replaces the axis's tick positions and labels; the bars, their order
    and the axis limits are unchanged. Call it after drawing and before
    ``dm.simple_layout``::

        bars = ax.bar(range(len(df)), df["sales"])
        dm.format_axis_dates(ax, df["month"])   # "2024-01" ... "2024-12"
        dm.simple_layout(fig)

    Parameters
    ----------
    ax:
        Matplotlib axes whose categories sit at ``0 … len(dates) - 1``
        (``ax.bar(range(n), …)`` or string categories).
    dates:
        One date per position, in position order: ISO strings
        (``"2024-01"``, ``"2024-01-15"``), ``datetime`` / ``date`` values,
        pandas timestamps or a ``datetime64`` array.
    axis:
        ``"x"`` (default) for vertical bars, ``"y"`` for horizontal ones.
    years:
        ``2`` (``24.01``) or ``4`` (``2024.01``); ``None`` (default) follows
        ``dm.config.tick_years``. Two-digit years that would repeat (a
        century of dates) print four digits.
    style:
        ``"period"`` (``24.01``) or ``"concise"`` (``24, Feb``); ``None``
        (default) follows ``dm.config.date_style``.

    Raises
    ------
    ValueError
        If ``dates`` is empty, holds a value that is not a date, ``axis``
        is not ``"x"`` or ``"y"``, ``years`` is not 2 or 4, or ``style`` is
        not ``"period"`` or ``"concise"``.
    """
    if axis not in ("x", "y"):
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")
    parsed = category_dates(dates)
    formatter = CategoryDateFormatter(parsed, years=years, style=style)
    target = ax.xaxis if axis == "x" else ax.yaxis
    target.set_major_locator(
        _category_locator(parsed, quarters=formatter.quarters)
    )
    target.set_major_formatter(formatter)


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

    # An integer with ``unit="max"`` keeps each tick in its own unit.
    per_tick = _MYRIAD_TEXT if decimals is not None and unit == "max" else None
    _set_formatter(
        ax,
        axis,
        lambda: AxisUnitFormatter(
            ladder,
            unit,
            decimals=decimals,
            currency=currency,
            per_tick=per_tick,
        ),
    )


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
    _set_formatter(ax, axis, lambda: _one_unit(Unit(1e6, suffix), decimals))


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
    _set_formatter(ax, axis, lambda: _one_unit(Unit(1e9, suffix), decimals))


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
    # The sign goes outside the symbol (``-$1,000``, not ``$-1,000``) and
    # drops when the value rounds to zero (``$0``, never ``-$0``). Any
    # position other than "prefix" writes the symbol after the number.
    prefix = position == "prefix"
    unit = Unit(1.0, "" if prefix else symbol)
    _set_formatter(
        ax,
        axis,
        lambda: AxisUnitFormatter(
            [unit],
            unit.label,
            decimals=decimals,
            currency=symbol if prefix else "",
            per_tick=_CURRENCY_TEXT,
        ),
    )


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
    # An integer with ``unit="max"`` keeps each tick in its own prefix.
    per_tick = _FIXED_TEXT if decimals is not None and unit == "max" else None
    _set_formatter(
        ax,
        axis,
        lambda: AxisUnitFormatter(
            _SI_LADDER, unit, decimals=decimals, per_tick=per_tick
        ),
    )


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
    renderer = get_renderer(fig)
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

    Installs a dynamic ``FuncFormatter`` that formats every tick value
    when drawn, so ticks that appear after the view changes follow it too.
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
