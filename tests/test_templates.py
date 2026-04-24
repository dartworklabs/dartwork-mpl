"""Tests for dartwork_mpl.templates (formerly dartwork_mpl.xplot)."""

from __future__ import annotations

import warnings

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

matplotlib.use("Agg")

from dartwork_mpl.templates import plot_diverging_bar


class TestPlotDivergingBar:
    """Tests for ``plot_diverging_bar()``."""

    def test_default_data(self) -> None:
        """Calling with no args should use default sample data."""
        fig, ax = plot_diverging_bar()
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        plt.close(fig)

    def test_custom_data(self) -> None:
        fig, ax = plot_diverging_bar(
            labels=["A", "B", "C"],
            neg_values=np.array([-30, -15, -25]),
            pos_values=np.array([40, 55, 35]),
        )
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        plt.close(fig)

    def test_no_total(self) -> None:
        fig, ax = plot_diverging_bar(
            labels=["X"],
            neg_values=np.array([-10]),
            pos_values=np.array([20]),
            add_total=False,
        )
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestXplotDeprecationAlias:
    """The legacy ``dartwork_mpl.xplot`` path must keep working.

    Until a future major release removes the backward-compatibility
    shim, ``dartwork_mpl.xplot.plot_diverging_bar`` must still resolve
    to the same callable as ``dartwork_mpl.templates.plot_diverging_bar``,
    and attribute access (``dm.xplot``) must emit a
    ``DeprecationWarning``.
    """

    def test_legacy_submodule_import_still_works(self) -> None:
        """``from dartwork_mpl.xplot import plot_diverging_bar`` resolves."""
        from dartwork_mpl.templates import plot_diverging_bar as canonical
        from dartwork_mpl.xplot import plot_diverging_bar as legacy

        assert legacy is canonical

    def test_attribute_access_emits_deprecation_warning(self) -> None:
        """``dm.xplot`` attribute access must emit ``DeprecationWarning``."""
        import dartwork_mpl as dm

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _ = dm.xplot
        messages = [
            str(w.message)
            for w in caught
            if issubclass(w.category, DeprecationWarning)
        ]
        assert any("xplot is deprecated" in m for m in messages), (
            f"Expected a DeprecationWarning mentioning 'xplot is deprecated'. "
            f"Got: {messages}"
        )
