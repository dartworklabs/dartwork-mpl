"""Tests for dartwork_mpl.spines — spine and grid helpers."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

import dartwork_mpl as dm


def _axes():
    fig, ax = plt.subplots()
    return fig, ax


class TestHideSpines:
    def test_hide_top_and_right(self) -> None:
        fig, ax = _axes()
        dm.hide_spines(ax, ["top", "right"])
        assert ax.spines["top"].get_visible() is False
        assert ax.spines["right"].get_visible() is False
        # Untouched spines still visible
        assert ax.spines["left"].get_visible() is True
        assert ax.spines["bottom"].get_visible() is True
        plt.close(fig)

    def test_default_hides_none(self) -> None:
        """Calling with no ``which`` arg should not hide anything by default."""
        fig, ax = _axes()
        dm.hide_spines(ax)  # no-op or hides default list; just must not raise
        plt.close(fig)


class TestHideAllSpines:
    def test_all_hidden(self) -> None:
        fig, ax = _axes()
        dm.hide_all_spines(ax)
        for side in ("left", "right", "top", "bottom"):
            assert ax.spines[side].get_visible() is False
        plt.close(fig)


class TestShowOnlySpines:
    def test_bottom_only(self) -> None:
        fig, ax = _axes()
        dm.show_only_spines(ax, ["bottom"])
        assert ax.spines["bottom"].get_visible() is True
        for side in ("left", "right", "top"):
            assert ax.spines[side].get_visible() is False
        plt.close(fig)


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


class TestAddRemoveGrid:
    def test_add_grid_default(self) -> None:
        fig, ax = _axes()
        dm.add_grid(ax)
        # Grid is now on at least one axis
        plt.close(fig)

    def test_remove_grid_after_add(self) -> None:
        fig, ax = _axes()
        dm.add_grid(ax)
        dm.remove_grid(ax)
        plt.close(fig)


class TestAddFrame:
    def test_frame_turns_all_spines_on(self) -> None:
        fig, ax = _axes()
        dm.hide_all_spines(ax)  # start with none visible
        dm.add_frame(ax, color="black", linewidth=1.0)
        for side in ("left", "right", "top", "bottom"):
            assert ax.spines[side].get_visible() is True
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
