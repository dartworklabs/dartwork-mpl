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

import functools
import warnings
from collections import Counter
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import drawn_axes

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


# --------------------------------- every check that walks the figure's Axes
#: The checks that counted the Axes of a hidden SubFigure (diagnosis in the
#: follow-up after #664): each fires on the trouble panels when they show.
WALKING = [
    "OVERLAP",
    "CROSS_AXES_OVERLAP",
    "TICK_CROWD",
    "TICK_OVERLAP",
    "TICK_ROTATION",
    "TICK_DECIMAL",
    "EMPTY_AXES",
    "TEXT_CONTRAST",
    "MIN_FONT_SIZE",
    "GRAYSCALE_SAFETY",
    "CLIPPED_TEXT",
]


def _trouble(holder: SubFigure) -> None:
    """Nine panels, each with something a check reports."""
    axs = iter(holder.subplots(3, 3).flat)
    a = next(axs)  # crowded long tick labels
    a.bar(range(24), np.arange(24))
    a.set_xticks(range(24), [f"Category number {i}" for i in range(24)])
    a = next(axs)  # uneven tick decimals
    a.plot([0, 1], [0, 1])
    a.set_xticks([0, 0.5, 1], ["0", "0.5", "1.00"])
    a = next(axs)  # overlapping, tiny, faint and clipped texts
    a.plot([0, 1], [0, 1])
    a.text(0.5, 0.5, "Overlap one", transform=a.transAxes)
    a.text(0.52, 0.5, "Overlap two", transform=a.transAxes)
    a.text(0.1, 0.9, "tiny", fontsize=3, transform=a.transAxes)
    a.text(0.1, 0.2, "faint", color="#fdfdfd", transform=a.transAxes)
    a.text(1.3, 0.5, "clipped away", transform=a.transAxes, clip_on=True)
    next(axs)  # an empty panel
    a = next(axs)  # lines a grayscale print cannot tell apart
    for color in ("#d62728", "#2ca02c", "#1f77b4"):
        a.plot([0, 1], [0.2, 0.8], color=color)
    for a in axs:
        a.plot([0, 1e6], [0, 1e6])


@functools.cache
def _found(state: str, where: str) -> Counter[str]:
    """Findings by check: the trouble panels shown, hidden, or never drawn
    (``empty``: the same pixels as ``hidden``)."""
    dm.style.use("report")
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    left, right = fig.subfigures(1, 2)
    left.subplots().plot([0, 1, 2], [3, 1, 2])
    holder = right.subfigures(1, 1) if where == "ancestor" else right
    if state != "empty":
        _trouble(holder)
    if state == "hidden":
        right.set_visible(False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        found = dm.validate_figure(fig, quiet=True)
    plt.close(fig)
    return Counter(w.check_id for w in found)


@pytest.mark.parametrize("where", ["holder", "ancestor"])
@pytest.mark.parametrize("check", WALKING)
def test_a_check_counts_nothing_a_hidden_subfigure_holds(
    check: str, where: str
) -> None:
    """Hidden, the panels draw what an empty SubFigure draws, and the check
    finds what it finds there; shown (the control), it reports them."""
    assert _found("shown", where)[check] > 0
    assert _found("hidden", where)[check] == _found("empty", where)[check]


def test_drawn_axes_keeps_the_figure_axes_index() -> None:
    """The index is into ``fig.axes``, not into the drawn list, and an Axes'
    own flag is the check's to read, as before."""
    fig = plt.figure()
    left, right = fig.subfigures(1, 2)
    a = left.add_subplot()
    b = right.add_subplot()
    c = left.add_subplot(2, 1, 2)
    c.set_visible(False)
    right.set_visible(False)
    assert drawn_axes(fig) == [(0, a), (2, c)]
    assert b in fig.axes
