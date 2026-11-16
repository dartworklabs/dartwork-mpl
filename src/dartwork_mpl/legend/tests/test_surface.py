"""Real charts through ``dm.place_legend`` / ``dm.figure_legend`` and the layout."""

from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.transforms import ScaledTranslation

import dartwork_mpl as dm
from dartwork_mpl.geometry import get_renderer


@pytest.fixture(autouse=True)
def _close():
    dm.style.use("report")
    yield
    plt.close("all")


def _lines(n=2, width="12cm"):
    fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"))
    x = np.linspace(0, 10, 80)
    for i in range(n):
        ax.plot(x, np.sin(x + i), label=f"Series {i}")
    return fig, ax


def _box(fig, artist):
    return artist.get_window_extent(get_renderer(fig))


def test_a_legend_inside_keeps_clear_of_a_rising_line():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot([0, 10], [0, 10], label="Rising")
    ax.margins(0)  # the line runs into the upper right corner
    legend = dm.place_legend(ax)
    dm.simple_layout(fig)
    assert legend is ax.get_legend()
    assert "LEGEND_ON_DATA" not in dm.check(fig).rules
    plot = _box(fig, ax)
    assert _box(fig, legend).x0 < (plot.x0 + plot.x1) / 2  # upper left


@pytest.mark.parametrize("side", ["above", "below", "right", "left"])
def test_a_named_side_sits_past_that_sides_labels(side):
    fig, ax = _lines(3)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Signal")
    legend = dm.place_legend(ax, loc=side)
    dm.simple_layout(fig)
    own, plot = _box(fig, legend), _box(fig, ax)
    label = _box(fig, ax.xaxis.label if side == "below" else ax.yaxis.label)
    match side:
        case "above":
            assert own.y0 >= plot.y1
        case "below":
            assert own.y1 <= label.y0
        case "right":
            assert own.x0 >= plot.x1
        case "left":
            assert own.x1 <= label.x0
    assert fig.bbox.x0 <= own.x0 and own.x1 <= fig.bbox.x1


def test_a_twin_pair_gets_one_legend_on_the_top_twin():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.bar(np.arange(6), [5, 7, 6, 8, 7, 9], label="Rain")
    twin = ax.twinx()
    twin.plot(np.arange(6), [20, 22, 25, 24, 21, 19], label="Temp")
    ax.legend()
    legend = dm.place_legend(ax)
    assert ax.get_legend() is None and twin.get_legend() is legend
    assert [t.get_text() for t in legend.get_texts()] == ["Rain", "Temp"]


@pytest.mark.parametrize("loc", ["best", "above"])
def test_the_handles_and_labels_given_on_a_twin_pair_are_shown(loc):
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    (rain,) = ax.plot(np.arange(6), [5, 7, 6, 8, 7, 9], label="rain")
    twin = ax.twinx()
    (temp,) = twin.plot(np.arange(6), [20, 22, 25, 24, 21, 19], label="temp")
    dm.place_legend(ax, loc=loc, handles=[temp, rain], labels=["Temp", "Rain"])
    dm.simple_layout(fig)
    legend = twin.get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["Temp", "Rain"]


def test_a_rebuilt_legend_keeps_its_title_and_follows_the_artists():
    fig, ax = _lines()
    ax.legend(title="Runs", frameon=False)
    legend = dm.place_legend(ax)
    assert legend.get_title().get_text() == "Runs" and not legend.get_frame_on()
    for line in ax.get_lines():
        line.set_label("_hidden")
    assert dm.place_legend(ax) is None and ax.get_legend() is None


def test_repeated_layouts_keep_the_same_legends():
    fig, axes = plt.subplots(2, 2, figsize=dm.figsize("17cm", "12cm"))
    for ax in axes.flat:
        for i in range(4):
            ax.fill_between(np.arange(10), 0, 10, alpha=0.2, label=f"Band {i}")
        dm.place_legend(ax)
    legends = []
    for _ in range(3):
        dm.simple_layout(fig)
        legends.append([ax.get_legend() for ax in fig.axes])
    assert legends[0] == legends[2]


def test_a_caller_anchor_with_a_side_raises():
    fig, ax = _lines()
    with pytest.raises(ValueError, match="anchors itself"):
        dm.place_legend(ax, loc="right", bbox_to_anchor=(1, 0.5))


def test_one_figure_legend_replaces_the_panel_legends():
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
    for ax in axes:
        ax.plot([0, 1], [0, 1], label="A")
        ax.plot([0, 1], [1, 0], label="B")
        ax.legend()
    legend = dm.figure_legend(fig)
    dm.simple_layout(fig)
    assert all(ax.get_legend() is None for ax in axes)
    assert [t.get_text() for t in legend.get_texts()] == ["A", "B"]
    own = _box(fig, legend)
    assert own.y1 <= fig.bbox.height + 0.5
    assert own.y0 >= max(_box(fig, ax).y1 for ax in axes)


def test_a_polar_legend_below_stays_off_the_circle():
    fig = plt.figure(figsize=dm.figsize("10cm", "square"))
    ax = fig.add_subplot(projection="polar")
    theta = np.linspace(0, 2 * np.pi, 60)
    ax.plot(theta, 1 + 0.3 * np.sin(3 * theta), label="Pattern")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        legend = dm.place_legend(ax, loc="below")
        dm.simple_layout(fig)
    assert _box(fig, legend).y1 <= _box(fig, ax).y0


def test_a_legend_the_caller_moved_stays_where_they_put_it() -> None:
    fig, ax = plt.subplots()
    x = np.linspace(0, 1, 20)
    ax.plot(x, x, label="up")
    ax.plot(x, 1 - x, label="down")
    legend = dm.place_legend(ax)
    assert legend is not None
    legend.set_loc("lower left")
    dm.simple_layout(fig)
    fig.canvas.draw()
    box, frame = legend.get_window_extent(), ax.get_window_extent()
    assert box.x0 - frame.x0 < frame.width / 4
    assert box.y0 - frame.y0 < frame.height / 4


def test_an_outside_legend_the_caller_moved_stays_where_they_put_it() -> None:
    # #749: a legend above moved with set_loc was rebuilt at the centre by
    # the next layout at another size.
    fig, ax = _lines(3)
    dm.place_legend(ax, loc="above")
    dm.simple_layout(fig)
    legend = ax.get_legend()
    assert legend is not None
    legend.set_loc("lower left")
    fig.set_size_inches(4.0, 3.0)
    dm.simple_layout(fig)
    middle = (_box(fig, ax).x0 + _box(fig, ax).x1) / 2
    assert ax.get_legend() is legend
    assert _box(fig, legend).x0 > middle  # centred, it would straddle it


def test_a_title_the_caller_moved_stays_where_they_put_it() -> None:
    # #749: a title raised over a legend above and given another transform
    # by the caller was raised again by the next layout.
    fig, ax = _lines(3)
    ax.set_title("Three series")
    dm.place_legend(ax, loc="above")
    dm.simple_layout(fig)
    mine = ax.transAxes + ScaledTranslation(0.0, 4 / 72, fig.dpi_scale_trans)
    ax.title.set_transform(mine)
    dm.simple_layout(fig)
    assert ax.title.get_transform() is mine


def test_a_figure_title_a_legend_above_and_panel_titles_stack():
    # #785: the legend was drawn on the suptitle, and below it the suptitle
    # sat flush on the panel titles.
    fig, axes = plt.subplots(2, 3, figsize=dm.figsize("17cm", "8.5cm"))
    for ax, name in zip(axes.flat, "ABCDEF", strict=True):
        ax.plot([1, 2, 3], [1, 3, 2], label="Actual")
        ax.plot([1, 2, 3], [2, 2, 2], label="Plan")
        ax.set_title(name)
    title = fig.suptitle("Every region beat plan from July on")
    legend = dm.figure_legend(fig)
    dm.simple_layout(fig)
    panels = max(_box(fig, ax.title).y1 for ax in axes[0])
    assert _box(fig, title).y0 >= _box(fig, legend).y1
    assert _box(fig, legend).y0 >= panels

    below = dm.figure_legend(fig, loc="below")
    dm.simple_layout(fig)
    pad = plt.rcParams["axes.titlepad"] * fig.dpi / 72
    assert below is not None
    gap = _box(fig, title).y0 - max(_box(fig, ax.title).y1 for ax in axes[0])
    assert gap >= pad  # the title pad, past the layout's margin
