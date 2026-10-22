"""Tests for the public dartwork_mpl.diagnostics entry and its font preview.

The colour and colormap helpers are tested next to their code in
``src/dartwork_mpl/_colors/diagnostics/tests/``; this file keeps the font
preview and the public re-export surface (the legacy
``dartwork_mpl.asset_viz`` path was removed in 0.5.4).
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

matplotlib.use("Agg")


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


class TestDiagnosticsExports:
    """Diagnostics keep renamed helpers in the diagnostics namespace."""

    def test_diagnostics_exposes_renamed_helpers(self) -> None:
        import dartwork_mpl as dm
        from dartwork_mpl import diagnostics

        assert not hasattr(dm, "classify_cmap")
        assert callable(diagnostics.classify_cmap)
        assert callable(diagnostics.render_cmap_catalog)
        assert callable(diagnostics.render_color_catalog)
        assert dm.plot_fonts is diagnostics.plot_fonts

    def test_explore_keeps_font_preview(self) -> None:
        from dartwork_mpl import diagnostics, explore

        assert explore.plot_fonts is diagnostics.plot_fonts
