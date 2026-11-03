"""dm.format_axis_dates: dated category positions read as the library's date words.

Pins the 2026-11-03 rule for crowded date labels under bars: the labels become
the concise date words a real date axis gets, dm.simple_layout thins them to
every 2nd, 3rd ... month until they are one em apart, and rotation stays the
last resort (the TICK_ROTATION check no longer fires on the result).
"""

from __future__ import annotations

import datetime
import random
from itertools import pairwise

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

import dartwork_mpl as dm
from dartwork_mpl.formatting._defaults import category_dates

MONTHS_2024 = [f"2024-{m:02d}" for m in range(1, 13)]
SALES = [1180, 1095, 1320, 1405, 1460, 1390, 1515, 1600, 1550, 1680, 1745, 1910]


@pytest.fixture(autouse=True)
def _restore_rc():
    """Each test sets its own preset; leave matplotlib's rc as it was."""
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _bars(preset: str, width: str, aspect: str, ylabel: str, dates=MONTHS_2024):
    """Twelve monthly bars labelled with format_axis_dates, laid out."""
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize(width, aspect))
    ax.bar(range(len(dates)), SALES[: len(dates)])
    ax.set_ylabel(ylabel)
    dm.format_axis_dates(ax, dates)
    return fig, ax


def _shown(ax: Axes) -> tuple[list[float], list[str]]:
    """Positions and texts of the x tick labels drawn, after a draw."""
    ax.figure.canvas.draw()
    ticks = [t for t in ax.xaxis.get_major_ticks() if t.label1.get_text()]
    return [t.get_loc() for t in ticks], [t.label1.get_text() for t in ticks]


def _min_gap_em(ax: Axes) -> float:
    """Smallest horizontal gap between drawn x labels, in ems of their font."""
    fig = ax.figure
    renderer = fig.canvas.get_renderer()
    labels = [
        t.label1 for t in ax.xaxis.get_major_ticks() if t.label1.get_text()
    ]
    boxes = sorted(
        (lab.get_window_extent(renderer) for lab in labels), key=lambda b: b.x0
    )
    em = labels[0].get_fontsize() * fig.dpi / 72.0
    return min(b.x0 - a.x1 for a, b in pairwise(boxes)) / em


def test_months_read_as_concise_words_when_they_fit() -> None:
    """A wide English axis keeps all twelve months: 2024, Feb … Dec."""
    fig, ax = _bars("report", "17cm", "standard", "Sales")
    dm.simple_layout(fig)
    locs, texts = _shown(ax)
    assert locs == list(range(12))
    assert texts == [
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


def test_korean_figure_thins_to_every_second_month() -> None:
    """The e10 draft (report-kr, 12 cm): 2024년, 3월 … 11월, one em apart."""
    fig, ax = _bars("report-kr", "12cm", "golden", "매출액 (억원)")
    dm.simple_layout(fig)
    locs, texts = _shown(ax)
    assert locs == [0, 2, 4, 6, 8, 10]
    assert texts == ["2024년", "3월", "5월", "7월", "9월", "11월"]
    assert _min_gap_em(ax) >= 1.0


def test_bars_and_limits_stay_where_they_were() -> None:
    """Only the tick positions and words change, not the bars or the view."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "golden"))
    bars = ax.bar(range(12), SALES)
    before = (ax.get_xlim(), [b.get_x() for b in bars])
    dm.format_axis_dates(ax, MONTHS_2024)
    assert (ax.get_xlim(), [b.get_x() for b in bars]) == before


def test_rotated_labels_are_left_alone() -> None:
    """Someone who rotated the labels keeps every month labelled."""
    fig, ax = _bars("report-kr", "12cm", "golden", "매출액 (억원)")
    dm.rotate_tick_labels(ax)
    dm.simple_layout(fig)
    locs, _ = _shown(ax)
    assert locs == list(range(12))


def test_axis_too_narrow_for_any_step_keeps_every_month() -> None:
    """With no step that leaves two labels one em apart, nothing is dropped."""
    fig, ax = _bars("report-kr", "2.5cm", "standard", "매출액 (억원)")
    dm.simple_layout(fig)
    locs, _ = _shown(ax)
    assert locs == list(range(12))


def test_year_goes_to_the_corner_when_no_january_is_shown() -> None:
    """Mar … Dec 2024 has no January tick, so the year is the corner label."""
    dates = MONTHS_2024[2:]
    fig, ax = _bars("report", "17cm", "standard", "Sales", dates=dates)
    dm.simple_layout(fig)
    _, texts = _shown(ax)
    assert texts[0] == "Mar"
    assert ax.xaxis.get_offset_text().get_text() == "2024"


def test_a_view_without_january_still_names_the_year() -> None:
    """Review 2026-11-03: a January outside the view must not take the year.

    Twelve months with the view cut to Feb … Dec: the words and the corner
    label come from the dates in view, so 2024 is still on the axis.
    """
    fig, ax = _bars("report", "17cm", "standard", "Sales")
    ax.set_xlim(0.5, 11.5)
    dm.simple_layout(fig)
    locs, texts = _shown(ax)
    assert locs == list(range(1, 12))
    assert texts[0] == "Feb"
    assert ax.xaxis.get_offset_text().get_text() == "2024"


def test_a_crowded_view_thins_over_the_dates_in_view() -> None:
    """Property: whatever slice of 36 months is in view, labels sit 1 em apart.

    Seeded loop over views of a 36-month Korean axis on 12 cm: after layout
    every drawn label is a date in view, under a bar, and the gap rule holds
    whenever two or more labels are drawn and some step fits.
    """
    months = [f"{2022 + m // 12}-{m % 12 + 1:02d}" for m in range(36)]
    rng = random.Random(1103)
    for _ in range(6):
        lo = rng.randrange(0, 20)
        hi = rng.randrange(lo + 6, 36)
        with matplotlib.rc_context():
            dm.style.use("report-kr")
            fig, ax = plt.subplots(figsize=dm.figsize("12cm", "golden"))
            ax.bar(range(36), range(36))
            ax.set_ylabel("매출액 (억원)")
            dm.format_axis_dates(ax, months)
            ax.set_xlim(lo - 0.5, hi + 0.5)
            dm.simple_layout(fig)
            locs, texts = _shown(ax)
            assert locs and all(lo <= p <= hi for p in locs), (lo, hi, locs)
            assert all(float(p).is_integer() for p in locs)
            years = {m[:4] for m in months[lo : hi + 1]}
            shown = " ".join(texts) + ax.xaxis.get_offset_text().get_text()
            assert any(y in shown for y in years), (lo, hi, texts)
            if len(locs) >= 2 and locs[1] - locs[0] > 1:
                assert _min_gap_em(ax) >= 1.0, (lo, hi, texts)
            plt.close(fig)


def test_tick_rotation_check_is_quiet_on_the_result() -> None:
    """The library's own overlap advice is satisfied, so it does not fire."""
    fig, ax = _bars("report-kr", "12cm", "golden", "매출액 (억원)")
    dm.simple_layout(fig)
    found = dm.validate_figure(fig, checks=("TICK_ROTATION",), quiet=True)
    assert [w for w in found if w.check_id == "TICK_ROTATION"] == []


@pytest.mark.parametrize(
    "dates",
    [
        ["2024/01"],
        ["Jan"],
        [None],
        ["2024-01", "not a date"],
        [],
        [2024, 2025],
        np.array([2024, 2025]),
        ["2024-01", 3],
        [True],
    ],
    ids=[
        "slashes",
        "month-name",
        "none",
        "one-bad",
        "empty",
        "bare-years",
        "int-array",
        "mixed-number",
        "bool",
    ],
)
def test_values_that_are_not_dates_are_refused(dates) -> None:
    """Anything but a date per position is a caller error, named in the message."""
    dm.style.use("report")
    _, ax = plt.subplots()
    with pytest.raises(ValueError, match="format_axis_dates"):
        dm.format_axis_dates(ax, dates)


def test_axis_other_than_x_or_y_is_refused() -> None:
    """``axis`` is "x" or "y"; "both" makes no sense for categories."""
    _, ax = plt.subplots()
    with pytest.raises(ValueError, match="axis must be"):
        dm.format_axis_dates(ax, MONTHS_2024, axis="both")  # type: ignore[arg-type]


def test_iso_strings_and_datetimes_read_as_the_same_dates() -> None:
    """Property: any datetime, as itself or as ISO text, reads back unchanged.

    Seeded loop over 300 random second-resolution datetimes between 1900 and
    2100 (no Hypothesis in the project's dependencies).
    """
    rng = random.Random(20261103)
    start = datetime.datetime(1900, 1, 1)
    for _ in range(300):
        moment = start + datetime.timedelta(
            seconds=rng.randrange(200 * 365 * 86_400)
        )
        expected = np.datetime64(moment, "s")
        for form in (moment, moment.isoformat(), np.datetime64(moment)):
            got = category_dates([form])
            assert got.dtype == np.dtype("datetime64[s]"), form
            assert got[0] == expected, (form, got[0], expected)


@pytest.mark.parametrize("unit", ["ns", "us", "ms", "s", "D", "M"])
def test_datetime64_arrays_of_any_unit_keep_their_dates(unit: str) -> None:
    """Review 2026-11-03: a datetime64[ns] array (pandas' unit) read as seconds.

    The array and a pandas Series of it give the same dates as the ISO text.
    """
    pd = pytest.importorskip("pandas")
    dates = np.array(MONTHS_2024, dtype=f"datetime64[{unit}]")
    expected = category_dates(MONTHS_2024)
    for form in (dates, pd.Series(dates), pd.DatetimeIndex(dates)):
        got = category_dates(form)
        assert got.dtype == np.dtype("datetime64[s]")
        assert (got == expected).all(), (unit, type(form), got[:2])


def test_any_text_is_read_or_refused_never_crashes() -> None:
    """Property: random short text is a date or a ValueError, nothing else."""
    rng = random.Random(7)
    alphabet = "0123456789-/: TZabcJan년월"
    for _ in range(500):
        text = "".join(
            rng.choice(alphabet) for _ in range(rng.randrange(0, 12))
        )
        try:
            got = category_dates([text])
        except ValueError:
            continue
        assert not np.isnat(got[0]), text
