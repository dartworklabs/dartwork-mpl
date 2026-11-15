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

import matplotlib.ticker as ticker
import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.axis import Axis

from ..geometry import (
    Letter,
    Letters,
    Which,
    X,
    Y,
    axis_of,
    parse_axes,
    parse_which,
    shared_axes,
)
from .apply import figure_ladder, prepare, remember_dates, thin_dates
from .dates import CategoryDateFormatter, category_locator
from .defaults import config
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
    SI,
    AffixedZero,
    AlignCentre,
    AlignLeft,
    AlignRight,
    CurrencyPosition,
    DateLike,
    Digits,
    ExactZero,
    FollowFigure,
    HAlign,
    HAlignName,
    Ladder,
    LadderName,
    NumberStyle,
    PerTick,
    TickScale,
    Unit,
    YearLocale,
    myriad_ladder,
    parse_currency_position,
    parse_digits,
    parse_halign,
    parse_ladder_name,
    unit_template,
    year_suffix,
)
from .text import number_text, recommend_tick_decimals, value_label_decimals

__all__ = [
    "TickScale",
    "Unit",
    "axis_unit",
    "axis_unit_of",
    "config",
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

# The fixed-decimal paths write each value alone.
FIXED_TEXT = PerTick(separators=False)
CURRENCY_TEXT = PerTick(zero=AffixedZero())
MYRIAD_TEXT = PerTick(zero=ExactZero(), compact=True)


def _axes(ax: Axes, axis: object) -> list[Axis]:
    return [axis_of(ax, which) for which in parse_axes(axis)]


def _install(
    ax: Axes, axis: object, make: Callable[[], ticker.Formatter]
) -> None:
    for target in _axes(
        ax, axis
    ):  # each axis its own: the decision is per axis
        target.set_major_formatter(make())


def _numbers(
    ax: Axes,
    axis: object,
    ladder: Ladder,
    unit: str,
    decimals: int | None,
    per_tick: PerTick,
    currency: str = "",
) -> None:
    """One ladder; an integer ``decimals`` with ``unit="max"`` writes each tick alone."""
    style = NumberStyle.parse(
        ladder, unit, decimals=decimals, currency=currency
    ).each_alone(per_tick)
    _install(ax, axis, lambda: AxisUnitFormatter(style))


def format_axis_si(
    ax: Axes,
    axis: Letters = "y",
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
    ax: Axes, axis: object, factor: float, suffix: str, decimals: int | None
) -> None:
    ladder = Ladder((Unit(factor, suffix),))
    each = FIXED_TEXT if decimals is not None else None
    style = NumberStyle.parse(ladder, suffix, decimals=decimals, per_tick=each)
    _install(ax, axis, lambda: AxisUnitFormatter(style))


def format_axis_millions(
    ax: Axes,
    axis: Letters = "y",
    suffix: str = "M",
    decimals: int | None = None,
) -> None:
    """Ticks in millions (``0.5M, 1.0M``; ``1M, 2M``), fewest exact decimals.

    An integer ``decimals`` fixes the places on every tick.
    """
    _one_unit(ax, axis, 1e6, suffix, decimals)


def format_axis_billions(
    ax: Axes,
    axis: Letters = "y",
    suffix: str = "B",
    decimals: int | None = None,
) -> None:
    """Ticks in billions (``1.5B``), as :func:`format_axis_millions`."""
    _one_unit(ax, axis, 1e9, suffix, decimals)


def format_axis_currency(
    ax: Axes,
    axis: Letters = "y",
    symbol: str = "$",
    position: CurrencyPosition = "prefix",
    decimals: int = 0,
) -> None:
    """Currency ticks with ``decimals`` places: ``-$1,500``, ``$0``, ``1,000€``."""
    currency, label = parse_currency_position(position).parts(symbol)
    ladder = Ladder((Unit(1.0, label),))
    style = NumberStyle.parse(
        ladder,
        label,
        decimals=decimals,
        currency=currency,
        per_tick=CURRENCY_TEXT,
    )
    _install(ax, axis, lambda: AxisUnitFormatter(style))


def format_axis_myriad(
    ax: Axes,
    axis: Letters = "y",
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
    _numbers(
        ax, axis, myriad_ladder(locale), unit, decimals, MYRIAD_TEXT, currency
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


def format_axis_year(
    ax: Axes, axis: Letters = "x", locale: YearLocale = "ko", digits: Digits = 2
) -> None:
    """Year ticks with a locale suffix: ``25년`` (``digits=4``: ``2025년``).

    Unless someone set the locator, ticks fall on whole years. Two digits
    that would repeat print four; a tick between years (a zoom under two
    years) makes every tick print its value.
    """
    suffix = year_suffix(locale)
    count = parse_digits(digits, "digits")
    for target in _axes(ax, axis):
        if target.isDefault_majloc:
            target.set_major_locator(WholeYearLocator())
        target.set_major_formatter(YearTickFormatter(count, suffix))


def category_dates(
    dates: Sequence[DateLike] | npt.ArrayLike,
) -> npt.NDArray[np.datetime64]:
    """The dates positions ``0, 1, …`` stand for, as ``datetime64[s]``.

    ISO strings, ``datetime`` / ``date`` values, pandas timestamps or a
    ``datetime64`` array; a number, ``None`` or an unparsable string raises.
    """
    loose = np.asarray(dates, dtype=object)
    try:
        typed = np.asarray(dates)
    except (TypeError, ValueError):  # ragged input stays loose
        typed = loose
    if np.issubdtype(typed.dtype, np.datetime64):
        values = list(typed.astype("datetime64[s]").ravel())
    else:
        values = list(loose.ravel())
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
    dates: Sequence[DateLike] | npt.ArrayLike,
    axis: Letter = "x",
    *,
    years: Digits | None = None,
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
    which = parse_which(axis)
    count = config_digits() if years is None else parse_digits(years)
    parsed = category_dates(dates)
    formatter = CategoryDateFormatter(parsed, count)
    target = axis_of(ax, which)
    target.set_major_locator(category_locator(parsed, formatter.quarters))
    target.set_major_formatter(formatter)


def axis_unit(
    ax: Axes,
    axis: Letter = "y",
    *,
    label: str | None = None,
    ladder: LadderName = "auto",
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
    target = axis_of(ax, parse_which(axis))
    current = target.get_major_formatter()
    known = current.templates if isinstance(current, LabelUnitFormatter) else {}
    if label is None:
        label = target.label.get_text()
        if (
            isinstance(current, LabelUnitFormatter)
            and current.wrote.get(target) == label
        ):
            label = known.get(target, label)  # called again: keep the template
    template = unit_template(label)
    match parse_ladder_name(ladder):
        case FollowFigure():
            rungs = figure_ladder(ax.get_figure(root=True), template)
        case Ladder() as asked:
            rungs = asked
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
            templates[other] = unit_template(text)
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
    which: Which = X() if axis is ax.xaxis else Y()
    axes: list[Axis] = [
        axis_of(m, which) for m in shared_axes(ax, which.letter)
    ]
    return [a for a in axes if a is not axis and a.major is axis.major]


def axis_unit_of(ax: Axes, axis: Letter = "y") -> Unit | None:
    """The unit :func:`axis_unit` chose for this axis at the last draw, if any."""
    formatter = axis_of(ax, parse_which(axis)).get_major_formatter()
    return formatter.unit if isinstance(formatter, LabelUnitFormatter) else None


def rotate_tick_labels(
    ax: Axes,
    axis: Letters = "x",
    rotation: float = 45,
    ha: HAlignName | None = None,
) -> None:
    """Turn the tick labels in place (the last resort for long names).

    ``ha`` defaults to ``"right"`` for a positive angle, ``"left"`` for a
    negative one and ``"center"`` for none.
    """
    align: HAlign = (
        parse_halign(ha)
        if ha is not None
        else AlignRight()
        if rotation > 0
        else AlignLeft()
        if rotation < 0
        else AlignCentre()
    )
    for target in _axes(ax, axis):
        for text in target.get_ticklabels():
            text.set_rotation(rotation)
            text.set_horizontalalignment(align.mpl)
