"""TICK_CROWD measures a turned tick label by the room it needs along the axis.

A label turned by an angle fills a slanted rectangle; its neighbour clears
it once the tick spacing reaches the rectangle's height over the sine of
the angle (or its width over the cosine, whichever is shorter), not once it
passes the label's whole axis-aligned window extent. TICK_CROWD used to sum
those window extents, so turned labels that stood apart (the waterfall and
boxplot templates under ``dm.simple_layout``'s 30 degrees) read as filling
over 100 % of the axis. Upright labels are measured as before.
"""

from __future__ import annotations

from collections.abc import Iterator

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

from dartwork_mpl._figure_geometry import tick_label_overlaps
from dartwork_mpl.validate import validate_figure


@pytest.fixture(autouse=True)
def _close() -> Iterator[None]:
    yield
    plt.close("all")


def _turned(n: int, angle: float) -> Figure:
    fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
    ax.bar(range(n), range(1, n + 1))
    ax.set_xticks(range(n))
    ax.set_xticklabels(
        [f"Category name {i}" for i in range(n)],
        rotation=angle,
        ha="right",
        rotation_mode="anchor",
        fontsize=8,
    )
    fig.subplots_adjust(bottom=0.4)
    fig.canvas.draw()
    return fig


def test_turned_labels_that_stand_apart_are_not_crowded() -> None:
    fig = _turned(8, 45)
    ax = fig.axes[0]
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    assert tick_label_overlaps(ax, "x", renderer).pairs == 0
    # Their window extents alone fill more than the axis: the old measure.
    widths = sum(
        t.get_window_extent(renderer).width for t in ax.get_xticklabels()
    )
    assert widths * 1.15 > ax.get_window_extent(renderer).width
    found = validate_figure(fig, checks=("TICK_CROWD",), quiet=True)
    assert found == [], [w.message for w in found]


def test_turned_labels_that_crowd_are_reported() -> None:
    fig = _turned(30, 45)
    ax = fig.axes[0]
    assert tick_label_overlaps(ax, "x", fig.canvas.get_renderer()).pairs > 0  # type: ignore[attr-defined]
    found = validate_figure(fig, checks=("TICK_CROWD",), quiet=True)
    assert [(w.detail["axis"], w.detail["count"]) for w in found] == [("x", 30)]


def test_upright_labels_keep_their_width() -> None:
    fig = _turned(8, 0)
    ax = fig.axes[0]
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    widths = sum(
        t.get_window_extent(renderer).width for t in ax.get_xticklabels()
    )
    span = ax.get_window_extent(renderer).width
    found = validate_figure(fig, checks=("TICK_CROWD",), quiet=True)
    assert [w.detail["occupancy"] for w in found] == [
        pytest.approx(round(widths * 1.15 / span, 2), abs=0.01)
    ]
