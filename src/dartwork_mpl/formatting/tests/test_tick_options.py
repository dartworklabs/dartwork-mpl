"""The tick formats a prompt can ask for, one ``dm.config`` field each.

``tick_years=4`` (four-digit years), ``date_style="concise"`` (with
``tick_years=4``: matplotlib's own concise words) and ``number_ladder="si"``
(k/M/G/T in Korean figures), on the four figures whose default tick text
changed: monthly dates (English and Korean), year data and Korean bars from
one million. Date text is compared with the stock formatter computed here,
because which ticks fit depends on the figure width.
"""

from __future__ import annotations

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._dates import KoreanConciseDateFormatter

MONTHS = np.arange(np.datetime64("2023-01"), np.datetime64("2026-02")).astype(
    "datetime64[D]"
)
OPTIONS = {"tick_years": 4, "date_style": "concise", "number_ladder": "si"}


@pytest.fixture(autouse=True)
def _report_preset():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _texts(axis) -> list[str]:
    axis.figure.canvas.draw()
    low, high = sorted(axis.get_view_interval())
    return [
        label.get_text()
        for loc, label in zip(
            axis.get_majorticklocs(), axis.get_majorticklabels(), strict=True
        )
        if low <= loc <= high and label.get_text()
    ]


def _stock_texts(ax, formatter_cls) -> list[str]:
    locs = list(ax.xaxis.get_majorticklocs())
    words = formatter_cls(ax.xaxis.get_major_locator()).format_ticks(locs)
    low, high = sorted(ax.xaxis.get_view_interval())
    return [w for loc, w in zip(locs, words, strict=True) if low <= loc <= high]


def _monthly(*, korean: bool):
    if korean:
        dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "wide"))
    ax.plot(MONTHS, np.linspace(1, 3, len(MONTHS)))
    if korean:
        ax.set_ylabel("인구")
    dm.simple_layout(fig)
    return ax


@pytest.mark.parametrize("korean", [False, True], ids=["en", "ko"])
def test_four_digit_concise_dates_are_matplotlibs_words(korean):
    with dm.config.override(**OPTIONS):
        ax = _monthly(korean=korean)
        cls = (
            KoreanConciseDateFormatter
            if korean
            else mdates.ConciseDateFormatter
        )
        assert type(ax.xaxis.get_major_formatter()) is cls
        got = _texts(ax.xaxis)
        assert got == _stock_texts(ax, cls)
        assert got[0] in ("2023", "2023년")


def test_four_digit_years_on_whole_year_ticks():
    with dm.config.override(**OPTIONS):
        fig, ax = plt.subplots(figsize=dm.figsize("14.5cm", "wide"))
        ax.plot(np.arange(2016, 2025), np.arange(9))
        dm.simple_layout(fig)
        assert _texts(ax.xaxis) == [str(y) for y in range(2016, 2025)]


def test_si_ladder_in_a_korean_figure():
    dm.style.use("report-kr")
    with dm.config.override(**OPTIONS):
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.bar(["가", "나"], [4e11, 1e12])
        ax.set_ylabel("인구")
        ax.set_yticks(np.arange(0, 1.01e12, 2e11))
        dm.simple_layout(fig)
        assert _texts(ax.yaxis) == ["0", "0.2T", "0.4T", "0.6T", "0.8T", "1.0T"]


def test_korean_default_reads_myriad_units():
    """The same Korean bars read 조 by default, so the option is meaningful."""
    dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.bar(["가", "나"], [4e11, 1e12])
    ax.set_ylabel("인구")
    ax.set_yticks(np.arange(0, 1.01e12, 2e11))
    dm.simple_layout(fig)
    assert any("억" in t or "조" in t for t in _texts(ax.yaxis))
