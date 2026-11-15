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
    tick_scale_of,
)
from dartwork_mpl.ticks.model import TickScale

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
    assert settled_twin_spines(twin) == {"right"} and drawn_like_twin(twin)
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


def test_dates_under_bars_thin_by_calendar_steps(figure):
    ax = figure.axes[0]
    months = MONTHS[:24]
    ax.bar(np.arange(24), np.arange(24))
    dm.format_axis_dates(ax, months)
    figure.set_size_inches(2.5, 2)
    dm.simple_layout(figure)
    shown = [t for t in _shown(ax.xaxis) if t]
    assert ax.xaxis.get_major_locator().step in (2, 3, 4, 6, 12)
    assert shown[0] == "19.01"


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


def test_log_axis_ticks_take_their_own_unit(figure):
    ax = figure.axes[0]
    ax.plot([1, 2, 3], [1, 1e3, 1e6])
    ax.set_yscale("log")
    dm.format_axis_si(ax)
    dm.simple_layout(figure)
    assert {"1", "1k", "1M"} <= set(_shown(ax.yaxis))


def test_unit_in_shared_labels_and_a_later_label_is_yours():
    dm.style.use("report")
    fig, (top, bottom) = plt.subplots(
        2, sharex=True, figsize=dm.figsize("13cm", "standard")
    )
    try:
        top.plot([0, 1], [0, 1])
        top.set_xlabel("Energy")
        bottom.set_xlabel("Energy")
        bottom.plot([0, 2e6], [0, 1])
        dm.axis_unit(bottom, "x", label="Energy ({unit}Wh)")
        fig.canvas.draw()
        assert (top.get_xlabel(), bottom.get_xlabel()) == (
            "Energy (M)",
            "Energy (MWh)",
        )
        assert dm.axis_unit_of(bottom, "x") == dm.ticks.Unit(1e6, "M")
        bottom.set_xlabel("Energy in MWh")
        fig.canvas.draw()
        assert bottom.get_xlabel() == "Energy in MWh"
    finally:
        plt.close(fig)


def test_text_reads_like_the_ticks(figure):
    ax = figure.axes[0]
    ax.plot([0, 1], [0, 3e9])
    dm.format_axis_si(ax)
    figure.canvas.draw()
    assert tick_scale_of(ax.yaxis, 3e9) == TickScale(1e9, "", "G")
    dm.format_axis_currency(ax, axis="x")
    assert tick_scale_of(ax.xaxis, 1.0) == TickScale(1.0, "$", "", "affixed")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1))
    assert tick_scale_of(ax.xaxis, 0.5) == TickScale(0.01, "", "%")


def test_a_year_zoom_prints_values_not_rounded_years(figure):
    ax = figure.axes[0]
    ax.plot([2019.0, 2020.0], [0, 1])
    dm.format_axis_year(ax, locale="en", digits=4)
    ax.set_xlim(2019.2, 2019.7)
    dm.simple_layout(figure)
    assert _shown(ax.xaxis)[:2] == ["2019.2", "2019.3"]


def test_an_hourly_axis_does_not_repeat_its_date(figure):
    ax = figure.axes[0]
    hours = np.arange("2024-03-01T00", "2024-03-03T00", dtype="datetime64[h]")
    ax.plot(hours, np.arange(len(hours)))
    dm.simple_layout(figure)
    figure.canvas.draw()
    assert "24.03.02" in _shown(ax.xaxis)
    assert ax.xaxis.get_offset_text().get_text() == ""
