"""The pure pieces the rules stand on: value labels and the report."""

from __future__ import annotations

import pytest

from dartwork_mpl.check.decide import reads_as_years
from dartwork_mpl.check.findings import Finding, Findings
from dartwork_mpl.check.model import (
    TickValues,
    ascii_minus_value,
    printed_value,
)
from dartwork_mpl.vocab import Which, X, Y


@pytest.mark.parametrize(
    ("label", "value"),
    [
        ("1,200 MWh", True),
        ("45.0%", True),
        ("$3.5", True),
        ("\u22122.0", True),
        ("260만", True),
        ("Total: 12", True),
        ("Q1", False),
        ("v2.0", False),
        ("24 months of data collected", False),
        ("1 to 2", False),
        ("$\\alpha$", False),
        ("", False),
    ],
)
def test_a_value_label_prints_one_number(label: str, value: bool):
    assert (printed_value(label) is not None) is value


def test_report_lists_findings_fixes_and_what_did_not_run():
    clean = Findings()
    assert not clean and clean.report() == "dm.check: nothing stands out."
    f = Finding("OVERLAP", "A overlaps B", "move one")
    found = Findings((f,), skipped=("TICK_OVERLAP",))
    assert found.report().splitlines() == [
        "dm.check: 1 place to look at",
        "OVERLAP: A overlaps B",
        "  try: move one",
        "NOT RUN: TICK_OVERLAP (could not measure this figure, so look at "
        "it yourself)",
    ]
    assert found.rules == ("OVERLAP",)


@pytest.mark.parametrize(
    ("values", "linear", "axis", "years"),
    [
        ((2019, 2020, 2021), True, X(), True),
        ((1990, 2000, 2010, 2020, 2030), True, X(), True),
        ((2019, 2019.5, 2020), True, X(), False),
        ((1000, 1500, 2000), True, X(), False),
        ((2019, 2020, 2021), False, X(), False),
        ((2019, 2020, 2021), True, Y(), False),
        ((), True, X(), False),
    ],
)
def test_whole_x_ticks_within_the_years_read_as_years(
    values: tuple[float, ...], linear: bool, axis: Which, years: bool
):
    ticks = TickValues(tuple(float(v) for v in values), linear)
    assert reads_as_years(ticks, axis) is years


@pytest.mark.parametrize(
    ("label", "uses_hyphen"),
    [
        ("-12.4%", True),
        ("-389.5", True),
        (" -1,200 GWh", True),
        ("\u221212.4%", False),
        ("2014-2024", False),
        ("2024-01-01", False),
        ("year-over-year", False),
        ("$10^{-4}$", False),
    ],
)
def test_numeric_hyphen_minus(label: str, uses_hyphen: bool):
    """Only a hyphen used as a numeric sign is a candidate."""
    assert ascii_minus_value(label) is uses_hyphen
