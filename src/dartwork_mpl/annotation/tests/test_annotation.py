"""Tests for annotation module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import pytest
from matplotlib.patches import Rectangle

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.annotation import place_legend
from tests.support.mpl_observe import legend_ncols, pinned_legend_corner


class TestConfigSlots:
    """dm.config rejects typo'd attributes (2026-07 audit)."""

    def test_typo_attribute_raises(self) -> None:

        import dartwork_mpl as dm

        with pytest.raises(AttributeError):
            dm.config.adopt_orphan_tick_fonts = False  # plural typo


class TestPlaceLegend:
    """Legend placement that avoids data and text obstacles and widens tall legends."""

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
        assert pinned_legend_corner(legend) == "upper right"
        plt.close(fig)

    def test_place_legend_repositions_existing_legend(self) -> None:
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1], label="series")
        ax.legend(loc="lower left")

        legend = place_legend(ax, loc="upper right")

        assert legend is ax.get_legend()
        assert pinned_legend_corner(legend) == "upper right"
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
        assert pinned_legend_corner(legend) == "upper left"
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
        assert legend_ncols(legend) > 1
        plt.close(fig)

    def test_public_exports(self) -> None:
        assert dm.place_legend is place_legend
