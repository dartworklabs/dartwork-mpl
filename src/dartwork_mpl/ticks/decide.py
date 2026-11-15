"""Pure tick decisions: domain types in, one axis-wide decision out.

At draw time a myriad axis reads the ticks it shows and takes one unit from
its ladder and the fewest decimals that print every tick exactly
(:func:`axis_text`).
"""

from __future__ import annotations

from typing import assert_never

from .model import (
    AxisText,
    Cost,
    Decimals,
    EachAlone,
    FixedUnit,
    Ladder,
    MaxUnit,
    TextFacts,
    TickValues,
    Unit,
    WholeUnit,
)
from .text import fewest_exact_decimals, number_text

TOLERANCE = 1e-9  # a 9,999.9999999 tick still reads 1만


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
