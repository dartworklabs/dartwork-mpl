"""LEGEND_ON_DATA and the outside-size rule of LEGEND_OVERFLOW.

The oracle is what a reader sees once the figure is drawn: a legend box
lying on a line, a bar, a marker, a text, another legend or another
panel, by more than half a point. The negatives are legends in a free
corner, beside the data by a touch, outside the Axes, on top of their own
overlay Axes, and artists the reader cannot see.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity
from tests.support.mpl_observe import drawn_renderer

ID = "LEGEND_ON_DATA"


@pytest.fixture(autouse=True)
def _style():
    dm.style.use("report")
    yield
    plt.close("all")


def _found(fig, *checks: str):
    return list(dm.validate_figure(fig, checks=checks or (ID,), quiet=True))


def _fig(width: str = "12cm"):
    return plt.subplots(figsize=dm.figsize(width, "standard"))


def _dense(ax, n: int = 5) -> None:
    """``n`` sine lines through the whole plot: every corner holds data."""
    x = np.linspace(0, 11, 60)
    for i in range(n):
        ax.plot(
            x,
            50 + 42 * np.sin(2 * np.pi * x / 6 + 2 * np.pi * i / n),
            label=f"Region {i + 1}",
        )


# ----------------------------------------------------------- must report
def test_a_legend_on_lines_is_reported() -> None:
    fig, ax = _fig()
    _dense(ax)
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.severity == Severity.WARNING
    assert w.detail["legend_axes"] == 0
    assert w.detail["covered"] == ["line"]
    assert w.detail["panels"] == [0]
    assert w.detail["legend_labels"][0] == "Region 1"
    assert w.message.startswith("Legend of axes[0] covers lines")


def test_a_legend_on_bars_is_reported() -> None:
    fig, ax = _fig()
    ax.bar(np.arange(6), [9, 9.5, 9.8, 9.6, 9.9, 9.7], label="Sales")
    ax.set_ylim(0, 10)
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.detail["covered"] == ["bar"]
    assert w.detail["artists"] == ["Sales"]


def test_a_legend_on_scatter_points_is_reported() -> None:
    fig, ax = _fig()
    grid = np.linspace(0, 10, 25)
    xs, ys = np.meshgrid(grid, grid)
    ax.scatter(xs.ravel(), ys.ravel(), s=12, label="Sites")
    ax.legend(loc="center")
    (w,) = _found(fig)
    assert w.detail["covered"] == ["marker"]


def test_a_legend_on_a_value_label_is_reported() -> None:
    fig, ax = _fig()
    ax.plot([0, 10], [0, 1], label="Trend")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.text(9.6, 9.6, "Peak 9.6", ha="right", va="top")
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.detail["covered"] == ["text"]
    assert w.detail["artists"] == ["Peak 9.6"]


def test_twin_legends_on_each_other_are_both_reported() -> None:
    fig, ax = _fig()
    ax.plot([0, 1], [0, 0.1], label="Left series")
    twin = ax.twinx()
    twin.plot([0, 1], [0, 0.1], color="oc.red5", label="Right series")
    ax.legend(loc="upper right")
    twin.legend(loc="upper right")
    found = _found(fig)
    assert [w.detail["covered"] for w in found] == [["legend"], ["legend"]]
    assert [w.detail["artists"] for w in found] == [
        ["legend of axes[1]"],
        ["legend of axes[0]"],
    ]


def test_a_legend_on_the_twins_data_is_reported() -> None:
    fig, ax = _fig()
    ax.plot([0, 1], [0, 0.1], label="Low")
    twin = ax.twinx()
    _dense(twin, 3)
    twin.set_ylim(20, 80)  # the twin's lines run through every corner
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.detail["legend_axes"] == 0
    assert w.detail["covered"] == ["line"]


def test_a_legend_reaching_into_the_next_panel_is_reported() -> None:
    fig, (left, right) = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
    left.plot([0, 1], [0, 0.1], label="A series with a long name")
    right.plot([0, 1], [0, 0.1])
    left.legend(loc="center left", bbox_to_anchor=(0.9, 0.5))
    (w,) = _found(fig)
    assert w.detail["legend_axes"] == 0
    assert "panel" in w.detail["covered"]
    assert "axes[1]" in w.detail["artists"]


def test_a_figure_legend_over_the_panels_is_reported() -> None:
    fig, axs = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
    for ax in axs:
        _dense(ax, 3)
    fig.legend(*axs[0].get_legend_handles_labels(), loc="center")
    found = _found(fig)
    assert len(found) == 1
    (w,) = found
    assert w.detail["legend_axes"] is None
    assert w.message.startswith("Figure legend covers")
    assert w.detail["panels"]  # the panel(s) whose lines it covers


# ----------------------------------------------------------- must not report
def test_a_legend_in_a_free_corner_is_clean() -> None:
    fig, ax = _fig()
    ax.plot([0, 10], [0, 2], label="Low")
    ax.plot([0, 10], [1, 3], label="Lower")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.legend(loc="upper left")
    assert _found(fig) == []


def _line_near_the_legend_bottom(overlap_pt: float):
    """A horizontal data line whose stroke overlaps the legend by ``overlap_pt``."""
    fig, ax = _fig()
    ax.plot([0, 10], [9, 9.5], label="Top")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    legend = ax.legend(loc="upper left")
    renderer = drawn_renderer(fig)
    box = legend.get_window_extent(renderer)
    width_pt = 1.0
    half = width_pt / 2 * fig.dpi / 72.0
    y_px = box.y0 - half + overlap_pt * fig.dpi / 72.0
    to_data = ax.transData.inverted()
    ((_x, y),) = to_data.transform([(box.x0, y_px)])
    ax.plot([0, 10], [y, y], lw=width_pt, color="oc.gray5", label="_ref")
    return fig


def test_a_touch_of_half_a_point_is_not_a_cover() -> None:
    assert _found(_line_near_the_legend_bottom(0.25)) == []


def test_more_than_half_a_point_is_a_cover() -> None:
    (w,) = _found(_line_near_the_legend_bottom(1.0))
    assert w.detail["covered"] == ["line"]
    assert w.detail["artists"] == [""]  # the line has no legend label


def test_a_legend_above_the_axes_is_clean() -> None:
    fig, ax = _fig()
    _dense(ax)
    dm.place_legend(ax, loc="above")
    dm.simple_layout(fig)
    assert _found(fig) == []


def test_hidden_data_and_hidden_legends_do_not_count() -> None:
    fig, ax = _fig()
    ax.plot([0, 1], [0, 0.1], label="Shown")
    hidden = ax.plot([0, 1], [1, 1], label="Hidden")[0]
    hidden.set_visible(False)
    ax.set(xlim=(0, 1), ylim=(0, 1.05))
    ax.legend(loc="upper right")
    assert _found(fig) == []
    _dense(ax)
    ax.legend(loc="upper right").set_visible(False)
    assert _found(fig) == []


def test_a_legend_inside_an_overlay_axes_is_drawn_over_the_panel_below() -> (
    None
):
    """An Axes added on top of a panel: its own legend is not on that panel."""
    fig, ax = _fig()
    _dense(ax)
    overlay = fig.add_axes((0.55, 0.55, 0.3, 0.3))
    overlay.plot([0, 1], [0, 0.1], label="Detail")
    overlay.set(xlim=(0, 1), ylim=(0, 1))
    overlay.legend(loc="upper left")
    assert _found(fig) == []


def _flat_line_under_centre(ax) -> None:
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.plot([0, 1], [0.5, 0.5], label="Series")


def test_a_legend_that_draws_nothing_is_not_reported() -> None:
    """No frame and no entry, or every part at alpha 0: nothing covers the line."""
    fig, ax = _fig()
    _flat_line_under_centre(ax)
    ax.legend([], [], loc="center", frameon=False)
    assert _found(fig) == []

    fig, ax = _fig()
    _flat_line_under_centre(ax)
    legend = ax.legend(loc="center")
    legend.get_frame().set_alpha(0)
    for text in legend.get_texts():
        text.set_alpha(0)
    for handle in legend.legend_handles:
        handle.set_alpha(0)
    assert _found(fig) == []


def test_a_frameless_legend_with_entries_is_still_reported() -> None:
    fig, ax = _fig()
    _flat_line_under_centre(ax)
    ax.legend(loc="center", frameon=False)
    (w,) = _found(fig)
    assert w.detail["covered"] == ["line"]


def _text_under_legend(**text_kw):
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.plot([0, 1], [0.05, 0.05], label="Low")
    text = ax.text(0.5, 0.5, "Centre note", ha="center", va="center", **text_kw)
    ax.legend(loc="center")
    return fig, text


def test_a_text_is_compared_where_it_is_drawn() -> None:
    """A text clipped away or drawn at alpha 0 is not under the legend."""
    from matplotlib.transforms import Bbox

    fig, _text = _text_under_legend()
    assert [w.detail["covered"] for w in _found(fig)] == [["text"]]
    fig, text = _text_under_legend(clip_on=True)
    text.set_clip_box(Bbox.from_bounds(0, 0, 1, 1))  # display px: nowhere
    assert _found(fig) == []
    fig, _text = _text_under_legend(alpha=0)
    assert _found(fig) == []


def test_an_annotation_counts_by_its_text_not_its_arrow() -> None:
    """The arrow points at the data on purpose; the empty corner it spans is free."""
    fig, ax = _fig()
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.plot([0, 1], [0, 0.5], label="Low")
    ax.annotate(
        "Note", (9.5, 9.5), xytext=(1, 1), arrowprops={"arrowstyle": "->"}
    )
    ax.legend(loc="center")
    assert _found(fig) == []
    ax.texts[0].set_position((5, 5))  # the text itself under the legend
    assert [w.detail["covered"] for w in _found(fig)] == [["text"]]


def test_an_inset_legend_and_inset_data_are_measured() -> None:
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.plot([0, 1], [0, 0.05], label="Main")
    inset = ax.inset_axes((0.5, 0.5, 0.45, 0.45))
    _dense(inset, 3)
    inset.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.detail["legend_axes"] == 0
    assert w.detail["legend_inset"] == [0]
    assert w.detail["covered"] == ["line"]  # the inset's lines, not a panel
    assert w.message.startswith("Legend of axes[0].insets[0] covers lines")


def test_a_legend_on_an_inset_is_reported_as_a_panel() -> None:
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.plot([0, 1], [0, 0.05], label="Main")
    inset = ax.inset_axes((0.5, 0.5, 0.5, 0.5))  # reaches the corner
    inset.plot([0, 1], [0, 1])
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    assert w.detail["legend_inset"] == []
    assert "panel" in w.detail["covered"] and "line" in w.detail["covered"]
    assert "axes[0].insets[0]" in w.detail["artists"]
    assert w.detail["panels"] == [0]


# ----------------------------------------------------------- fixes
def test_the_fixes_name_the_placements_that_keep_a_legend_off_the_data() -> (
    None
):
    fig, ax = _fig()
    _dense(ax)
    ax.legend(loc="upper right")
    (w,) = _found(fig)
    suggestions = dm.validate_fixes.get_fix_suggestions(w)
    assert any("dm.place_legend(ax)" in s for s in suggestions)
    assert any("dm.label_line_ends(ax)" in s for s in suggestions)


# ------------------------------------------- LEGEND_OVERFLOW, outside size
def _names(n: int) -> list[str]:
    return [f"Region {i + 1}, seasonally adjusted" for i in range(n)]


def test_an_outside_legend_larger_than_half_its_plot_is_reported() -> None:
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "wide"))
    for i, name in enumerate(_names(16)):
        ax.plot([0, 1], [i, i + 1], label=name)
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    dm.simple_layout(fig)
    found = _found(fig, "LEGEND_OVERFLOW")
    outside = [w for w in found if "outside_ratio" in w.detail]
    assert len(outside) == 1
    (w,) = outside
    assert w.detail["axes_index"] == 0
    assert 0.5 < w.detail["outside_ratio"] < 1.0
    assert w.detail["threshold"] == 0.5
    assert "the size of its plot" in w.message
    suggestions = dm.validate_fixes.get_fix_suggestions(w)
    assert "dm.label_line_ends(ax)" in suggestions[0]


def test_a_small_outside_legend_is_not_reported() -> None:
    fig, ax = _fig()
    ax.plot([0, 1], [0, 1], label="One")
    ax.plot([0, 1], [1, 0], label="Two")
    dm.place_legend(ax, loc="right")
    dm.simple_layout(fig)
    assert _found(fig, "LEGEND_OVERFLOW") == []


def _grow_figure_legend(fig, ax, plot_area: float) -> float:
    """Add a figure legend, two entries at a time, until it is 55 % of ``plot_area``."""
    handles = [ax.plot([], [])[0] for _ in range(40)]
    share = 0.0
    for n in range(2, 41, 2):
        names = [f"Series {i + 1}" for i in range(n)]
        legend = fig.legend(handles[:n], names, loc="center", ncols=2)
        box = legend.get_window_extent(drawn_renderer(fig))
        share = box.width * box.height / plot_area
        if share > 0.55:
            assert fig.bbox.y0 <= box.y0 and box.y1 <= fig.bbox.y1
            return share
        legend.remove()
    return share


def _sized(fig) -> list[int | None]:
    return [
        w.detail["axes_index"]
        for w in _found(fig, "LEGEND_OVERFLOW")
        if "outside_ratio" in w.detail
    ]


def test_a_figure_legend_larger_than_half_the_panels_is_reported() -> None:
    fig, axs = plt.subplots(1, 2, figsize=dm.figsize("12cm", "wide"))
    axs[0].set_position((0.05, 0.3, 0.2, 0.4))
    axs[1].set_position((0.75, 0.3, 0.2, 0.4))
    renderer = drawn_renderer(fig)
    area = sum(
        box.width * box.height
        for box in (ax.get_window_extent(renderer) for ax in axs)
    )
    share = _grow_figure_legend(fig, axs[0], area)
    assert 0.55 < share < 1.0
    assert _sized(fig) == [None]


def test_a_twin_pair_counts_its_plot_box_once() -> None:
    """A figure legend's share is of the panels, not of every twin Axes.

    The legend is grown until it is 55-100 % of the one plot box: counted
    once it is reported, counted twice (Axes and twin) it would not be.
    """
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "wide"))
    ax.set_position((0.3, 0.3, 0.4, 0.4))
    twin = ax.twinx()
    ax.plot([0, 1], [0, 1])
    twin.plot([0, 1], [1, 0], color="oc.red5")
    plot = ax.get_window_extent(drawn_renderer(fig))
    share = _grow_figure_legend(fig, ax, plot.width * plot.height)
    assert 0.55 < share < 1.0
    assert _sized(fig) == [None]
