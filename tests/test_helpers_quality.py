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
