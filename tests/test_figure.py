"""Tests for dartwork_mpl.figure (dm.subplots / dm.figure)."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

matplotlib.use("Agg")

import dartwork_mpl as dm


class TestSubplots:
    """Tests for ``dm.subplots``."""

    def test_default_returns_figure_and_axes(self) -> None:
        fig, ax = dm.subplots()
        assert isinstance(fig, Figure)
        assert isinstance(ax, Axes)
        plt.close(fig)

    def test_grid_returns_axes_array(self) -> None:
        fig, axes = dm.subplots(2, 3)
        assert isinstance(fig, Figure)
        assert isinstance(axes, np.ndarray)
        assert axes.shape == (2, 3)
        plt.close(fig)

    def test_with_style_preset(self) -> None:
        """Passing style='scientific' should not raise and should give a Figure."""
        fig, ax = dm.subplots(style="scientific")
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_figsize_and_dpi_forwarded(self) -> None:
        fig, _ax = dm.subplots(figsize=(6.4, 4.8), dpi=150)
        assert fig.get_size_inches().tolist() == [6.4, 4.8]
        assert fig.dpi == 150
        plt.close(fig)

    def test_squeeze_false_always_returns_array(self) -> None:
        fig, axes = dm.subplots(squeeze=False)
        assert isinstance(axes, np.ndarray)
        assert axes.shape == (1, 1)
        plt.close(fig)

    def test_invalid_style_raises(self) -> None:
        """A non-str, non-list style argument should fail loudly."""
        with pytest.raises((ValueError, TypeError)):
            dm.subplots(style=42)  # type: ignore[arg-type]


class TestFigure:
    """Tests for ``dm.figure``."""

    def test_default_returns_figure(self) -> None:
        fig = dm.figure()
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_with_style_preset(self) -> None:
        fig = dm.figure(style="scientific")
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_figsize_override(self) -> None:
        fig = dm.figure(figsize=(3.0, 2.0), dpi=100)
        assert fig.get_size_inches().tolist() == [3.0, 2.0]
        assert fig.dpi == 100
        plt.close(fig)
