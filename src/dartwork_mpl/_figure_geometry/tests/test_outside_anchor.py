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

from dartwork_mpl._figure_geometry import (
    anchor_outside,
    outside_clearance_px,
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
