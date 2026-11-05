"""``ax.ticklabel_format`` on a year axis, before or after ``dm.simple_layout``.

The year formatter is a matplotlib ``ScalarFormatter``: ``ticklabel_format``
and the ``set_useOffset`` / ``set_scientific`` / ``set_powerlimits`` /
``set_useMathText`` / ``set_useLocale`` calls behind it work on it, and what
was asked of matplotlib's own formatter before the layout carries over, so
both orders draw the same ticks.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._years import (
    WholeYearLocator,
    YearTickFormatter,
    requested_format,
)

YEARS = np.arange(2014, 2025)


@pytest.fixture(autouse=True)
def _report_preset():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _shown(ax) -> tuple[list[float], list[str], str]:
    """In-view x tick locations and texts, and the offset text, after a draw."""
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
    offset = ax.xaxis.get_offset_text().get_text()
    return [p[0] for p in pairs], [p[1] for p in pairs], offset


def _year_line(request: dict, order: str):
    """Annual line; ``ticklabel_format(**request)`` before or after the layout."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot(YEARS, np.arange(len(YEARS)))
    if order == "before":
        ax.ticklabel_format(axis="x", **request)
        dm.simple_layout(fig)
    else:
        dm.simple_layout(fig)
        ax.ticklabel_format(axis="x", **request)
    return ax


def _two_digits(locs) -> list[str]:
    return [f"{round(v) % 100:02d}" for v in locs]


def _matplotlib_reads(ax, request: dict) -> tuple[list[str], str]:
    """What matplotlib's own ScalarFormatter prints for the same ticks.

    Configured the way ``ticklabel_format`` configures one, on the same axis
    and ticks, starting without an offset, as the year axis does.
    """
    oracle = mticker.ScalarFormatter(useOffset=False)
    oracle.set_axis(ax.xaxis)
    style = request.get("style")
    if style is not None:
        oracle.set_scientific(style in ("sci", "scientific"))
    if "scilimits" in request:
        oracle.set_powerlimits(request["scilimits"])
    if "useOffset" in request:
        oracle.set_useOffset(request["useOffset"])
    if "useMathText" in request:
        oracle.set_useMathText(request["useMathText"])
    locs = list(ax.xaxis.get_majorticklocs())
    labels = oracle.format_ticks(locs)
    low, high = sorted(ax.xaxis.get_view_interval())
    shown = [t for v, t in zip(locs, labels, strict=True) if low <= v <= high]
    return shown, oracle.get_offset()


ORDERS = ["before", "after"]


@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize(
    "request_",
    [{"useOffset": False}, {"style": "plain"}, {"style": "sci"}],
    ids=["useOffset-False", "plain", "sci-default-limits"],
)
def test_requests_years_already_meet_keep_two_digit_years(order, request_):
    """No offset, no exponent: what a year label already is.

    ``useOffset=False`` and ``style="plain"`` ask for neither; ``style="sci"``
    with the default power limits puts no exponent on 2014-2024 in
    matplotlib either. The axis keeps whole years in two digits. After the
    layout these raised ``AttributeError: This method only works with the
    ScalarFormatter`` (follow-up F3).
    """
    ax = _year_line(request_, order)
    locs, labels, offset = _shown(ax)
    assert isinstance(ax.xaxis.get_major_formatter(), YearTickFormatter)
    assert isinstance(ax.xaxis.get_major_locator(), WholeYearLocator)
    assert len(locs) >= 3 and labels == _two_digits(locs), labels
    assert offset == ""


@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize(
    "request_",
    [
        {"style": "sci", "scilimits": (0, 0)},
        {"scilimits": (0, 0)},
        {"style": "sci", "scilimits": (0, 0), "useMathText": True},
        {"useOffset": 2000},
    ],
    ids=["sci-0-0", "scilimits-only", "sci-mathtext", "fixed-offset"],
)
def test_an_exponent_or_offset_asked_for_reads_as_matplotlib_writes_it(
    order, request_
):
    """A year label cannot carry an exponent or an offset: matplotlib's does.

    The ticks stay on whole years; their text and the corner label are what
    matplotlib's ScalarFormatter writes with the same settings. Before the
    layout, the request was dropped when the year formatter replaced
    matplotlib's (the axis read ``14 … 24``).
    """
    ax = _year_line(request_, order)
    locs, labels, offset = _shown(ax)
    assert isinstance(ax.xaxis.get_major_locator(), WholeYearLocator)
    assert all(abs(v - round(v)) < 1e-9 for v in locs), locs
    expected_labels, expected_offset = _matplotlib_reads(ax, request_)
    assert (labels, offset) == (expected_labels, expected_offset)
    assert offset != ""


@pytest.mark.parametrize(
    "request_",
    [
        {"useOffset": False},
        {"style": "sci", "scilimits": (0, 0)},
        {"useOffset": 2000},
    ],
    ids=["useOffset-False", "sci-0-0", "fixed-offset"],
)
def test_both_orders_draw_the_same_ticks(request_):
    before = _shown(_year_line(request_, "before"))
    after = _shown(_year_line(request_, "after"))
    assert before == after


def test_a_request_after_the_layout_survives_another_layout():
    ax = _year_line({"style": "sci", "scilimits": (0, 0)}, "after")
    first = _shown(ax)
    dm.simple_layout(ax.figure)
    assert _shown(ax) == first


def test_requested_format_reads_what_someone_changed():
    def configured(**request):
        fig, ax = plt.subplots()
        ax.plot(YEARS, YEARS)
        if request:
            ax.ticklabel_format(axis="x", **request)
        return ax.xaxis.get_major_formatter()

    assert requested_format(configured()) == {}
    assert requested_format(configured(useOffset=False)) == {"useOffset": False}
    assert requested_format(configured(useOffset=2000)) == {"useOffset": 2000}
    assert requested_format(configured(style="plain")) == {"scientific": False}
    assert requested_format(configured(scilimits=(0, 0))) == {
        "powerlimits": (0, 0)
    }
    assert requested_format(configured(useMathText=True)) == {
        "useMathText": True
    }
    assert requested_format(configured(useLocale=True)) == {"useLocale": True}
    assert requested_format(mticker.FuncFormatter(lambda v, p: "")) == {}


def test_year_formatter_is_matplotlibs_scalar_formatter():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot(YEARS, np.arange(len(YEARS)))
    dm.simple_layout(fig)
    fmt = ax.xaxis.get_major_formatter()
    assert isinstance(fmt, mticker.ScalarFormatter)
    assert fmt.get_useOffset() is False
    carried = YearTickFormatter(2, useOffset=2000, scientific=False)
    assert carried.get_useOffset() is False and carried.offset == 2000
