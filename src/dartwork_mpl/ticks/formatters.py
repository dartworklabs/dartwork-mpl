"""The matplotlib formatters and locators the tick plans install.

Each formatter decides when matplotlib formats its ticks (every draw), from
the ticks in view: :class:`AxisUnitFormatter` one unit and decimal count
per axis (``decide.axis_text``), :class:`YearTickFormatter` whole years
(dates are in ``dates``).
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Any

import matplotlib.ticker as ticker
from matplotlib.axis import Axis

from . import decide
from .measure import in_view, tick_values
from .model import (
    PLAIN,
    AffixedZero,
    AxisText,
    BareZero,
    ExactZero,
    NumberStyle,
    ScaleZero,
    TextFacts,
    TickScale,
    TickValues,
    Unit,
    YearDigits,
)
from .text import fewest_exact_decimals, number_text, per_tick_text

WHOLE_TOL = 1e-6


def shown_values(
    formatter: ticker.Formatter, values: Sequence[float]
) -> list[float]:
    """The values inside the formatter's axis view (all of them unattached)."""
    axis = formatter.axis
    if not isinstance(axis, Axis):
        return [float(v) for v in values]
    return in_view(axis, values)


# -- numbers ---------------------------------------------------------------------


class AxisUnitFormatter(ticker.Formatter):
    """One unit and one decimal count per axis, settled from the ticks in view.

    With ``style.per_tick`` each value is written alone with fixed decimals
    (the ``decimals=n`` paths and currency). Called without a draw, a value
    decides for itself.
    """

    def __init__(self, style: NumberStyle) -> None:
        """Keep the settings this formatter or locator was made with."""
        self.style = style
        self._text: AxisText | None = None

    def decide(self, ticks: TickValues) -> AxisText:
        """The unit and decimals for these ticks."""
        return decide.axis_text(TextFacts(ticks, self.style))

    def set_locs(self, locs: list[float]) -> None:
        """Record the ticks and settle this axis's unit and decimals."""
        super().set_locs(locs)
        if self.style.per_tick is not None or not len(locs):
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
        self._text = self.decide(ticks)

    def format_ticks(self, values: list[float]) -> list[str]:
        """Every tick under one axis-wide decision."""
        self.set_locs(values)
        return [self(v, i) for i, v in enumerate(values)]

    def _decision(self, value: float) -> tuple[Unit, int | None]:
        text = self._text
        if text is None:
            text = self.decide(TickValues.of([value]))
        unit = text.unit or decide.max_unit(
            TickValues((value,)), self.style.ladder
        )
        return unit, text.decimals

    def write(self, value: float, unit: Unit, decimals: int) -> str:
        """``value`` in ``unit`` with ``decimals`` places, as a tick."""
        return number_text(
            value / unit.factor,
            decimals,
            fixed=self.style.decimals is not None,
            prefix=self.style.currency,
            suffix=unit.label,
        )

    def __call__(self, x: float, pos: int | None = None) -> str:
        """One value under the last axis decision (or its own)."""
        value = float(x)
        if self.style.per_tick is not None:
            return per_tick_text(value, self.style)
        if not math.isfinite(value):
            return str(value)
        unit, decimals = self._decision(value)
        if decimals is None:
            decimals = fewest_exact_decimals([abs(value) / unit.factor])
        return self.write(value, unit, decimals)

    def scale_for(self, value: float) -> TickScale:
        """How a tick at ``value`` prints under the last decision."""
        style, rules = self.style, self.style.per_tick
        if rules is not None:
            if style.unit is None:
                return TickScale()
            zero: ScaleZero
            match rules.zero:
                case AffixedZero():
                    zero = AffixedZero()
                case BareZero() | ExactZero():
                    zero = BareZero()
            return TickScale(
                style.unit.factor, style.currency, style.unit.label, zero
            )
        unit, _ = self._decision(float(value))
        return TickScale(unit.factor, style.currency, unit.label)


class LabelUnitFormatter(AxisUnitFormatter):
    """Plain-number ticks, the axis unit written into the axis labels.

    ``templates`` maps each axis whose label this formatter writes (the
    installing one and those sharing its ticker) to its template with
    ``{unit}``. Each draw writes ``fill(template, unit)``; a label someone
    set since (an edit, a line break from the layout) is theirs and is left
    alone. On a log axis the ticks print whole values and the unit is plain.
    """

    def __init__(self, style: NumberStyle, templates: dict[Axis, str]) -> None:
        """Keep the settings this formatter or locator was made with."""
        super().__init__(style)
        self.templates = dict(templates)
        self.wrote: dict[Axis, str] = {}
        self.unit: Unit | None = None

    def decide(self, ticks: TickValues) -> AxisText:
        """The axis decision; a per-tick unit cannot go into one label."""
        text = super().decide(ticks)
        return AxisText(text.unit or PLAIN, text.decimals)

    def write(self, value: float, unit: Unit, decimals: int) -> str:
        """The number alone: the label names the unit."""
        return super().write(value, Unit(unit.factor, ""), decimals)

    def scale_for(self, value: float) -> TickScale:
        """The unit's factor with no suffix."""
        scale = super().scale_for(value)
        return TickScale(scale.factor, scale.prefix, "")

    def set_locs(self, locs: list[float]) -> None:
        """Settle the unit, then write it into every label still ours."""
        super().set_locs(locs)
        if self._text is None:
            return
        self.unit = self._text.unit or PLAIN
        for axis, template in list(self.templates.items()):
            if axis in self.wrote and axis.label.get_text() != self.wrote[axis]:
                del self.templates[axis]  # set by someone since: theirs
                continue
            text = fill(template, self.unit.label)
            axis.label.set_text(text)
            self.wrote[axis] = text


def fill(template: str, unit: str) -> str:
    """``template`` with ``unit`` for ``{unit}``; an empty ``()`` goes."""
    text = template.replace("{unit}", unit)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return re.sub(r"\s*\(\)", "", text)


def tick_scale_of(axis: Axis, value: float) -> TickScale:
    """How ``axis``'s major ticks print ``value``, as of their last draw.

    The library's number formatters report their unit and currency
    (``33G``; under ``dm.axis_unit`` no suffix: the label names it), a
    ``PercentFormatter`` its ``xmax / 100`` and symbol, any other formatter
    the plain scale.
    """
    formatter = axis.get_major_formatter()
    if isinstance(formatter, AxisUnitFormatter):
        return formatter.scale_for(value)
    if isinstance(formatter, ticker.PercentFormatter) and formatter.xmax:
        return TickScale(formatter.xmax / 100.0, "", formatter.symbol)
    return TickScale()


# -- years -----------------------------------------------------------------------


def _whole(value: float) -> bool:
    return math.isfinite(value) and abs(value - round(value)) <= WHOLE_TOL


class WholeYearLocator(ticker.MaxNLocator):
    """Ticks on whole years, every 1, 2, 5, 10, 20, 50 ... years.

    ``nbins`` set by someone (``ax.locator_params``) is a request the
    layout's thinning keeps; :meth:`thin` is the layout's own.
    """

    asked_nbins: bool = False
    nbins: int | str = "auto"
    """The tick-count ceiling (``"auto"``: from the axis length)."""

    def __init__(self) -> None:
        """Keep the settings this formatter or locator was made with."""
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            nbins="auto", steps=[1, 2, 5, 10], integer=True
        )
        self.asked_nbins = False

    def set_params(
        self, *, nbins: int | str | None = None, **kwargs: Any
    ) -> None:
        """Set MaxNLocator parameters; an ``nbins`` set here is a request."""
        if nbins is not None:
            kwargs["nbins"] = nbins
            self.nbins = nbins
            self.asked_nbins = True
        super().set_params(**kwargs)  # pyright: ignore[reportUnknownMemberType]

    def thin(self, nbins: int | str) -> None:
        """The layout's own ``nbins``, not a request."""
        self.nbins = nbins
        ticker.MaxNLocator.set_params(self, nbins=nbins)  # pyright: ignore[reportUnknownMemberType]


class YearTickFormatter(ticker.Formatter):
    """Whole years as two digits (``24``) or four (``2024``), plus ``suffix``.

    Two digits that would repeat in view (1965, 2065) print four. While a
    tick in view falls between years (a zoom under two years) every tick
    prints its value (``2019.2 ... 2019.7``), never a rounded year.
    """

    def __init__(self, digits: YearDigits, suffix: str = "") -> None:
        """Keep the settings this formatter or locator was made with."""
        self.digits: YearDigits = digits
        self.suffix = suffix
        self._four = digits.four(())
        self._decimals: int | None = None

    def set_locs(self, locs: list[float]) -> None:
        """Years or values, from the ticks in view."""
        super().set_locs(locs)
        shown = shown_values(self, locs)
        between = not all(_whole(v) for v in shown)
        self._decimals = fewest_exact_decimals(shown) if between else None
        years = [round(v) for v in shown if _whole(v)]
        self._four = self.digits.four(years)

    def format_ticks(self, values: list[float]) -> list[str]:
        """Every tick under one decision."""
        self.set_locs(values)
        return [self(v, i) for i, v in enumerate(values)]

    def __call__(self, x: float, pos: int | None = None) -> str:
        """One tick: its year, or its value between years."""
        if self._decimals is not None:
            return number_text(float(x), self._decimals).replace(",", "")
        if not _whole(float(x)):
            return ""
        year = round(x)
        body = f"{year}" if self._four else f"{year % 100:02d}"
        return f"{body}{self.suffix}"
