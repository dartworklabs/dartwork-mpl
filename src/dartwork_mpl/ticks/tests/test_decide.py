"""The pure tick decisions, as tables: ticks in, unit and decimals out."""

from __future__ import annotations

import pytest

from dartwork_mpl.ticks.decide import axis_plan, axis_text, ladder
from dartwork_mpl.ticks.model import (
    FINANCE,
    MYRIAD,
    SI,
    Asked,
    AxisFacts,
    ByFigure,
    DateAxis,
    DefaultUnit,
    ExactZero,
    Leave,
    NumberAxis,
    Numbers,
    NumberStyle,
    OtherAxis,
    PeriodDates,
    PerTick,
    TextFacts,
    TickValues,
)
from dartwork_mpl.ticks.text import (
    fewest_exact_decimals,
    number_text,
    per_tick_text,
    recommend_tick_decimals,
    value_label_decimals,
)

M = "\N{MINUS SIGN}"


def _text(values: list[float], style: NumberStyle) -> tuple[str, int | None]:
    text = axis_text(TextFacts(TickValues.of(values), style))
    return ("" if text.unit is None else text.unit.label), text.decimals


@pytest.mark.parametrize(
    ("values", "style", "expected"),
    [
        ([0, 200, 400, 800], NumberStyle.parse(SI), ("", 0)),
        ([0, 400, 800, 1200], NumberStyle.parse(SI), ("k", 1)),
        ([-1e6, -5e5, 0, 5e5, 1e6], NumberStyle.parse(SI), ("M", 1)),
        ([0, 1e6, 2e6], NumberStyle.parse(SI), ("M", 0)),
        ([0, 250, 500, 1250], NumberStyle.parse(SI), ("k", 2)),
        ([0, 400, 800, 1200], NumberStyle.parse(SI, "whole"), ("", 0)),
        ([-1e6, 0, 1e6], NumberStyle.parse(SI, "k"), ("k", 0)),
        ([0, 1e6, 2e6], NumberStyle.parse(SI, "max", decimals=2), ("M", 2)),
        ([0, 2.5e7, 1.75e8], NumberStyle.parse(MYRIAD), ("억", 2)),
        ([0, 2.5e7, 1.75e8], NumberStyle.parse(MYRIAD, "whole"), ("만", 0)),
        ([0, 1.5e9, 3e9], NumberStyle.parse(FINANCE), ("B", 1)),
        # the library's numbers: plain under a million, a unit from it ...
        ([0, 2.5e5, 7.5e5], NumberStyle(SI, DefaultUnit()), ("", 0)),
        ([0, 1e6, 4e6], NumberStyle(SI, DefaultUnit()), ("M", 0)),
        # ... unless that needs more than two decimals
        ([123456, 123457, 123458], NumberStyle(SI, DefaultUnit()), ("", 0)),
        ([1_000_000, 1_000_500], NumberStyle(SI, DefaultUnit()), ("", 0)),
        ([], NumberStyle.parse(SI, "k", decimals=1), ("k", 1)),
    ],
)
def test_one_unit_and_decimal_count_per_axis(values, style, expected):
    assert _text(values, style) == expected


def test_a_style_names_only_rules_and_ladder_labels():
    with pytest.raises(ValueError, match="unit must be"):
        NumberStyle.parse(SI, "억")
    with pytest.raises(ValueError, match="non-negative"):
        NumberStyle.parse(SI, decimals=-1)


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([0, 1, 2], 0),
        ([0.5, 1.0, 1.5], 1),
        ([17.5, 20, 22.5], 1),
        ([0.25, 0.5], 2),
        ([5.6e-17, 0.2, 0.4], 1),  # float noise on zero
        ([1 / 3, 2 / 3], 1),  # no exact count: the step rule, kept apart
        ([1e-9], 9),
    ],
)
def test_fewest_exact_decimals(values, expected):
    assert fewest_exact_decimals(values) == expected


@pytest.mark.parametrize(
    ("args", "kwargs", "expected"),
    [
        ((1750, 0), {}, "1,750"),
        ((-1.5, 1), {"suffix": "M"}, f"{M}1.5M"),
        ((-0.0001, 2), {}, "0"),
        ((0, 2), {"fixed": True}, "0.00"),
        ((0, 0), {"prefix": "$", "zero": "affixed"}, "$0"),
        ((-1500, 0), {"prefix": "$"}, f"{M}$1,500"),
    ],
)
def test_number_text(args, kwargs, expected):
    assert number_text(*args, **kwargs, unicode_minus=True) == expected


@pytest.mark.parametrize(
    ("value", "style", "expected"),
    [
        (1500, NumberStyle.parse(SI, decimals=1, per_tick=PerTick(separators=False)), "1.5k"),
        (800, NumberStyle.parse(SI, decimals=1, per_tick=PerTick(separators=False)), "800.0"),
        (1.5e8, NumberStyle.parse(MYRIAD, decimals=1, per_tick=PerTick(zero=ExactZero(), compact=True)), "1.5억"),
        (7500, NumberStyle.parse(MYRIAD, decimals=1, per_tick=PerTick(zero=ExactZero(), compact=True)), "7,500"),
    ],
)  # fmt: skip
def test_fixed_decimals_write_each_value_alone(value, style, expected):
    assert per_tick_text(value, style) == expected


def test_value_labels_and_the_validator_step_rule():
    assert value_label_decimals([21.4, 18.0, 21.5]) == 1
    assert value_label_decimals([120, 135]) == 0
    assert recommend_tick_decimals([0, 0.25, 0.5]) == 1
    assert recommend_tick_decimals([3]) == 0


NUMBERS = NumberAxis()


def _axis(kind=NUMBERS, values=(0, 1), **kw) -> AxisFacts:
    return AxisFacts(
        x=kw.pop("x", False), kind=kind, ticks=TickValues.of(values), **kw
    )


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (_axis(values=(0, 500, 1000, 1500)), Numbers()),
        (_axis(values=(0, 250, 750)), Leave()),
        (_axis(values=(0, 500, 1000), own_formatter=False), Leave()),
        (_axis(values=(1950, 2000, 2050), x=True), Leave()),  # looks like years
        (_axis(values=(1950, 2000, 2050)), Numbers()),
        (_axis(DateAxis()), PeriodDates(2)),
        (_axis(OtherAxis(), values=(0, 5000)), Leave()),
    ],
)
def test_default_format_of_an_axis_nobody_formatted(facts, expected):
    assert axis_plan(facts, 2) == expected


def test_the_ladder_asked_by_name():
    assert ladder(Asked(MYRIAD)) is MYRIAD
    assert ladder(Asked(SI)) is SI
    assert ladder(ByFigure(korean=False)) is SI
