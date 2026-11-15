"""Tick text: numbers, units, years and dates on an axis.

``format_axis_myriad`` installs a formatter that
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

from collections.abc import Callable

import matplotlib.ticker as ticker
from matplotlib.axes import Axes
from matplotlib.axis import Axis

from ..geometry import axis_of
from ..vocab import Letters, parse_axes
from .apply import prepare, thin_dates
from .defaults import config
from .formatters import AxisUnitFormatter, tick_scale_of
from .model import ExactZero, Ladder, NumberStyle, PerTick, Unit, myriad_ladder
from .text import number_text, recommend_tick_decimals, value_label_decimals
from .twins import settled_twin_spines

__all__ = [
    "Unit",
    "config",
    "format_axis_myriad",
    "number_text",
    "prepare",
    "recommend_tick_decimals",
    "settled_twin_spines",
    "thin_dates",
    "tick_scale_of",
    "value_label_decimals",
]

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
