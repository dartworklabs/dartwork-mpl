"""Tests for xplot module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

matplotlib.use("Agg")

from dartwork_mpl.xplot import plot_diverging_bar


class TestPlotDivergingBar:
    """Tests for plot_diverging_bar()."""

    def test_default_data(self) -> None:
        """Calling with no args should use default sample data."""
        fig, ax = plot_diverging_bar()
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        plt.close(fig)

    def test_custom_data(self) -> None:
        import numpy as np

        fig, ax = plot_diverging_bar(
            labels=["A", "B", "C"],
            neg_values=np.array([-30, -15, -25]),
            pos_values=np.array([40, 55, 35]),
        )
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        plt.close(fig)

    def test_no_total(self) -> None:
        import numpy as np

        fig, ax = plot_diverging_bar(
            labels=["X"],
            neg_values=np.array([-10]),
            pos_values=np.array([20]),
            add_total=False,
        )
        assert isinstance(fig, Figure)
        plt.close(fig)
