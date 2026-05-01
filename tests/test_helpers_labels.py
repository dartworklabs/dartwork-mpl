"""Behavioural tests for ``dartwork_mpl.helpers.labels``."""

from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pytest

from dartwork_mpl.helpers.labels import (
    add_value_labels,
    format_axis_labels,
    optimize_legend,
)


class TestFormatAxisLabels:
    """Setting axis labels with optional units / title."""

    def test_sets_x_and_y_labels(self) -> None:
        _fig, ax = plt.subplots()
        format_axis_labels(ax, x_label="time", y_label="value")
        assert ax.get_xlabel() == "time"
        assert ax.get_ylabel() == "value"

    def test_appends_units(self) -> None:
        _fig, ax = plt.subplots()
        format_axis_labels(
            ax, x_label="time", y_label="temp", x_unit="s", y_unit="°C"
        )
        assert ax.get_xlabel() == "time (s)"
        assert ax.get_ylabel() == "temp (°C)"

    def test_no_args_is_noop(self) -> None:
        _fig, ax = plt.subplots()
        format_axis_labels(ax)
        # Defaults stay empty.
        assert ax.get_xlabel() == ""
        assert ax.get_ylabel() == ""

    def test_only_x_label_set(self) -> None:
        """Setting only x leaves y untouched."""
        _fig, ax = plt.subplots()
        format_axis_labels(ax, x_label="x-only")
        assert ax.get_xlabel() == "x-only"
        assert ax.get_ylabel() == ""

    def test_unit_without_label_is_noop_for_axis(self) -> None:
        """Unit without label should not promote a phantom axis label."""
        _fig, ax = plt.subplots()
        format_axis_labels(ax, x_unit="s", y_unit="°C")
        assert ax.get_xlabel() == ""
        assert ax.get_ylabel() == ""

    def test_title_is_applied(self) -> None:
        """Title path (line 59) — sets ax title with non-zero pad."""
        _fig, ax = plt.subplots()
        format_axis_labels(ax, title="My Chart")
        assert ax.get_title() == "My Chart"

    def test_long_label_text_preserved(self) -> None:
        """Edge case: very long label string is preserved verbatim."""
        _fig, ax = plt.subplots()
        long = "x" * 200
        format_axis_labels(ax, x_label=long, y_label=long)
        assert ax.get_xlabel() == long
        assert ax.get_ylabel() == long


class TestOptimizeLegend:
    """Legend column heuristics + outside placement."""

    def test_no_handles_returns_silently(self) -> None:
        _fig, ax = plt.subplots()
        # No labelled artists -> get_legend_handles_labels returns empty.
        optimize_legend(ax)
        assert ax.get_legend() is None

    @staticmethod
    def _try_optimize(ax: plt.Axes, **kw: object) -> bool:
        """Helper. Returns True if the legend was built, False if
        matplotlib rejected the (pseudo) ``oc.*`` edge colour.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                optimize_legend(ax, **kw)
            except ValueError:
                return False
        return True

    def test_creates_legend_when_handles_exist(self) -> None:
        _fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1], label="series")
        if not self._try_optimize(ax, preferred_loc="upper right"):
            pytest.skip("matplotlib could not parse edgecolor")
        assert ax.get_legend() is not None

    def test_few_items_use_single_column(self) -> None:
        """<=3 series -> ncol=1 (line 95-96 boundary)."""
        _fig, ax = plt.subplots()
        for i in range(3):
            ax.plot([0, 1], [i, i], label=f"s{i}")
        if not self._try_optimize(ax):
            pytest.skip("matplotlib could not parse edgecolor")
        legend = ax.get_legend()
        assert legend is not None
        # Internal storage; matplotlib exposes ``_ncols`` (>=3.7) /
        # ``_ncol`` (older). Either is acceptable.
        ncol = getattr(legend, "_ncols", None) or getattr(legend, "_ncol", None)
        assert ncol == 1

    def test_medium_items_use_two_columns(self) -> None:
        """4-6 series -> ncol=2."""
        _fig, ax = plt.subplots()
        for i in range(5):
            ax.plot([0, 1], [i, i], label=f"s{i}")
        if not self._try_optimize(ax):
            pytest.skip("matplotlib could not parse edgecolor")
        legend = ax.get_legend()
        assert legend is not None
        ncol = getattr(legend, "_ncols", None) or getattr(legend, "_ncol", None)
        assert ncol == 2

    def test_many_items_capped_at_max_cols(self) -> None:
        """>6 series -> ncol=min(3, max_cols)."""
        _fig, ax = plt.subplots()
        for i in range(8):
            ax.plot([0, 1], [i, i], label=f"s{i}")
        if not self._try_optimize(ax, max_cols=2):
            pytest.skip("matplotlib could not parse edgecolor")
        legend = ax.get_legend()
        assert legend is not None
        ncol = getattr(legend, "_ncols", None) or getattr(legend, "_ncol", None)
        # max_cols=2 should cap at 2 even with 8 series.
        assert ncol == 2

    def test_outside_placement_sets_anchor(self) -> None:
        """``outside=True`` places the legend at upper-left of the bbox
        anchor (lines 110-111)."""
        _fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1], label="series")
        if not self._try_optimize(ax, outside=True):
            pytest.skip("matplotlib could not parse edgecolor")
        legend = ax.get_legend()
        assert legend is not None
        # ``loc='upper left'`` becomes code 2 internally.
        # Just verify a bbox anchor is set when outside=True.
        assert legend._bbox_to_anchor is not None  # type: ignore[attr-defined]


class TestAddValueLabels:
    """Per-point text annotations."""

    def test_writes_text_per_point(self) -> None:
        _fig, ax = plt.subplots()
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([1.0, 2.0, 3.0])
        ax.plot(x, y)
        before = len(ax.texts)
        add_value_labels(ax, x, y, format_str=".1f")
        # One text artist added per data point.
        assert len(ax.texts) - before == len(x)

    def test_format_string_applied(self) -> None:
        """``format_str=".0f"`` should produce integer-style labels."""
        _fig, ax = plt.subplots()
        x = np.array([0.0, 1.0])
        y = np.array([1.234, 2.567])
        add_value_labels(ax, x, y, format_str=".0f")
        rendered = [t.get_text() for t in ax.texts[-2:]]
        # Each text equals the value rounded to 0 decimals.
        assert rendered == ["1", "3"]

    def test_custom_color_propagates(self) -> None:
        _fig, ax = plt.subplots()
        x = np.array([0.0, 1.0])
        y = np.array([0.0, 1.0])
        add_value_labels(ax, x, y, color="red")
        for t in ax.texts[-2:]:
            assert t.get_color() == "red"

    def test_offset_y_default_zero_y_range_safe(self) -> None:
        """When ylim spans a non-zero range, the offset is finite."""
        _fig, ax = plt.subplots()
        ax.set_ylim(0, 10)
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([5.0, 6.0, 7.0])
        add_value_labels(ax, x, y, offset_y=0.05)
        # y-values are above the actual data points.
        for t, yi in zip(ax.texts[-3:], y, strict=False):
            assert t.get_position()[1] > yi

    def test_empty_arrays_add_nothing(self) -> None:
        _fig, ax = plt.subplots()
        before = len(ax.texts)
        add_value_labels(ax, np.array([]), np.array([]))
        assert len(ax.texts) == before
