"""The pure pieces the rules stand on: value labels and the report."""

from __future__ import annotations

from dataclasses import replace

import pytest

from dartwork_mpl.check.column_gap import column_gap
from dartwork_mpl.check.decide import reads_as_years
from dartwork_mpl.check.findings import Finding, Findings
from dartwork_mpl.check.model import (
    Beside,
    Box,
    Facts,
    Gap,
    Heading,
    Placed,
    Step,
    Text,
    TickValues,
    ascii_minus_value,
    printed_value,
)
from dartwork_mpl.check.roles import FreeText
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


def beside_column(x: float, reach: float, rows: int = 5) -> tuple[Beside, ...]:
    """Rows of 40 px type ending on one right edge at ``x``, the first of
    them ``reach`` px from what they sit beside and each next 10 px more."""
    step = 10.0 if reach > 0 else -10.0
    return tuple(
        Beside(
            Text(
                object(),
                f"+{i}",
                FreeText(),
                0,
                Box(x - 80.0, 100.0 + 60 * i, x, 140.0 + 60 * i),
                em=40.0,
            ),
            reach + step * i,
            None,
            Placed(1.2, 500.0),
        )
        for i in range(rows)
    )


def gaps(
    *columns: tuple[Beside, ...], headings: tuple[Heading, ...] = ()
) -> Findings:
    rows = tuple(row for column in columns for row in column)
    facts = Facts(
        canvas=Box(0, 0, 1000, 600),
        px_per_pt=300 / 72,
        beside=rows,
        headings=headings,
    )
    return column_gap(facts, Findings())


@pytest.mark.parametrize(
    ("reach", "rows", "moves"),
    [
        (-40.0, 5, None),  # one em from the plot
        (-60.0, 5, None),  # 1.5 em: still beside it
        (
            -70.0,
            5,
            "move it 7 pt to the left (the x they were given: 1.2 to 1.14)",
        ),
        (-160.0, 5, "move it 29 pt to the left"),  # the nearest row counts
        (160.0, 5, "move it 29 pt to the right"),
        (-160.0, 3, None),  # three labels are not a column
    ],
)
def test_column_gap_by_distance(reach: float, rows: int, moves: str | None):
    found = gaps(beside_column(700.0, reach, rows))
    assert found.rules == (("TEXT_COLUMN_GAP",) if moves else ())
    assert moves is None or moves in found.items[0].fix


@pytest.mark.parametrize(
    ("off", "hint"),
    [
        (10.0, None),  # 0.05 of the cells' spacing: the next cell
        (-70.0, "next cell of the rows"),  # 0.35 off: neither close nor in step
    ],
)
def test_column_in_step_with_a_grid_is_not_adrift(off: float, hint: str | None):
    """A totals column a cell's spacing on from the numbers in the cells."""
    rows = tuple(
        replace(row, step=Step(off, 200.0))
        for row in beside_column(700.0, -160.0)
    )
    found = gaps(rows)
    assert found.rules == (("TEXT_COLUMN_GAP",) if hint else ())
    assert hint is None or hint in found.items[0].fix


def test_column_gap_follows_the_column_it_sits_beside():
    first = beside_column(700.0, -120.0)
    second = tuple(
        replace(row, neighbour=near.text)
        for row, near in zip(beside_column(900.0, -120.0), first, strict=True)
    )
    one, two = gaps(first, second)
    assert "move it 19 pt to the left" in one.fix
    assert "move it 34 pt to the left" in two.fix  # a gutter is wider


def test_a_heading_against_the_next_heading_holds_its_column_off():
    first = beside_column(400.0, -40.0)
    second = tuple(
        replace(row, neighbour=near.text)
        for row, near in zip(beside_column(700.0, -220.0), first, strict=True)
    )

    def head(x0: float, x1: float) -> Text:
        return Text(object(), "Share", FreeText(), 0, Box(x0, 40, x1, 80), 40.0)

    ours, theirs = head(620.0, 700.0), head(320.0, 600.0)
    held = (Heading(theirs, None, None), Heading(ours, Gap(20.0, theirs), None))
    assert gaps(first, second, headings=held).rules == ()
    loose = (Heading(ours, Gap(20.0, head(0.0, 600.0)), None),)
    assert len(gaps(first, second, headings=loose)) == 1


@pytest.mark.parametrize(
    ("string", "words"),
    [("■", False), ("▲ 2", True), ("+", False), ("n/a", True)],
)
def test_a_text_of_shapes_alone_has_no_words(string: str, words: bool):
    box = Box(0.0, 0.0, 10.0, 10.0)
    assert Text(object(), string, FreeText(), 0, box, em=10.0).words is words
