"""Tick labels someone fixed stay on the ticks they were made for.

``ax.set_xticklabels(ax.get_xticklabels(), rotation=45)``, a common way to
rotate labels, freezes the current label texts in a ``FixedFormatter``,
which labels the ticks by order, under matplotlib's own locator. On annual
data ``dm.simple_layout`` put its whole-year locator under them, so every
label moved to another tick: a 17 cm axis over 2005-2024 read ``2007.5`` at
2010, ``2010.0`` at 2015 and ``2012.5`` at 2020 (diagnosis D, S1,
2026-11-06). Labels someone fixed are theirs: the layout keeps the ticks
under them.
"""

from __future__ import annotations

import warnings

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._years import WholeYearLocator, YearTickFormatter


@pytest.fixture(autouse=True)
def _report_preset():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _on(axis) -> tuple[list[float], list[str]]:
    """In-view major tick locations and texts of ``axis``, after a draw."""
    axis.axes.get_figure(root=True).canvas.draw()
    low, high = sorted(axis.get_view_interval())
    pairs = [
        (float(loc), label.get_text())
        for loc, label in zip(
            axis.get_majorticklocs(), axis.get_majorticklabels(), strict=True
        )
        if low <= loc <= high
    ]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def _number(text: str) -> float:
    return float(text.replace(",", "").replace("\N{MINUS SIGN}", "-"))


def _misplaced(axis) -> list[tuple[float, str]]:
    """Labels that print another tick's value than their own."""
    locs, labels = _on(axis)
    return [
        (loc, text)
        for loc, text in zip(locs, labels, strict=True)
        if text and _number(text) != pytest.approx(loc)
    ]


def _fix_labels(axis, **text) -> None:
    """The idiom: give the axis its own current labels back."""
    with warnings.catch_warnings():
        # matplotlib: "set_ticklabels() should only be used with a fixed
        # number of ticks", the reason the labels can move at all
        warnings.simplefilter("ignore", UserWarning)
        axis.set_ticklabels(axis.get_ticklabels(), **text)


@pytest.mark.parametrize("draw_first", [False, True])
def test_rotation_idiom_keeps_the_years_on_their_ticks(draw_first):
    """The reported case: 17 cm, 2005-2024, labels rotated by the idiom."""
    fig, ax = plt.subplots(figsize=dm.figsize("17cm", "standard"))
    years = np.arange(2005, 2025)
    ax.plot(years, np.arange(len(years)))
    if draw_first:
        fig.canvas.draw()
    _fix_labels(ax.xaxis, rotation=45)
    fixed = ax.xaxis.get_major_formatter()
    dm.simple_layout(fig)
    assert ax.xaxis.get_major_formatter() is fixed
    assert not isinstance(ax.xaxis.get_major_locator(), WholeYearLocator)
    locs, labels = _on(ax.xaxis)
    assert len(locs) >= 2 and all(labels), (locs, labels)
    assert _misplaced(ax.xaxis) == [], _on(ax.xaxis)
    assert all(t.get_rotation() == 45 for t in ax.get_xticklabels())


def test_fixed_labels_on_a_y_year_axis_stay_on_their_ticks():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.barh(np.arange(2014, 2025), np.arange(11) + 1)
    _fix_labels(ax.yaxis)
    dm.simple_layout(fig)
    assert not isinstance(ax.yaxis.get_major_locator(), WholeYearLocator)
    assert _misplaced(ax.yaxis) == [], _on(ax.yaxis)


def test_pinned_ticks_with_their_own_labels_are_kept():
    """``set_xticks`` then ``set_xticklabels``: matplotlib's own pairing."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    years = np.arange(2005, 2025)
    ax.plot(years, np.arange(len(years)))
    ax.set_xticks([2005, 2010, 2015, 2020])
    ax.set_xticklabels(["FY05", "FY10", "FY15", "FY20"], rotation=45)
    dm.simple_layout(fig)
    assert isinstance(ax.xaxis.get_major_locator(), mticker.FixedLocator)
    assert _on(ax.xaxis) == (
        [2005.0, 2010.0, 2015.0, 2020.0],
        ["FY05", "FY10", "FY15", "FY20"],
    )


def test_rotation_by_tick_params_keeps_the_year_defaults():
    """``tick_params(rotation=...)`` rotates without fixing any text."""
    fig, ax = plt.subplots(figsize=dm.figsize("17cm", "standard"))
    years = np.arange(2005, 2025)
    ax.plot(years, np.arange(len(years)))
    ax.tick_params(axis="x", rotation=45)
    dm.simple_layout(fig)
    assert isinstance(ax.xaxis.get_major_locator(), WholeYearLocator)
    assert isinstance(ax.xaxis.get_major_formatter(), YearTickFormatter)
    locs, labels = _on(ax.xaxis)
    assert len(locs) >= 2 and all(v == round(v) for v in locs), locs
    assert labels == [f"{round(v) % 100:02d}" for v in locs], labels
    assert all(t.get_rotation() == 45 for t in ax.get_xticklabels())


def test_fixed_labels_on_a_number_axis_keep_their_formatter():
    """The library's numbers never replace labels someone fixed."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot(np.arange(60), np.linspace(1500, 2400, 60))
    _fix_labels(ax.yaxis)
    fixed = ax.yaxis.get_major_formatter()
    dm.simple_layout(fig)
    assert ax.yaxis.get_major_formatter() is fixed
    assert _misplaced(ax.yaxis) == [], _on(ax.yaxis)


FIXED_CASES = [
    # (x data, y data, axis)
    (np.arange(2005, 2025), None, "x"),
    (np.arange(1995, 2025), None, "x"),
    (np.arange(2011, 2025), None, "x"),
    (np.linspace(0, 5000, 20), None, "x"),
    (np.linspace(0, 1, 20), None, "x"),
    (None, np.linspace(1500, 2400, 20), "y"),
    (None, np.linspace(-37, 412, 20), "y"),
]


@pytest.mark.parametrize("width", ["6cm", "9cm", "12cm", "17cm"])
@pytest.mark.parametrize("preset", ["report", "scientific"])
def test_fixed_labels_survive_the_refit_at_every_width(preset, width):
    """The refit changes the axis length, and with it matplotlib's ticks.

    Matplotlib's locator picks its tick count from the axis length, so a
    refit 9 cm axis over 2005-2024 ticked every 5 years where the labels
    were made for 2.5-year steps (``2010`` at 2007.5), and a 6 cm one over
    0-5,000 put ``2000`` at 1,000; years and other numbers alike. The
    ticks the texts were made for are pinned before the refit.
    """
    for x, y, which in FIXED_CASES:
        for aspect in ("standard", "wide"):
            dm.style.use(preset)
            fig, ax = plt.subplots(figsize=dm.figsize(width, aspect))
            if x is None:
                x = np.arange(len(y))
            if y is None:
                y = np.arange(len(x))
            ax.plot(x, y)
            axis = ax.xaxis if which == "x" else ax.yaxis
            made_for = list(axis.get_majorticklocs())
            _fix_labels(axis, rotation=45 if which == "x" else 0)
            dm.simple_layout(fig)
            case = (preset, width, aspect, which, x[0], _on(axis))
            assert _misplaced(axis) == [], case
            assert list(axis.get_majorticklocs()) == made_for, case
            plt.close(fig)


def test_fixed_labels_made_for_other_ticks_are_left_alone():
    """Texts that no longer match the ticks in number: nothing to keep."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot(np.linspace(0, 5000, 20), np.arange(20))
    _fix_labels(ax.xaxis)
    ax.set_xlim(0, 1200)  # the view moved after the texts were taken
    dm.simple_layout(fig)
    assert type(ax.xaxis.get_major_locator()) is mticker.AutoLocator


def test_labels_fixed_after_the_layout_are_not_thinned():
    """A second layout does not thin the year ticks under fixed labels.

    Thinning lowers the whole-year tick count; fixed labels would then
    print other ticks' years.
    """
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    years = np.arange(1995, 2025)
    ax.plot(years, np.arange(len(years)))
    dm.simple_layout(fig)
    locs, labels = _on(ax.xaxis)
    # 20 pt labels are too wide for 1995 … 2025: thinning would keep
    # 2000, 2010, 2020 and the fixed texts would read 95, 00, 05 there
    _fix_labels(ax.xaxis, fontsize=20)
    dm.simple_layout(fig)
    assert _on(ax.xaxis) == (locs, labels)
