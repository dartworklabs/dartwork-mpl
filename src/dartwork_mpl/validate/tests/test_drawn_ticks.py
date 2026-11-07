"""The layout checks judge only the tick labels matplotlib draws.

Matplotlib keeps every major tick label on the artist tree, positioned and
``get_visible()``, but draws one only when the axes' axis is on and the tick
lies in the view interval. OVERFLOW, CLIPPED_TEXT and CROSS_AXES_OVERLAP
used a pixel anchor with 0.5 px slack and ignored ``ax.axis("off")``, so the
docs' colour-space figures were flagged for labels nobody sees: the hidden
ticks of a title-only panel, and a colorbar's ``1.00`` a hair past its
limit (review of PR #595, item 6).
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import drawn_tick_labels


@pytest.fixture(autouse=True)
def _scientific():
    with matplotlib.rc_context():
        dm.style.use("scientific")
        yield
    plt.close("all")


def _ids(fig, *checks):
    return [
        w.check_id for w in dm.validate_figure(fig, checks=checks, quiet=True)
    ]


def _overlaid_panels(second_axis_on: bool):
    """Two Axes in one box: the second's tick labels sit on the first's."""
    fig = plt.figure(figsize=dm.figsize("12cm", "8cm"))
    first = fig.add_axes((0.15, 0.15, 0.8, 0.8))
    first.plot([0, 1], [0, 1])
    second = fig.add_axes((0.15, 0.15, 0.8, 0.8))
    second.patch.set_alpha(0)
    second.plot([0, 1], [0, 1])
    if not second_axis_on:
        second.axis("off")  # draws neither axis: nothing to overlap
    return fig


def test_an_axes_with_its_axis_off_overlaps_nothing():
    assert "CROSS_AXES_OVERLAP" in _ids(
        _overlaid_panels(second_axis_on=True), "CROSS_AXES_OVERLAP"
    )
    assert (
        _ids(_overlaid_panels(second_axis_on=False), "CROSS_AXES_OVERLAP") == []
    )


def _colorbar_at_the_top(scale: float):
    """A colorbar reaching the canvas top, data in +/- ``scale``."""
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    yy, xx = np.mgrid[-1:1:60j, -1:1:60j]
    data = xx * yy * scale
    image = ax.imshow(data, vmin=data.min(), vmax=data.max())
    bar = fig.colorbar(image, ax=ax)
    fig.subplots_adjust(top=1.0, bottom=0.0)
    fig.canvas.draw()
    return fig, bar


def test_a_colorbar_tick_past_its_limit_is_not_drawn_or_flagged():
    """The ``1.00`` tick of a bar ending at 0.9997 is not drawn."""
    fig, bar = _colorbar_at_the_top(0.9997)
    drawn = [t.get_text() for t in drawn_tick_labels(bar.ax, "y")]
    assert "1.00" not in drawn and "0.75" in drawn, drawn
    assert _ids(fig, "OVERFLOW", "CLIPPED_TEXT") == []


def test_a_drawn_tick_label_past_the_canvas_is_still_flagged():
    fig, bar = _colorbar_at_the_top(1.0)
    assert "1.00" in [t.get_text() for t in drawn_tick_labels(bar.ax, "y")]
    assert set(_ids(fig, "OVERFLOW", "CLIPPED_TEXT")) == {
        "OVERFLOW",
        "CLIPPED_TEXT",
    }


# Re-review of PR #595, item 6: drawn_tick_labels paired N tick locations
# with matplotlib's label list (visible left/bottom labels, then right/top
# ones), so labels on the second side were never checked and one hidden
# label shifted every pairing after it.


def test_labels_on_the_right_and_top_are_drawn_and_checked():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 1], [0, 1_000_000])
    ax.tick_params(axis="y", labelright=True)
    ax.tick_params(axis="x", labeltop=True)
    fig.subplots_adjust(left=0.3, right=0.995, top=0.995, bottom=0.2)
    fig.canvas.draw()
    for which in ("x", "y"):
        axis = ax.xaxis if which == "x" else ax.yaxis
        drawn = drawn_tick_labels(ax, which)
        seconds = [t.label2 for t in axis.get_major_ticks()]
        assert any(label in drawn for label in seconds), which
    found = dm.validate_figure(
        fig, checks=("OVERFLOW", "CLIPPED_TEXT"), quiet=True
    )
    seconds_text = {
        t.label2.get_text()
        for axis in (ax.xaxis, ax.yaxis)
        for t in axis.get_major_ticks()
    }
    over = {w.detail["text"] for w in found if w.check_id == "OVERFLOW"}
    assert over and over <= seconds_text, found  # the right / top labels


def test_a_hidden_label_shifts_nothing():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 1], [0, 1])
    ax.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0, 1.25])
    ax.set_ylim(0, 1.1)  # 1.25 is out of view: not drawn
    fig.canvas.draw()
    ticks = ax.yaxis.get_major_ticks()
    ticks[0].label1.set_visible(False)  # the shared-panel idiom
    drawn = drawn_tick_labels(ax, "y")
    assert drawn == [t.label1 for t in ticks[1:5]], [
        t.get_text() for t in drawn
    ]


def test_a_left_panels_right_labels_running_into_the_next_panel():
    fig, (left, right) = plt.subplots(1, 2, figsize=dm.figsize("12cm", "6cm"))
    left.plot([0, 1], [0, 123456.789])
    right.plot([0, 1], [0, 1])
    left.ticklabel_format(useOffset=False, style="plain")
    left.tick_params(axis="y", labelright=True)
    fig.subplots_adjust(wspace=0.05, left=0.2, right=0.95)
    assert "CROSS_AXES_OVERLAP" in _ids(fig, "CROSS_AXES_OVERLAP")
