"""Tests for dartwork_mpl.templates (formerly dartwork_mpl.xplot, removed in 0.4.x)."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
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


class TestXplotRemoval:
    """``dartwork_mpl.xplot`` was deprecated in 0.4.0 and removed in 0.4.x."""

    def test_legacy_submodule_import_raises(self) -> None:
        """``from dartwork_mpl.xplot import …`` must now raise ModuleNotFoundError."""
        with pytest.raises(ModuleNotFoundError):
            import dartwork_mpl.xplot  # noqa: F401

    def test_attribute_access_raises(self) -> None:
        """``dm.xplot`` attribute access must now raise AttributeError."""
        import dartwork_mpl as dm

        with pytest.raises(AttributeError, match="xplot"):
            _ = dm.xplot
