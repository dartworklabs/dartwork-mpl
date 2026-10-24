"""The library's tick numbers on axes nobody formatted (#523).

Agents left the same 0-1,750 axis as ``1750``, ``1,750`` or ``1.75k``
depending on which formatter they reached for. ``dm.simple_layout`` now
settles the numbers of every axis still on matplotlib's default formatter.
The observed value is the label text after a real canvas draw.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pytest
from matplotlib.axes import Axes

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._defaults import apply_default_tick_format

MINUS = "\N{MINUS SIGN}"


@pytest.fixture(autouse=True)
def _report_preset():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _drawn(ax: Axes, which: str = "y") -> list[str]:
    ax.figure.canvas.draw()
    axis = ax.yaxis if which == "y" else ax.xaxis
    low, high = sorted(axis.get_view_interval())
    return [
        label.get_text()
        for loc, label in zip(
            axis.get_majorticklocs(), axis.get_majorticklabels(), strict=True
        )
        if low <= loc <= high and label.get_text()
    ]


def _fig():
    return plt.subplots(figsize=dm.figsize("9cm", "standard"))


class TestThousandsSeparators:
    """Axes reaching 1,000 group digits; smaller ones are left alone."""

    def test_bar_axis_to_1750(self):
        fig, ax = _fig()
        ax.bar(["N", "S", "E"], [1720, 1180, 940])
        dm.simple_layout(fig)
        assert _drawn(ax) == [
            "0",
            "250",
            "500",
            "750",
            "1,000",
            "1,250",
            "1,500",
            "1,750",
        ]

    def test_line_axis_in_ten_thousands(self):
        fig, ax = _fig()
        ax.plot(range(10), np.linspace(24_000, 34_000, 10))
        dm.simple_layout(fig)
        assert "34,000" in _drawn(ax) and all("k" not in t for t in _drawn(ax))

    def test_negative_ticks_use_the_axis_minus(self):
        fig, ax = _fig()
        ax.plot(range(5), [-2000, -500, 0, 1200, 3000])
        dm.simple_layout(fig)
        assert f"{MINUS}2,000" in _drawn(ax)

    def test_small_axis_keeps_matplotlib(self):
        fig, ax = _fig()
        ax.plot(range(5), [0, 250, 500, 600, 750])
        dm.simple_layout(fig)
        assert type(ax.yaxis.get_major_formatter()) is mticker.ScalarFormatter


class TestMillions:
    """From one million the largest tick's unit replaces the 1e6 corner label."""

    def test_population_axis(self):
        fig, ax = _fig()
        ax.bar(["A", "B", "C"], [2_400_000, 1_350_000, 300_000])
        dm.simple_layout(fig)
        assert _drawn(ax) == ["0", "0.5M", "1.0M", "1.5M", "2.0M", "2.5M"]
        assert ax.yaxis.get_offset_text().get_text() == ""

    def test_narrow_million_range_stays_plain(self):
        fig, ax = _fig()
        ax.plot(range(3), [1_000_000, 1_000_050, 1_000_100])
        dm.simple_layout(fig)
        assert all("M" not in t for t in _drawn(ax))
        assert "1,000,100" in _drawn(ax)


class TestLeftAlone:
    """Years, chosen formatters and non-linear or non-numeric axes."""

    def test_year_axis_has_no_separator(self):
        fig, ax = _fig()
        ax.plot(np.arange(2012, 2024), np.linspace(1, 3, 12))
        dm.simple_layout(fig)
        assert all("," not in t for t in _drawn(ax, "x"))
        assert "2016" in _drawn(ax, "x")

    def test_chosen_formatter_wins(self):
        fig, ax = _fig()
        ax.bar(["a", "b"], [1200, 1750])
        dm.format_axis_si(ax)
        chosen = ax.yaxis.get_major_formatter()
        dm.simple_layout(fig)
        assert ax.yaxis.get_major_formatter() is chosen

    def test_log_axis(self):
        fig, ax = _fig()
        ax.plot([1, 2, 3], [100, 10_000, 100_000])
        ax.set_yscale("log")
        dm.simple_layout(fig)
        assert (
            type(ax.yaxis.get_major_formatter())
            is mticker.LogFormatterSciNotation
        )

    def test_colorbar(self):
        fig, ax = _fig()
        im = ax.imshow(np.arange(16).reshape(4, 4) * 1000)
        cbar = fig.colorbar(im)
        dm.simple_layout(fig)
        assert (
            type(cbar.ax.yaxis.get_major_formatter())
            is not dm.formatting._defaults.DefaultNumberFormatter
        )

    def test_opt_out(self):
        fig, ax = _fig()
        ax.bar(["a", "b"], [1200, 1750])
        dm.simple_layout(fig, format_ticks=False)
        assert type(ax.yaxis.get_major_formatter()) is mticker.ScalarFormatter
        assert "1000" in _drawn(ax)

    def test_second_call_changes_nothing(self):
        fig, ax = _fig()
        ax.bar(["a", "b"], [1200, 1750])
        assert apply_default_tick_format(fig) == 1
        assert apply_default_tick_format(fig) == 0


class TestDates:
    """Every preset formats unformatted date axes concisely."""

    @pytest.mark.parametrize(
        "preset", ["scientific", "report", "presentation", "report-kr", "dark"]
    )
    def test_presets_use_the_concise_converter(self, preset):
        dm.style.use(preset)
        assert matplotlib.rcParams["date.converter"] == "concise"

    def test_one_year_of_weeks(self):
        fig, ax = _fig()
        x = np.arange(
            np.datetime64("2024-01-01"),
            np.datetime64("2024-12-30"),
            np.timedelta64(7, "D"),
        )
        ax.plot(x, np.arange(len(x)))
        dm.simple_layout(fig)
        assert _drawn(ax, "x") == [
            "2024",
            "Mar",
            "May",
            "Jul",
            "Sep",
            "Nov",
            "2025",
        ]
