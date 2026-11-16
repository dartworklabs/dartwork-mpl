"""The pure pieces the rules stand on: value labels and the report."""

from __future__ import annotations

import pytest

from dartwork_mpl.check.findings import Finding, Findings
from dartwork_mpl.check.model import printed_value


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
