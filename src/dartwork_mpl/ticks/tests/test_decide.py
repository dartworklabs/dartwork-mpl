"""The pure tick decisions, as tables: ticks in, unit and decimals out."""

from __future__ import annotations

import pytest

from dartwork_mpl.ticks.decide import axis_text, fewest_whole_ticks, reads_whole
from dartwork_mpl.ticks.model import (
    MYRIAD_LOCALES,
    AxisData,
    NumberStyle,
    TextFacts,
    TickValues,
)
from dartwork_mpl.ticks.text import (
    alone_text,
    fewest_exact_decimals,
    number_text,
    value_label_decimals,
)
from dartwork_mpl.vocab import AffixedZero, X, Y

M = "\N{MINUS SIGN}"
KO = MYRIAD_LOCALES["ko"]


def _text(values: list[float], style: NumberStyle) -> tuple[str, int | None]:
    text = axis_text(TextFacts(TickValues.of(values), style))
    return ("" if text.unit is None else text.unit.label), text.decimals


@pytest.mark.parametrize(
    ("values", "style", "expected"),
    [
        ([0, 2000, 4000, 8000], NumberStyle.parse(KO), ("", 0)),
        ([0, 4000, 8000, 12000], NumberStyle.parse(KO), ("만", 1)),
        ([0, 2.5e7, 1.75e8], NumberStyle.parse(KO), ("억", 2)),
        ([0, 2.5e7, 1.75e8], NumberStyle.parse(KO, "whole"), ("만", 0)),
        ([-1e8, 0, 1e8], NumberStyle.parse(KO, "만"), ("만", 0)),
        ([0, 1e8, 2e8], NumberStyle.parse(KO, "whole", decimals=2), ("억", 2)),
        ([], NumberStyle.parse(KO, "만", decimals=1), ("만", 1)),
    ],
)
def test_one_unit_and_decimal_count_per_axis(values, style, expected):
    assert _text(values, style) == expected


def test_a_style_names_only_rules_and_ladder_labels():
    with pytest.raises(ValueError, match="unit must be"):
        NumberStyle.parse(KO, "M")
    with pytest.raises(ValueError, match="non-negative"):
        NumberStyle.parse(KO, decimals=-1)


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
        ((-1.5, 1), {"suffix": "억"}, f"{M}1.5억"),
        ((-0.0001, 2), {}, "0"),
        ((0, 2), {"fixed": True}, "0.00"),
        ((0, 0), {"prefix": "$", "zero": AffixedZero()}, "$0"),
        ((-1500, 0), {"prefix": "$"}, f"{M}$1,500"),
    ],
)
def test_number_text(args, kwargs, expected):
    assert number_text(*args, **kwargs, unicode_minus=True) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1.5e8, "1.5억"), (7500, "7,500"), (2e4, "2만"), (0, "0")],
)
def test_fixed_decimals_write_each_value_alone(value, expected):
    assert alone_text(value, NumberStyle.parse(KO, decimals=1)) == expected


def test_value_label_decimals():
    assert value_label_decimals([21.4, 18.0, 21.5]) == 1
    assert value_label_decimals([120, 135]) == 0


@pytest.mark.parametrize(
    ("data", "whole"),
    [
        (range(1, 13), True),  # months
        (range(2019, 2024), True),  # years
        ((0, 3, 7), True),  # counts: a bar's two ends
        ((10.0, 20.0, 30.0), True),  # measured, and whole
        ((1, 2, 3.0000000000000004), True),  # float noise on a whole 3
        ((0, 1), False),  # a 0, 1 line: too few to say
        ((1, 2, 2.5), False),
        ((-0.5, 2.5), False),  # an image's edges around its pixels
        ((2019.25, 2019.75), False),
        ((), False),
    ],
)
def test_data_on_whole_numbers_read_whole(data, whole):
    assert reads_whole(AxisData.of(list(data))) is whole


@pytest.mark.parametrize(
    ("data", "which", "fewest"),
    [
        (range(1, 13), X(), 3),  # months: 2, 4 … 12, not 5, 10
        (range(0, 101, 10), X(), 3),
        (range(2015, 2025), X(), 2),  # years side by side need the room
        ((-100, 0, 100), X(), 2),
        (range(2015, 2025), Y(), 3),  # stacked up the side, any width
    ],
)
def test_a_whole_axis_keeps_three_ticks_unless_wide_along_x(
    data, which, fewest
):
    assert fewest_whole_ticks(AxisData.of(list(data)), which) == fewest
