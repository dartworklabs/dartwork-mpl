"""Pure tick decisions: domain types in, one axis-wide decision out.

At draw time a myriad axis reads the ticks it shows and takes one unit from
its ladder and the fewest decimals that print every tick exactly
(:func:`axis_text`). Before the layout, an axis whose data are all whole
numbers ticks at whole numbers only (:func:`reads_whole`).
"""

from __future__ import annotations

from typing import assert_never

from ..vocab import Which, X, Y
from .model import (
    PLAIN,
    AxisData,
    AxisText,
    Cost,
    Decimals,
    DefaultUnit,
    EachAlone,
    FixedUnit,
    Ladder,
    MaxUnit,
    TextFacts,
    TickCount,
    TickValues,
    Unit,
    WholeUnit,
)
from .text import fewest_exact_decimals, number_text

TOLERANCE = 1e-9  # a 9,999.9999999 tick still reads 1만
SEPARATORS_FROM = 1_000.0
UNIT_FROM = 1_000_000.0
MOST_UNIT_DECIMALS = 2  # past this a default axis keeps plain numbers
YEAR_LIKE = (1_000.0, 2_999.0)  # ticks across all here read 2024, not 2,024
WHOLE = 1e-9  # a value this close to a whole number is one
FEWEST_WHOLE = 3  # whole numbers the data span; ticks a whole axis keeps
WIDE_LABEL = 4  # characters (2020, -100) that need room along x


def reads_whole(data: AxisData) -> bool:
    """Whether an axis's data are whole numbers: every value it draws sits
    on one (months ``1 … 12``, counts, ranks, years), so a tick between two
    (``2.5``, ``2019.5``) names none of them.

    Data spanning fewer than :data:`FEWEST_WHOLE` whole numbers (a ``0, 1``
    line) say too little to give up matplotlib's ticks between them.
    """
    values = data.values
    return (
        bool(values)
        and all(abs(v - round(v)) < WHOLE for v in values)
        and max(values) - min(values) >= FEWEST_WHOLE - 1 - WHOLE
    )


def fewest_whole_ticks(data: AxisData, which: Which) -> TickCount:
    """How few ticks a whole-number axis may keep.

    Without the half step a small panel jumps from 2.5 to 5 and may keep two
    ticks for twelve months (``5, 10``); three keep a scale (``2, 4 … 12``).
    Labels of :data:`WIDE_LABEL` characters or more (``2020``) side by side
    along x need the room the fewer ticks leave, so they keep matplotlib's
    two.
    """
    widest = max((len(f"{round(v)}") for v in data.values), default=0)
    match which:
        case X():
            return TickCount(2 if widest >= WIDE_LABEL else FEWEST_WHOLE)
        case Y():
            return TickCount(FEWEST_WHOLE)
        case _:
            assert_never(which)


def reads_large(ticks: TickValues, which: Which) -> bool:
    """Whether an axis nobody formatted takes the preset's numbers: its
    ticks reach 1,000, and are not years along x."""
    if not ticks.values or max(abs(v) for v in ticks.values) < SEPARATORS_FROM:
        return False
    low, high = YEAR_LIKE
    years = all(low <= v <= high for v in ticks.values)
    match which:
        case X():
            return not years
        case Y():
            return True
        case _:
            assert_never(which)


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
    style = facts.style
    match style.rule:
        case FixedUnit(unit=unit):
            return unit
        case WholeUnit():
            return min(style.ladder.rungs, key=lambda rung: _cost(facts, rung))
        case MaxUnit() | EachAlone():
            return max_unit(facts.ticks, style.ladder)
        case DefaultUnit():
            unit = max_unit(facts.ticks, style.ladder)
            top = max(abs(v) for v in facts.ticks.values)
            crowded = fewest_decimals(facts.ticks, unit) > MOST_UNIT_DECIMALS
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
