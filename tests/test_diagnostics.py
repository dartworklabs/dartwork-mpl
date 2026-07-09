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

    def test_v5_catalog_categories(self) -> None:
        """Every v5 colormap classifies into its true taxonomy bucket.

        The HSV heuristic mislabels the v5 maps (single-hue family ramps look
        multi-hue, warm scenes look single-hue), so the taxonomy is pinned in
        ``_CLASSIFICATION_OVERRIDES``. Expected categories here are stated
        independently of that dict — this is the regression guard.
        """
        import dartwork_mpl  # noqa: F401 — registers the v5 catalog
        from dartwork_mpl.colors._generated import CMAPS_256
        from dartwork_mpl.diagnostics import classify_colormap

        expected = {
            **dict.fromkeys(
                (
                    "red",
                    "rose",
                    "coral",
                    "tangerine",
                    "orange",
                    "amber",
                    "yellow",
                    "lime",
                    "green",
                    "teal",
                    "cyan",
                    "sky",
                    "blue",
                    "cobalt",
                    "indigo",
                    "violet",
                    "purple",
                    "fuchsia",
                    "pink",
                    "gray",
                ),
                "Single-Hue",
            ),
            **dict.fromkeys(
                (
                    "aurora",
                    "afterglow",
                    "blaze",
                    "lava",
                    "lagoon",
                    "glacier",
                    "canopy",
                    "haze",
                    "iris",
                ),
                "Multi-Hue",
            ),
            **dict.fromkeys(
                (
                    "blue_red",
                    "blue_orange",
                    "teal_rose",
                    "green_purple",
                    "purple_orange",
                    "cyan_red",
                    "teal_amber",
                    "violet_lime",
                    "indigo_amber",
                    "gray_blue",
                    "gray_red",
                ),
                "Diverging",
            ),
            **dict.fromkeys(("hue", "halo", "corona"), "Cyclical"),
        }
        # every generated map has a stated expectation.
        assert set(CMAPS_256) <= set(expected)
        for name, want in expected.items():
            got = classify_colormap(matplotlib.colormaps[f"dc.{name}"])
            assert got == want, f"dc.{name}: {got} != {want}"
        # the registered qualitative cycles read as categorical
        for name in ("octave", "octave_print"):
            assert (
                classify_colormap(matplotlib.colormaps[f"dc.{name}"])
                == "Categorical"
            )


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


class TestClassificationOverridesParity:
    """``_CLASSIFICATION_OVERRIDES`` must stay 1:1 with every real dartwork
    colormap — a new/renamed map without an explicit class falls back to the
    heuristic, which misclassified 7 of the 8 maps that were missing before
    this guard. The v5 catalog (``colors._generated.CMAPS_256`` + the two
    registered cycles) is the only dartwork colormap surface."""

    def test_overrides_match_bundled_cmaps_exactly(self) -> None:
        import dartwork_mpl.diagnostics._colormaps as dcm
        from dartwork_mpl.colors._generated import CMAPS_256

        v5 = {f"dc.{n}" for n in CMAPS_256} | {"dc.octave", "dc.octave_print"}
        expected = v5
        overrides = set(dcm._CLASSIFICATION_OVERRIDES)
        assert overrides == expected, (
            f"missing: {sorted(expected - overrides)}; "
            f"stale: {sorted(overrides - expected)}"
        )


class TestClassifyColormapAudit:
    """2026-07 audit: Spectral is diverging, not categorical."""

    def test_spectral_is_not_categorical(self) -> None:
        import matplotlib

        from dartwork_mpl.diagnostics import classify_colormap

        assert (
            classify_colormap(matplotlib.colormaps["Spectral"]) != "Categorical"
        )

    def test_dead_opencolor_names_removed(self) -> None:
        import dartwork_mpl.diagnostics._colors as colors_mod

        assert not hasattr(colors_mod, "_OPENCOLOR_NAMES")
