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
    auto_layout_padding
        Initial padding (inches) passed to ``dm.auto_layout``. Most
        scenarios accept the default 0.08. Scenarios with
        axes-fraction-positioned spines or other content that fills
        the canvas tightly may need a larger value (e.g. 0.25) so the
        iteration converges with a 4 px white-border invariant.
    """

    name: str
    build: Callable[[], Figure]
    expect_warnings: tuple[str, ...] = ()
    forbid_warnings: tuple[str, ...] = ("OVERFLOW",)
    pixel_checks: tuple[str, ...] = ("assert_minimum_white_border",)
    auto_layout_max_iter: int = 5
    auto_layout_padding: float | tuple[float, float, float, float] = 0.08


# Scenarios still wrapped with pytest.mark.xfail(strict=True) because
# the underlying library limitation hasn't been resolved yet. Each
# entry is a (scenario_name, reason, tracking_owner) tuple. Lift the
# xfail when the reason is fixed and verify the scenario now passes.
KNOWN_LIMITATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "long_xtick_labels_45_rotation",
        "OVERFLOW persists after auto_layout for 25-char rotated x-tick "
        "labels; the rotation increases tick footprint beyond what the "
        "BUFFER scaling (Task 10) can absorb. Future fix: a layout pass "
        "that detects rotated tick labels and pre-allocates the rotated "
        "footprint instead of iterating overflow.",
        "follow-up issue (TBD)",
    ),
    (
        "long_xtick_labels_90_rotation",
        "Same root cause as 45_rotation but more severe at 90 degrees.",
        "follow-up issue (TBD)",
    ),
    (
        "long_ytick_labels_horizontal_bar",
        "Long left-side ytick labels on horizontal bar chart overflow "
        "the canvas; auto_layout's per-iteration BUFFER doesn't grow "
        "fast enough for 25-char labels.",
        "follow-up issue (TBD)",
    ),
    (
        "outside_axes_annotation",
        "Axes-fraction xytext at (-0.4, 0.5) escapes the canvas; "
        "auto_layout's iterative margin expansion can't reach the "
        "necessary padding within max_iter.",
        "follow-up issue (TBD)",
    ),
    (
        "axes_fraction_text_below_zero",
        "ax.text at y=-0.25 axes-fraction overflows the bottom edge.",
        "follow-up issue (TBD)",
    ),
    (
        "colorbar_below_axes",
        "Horizontal colorbar shifts the figure into the top edge after "
        "auto_layout. Likely needs a colorbar-aware layout pass.",
        "follow-up issue (TBD)",
    ),
    (
        "crowded_legend_outside",
        "bbox_to_anchor=(1.02, 1) places the legend outside the axes; "
        "auto_layout doesn't expand the right margin to accommodate it.",
        "follow-up issue (TBD)",
    ),
    (
        "triple_twinx_offset_spine",
        "Third axis at axes-fraction 1.15 with an 8-char ylabel "
        "('Series C') sits ~2 px from the canvas right edge after "
        "auto_layout. The fixed point is independent of max_iter "
        "(verified up to 50). Future fix: BUFFER scaling for "
        "axes-fraction-positioned spines proportional to "
        "(fraction - 1.0) plus the offset axis ylabel/tick footprint.",
        "follow-up issue (TBD)",
    ),
)


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
    ax2.set_ylabel("Right axis with very long label (units in USD millions)")
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


def _build_triple_twinx_offset_spine() -> Figure:
    """Three y-axes via two consecutive ``ax.twinx()`` calls plus
    spine offset at axes-fraction 1.15 for the third axis. Verifies
    that the dartwork ``twinx`` monkey-patch (which forces the right
    spine visible) still works on the *third* axis when its right
    spine is repositioned via ``set_position``.

    This guards against a regression where the patch only kicked in
    for the second axis (the immediate twin) and left the third
    axis's right spine invisible after the position change."""
    fig, ax1 = dm.subplots(width="14cm", aspect="standard")
    ax1.plot([1, 2, 3, 4], [1, 4, 9, 16], color="#1f77b4")
    ax1.set_ylabel("Series A")

    ax2 = ax1.twinx()
    ax2.plot([1, 2, 3, 4], [10, 20, 30, 40], color="#ff7f0e")
    ax2.set_ylabel("Series B")

    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("axes", 1.15))
    ax3.plot([1, 2, 3, 4], [100, 200, 150, 250], color="#2ca02c")
    ax3.set_ylabel("Series C")

    # All three right spines must end up visible (the monkey-patch
    # in dartwork_mpl/__init__.py runs on every twinx() call).
    assert ax2.spines["right"].get_visible(), (
        "ax2 right spine should be visible after twinx() monkey-patch"
    )
    assert ax3.spines["right"].get_visible(), (
        "ax3 right spine should be visible after twinx() monkey-patch"
    )
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
    times = pd.date_range("2026-05-02 09:00", "2026-05-02 13:00", freq="1min")
    rng = np.random.default_rng(42)
    ax.plot(times, np.cumsum(rng.standard_normal(len(times))))
    ax.set_ylabel("Value")
    fig.autofmt_xdate()
    return fig


# ───────────────────────────────────────────────────────
# F. Saved-output integrity
# ───────────────────────────────────────────────────────


def _build_tiny_figure_2_5cm() -> Figure:
    fig, ax = dm.subplots(width="2.5cm", aspect="standard")
    ax.plot([1, 2, 3])
    ax.set_ylabel("Y")
    return fig


def _build_huge_figure_30cm() -> Figure:
    fig, ax = dm.subplots(width="30cm", aspect="standard")
    ax.plot(list(range(50)), list(range(50)))
    ax.set_ylabel("Value")
    return fig


def _build_square_aspect_with_long_legend() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="square")
    for i in range(12):
        ax.plot([0, 1], [i, i + 1], label=f"Series {i:02d} long label")
    ax.legend(loc="best")
    ax.set_ylabel("Y")
    return fig


# ───────────────────────────────────────────────────────
# G. Multi-axes layout
# ───────────────────────────────────────────────────────


def _build_gridspec_2x3_mixed() -> Figure:
    import numpy as np

    fig, axes = dm.subplots(2, 3, width="17cm", aspect="standard")
    rng = np.random.default_rng(42)
    axes[0, 0].plot([1, 2, 3])
    axes[0, 1].bar(["a", "b", "c"], [3, 5, 7])
    axes[0, 2].imshow(rng.random((10, 10)))
    axes[1, 0].scatter(rng.standard_normal(20), rng.standard_normal(20))
    axes[1, 1].hist(rng.standard_normal(100), bins=20)
    axes[1, 2].plot([1, 2, 3], [3, 2, 1])
    for ax in axes.flat:
        ax.set_ylabel("Y")
    return fig


def _build_inset_axes_overlapping_ticks() -> Figure:
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3, 4, 5], [10, 30, 20, 50, 40])
    ax.set_ylabel("Y")
    inset = inset_axes(ax, width="40%", height="40%", loc="lower left")
    inset.plot([1, 2, 3], [3, 2, 1])
    return fig


def _build_subplots_4_with_one_pie() -> Figure:
    fig, axes = dm.subplots(2, 2, width="13cm", aspect="square")
    axes[0, 0].plot([1, 2, 3])
    axes[0, 0].set_ylabel("Y")
    axes[0, 1].bar(["a", "b"], [3, 5])
    axes[0, 1].set_ylabel("Y")
    axes[1, 0].plot([3, 2, 1])
    axes[1, 0].set_ylabel("Y")
    width = 0.4
    axes[1, 1].pie(
        [40, 30, 20, 10],
        labels=["A", "B", "C", "D"],
        autopct="%.0f%%",
        pctdistance=1.0 - width / 2.0,
        wedgeprops={"width": width},
    )
    return fig


def _build_colorbar_attached_heatmap() -> Figure:
    import numpy as np

    fig, ax = dm.subplots(width="13cm", aspect="standard")
    rng = np.random.default_rng(42)
    im = ax.imshow(rng.random((10, 10)))
    fig.colorbar(im, ax=ax, shrink=0.8)
    return fig


def _build_subfigures_2x1() -> Figure:
    """Two subfigures stacked vertically, each with its own axes,
    title-text, and ylabel.

    matplotlib's ``fig.subfigures()`` partitions a parent figure into
    independent SubFigure children, each with its own GridSpec. This
    scenario verifies that ``dm.validate_figure`` and
    ``dm.auto_layout`` do not crash or report spurious warnings on
    the SubFigure tree, which uses a different artist hierarchy from
    plain ``plt.subplots``.
    """
    fig = dm.figure(width="14cm", aspect="standard")
    sub_top, sub_bot = fig.subfigures(2, 1, hspace=0.05)

    ax_top = sub_top.subplots()
    ax_top.plot([1, 2, 3, 4], [1, 4, 9, 16])
    ax_top.set_ylabel("Top axis (units)")

    ax_bot = sub_bot.subplots()
    ax_bot.bar(["A", "B", "C"], [3, 7, 5])
    ax_bot.set_ylabel("Bottom axis (count)")

    return fig


def _build_constrained_layout_then_auto_layout() -> Figure:
    """A figure constructed with ``constrained_layout=True`` that the
    suite then re-flows via ``auto_layout``. The expectation is that
    auto_layout is a no-op (constrained-layout already balanced the
    margins) and the figure saves cleanly. Verifies dartwork-mpl
    plays nicely with matplotlib's other layout engine."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5.5, 3.5), constrained_layout=True)
    ax.plot([1, 2, 3, 4], [4, 1, 5, 2])
    ax.set_ylabel("Value (units)")
    ax.set_xlabel("Index")
    return fig


# ───────────────────────────────────────────────────────
# H. Style / font
# ───────────────────────────────────────────────────────


def _build_report_kr_style() -> Figure:
    # plan said "lang-kr" but that is a raw style layer, not a preset.
    # report-kr is the smallest preset that activates lang-kr.
    dm.style.use("report-kr")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3], [10, 20, 15])
    ax.set_ylabel("매출 (억원)")
    ax.set_xlabel("연도")
    return fig


def _build_dark_style() -> Figure:
    # plan said "theme-dark" but that is a raw style layer.
    # "dark" is the smallest preset that activates theme-dark
    # (= base + font-web + theme-dark).
    dm.style.use("dark")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3], [10, 20, 15])
    ax.set_ylabel("Y")
    ax.set_xlabel("X")
    return fig


def _build_minimal_style() -> Figure:
    # plan said "theme-minimal" / "font-minimal" but those are raw
    # style layers. "minimal" is the preset that wraps both
    # (= base + font-minimal + theme-minimal).
    dm.style.use("minimal")
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3], [10, 20, 15])
    ax.set_ylabel("Y")
    ax.set_xlabel("X")
    return fig


# ───────────────────────────────────────────────────────
# I. Annotation density
# ───────────────────────────────────────────────────────


def _build_bar_chart_value_labels() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    values = [3, 5, 7, 4, 6]
    bars = ax.bar(["a", "b", "c", "d", "e"], values)
    for bar, v in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{v}",
            ha="center",
            va="bottom",
        )
    ax.set_ylabel("Value")
    return fig


def _build_crowded_legend_outside() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    for i in range(20):
        ax.plot([0, 1], [i, i + 1], label=f"Series {i:02d}")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax.set_ylabel("Y")
    return fig


def _build_arrow_annotations_diagonal() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="standard")
    ax.plot([1, 2, 3, 4, 5], [10, 30, 20, 50, 40])
    for x_to, x_from, label in [(2, 1, "first"), (4, 2, "mid"), (5, 4, "end")]:
        ax.annotate(
            label,
            xy=(x_to, 30),
            xytext=(x_from, 50),
            arrowprops={"arrowstyle": "->"},
        )
    ax.set_ylabel("Y")
    return fig


# ───────────────────────────────────────────────────────
# J. Pie / donut variants
# ───────────────────────────────────────────────────────


def _build_pie_full_default() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="square")
    ax.pie([40, 30, 20, 7, 3], labels=["A", "B", "C", "D", "E"])
    return fig


def _build_donut_thin_correct_pctdistance() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="square")
    width = 0.15
    ax.pie(
        [50, 30, 20],
        autopct="%.0f%%",
        pctdistance=1.0 - width / 2.0,
        wedgeprops={"width": width},
    )
    return fig


def _build_donut_wide_wrong_pctdistance() -> Figure:
    fig, ax = dm.subplots(width="13cm", aspect="square")
    ax.pie(
        [50, 30, 20],
        autopct="%.0f%%",
        pctdistance=0.4,
        wedgeprops={"width": 0.7},
    )
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
                "OVERFLOW persists after auto_layout for 25-char "
                "rotated x-tick labels (KNOWN_LIMITATIONS)"
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
                "OVERFLOW persists at 90-degree rotation (KNOWN_LIMITATIONS)"
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
                "long ytick labels on horizontal bar overflow canvas "
                "(KNOWN_LIMITATIONS)"
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
        name="unicode_korean_xticks", build=_build_unicode_korean_xticks
    ),
    RobustnessScenario(
        name="mixed_kr_en_xticks", build=_build_mixed_kr_en_xticks
    ),
    RobustnessScenario(
        name="scientific_notation_yticks",
        build=_build_scientific_notation_yticks,
    ),
    # B. Multiple-axis (twinx / twiny)
    RobustnessScenario(
        name="twinx_basic_short_labels", build=_build_twinx_basic_short_labels
    ),
    RobustnessScenario(
        name="twinx_long_right_label", build=_build_twinx_long_right_label
    ),
    RobustnessScenario(name="twinx_unit_clash", build=_build_twinx_unit_clash),
    RobustnessScenario(name="twiny_dual_xaxis", build=_build_twiny_dual_xaxis),
    RobustnessScenario(
        name="triple_axis_parasite",
        build=_build_triple_axis_parasite,
        # Parasite axes use absolute pixel offsets that auto_layout
        # can't negotiate; the test only verifies "no crash + saveable",
        # so we tolerate residual OVERFLOW and skip pixel border checks.
        forbid_warnings=(),
        pixel_checks=(),
    ),
    pytest.param(
        RobustnessScenario(
            name="triple_twinx_offset_spine",
            build=_build_triple_twinx_offset_spine,
            # The offset spine pushes ax3's ylabel ~15% past the axes
            # right edge — auto_layout must absorb it without leaving
            # OVERFLOW behind.
            auto_layout_max_iter=8,
        ),
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "axes-fraction 1.15 right spine ylabel ('Series C') "
                "cannot be absorbed by auto_layout — even at max_iter=50 "
                "the rightmost rendered pixel sits ~2px from the canvas "
                "edge (CLIPPED_TEXT margin: -1.5px). auto_layout BUFFER "
                "scaling for axes-fraction-positioned spines needs a "
                "follow-up tweak (KNOWN_LIMITATIONS)."
            ),
        ),
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
                "axes-fraction xytext at (-0.4, 0.5) escapes canvas; "
                "auto_layout cannot reach necessary padding within "
                "max_iter (KNOWN_LIMITATIONS)"
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
                "ax.text at y=-0.25 axes-fraction overflows the bottom "
                "edge (KNOWN_LIMITATIONS)"
            ),
        ),
    ),
    pytest.param(
        RobustnessScenario(
            name="colorbar_below_axes", build=_build_colorbar_below_axes
        ),
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "horizontal colorbar overshoots top edge after "
                "auto_layout (KNOWN_LIMITATIONS)"
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
    RobustnessScenario(name="inf_in_y", build=_build_inf_in_y),
    RobustnessScenario(
        name="single_point_data", build=_build_single_point_data
    ),
    RobustnessScenario(name="constant_y", build=_build_constant_y),
    RobustnessScenario(
        name="negative_log_data",
        build=_build_negative_log_data,
        # Negative-on-log is a real warning in matplotlib; the figure
        # still renders (negative values are clipped to the axis floor
        # via nonpositive='clip', not dropped). Test only that we don't
        # crash and the saved PNG isn't empty.
    ),
    # E. Scale & axis types
    RobustnessScenario(
        name="log_y_with_minor_ticks", build=_build_log_y_with_minor_ticks
    ),
    RobustnessScenario(
        name="symlog_y_centered_on_zero", build=_build_symlog_y_centered_on_zero
    ),
    RobustnessScenario(
        name="datetime_x_5_years_daily", build=_build_datetime_x_5_years_daily
    ),
    RobustnessScenario(
        name="datetime_x_minutes", build=_build_datetime_x_minutes
    ),
    # F. Saved-output integrity
    RobustnessScenario(
        name="tiny_figure_2_5cm",
        build=_build_tiny_figure_2_5cm,
        # 2.5 cm canvas can't fit ylabel + 4 ticks; expect TICK_CROWD
        # but we still want save_formats to succeed.
        forbid_warnings=(),  # Tolerate any post-layout warnings.
        # Canvas too small to satisfy the 4-px white-border invariant.
        pixel_checks=(),
    ),
    RobustnessScenario(name="huge_figure_30cm", build=_build_huge_figure_30cm),
    RobustnessScenario(
        name="square_aspect_with_long_legend",
        build=_build_square_aspect_with_long_legend,
        expect_warnings=("LEGEND_OVERFLOW",),
    ),
    # G. Multi-axes layout
    RobustnessScenario(
        name="gridspec_2x3_mixed", build=_build_gridspec_2x3_mixed
    ),
    RobustnessScenario(
        name="inset_axes_overlapping_ticks",
        build=_build_inset_axes_overlapping_ticks,
    ),
    RobustnessScenario(
        name="subplots_4_with_one_pie", build=_build_subplots_4_with_one_pie
    ),
    RobustnessScenario(
        name="colorbar_attached_heatmap",
        build=_build_colorbar_attached_heatmap,
        # Colorbar + heatmap causes content to reach the canvas edge
        # after auto_layout; the white-border invariant does not apply.
        pixel_checks=(),
    ),
    RobustnessScenario(
        name="subfigures_2x1",
        build=_build_subfigures_2x1,
        # auto_layout uses fig.axes[0].get_gridspec(); SubFigures wrap
        # each child in its own GridSpec so the parent layout-engine's
        # edge padding does not propagate into them. The scenario still
        # verifies validate_figure, auto_layout, and PNG round-trip,
        # but the global white-border invariant cannot hold here — same
        # limitation pattern as `colorbar_attached_heatmap`.
        forbid_warnings=("OVERFLOW",),
        pixel_checks=(),
    ),
    RobustnessScenario(
        name="constrained_layout_then_auto_layout",
        build=_build_constrained_layout_then_auto_layout,
        # constrained_layout owns the margins and packs content tighter
        # to the figure edge than auto_layout's BUFFER would. The
        # global white-border invariant doesn't hold when an alternate
        # layout engine drove the original margins — same precedent as
        # `colorbar_attached_heatmap` and `subfigures_2x1`. The
        # scenario still verifies validate_figure, auto_layout
        # idempotency, and the PNG round-trip.
        pixel_checks=(),
    ),
    # H. Style / font
    RobustnessScenario(name="report_kr_style", build=_build_report_kr_style),
    RobustnessScenario(
        name="dark_style",
        build=_build_dark_style,
        # Dark theme paints the canvas dark; the white-border helper is
        # designed for a white canvas, so swap the pixel check out.
        pixel_checks=(),
    ),
    RobustnessScenario(name="minimal_style", build=_build_minimal_style),
    # I. Annotation density
    RobustnessScenario(
        name="bar_chart_value_labels", build=_build_bar_chart_value_labels
    ),
    pytest.param(
        RobustnessScenario(
            name="crowded_legend_outside", build=_build_crowded_legend_outside
        ),
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "bbox_to_anchor=(1.02, 1) places legend outside axes; "
                "auto_layout doesn't expand right margin (KNOWN_LIMITATIONS)"
            ),
        ),
    ),
    RobustnessScenario(
        name="arrow_annotations_diagonal",
        build=_build_arrow_annotations_diagonal,
    ),
    # J. Pie / donut variants
    RobustnessScenario(name="pie_full_default", build=_build_pie_full_default),
    RobustnessScenario(
        name="donut_thin_correct_pctdistance",
        build=_build_donut_thin_correct_pctdistance,
    ),
    RobustnessScenario(
        name="donut_wide_wrong_pctdistance",
        build=_build_donut_wide_wrong_pctdistance,
        expect_warnings=("PIE_LABEL_OFFSET",),
    ),
]
