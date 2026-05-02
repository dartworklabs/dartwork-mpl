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
import pytest
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


def _build_long_xtick_labels_45_rotation() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = [f"category_label_45_{i:02d}" for i in range(8)]
    ax.bar(labels, [3, 5, 7, 4, 6, 2, 8, 5])
    ax.set_ylabel("Value")
    dm.rotate_tick_labels(ax, axis="x", rotation=45)
    return fig


def _build_long_xtick_labels_90_rotation() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = [f"category_label_90_{i:02d}" for i in range(8)]
    ax.bar(labels, [3, 5, 7, 4, 6, 2, 8, 5])
    ax.set_ylabel("Value")
    dm.rotate_tick_labels(ax, axis="x", rotation=90)
    return fig


def _build_long_ytick_labels_horizontal_bar() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="wide")
    labels = [f"horizontal_bar_label_{i:02d}" for i in range(6)]
    ax.barh(labels, [3, 5, 7, 4, 6, 2])
    ax.set_xlabel("Value")
    return fig


def _build_dense_xticks_50_categories() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = [f"c{i:02d}" for i in range(50)]
    ax.bar(labels, list(range(50)))
    ax.set_ylabel("Value")
    return fig


def _build_unicode_korean_xticks() -> Figure:
    dm.style.use("report-kr")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = ["삼성전자", "한국전력", "포스코", "현대차", "엘지화학"]
    ax.bar(labels, [3, 5, 7, 4, 6])
    ax.set_ylabel("매출 (억원)")
    return fig


def _build_mixed_kr_en_xticks() -> Figure:
    dm.style.use("report-kr")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    labels = ["Samsung", "한국전력", "Apple", "현대차", "NVIDIA"]
    ax.bar(labels, [3, 5, 7, 4, 6])
    ax.set_ylabel("Value")
    return fig


def _build_scientific_notation_yticks() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([0, 1, 2], [1e-9, 1e0, 1e9])
    ax.set_yscale("log")
    ax.set_ylabel("Value")
    return fig


SCENARIOS: list[RobustnessScenario] = [
    # A. Tick label stress
    RobustnessScenario(
        name="long_xtick_labels_no_rotation",
        build=_build_long_xtick_labels_no_rotation,
        # 25-char labels, no rotation — auto_layout should resolve
        # any overflow without xfail. Baseline "happy path" for section A.
        expect_warnings=(),
        forbid_warnings=("OVERFLOW",),
        pixel_checks=("assert_minimum_white_border",),
    ),
    pytest.param(
        RobustnessScenario(
            name="long_xtick_labels_45_rotation",
            build=_build_long_xtick_labels_45_rotation,
        ),
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "rotated-tick layout bug — fixed in Task 11"
            ),
        ),
    ),
    pytest.param(
        RobustnessScenario(
            name="long_xtick_labels_90_rotation",
            build=_build_long_xtick_labels_90_rotation,
        ),
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "rotated-tick layout bug — fixed in Task 11"
            ),
        ),
    ),
    pytest.param(
        RobustnessScenario(
            name="long_ytick_labels_horizontal_bar",
            build=_build_long_ytick_labels_horizontal_bar,
        ),
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "long-tick layout bug — fixed in Task 10/11"
            ),
        ),
    ),
    RobustnessScenario(
        name="dense_xticks_50_categories",
        build=_build_dense_xticks_50_categories,
        # 50 ticks in 13 cm guarantees a TICK_CROWD info. After
        # auto_layout we still have 50 ticks; the info is informational
        # and OVERFLOW must remain absent.
        expect_warnings=("TICK_CROWD",),
    ),
    RobustnessScenario(
        name="unicode_korean_xticks",
        build=_build_unicode_korean_xticks,
    ),
    RobustnessScenario(
        name="mixed_kr_en_xticks",
        build=_build_mixed_kr_en_xticks,
    ),
    pytest.param(
        RobustnessScenario(
            name="scientific_notation_yticks",
            build=_build_scientific_notation_yticks,
        ),
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "log-scale y-axis exponent labels overflow "
                "auto_layout — fixed in Task 10 (BUFFER scaling) "
                "or Task 11 if exponent footprint requires alignment fix"
            ),
        ),
    ),
]
