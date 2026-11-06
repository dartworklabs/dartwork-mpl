"""Secondary axes read their numbers the way their parent reads its own.

``ax.secondary_yaxis("right")`` over a price line of 1,500-2,400 printed
``1600 … 2400`` beside the parent's ``1,600 … 2,400``, and over 0-3M
``0.0 … 3.0`` under ``1e6`` beside ``0.5M``: matplotlib keeps secondary axes
out of ``fig.axes``, so the library's numbers never reached them (diagnosis
D, bug 1, 2026-11-06). A secondary axis whose functions are affine over its
view (the same values, ``x1.3``, degrees C to F) shows the same kind of
quantity on a linear scale, and gets the same numbers under the same rules.
Others (``1 / x``) keep matplotlib's, as log axes do.

``dm.format_axis_si`` on such a secondary printed a unit per tick (``500k,
1M, 1.5M``): its ``"function"`` scale counted as non-linear (S5).
"""

from __future__ import annotations

import warnings

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.transforms as mtransforms
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._axis_wide import SI_LADDER, AxisUnitFormatter
from dartwork_mpl.formatting._defaults import (
    DefaultNumberFormatter,
    apply_default_tick_format,
)
from dartwork_mpl.formatting._years import YearTickFormatter


@pytest.fixture(autouse=True)
def _scientific_preset():
    with matplotlib.rc_context():
        dm.style.use("scientific")
        yield
    plt.close("all")


def _on(axis) -> tuple[list[float], list[str]]:
    """In-view major tick locations and texts of ``axis``, after a draw.

    A right or top secondary axis prints on its second label.
    """
    axis.axes.get_figure(root=True).canvas.draw()
    low, high = sorted(axis.get_view_interval())
    pairs = [
        (float(loc), tick.label1.get_text() or tick.label2.get_text())
        for loc, tick in zip(
            axis.get_majorticklocs(), axis.get_major_ticks(), strict=False
        )
        if low <= loc <= high
    ]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def _labels(axis) -> list[str]:
    return _on(axis)[1]


def _reads_its_value(loc: float, text: str) -> bool:
    return float(text.replace(",", "")) == pytest.approx(loc)


X = np.arange(60)
PRICE = np.linspace(1500, 2400, 60)


def _price(functions=None):
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot(X, PRICE)
    if functions is None:
        secondary = ax.secondary_yaxis("right")
    else:
        secondary = ax.secondary_yaxis("right", functions=functions)
    return fig, ax, secondary


def test_an_identity_secondary_reads_like_its_parent():
    fig, ax, secondary = _price()
    dm.simple_layout(fig)
    parent = _on(ax.yaxis)
    assert _on(secondary.yaxis) == parent
    assert all("," in t for t in parent[1]), parent  # 1,600 … 2,400
    assert isinstance(secondary.yaxis.get_major_formatter(), DefaultNumberFormatter)
    assert apply_default_tick_format(fig) == 0  # nothing left to install


def test_a_scaled_secondary_gets_separators():
    fig, _ax, secondary = _price((lambda v: v * 1.3, lambda v: v / 1.3))
    dm.simple_layout(fig)
    locs, labels = _on(secondary.yaxis)
    assert max(locs) >= 3000, locs
    assert all("," in t for t in labels), labels  # 2,000 … 3,200
    assert all(map(_reads_its_value, locs, labels)), labels


def test_a_secondary_x_axis_gets_separators():
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot(np.linspace(0, 5000, 50), np.linspace(0, 1, 50))
    top = ax.secondary_xaxis("top")
    dm.simple_layout(fig)
    assert _on(top.xaxis) == _on(ax.xaxis)
    assert "1,000" in _labels(top.xaxis), _labels(top.xaxis)


@pytest.mark.parametrize(
    ("ylabel", "unit"), [("Population", "M"), ("인구", "만")], ids=["si", "myriad"]
)
def test_a_secondary_over_millions_takes_the_parents_unit(ylabel, unit):
    if unit == "만":
        dm.style.use("scientific-kr")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot(X, np.linspace(0, 3e6, 60))
    ax.set_ylabel(ylabel)
    secondary = ax.secondary_yaxis("right")
    dm.simple_layout(fig)
    labels = _labels(secondary.yaxis)
    assert labels == _labels(ax.yaxis)
    assert all(t == "0" or t.endswith(unit) for t in labels), labels
    assert ("0.5M" if unit == "M" else "300만") in labels, labels
    assert secondary.yaxis.get_offset_text().get_text() == ""


def test_a_secondary_someone_formatted_keeps_its_formatter():
    fig, _ax, secondary = _price()
    chosen = mticker.FormatStrFormatter("%d")
    secondary.yaxis.set_major_formatter(chosen)
    dm.simple_layout(fig)
    assert secondary.yaxis.get_major_formatter() is chosen
    assert all("," not in t for t in _labels(secondary.yaxis))


@pytest.mark.parametrize("values", [PRICE, np.linspace(0, 3e6, 60)], ids=["price", "millions"])
def test_plain_asked_of_a_secondary_reads_as_on_its_parent(values):
    """``ticklabel_format(style="plain")`` before the layout: the same rule.

    Met by the library's numbers on a ``1,600`` axis; a ``0.5M`` axis asked
    for plain full numbers keeps matplotlib's formatter (``3000000``).
    """
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot(X, values)
    secondary = ax.secondary_yaxis("right")
    ax.ticklabel_format(axis="y", style="plain")
    secondary.ticklabel_format(axis="y", style="plain")
    dm.simple_layout(fig)
    assert _labels(secondary.yaxis) == _labels(ax.yaxis)
    assert type(secondary.yaxis.get_major_formatter()) is type(
        ax.yaxis.get_major_formatter()
    )


def test_a_reciprocal_secondary_keeps_matplotlibs():
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot(X, np.linspace(0.001, 1, 60))
    secondary = ax.secondary_yaxis(
        "right", functions=(lambda v: 1 / v, lambda v: 1 / v)
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # 1 / 0 at draw
        dm.simple_layout(fig)
    assert type(secondary.yaxis.get_major_formatter()) is mticker.ScalarFormatter


def test_a_secondary_over_elevations_keeps_matplotlibs():
    """X ticks all in 1000-2999 that are not years (``1950.3 …``) keep theirs."""
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot(np.linspace(1950.3, 2010.7, 30), np.arange(30))
    top = ax.secondary_xaxis("top")
    dm.simple_layout(fig)
    assert type(top.xaxis.get_major_formatter()) is mticker.ScalarFormatter
    assert type(ax.xaxis.get_major_formatter()) is mticker.ScalarFormatter


def test_a_secondary_showing_years_reads_years():
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot(np.arange(2000, 2025), np.arange(25))
    top = ax.secondary_xaxis("top")
    dm.simple_layout(fig)
    assert isinstance(top.xaxis.get_major_formatter(), YearTickFormatter)
    assert _on(top.xaxis) == _on(ax.xaxis)


def test_secondary_functions_that_fail_leave_the_axis_alone():
    """The functions run under the same safety contract as for year data.

    A ``Transform`` given as functions fails on 1-D values, and ``1 / x``
    meets 0: no warning, no error, matplotlib's formatter stays.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        ax.plot(X, PRICE)
        shifted = ax.secondary_yaxis(
            "right", functions=mtransforms.Affine2D().translate(0, 1)
        )
        assert apply_default_tick_format(fig) == 1  # the parent only
        assert (
            type(shifted.yaxis.get_major_formatter()) is mticker.ScalarFormatter
        )

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        ax.plot(np.linspace(-1000, 1000, 11), np.arange(11))
        top = ax.secondary_xaxis(
            "top", functions=(lambda v: 1 / v, lambda v: 1 / v)
        )
        apply_default_tick_format(fig)
        assert type(top.xaxis.get_major_formatter()) is mticker.ScalarFormatter


def test_format_axis_si_on_an_affine_secondary_takes_one_unit():
    """S5: ``0.5M … 3.0M`` on both sides, not ``500k, 1M, 1.5M``."""
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot(X, np.linspace(0, 3e6, 60))
    secondary = ax.secondary_yaxis("right")
    dm.format_axis_si(ax, "y")
    dm.format_axis_si(secondary, "y")
    dm.simple_layout(fig)
    labels = _labels(secondary.yaxis)
    assert labels == _labels(ax.yaxis)
    assert all(t == "0" or t.endswith("M") for t in labels), labels


def test_an_affine_function_scale_reads_as_linear():
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot(X, np.linspace(0, 3e6, 60))
    ax.set_yscale("function", functions=(lambda v: v * 2, lambda v: v / 2))
    dm.format_axis_si(ax, "y")
    labels = _labels(ax.yaxis)
    assert all(t == "0" or t.endswith("M") for t in labels), labels


def test_a_reciprocal_secondary_keeps_a_unit_per_tick():
    """Ticks spanning decades on a non-affine scale keep their own units."""
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    ax.plot(X, np.linspace(1e-4, 1e-2, 60))
    secondary = ax.secondary_yaxis(
        "right", functions=(lambda v: 1 / v, lambda v: 1 / v)
    )
    secondary.yaxis.set_major_formatter(AxisUnitFormatter(SI_LADDER))
    secondary.yaxis.set_major_locator(mticker.FixedLocator([100, 1000, 5000]))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        fig.canvas.draw()
    assert secondary.yaxis.get_major_formatter().format_ticks(
        [100, 1000, 5000]
    ) == ["100", "1k", "5k"]
