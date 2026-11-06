"""How an axis's ticks print a number, for text that reads like them.

``tick_scale_of`` reads the decision the axis's formatter made at its last
draw; ``number_text`` prints a number the way the axis-wide formatters
print a tick; ``value_label_decimals`` is the value-label decimal rule.
``dm.label_bars`` is built on the three.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting import (
    TickScale,
    number_text,
    tick_scale_of,
    value_label_decimals,
)

MINUS = "\N{MINUS SIGN}"


pytestmark = pytest.mark.usefixtures("report_preset")


def _bars(values):
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.bar(range(len(values)), values)
    return fig, ax


def test_axis_unit_scale_has_no_suffix():
    fig, ax = _bars([21.4e9, 33.0e9])
    dm.axis_unit(ax, "y", label="Revenue (USD {unit})", ladder="finance")
    fig.canvas.draw()
    assert tick_scale_of(ax.yaxis, 21.4e9) == TickScale(1e9)


def test_suffix_formatters_give_unit_and_currency():
    fig, ax = _bars([12e9, 33e9])
    dm.simple_layout(fig)  # the library's default numbers: SI
    assert tick_scale_of(ax.yaxis, 12e9) == TickScale(1e9, "", "G")

    fig, ax = _bars([1.2e8, 3.4e8])
    dm.format_axis_myriad(ax, currency="$")
    fig.canvas.draw()
    assert tick_scale_of(ax.yaxis, 1.2e8) == TickScale(1e8, "$", "억")


@pytest.mark.parametrize(
    "install",
    [
        lambda ax: dm.format_axis_si(ax, decimals=1),
        lambda ax: dm.format_axis_myriad(ax, decimals=1),
        lambda ax: dm.format_axis_myriad(ax, decimals=1, currency="$"),
    ],
    ids=["si-1", "myriad-1", "myriad-1-currency"],
)
def test_unit_per_value_formatters_give_the_plain_scale(install):
    """``decimals=n`` of si and myriad with ``unit="max"`` give each tick its
    own unit (``800.0`` beside ``1.2M``): no unit is the axis's, so bar
    labels stay plain values (``1,250,000``) rather than borrow one."""
    fig, ax = _bars([1.25e6, 3.4e6])
    install(ax)
    fig.canvas.draw()
    assert tick_scale_of(ax.yaxis, 1.25e6) == TickScale()
    dm.label_bars(ax)
    fig.canvas.draw()
    assert [t.get_text() for t in ax.texts] == ["1,250,000", "3,400,000"]


@pytest.mark.parametrize(
    ("install", "scale"),
    [
        (
            lambda ax: dm.format_axis_millions(ax, decimals=1),
            TickScale(1e6, "", "M"),
        ),
        (
            lambda ax: dm.format_axis_billions(ax, suffix="bn", decimals=2),
            TickScale(1e9, "", "bn"),
        ),
        (
            lambda ax: dm.format_axis_currency(ax),
            TickScale(1.0, "$", "", zero="affixed"),
        ),
        (
            lambda ax: dm.format_axis_currency(
                ax, symbol="€", position="suffix", decimals=2
            ),
            TickScale(1.0, "", "€", zero="affixed"),
        ),
    ],
    ids=["millions-1", "billions-bn-2", "currency", "currency-suffix-2"],
)
def test_fixed_unit_formatters_give_their_unit(install, scale):
    """``decimals=n`` of millions / billions and ``format_axis_currency``
    write every tick in one unit: that unit, its currency and its zero
    rule, whatever the value. The axis-wide millions report the same."""
    fig, ax = _bars([1.25e6, 3.4e6])
    install(ax)
    for value in (1.25e6, -800.0, 0.0):
        assert tick_scale_of(ax.yaxis, value) == scale
    fig.canvas.draw()
    assert tick_scale_of(ax.yaxis, 1.25e6) == scale

    fig, ax = _bars([1.25e6, 3.4e6])
    dm.format_axis_millions(ax)  # axis-wide
    fig.canvas.draw()
    assert tick_scale_of(ax.yaxis, 1.25e6) == TickScale(1e6, "", "M")


def test_log_axis_scale_is_per_value():
    fig, ax = _bars([10.0, 2_000.0, 3e6])
    ax.set_yscale("log")
    dm.format_axis_si(ax)
    fig.canvas.draw()
    assert tick_scale_of(ax.yaxis, 2_000.0) == TickScale(1e3, "", "k")
    assert tick_scale_of(ax.yaxis, 3e6) == TickScale(1e6, "", "M")


def test_percent_and_other_formatters():
    fig, ax = _bars([0.31, 0.22])
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
    assert tick_scale_of(ax.yaxis, 0.31) == TickScale(0.01, "", "%")

    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:.1f} kg"))
    assert tick_scale_of(ax.yaxis, 0.31) == TickScale()
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
    assert tick_scale_of(ax.yaxis, 0.31) == TickScale()


def test_number_text_prints_like_a_tick():
    assert number_text(1234.5, 1) == "1,234.5"
    assert number_text(-3.5, 1) == f"{MINUS}3.5"
    assert number_text(-1.2, 1, prefix="$", suffix="B") == f"{MINUS}$1.2B"
    assert number_text(0.0, 2) == "0"
    assert number_text(-0.004, 2) == "0"  # rounds to zero: no sign
    assert number_text(0.0, 2, fixed=True) == "0.00"
    with matplotlib.rc_context({"axes.unicode_minus": False}):
        assert number_text(-3.5, 1) == "-3.5"
    # An affixed zero keeps prefix and suffix and never a sign.
    assert number_text(0.0, 0, prefix="$", zero="affixed") == "$0"
    assert number_text(-0.004, 2, suffix="€", zero="affixed") == "0€"
    assert (
        number_text(-0.004, 2, fixed=True, suffix="€", zero="affixed")
        == "0.00€"
    )
    assert number_text(-8.0, 0, prefix="$", zero="affixed") == f"{MINUS}$8"


def test_value_label_decimals():
    assert value_label_decimals([21.4, 18.0, 21.5]) == 1
    assert value_label_decimals([120.0, 135.0]) == 0
    assert value_label_decimals([1234.5678, 980.25]) == 0
    assert value_label_decimals([0.5234, 0.1]) == 3
    assert value_label_decimals([0.0, float("nan")]) == 0
    assert value_label_decimals([]) == 0
