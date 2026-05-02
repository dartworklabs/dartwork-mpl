# tests/robustness/scenarios.py
"""Scenario registry for the robustness suite.

Adding a scenario:
    1. Write a builder function returning a fully-configured Figure.
    2. Append a RobustnessScenario instance to SCENARIOS.

Builder functions own their figure size and styling. The harness in
test_robustness_suite.py never modifies the figure between build() and
the first validate_figure call.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import matplotlib.pyplot as plt  # noqa: F401  used in Task 4+ builders
import pytest  # noqa: F401  used in xfail markers added in Task 4+
from matplotlib.figure import Figure

import dartwork_mpl as dm


@dataclass(frozen=True)
class RobustnessScenario:
    """One scenario in the robustness suite.

    Parameters
    ----------
    name
        Snake-case identifier used as the pytest test id.
    build
        Callable returning a fully-built Figure.
    expect_warnings
        Substrings of validate_figure check_ids that **must** appear
        before auto_layout runs (i.e. validate is supposed to catch
        the issue this scenario plants).
    forbid_warnings
        Substrings that **must not** appear after auto_layout. Empty
        by default (i.e. layout should clean up cleanly).
    pixel_checks
        Names of callables in pixel_assertions to invoke against the
        post-layout figure (e.g. ("assert_minimum_white_border",)).
    auto_layout_max_iter
        Iteration cap for auto_layout. Most scenarios accept the
        default (5); pathological annotations may need more.
    """

    name: str
    build: Callable[[], Figure]
    expect_warnings: tuple[str, ...] = ()
    forbid_warnings: tuple[str, ...] = ("OVERFLOW",)
    pixel_checks: tuple[str, ...] = ("assert_minimum_white_border",)
    auto_layout_max_iter: int = 5


# ───────────────────────────────────────────────────────
# A. Tick label stress
# ───────────────────────────────────────────────────────


def _build_long_xtick_labels_no_rotation() -> Figure:
    """8 categorical bars, each with a 25-character label, no rotation."""
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = [f"category_label_no_{i:02d}" for i in range(8)]
    ax.bar(labels, [3, 5, 7, 4, 6, 2, 8, 5])
    ax.set_ylabel("Value")
    return fig


SCENARIOS: list[RobustnessScenario] = [
    RobustnessScenario(
        name="long_xtick_labels_no_rotation",
        build=_build_long_xtick_labels_no_rotation,
        expect_warnings=(),  # auto_layout should handle it without warning
        forbid_warnings=("OVERFLOW",),
        pixel_checks=("assert_minimum_white_border",),
    ),
]
