"""Tick text: numbers, units, years and dates on an axis.

The ``format_axis_*`` helpers and :func:`axis_unit` install a formatter that
decides at every draw from the ticks in view: one unit for the axis and the
fewest decimals that print every tick exactly (``0.5M, 1.0M``; ``0, 1M``).
Axes nobody formatted get the library's numbers and dates from
``dm.simple_layout`` through :func:`prepare`: thousands separators, an SI
(or, in Korean figures, 만/억) unit from one million, whole two-digit years
and dates (``24.01``), quarters (``24.Q1``). Text that should read like the
ticks (bar value labels) asks :func:`tick_scale_of` and prints with
:func:`number_text`.
"""

from __future__ import annotations

import numbers
from collections.abc import Callable, Sequence
from typing import Any, Literal

import matplotlib.ticker as ticker
import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.axis import Axis

from .._figure_geometry import shared_axes
from .apply import figure_ladder, prepare, remember_dates, thin_dates
from .dates import CategoryDateFormatter, category_locator
from .formatters import (
    AxisUnitFormatter,
    LabelUnitFormatter,
    WholeYearLocator,
    YearTickFormatter,
    fill,
    tick_scale_of,
)
from .measure import config_digits, drawn_like_twin, settled_twin_spines
from .model import (
    LADDERS,
    MYRIAD_LOCALES,
    SI,
    Ladder,
    NumberStyle,
    PerTick,
    TickScale,
    Unit,
    parse_digits,
)
from .text import number_text, recommend_tick_decimals, value_label_decimals

__all__ = [
    "TickScale",
    "Unit",
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
    "prepare",
    "recommend_tick_decimals",
    "remember_dates",
    "rotate_tick_labels",
    "set_decimal",
    "settled_twin_spines",
    "thin_dates",
    "tick_scale_of",
    "value_label_decimals",
]

AxisName = Literal["x", "y", "both"]
# The fixed-decimal paths write each value alone.
FIXED_TEXT = PerTick(separators=False)
CURRENCY_TEXT = PerTick(zero="affixed")
MYRIAD_TEXT = PerTick(zero="exact", compact=True)


def _axes(ax: Axes, axis: str) -> list[Axis]:
    if axis not in ("x", "y", "both"):
        raise ValueError(f"axis must be 'x', 'y' or 'both', got {axis!r}")
    return [
        a
        for name, a in (("x", ax.xaxis), ("y", ax.yaxis))
        if axis in (name, "both")
    ]


def _install(ax: Axes, axis: str, make: Callable[[], ticker.Formatter]) -> None:
    for target in _axes(
        ax, axis
    ):  # each axis its own: the decision is per axis
        target.set_major_formatter(make())


def _numbers(
    ax: Axes,
    axis: str,
    ladder: Ladder,
    unit: str,
    decimals: int | None,
    per_tick: PerTick,
    currency: str = "",
) -> None:
    """One ladder; an integer ``decimals`` with ``unit="max"`` writes each tick alone."""
    each = per_tick if decimals is not None and unit == "max" else None
    style = NumberStyle.parse(
        ladder, unit, decimals=decimals, currency=currency, per_tick=each
    )
    _install(ax, axis, lambda: AxisUnitFormatter(style))


def format_axis_si(
    ax: Axes,
    axis: AxisName = "y",
    decimals: int | None = None,
    unit: str = "max",
) -> None:
    """SI units (k, M, G, T) on the ticks: one unit and decimal count per axis.

    ``unit="max"`` (default) takes the unit of the largest visible tick
    (``-1.0M, -0.5M, 0, 0.5M, 1.0M``; plain below 1000), ``"whole"`` a unit
    in which every tick is whole (``0, 200 … 1,200``), a prefix fixes it.
    Decimals are the fewest that print every tick exactly; an integer fixes
    them (with ``unit="max"`` each tick then takes its own prefix). Log axes
    give each tick its own unit (``0.1, 1, 10, 1k``).
    """
    _numbers(ax, axis, SI, unit, decimals, FIXED_TEXT)


def _one_unit(
    ax: Axes, axis: str, factor: float, suffix: str, decimals: int | None
) -> None:
    ladder = Ladder((Unit(factor, suffix),))
    each = FIXED_TEXT if decimals is not None else None
    style = NumberStyle.parse(ladder, suffix, decimals=decimals, per_tick=each)
    _install(ax, axis, lambda: AxisUnitFormatter(style))


def format_axis_millions(
    ax: Axes,
    axis: AxisName = "y",
    suffix: str = "M",
    decimals: int | None = None,
) -> None:
    """Ticks in millions (``0.5M, 1.0M``; ``1M, 2M``), fewest exact decimals.

    An integer ``decimals`` fixes the places on every tick.
    """
    _one_unit(ax, axis, 1e6, suffix, decimals)


def format_axis_billions(
    ax: Axes,
    axis: AxisName = "y",
    suffix: str = "B",
    decimals: int | None = None,
) -> None:
    """Ticks in billions (``1.5B``), as :func:`format_axis_millions`."""
    _one_unit(ax, axis, 1e9, suffix, decimals)


def format_axis_currency(
    ax: Axes,
    axis: AxisName = "y",
    symbol: str = "$",
    position: Literal["prefix", "suffix"] = "prefix",
    decimals: int = 0,
) -> None:
    """Currency ticks with ``decimals`` places: ``-$1,500``, ``$0``, ``1,000€``."""
    prefix = position == "prefix"
    ladder = Ladder((Unit(1.0, "" if prefix else symbol),))
    style = NumberStyle.parse(
        ladder,
        ladder.rungs[0].label,
        decimals=decimals,
        currency=symbol if prefix else "",
        per_tick=CURRENCY_TEXT,
    )
    _install(ax, axis, lambda: AxisUnitFormatter(style))


def format_axis_myriad(
    ax: Axes,
    axis: AxisName = "y",
    *,
    locale: str = "ko",
    decimals: int | None = None,
    currency: str = "",
    unit: str = "max",
) -> None:
    """East-Asian myriad units (만/억/조/경; zh 万/亿, ja 万/億) on the ticks.

    ``unit="max"`` (default) takes the unit of the largest visible tick
    (``0, 0.25억 … 1.75억``), ``"whole"`` a unit in which every tick is
    whole (``0, 2,500만 … 17,500만``), a ladder label fixes it. An integer
    ``decimals`` with ``unit="max"`` writes each tick alone in its own unit,
    trailing zeros dropped (``1.5억``, ``7,500``).
    """
    if locale not in MYRIAD_LOCALES:
        raise ValueError(
            f"locale must be one of 'ko', 'zh', or 'ja' (got {locale!r})"
        )
    _numbers(
        ax, axis, MYRIAD_LOCALES[locale], unit, decimals, MYRIAD_TEXT, currency
    )


def _fixed_point(places: int) -> ticker.FuncFormatter:
    def text(value: float, _pos: object = None) -> str:
        return f"{value:.{places}f}"

    return ticker.FuncFormatter(text)


def set_decimal(ax: Axes, xn: int | None = None, yn: int | None = None) -> None:
    """Fixed-point tick text with ``xn`` / ``yn`` places; ``None`` leaves an axis."""
    for places, axis in ((xn, ax.xaxis), (yn, ax.yaxis)):
        if places is not None:
            format(0.0, f".{places}f")  # refuse a bad count before changing
            axis.set_major_formatter(_fixed_point(places))


_YEAR_SUFFIX = {"ko": "년", "ja": "年", "zh": "年", "en": ""}


def format_axis_year(
    ax: Axes,
    axis: AxisName = "x",
    locale: Literal["ko", "ja", "zh", "en"] = "ko",
    digits: Literal[2, 4] = 2,
) -> None:
    """Year ticks with a locale suffix: ``25년`` (``digits=4``: ``2025년``).

    Unless someone set the locator, ticks fall on whole years. Two digits
    that would repeat print four; a tick between years (a zoom under two
    years) makes every tick print its value.
    """
    if locale not in _YEAR_SUFFIX:
        raise ValueError(
            f"Unknown locale {locale!r}; valid locales: {', '.join(_YEAR_SUFFIX)}"
        )
    count = parse_digits(digits, "digits")
    for target in _axes(ax, axis):
        if target.isDefault_majloc:
            target.set_major_locator(WholeYearLocator())
        target.set_major_formatter(
            YearTickFormatter(count, _YEAR_SUFFIX[locale])
        )


def category_dates(
    dates: Sequence[Any] | npt.NDArray[Any],
) -> npt.NDArray[np.datetime64]:
    """The dates positions ``0, 1, …`` stand for, as ``datetime64[s]``.

    ISO strings, ``datetime`` / ``date`` values, pandas timestamps or a
    ``datetime64`` array; a number, ``None`` or an unparsable string raises.
    """
    dtype = getattr(dates, "dtype", None)
    if isinstance(dtype, np.dtype) and dtype.kind == "M":
        values = list(np.asarray(dates).astype("datetime64[s]").ravel())
    else:
        values = list(np.asarray(dates, dtype=object).ravel())
    if not values:
        raise ValueError("format_axis_dates needs at least one date")
    parsed: list[np.datetime64] = []
    for position, value in enumerate(values):
        try:
            if isinstance(value, numbers.Number | np.number | np.bool_):
                raise TypeError("a number is not a date")
            day = np.datetime64(value, "s")
        except (TypeError, ValueError):
            day = np.datetime64("NaT", "s")
        if np.isnat(day):
            raise ValueError(
                f"format_axis_dates: position {position} ({value!r}) is not "
                "a date; pass ISO strings such as '2024-01' or datetimes"
            )
        parsed.append(day)
    return np.array(parsed, dtype="datetime64[s]")


def format_axis_dates(
    ax: Axes,
    dates: Sequence[Any] | Any,
    axis: Literal["x", "y"] = "x",
    *,
    years: Literal[2, 4] | None = None,
) -> None:
    """Label category positions with the dates they stand for.

    For bars at ``0 … n-1`` whose categories are dates: the labels read
    ``24.01, 24.02 …`` (quarters ``23.Q1``), and ``dm.simple_layout`` thins a
    crowded axis to every 2nd, 3rd, 4th, 6th or 12th month (quarters: 2nd,
    4th, 8th, keeping Q1) instead of rotating. ``years`` is 2 or 4; ``None``
    follows ``dm.config.tick_years``. Call after drawing, before the layout::

        ax.bar(range(len(df)), df["sales"])
        dm.format_axis_dates(ax, df["month"])
    """
    if axis not in ("x", "y"):
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")
    count = config_digits() if years is None else parse_digits(years)
    parsed = category_dates(dates)
    formatter = CategoryDateFormatter(parsed, count)
    target = ax.xaxis if axis == "x" else ax.yaxis
    target.set_major_locator(category_locator(parsed, formatter.quarters))
    target.set_major_formatter(formatter)


def _template(label: str) -> str:
    if "{unit}" in label:
        return label
    return f"{label} ({{unit}})" if label.strip() else "({unit})"


def axis_unit(
    ax: Axes,
    axis: Literal["x", "y"] = "y",
    *,
    label: str | None = None,
    ladder: Literal["auto", "myriad", "finance", "si"] = "auto",
    scale: str = "max",
    decimals: int | None = None,
) -> LabelUnitFormatter:
    """Put the axis unit in the axis label and print the ticks as plain numbers.

    ``0, 0.2 … 1.0`` under ``인구 (억명)`` instead of ``0.2억 … 1.0억``::

        dm.axis_unit(ax, "y", label="인구 ({unit}명)")
        dm.axis_unit(ax, "y", label="Exports (USD {unit})", ladder="finance")

    ``label`` marks the unit with ``{unit}``; without it the unit is appended
    in parentheses (``None``: the current label). ``ladder="auto"`` follows
    ``dm.config.number_ladder`` (만/억 when the figure or the label is
    Korean). ``scale`` is ``"max"``, ``"whole"`` or a ladder symbol; an
    integer ``decimals`` fixes the count. Axes sharing the ticker
    (``sharex`` / ``sharey``) get the unit in their own non-empty labels. A
    label you set later is yours and stays as you wrote it. Returns the
    installed formatter; its ``unit`` is the unit of the last draw.
    """
    if axis not in ("x", "y"):
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")
    target = ax.xaxis if axis == "x" else ax.yaxis
    current = target.get_major_formatter()
    known = current.templates if isinstance(current, LabelUnitFormatter) else {}
    if label is None:
        label = target.label.get_text()
        if (
            isinstance(current, LabelUnitFormatter)
            and current.wrote.get(target) == label
        ):
            label = known.get(target, label)  # called again: keep the template
    template = _template(label)
    if ladder == "auto":
        rungs = figure_ladder(ax.get_figure(root=True), template)
    elif ladder in LADDERS:
        rungs = LADDERS[ladder]
    else:
        raise ValueError(
            f"ladder must be 'auto', 'myriad', 'finance' or 'si', got {ladder!r}"
        )
    try:
        style = NumberStyle.parse(rungs, scale, decimals=decimals)
    except ValueError as error:
        raise ValueError(f"scale: {error}") from None
    templates: dict[Axis, str] = {target: template}
    for other in _sharing(target):
        text = other.label.get_text()
        if other in known:
            templates[other] = known[other]
        elif text.strip():
            templates[other] = _template(text)
    formatter = LabelUnitFormatter(style, templates)
    if isinstance(current, LabelUnitFormatter):
        formatter.wrote.update(
            {a: t for a, t in current.wrote.items() if a is not target}
        )
    target.set_major_formatter(formatter)
    text = fill(template, "")
    target.label.set_text(text)
    formatter.wrote[target] = text
    for other in templates:
        formatter.wrote.setdefault(other, other.label.get_text())
    return formatter


def _sharing(axis: Axis) -> list[Axis]:
    """The other axes sharing ``axis``'s ticker (``sharex`` / ``sharey``)."""
    ax = axis.axes
    which = "x" if axis is ax.xaxis else "y"
    axes: list[Axis] = [
        m.xaxis if which == "x" else m.yaxis for m in shared_axes(ax, which)
    ]
    return [a for a in axes if a is not axis and a.major is axis.major]


def axis_unit_of(ax: Axes, axis: Literal["x", "y"] = "y") -> Unit | None:
    """The unit :func:`axis_unit` chose for this axis at the last draw, if any."""
    if axis not in ("x", "y"):
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")
    formatter = (ax.xaxis if axis == "x" else ax.yaxis).get_major_formatter()
    return formatter.unit if isinstance(formatter, LabelUnitFormatter) else None


def rotate_tick_labels(
    ax: Axes,
    axis: AxisName = "x",
    rotation: float = 45,
    ha: Literal["left", "center", "right"] | None = None,
) -> None:
    """Turn the tick labels in place (the last resort for long names).

    ``ha`` defaults to ``"right"`` for a positive angle, ``"left"`` for a
    negative one and ``"center"`` for none.
    """
    align = ha or (
        "right" if rotation > 0 else "left" if rotation < 0 else "center"
    )
    for target in _axes(ax, axis):
        for text in target.get_ticklabels():
            text.set_rotation(rotation)
            text.set_horizontalalignment(align)
