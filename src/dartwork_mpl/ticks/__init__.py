"""Tick text in East-Asian myriad units, and how an axis prints a value.

``format_axis_myriad`` installs a formatter that decides at every draw from
the ticks in view: one unit for the axis and the fewest decimals that print
every tick exactly (``0.25억 … 1.75억``). Every other tick text is
matplotlib's, under the preset's ``axes.formatter.*`` and
``date.autoformatter.*``. Text that should read like the ticks (bar value
labels) asks :func:`tick_scale_of` and prints with :func:`number_text`.
Before the layout, :func:`prepare` ticks an axis of whole numbers at whole
numbers and writes large numbers in the preset's units.
"""

from __future__ import annotations

import logging

from matplotlib.axes import Axes
from matplotlib.category import StrCategoryFormatter
from matplotlib.figure import Figure

from ..geometry import axis_of, projection
from ..hidden import axes_name
from ..vocab import Letters, Locale, Rectilinear, Which, X, Y, parse_axes
from . import decide
from .apply import tick_default, tick_whole
from .formatters import AxisUnitFormatter, tick_scale_of, tick_values, untouched
from .measure import data_along, default_locator, placed_whole
from .model import DefaultUnit, NumberStyle, myriad_ladder, preset_ladder
from .text import number_text, value_label_decimals

LOG = logging.getLogger("dartwork_mpl.ticks")

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
    trailing zeros dropped (``1.5억``, ``7,500``). An axis that shows
    category names (the y axis of ``ax.barh``) is left as it is.
    """
    style = NumberStyle.parse(
        myriad_ladder(locale), unit, decimals=decimals, currency=currency
    )
    for which in parse_axes(axis):  # one formatter each: it decides per axis
        target = axis_of(ax, which)
        if isinstance(target.get_major_formatter(), StrCategoryFormatter):
            LOG.info(
                "left the %s axis of %s as it is: it shows category names, "
                "not numbers, and units would replace the names; pass the "
                "value axis (axis=...) to dm.format_axis_myriad",
                which.letter,
                axes_name(ax),
            )
            continue
        target.set_major_formatter(AxisUnitFormatter(style))


def _whole_ticks(ax: Axes, which: Which) -> None:
    """Whole-number ticks on an axis whose data are whole and whose
    locator is matplotlib's, or the one this slice placed while they were."""
    axis = axis_of(ax, which)
    ours = placed_whole(axis)
    if not (ours or default_locator(axis)):
        return
    data = data_along(ax, which)
    whole = decide.reads_whole(data)
    if whole and not ours:
        before = list(axis.get_majorticklocs())
        tick_whole(axis, decide.fewest_whole_ticks(data, which))
        if list(axis.get_majorticklocs()) == before:
            return  # matplotlib's ticks were whole already: nothing to say
        LOG.info(
            "put the %s ticks of %s on whole numbers only: everything it "
            "draws sits on whole numbers (months, counts, ranks, years), and "
            "a tick between two (2.5) names none of them; set your own "
            "locator (ax.%saxis.set_major_locator) to keep matplotlib's",
            which.letter,
            axes_name(ax),
            which.letter,
        )
    elif ours and not whole:
        tick_default(axis)


def prepare(fig: Figure, locale: Locale) -> None:
    """Whole-number ticks and large numbers on axes nobody set, before the
    layout measures.

    An axis whose data all sit at whole numbers (months, counts, ranks,
    years) ticks at whole numbers only (``2, 4, 6``, not ``2.5, 5.0, 7.5``)
    unless someone placed its ticks, set its formatter or its scale; when
    its data stop being whole, matplotlib's own locator comes back.

    A plain number axis whose ticks reach 1,000 prints thousands separators
    and, from one million, one unit for the axis: ``1M`` or, under a Korean
    preset, ``100만``. An axis with a formatter someone set, a log, date or
    category axis, ticks along x that read as years and an axis whose
    formatter was told how to write (``ax.ticklabel_format``) are left
    alone.
    """
    style = NumberStyle(preset_ladder(locale), DefaultUnit())
    for ax in fig.axes:
        if not isinstance(projection(ax), Rectilinear):
            continue
        for which in (X(), Y()):
            axis = axis_of(ax, which)
            if untouched(axis):
                _whole_ticks(ax, which)
            ticks = tick_values(axis, list(axis.get_majorticklocs()))
            if decide.reads_large(ticks, which) and untouched(axis):
                axis.set_major_formatter(AxisUnitFormatter(style))
                LOG.info(
                    "wrote the %s tick numbers of %s with thousands "
                    "separators and, from a million, one unit for the axis: "
                    "they reach 1,000 and nobody set a "
                    "formatter; set your own (ax.%saxis.set_major_formatter) "
                    "to keep matplotlib's",
                    which.letter,
                    axes_name(ax),
                    which.letter,
                )
