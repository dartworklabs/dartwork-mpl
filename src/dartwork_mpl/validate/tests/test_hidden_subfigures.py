"""What a hidden SubFigure holds is not drawn, so the checks do not report it.

``SubFigure.set_visible(False)`` hides its legends, suptitle, texts and
Axes, but matplotlib leaves each child's own ``get_visible()`` True. Once
the checks read SubFigure legends and figure-level texts (#664) they took
hidden ones as drawn: an off-canvas legend was LEGEND_OVERFLOW, a legend on
data LEGEND_ON_DATA, an off-canvas text OVERFLOW and a hidden suptitle under
a legend LEGEND_OVERLAP. Each scene runs shown (the control: reported) and
hidden, in the SubFigure itself or in one above it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm

if TYPE_CHECKING:
    from collections.abc import Iterator

    from matplotlib.figure import Figure, SubFigure

STATES = ["shown", "holder_hidden", "ancestor_hidden"]


@pytest.fixture(autouse=True)
def _style() -> Iterator[None]:
    dm.style.use("report")
    yield
    plt.close("all")


def _two_columns() -> tuple[Figure, SubFigure]:
    """A visible left column and the right SubFigure."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    left, right = fig.subfigures(1, 2)
    left.subplots().plot([0, 1], [0, 1], label="Left series")
    return fig, right


def _holder(right: SubFigure, state: str) -> SubFigure:
    """Where the scene goes: the right SubFigure, or one nested in it when
    the SubFigure above it is the one hidden."""
    return right.subfigures(1, 1) if state == "ancestor_hidden" else right


def _hide(right: SubFigure, state: str) -> None:
    if state != "shown":
        right.set_visible(False)


def _ids(fig: Figure, *checks: str) -> list[str]:
    found = dm.validate_figure(fig, checks=checks, quiet=True)
    return [w.check_id for w in found]


@pytest.mark.parametrize("state", STATES)
def test_an_off_canvas_subfigure_legend(state: str) -> None:
    fig, right = _two_columns()
    holder = _holder(right, state)
    holder.subplots().plot([0, 1], [0, 1], label="Right series")
    holder.legend(loc="center", bbox_to_anchor=(4, 0.5))
    _hide(right, state)
    expected = ["LEGEND_OVERFLOW"] if state == "shown" else []
    assert _ids(fig, "LEGEND_OVERFLOW") == expected


@pytest.mark.parametrize("state", STATES)
def test_a_subfigure_legend_on_its_data(state: str) -> None:
    fig, right = _two_columns()
    holder = _holder(right, state)
    ax = holder.subplots()
    for k in range(3):
        ax.plot([0, 1], [0.2 * k, 1 - 0.2 * k], label=f"Series {k + 1}")
    holder.legend(loc="center")
    _hide(right, state)
    expected = ["LEGEND_ON_DATA"] if state == "shown" else []
    assert _ids(fig, "LEGEND_ON_DATA") == expected


@pytest.mark.parametrize("state", STATES)
def test_an_off_canvas_subfigure_text(state: str) -> None:
    fig, right = _two_columns()
    holder = _holder(right, state)
    holder.subplots()
    holder.text(0.9, 0.5, "A note that runs past the canvas edge")
    _hide(right, state)
    expected = ["OVERFLOW"] if state == "shown" else []
    assert _ids(fig, "OVERFLOW") == expected


@pytest.mark.parametrize("state", STATES)
def test_a_subfigure_suptitle_under_a_legend(state: str) -> None:
    fig, right = _two_columns()
    holder = _holder(right, state)
    holder.subplots()
    holder.suptitle("A group title under the legend", y=0.99)
    fig.legend(loc="upper center", bbox_to_anchor=(0.75, 1.0), ncols=1)
    _hide(right, state)
    found = dm.validate_figure(fig, checks=("LEGEND_OVERLAP",), quiet=True)
    roles = [w.detail["role"] for w in found if w.detail]
    assert ("suptitle" in roles) is (state == "shown")
