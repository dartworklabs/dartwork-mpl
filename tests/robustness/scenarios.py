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

import matplotlib.pyplot as plt
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


# ───────────────────────────────────────────────────────
# B. Multiple-axis (twinx / twiny)
# ───────────────────────────────────────────────────────


def _build_twinx_basic_short_labels() -> Figure:
    fig, ax1 = dm.subplots(width="13cm", aspect="standard")
    ax1.plot([1, 2, 3], [1, 2, 3], label="L")
    ax1.set_ylabel("L")
    ax2 = ax1.twinx()
    ax2.plot([1, 2, 3], [10, 20, 30], color="red", label="R")
    ax2.set_ylabel("R")
    return fig


def _build_twinx_long_right_label() -> Figure:
    fig, ax1 = dm.subplots(width="13cm", aspect="standard")
    ax1.plot([1, 2, 3], [1, 2, 3])
    ax1.set_ylabel("Left axis")
    ax2 = ax1.twinx()
    ax2.plot([1, 2, 3], [1e6, 2e6, 3e6], color="red")
    ax2.set_ylabel(
        "Right axis with very long label (units in USD millions)"
    )
    return fig


def _build_twinx_unit_clash() -> Figure:
    # plan said "lang-kr" but that is a raw style layer, not a preset.
    # report-kr is the smallest preset that activates lang-kr.
    dm.style.use("report-kr")
    fig, ax1 = dm.subplots(width="13cm", aspect="standard")
    ax1.plot([1, 2, 3], [-10, 0, 25])
    ax1.set_ylabel("온도 (°C)")
    ax2 = ax1.twinx()
    ax2.plot([1, 2, 3], [1.2e12, 1.5e12, 1.8e12], color="red")
    ax2.set_ylabel("Revenue (₩, 조원)")
    return fig


def _build_twiny_dual_xaxis() -> Figure:
    fig, ax1 = dm.subplots(width="13cm", aspect="standard")
    ax1.plot([1, 2, 3], [1, 2, 3])
    ax1.set_xlabel("Bottom axis: index")
    ax2 = ax1.twiny()
    ax2.set_xlim(2020, 2025)
    ax2.set_xlabel("Top axis: year")
    return fig


def _build_triple_axis_parasite() -> Figure:
    # Imported inside the builder to keep the only mpl_toolkits usage
    # in the suite scoped to the one scenario that needs it.
    # mpl_toolkits.axes_grid1 is part of matplotlib core (always
    # available); the placement is stylistic, not a dependency guard.
    from mpl_toolkits.axes_grid1 import host_subplot

    # host_subplot requires a raw plt.figure(); dm.subplots cannot be
    # used here because host_subplot manages its own axes layout.
    # Width 13/2.54 in x 0.75 matches the 13 cm / "standard" aspect
    # used by other builders in this file.
    fig = plt.figure(figsize=(13 / 2.54, 13 / 2.54 * 0.75))
    host = host_subplot(111)
    par1 = host.twinx()
    par2 = host.twinx()
    # Offset the third axis 60 px to the right.
    par2.spines["right"].set_position(("outward", 60))
    host.plot([1, 2, 3], [1, 2, 3], label="A")
    par1.plot([1, 2, 3], [10, 20, 30], color="red", label="B")
    par2.plot([1, 2, 3], [1e6, 2e6, 3e6], color="green", label="C")
    host.set_ylabel("A")
    par1.set_ylabel("B")
    par2.set_ylabel("C (millions)")
    return fig


# ───────────────────────────────────────────────────────
# C. Margin / layout corner cases
# ───────────────────────────────────────────────────────


def _build_extreme_left_squeeze() -> Figure:
    # left=0.05 would push content to the canvas edge so left_margin
    # falls below the 30 px MIN_MARGIN_PX threshold in _check_margin_asymmetry
    # and the check skips the comparison. left=0.10 gives ~113 px left
    # margin, well above the threshold, while right margin stays ~1300 px
    # (ratio ~11x), reliably triggering MARGIN_ASYMMETRY.
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.barh([0, 1, 2], [1, 2, 3])
    fig.subplots_adjust(left=0.10, right=0.35)
    return fig


def _build_extreme_right_squeeze() -> Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.barh([0, 1, 2], [1, 2, 3])
    fig.subplots_adjust(left=0.70, right=0.95)
    return fig


def _build_extreme_bottom_squeeze() -> Figure:
    fig, ax = plt.subplots(figsize=(6, 8))
    ax.bar([0, 1, 2], [1, 2, 3])
    fig.subplots_adjust(bottom=0.60, top=0.95)
    return fig


def _build_outside_axes_annotation() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3])
    ax.annotate(
        "Far left annotation",
        xy=(1, 1),
        xytext=(-0.4, 0.5),
        textcoords="axes fraction",
        fontsize=12,
    )
    return fig


def _build_axes_fraction_text_below_zero() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3])
    ax.text(0.5, -0.25, "below the axis", transform=ax.transAxes)
    return fig


def _build_colorbar_below_axes() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    # Seeded RNG for reproducible test artefacts (per plan §Execution Notes).
    rng = np.random.default_rng(42)
    im = ax.imshow(rng.random((10, 10)))
    fig.colorbar(im, ax=ax, orientation="horizontal", shrink=0.8)
    return fig


# ───────────────────────────────────────────────────────
# D. Data degeneracies
# ───────────────────────────────────────────────────────


def _build_nan_only_y() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3], [np.nan, np.nan, np.nan])
    ax.set_ylabel("Value")
    return fig


def _build_inf_in_y() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3, 4, 5], [1.0, 2.0, np.inf, -np.inf, 5.0])
    ax.set_ylabel("Value")
    return fig


def _build_single_point_data() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([5], [5], "o")
    ax.set_ylabel("Value")
    return fig


def _build_constant_y() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3, 4, 5], [7, 7, 7, 7, 7])
    ax.set_ylabel("Value")
    return fig


def _build_negative_log_data() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3, 4, 5], [-2, 1, 10, 100, -50])
    ax.set_yscale("log")
    ax.set_ylabel("Value")
    return fig


# ───────────────────────────────────────────────────────
# E. Scale & axis types
# ───────────────────────────────────────────────────────


def _build_log_y_with_minor_ticks() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    x = np.linspace(1, 5, 100)
    ax.plot(x, 10**x)
    ax.set_yscale("log")
    ax.minorticks_on()
    ax.set_ylabel("Value")
    return fig


def _build_symlog_y_centered_on_zero() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    x = np.linspace(-10, 10, 200)
    ax.plot(x, x**3)
    ax.set_yscale("symlog", linthresh=10)
    ax.set_ylabel("Value")
    return fig


def _build_datetime_x_5_years_daily() -> Figure:
    import numpy as np
    import pandas as pd

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    dates = pd.date_range("2021-01-01", "2025-12-31", freq="D")
    rng = np.random.default_rng(42)
    ax.plot(dates, np.cumsum(rng.standard_normal(len(dates))))
    ax.set_ylabel("Value")
    fig.autofmt_xdate()
    return fig


def _build_datetime_x_minutes() -> Figure:
    import numpy as np
    import pandas as pd

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    times = pd.date_range(
        "2026-05-02 09:00", "2026-05-02 13:00", freq="1min"
    )
    rng = np.random.default_rng(42)
    ax.plot(times, np.cumsum(rng.standard_normal(len(times))))
    ax.set_ylabel("Value")
    fig.autofmt_xdate()
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
    # B. Multiple-axis (twinx / twiny)
    RobustnessScenario(
        name="twinx_basic_short_labels",
        build=_build_twinx_basic_short_labels,
    ),
    RobustnessScenario(
        name="twinx_long_right_label",
        build=_build_twinx_long_right_label,
    ),
    RobustnessScenario(
        name="twinx_unit_clash",
        build=_build_twinx_unit_clash,
    ),
    RobustnessScenario(
        name="twiny_dual_xaxis",
        build=_build_twiny_dual_xaxis,
    ),
    RobustnessScenario(
        name="triple_axis_parasite",
        build=_build_triple_axis_parasite,
        # Parasite axes use absolute pixel offsets that auto_layout
        # can't negotiate; the test only verifies "no crash + saveable",
        # so we tolerate residual OVERFLOW and skip pixel border checks.
        forbid_warnings=(),
        pixel_checks=(),
    ),
    # C. Margin / layout corner cases
    RobustnessScenario(
        name="extreme_left_squeeze",
        build=_build_extreme_left_squeeze,
        # MARGIN_ASYMMETRY is the whole point — must be flagged before
        # auto_layout. simple_layout's scipy optimizer targets all four
        # margins simultaneously, so it incidentally rebalances the
        # squeeze without a dedicated symmetry pass (that is Task 13).
        # No xfail needed.
        expect_warnings=("MARGIN_ASYMMETRY",),
    ),
    RobustnessScenario(
        name="extreme_right_squeeze",
        build=_build_extreme_right_squeeze,
        expect_warnings=("MARGIN_ASYMMETRY",),
    ),
    RobustnessScenario(
        name="extreme_bottom_squeeze",
        build=_build_extreme_bottom_squeeze,
        expect_warnings=("MARGIN_ASYMMETRY",),
    ),
    pytest.param(
        RobustnessScenario(
            name="outside_axes_annotation",
            build=_build_outside_axes_annotation,
            # Axes-fraction annotations move *with* the subplot; auto_layout
            # may need extra iterations.
            auto_layout_max_iter=15,
        ),
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "axes-fraction annotations escape canvas — "
                "fixed in Task 10 (auto_layout BUFFER scaling)"
            ),
        ),
    ),
    pytest.param(
        RobustnessScenario(
            name="axes_fraction_text_below_zero",
            build=_build_axes_fraction_text_below_zero,
            auto_layout_max_iter=15,
        ),
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "axes-fraction text below zero overflows canvas — "
                "fixed in Task 10 (auto_layout BUFFER scaling)"
            ),
        ),
    ),
    pytest.param(
        RobustnessScenario(
            name="colorbar_below_axes",
            build=_build_colorbar_below_axes,
        ),
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "horizontal colorbar overshoots top edge after "
                "auto_layout — fixed in Task 13 (auto_layout "
                "symmetry pass) or Task 10 (BUFFER scaling) if "
                "the overshoot turns out to be a per-side margin "
                "amount problem"
            ),
        ),
    ),
    # D. Data degeneracies
    RobustnessScenario(
        name="nan_only_y",
        build=_build_nan_only_y,
        # No data to plot but axes still has a Line2D artist → not empty.
        # Must not crash anywhere in validate or auto_layout.
        forbid_warnings=("OVERFLOW",),
    ),
    RobustnessScenario(
        name="inf_in_y",
        build=_build_inf_in_y,
    ),
    RobustnessScenario(
        name="single_point_data",
        build=_build_single_point_data,
    ),
    RobustnessScenario(
        name="constant_y",
        build=_build_constant_y,
    ),
    RobustnessScenario(
        name="negative_log_data",
        build=_build_negative_log_data,
        # Negative-on-log is a real warning in matplotlib; the figure
        # still renders (negative samples are dropped). Test only that
        # we don't crash and the saved PNG isn't empty.
    ),
    # E. Scale & axis types
    RobustnessScenario(
        name="log_y_with_minor_ticks",
        build=_build_log_y_with_minor_ticks,
    ),
    RobustnessScenario(
        name="symlog_y_centered_on_zero",
        build=_build_symlog_y_centered_on_zero,
    ),
    RobustnessScenario(
        name="datetime_x_5_years_daily",
        build=_build_datetime_x_5_years_daily,
    ),
    RobustnessScenario(
        name="datetime_x_minutes",
        build=_build_datetime_x_minutes,
    ),
]
