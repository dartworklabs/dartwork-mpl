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
from dartwork_mpl.validate._checks._tick_utils import drawn_tick_labels


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
