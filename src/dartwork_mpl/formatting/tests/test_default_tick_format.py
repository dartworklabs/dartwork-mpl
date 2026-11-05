"""The library's tick numbers on axes nobody formatted (#523).

Agents left the same 0-1,750 axis as ``1750``, ``1,750`` or ``1.75k``
depending on which formatter they reached for. ``dm.simple_layout`` now
settles the numbers of every axis still on matplotlib's default formatter.
The observed value is the label text after a real canvas draw.
"""

from __future__ import annotations

from itertools import pairwise

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
        assert "16" in _drawn(ax, "x")

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

    @pytest.fixture(autouse=True)
    def _concise_dates(self):
        """These pin the 0.6.0 concise words, one config line away now."""
        with dm.config.override(tick_years=4, date_style="concise"):
            yield

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

    def _weeks(self, ax):
        x = np.arange(
            np.datetime64("2024-01-01"),
            np.datetime64("2024-12-30"),
            np.timedelta64(7, "D"),
        )
        ax.plot(x, np.arange(len(x)))

    def test_korean_labels_give_korean_dates(self):
        dm.style.use("report-kr")
        fig, ax = _fig()
        self._weeks(ax)
        ax.set_ylabel("방문자 수")
        dm.simple_layout(fig)
        assert _drawn(ax, "x") == [
            "2024년",
            "3월",
            "5월",
            "7월",
            "9월",
            "11월",
            "2025년",
        ]

    def test_edited_concise_formats_stay_on_a_korean_figure(self):
        # company-analysis's finish step rewrites the stock %Y as %y before
        # simple_layout (two-digit years); its labels must not turn into
        # "2026년" (company-analysis CI, 2026-11-04).
        import matplotlib.dates as mdates

        dm.style.use("report-kr")
        fig, ax = _fig()
        self._weeks(ax)
        ax.set_ylabel("방문자 수")
        fmt = ax.xaxis.get_major_formatter()
        assert type(fmt) is mdates.ConciseDateFormatter
        for name in ("formats", "zero_formats", "offset_formats"):
            setattr(
                fmt, name, [f.replace("%Y", "%y") for f in getattr(fmt, name)]
            )
        dm.simple_layout(fig)
        assert ax.xaxis.get_major_formatter() is fmt
        drawn = _drawn(ax, "x")
        assert drawn[0] == "24"
        assert not any("년" in label or "2024" in label for label in drawn)

    def test_korean_dates_keep_the_offset_and_tex_choice(self):
        import matplotlib.dates as mdates

        dm.style.use("report-kr")
        fig, ax = _fig()
        self._weeks(ax)
        ax.set_ylabel("방문자 수")
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(locator, show_offset=False, usetex=True)
        )
        apply_default_tick_format(fig)
        fmt = ax.xaxis.get_major_formatter()
        assert type(fmt).__name__ == "KoreanConciseDateFormatter"
        assert fmt.show_offset is False
        assert fmt._usetex is True

    def test_days_drop_the_zero_padding(self):
        dm.style.use("report-kr")
        fig, ax = _fig()
        x = np.arange(
            np.datetime64("2024-01-01"),
            np.datetime64("2024-03-01"),
            np.timedelta64(1, "D"),
        )
        ax.plot(x, np.arange(len(x)))
        ax.set_xlabel("날짜")
        dm.simple_layout(fig)
        assert "8일" in _drawn(ax, "x") and "08일" not in _drawn(ax, "x")

    def test_english_labels_keep_english_dates_on_a_kr_preset(self):
        dm.style.use("report-kr")
        fig, ax = _fig()
        self._weeks(ax)
        ax.set_xlabel("Week start")
        fig.text(
            0, 0, "출처: 사내 웹 로그"
        )  # a note does not decide the language
        dm.simple_layout(fig)
        assert "Mar" in _drawn(ax, "x")

    def test_chosen_date_format_wins(self):
        import matplotlib.dates as mdates

        fig, ax = _fig()
        self._weeks(ax)
        ax.set_ylabel("방문자 수")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        dm.simple_layout(fig)
        assert type(ax.xaxis.get_major_formatter()) is mdates.DateFormatter


def _months(ax, n=36):
    x = np.arange(
        np.datetime64("2021-01"), np.datetime64("2021-01") + n
    ).astype("datetime64[D]")
    ax.plot(x, np.sin(np.arange(n)))


def _gaps_em(ax) -> list[float]:
    """Gaps between neighbouring drawn x tick labels, in ems."""
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    low, high = sorted(ax.xaxis.get_view_interval())
    boxes = sorted(
        (
            label.get_window_extent(renderer).x0,
            label.get_window_extent(renderer).x1,
        )
        for loc, label in zip(
            ax.xaxis.get_majorticklocs(),
            ax.xaxis.get_majorticklabels(),
            strict=True,
        )
        if low <= loc <= high and label.get_text()
    )
    em = ax.xaxis.get_majorticklabels()[0].get_fontsize() * fig.dpi / 72
    return [(b[0] - a[1]) / em for a, b in pairwise(boxes)]


class TestCrowdedDates:
    """A narrow date axis takes fewer ticks until its labels are 1 em apart.

    matplotlib picks date ticks from the date range alone: 36 months got ten
    ticks on a 23.4 cm slide and on an 11.4 cm half slide alike, where
    ``2021년 5월 9월 2022년`` ran together.
    """

    @pytest.fixture(autouse=True)
    def _concise_dates(self):
        """These pin the 0.6.0 concise words, one config line away now."""
        with dm.config.override(tick_years=4, date_style="concise"):
            yield

    def test_half_slide_drops_to_two_year_steps(self):
        # At the slide's 18.2 pt ticks (scientific x 2.6, 2026-11-03) neither
        # six-month nor yearly labels fit 36 months into a half slide; the
        # 10.5 pt ticks before that took six-month steps. figsize_for gives
        # 36 positions the full 23.4 cm body (test_wide_axis_keeps_its_ticks).
        dm.style.use("presentation-kr")
        fig, ax = plt.subplots(figsize=dm.figsize("11.4cm", "10.5cm"))
        _months(ax)
        ax.set_xlabel("월")
        dm.simple_layout(fig)
        assert _drawn(ax, "x") == ["2022년", "2024년"]
        assert min(_gaps_em(ax)) >= 1.0

    def test_report_column_is_thinned_too(self):
        fig, ax = _fig()
        _months(ax)
        dm.simple_layout(fig)
        assert _drawn(ax, "x")[:3] == ["2021", "Jul", "2022"]
        assert min(_gaps_em(ax)) >= 1.0

    def test_wide_axis_keeps_its_ticks(self):
        dm.style.use("presentation")
        fig, ax = plt.subplots(figsize=dm.figsize("23.4cm", "10.5cm"))
        _months(ax)
        dm.simple_layout(fig)
        assert _drawn(ax, "x")[:3] == ["2021", "May", "Sep"]

    def test_chosen_locator_wins(self):
        import matplotlib.dates as mdates

        fig, ax = _fig()
        _months(ax)
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
        dm.simple_layout(fig)
        assert len(_drawn(ax, "x")) == 13

    def test_configured_auto_locator_wins(self):
        import matplotlib.dates as mdates

        fig, ax = _fig()
        _months(ax)
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=20))
        ax.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(ax.xaxis.get_major_locator())
        )
        dm.simple_layout(fig)
        assert ax.xaxis.get_major_locator().maxticks == dict.fromkeys(
            ax.xaxis.get_major_locator().maxticks, 20
        )

    def test_rotated_labels_are_left_alone(self):
        fig, ax = _fig()
        _months(ax)
        ax.tick_params(axis="x", labelrotation=45)
        dm.simple_layout(fig)
        assert len(_drawn(ax, "x")) == 10

    def test_opt_out(self):
        fig, ax = _fig()
        _months(ax)
        dm.simple_layout(fig, format_ticks=False)
        assert len(_drawn(ax, "x")) == 10

    def test_no_matplotlib_warning_and_stable(self, recwarn):
        fig, ax = _fig()
        _months(ax)
        dm.simple_layout(fig)
        first = _drawn(ax, "x")
        dm.simple_layout(fig)
        assert _drawn(ax, "x") == first
        assert not [w for w in recwarn if "AutoDateLocator" in str(w.message)]
