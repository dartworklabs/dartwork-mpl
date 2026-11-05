"""Two-digit years on untouched year and date axes, and on dated categories."""

from __future__ import annotations

import datetime
import re
from itertools import pairwise

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._dates import (
    KoreanConciseDateFormatter,
    PeriodDateFormatter,
    ShortConciseDateFormatter,
)
from dartwork_mpl.formatting._defaults import apply_default_tick_format
from dartwork_mpl.formatting._quarters import (
    QuarterLocator,
    plotted_dates,
    quarter_words,
    quarterly,
)
from dartwork_mpl.formatting._years import (
    WholeYearLocator,
    YearTickFormatter,
    requested_params,
    two_digits_repeat,
    whole_years,
    year_data,
)


@pytest.fixture(autouse=True)
def _report_preset():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _xticks(ax) -> list[str]:
    ax.figure.canvas.draw()
    low, high = sorted(ax.xaxis.get_view_interval())
    return [
        label.get_text()
        for loc, label in zip(
            ax.xaxis.get_majorticklocs(),
            ax.xaxis.get_majorticklabels(),
            strict=True,
        )
        if low <= loc <= high and label.get_text()
    ]


def _line(x, ylabel=None, ticks=None, width="9cm", aspect="standard"):
    """A line over ``x``; matplotlib's own locator unless ``ticks`` pins it."""
    fig, ax = plt.subplots(figsize=dm.figsize(width, aspect))
    ax.plot(x, np.linspace(1, 3, len(x)))
    if ticks is not None:
        ax.set_xticks(ticks)
    if ylabel:
        ax.set_ylabel(ylabel)
    dm.simple_layout(fig)
    return ax


def _shown(ax) -> tuple[list[float], list[str]]:
    """Locations and texts of every x tick inside the view, after a draw."""
    ax.figure.canvas.draw()
    low, high = sorted(ax.xaxis.get_view_interval())
    pairs = [
        (float(loc), label.get_text())
        for loc, label in zip(
            ax.xaxis.get_majorticklocs(),
            ax.xaxis.get_majorticklabels(),
            strict=True,
        )
        if low <= loc <= high
    ]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def _two_digits(locs, suffix="") -> list[str]:
    return [f"{round(loc) % 100:02d}{suffix}" for loc in locs]


def _whole(locs) -> bool:
    return all(abs(loc - round(loc)) < 1e-9 for loc in locs)


def test_untouched_year_axis_two_digits():
    locs, labels = _shown(_line(np.arange(2016, 2025)))
    assert len(locs) >= 3 and _whole(locs), locs
    assert labels == _two_digits(locs)


def test_korean_period_year_axis_has_no_suffix():
    locs, labels = _shown(_line(np.arange(2016, 2025), "매출"))
    assert len(locs) >= 3 and _whole(locs), locs
    assert labels == _two_digits(locs)
    with dm.config.override(date_style="concise"):
        locs, labels = _shown(_line(np.arange(2016, 2025), "매출"))
        assert len(locs) >= 3 and _whole(locs), locs
        assert labels == _two_digits(locs, "년")


# Report 9 cm: 2004/2005 starts ended on 2.5-year ticks once the margins
# were refitted (2007.5 read "08"), 2008/2009 on whole years after starting
# on 2.5 (read "2010"). Review 2026-11-05, C1.
SWEEP_STARTS = (1995, 2004, 2005, 2008, 2009, 2012)


@pytest.mark.parametrize("width", ["6cm", "9cm", "12cm", "17cm"])
@pytest.mark.parametrize("preset", ["report", "scientific"])
def test_annual_lines_tick_whole_years(preset, width):
    """Annual data tick whole years at every width, labelled two digits.

    The year axis is read from the data (integers 1900-2099), so the ticks
    are whole years before and after the margins are refitted, where
    matplotlib's own locator steps 2.5 years (``2005.0, 2007.5``).
    """
    dm.style.use(preset)
    for start in SWEEP_STARTS:
        for aspect in ("standard", "wide"):
            ax = _line(np.arange(start, 2025), "y", width=width, aspect=aspect)
            locs, labels = _shown(ax)
            case = (preset, width, aspect, start, locs, labels)
            assert len(locs) >= 2 and _whole(locs), case
            assert labels == _two_digits(locs), case
            assert ax.xaxis.get_offset_text().get_text() == "", case
            assert _min_gap_em(ax) >= 1.0, case
            plt.close(ax.figure)


@pytest.mark.parametrize(
    "options",
    [{"date_style": "concise"}, {"tick_years": 4}],
    ids=["korean-concise", "four-digits"],
)
def test_wider_year_labels_stay_one_em_apart(options):
    """``24년`` and ``2024`` are wider than ``24``: the ticks thin to fit."""
    dm.style.use("report-kr")
    with dm.config.override(**options):
        for width in ("6cm", "9cm"):
            ax = _line(np.arange(1995, 2025), "매출", width=width)
            locs, labels = _shown(ax)
            assert len(locs) >= 2 and _whole(locs), (width, locs)
            if options.get("tick_years") == 4:
                assert labels == [f"{round(v)}" for v in locs], labels
            else:
                assert labels == _two_digits(locs, "년"), labels
            assert _min_gap_em(ax) >= 1.0, (width, labels)
            plt.close(ax.figure)


def test_thinning_again_keeps_the_count_it_started_from():
    """A repeat layout that finds no better count leaves the last one.

    Review 2026-11-05, R7: it reset ``nbins`` to ``"auto"``, so a thinned
    axis got its crowded ticks back.
    """
    dm.style.use("report-kr")
    with dm.config.override(tick_years=4, date_style="concise"):
        ax = _line(np.arange(2016, 2025), "매출")
        locator = ax.xaxis.get_major_locator()
        first = locator.nbins
        assert isinstance(first, int), first  # "2016년" labels were thinned
        thinned = _shown(ax)
        ax.tick_params(axis="x", labelsize=40)  # now no count fits
        dm.simple_layout(ax.figure)
        assert locator.nbins == first
        ax.tick_params(
            axis="x", labelsize=matplotlib.rcParams["xtick.labelsize"]
        )
        assert _shown(ax) == thinned


def test_zoomed_year_axis_never_rounds_a_fraction():
    ax = _line(np.arange(2005, 2025))
    ax.set_xlim(2016, 2017)
    locs, labels = _shown(ax)
    assert locs == [2016.0, 2017.0] and labels == ["16", "17"], (locs, labels)
    ax.set_xlim(2016.2, 2016.8)  # no whole year in view
    locs, labels = _shown(ax)
    assert locs and not _whole(locs), locs
    assert labels == [""] * len(locs), labels  # unlabelled, never "16"/"17"
    assert ax.xaxis.get_offset_text().get_text() == ""


def test_year_axis_cursor_reads_the_value_not_a_rounded_year():
    ax = _line(np.arange(2005, 2025))
    _shown(ax)
    oracle = mticker.ScalarFormatter()
    oracle.set_axis(ax.xaxis)
    fmt = ax.xaxis.get_major_formatter()
    for value in (2007.5, 2016.43, 2020.0):
        assert fmt.format_data_short(value) == oracle.format_data_short(value)
    assert fmt.format_data_short(2007.5) != "08"


def _year_axis(ax) -> bool:
    return isinstance(ax.xaxis.get_major_formatter(), YearTickFormatter)


def test_year_data_on_bars_scatter_twins_and_shared_axes():
    years = np.arange(2014, 2025)
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.bar(years, np.arange(len(years)) + 1)
    dm.simple_layout(fig)
    locs, labels = _shown(ax)
    assert _whole(locs) and labels == _two_digits(locs), labels

    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.scatter(years, np.arange(len(years)))
    dm.simple_layout(fig)
    assert _year_axis(ax)

    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.axhline(0.5)  # axes fractions across: not data
    twin = ax.twinx()
    twin.plot(years, np.arange(len(years)))  # the twin's line is the data
    dm.simple_layout(fig)
    assert _year_axis(ax) and _year_axis(twin)

    fig, axes = plt.subplots(2, 1, sharex=True, figsize=dm.figsize("12cm"))
    for a in axes:
        a.plot(years, np.arange(len(years)))
    dm.simple_layout(fig)
    assert _year_axis(axes[0])
    locs, labels = _shown(axes[1])  # the top axes hides its tick labels
    assert _whole(locs) and labels == _two_digits(locs), labels


@pytest.mark.parametrize(
    "x",
    [
        np.linspace(1950.3, 2010.3, 7),  # elevations, not years
        np.arange(1880, 2025),  # reaches outside 1900-2099
        np.array([2020.0, 2020.0]),  # one year is not a span
    ],
    ids=["fractions", "out-of-range", "one-value"],
)
def test_other_data_keep_matplotlibs_locator_and_formatter(x):
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.plot(x, np.arange(len(x)))
    dm.simple_layout(fig)
    assert type(ax.xaxis.get_major_locator()) is mticker.AutoLocator
    assert type(ax.xaxis.get_major_formatter()) is mticker.ScalarFormatter


def test_a_chosen_year_formatter_still_gets_whole_year_ticks():
    """``dm.format_axis_year`` set the formatter, not the locator.

    The locator is still matplotlib's, so the year locator goes in and the
    chosen formatter stays: no ``2007.5`` rounded to ``08년``.
    """
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "wide"))
    ax.plot(np.arange(2004, 2025), np.arange(21))
    ax.set_ylabel("y")
    dm.format_axis_year(ax)
    chosen = ax.xaxis.get_major_formatter()
    dm.simple_layout(fig)
    assert ax.xaxis.get_major_formatter() is chosen
    locs, labels = _shown(ax)
    assert len(locs) >= 2 and _whole(locs), locs
    assert labels == _two_digits(locs, "년"), labels


@pytest.mark.parametrize(
    ("ask", "expected"),
    [
        (lambda ax: ax.locator_params(axis="x", nbins=3), ["00", "10", "20"]),
        (
            lambda ax: ax.xaxis.get_major_locator().set_params(nbins=2),
            ["00", "20"],
        ),
    ],
    ids=["locator_params", "set_params"],
)
def test_a_requested_tick_count_stays_on_whole_years(ask, expected):
    """A tick count asked of matplotlib's own locator is kept.

    ``locator_params`` and ``set_params`` edit that locator in place and
    leave ``isDefault_majloc`` set, so the year locator still goes in: it
    carries the request, on whole years, and is not thinned below it
    (review 2026-11-05, R1: ``nbins=3`` read ``00, 05 … 25``).
    """
    for width in ("9cm", "17cm"):
        fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"))
        ax.plot(np.arange(2000, 2025), np.arange(25))
        ask(ax)
        dm.simple_layout(fig)
        locs, labels = _shown(ax)
        assert labels == expected, (width, locs, labels)
        assert isinstance(ax.xaxis.get_major_locator(), WholeYearLocator)
        plt.close(fig)


def test_a_tick_count_asked_after_the_layout_is_kept():
    """The year locator is the axis's from then on: asking it again wins."""
    fig, ax = plt.subplots(figsize=dm.figsize("6cm", "standard"))
    ax.plot(np.arange(1995, 2025), np.arange(30))
    dm.simple_layout(fig)
    ax.locator_params(axis="x", nbins=8)
    dm.simple_layout(fig)
    locator = ax.xaxis.get_major_locator()
    assert isinstance(locator, WholeYearLocator) and locator.nbins == 8
    locs, labels = _shown(ax)
    assert _whole(locs) and labels == _two_digits(locs), labels


def test_requested_params_read_what_someone_changed():
    fresh = mticker.AutoLocator()
    assert requested_params(fresh) == {}
    fresh.set_params(nbins=4, prune="lower", min_n_ticks=3)
    assert requested_params(fresh) == {
        "nbins": 4,
        "prune": "lower",
        "min_n_ticks": 3,
    }
    stepped = mticker.AutoLocator()
    stepped.set_params(steps=[1, 3, 10])
    assert list(requested_params(stepped)["steps"]) == [1, 3, 10]
    assert requested_params(mticker.MultipleLocator(5)) == {}
    locator = WholeYearLocator(nbins=3)
    assert locator.requested == {"nbins"} and locator.nbins == 3
    assert locator.tick_values(1998.8, 2025.2) == pytest.approx(
        [1990, 2000, 2010, 2020, 2030]  # one past each edge, as matplotlib's
    )
    locator.thin(2)  # the library's own count: not a request
    assert locator.requested == {"nbins"} and locator.nbins == 2
    assert WholeYearLocator().requested == frozenset()


def test_pinned_ticks_keep_their_places():
    """Whole years someone pinned read two digits; other pins keep numbers."""
    ax = _line(np.arange(2016, 2025), ticks=[2016, 2020, 2024])
    assert _shown(ax) == ([2016.0, 2020.0, 2024.0], ["16", "20", "24"])
    ax = _line(np.arange(2016, 2025), ticks=[2016.5, 2020.5])
    locs, labels = _shown(ax)
    assert type(ax.xaxis.get_major_formatter()) is mticker.ScalarFormatter
    assert all(len(t) >= 6 for t in labels), labels  # "2016.5", never "16"


def test_year_axis_rejects_non_integer_and_out_of_range():
    wide = _xticks(
        _line(np.arange(1000, 2501, 100), ticks=np.arange(1000, 2501, 500))
    )
    assert all(len(t) >= 4 for t in wide)
    assert "1,000" in wide or "1000" in wide
    frac = _xticks(
        _line(np.linspace(1900.5, 1950.5, 6), ticks=[1900.5, 1920.5, 1940.5])
    )
    assert frac and all(len(t) >= 6 for t in frac)  # "1900.5", not "00"


def test_century_span_keeps_four_digits():
    """1900 … 2024 would print ``00`` twice: the years print four digits."""
    locs, labels = _shown(_line(np.arange(1900, 2025), width="12cm"))
    assert len(locs) >= 3 and _whole(locs), locs
    assert labels == [f"{round(v)}" for v in locs], labels


def test_override_four_digits():
    with dm.config.override(tick_years=4):
        locs, labels = _shown(_line(np.arange(2016, 2025)))
        assert len(locs) >= 3 and _whole(locs), locs
        assert labels == [str(round(loc)) for loc in locs]


@pytest.mark.parametrize("field", ["tick_years", "date_style"])
def test_invalid_config_value_raises_naming_field(field):
    fig, ax = plt.subplots()
    ax.plot([1, 2], [1, 2])
    with dm.config.override(**{field: "bogus"}):
        with pytest.raises(ValueError, match=field):
            dm.simple_layout(fig)


def test_helpers():
    assert year_data([2016, 2017, 2018]) and year_data([2016.0, 2016.0, 2020])
    assert year_data(np.array([2015.6]) + 0.4 + [0, 1])  # bar centres
    assert not year_data([2016, 2016])  # one year is not a span
    assert not year_data([1890, 1900])
    assert not year_data([2016, 2016.5])
    assert not year_data([2016, float("inf")])  # no OverflowError
    assert not year_data([2016, float("nan")])
    assert whole_years([2016, 2017, 2020]) and not whole_years([])
    assert not whole_years([2016, 2016.5])
    fmt = YearTickFormatter(2)
    assert fmt.format_ticks([2016, 2016.5, 2017]) == ["16", "", "17"]
    assert fmt.format_ticks([1900, 2000]) == ["1900", "2000"]
    assert fmt.format_data_short(2016.5) == "2016.5"
    locator = WholeYearLocator()
    assert locator.tick_values(2004.05, 2024.95) == pytest.approx(
        [2000, 2005, 2010, 2015, 2020, 2025]
    )
    assert two_digits_repeat([1900, 2000]) and not two_digits_repeat(
        [2016, 2017]
    )
    with pytest.raises(ValueError, match="digits"):
        YearTickFormatter(3)  # type: ignore[arg-type]


# ---------------------------------------------------------------- date axes

# 2023-01 … 2026-01, one point a month (the approved m-L2 capture's data).
MONTHS = np.arange(np.datetime64("2023-01"), np.datetime64("2026-02")).astype(
    "datetime64[D]"
)
# 2023Q1 … 2025Q4 as quarter starts and as quarter ends.
QUARTER_STARTS = np.arange(
    np.datetime64("2023-01"), np.datetime64("2026-01"), 3
).astype("datetime64[D]")
QUARTER_ENDS = (
    np.arange(np.datetime64("2023-04"), np.datetime64("2026-04"), 3).astype(
        "datetime64[D]"
    )
    - 1
)
PERIOD_MONTH = re.compile(r"\d\d\.\d\d")
PERIOD_QUARTER = re.compile(r"\d\d\.Q[1-4]")
# Every period label: year, month, day, or a time under a dated corner.
PERIOD_ANY = re.compile(r"\d\d|\d\d\.\d\d|\d\d\.\d\d\.\d\d|\d\d:\d\d")


def _dated(x, width="14.5cm", ylabel=None, *, korean=False):
    if korean:
        dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize(width, "wide"))
    ax.plot(x, np.linspace(1, 3, len(x)))
    if ylabel:
        ax.set_ylabel(ylabel)
    return fig, ax


def _laid_out(x, width="14.5cm", ylabel=None, *, korean=False):
    fig, ax = _dated(x, width, ylabel, korean=korean)
    dm.simple_layout(fig)
    return ax


def _ticks(ax) -> tuple[list[float], list[str]]:
    """Locations and texts of the labelled x ticks inside the view."""
    ax.figure.canvas.draw()
    low, high = sorted(ax.xaxis.get_view_interval())
    pairs = [
        (float(loc), label.get_text())
        for loc, label in zip(
            ax.xaxis.get_majorticklocs(),
            ax.xaxis.get_majorticklabels(),
            strict=True,
        )
        if low <= loc <= high and label.get_text()
    ]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def _min_gap_em(ax) -> float:
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    low, high = sorted(ax.xaxis.get_view_interval())
    labels = [
        label
        for loc, label in zip(
            ax.xaxis.get_majorticklocs(),
            ax.xaxis.get_majorticklabels(),
            strict=True,
        )
        if low <= loc <= high and label.get_text()
    ]
    boxes = sorted(
        (lab.get_window_extent(renderer) for lab in labels), key=lambda b: b.x0
    )
    em = labels[0].get_fontsize() * fig.dpi / 72.0
    return min(b.x0 - a.x1 for a, b in pairwise(boxes)) / em


def _quarter_index(label: str) -> int:
    """``23.Q3`` -> 2023 * 4 + 2."""
    year, quarter = label.split(".Q")
    return (2000 + int(year)) * 4 + int(quarter) - 1


def _assert_quarter_rhythm(labels: list[str]) -> int:
    """Labels step by 1, 2, 4 or 8 quarters and keep Q1; return the step."""
    index = [_quarter_index(t) for t in labels]
    steps = {b - a for a, b in pairwise(index)}
    assert len(steps) == 1, labels
    (step,) = steps
    assert step in (1, 2, 4, 8), labels
    assert all(i % min(step, 4) == 0 for i in index), labels  # Q1 kept
    return step


def test_monthly_line_period():
    ax = _laid_out(MONTHS)
    labels = _xticks(ax)
    assert labels[0] == "23.01"
    assert all(PERIOD_MONTH.fullmatch(t) for t in labels), labels
    assert ax.xaxis.get_offset_text().get_text() == ""
    # The approved capture m-L2 (14.5 cm, report).
    assert labels == [
        "23.01",
        "23.05",
        "23.09",
        "24.01",
        "24.05",
        "24.09",
        "25.01",
        "25.05",
        "25.09",
        "26.01",
    ]


def test_monthly_line_concise_override():
    with dm.config.override(date_style="concise"):
        labels = _xticks(_laid_out(MONTHS))
        assert "May" in labels and "23" in labels, labels
        assert not any("2023" in t for t in labels), labels
        korean = _xticks(_laid_out(MONTHS, ylabel="매출", korean=True))
        assert "5월" in korean and "23년" in korean, korean
        assert not any("2023" in t or "05월" in t for t in korean), korean


def test_period_style_on_a_korean_figure_has_no_words():
    labels = _xticks(_laid_out(MONTHS, ylabel="매출", korean=True))
    assert labels[0] == "23.01"
    assert all(PERIOD_MONTH.fullmatch(t) for t in labels), labels


def test_quarterly_line_period():
    ax = _laid_out(QUARTER_STARTS)
    locs, labels = _ticks(ax)
    assert labels[0] == "23.Q1"
    assert all(PERIOD_QUARTER.fullmatch(t) for t in labels), labels
    assert not any(PERIOD_MONTH.fullmatch(t) for t in labels)  # never 23.04
    _assert_quarter_rhythm(labels)
    days = [mdates.num2date(v) for v in locs]
    assert all(d.day == 1 and d.month in (1, 4, 7, 10) for d in days)
    assert ax.xaxis.get_offset_text().get_text() == ""


def test_thinning_never_switches_notation():
    ax = _laid_out(QUARTER_STARTS, "9cm")
    labels = _xticks(ax)
    assert 2 <= len(labels) < 12, labels
    assert all(PERIOD_QUARTER.fullmatch(t) for t in labels), labels
    assert "23.Q1" in labels
    assert _assert_quarter_rhythm(labels) > 1
    assert _min_gap_em(ax) >= 1.0


def test_quarter_end_data_ticks_on_quarter_ends():
    """Quarter-end dates (pandas "QE") keep each label next to its quarter."""
    locs, labels = _ticks(_laid_out(QUARTER_ENDS))
    assert labels[0] == "23.Q1"
    assert all(PERIOD_QUARTER.fullmatch(t) for t in labels), labels
    plotted = set(mdates.date2num(QUARTER_ENDS).tolist())
    assert set(locs) <= plotted, locs


def test_quarter_words_in_concise_style():
    with dm.config.override(date_style="concise"):
        labels = _xticks(_laid_out(QUARTER_STARTS))
        assert "23" in labels and any(re.fullmatch("Q[2-4]", t) for t in labels)
        assert all(re.fullmatch(r"\d\d|Q[2-4]", t) for t in labels), labels
        korean = _xticks(_laid_out(QUARTER_STARTS, ylabel="매출", korean=True))
        assert "23년" in korean and "Q2" in korean, korean
        assert all(re.fullmatch(r"\d\d년|Q[2-4]", t) for t in korean), korean


def test_reference_line_does_not_hide_quarters():
    """An axhline's x runs in axes fractions (0 … 1), not dates."""
    fig, ax = _dated(QUARTER_STARTS)
    ax.axhline(2, linewidth=0.5)
    dm.simple_layout(fig)
    assert all(PERIOD_QUARTER.fullmatch(t) for t in _xticks(ax))


def test_marker_line_does_not_hide_quarters():
    """An axvline at a date between quarters is a marker, not quarterly data.

    Its x is a date but its y runs in axes fractions, so it is left out of
    the plotted dates as an axhline is (review 2026-11-05: it turned the
    axis back to ``23.01, 23.05``).
    """
    fig, ax = _dated(QUARTER_STARTS)
    ax.axvline(np.datetime64("2024-02-15"), linewidth=0.5)
    dm.simple_layout(fig)
    labels = _xticks(ax)
    assert labels and all(PERIOD_QUARTER.fullmatch(t) for t in labels), labels
    np.testing.assert_allclose(
        np.sort(plotted_dates(ax, "x")), mdates.date2num(QUARTER_STARTS)
    )


def test_auto_date_locator_labels_read_as_periods():
    """Property over spans and widths on the default locator path."""
    spans = [
        np.arange(np.datetime64("2024-01-01"), np.datetime64("2024-03-01")),
        np.arange(np.datetime64("2024-01-01"), np.datetime64("2024-12-30"), 7),
        MONTHS,
        np.arange(np.datetime64("2005-01"), np.datetime64("2025-01")).astype(
            "datetime64[D]"
        ),
        np.arange(
            np.datetime64("2026-05-02T09:00"),
            np.datetime64("2026-05-02T13:00"),
            np.timedelta64(1, "m"),
        ),
    ]
    for x in spans:
        for width in ("6cm", "9cm", "17cm"):
            ax = _laid_out(x, width)
            labels = _xticks(ax)
            assert len(labels) >= 2, (x[0], width, labels)
            assert all(PERIOD_ANY.fullmatch(t) for t in labels), (x[0], labels)
            assert len(set(labels)) == len(labels), (x[0], width, labels)
            assert not re.search(
                r"\d{4}", ax.xaxis.get_offset_text().get_text()
            )
            plt.close(ax.figure)


def test_century_date_axis_keeps_four_digits():
    years = np.arange(np.datetime64("1880"), np.datetime64("2025")).astype(
        "datetime64[D]"
    )
    labels = _xticks(_laid_out(years))
    assert labels and all(re.fullmatch(r"\d{4}", t) for t in labels), labels
    assert len(set(labels)) == len(labels)


def _edited_concise(ax):
    fmt = ax.xaxis.get_major_formatter()
    for name in ("formats", "zero_formats", "offset_formats"):
        setattr(fmt, name, [f.replace("%Y", "%y") for f in getattr(fmt, name)])
    return fmt


@pytest.mark.parametrize("data", [MONTHS, QUARTER_STARTS], ids=["m", "q"])
@pytest.mark.parametrize(
    "make",
    [
        lambda ax: mdates.DateFormatter("%Y"),
        _edited_concise,
        lambda ax: mticker.FuncFormatter(lambda x, pos: "x"),
    ],
    ids=["DateFormatter", "edited-concise", "FuncFormatter"],
)
def test_explicit_date_formatters_survive(data, make):
    fig, ax = _dated(data)
    fmt = make(ax)
    ax.xaxis.set_major_formatter(fmt)
    locator = ax.xaxis.get_major_locator()
    dm.simple_layout(fig)
    assert ax.xaxis.get_major_formatter() is fmt
    assert type(ax.xaxis.get_major_locator()) is type(locator)
    if isinstance(fmt, mdates.DateFormatter):
        assert all(re.fullmatch(r"\d{4}", t) for t in _xticks(ax))


def _labels_of(ax, fresh) -> list[str]:
    """What a fresh formatter prints for the axis's ticks, in view."""
    ax.figure.canvas.draw()
    locs = list(ax.xaxis.get_majorticklocs())
    low, high = sorted(ax.xaxis.get_view_interval())
    words = fresh.format_ticks(locs)
    return [
        w
        for loc, w in zip(locs, words, strict=True)
        if low <= loc <= high and w
    ]


@pytest.mark.parametrize("data", [MONTHS, QUARTER_STARTS], ids=["m", "q"])
def test_override_reproduces_concise(data):
    with dm.config.override(tick_years=4, date_style="concise"):
        ax = _laid_out(data)
        fmt = ax.xaxis.get_major_formatter()
        locator = ax.xaxis.get_major_locator()
        assert type(fmt) is mdates.ConciseDateFormatter
        assert type(locator) is mdates.AutoDateLocator
        assert _xticks(ax) == _labels_of(
            ax, mdates.ConciseDateFormatter(locator)
        )
        assert re.fullmatch(r"\d{4}", _xticks(ax)[0])

        ax = _laid_out(data, ylabel="매출", korean=True)
        fmt = ax.xaxis.get_major_formatter()
        locator = ax.xaxis.get_major_locator()
        assert type(fmt) is KoreanConciseDateFormatter and fmt.digits == 4
        assert type(locator) is mdates.AutoDateLocator
        assert _xticks(ax) == _labels_of(
            ax, KoreanConciseDateFormatter(locator)
        )
        assert re.fullmatch(r"\d{4}년", _xticks(ax)[0])


def test_period_dates_keep_the_offset_and_tex_choice():
    """The converter's own formatter, adjusted in place, keeps those choices."""
    with matplotlib.rc_context({"text.usetex": True}):
        fig, ax = _dated(MONTHS)  # the converter reads usetex here
    ax.xaxis.get_major_formatter().show_offset = False
    locator = ax.xaxis.get_major_locator()
    assert ax.xaxis.isDefault_majfmt and ax.xaxis.isDefault_majloc
    assert apply_default_tick_format(fig) == 1
    fmt = ax.xaxis.get_major_formatter()
    assert type(fmt) is PeriodDateFormatter
    assert fmt.show_offset is False and fmt._usetex is True
    assert ax.xaxis.get_major_locator() is locator


def test_matplotlib_flags_mark_what_someone_set():
    """The matplotlib 3.11 contract the defaults rely on.

    ``isDefault_majfmt`` / ``isDefault_majloc`` stay True on untouched date
    axes (plain, twinx, sharex, bars), turn False after ``set_major_*``, and
    live on the shared ticker, so setting them on one shared axes marks all.
    """

    def flags(a):
        return a.xaxis.isDefault_majfmt, a.xaxis.isDefault_majloc

    fig, ax = _dated(MONTHS)
    twin = ax.twinx()
    twin.plot(MONTHS, np.arange(len(MONTHS)))
    assert flags(ax) == flags(twin) == (True, True)
    fig, axes = plt.subplots(2, 1, sharex=True)
    for a in axes:
        a.plot(MONTHS, np.arange(len(MONTHS)))
    assert flags(axes[0]) == flags(axes[1]) == (True, True)
    fig, ax = plt.subplots()
    ax.bar(MONTHS, np.arange(len(MONTHS)), width=20)
    assert flags(ax) == (True, True)
    fig, ax = plt.subplots()
    ax.plot([2000, 3000], [1, 2])
    assert flags(ax) == (True, True)

    loc = mdates.AutoDateLocator()
    axes[1].xaxis.set_major_locator(loc)
    assert flags(axes[0]) == (True, False)
    axes[1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))
    assert flags(axes[0]) == flags(axes[1]) == (False, False)


@pytest.mark.parametrize("korean", [False, True], ids=["en", "ko"])
@pytest.mark.parametrize("data", [MONTHS, QUARTER_STARTS], ids=["m", "q"])
@pytest.mark.parametrize("width", ["6cm", "14.5cm"])
def test_matplotlib_concise_idiom_is_kept(data, korean, width):
    """``loc = AutoDateLocator(); ConciseDateFormatter(loc)`` is a choice.

    Formatter and locator stay the user's objects, untouched (no quarter
    locator, no thinning), and the ticks read matplotlib's own words, also
    in a Korean figure (review 2026-11-05, Important 2).
    """
    fig, ax = _dated(data, width, "매출" if korean else None, korean=korean)
    loc = mdates.AutoDateLocator()
    fmt = mdates.ConciseDateFormatter(loc)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(fmt)
    dm.simple_layout(fig)
    assert ax.xaxis.get_major_formatter() is fmt
    assert ax.xaxis.get_major_locator() is loc
    fresh = mdates.AutoDateLocator()
    assert (loc.minticks, loc.maxticks) == (fresh.minticks, fresh.maxticks)
    assert _xticks(ax) == _labels_of(ax, mdates.ConciseDateFormatter(loc))
    assert re.fullmatch(r"\d{4}", _xticks(ax)[0])


@pytest.mark.parametrize("data", [MONTHS, QUARTER_STARTS], ids=["m", "q"])
def test_date_axes_are_restyled_once(data):
    fig, ax = _dated(data)
    assert apply_default_tick_format(fig) == 1
    assert apply_default_tick_format(fig) == 0
    dm.simple_layout(fig)
    first = _xticks(ax)
    dm.simple_layout(fig)
    assert _xticks(ax) == first


def test_horizontal_quarter_bars_read_quarters():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "tall"))
    ax.barh(QUARTER_STARTS, np.arange(12) + 1, height=60)
    dm.simple_layout(fig)
    fig.canvas.draw()
    low, high = sorted(ax.yaxis.get_view_interval())
    labels = [
        label.get_text()
        for loc, label in zip(
            ax.yaxis.get_majorticklocs(),
            ax.yaxis.get_majorticklabels(),
            strict=True,
        )
        if low <= loc <= high and label.get_text()
    ]
    assert len(labels) >= 2
    assert all(PERIOD_QUARTER.fullmatch(t) for t in labels), labels


def test_period_four_digits():
    with dm.config.override(tick_years=4):
        assert _xticks(_laid_out(MONTHS))[0] == "2023.01"
        assert _xticks(_laid_out(QUARTER_STARTS))[0] == "2023.Q1"


# ---------------------------------------------------------------- categories

MONTHS_2024 = [f"2024-{m:02d}" for m in range(1, 13)]
QUARTERS_23_25 = [
    f"{y}-{m:02d}" for y in (2023, 2024, 2025) for m in (1, 4, 7, 10)
]
SALES = [5210, 5480, 5830, 6420, 6150, 6690, 7120, 7880, 7540, 8210, 8930, 9650]


def _category_bars(dates, width, *, korean=False, **kwargs):
    if korean:
        dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize(width, "wide"))
    ax.bar(range(len(dates)), np.linspace(5210, 9650, len(dates)))
    if korean:
        ax.set_ylabel("매출 (억원)")
    dm.format_axis_dates(ax, dates, **kwargs)
    dm.simple_layout(fig)
    return ax


def _capture_q(**kwargs):
    """The approved capture chart q: quarterly 원 bars, report-kr, 12 cm."""
    dm.style.use("report-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.bar(range(12), np.array(SALES) * 1e8, width=0.65)
    dm.format_axis_dates(ax, QUARTERS_23_25, **kwargs)
    ax.set_ylabel("매출 (원)")
    dm.format_axis_si(ax)  # the capture's 0.2T … 1.0T, whatever the default
    dm.simple_layout(fig)
    return ax


def test_category_dates_period():
    labels = _xticks(_category_bars(MONTHS_2024, "17cm"))
    assert labels[0] == "24.01"
    assert all(PERIOD_MONTH.fullmatch(t) for t in labels), labels

    ax = _category_bars(QUARTERS_23_25, "9cm")
    locs, labels = _ticks(ax)
    assert labels[0] == "23.Q1"
    assert all(PERIOD_QUARTER.fullmatch(t) for t in labels), labels
    assert ax.xaxis.get_major_locator().steps == (1, 2, 4, 8)
    assert _assert_quarter_rhythm(labels) > 1  # thinned, Q1 kept
    assert locs[0] == 0
    assert _min_gap_em(ax) >= 1.0


def test_category_quarters_match_the_approved_captures():
    """q-L2 and q-L1 (12 cm, report-kr, Korean label) tick texts."""
    assert _xticks(_capture_q()) == [
        "23.Q1",
        "23.Q3",
        "24.Q1",
        "24.Q3",
        "25.Q1",
        "25.Q3",
    ]
    assert _xticks(_capture_q(style="concise")) == [
        "23년",
        "Q2",
        "Q3",
        "Q4",
        "24년",
        "Q2",
        "Q3",
        "Q4",
        "25년",
        "Q2",
        "Q3",
        "Q4",
    ]


def test_category_quarters_not_starting_in_q1_keep_q1():
    dates = [*QUARTERS_23_25[1:], "2026-01", "2026-04"]  # 2023Q2 … 2026Q2
    labels = _xticks(_category_bars(dates, "6cm"))
    assert all(PERIOD_QUARTER.fullmatch(t) for t in labels), labels
    assert _assert_quarter_rhythm(labels) > 1


def test_category_dates_keep_todays_words_on_request():
    ax = _category_bars(MONTHS_2024, "17cm", years=4, style="concise")
    assert _xticks(ax) == [
        "2024",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    ax = _category_bars(QUARTERS_23_25, "17cm", years=4, style="concise")
    locs, labels = _ticks(ax)
    nums = mdates.date2num(np.array(QUARTERS_23_25, dtype="datetime64[s]"))
    stock = mdates.ConciseDateFormatter(mdates.AutoDateLocator())
    assert labels == stock.format_ticks([nums[round(p)] for p in locs])
    assert ax.xaxis.get_major_locator().steps[:3] == (1, 2, 3)


def test_category_dates_follow_config():
    with dm.config.override(tick_years=4, date_style="concise"):
        ax = _category_bars(MONTHS_2024, "17cm")
    assert _xticks(ax)[:2] == ["2024", "Feb"]
    with dm.config.override(date_style="concise"):
        ax = _category_bars(MONTHS_2024, "17cm")
    assert _xticks(ax)[:2] == ["24", "Feb"]


@pytest.mark.parametrize(
    "kwargs, field", [({"years": 3}, "years"), ({"style": "bogus"}, "style")]
)
def test_format_axis_dates_rejects_bad_years_or_style(kwargs, field):
    _, ax = plt.subplots()
    before = ax.xaxis.get_major_formatter()
    with pytest.raises(ValueError, match=field):
        dm.format_axis_dates(ax, MONTHS_2024, **kwargs)
    assert ax.xaxis.get_major_formatter() is before


# ---------------------------------------------------------------- helpers


def test_period_formatter_formats():
    fmt = PeriodDateFormatter(mdates.AutoDateLocator())
    assert fmt.formats == ["%y", "%y.%m", "%y.%m.%d", "%H:%M", "%H:%M", "%S.%f"]
    assert fmt.zero_formats == [
        "",
        "%y.%m",
        "%y.%m.%d",
        "%y.%m.%d",
        "%H:%M",
        "%H:%M",
    ]
    assert fmt.offset_formats == [
        "",
        "",
        "",
        "%y.%m.%d",
        "%y.%m.%d",
        "%y.%m.%d %H:%M",
    ]
    with pytest.raises(ValueError, match="digits"):
        PeriodDateFormatter(mdates.AutoDateLocator(), digits=3)  # type: ignore[arg-type]


def test_short_concise_words_drop_day_padding_not_year_padding():
    days = [mdates.date2num(datetime.datetime(2005, 3, d)) for d in (1, 8, 15)]
    assert ShortConciseDateFormatter(mdates.AutoDateLocator()).format_ticks(
        days
    ) == ["Mar", "8", "15"]
    years = [mdates.date2num(datetime.datetime(y, 1, 1)) for y in (2005, 2006)]
    assert ShortConciseDateFormatter(mdates.AutoDateLocator()).format_ticks(
        years
    ) == ["05", "06"]
    korean = KoreanConciseDateFormatter(mdates.AutoDateLocator(), digits=2)
    assert korean.format_ticks(days) == ["3월", "8일", "15일"]
    assert korean.get_offset() == "05년 3월"
    assert korean.format_ticks(years) == ["05년", "06년"]


def test_quarterly():
    starts = mdates.date2num(QUARTER_STARTS)
    assert quarterly(starts)
    assert quarterly(mdates.date2num(QUARTER_ENDS))
    assert quarterly(np.concatenate([starts, starts]))  # two series, same dates
    assert not quarterly(starts[:1])
    assert not quarterly(mdates.date2num(MONTHS))
    assert not quarterly(np.concatenate([starts, mdates.date2num(MONTHS)]))
    assert not quarterly(starts[::2])  # half-yearly


def test_plotted_dates():
    fig, ax = plt.subplots()
    ax.plot(QUARTER_STARTS[:4], [1, 2, 3, 4])
    ax.axhline(2)  # x in axes fractions
    ax.scatter(QUARTER_STARTS[4:6], [1, 2])
    ax.bar(QUARTER_STARTS[6:8], [1, 2], width=30)
    ax.fill_between(QUARTER_STARTS[:2], [0, 0], [1, 1])  # no offsets
    twin = ax.twinx()
    twin.plot(QUARTER_STARTS[8:], [1, 2, 3, 4])
    got = np.sort(plotted_dates(ax, "x"))
    np.testing.assert_allclose(got, mdates.date2num(QUARTER_STARTS))
    assert len(plotted_dates(ax, "y")) > 0  # the line's y values
    assert all(abs(v) < 10 for v in plotted_dates(ax, "y"))


def test_quarter_locator_and_words():
    locator = QuarterLocator()
    lo, hi = mdates.date2num(
        [np.datetime64("2023-02-01"), np.datetime64("2024-12-01")]
    )
    ticks = locator.tick_values(lo, hi)
    assert [mdates.num2date(t).strftime("%Y-%m-%d") for t in ticks] == [
        "2023-04-01",
        "2023-07-01",
        "2023-10-01",
        "2024-01-01",
        "2024-04-01",
        "2024-07-01",
        "2024-10-01",
    ]
    locator.step = 4
    assert [mdates.num2date(t).month for t in locator.tick_values(lo, hi)] == [
        1
    ]
    ends = QuarterLocator(anchor="end").tick_values(lo, hi)
    assert mdates.num2date(ends[0]).strftime("%Y-%m-%d") == "2023-03-31"
    with pytest.raises(ValueError, match="anchor"):
        QuarterLocator(anchor="middle")  # type: ignore[arg-type]

    moments = [datetime.datetime(2023, m, 1) for m in (4, 7, 10)]
    assert quarter_words(moments, style="period", digits=2, korean=False) == (
        ["23.Q2", "23.Q3", "23.Q4"],
        "",
    )
    assert quarter_words(moments, style="concise", digits=2, korean=True) == (
        ["Q2", "Q3", "Q4"],
        "23년",
    )
    century = [datetime.datetime(y, 1, 1) for y in (1923, 2023)]
    assert quarter_words(century, style="period", digits=2, korean=False)[
        0
    ] == ["1923.Q1", "2023.Q1"]
