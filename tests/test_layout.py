"""Tests for layout module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from dartwork_mpl.layout import (
    _measure_overflow,
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
    """Tests for the new direct-calc ``simple_layout``."""

    def test_single_subplot(self) -> None:
        """simple_layout should not raise on a basic figure and must
        return None (the function no longer exposes the optimizer
        result that the legacy scipy-based implementation returned)."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        result = simple_layout(fig)
        assert result is None
        plt.close(fig)

    def test_multi_subplot(self) -> None:
        """simple_layout should handle 2x2 subplots."""
        fig, axes = plt.subplots(2, 2)
        for ax in axes.flat:
            ax.plot([1, 2, 3])
        result = simple_layout(fig)
        assert result is None
        plt.close(fig)

    def test_margin_units(self) -> None:
        """Accepts Length, percentage string, unit string, and bare
        figure-fraction floats."""
        import dartwork_mpl as dm

        for margin in (0, 0.05, "5%", "5mm", dm.cm(0.5), dm.mm(5)):
            fig, ax = plt.subplots()
            ax.plot([1, 2, 3])
            simple_layout(fig, margin=margin)
            plt.close(fig)

    def test_per_side_overrides(self) -> None:
        """``ml/mr/mt/mb`` should override the global ``margin``."""
        import dartwork_mpl as dm

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        simple_layout(fig, margin="2%", ml=dm.mm(5), mr="0%")
        plt.close(fig)

    def test_verbose_mode(self, capsys) -> None:
        """Verbose mode should print layout info."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        simple_layout(fig, verbose=True)
        captured = capsys.readouterr()
        assert "[simple_layout]" in captured.out
        plt.close(fig)


class TestMeasureOverflowLegend:
    """Regression: _measure_overflow must include legend bbox so
    simple_layout can pad for legends positioned outside axes via
    bbox_to_anchor."""

    def test_legend_outside_axes_detected(self) -> None:
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        for i in range(20):
            ax.plot([0, 1], [i, i + 1], label=f"S{i:02d}")
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
        ax.set_ylabel("Y")
        overflow = _measure_overflow(fig)
        assert overflow["right"] > 5.0, (
            f"legend outside axes should contribute right overflow; "
            f"got {overflow}"
        )
        plt.close(fig)

    def test_no_legend_no_extra_overflow(self) -> None:
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        ax.plot([1, 2, 3])
        ax.set_ylabel("Y")
        overflow = _measure_overflow(fig)
        assert all(v == 0.0 for v in overflow.values()), overflow
        plt.close(fig)

    def test_legend_inside_axes_no_overflow(self) -> None:
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        ax.plot([1, 2, 3], label="A")
        ax.legend(loc="best")
        ax.set_ylabel("Y")
        overflow = _measure_overflow(fig)
        assert all(v == 0.0 for v in overflow.values()), overflow
        plt.close(fig)
