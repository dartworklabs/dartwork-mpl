"""Tests for layout module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from dartwork_mpl.layout import (
    _measure_overflow,
    auto_layout,
    get_bounding_box,
    simple_layout,
)


class TestGetBoundingBox:
    """Tests for get_bounding_box()."""

    def test_single_axes(self) -> None:
        """Bounding box of a single subplot."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        fig.canvas.draw()

        boxes = [ax.get_tightbbox()]
        result = get_bounding_box(boxes)

        assert len(result) == 4
        min_x, min_y, width, height = result
        assert width > 0
        assert height > 0
        plt.close(fig)

    def test_multiple_axes(self) -> None:
        """Bounding box of multiple subplots should enclose all."""
        fig, axes = plt.subplots(1, 2)
        for ax in axes:
            ax.plot([1, 2, 3])
        fig.canvas.draw()

        boxes = [ax.get_tightbbox() for ax in axes]
        result = get_bounding_box(boxes)

        min_x, min_y, width, height = result
        assert width > 0
        assert height > 0
        plt.close(fig)


class TestSimpleLayout:
    """Tests for simple_layout()."""

    def test_single_subplot(self) -> None:
        """simple_layout should not raise on a basic figure."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        result = simple_layout(fig)
        assert result.success
        plt.close(fig)

    def test_multi_subplot(self) -> None:
        """simple_layout should handle 2x2 subplots."""
        fig, axes = plt.subplots(2, 2)
        for ax in axes.flat:
            ax.plot([1, 2, 3])
        result = simple_layout(fig)
        assert result.success
        plt.close(fig)

    def test_returns_optimize_result(self) -> None:
        from scipy.optimize import OptimizeResult

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        result = simple_layout(fig)
        assert isinstance(result, OptimizeResult)
        plt.close(fig)


class TestAutoLayout:
    """Tests for auto_layout()."""

    def test_basic(self) -> None:
        """auto_layout should run without error on a basic figure."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        ax.set_ylabel("Y Label")
        ax.set_xlabel("X Label")
        auto_layout(fig)  # should not raise
        plt.close(fig)

    def test_twinx_no_overflow(self) -> None:
        """auto_layout should eliminate overflow on a twinx chart."""
        fig, ax1 = plt.subplots(figsize=(6, 4))
        ax1.plot([1, 2, 3], label="Left")
        ax1.set_ylabel("Left Axis (온도 ℃)")

        ax2 = ax1.twinx()
        ax2.plot([10, 20, 30], color="red", label="Right")
        ax2.set_ylabel("Right Axis (%)")

        auto_layout(fig)

        # After auto_layout, overflow should be within tolerance
        overflow = _measure_overflow(fig)
        for side, px in overflow.items():
            assert px <= 2.0, f"Overflow on {side}: {px:.1f}px"
        plt.close(fig)

    def test_verbose_mode(self, capsys) -> None:
        """Verbose mode should print iteration info."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        auto_layout(fig, verbose=True)
        captured = capsys.readouterr()
        assert "[auto_layout]" in captured.out
        plt.close(fig)

    def test_custom_padding(self) -> None:
        """auto_layout should accept custom per-side padding."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        auto_layout(fig, padding=(0.15, 0.10, 0.10, 0.05))
        plt.close(fig)


class TestAutoLayoutEdgeCases:
    """Edge-case tests for auto_layout convergence."""

    def test_twinx_convergence(self) -> None:
        """auto_layout should converge on twinx with long labels."""
        fig, ax1 = plt.subplots(figsize=(8, 4))
        ax1.plot(range(20), [x**2 for x in range(20)])
        ax1.set_ylabel("Long Left Y-Axis Label (units)")
        ax2 = ax1.twinx()
        ax2.plot(range(20), [x * 5 for x in range(20)], color="red")
        ax2.set_ylabel("Right Axis With Long Label (%)")
        auto_layout(fig)
        overflow = _measure_overflow(fig)
        assert max(overflow.values()) <= 2.0
        plt.close(fig)

    def test_annotation_outside_axes(self) -> None:
        """Annotation extending beyond axes should converge."""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot([1, 2, 3])
        ax.annotate(
            "Far left annotation",
            xy=(1, 1),
            xytext=(-0.3, 0.5),
            textcoords="axes fraction",
            fontsize=12,
        )
        auto_layout(fig, max_iter=15)
        overflow = _measure_overflow(fig)
        assert max(overflow.values()) <= 2.0
        plt.close(fig)

    def test_large_tick_labels(self) -> None:
        """Large tick labels (billion-scale) should converge."""
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(range(10), [x * 1_000_000_000 for x in range(10)])
        ax.set_ylabel("Revenue")
        auto_layout(fig)
        overflow = _measure_overflow(fig)
        assert max(overflow.values()) <= 2.0
        plt.close(fig)

    def test_empty_axes(self) -> None:
        """auto_layout on empty axes should not crash."""
        fig, ax = plt.subplots(figsize=(6, 4))
        auto_layout(fig)
        plt.close(fig)

    def test_empty_figure_no_axes(self) -> None:
        """auto_layout on a figure with *no axes at all* must no-op
        rather than IndexError on ``fig.axes[0]``."""
        fig = plt.figure(figsize=(6, 4))
        try:
            assert fig.axes == []
            # Should return cleanly with no exception.
            auto_layout(fig)
            simple_layout(fig)
        finally:
            plt.close(fig)

    def test_colorbar_gridspec(self) -> None:
        """``fig.colorbar(im, ax=ax)`` wraps the axis in a
        ``GridSpecFromSubplotSpec`` which has no ``.update()``. The
        optimizer must walk up to the root ``GridSpec``. Regression for
        a crash on heatmaps with attached colorbars.
        """
        import numpy as np

        fig, ax = plt.subplots(figsize=(6, 4))
        im = ax.imshow(np.random.rand(10, 10))
        fig.colorbar(im, ax=ax, shrink=0.8)
        auto_layout(fig)
        plt.close(fig)

    def test_constrained_layout_off_then_auto_layout_runs_normally(self) -> None:
        """When ``constrained_layout`` is off (the dartwork default), a
        plain ``auto_layout`` call must run to convergence on a chart
        with reasonable labels."""
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=False)
        ax.plot([1, 2, 3])
        ax.set_ylabel("Value")
        ax.set_xlabel("Index")
        auto_layout(fig)
        overflow = _measure_overflow(fig)
        assert max(overflow.values()) <= 2.0

    def test_constrained_layout_on_then_auto_layout_no_crash(self) -> None:
        """``constrained_layout=True`` and ``auto_layout`` are normally
        mutually exclusive (constrained-layout owns the margins). The
        dartwork contract is: ``auto_layout`` may not crash when both
        are active, even if it has nothing to optimize. It must return
        cleanly and leave the figure in a renderable state."""
        fig, ax = plt.subplots(figsize=(6, 4), constrained_layout=True)
        ax.plot([1, 2, 3])
        ax.set_ylabel("Value")
        ax.set_xlabel("Index")
        # Must not raise.
        auto_layout(fig)
        # The figure must still render without error.
        fig.canvas.draw()
        plt.close(fig)


class TestAutoLayoutDatetime:
    """Regressions for datetime-tick figures."""

    def test_datetime_xaxis_converges_under_max_iter(self) -> None:
        """A 5-year daily-resolution datetime x-axis must converge in
        ≤ 5 iterations to ≤ 2 px overflow on every side."""
        import numpy as np
        import pandas as pd

        import dartwork_mpl as dm

        fig, ax = dm.subplots(width="13cm", aspect="standard")
        dates = pd.date_range("2021-01-01", "2025-12-31", freq="D")
        rng = np.random.default_rng(42)
        ax.plot(dates, np.cumsum(rng.standard_normal(len(dates))))
        ax.set_ylabel("Value")
        fig.autofmt_xdate()

        auto_layout(fig, max_iter=5)

        overflow = _measure_overflow(fig)
        assert max(overflow.values()) <= 2.0, (
            f"datetime auto_layout did not converge: {overflow}"
        )
        plt.close(fig)


class TestAutoLayoutSymmetry:
    """auto_layout should leave both horizontal and vertical margins
    balanced (within MARGIN_ASYMMETRY's 3x ratio threshold)."""

    def test_extreme_left_squeeze_recovers(self) -> None:
        """A figure squeezed into the left 25% of the canvas should be
        re-centred by auto_layout."""
        from dartwork_mpl.validate import validate_figure

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.barh([0, 1, 2], [1, 2, 3])
        ax.set_ylabel("Y")
        ax.set_xlabel("X")
        fig.subplots_adjust(left=0.05, right=0.30)

        auto_layout(fig)

        warnings = validate_figure(
            fig, checks=("MARGIN_ASYMMETRY",), quiet=True
        )
        asym = [w for w in warnings if w.check_id == "MARGIN_ASYMMETRY"]
        assert len(asym) == 0, f"Asymmetry remains: {[w.message for w in asym]}"
        plt.close(fig)
