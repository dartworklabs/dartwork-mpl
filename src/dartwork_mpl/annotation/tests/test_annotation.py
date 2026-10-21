"""Tests for annotation module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.annotation import (
    annotate_corner,
    annotate_value,
    arrow_axis,
    label_axes,
    label_hline,
    place_legend,
    wrap_axis_label,
    wrap_axis_labels,
)


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


class TestAnnotateValue:
    def test_default_places_label_above_point(self) -> None:
        fig, ax = plt.subplots()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        text = annotate_value(ax, 0.5, 0.5, "0.5")

        assert text.get_text() == "0.5"
        assert text.get_horizontalalignment() == "center"
        assert text.get_verticalalignment() == "bottom"
        assert text.get_fontsize() == dm.fs(-2)
        plt.close(fig)

    def test_auto_flips_below_axes_top(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.set_ylim(0, 1)
        ax.plot([0, 1], [0.98, 0.98])

        text = annotate_value(ax, 0.5, 0.98, "near top")

        assert text.get_verticalalignment() == "center"
        assert text.get_horizontalalignment() == "left"
        assert text.xyann == (3.0, 0.0)
        plt.close(fig)

    def test_explicit_below_uses_negative_vertical_offset(self) -> None:
        fig, ax = plt.subplots()
        text = annotate_value(ax, 0.5, 0.5, "below", side="below")

        assert text.get_verticalalignment() == "top"
        assert text.xyann == (0.0, -3.0)
        plt.close(fig)

    def test_explicit_horizontal_side_supports_straight_arrow(self) -> None:
        fig, ax = plt.subplots()

        text = annotate_value(
            ax, 0.5, 0.5, "left", side="left", arrowprops={"arrowstyle": "-"}
        )

        assert text.get_horizontalalignment() == "right"
        assert text.get_verticalalignment() == "center"
        assert text.xyann == (-3.0, 0.0)
        assert text.arrow_patch is not None
        plt.close(fig)


class TestAnnotateCorner:
    def test_annotate_corner_places_text_tight_to_requested_corner(
        self,
    ) -> None:
        fig, ax = plt.subplots()

        text = annotate_corner(
            ax, "note", loc="lower right", avoid_overlap=False
        )

        assert text.xy == (1.0, 0.0)
        assert text.xyann == (-3.0, 3.0)
        assert text.get_horizontalalignment() == "right"
        assert text.get_verticalalignment() == "bottom"
        plt.close(fig)

    def test_annotate_corner_avoids_existing_corner_text(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(
            0.02,
            0.98,
            "occupied",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=18,
        )

        text = annotate_corner(ax, "note")

        assert text.xy == (1.0, 1.0)
        assert text.get_horizontalalignment() == "right"
        assert text.get_verticalalignment() == "top"
        plt.close(fig)


class TestLabelHLine:
    def test_label_hline_sits_close_above_reference_line(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.set_ylim(0, 1)
        ax.axhline(0.5)

        text = label_hline(ax, 0.5, "reference")
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        line_y = ax.transData.transform((0.0, 0.5))[1]
        bbox = text.get_window_extent(renderer)

        assert text.get_verticalalignment() == "bottom"
        assert text.get_horizontalalignment() == "right"
        assert 0 <= bbox.y0 - line_y <= 6
        plt.close(fig)

    def test_label_hline_supports_below_side(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.set_ylim(0, 1)

        text = label_hline(ax, 0.5, "below", side="below", x="left")
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        line_y = ax.transData.transform((0.0, 0.5))[1]
        bbox = text.get_window_extent(renderer)

        assert text.get_verticalalignment() == "top"
        assert text.get_horizontalalignment() == "left"
        assert 0 <= line_y - bbox.y1 <= 6
        plt.close(fig)

    def test_label_hline_defaults_to_visible_line_right_endpoint(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.plot([0.2, 0.8], [0.5, 0.5])

        text = label_hline(ax, 0.5, "end")

        assert abs(text.xy[0] - 0.8) < 0.01
        assert text.get_horizontalalignment() == "right"
        plt.close(fig)

    def test_label_hline_auto_chooses_unoccupied_endpoint(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.plot([0.0, 1.0], [0.5, 0.5])
        ax.text(
            0.98,
            0.5,
            "right busy",
            transform=ax.get_yaxis_transform(),
            ha="right",
            va="center",
            fontsize=18,
        )

        text = label_hline(ax, 0.5, "auto", x="auto")

        assert text.get_horizontalalignment() == "left"
        assert abs(text.xy[0] - 0.0) < 0.01
        plt.close(fig)


class TestPlaceLegend:
    def test_place_legend_chooses_empty_upper_right_candidate(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        rectangles = [
            Rectangle((0.00, 0.62), 0.36, 0.36, label="occupied"),
            Rectangle((0.00, 0.00), 0.36, 0.36),
            Rectangle((0.62, 0.00), 0.36, 0.36),
            Rectangle((0.35, 0.62), 0.30, 0.36),
        ]
        for rect in rectangles:
            ax.add_patch(rect)

        legend = place_legend(ax)

        assert legend is not None
        assert legend._loc == 1  # upper right
        plt.close(fig)

    def test_place_legend_repositions_existing_legend(self) -> None:
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1], label="series")
        ax.legend(loc="lower left")

        legend = place_legend(ax, loc="upper right")

        assert legend is ax.get_legend()
        assert legend._loc == 1
        plt.close(fig)

    def test_place_legend_avoids_existing_text_obstacle(self) -> None:
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.plot([0, 1], [0.1, 0.2], label="series")
        ax.add_patch(Rectangle((0.0, 0.0), 0.25, 0.25))
        ax.text(
            0.98,
            0.98,
            "callout",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=20,
        )

        legend = place_legend(ax)

        assert legend is not None
        assert legend._loc == 2  # upper left
        plt.close(fig)

    def test_place_legend_raises_ncol_for_tall_legend(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 2))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        for index in range(9):
            ax.plot(
                [0.05, 0.15],
                [0.05 + index * 0.02, 0.08 + index * 0.02],
                label=f"Series {index}",
            )
        ax.add_patch(Rectangle((0.45, 0.2), 0.10, 0.60))

        legend = place_legend(ax)

        assert legend is not None
        assert legend._ncols > 1
        plt.close(fig)

    def test_public_exports(self) -> None:
        assert dm.annotate_value is annotate_value
        assert dm.annotate_corner is annotate_corner
        assert dm.label_hline is label_hline
        assert dm.place_legend is place_legend
        assert dm.wrap_axis_label is wrap_axis_label
        assert dm.wrap_axis_labels is wrap_axis_labels


class TestWrapAxisLabel:
    def test_wrap_axis_label_splits_long_ylabel_without_breaking_unit(
        self,
    ) -> None:
        fig, ax = plt.subplots(figsize=(3, 2))
        ax.set_ylabel("Very long response measurement (unit)")

        wrapped = wrap_axis_label(ax, axis="y", max_frac=0.5)

        assert wrapped is True
        assert ax.get_ylabel().count("\n") == 1
        assert ax.get_ylabel().split("\n")[1].endswith("(unit)")
        plt.close(fig)

    def test_wrap_axis_label_leaves_short_label_unchanged(self) -> None:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.set_xlabel("Time")

        wrapped = wrap_axis_label(ax, axis="x")

        assert wrapped is False
        assert ax.get_xlabel() == "Time"
        plt.close(fig)

    def test_wrap_axis_labels_applies_to_all_axes(self) -> None:
        fig, axes = plt.subplots(1, 2, figsize=(5, 2))
        axes[0].set_ylabel("Very long response measurement (unit)")
        axes[1].set_ylabel("Short")

        wrapped = wrap_axis_labels(fig, axis="y", max_frac=0.5)

        assert wrapped == [axes[0].yaxis.label]
        assert "\n" in axes[0].get_ylabel()
        assert "\n" not in axes[1].get_ylabel()
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
