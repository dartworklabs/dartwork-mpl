"""Tests for layout module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from dartwork_mpl.layout import get_bounding_box, simple_layout


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
