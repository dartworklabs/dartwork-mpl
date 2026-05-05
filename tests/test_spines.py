"""Tests for dartwork_mpl.spines — spine and grid helpers."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

import dartwork_mpl as dm


def _axes():
    fig, ax = plt.subplots()
    return fig, ax


class TestStyleSpines:
    def test_sets_colour_and_linewidth(self) -> None:
        fig, ax = _axes()
        dm.style_spines(
            ax, color="red", linewidth=2.5, which=["left", "bottom"]
        )
        # Visible spines get the new style
        for side in ("left", "bottom"):
            spine = ax.spines[side]
            assert spine.get_linewidth() == 2.5
        plt.close(fig)


class TestAddGrid:
    def test_add_grid_default(self) -> None:
        fig, ax = _axes()
        dm.add_grid(ax)
        # Grid is now on at least one axis
        plt.close(fig)


class TestMinimalAxes:
    def test_top_and_right_hidden(self) -> None:
        """``minimal_axes`` should leave only left + bottom visible."""
        fig, ax = _axes()
        dm.minimal_axes(ax)
        assert ax.spines["top"].get_visible() is False
        assert ax.spines["right"].get_visible() is False
        assert ax.spines["left"].get_visible() is True
        assert ax.spines["bottom"].get_visible() is True
        plt.close(fig)
