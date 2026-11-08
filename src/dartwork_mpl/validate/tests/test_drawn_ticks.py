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


def test_a_hidden_axes_draws_no_tick_labels():
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 1], [0, 1])
    ax.minorticks_on()
    ax.tick_params(which="minor", labelbottom=True)
    fig.canvas.draw()
    assert drawn_tick_labels(ax, "x"), "precondition: shown, labels drawn"
    ax.set_visible(False)  # the idiom for an empty grid slot
    assert [
        drawn_tick_labels(ax, which, minor=minor)
        for which in ("x", "y")
        for minor in (False, True)
    ] == [[], [], [], []]


def test_a_left_panels_right_labels_running_into_the_next_panel():
    fig, (left, right) = plt.subplots(1, 2, figsize=dm.figsize("12cm", "6cm"))
    left.plot([0, 1], [0, 123456.789])
    right.plot([0, 1], [0, 1])
    left.ticklabel_format(useOffset=False, style="plain")
    left.tick_params(axis="y", labelright=True)
    fig.subplots_adjust(wspace=0.05, left=0.2, right=0.95)
    assert "CROSS_AXES_OVERLAP" in _ids(fig, "CROSS_AXES_OVERLAP")


# ── the tick labels of UNIT_DUP, TICK_DECIMAL, TICK_CROWD, LEGEND_OVERLAP
# and TICK_ROTATION (``iter_view_ticks``) are the drawn ones too ─────────


def _texts(labels) -> list[str]:
    return [label.get_text() for label in labels]


def _a_tick_just_above_the_limit():
    """y ticks 0 ... 1.0 with the limit 0.001 below 1.0: about a third of a
    pixel, so the label's centre-baseline box still reaches into the view,
    but matplotlib does not draw it."""
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 1], [0, 0.99])
    ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylim(0, 0.999)
    fig.canvas.draw()
    return fig, ax


def test_a_tick_label_just_past_the_limit_is_not_counted():
    from dartwork_mpl._figure_geometry import get_renderer
    from dartwork_mpl.validate._checks._tick_utils import iter_view_ticks

    fig, ax = _a_tick_just_above_the_limit()
    counted = _texts(iter_view_ticks(ax, "y", get_renderer(fig)))
    assert "1.0" not in counted
    assert counted == _texts(drawn_tick_labels(ax, "y"))


def test_a_legend_over_a_tick_label_nobody_sees_is_not_reported():
    """A figure legend sitting on the undrawn 1.0 above the y labels (the
    pixels there are blank) covers nothing (I-O2: two such reports)."""
    fig, ax = _a_tick_just_above_the_limit()
    # right edge on the plot's left edge, bottom on its top: over the y
    # label column, just above the plot
    fig.legend(
        ["Signal"],
        loc="lower right",
        bbox_to_anchor=(0.0, 1.0),
        bbox_transform=ax.transAxes,
        borderaxespad=0,
    )
    assert _ids(fig, "LEGEND_OVERLAP") == []
    # the same legend over a label that is drawn is reported
    ax.set_ylim(0, 1.0)
    assert _ids(fig, "LEGEND_OVERLAP") == ["LEGEND_OVERLAP"]


def test_a_turned_label_at_the_view_edge_is_counted():
    """The first label sits at the left limit, turned 45 degrees with its
    end at the tick: its box lies left of the plot, yet matplotlib draws
    it, so it counts."""
    from dartwork_mpl._figure_geometry import get_renderer
    from dartwork_mpl.validate._checks._tick_utils import iter_view_ticks

    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    names = ["Thermoregulation", "Electrification", "Decarbonisation"]
    ax.bar(range(3), [1, 2, 3])
    ax.set_xticks(range(3), names, rotation=45, ha="right")
    ax.set_xlim(0, 2)
    fig.canvas.draw()
    counted = _texts(iter_view_ticks(ax, "x", get_renderer(fig)))
    assert counted == names
    assert counted == _texts(drawn_tick_labels(ax, "x"))


def test_a_twins_hidden_x_axis_has_no_tick_labels():
    """``twinx`` hides the second Axes' x axis: its labels sit on the
    first's, never drawn, and were counted twice (UNIT_DUP, TICK_CROWD and
    TICK_ROTATION on every twin of the stress set)."""
    from dartwork_mpl._figure_geometry import get_renderer
    from dartwork_mpl.validate._checks._tick_utils import iter_view_ticks

    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.bar(range(4), [1, 2, 3, 4])
    ax.set_xticks(range(4), ["A", "B", "C", "D"])
    twin = ax.twinx()
    twin.plot(range(4), [4, 3, 2, 1])
    fig.canvas.draw()
    renderer = get_renderer(fig)
    assert _texts(iter_view_ticks(ax, "x", renderer)) == ["A", "B", "C", "D"]
    assert list(iter_view_ticks(twin, "x", renderer)) == []


@pytest.mark.parametrize("name", ["polar.py", "advanced/polar.py"])
def test_a_polar_theta_ring_is_not_a_row_of_labels(name: str) -> None:
    """TICK_CROWD and TICK_ROTATION share out a straight axis' width; the
    theta labels around a polar plot have none. On the shipped polar
    templates in presentation TICK_CROWD measured "8 ticks in 0.00in", and
    counting every drawn theta label added TICK_ROTATION."""
    from pathlib import Path

    source = (
        Path(dm.__file__).parent / "asset/prompt/05-templates" / name
    ).read_text(encoding="utf-8")
    ends = ("dm.validate_with_fixes(fig)", "dm.save_formats(")
    source = source[: min(i for e in ends if (i := source.find(e)) >= 0)]
    source = source.replace(
        'dm.style.use("scientific")', 'dm.style.use("presentation")'
    )
    namespace: dict = {}
    exec(compile(source, name, "exec"), namespace)
    fig = namespace["fig"]
    assert fig.axes[0].name == "polar"  # precondition
    assert _ids(fig, "TICK_CROWD", "TICK_ROTATION") == []
