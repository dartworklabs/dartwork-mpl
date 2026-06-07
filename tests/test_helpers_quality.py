"""Smoke tests for ``dartwork_mpl.helpers.quality``."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl.helpers.quality import (
    check_figure_quality,
    suggest_chart_type,
)


class TestSuggestChartType:
    """Happy-path coverage for the chart-type heuristic."""

    @pytest.mark.parametrize(
        "x_type, y_type, n_points, n_series, expected",
        [
            ("categorical", "continuous", 5, 1, "bar"),
            ("categorical", "continuous", 5, 3, "grouped_bar"),
            ("temporal", "continuous", 10, 1, "bar_line"),
            ("temporal", "continuous", 100, 1, "line"),
            ("temporal", "continuous", 50, 3, "multi_line"),
            ("continuous", "continuous", 30, 1, "scatter"),
            ("continuous", "continuous", 200, 1, "scatter_density"),
            ("continuous", "continuous", 1000, 1, "hexbin"),
            ("continuous", None, 50, 1, "histogram"),
            ("categorical", None, 5, 1, "count_bar"),
        ],
    )
    def test_returns_expected_type(
        self,
        x_type: str,
        y_type: str | None,
        n_points: int,
        n_series: int,
        expected: str,
    ) -> None:
        result = suggest_chart_type(x_type, y_type, n_points, n_series)
        assert result == expected


class TestCheckFigureQuality:
    """Happy-path coverage for the figure-quality lint."""

    def test_clean_figure_with_labels(self) -> None:
        """A figure with labels and data should produce few/no issues."""
        fig, ax = plt.subplots(dpi=200)
        ax.plot([1, 2, 3], [4, 5, 6])
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        issues = check_figure_quality(fig)
        # Should not flag missing labels.
        assert not any("Missing x-axis label" in i for i in issues)
        assert not any("Missing y-axis label" in i for i in issues)

    def test_low_dpi_flagged(self) -> None:
        fig, ax = plt.subplots(dpi=72)
        ax.plot([1, 2], [3, 4])
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        issues = check_figure_quality(fig)
        assert any("Low DPI" in i for i in issues)

    def test_missing_labels_flagged(self) -> None:
        fig, ax = plt.subplots(dpi=200)
        ax.plot([1, 2, 3], [4, 5, 6])
        # Intentionally omit set_xlabel/set_ylabel.
        issues = check_figure_quality(fig)
        assert any("Missing x-axis label" in i for i in issues)
        assert any("Missing y-axis label" in i for i in issues)

    def test_returns_a_list(self) -> None:
        """The function always returns a list (never None / dict)."""
        fig, _ax = plt.subplots(dpi=200)
        issues = check_figure_quality(fig)
        assert isinstance(issues, list)
        assert all(isinstance(i, str) for i in issues)

    def test_axes_with_no_data_flagged(self) -> None:
        """Empty axes (no plotted artists) should be flagged."""
        fig, ax = plt.subplots(dpi=200)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        # No plot/scatter calls -> no real data artist on the axes.
        issues = check_figure_quality(fig)
        assert any("No data plotted" in i for i in issues)

    def test_invisible_axes_skipped(self) -> None:
        """``ax.set_visible(False)`` axes are not inspected."""
        fig, (ax_a, ax_b) = plt.subplots(1, 2, dpi=200)
        ax_a.plot([1, 2], [3, 4])
        ax_a.set_xlabel("x")
        ax_a.set_ylabel("y")
        # b is hidden -> should not trigger missing-label warnings.
        ax_b.set_visible(False)
        issues = check_figure_quality(fig)
        assert not any("Axes 1: Missing x-axis label" in i for i in issues)
        assert not any("Axes 1: Missing y-axis label" in i for i in issues)

    def test_dpi_at_threshold_not_flagged(self) -> None:
        """DPI >= the recommended threshold must not flag.

        The threshold and the advice text now share one constant
        (_MIN_RECOMMENDED_DPI = 200); previously the check used 150 while
        the message said 200.
        """
        from dartwork_mpl.helpers.quality import _MIN_RECOMMENDED_DPI

        fig, ax = plt.subplots(dpi=_MIN_RECOMMENDED_DPI)
        ax.plot([1, 2], [3, 4])
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        issues = check_figure_quality(fig)
        assert not any("Low DPI" in i for i in issues)

    def test_dpi_below_threshold_message_matches_threshold(self) -> None:
        """The flagged message advises exactly the threshold value, so the
        two can never drift apart again.

        Uses ``Figure`` directly rather than ``plt.subplots`` so the
        figure dpi is exactly what we set — an interactive backend
        (e.g. macOS Retina) otherwise scales canvas dpi by the device
        pixel ratio and would push 199 over the threshold.
        """
        from matplotlib.figure import Figure

        from dartwork_mpl.helpers.quality import _MIN_RECOMMENDED_DPI

        fig = Figure(dpi=_MIN_RECOMMENDED_DPI - 1)
        ax = fig.subplots()
        ax.plot([1, 2], [3, 4])
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        issues = check_figure_quality(fig)
        low = [i for i in issues if "Low DPI" in i]
        assert low
        assert f"at least {_MIN_RECOMMENDED_DPI}" in low[0]

    def test_too_many_ticks_flagged(self) -> None:
        """>20 fixed ticks on either axis should be flagged."""
        fig, ax = plt.subplots(dpi=200)
        ax.plot([0, 1], [0, 1])
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        # Force >20 ticks on both axes via fixed locator.
        ax.set_xticks(list(range(25)))
        ax.set_yticks(list(range(25)))
        issues = check_figure_quality(fig)
        assert any("Too many x-ticks" in i for i in issues)
        assert any("Too many y-ticks" in i for i in issues)


class TestSuggestChartTypeEdgeCases:
    """Branches not covered by parametrized happy paths."""

    def test_unknown_x_type_with_y_returns_scatter_default(self) -> None:
        """An unrecognized ``x_type`` falls through to the scatter default."""
        result = suggest_chart_type("weird", "continuous", 10, 1)
        assert result == "scatter"

    def test_unknown_x_type_no_y_returns_line(self) -> None:
        """``y_type=None`` with unknown x_type hits the ``return 'line'``
        branch (line 45)."""
        result = suggest_chart_type("weird", None, 10, 1)
        assert result == "line"

    def test_categorical_with_categorical_y_returns_bar(self) -> None:
        """Categorical x + non-continuous y still routes via ``n_series``."""
        # Single series -> bar (regardless of y_type categorical/count).
        assert suggest_chart_type("categorical", "count", 5, 1) == "bar"
        # Multi series -> grouped_bar.
        assert suggest_chart_type("categorical", "count", 5, 4) == "grouped_bar"

    def test_continuous_x_count_y_routes_to_line(self) -> None:
        """``y_type != 'continuous'`` with continuous x falls to the
        line branch (line 67)."""
        result = suggest_chart_type("continuous", "count", 10, 1)
        assert result == "line"

    def test_temporal_boundary_19_vs_20(self) -> None:
        """Boundary at ``n_points < 20`` for temporal single-series."""
        # 19 -> bar_line.
        assert suggest_chart_type("temporal", "continuous", 19, 1) == "bar_line"
        # 20 -> line.
        assert suggest_chart_type("temporal", "continuous", 20, 1) == "line"

    def test_continuous_continuous_boundaries(self) -> None:
        """Boundaries at 50 (scatter -> scatter_density) and 500
        (scatter_density -> hexbin)."""
        assert (
            suggest_chart_type("continuous", "continuous", 49, 1) == "scatter"
        )
        assert (
            suggest_chart_type("continuous", "continuous", 50, 1)
            == "scatter_density"
        )
        assert (
            suggest_chart_type("continuous", "continuous", 499, 1)
            == "scatter_density"
        )
        assert (
            suggest_chart_type("continuous", "continuous", 500, 1) == "hexbin"
        )
