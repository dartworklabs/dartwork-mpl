"""Tests for dartwork_mpl.diagnostics (color, font, colormap helpers).

These four helpers used to live under ``dartwork_mpl.asset_viz``; that
legacy import path was removed in 0.5.4. Here we exercise the canonical
:mod:`dartwork_mpl.diagnostics` import path.
"""

from __future__ import annotations

from unittest.mock import patch

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

matplotlib.use("Agg")


class TestPlotColors:
    """Tests for plot_colors()."""

    def test_returns_list_of_figures(self) -> None:
        """plot_colors() returns a non-empty list of Figure."""
        from dartwork_mpl.diagnostics import plot_colors

        figs = plot_colors()
        assert isinstance(figs, list)
        assert len(figs) > 0
        for fig in figs:
            assert isinstance(fig, Figure)
        for fig in figs:
            plt.close(fig)

    def test_custom_dict(self) -> None:
        """plot_colors() works with a custom color dict."""
        from dartwork_mpl.diagnostics import plot_colors

        custom = {
            "oc.red0": "#fff5f5",
            "oc.red5": "#ff6b6b",
            "tw.blue500": "#3b82f6",
        }
        figs = plot_colors(custom, ncols=2)
        assert isinstance(figs, list)
        assert len(figs) > 0
        for fig in figs:
            plt.close(fig)

    def test_show_hex_false(self) -> None:
        """plot_colors(show_hex=False) still returns figures."""
        from dartwork_mpl.diagnostics import plot_colors

        figs = plot_colors({"oc.red0": "#fff5f5"}, show_hex=False)
        assert len(figs) > 0
        for fig in figs:
            plt.close(fig)

    def test_empty_dict_returns_empty(self) -> None:
        """plot_colors({}) returns an empty list."""
        from dartwork_mpl.diagnostics import plot_colors

        figs = plot_colors({})
        assert figs == []

    def test_sort_colors_false_does_not_crash(self) -> None:
        """plot_colors(sort_colors=False) must not raise (regression: #225)."""
        from dartwork_mpl.diagnostics import plot_colors

        figs = plot_colors(
            {"oc.red0": "#fff5f5", "oc.red5": "#ff6b6b"}, sort_colors=False
        )
        assert len(figs) > 0
        for fig in figs:
            plt.close(fig)

    def test_sort_colors_true_orders_swatches_by_weight(self) -> None:
        """sort_colors=True actually sorts swatches (regression: #225 dead code).

        Input is given out of weight order; the rendered name labels,
        read top-to-bottom, must come back sorted by weight.
        """
        from dartwork_mpl.diagnostics import _plot_single_library

        colors = {
            "oc.red9": "#c92a2a",
            "oc.red0": "#fff5f5",
            "oc.red5": "#ff6b6b",
        }
        fig = _plot_single_library(
            colors, "oc", ncols=1, sort_colors=True, show_hex=False
        )
        assert fig is not None
        # Keep only the swatch name labels (drop the title and count text),
        # then read them top-to-bottom. Axis is inverted, so ascending y is
        # top-to-bottom on screen.
        swatches = [t for t in fig.axes[0].texts if t.get_text() in colors]
        names = [
            t.get_text()
            for t in sorted(swatches, key=lambda t: t.get_position()[1])
        ]
        assert names == ["oc.red0", "oc.red5", "oc.red9"]
        plt.close(fig)


class TestPlotFonts:
    """Tests for plot_fonts()."""

    def test_returns_figure(self) -> None:
        """plot_fonts() returns a Figure."""
        from dartwork_mpl.diagnostics import plot_fonts

        fig = plot_fonts()
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_custom_ncols(self) -> None:
        """plot_fonts(ncols=1) returns a Figure."""
        from dartwork_mpl.diagnostics import plot_fonts

        fig = plot_fonts(ncols=1)
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestPlotColormaps:
    """Tests for plot_colormaps()."""

    def test_returns_list_of_figures(self) -> None:
        """plot_colormaps() returns a list of Figure."""
        from dartwork_mpl.diagnostics import plot_colormaps

        figs = plot_colormaps()
        assert isinstance(figs, list)
        assert len(figs) > 0
        for fig in figs:
            assert isinstance(fig, Figure)
        for fig in figs:
            plt.close(fig)

    def test_no_plt_show_called(self) -> None:
        """plot_colormaps() must not call plt.show()."""
        from dartwork_mpl.diagnostics import plot_colormaps

        with patch.object(plt, "show") as mock_show:
            figs = plot_colormaps(cmap_list=["viridis", "plasma"])
            mock_show.assert_not_called()
        for fig in figs:
            plt.close(fig)

    def test_flat_mode(self) -> None:
        """plot_colormaps(group_by_type=False) returns single fig."""
        from dartwork_mpl.diagnostics import plot_colormaps

        figs = plot_colormaps(
            cmap_list=["viridis", "plasma"], group_by_type=False
        )
        assert isinstance(figs, list)
        assert len(figs) == 1
        for fig in figs:
            plt.close(fig)

    def test_custom_cmap_list(self) -> None:
        """plot_colormaps() works with a custom cmap list."""
        from dartwork_mpl.diagnostics import plot_colormaps

        figs = plot_colormaps(cmap_list=["viridis", "coolwarm", "tab10"])
        assert isinstance(figs, list)
        assert len(figs) > 0
        for fig in figs:
            plt.close(fig)


class TestClassifyColormap:
    """Tests for classify_colormap()."""

    def test_known_categories(self) -> None:
        """Known colormaps should be classified correctly."""
        from dartwork_mpl.diagnostics import classify_colormap

        # Sequential
        result = classify_colormap(matplotlib.colormaps["viridis"])
        assert result in ("Single-Hue", "Multi-Hue")

        # Coolwarm — may classify as diverging or multi-hue
        result = classify_colormap(matplotlib.colormaps["coolwarm"])
        assert result in ("Diverging", "Multi-Hue", "Single-Hue")

        # Categorical
        assert classify_colormap(matplotlib.colormaps["tab10"]) == "Categorical"

    def test_returns_string(self) -> None:
        """classify_colormap always returns a string."""
        from dartwork_mpl.diagnostics import classify_colormap

        result = classify_colormap(matplotlib.colormaps["viridis"])
        assert isinstance(result, str)


class TestTopLevelReexport:
    """The four names must be reachable from the top-level namespace."""

    def test_dm_top_level_exposes_helpers(self) -> None:
        import dartwork_mpl as dm
        from dartwork_mpl import diagnostics

        assert dm.classify_colormap is diagnostics.classify_colormap
        assert dm.plot_colormaps is diagnostics.plot_colormaps
        assert dm.plot_colors is diagnostics.plot_colors
        assert dm.plot_fonts is diagnostics.plot_fonts

    def test_explore_reexport(self) -> None:
        """``dm.explore`` keeps re-exporting the four helpers."""
        from dartwork_mpl import diagnostics, explore

        assert explore.classify_colormap is diagnostics.classify_colormap
        assert explore.plot_colormaps is diagnostics.plot_colormaps
        assert explore.plot_colors is diagnostics.plot_colors
        assert explore.plot_fonts is diagnostics.plot_fonts
