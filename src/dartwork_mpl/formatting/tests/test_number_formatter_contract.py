"""What the numeric-unit helpers do besides their tick text.

The non-text columns of ``docs/development/numeric-unit-formatters.md``:
return value, the axis label, a locator and limits someone set, which axis
choices are taken, and when a negative ``decimals`` fails. The tick text
itself is pinned in ``test_number_formatters_grid.py``. A failure here is a
change of the public contract, decided by a person, not a test fix.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pytest

import dartwork_mpl as dm
from dartwork_mpl.formatting._label_unit import LabelUnitFormatter

_CALLS: dict[str, Callable[..., Any]] = {
    "millions": dm.format_axis_millions,
    "billions": dm.format_axis_billions,
    "currency": dm.format_axis_currency,
    "si": dm.format_axis_si,
    "myriad": dm.format_axis_myriad,
    "axis_unit": dm.axis_unit,
}
_HELPERS = ("millions", "billions", "currency", "si", "myriad")


def _axes() -> tuple[Any, Any]:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([-2.5e6, 4e6], [0, 3e6])
    ax.set_xlabel("X")
    ax.set_ylabel("Value")
    return fig, ax


def _texts(ax: Any, which: str) -> list[str]:
    ax.figure.canvas.draw()
    labels = ax.get_xticklabels() if which == "x" else ax.get_yticklabels()
    return [t.get_text() for t in labels]


@pytest.mark.parametrize("name", list(_CALLS))
def test_return_label_locator_and_limits(name: str) -> None:
    """None and the label untouched (``axis_unit``: its formatter, and the
    unit in the label); a locator and limits set before stay."""
    fig, ax = _axes()
    locator = mticker.MultipleLocator(7.5e5)
    ax.yaxis.set_major_locator(locator)
    ax.set_ylim(-2.5e5, 3.1e6)
    result = _CALLS[name](ax, "y")
    dm.simple_layout(fig)
    assert ax.yaxis.get_major_locator() is locator
    assert ax.get_ylim() == (-2.5e5, 3.1e6)
    if name == "axis_unit":
        assert isinstance(result, LabelUnitFormatter)
        assert ax.get_ylabel() == "Value (M)"
    else:
        assert result is None
        assert ax.get_ylabel() == "Value"
    plt.close(fig)


@pytest.mark.parametrize("name", _HELPERS)
def test_helpers_take_both_and_ignore_another_axis_name(name: str) -> None:
    """``"both"`` formats x and y. Another name: myriad raises, the other
    four leave the axes as they were."""
    fig, ax = _axes()
    plain = _texts(ax, "y")
    _CALLS[name](ax, "both")
    assert _texts(ax, "x") != plain and _texts(ax, "y") != plain
    plt.close(fig)
    fig, ax = _axes()
    if name == "myriad":
        with pytest.raises(ValueError, match="axis must be one of"):
            _CALLS[name](ax, "z")
    else:
        _CALLS[name](ax, "z")
    assert _texts(ax, "y") == plain
    plt.close(fig)


def test_axis_unit_takes_x_or_y_only() -> None:
    fig, ax = _axes()
    with pytest.raises(ValueError, match="axis must be 'x' or 'y'"):
        dm.axis_unit(ax, "both")  # type: ignore[arg-type]
    plt.close(fig)


@pytest.mark.parametrize("name", list(_CALLS))
def test_negative_decimals_fail_at_the_call_or_the_draw(name: str) -> None:
    """myriad and axis_unit refuse at the call; the other four install the
    formatter and fail when it formats."""
    fig, ax = _axes()
    if name in ("myriad", "axis_unit"):
        with pytest.raises(ValueError, match="non-negative"):
            _CALLS[name](ax, "y", decimals=-1)
    else:
        _CALLS[name](ax, "y", decimals=-1)
        with pytest.raises(ValueError, match="precision"):
            fig.canvas.draw()
    plt.close(fig)
