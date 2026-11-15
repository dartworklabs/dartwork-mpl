"""Tick text in East-Asian myriad units, and how an axis prints a value.

``format_axis_myriad`` installs a formatter that decides at every draw from
the ticks in view: one unit for the axis and the fewest decimals that print
every tick exactly (``0.25억 … 1.75억``). Every other tick text is
matplotlib's, under the preset's ``axes.formatter.*`` and
``date.autoformatter.*``. Text that should read like the ticks (bar value
labels) asks :func:`tick_scale_of` and prints with :func:`number_text`.
"""

from __future__ import annotations

from matplotlib.axes import Axes

from ..geometry import axis_of
from ..vocab import Letters, parse_axes
from .formatters import AxisUnitFormatter, tick_scale_of
from .model import NumberStyle, myriad_ladder
from .text import number_text, value_label_decimals

__all__ = [
    "format_axis_myriad",
    "number_text",
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
