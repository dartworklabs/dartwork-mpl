"""Tick text in East-Asian myriad units, and how an axis prints a value.

``format_axis_myriad`` installs a formatter that decides at every draw from
the ticks in view: one unit for the axis and the fewest decimals that print
every tick exactly (``0.25억 … 1.75억``). Every other tick text is
matplotlib's, under the preset's ``axes.formatter.*`` and
``date.autoformatter.*``. Text that should read like the ticks (bar value
labels) asks :func:`tick_scale_of` and prints with :func:`number_text`.
"""

from __future__ import annotations

import matplotlib.ticker as ticker
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ..geometry import axis_of, projection
from ..vocab import Letters, Locale, Rectilinear, X, Y, parse_axes
from . import decide
from .formatters import AxisUnitFormatter, tick_scale_of, tick_values
from .model import DefaultUnit, NumberStyle, myriad_ladder, preset_ladder
from .text import number_text, value_label_decimals

__all__ = [
    "format_axis_myriad",
    "number_text",
    "prepare",
    "tick_scale_of",
    "value_label_decimals",
]


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
    style = NumberStyle.parse(
        myriad_ladder(locale), unit, decimals=decimals, currency=currency
    )
    for which in parse_axes(axis):  # one formatter each: it decides per axis
        axis_of(ax, which).set_major_formatter(AxisUnitFormatter(style))


def prepare(fig: Figure, locale: Locale) -> None:
    """Large numbers on axes nobody formatted, before the layout measures.

    A plain number axis whose ticks reach 1,000 prints thousands separators
    and, from one million, one unit for the axis: ``1M`` or, under a Korean
    preset, ``100만``. An axis with a formatter someone set, a log, date or
    category axis and ticks along x that read as years are left alone.
    """
    style = NumberStyle(preset_ladder(locale), DefaultUnit())
    for ax in fig.axes:
        if not isinstance(projection(ax), Rectilinear):
            continue
        for which in (X(), Y()):
            axis = axis_of(ax, which)
            untouched = axis.isDefault_majfmt and isinstance(
                axis.get_major_formatter(), ticker.ScalarFormatter
            )
            ticks = tick_values(axis, list(axis.get_majorticklocs()))
            if untouched and decide.reads_large(ticks, which):
                axis.set_major_formatter(AxisUnitFormatter(style))
