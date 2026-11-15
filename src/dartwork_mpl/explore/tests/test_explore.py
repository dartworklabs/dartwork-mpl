"""Tests for the Model B exploration namespace."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl import explore


def test_explore_lists_model_b_families() -> None:
    assert explore.list_colors() == dm.list_colors()
    assert len(explore.list_colors(kind="qualitative")) == 13
