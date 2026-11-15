"""Realistic charts through the public surface, beyond the tick-text table."""

from __future__ import annotations

from collections.abc import Iterator

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pytest
from matplotlib.axis import Axis

import dartwork_mpl as dm
from dartwork_mpl.ticks import (
    drawn_like_twin,
    remember_dates,
    settled_twin_spines,
    thin_dates,
)
from dartwork_mpl.ticks.model import RightSide

MONTHS = np.arange("2019-01", "2025-01", dtype="datetime64[M]")


@pytest.fixture
def figure() -> Iterator[plt.Figure]:
    dm.style.use("report")
    fig, _ = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    yield fig
    plt.close(fig)


def _shown(axis: Axis) -> list[str]:
    lo, hi = sorted(axis.get_view_interval())
    return [
        t.label1.get_text() or t.label2.get_text()
        for t in axis.get_major_ticks()
        if lo - 1e-9 <= t.get_loc() <= hi + 1e-9
    ]


def test_a_twin_scale_gets_its_spine_once(figure):
    ax = figure.axes[0]
    ax.plot(MONTHS[:12], np.arange(12))
    twin = ax.twinx()
    twin.plot(MONTHS[:12], np.arange(12) * 1000.0, color="C1")
    dm.simple_layout(figure)
    assert twin.spines["right"].get_visible()
    assert not ax.spines["right"].get_visible()
    assert settled_twin_spines(twin) == {RightSide()} and drawn_like_twin(twin)
    twin.spines["right"].set_visible(False)  # hidden after a layout: kept
    dm.simple_layout(figure)
    assert not twin.spines["right"].get_visible()


def test_an_inset_twin_gets_its_spine(figure):
    inset = figure.axes[0].inset_axes((0.55, 0.15, 0.35, 0.35))
    twin = inset.twinx()
    twin.plot([0, 1, 2], [30, 10, 20])
    dm.simple_layout(figure)
    assert twin.spines["right"].get_visible()


def test_crowded_dates_thin_and_are_put_back(figure):
    ax = figure.axes[0]
    ax.plot(MONTHS[48:66], np.arange(18))
    figure.set_size_inches(2.0, 2)
    put_back = remember_dates(figure)
    dm.simple_layout(figure, margin=0)  # prepare, fit, then thin
    assert _shown(ax.xaxis) == ["23.01", "23.05", "23.09", "24.01", "24.05"]
    assert thin_dates(figure) is False  # thinned already
    put_back()
    figure.canvas.draw()
    assert len(_shown(ax.xaxis)) > 5


def test_texts_fixed_by_order_keep_their_ticks(figure):
    ax = figure.axes[0]
    ax.plot(np.arange(2005, 2016) + 0.5, np.arange(11))
    figure.canvas.draw()
    locs = list(ax.get_xticks())
    with pytest.warns(UserWarning, match="FixedLocator"):
        ax.set_xticklabels(
            [t.get_text() for t in ax.get_xticklabels()], rotation=45
        )
    dm.simple_layout(figure)
    assert list(ax.get_xticks()) == locs


def test_formatters_someone_set_are_kept(figure):
    ax = figure.axes[0]
    ax.plot([0, 1, 2], [0, 5000, 10000])
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(10000))
    ax.ticklabel_format(axis="x", style="sci", scilimits=(0, 0))
    dm.simple_layout(figure)
    assert _shown(ax.yaxis)[-1] == "100%"
    assert type(ax.xaxis.get_major_formatter()) is mticker.ScalarFormatter


def test_an_hourly_axis_does_not_repeat_its_date(figure):
    ax = figure.axes[0]
    hours = np.arange("2024-03-01T00", "2024-03-03T00", dtype="datetime64[h]")
    ax.plot(hours, np.arange(len(hours)))
    dm.simple_layout(figure)
    figure.canvas.draw()
    assert "24.03.02" in _shown(ax.xaxis)
    assert ax.xaxis.get_offset_text().get_text() == ""
