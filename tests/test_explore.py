"""Tests for the Model B exploration namespace."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.figure
import matplotlib.pyplot as plt

import dartwork_mpl as dm
from dartwork_mpl import explore


def test_explore_lists_model_b_families() -> None:
    assert explore.list_colors() == dm.list_colors()
    assert len(explore.list_colors(kind="qualitative")) == 13


def test_explore_preview_returns_figure() -> None:
    fig = explore.show_colors(names=["blue"], n=5)
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
    finally:
        plt.close(fig)
