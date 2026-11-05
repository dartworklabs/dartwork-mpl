"""Two-digit years on untouched integer year axes."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.formatting._years import (
    YearTickFormatter,
    is_year_axis,
    two_digits_repeat,
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


def _line(x, ylabel=None, ticks=None):
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot(x, np.linspace(1, 3, len(x)))
    # Fixed locations keep the tick count independent of font and canvas.
    ax.set_xticks(np.arange(2016, 2025, 2) if ticks is None else ticks)
    if ylabel:
        ax.set_ylabel(ylabel)
    dm.simple_layout(fig)
    return ax


def test_untouched_year_axis_two_digits():
    ax = _line(np.arange(2016, 2025))
    assert _xticks(ax) == ["16", "18", "20", "22", "24"]


def test_korean_period_year_axis_has_no_suffix():
    assert _xticks(_line(np.arange(2016, 2025), "매출")) == [
        "16",
        "18",
        "20",
        "22",
        "24",
    ]
    with dm.config.override(date_style="concise"):
        ax = _line(np.arange(2016, 2025), "매출")
        assert _xticks(ax) == ["16년", "18년", "20년", "22년", "24년"]


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
    labels = _xticks(
        _line(np.arange(1880, 2025), ticks=np.arange(1900, 2025, 20))
    )
    assert labels and all(len(t) == 4 for t in labels)
    assert len(set(labels)) == len(labels)


def test_override_four_digits():
    with dm.config.override(tick_years=4):
        ax = _line(np.arange(2016, 2025))
        assert _xticks(ax) == ["2016", "2018", "2020", "2022", "2024"]


@pytest.mark.parametrize("field", ["tick_years", "date_style"])
def test_invalid_config_value_raises_naming_field(field):
    fig, ax = plt.subplots()
    ax.plot([1, 2], [1, 2])
    with dm.config.override(**{field: "bogus"}):
        with pytest.raises(ValueError, match=field):
            dm.simple_layout(fig)


def test_helpers():
    assert is_year_axis([2016, 2018, 2020])
    assert not is_year_axis([2016])
    assert not is_year_axis([1890, 1900])
    assert not is_year_axis([2016.5, 2017.5])
    assert not is_year_axis([2000, 2001, 2003])
    assert two_digits_repeat([1900, 2000]) and not two_digits_repeat(
        [2016, 2017]
    )
    with pytest.raises(ValueError, match="digits"):
        YearTickFormatter(3)  # type: ignore[arg-type]
