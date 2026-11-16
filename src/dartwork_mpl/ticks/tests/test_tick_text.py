"""The tick text a realistic myriad axis shows after ``dm.simple_layout``.

Each row draws one ordinary chart (13 cm, 4:3) and reads the in-view major
tick labels of one axis. The expected text is the held look, so a row
changes only with an owner's decision.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes

import dartwork_mpl as dm

EOK = [0, 0.9e8, 1.75e8]


@dataclass(frozen=True)
class Row:
    """One chart and the y tick text it must show."""

    name: str
    draw: Callable[[Axes], object]
    ticks: tuple[str, ...]


ROWS = (
    Row("man", lambda ax: (ax.plot([0, 1, 2], [1.0e6, 1.8e6, 2.6e6]), dm.format_axis_myriad(ax)),
        ("100만", "125만", "150만", "175만", "200만", "225만", "250만", "275만")),
    Row("eok", lambda ax: (ax.plot([0, 1, 2], EOK), dm.format_axis_myriad(ax)),
        ("0", "0.25억", "0.50억", "0.75억", "1.00억", "1.25억", "1.50억", "1.75억")),
    Row("whole-man", lambda ax: (ax.plot([0, 1, 2], EOK), dm.format_axis_myriad(ax, unit="whole")),
        ("0", "2,500만", "5,000만", "7,500만", "10,000만", "12,500만", "15,000만", "17,500만")),
    Row("each-alone", lambda ax: (ax.plot([0, 1, 2], EOK), dm.format_axis_myriad(ax, decimals=1)),
        ("0", "2,500만", "5,000만", "7,500만", "1억", "1.2억", "1.5억", "1.8억")),
    Row("zh-currency", lambda ax: (ax.plot([0, 1, 2], EOK), dm.format_axis_myriad(ax, locale="zh", currency="¥")),
        ("0", "¥0.25亿", "¥0.50亿", "¥0.75亿", "¥1.00亿", "¥1.25亿", "¥1.50亿", "¥1.75亿")),
)  # fmt: skip


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row.name)
def test_tick_text(row: Row) -> None:
    dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    row.draw(ax)
    dm.simple_layout(fig)
    fig.canvas.draw()
    lo, hi = sorted(ax.yaxis.get_view_interval())
    slack = 1e-9 * (hi - lo)
    shown = tuple(
        tick.label1.get_text()
        for tick in ax.yaxis.get_major_ticks()
        if lo - slack <= tick.get_loc() <= hi + slack
    )
    assert shown == row.ticks


def test_a_locale_outside_the_ladders_is_refused() -> None:
    _, ax = plt.subplots()
    with pytest.raises(ValueError, match="locale must be"):
        dm.format_axis_myriad(ax, locale="en")


def test_large_numbers_leave_an_axis_told_how_to_write_alone() -> None:
    fig, (told, free) = plt.subplots(1, 2)
    for ax in (told, free):
        ax.plot([0, 1], [0, 5e6])
    told.ticklabel_format(axis="y", style="plain")
    dm.simple_layout(fig)
    fig.canvas.draw()
    assert "1000000" in {t.get_text() for t in told.get_yticklabels()}
    assert "1M" in {t.get_text() for t in free.get_yticklabels()}
    plt.close(fig)


def test_myriad_leaves_a_category_axis_its_names():
    fig, ax = plt.subplots()
    ax.barh(["서울", "부산"], [12.5e8, 8.2e8])
    dm.format_axis_myriad(ax)  # y: the names
    dm.format_axis_myriad(ax, axis="x")
    dm.simple_layout(fig)
    fig.canvas.draw()
    assert [t.get_text() for t in ax.get_yticklabels()] == ["서울", "부산"]
    assert ax.get_xticklabels()[1].get_text().endswith("억")
    plt.close(fig)
