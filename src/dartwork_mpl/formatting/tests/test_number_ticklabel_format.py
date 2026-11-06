"""``ax.ticklabel_format`` on an axis with the library's default numbers.

An untouched axis reaching 1,000 gets ``DefaultNumberFormatter``
(``1,750``; ``0.5M``). ``ax.ticklabel_format()`` (``axis="both"``) after
``dm.simple_layout`` raised ``AttributeError: This method only works with
the ScalarFormatter`` on it, and before the layout a request made of
matplotlib's formatter in place was replaced. Now, as on year axes:
``useOffset=False`` and ``style="plain"`` (no offset, no exponent: what
these numbers already are) keep the library's numbers; a request for
matplotlib's own notation (scientific, power limits, an offset) gets
matplotlib's ScalarFormatter, in either order.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._defaults import DefaultNumberFormatter
from dartwork_mpl.formatting._years import YearTickFormatter

YEARS = np.arange(2014, 2025)
VALUES = np.linspace(12_000, 48_000, len(YEARS))


@pytest.fixture(autouse=True)
def _report_preset():
    with matplotlib.rc_context():
        dm.style.use("report")
        yield
    plt.close("all")


def _y(ax) -> tuple[list[str], str]:
    """In-view y tick texts and the y offset text, after a draw."""
    ax.figure.canvas.draw()
    low, high = sorted(ax.yaxis.get_view_interval())
    labels = [
        t.get_text()
        for loc, t in zip(
            ax.yaxis.get_majorticklocs(),
            ax.yaxis.get_majorticklabels(),
            strict=True,
        )
        if low <= loc <= high
    ]
    return labels, ax.yaxis.get_offset_text().get_text()


def _chart(request: dict, order: str, axis: str = "both"):
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot(YEARS, VALUES)
    if order == "before":
        ax.ticklabel_format(axis=axis, **request)
        dm.simple_layout(fig)
    else:
        dm.simple_layout(fig)
        ax.ticklabel_format(axis=axis, **request)
    return ax


ORDERS = ["before", "after"]


@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize(
    "request_",
    [{"useOffset": False}, {"style": "plain"}],
    ids=["useOffset-False", "plain"],
)
def test_requests_the_numbers_already_meet_keep_them(order, request_):
    ax = _chart(request_, order)
    labels, offset = _y(ax)
    assert isinstance(ax.yaxis.get_major_formatter(), DefaultNumberFormatter)
    assert isinstance(ax.xaxis.get_major_formatter(), YearTickFormatter)
    assert labels and all("," in t for t in labels if t != "0"), labels
    assert offset == ""


def _matplotlib_reads(ax, request: dict) -> tuple[list[str], str]:
    """matplotlib's ScalarFormatter, configured as ticklabel_format does."""
    oracle = mticker.ScalarFormatter()
    oracle.set_axis(ax.yaxis)
    if "style" in request:
        oracle.set_scientific(request["style"] in ("sci", "scientific"))
    if "scilimits" in request:
        oracle.set_powerlimits(request["scilimits"])
    if "useOffset" in request:
        oracle.set_useOffset(request["useOffset"])
    locs = list(ax.yaxis.get_majorticklocs())
    labels = oracle.format_ticks(locs)
    low, high = sorted(ax.yaxis.get_view_interval())
    shown = [t for v, t in zip(locs, labels, strict=True) if low <= v <= high]
    return shown, oracle.get_offset()


@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize(
    "request_",
    [
        {"style": "sci", "scilimits": (0, 0)},
        {"scilimits": (3, 3)},
        {"useOffset": 10_000},
    ],
    ids=["sci-0-0", "fixed-exponent", "fixed-offset"],
)
def test_matplotlibs_notation_asked_for_reads_as_matplotlib_writes_it(
    order, request_
):
    ax = _chart(request_, order, axis="y")
    assert isinstance(ax.yaxis.get_major_formatter(), mticker.ScalarFormatter)
    assert _y(ax) == _matplotlib_reads(ax, request_)
    assert _y(ax)[1] != ""


def test_axis_both_after_the_layout_reaches_every_axis():
    """The idiom ``ax.ticklabel_format(useOffset=False)`` no longer raises."""
    ax = _chart({"useOffset": False}, "after")
    ax.ticklabel_format(style="sci", scilimits=(0, 0))  # both axes
    assert isinstance(ax.yaxis.get_major_formatter(), mticker.ScalarFormatter)
    labels, offset = _y(ax)
    assert offset != "" and not any("," in t for t in labels), labels


def test_both_orders_draw_the_same_ticks():
    for request_ in (
        {"useOffset": False},
        {"style": "sci", "scilimits": (0, 0)},
    ):
        assert _y(_chart(request_, "before")) == _y(_chart(request_, "after"))


def _oracle(ax, *calls) -> tuple[list[str], str]:
    """matplotlib's ScalarFormatter after the same setter calls, in order."""
    oracle = mticker.ScalarFormatter()
    oracle.set_axis(ax.yaxis)
    for name, value in calls:
        getattr(oracle, f"set_{name}")(value)
    locs = list(ax.yaxis.get_majorticklocs())
    labels = oracle.format_ticks(locs)
    low, high = sorted(ax.yaxis.get_view_interval())
    shown = [t for v, t in zip(locs, labels, strict=True) if low <= v <= high]
    return shown, oracle.get_offset()


def test_a_kept_setting_is_replayed_when_the_axis_is_handed_over():
    """``style="plain"`` then ``scilimits=(0, 0)`` stays plain, as in matplotlib.

    Review of PR #595, item 3 (Codex P2): the plain request was accepted
    without a handoff and forgotten, so the later ``scilimits`` handed the
    axis to a fresh ScalarFormatter with scientific notation on.
    """
    for calls in (
        [{"style": "plain"}, {"scilimits": (0, 0)}],
        [{"style": "plain", "scilimits": (0, 0)}],
    ):
        ax = _chart({}, "after", axis="y")
        for request_ in calls:
            ax.ticklabel_format(axis="y", **request_)
        expected = _oracle(ax, ("scientific", False), ("powerlimits", (0, 0)))
        assert _y(ax) == expected, calls
        assert _y(ax)[1] == "" and "1e4" not in "".join(_y(ax)[0])


MILLIONS = np.array([500_000, 900_000, 1_200_000, 2_500_000, 3_000_000])


@pytest.mark.parametrize("order", ORDERS)
def test_plain_on_a_unit_axis_prints_full_numbers(order):
    """``style="plain"`` on ``0.5M … 3.0M`` asks for no scaling: full numbers.

    Review of PR #595, item 6: the request was met by keeping the units.
    """
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot(np.arange(len(MILLIONS)), MILLIONS)
    if order == "before":
        ax.ticklabel_format(axis="y", style="plain")
        dm.simple_layout(fig)
    else:
        dm.simple_layout(fig)
        ax.ticklabel_format(axis="y", style="plain")
    labels, offset = _y(ax)
    assert not any("M" in t for t in labels), labels
    assert (labels, offset) == _oracle(ax, ("scientific", False))


THOUSANDS = np.array([1200.0, 1500.0, 1750.0])


def _split(first: dict, second: dict, values=THOUSANDS):
    """``first`` asked before dm.simple_layout, ``second`` after it."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot(np.arange(len(values)), values)
    ax.ticklabel_format(axis="y", **first)
    dm.simple_layout(fig)
    ax.ticklabel_format(axis="y", **second)
    return ax


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ({"style": "plain"}, {"scilimits": (0, 0)}),
        ({"scilimits": (0, 0)}, {"style": "plain"}),
    ],
    ids=["plain-then-scilimits", "scilimits-then-plain"],
)
def test_a_request_before_the_layout_counts_with_one_after_it(first, second):
    """Re-review of PR #595, item 3: settings asked before the layout and met
    by the library's numbers were not remembered, so ``style="plain"``
    before and ``scilimits=(0, 0)`` after printed ``1.1 … 1.9`` under
    ``×1e3``; matplotlib alone prints ``1100 … 1900``.
    """
    ax = _split(first, second)
    calls = [("scientific", False), ("powerlimits", (0, 0))]
    if "scilimits" in first:
        calls.reverse()  # matplotlib applies them in the order asked
    assert _y(ax) == _oracle(ax, *calls)
    assert _y(ax)[1] == ""  # plain: no exponent in either order


def test_plain_kept_when_the_axis_later_reaches_millions():
    """``style="plain"`` met on 1,750 still holds when the view reaches 3M."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot([0, 1, 2], THOUSANDS)
    dm.simple_layout(fig)
    ax.ticklabel_format(axis="y", style="plain")
    ax.set_ylim(0, 3_000_000)
    labels, offset = _y(ax)
    assert offset == "" and not any("M" in t for t in labels), labels
    assert "3,000,000" in labels, labels
