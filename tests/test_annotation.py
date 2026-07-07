"""Tests for annotation module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from dartwork_mpl.annotation import arrow_axis, label_axes


class TestLabelAxes:
    """Tests for label_axes()."""

    def test_default_labels(self) -> None:
        """Should add (a), (b) labels by default."""
        fig, axes = plt.subplots(1, 2)
        for ax in axes:
            ax.plot([1, 2, 3])

        texts = label_axes(axes)
        assert len(texts) == 2
        assert texts[0].get_text() == "a"
        assert texts[1].get_text() == "b"
        assert texts[0].get_fontweight() == "normal"
        plt.close(fig)

    def test_custom_labels(self) -> None:
        fig, axes = plt.subplots(1, 2)
        for ax in axes:
            ax.plot([1, 2, 3])

        texts = label_axes(axes, labels=["X", "Y"])
        assert texts[0].get_text() == "X"
        assert texts[1].get_text() == "Y"
        plt.close(fig)

    def test_ndarray_axes(self) -> None:
        """Should handle np.ndarray of axes."""
        fig, axes = plt.subplots(2, 2)
        for ax in axes.flat:
            ax.plot([1, 2, 3])

        texts = label_axes(axes)
        assert len(texts) == 4
        plt.close(fig)

    def test_auto_x_with_ylabel(self) -> None:
        """Auto x should detect ylabel presence."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        ax.set_ylabel("Value")

        texts = label_axes([ax])
        assert len(texts) == 1
        plt.close(fig)

    def test_auto_x_without_ylabel(self) -> None:
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        texts = label_axes([ax])
        assert len(texts) == 1
        plt.close(fig)

    def test_explicit_x_position(self) -> None:
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])

        texts = label_axes([ax], x=-0.1)
        assert len(texts) == 1
        plt.close(fig)


class TestArrowAxis:
    """Tests for arrow_axis()."""

    def test_x_direction(self) -> None:
        """Should not crash with direction='x'."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        fig.canvas.draw()

        arrow_axis(ax, "x", "Cost")
        plt.close(fig)

    def test_y_direction(self) -> None:
        """Should not crash with direction='y'."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        fig.canvas.draw()

        arrow_axis(ax, "y", "Quality")
        plt.close(fig)

    def test_custom_labels(self) -> None:
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        fig.canvas.draw()

        arrow_axis(ax, "x", "Price", low="Cheap", high="Expensive")
        plt.close(fig)


class TestConfigSlots:
    """dm.config rejects typo'd attributes (2026-07 audit)."""

    def test_typo_attribute_raises(self) -> None:
        import pytest

        import dartwork_mpl as dm

        with pytest.raises(AttributeError):
            dm.config.adopt_orphan_tick_fonts = False  # plural typo


class TestArrowAxisDirection:
    """arrow_axis validates direction (2026-07 audit)."""

    def test_invalid_direction_raises(self) -> None:
        import matplotlib.pyplot as plt
        import pytest

        import dartwork_mpl as dm

        fig, ax = plt.subplots()
        with pytest.raises(ValueError, match="direction"):
            dm.arrow_axis(ax, "X", "label")
        plt.close(fig)


class TestLabelAxesBeyond26:
    """label_axes labels grids larger than 26 panels (2026-07 audit)."""

    def test_thirty_panels_all_labeled(self) -> None:
        import matplotlib.pyplot as plt

        import dartwork_mpl as dm

        fig, axes = plt.subplots(6, 5)
        flat = axes.flatten()
        texts = dm.label_axes(flat)
        assert len(texts) == 30
        assert texts[26].get_text() == "aa"
        plt.close(fig)
