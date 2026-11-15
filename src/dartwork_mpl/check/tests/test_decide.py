"""The pure pieces the rules stand on: label parsing, boxes, the report."""

from __future__ import annotations

import pytest

from dartwork_mpl.check.model import (
    Box,
    Finding,
    Findings,
    Number,
    Severity,
    step_decimals,
)


@pytest.mark.parametrize(
    ("label", "parts"),
    [
        ("1,200 MWh", ("", "1200", "MWh")),
        ("45.0%", ("", "45.0", "%")),
        ("$3.5", ("$", "3.5", "")),
        ("\u22122.0", ("", "-2.0", "")),
        ("260만", ("", "260", "만")),
        ("Total: 12", ("Total: ", "12", "")),
        ("Q1", None),
        ("v2.0", None),
        ("24 months of data collected", None),
        ("1 to 2", None),
        ("$\\alpha$", None),
        ("", None),
    ],
)
def test_number_parse(label: str, parts: tuple[str, str, str] | None):
    n = Number.parse(label)
    assert (None if n is None else (n.prefix, n.digits, n.suffix)) == parts


@pytest.mark.parametrize(
    ("digits", "decimals", "whole"),
    [
        ("2.0", 1, True),
        ("2.5", 1, False),
        ("45.00000000000001", 14, True),
        ("0.00000000000001", 14, False),
        ("5.6e-17", 1, True),
    ],
)
def test_number_decimals_and_whole(digits: str, decimals: int, whole: bool):
    n = Number("", digits, "")
    assert (n.decimals, n.whole) == (decimals, whole)


@pytest.mark.parametrize(
    ("values", "need"),
    [((0.0, 0.5, 1.0), 1), ((0, 10, 20), 0), ((0.01, 0.02), 2), ((1.0,), 0)],
)
def test_step_decimals(values: tuple[float, ...], need: int):
    assert step_decimals(values) == need


def test_box_cover_gap_and_margins():
    a, b = Box(0, 0, 10, 10), Box(5, 5, 25, 25)
    assert a.cover(b) == pytest.approx(0.25)
    assert a.gap(Box(13, 0, 20, 10)) == 3
    assert Box(-2, 1, 5, 5).margins(a)["left"] == -2


def test_report_lists_findings_fixes_and_what_did_not_run():
    clean = Findings()
    assert not clean and clean.report() == "dm.check: no defects found."
    f = Finding("OVERLAP", Severity.WARNING, "A overlaps B", "move one")
    found = Findings((f,), skipped=("TICK_*",))
    assert found.report().splitlines() == [
        "dm.check: 1 finding",
        "WARNING OVERLAP: A overlaps B",
        "  fix: move one",
        "NOT RUN: TICK_* (could not measure; the figure is not proven clean)",
    ]
    assert found.of("OVERLAP") == (f,) and found.rules == ("OVERLAP",)
