"""Year positions on a y axis read as years; values on y never do.

``ax.barh(range(2014, 2025), …)`` read ``2,014 … 2,024`` (thousands
separators on a year) before follow-up F1. On y only artists that place
data AT a y position count as year data: horizontal bars' centres
(grouped too), ``fill_betweenx`` spans, and a ``twiny`` sibling or a
``secondary_yaxis`` following such an axis. Line, scatter and errorbar y
values are quantities: a KRW price of 1,985-2,045 or a headcount of
2,031-2,090 keeps its numbers (review of PR #595, item 1).
"""

from __future__ import annotations

from itertools import pairwise

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._defaults import DefaultNumberFormatter
from dartwork_mpl.formatting._years import WholeYearLocator, YearTickFormatter

YEARS = np.arange(2014, 2025)


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


def _whole(locs) -> bool:
    return all(abs(v - round(v)) < 1e-9 for v in locs)


def _two_digits(locs, suffix="") -> list[str]:
    return [f"{round(v) % 100:02d}{suffix}" for v in locs]


def _assert_years(axis, suffix=""):
    locs, labels = _on(axis)
    assert len(locs) >= 2 and _whole(locs), locs
    assert labels == _two_digits(locs, suffix), labels
    assert not any("," in t for t in labels), labels
    assert isinstance(axis.get_major_formatter(), YearTickFormatter)
    assert isinstance(axis.get_major_locator(), WholeYearLocator)
    assert axis.get_offset_text().get_text() == ""


def _laid_out(draw, preset="report", width="12cm", aspect="standard"):
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize(width, aspect))
    draw(ax)
    dm.simple_layout(fig)
    return ax


@pytest.mark.parametrize("width", ["9cm", "12cm", "17cm"])
def test_horizontal_bars_over_years_read_two_digits(width):
    ax = _laid_out(lambda ax: ax.barh(YEARS, np.arange(11) + 1), width=width)
    _assert_years(ax.yaxis)
    assert not isinstance(ax.xaxis.get_major_formatter(), YearTickFormatter)


def test_korean_horizontal_bars_follow_the_date_style():
    def draw(ax):
        ax.barh(YEARS, np.arange(11) + 1)
        ax.set_xlabel("매출 (억원)")

    _assert_years(_laid_out(draw, preset="report-kr").yaxis)
    with dm.config.override(date_style="concise"):
        _assert_years(_laid_out(draw, preset="report-kr").yaxis, "년")


@pytest.mark.parametrize("series", [2, 3])
def test_grouped_horizontal_bars_read_as_years(series):
    height = 0.8 / series

    def draw(ax):
        for i in range(series):
            offset = (i - (series - 1) / 2) * height
            ax.barh(YEARS + offset, np.arange(11) + i + 1, height=height)

    _assert_years(_laid_out(draw).yaxis)


def test_fill_betweenx_spans_over_years_read_two_digits():
    _assert_years(
        _laid_out(lambda ax: ax.fill_betweenx(YEARS, 0, np.arange(11))).yaxis
    )


MONTHS = np.arange(12)
# A small-cap share price in KRW and a headcount: integers in 1900-2099.
PRICE = np.array(
    [1985, 1990, 2010, 2045, 2030, 2060, 2080, 2075, 2040, 2020, 2005, 1995]
)
HEADCOUNT = np.arange(2031, 2091, 5)


@pytest.mark.parametrize(
    "draw",
    [
        lambda ax: ax.plot(MONTHS, PRICE),
        lambda ax: ax.plot(MONTHS, HEADCOUNT),
        lambda ax: ax.scatter(MONTHS, PRICE),
        lambda ax: ax.errorbar(MONTHS, PRICE, yerr=5),
        lambda ax: ax.step(MONTHS, PRICE),
        lambda ax: (ax.bar(MONTHS, PRICE), ax.plot(MONTHS, PRICE)),
        lambda ax: ax.plot(np.arange(2014, 2026), PRICE),  # years on x
        lambda ax: ax.plot(np.linspace(1, 9, 11), YEARS),  # a line's y values
    ],
    ids=[
        "price-line",
        "headcount-line",
        "price-scatter",
        "errorbar",
        "step",
        "value-line-over-bars",
        "years-on-x",
        "line-of-year-values",
    ],
)
def test_integer_values_on_y_keep_their_numbers(draw):
    """Values on y in 1900-2099 are quantities, never years."""
    ax = _laid_out(draw)
    assert not isinstance(ax.yaxis.get_major_formatter(), YearTickFormatter)
    assert type(ax.yaxis.get_major_locator()) is mticker.AutoLocator
    locs, labels = _on(ax.yaxis)
    big = [t for t in labels if len(t.replace(",", "")) >= 4]
    assert big and all("," in t for t in big), labels  # 1,985, not 85


def test_twiny_and_secondary_yaxis_read_the_same_years():
    def draw(ax):
        ax.barh(YEARS, np.arange(11) + 1)
        top = ax.twiny()  # shares the y axis
        top.plot(np.arange(11) * 2.5, YEARS)
        ax.secondary_yaxis("right")

    ax = _laid_out(draw)
    _assert_years(ax.yaxis)
    (right,) = ax.child_axes
    assert _on(right.yaxis) == _on(ax.yaxis)
    assert isinstance(right.yaxis.get_major_formatter(), YearTickFormatter)


def test_a_y_year_axis_never_labels_a_tick_between_years():
    ax = _laid_out(lambda ax: ax.barh(YEARS, np.arange(11) + 1))
    ax.set_ylim(2016, 2017)
    assert _on(ax.yaxis) == ([2016.0, 2017.0], ["16", "17"])
    ax.set_ylim(2016.2, 2016.8)  # no whole year in view
    locs, labels = _on(ax.yaxis)
    assert locs and not _whole(locs), locs
    assert labels == [""] * len(locs), labels


def test_crowded_y_years_thin_to_one_em():
    """Thirty years on a short axis: fewer whole-year ticks, never overlapping."""
    years = np.arange(1995, 2025)
    ax = _laid_out(
        lambda ax: ax.barh(years, np.ones(len(years))),
        width="9cm",
        aspect="wide",
    )
    locs, labels = _on(ax.yaxis)
    assert _whole(locs) and labels == _two_digits(locs), labels
    renderer = ax.figure.canvas.get_renderer()
    low, high = sorted(ax.yaxis.get_view_interval())
    shown = [
        text
        for loc, text in zip(
            ax.yaxis.get_majorticklocs(),
            ax.yaxis.get_majorticklabels(),
            strict=True,
        )
        if low <= loc <= high
    ]
    boxes = sorted(
        (t.get_window_extent(renderer) for t in shown), key=lambda b: b.y0
    )
    em = shown[0].get_fontsize() * ax.figure.dpi / 72
    gaps = [b.y0 - a.y1 for a, b in pairwise(boxes)]
    assert gaps and min(gaps) >= em - 0.5, (min(gaps), em, labels)


@pytest.mark.parametrize(
    "draw",
    [
        # vertical bars: their heights are values, not positions
        lambda ax: ax.bar(["a", "b", "c"], [1950, 2010, 2040]),
        # fractions on y
        lambda ax: ax.plot(np.arange(7), np.linspace(1950.3, 2010.3, 7)),
        # past 2099
        lambda ax: ax.plot(np.arange(5), [1800, 1900, 2000, 2100, 2200]),
    ],
    ids=["bar-heights", "fractions", "out-of-range"],
)
def test_other_y_data_keep_their_numbers(draw):
    ax = _laid_out(draw)
    assert not isinstance(ax.yaxis.get_major_formatter(), YearTickFormatter)
    assert isinstance(ax.yaxis.get_major_locator(), mticker.AutoLocator)


def test_large_y_values_keep_thousands_separators():
    ax = _laid_out(lambda ax: ax.plot(YEARS, np.linspace(1_000, 50_000, 11)))
    assert isinstance(ax.yaxis.get_major_formatter(), DefaultNumberFormatter)
    assert isinstance(ax.xaxis.get_major_formatter(), YearTickFormatter)


def test_a_formatter_someone_set_on_y_stays():
    chosen = mticker.FuncFormatter(lambda v, pos: f"FY{v:.0f}")

    def draw(ax):
        ax.barh(YEARS, np.arange(11) + 1)
        ax.yaxis.set_major_formatter(chosen)

    ax = _laid_out(draw)
    assert ax.yaxis.get_major_formatter() is chosen
    assert isinstance(ax.yaxis.get_major_locator(), WholeYearLocator)
    locs, labels = _on(ax.yaxis)
    assert _whole(locs) and labels == [f"FY{v:.0f}" for v in locs]
