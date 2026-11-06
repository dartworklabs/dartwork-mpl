"""Anchoring an artist outside one side of an Axes, past its labels (#523).

``anchor_outside`` is the mechanism behind ``place_legend(loc="above")``
and the layout's re-anchoring; ``outside_clearance_px`` measures how far a
side's tick labels and axis label reach past the spine.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.transforms import Bbox

from dartwork_mpl._figure_geometry import (
    anchor_outside,
    outside_clearance_px,
    outside_side,
    reanchor_outside,
    same_position_axes,
)
from tests.support.mpl_observe import drawn_renderer


def test_twins_share_a_position_and_other_panels_do_not() -> None:
    fig, (left, right) = plt.subplots(1, 2)
    twin = left.twinx()
    assert same_position_axes(left) == [left, twin]
    assert same_position_axes(right) == [right]
    plt.close(fig)


def test_clearance_reaches_the_outermost_label_of_each_side() -> None:
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    ax.set(xlabel="x label", ylabel="y label")
    renderer = drawn_renderer(fig)
    box = ax.get_window_extent(renderer)
    below = box.y0 - ax.xaxis.label.get_window_extent(renderer).y0
    left = box.x0 - ax.yaxis.label.get_window_extent(renderer).x0
    assert outside_clearance_px(ax, "below", renderer) == pytest.approx(below)
    assert outside_clearance_px(ax, "left", renderer) == pytest.approx(left)
    assert outside_clearance_px(ax, "above", renderer) == 0.0
    assert outside_clearance_px(ax, "right", renderer) == 0.0
    plt.close(fig)


def test_reanchor_follows_a_label_added_later() -> None:
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], label="line")
    legend = ax.legend(loc="upper center")
    renderer = drawn_renderer(fig)
    assert anchor_outside(legend, ax, "below", renderer) is True
    assert reanchor_outside(legend, ax, renderer) is False  # nothing changed
    ax.set_xlabel("added later")
    renderer = drawn_renderer(fig)
    assert reanchor_outside(legend, ax, renderer) is True
    legend_top = legend.get_window_extent(renderer).y1
    assert legend_top <= ax.xaxis.label.get_window_extent(renderer).y0
    plt.close(fig)


def test_reanchor_ignores_artists_it_did_not_anchor() -> None:
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], label="line")
    legend = ax.legend()
    assert reanchor_outside(legend, ax, drawn_renderer(fig)) is False
    plt.close(fig)


def test_anchor_clears_the_obstacles_in_its_way_and_not_the_others() -> None:
    # Re-review N-I2: bar values past the top limit sit above the axes; a
    # legend anchored above moves past the ones it overlaps along the top
    # (in x), not past one beside it.
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], label="line")
    legend = ax.legend(loc="lower center")
    renderer = drawn_renderer(fig)
    assert anchor_outside(legend, ax, "above", renderer) is True
    renderer = drawn_renderer(fig)
    box = ax.get_window_extent(renderer)
    own = legend.get_window_extent(renderer)
    in_way = Bbox.from_extents(own.x0, box.y1 + 2, own.x1, box.y1 + 30)
    beside = Bbox.from_extents(box.x0, box.y1 + 2, own.x0 - 5, box.y1 + 60)
    assert outside_side(legend) == "above"
    assert reanchor_outside(legend, ax, renderer, [beside]) is False
    assert reanchor_outside(legend, ax, renderer, [in_way, beside]) is True
    renderer = drawn_renderer(fig)
    assert legend.get_window_extent(renderer).y0 >= in_way.y1 - 0.5
    assert outside_side(ax.legend()) is None  # a legend it did not anchor
    plt.close(fig)
