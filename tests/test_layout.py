"""Tests for layout module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from dartwork_mpl.layout import get_bounding_box, simple_layout
from dartwork_mpl.layout import auto_layout, _measure_overflow


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
        ax1.set_ylabel("Left Axis (억원)")

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

