"""Pure tick decisions for the ordinary axis: domain types in, plan out.

At draw time a number axis reads the ticks it shows and takes one unit from
its ladder and the fewest decimals that print every tick exactly
(:func:`axis_text`). Before the layout measures, an axis nobody formatted
gets the library's format (:func:`axes_plan`): a date axis on matplotlib's
concise formatter reads whole two-digit dates (``24.01``), a number axis
reaching 1,000 gets thousands separators and, from one million, the largest
tick's unit (``0.5M``). Special cases (Korean units, year axes, quarters,
texts someone fixed, twin spines, log axes, crowded dates) are in
``edges.py``.
"""

from __future__ import annotations

from typing import assert_never

from .model import (
    PLAIN,
    SI,
    Asked,
    AxesFacts,
    AxesPlan,
    AxisFacts,
    AxisPlan,
    AxisText,
    ByFigure,
    Cost,
    Crowding,
    DateAxis,
    Decimals,
    DefaultUnit,
    FixedUnit,
    Ladder,
    Language,
    Leave,
    MaxUnit,
    NumberAxis,
    Numbers,
    OtherAxis,
    PeriodDates,
    TextFacts,
    Thinning,
    TickValues,
    Unit,
    WholeUnit,
    YearDigits,
)
from .text import fewest_exact_decimals, number_text

TOLERANCE = 1e-9  # a 999.9999999 tick still reads 1k
SEPARATORS_FROM = 1_000.0
UNIT_FROM = 1_000_000.0
MOST_UNIT_DECIMALS = 2  # past this a default axis keeps plain numbers
YEAR_LIKE = (1_000.0, 2_999.0)  # x ticks all here read 2024, not 2,024


def ladder(language: Language) -> Ladder:
    """The ladder asked by name; one following the figure starts from SI."""
    match language:
        case Asked(ladder=asked):
            return asked
        case ByFigure():
            return SI
        case _:
            assert_never(language)


def fewest_decimals(ticks: TickValues, unit: Unit) -> Decimals:
    """Fewest decimals that print every tick in ``unit`` exactly and apart."""
    return Decimals(
        fewest_exact_decimals([v / unit.factor for v in ticks.values])
    )


def max_unit(ticks: TickValues, scale: Ladder) -> Unit:
    """The largest rung at or below the largest ``|tick|``."""
    top = max(abs(v) for v in ticks.values)
    under = [r for r in scale.rungs if top >= r.factor * (1 - TOLERANCE)]
    return under[-1] if under else scale.rungs[0]


def _cost(facts: TextFacts, unit: Unit) -> Cost:
    decimals = fewest_decimals(facts.ticks, unit)
    prefix, fixed = facts.style.currency, facts.style.decimals is not None
    longest = max(
        len(
            number_text(
                v / unit.factor,
                decimals,
                fixed=fixed,
                prefix=prefix,
                suffix=unit.label,
                unicode_minus=True,
            )
        )
        for v in facts.ticks.values
    )
    return Cost(decimals, longest, unit.factor)


def axis_unit(facts: TextFacts) -> Unit:
    """The one unit the axis prints in, by the style's rule."""
    style, ticks = facts.style, facts.ticks
    match style.rule:
        case FixedUnit(unit=unit):
            return unit
        case WholeUnit():
            return min(style.ladder.rungs, key=lambda rung: _cost(facts, rung))
        case MaxUnit():
            return max_unit(ticks, style.ladder)
        case DefaultUnit():
            unit = max_unit(ticks, style.ladder)
            top = max(abs(v) for v in ticks.values)
            crowded = fewest_decimals(ticks, unit) > MOST_UNIT_DECIMALS
            if top < UNIT_FROM * (1 - TOLERANCE) or crowded:
                return PLAIN
            return unit
        case _:
            assert_never(style.rule)


def axis_text(facts: TextFacts) -> AxisText:
    """One unit and one decimal count for every tick the axis shows."""
    style = facts.style
    if not facts.ticks.values:
        return AxisText(style.unit, style.decimals)
    unit = axis_unit(facts)
    decimals = style.decimals
    if decimals is None:
        decimals = fewest_decimals(facts.ticks, unit)
    return AxisText(unit, decimals)


def reaches_thousands(facts: AxisFacts) -> bool:
    """Whether the ticks reach 1,000, except x ticks that all look like years."""
    values = facts.ticks.values
    if not values or max(abs(v) for v in values) < SEPARATORS_FROM:
        return False
    low, high = YEAR_LIKE
    return not (facts.x and all(low <= v <= high for v in values))


def axis_plan(facts: AxisFacts, digits: YearDigits) -> AxisPlan:
    """The library's format for one axis nobody formatted."""
    if not facts.own_formatter:
        return Leave()
    match facts.kind:
        case DateAxis():
            return PeriodDates(digits)
        case NumberAxis():
            return Numbers() if reaches_thousands(facts) else Leave()
        case OtherAxis():
            return Leave()
        case _:
            assert_never(facts.kind)


def axes_plan(facts: AxesFacts) -> AxesPlan:
    """The library's format for both axes of one Axes."""
    return AxesPlan(
        axis_plan(facts.x, facts.digits), axis_plan(facts.y, facts.digits)
    )


def thinning(facts: Crowding) -> Thinning:
    """Date ticks keep their count; crowded ones are an edge case."""
    return Thinning()
