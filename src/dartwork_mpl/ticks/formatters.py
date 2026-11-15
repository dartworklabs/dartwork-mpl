"""The matplotlib formatter ``format_axis_myriad`` installs, and how an axis
prints a value for text that should read like its ticks.

:class:`AxisUnitFormatter` decides when matplotlib formats its ticks (every
draw), from the ticks in view: one unit and decimal count per axis
(``decide.axis_text``).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import matplotlib.ticker as ticker
from matplotlib.axis import Axis

from ..vocab import TickScale
from . import decide
from .model import (
    AxisText,
    EachAlone,
    FixedUnit,
    MaxUnit,
    NumberStyle,
    TextFacts,
    TickValues,
    Unit,
    WholeUnit,
)
from .text import alone_text, fewest_exact_decimals, number_text


def tick_values(axis: Axis, values: Sequence[float]) -> TickValues:
    """The values inside the axis view, a limit's float noise included."""
    low, high = sorted(float(v) for v in axis.get_view_interval())
    slack = 1e-12 * (high - low)
    low -= 1e-9 * abs(low) + slack
    high += 1e-9 * abs(high) + slack
    return TickValues.of([float(v) for v in values if low <= float(v) <= high])


class AxisUnitFormatter(ticker.Formatter):
    """One unit and one decimal count per axis, settled from the ticks in view.

    Under :class:`EachAlone` each value is written alone. Called without a
    draw, a value decides for itself.
    """

    def __init__(self, style: NumberStyle) -> None:
        """Keep the settings this formatter was made with."""
        self.style = style
        self._text: AxisText | None = None

    def set_locs(self, locs: list[float]) -> None:
        """Record the ticks and settle this axis's unit and decimals."""
        super().set_locs(locs)
        if not len(locs):
            self._text = None
            return
        axis = self.axis
        values = [float(v) for v in locs]
        ticks = (
            tick_values(axis, values)
            if isinstance(axis, Axis)
            else TickValues.of(values)
        )
        if not ticks.values:  # none in view: every tick votes
            ticks = TickValues.of(values)
        self._text = decide.axis_text(TextFacts(ticks, self.style))

    def format_ticks(self, values: list[float]) -> list[str]:
        """Every tick under one axis-wide decision."""
        self.set_locs(values)
        return [self(v, i) for i, v in enumerate(values)]

    def _decision(self, value: float) -> tuple[Unit, int | None]:
        text = self._text or decide.axis_text(
            TextFacts(TickValues.of([value]), self.style)
        )
        unit = text.unit or decide.max_unit(
            TickValues((value,)), self.style.ladder
        )
        return unit, text.decimals

    def __call__(self, x: float, pos: int | None = None) -> str:
        """One value under the last axis decision (or its own)."""
        value, style = float(x), self.style
        match style.rule:
            case EachAlone():
                return alone_text(value, style)
            case MaxUnit() | WholeUnit() | FixedUnit():
                pass
        if not math.isfinite(value):
            return str(value)
        unit, decimals = self._decision(value)
        if decimals is None:
            decimals = fewest_exact_decimals([abs(value) / unit.factor])
        return number_text(
            value / unit.factor,
            decimals,
            fixed=style.decimals is not None,
            prefix=style.currency,
            suffix=unit.label,
        )

    def scale_for(self, value: float) -> TickScale:
        """How a tick at ``value`` prints under the last decision."""
        match self.style.rule:
            case EachAlone():
                return TickScale()
            case MaxUnit() | WholeUnit() | FixedUnit():
                unit, _ = self._decision(float(value))
                return TickScale(unit.factor, self.style.currency, unit.label)


def tick_scale_of(axis: Axis, value: float) -> TickScale:
    """How ``axis``'s major ticks print ``value``, as of their last draw.

    A myriad formatter reports its unit and currency (``1.2억``), a
    ``PercentFormatter`` its ``xmax / 100`` and symbol, any other formatter
    the plain scale.
    """
    formatter = axis.get_major_formatter()
    if isinstance(formatter, AxisUnitFormatter):
        return formatter.scale_for(value)
    if isinstance(formatter, ticker.PercentFormatter) and formatter.xmax:
        return TickScale(formatter.xmax / 100.0, "", formatter.symbol)
    return TickScale()
