"""VALUE_LABEL_ON_DATA: value labels drawn over bars, lines and markers.

Each case is a figure an agent writes; the oracle is what a reader sees: a
label whose ink lies on a bar it does not belong to, on a line, or on a
marker it is not inside. The negatives are the designs that put text on
data on purpose (inside labels, bubbles, heatmap cells, boxed labels,
contour labels, annotation arrows), the library's own placements, and
artists the reader cannot see.
"""

from __future__ import annotations

import time

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.transforms import Bbox

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import get_renderer
from dartwork_mpl.validate import Severity
from dartwork_mpl.validate._checks.value_label_on_data import (
    check_value_label_on_data,
)

ID = "VALUE_LABEL_ON_DATA"


@pytest.fixture(autouse=True)
def _style():
    dm.style.use("report")
    yield
    plt.close("all")


def _found(fig):
    dm.simple_layout(fig)
    return list(dm.validate_figure(fig, checks=(ID,), quiet=True))


def _fig():
    return plt.subplots(figsize=dm.figsize("12cm", "standard"))


def _line_with_centred_labels(**line_kw):
    fig, ax = _fig()
    x, y = np.arange(6), np.array([12, 18, 15, 22, 19, 25])
    line = ax.plot(x, y, **line_kw)[0]
    texts = [
        ax.text(xi, yi, f"{yi}", ha="center", va="center")
        for xi, yi in zip(x, y, strict=True)
    ]
    return fig, ax, line, texts


# ----------------------------------------------------------- must report
def test_reports_labels_centred_on_line_points():
    fig, _ax, _line, _texts = _line_with_centred_labels(marker="o")
    (w,) = _found(fig)
    assert w.severity == Severity.WARNING
    assert w.detail["count"] == 6
    assert w.detail["covered"] == ["line"]  # a line met is one hit


def test_reports_markers_alone_when_the_line_is_not_drawn():
    fig, _ax, _line, _texts = _line_with_centred_labels(
        marker="o", linestyle="none"
    )
    (w,) = _found(fig)
    assert w.detail["covered"] == ["marker"]


def test_reports_bar_labels_under_a_combo_line():
    # label_bars places 3 pt beyond the ends; a target line runs there.
    fig, ax = _fig()
    x = np.arange(5)
    values = np.array([40, 42, 41, 43, 42])
    ax.bar(x, values)
    dm.label_bars(ax)
    ax.plot(x, values + 1.3, color="dc.red6", label="Target")
    (w,) = _found(fig)
    assert w.detail["covered"] == ["line"]
    assert w.detail["artists"] == ["Target"]


def test_reports_a_twin_line_over_the_bar_labels():
    # The plot box is shared: the twin's line covers the bars' labels
    # (label_bars draws them on the top Axes of the pair).
    fig, ax = _fig()
    x = np.arange(5)
    ax.bar(x, [40, 42, 41, 43, 42])
    dm.label_bars(ax)
    twin = ax.twinx()
    twin.set_ylim(0, 50)
    twin.plot(x, [43.5, 45.5, 44.5, 46.5, 45.5], label="YoY")
    (w,) = _found(fig)
    assert w.detail["count"] == 5
    assert w.detail["artists"] == ["YoY"]


def test_reports_a_twin_line_over_hand_labels_on_the_primary():
    # The labels belong to the primary Axes; the line to its twin.
    fig, ax = _fig()
    values = [40, 42, 41, 43, 42]
    ax.bar(range(5), values)
    for i, v in enumerate(values):
        ax.text(i, v, f"{v}", ha="center", va="bottom")
    twin = ax.twinx()
    twin.set_ylim(0, 50)
    twin.plot(range(5), [43.5, 45.5, 44.5, 46.5, 45.5], label="YoY")
    (w,) = _found(fig)
    assert w.detail["axes_index"] == 0
    assert w.detail["artists"] == ["YoY"]


def _on_flat_line(dy_pt, va, linewidth=2.0):
    """A ``va`` label ``dy_pt`` points above a point of a flat line."""
    fig, ax = _fig()
    ax.plot(range(5), [5] * 5, linewidth=linewidth)
    ax.set_ylim(0, 10)
    ax.annotate(
        "50",
        (2, 5),
        xytext=(0, dy_pt),
        textcoords="offset points",
        ha="center",
        va=va,
    )
    return fig


def test_reports_digits_set_on_a_thick_line_centre():
    # The 2 pt stroke's upper half (1 pt) runs through the digits' feet.
    assert [
        w.detail["covered"] for w in _found(_on_flat_line(0, "baseline"))
    ] == [["line"]]


def _checked(fig):
    """Validate as laid out: the line below was placed in display units."""
    return list(dm.validate_figure(fig, checks=(ID,), quiet=True))


def _line_under_baseline(label, rotation, offset_pt):
    """``label`` on a baseline through (.5, .5), a 0.8 pt line beside it.

    The line runs along the baseline, ``offset_pt`` points off it on the
    glyphs' top side (negative: towards their feet), turned with the text.
    """
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.text(
        0.5,
        0.5,
        label,
        fontsize=28,
        ha="center",
        va="baseline",
        rotation=rotation,
        rotation_mode="anchor",
    )
    dm.simple_layout(fig)
    phi = np.radians(rotation)
    along = np.array([np.cos(phi), np.sin(phi)])
    normal = np.array([-np.sin(phi), np.cos(phi)])
    centre = ax.transData.transform((0.5, 0.5))
    centre = centre + normal * offset_pt * fig.dpi / 72
    ends = ax.transData.inverted().transform(
        [centre - along * 100, centre + along * 100]
    )
    ax.plot(ends[:, 0], ends[:, 1], linewidth=0.8)
    return fig


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("label", ["10 g", "10 y", "10 p", "10 $p$"])
def test_reports_a_line_through_the_descenders(label, rotation):
    # 2.5 pt under the baseline the line cuts the tails of g, y and p
    # (about 6 pt deep at 28 pt): drawn ink, not the box's empty descent.
    found = _checked(_line_under_baseline(label, rotation, -2.5))
    assert [w.detail["covered"] for w in found] == [["line"]]


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_clean_when_a_line_runs_under_bare_digits(rotation):
    # Digits have no tail: 0.6 pt under the baseline the line only touches
    # their feet, and 2.5 pt under it the box's descent is empty.
    assert _checked(_line_under_baseline("10", rotation, -0.6)) == []
    assert _checked(_line_under_baseline("10", rotation, -2.5)) == []


def test_reports_a_hand_label_centred_on_the_bar_end():
    fig, ax = _fig()
    values = [20, 35, 30]
    ax.bar(range(3), values)
    for i, v in enumerate(values):
        ax.text(i, v, f"{v}", ha="center", va="center")
    (w,) = _found(fig)
    assert w.detail["count"] == 3
    assert w.detail["covered"] == ["bar"]


def test_reports_wide_hand_labels_on_grouped_neighbours():
    fig, ax = _fig()
    x = np.arange(4)
    a = ax.bar(x - 0.2, [1200, 1350, 1300, 1420], 0.4)
    b = ax.bar(x + 0.2, [1100, 1500, 1250, 1380], 0.4)
    for bars in (a, b):
        for p in bars:
            ax.text(
                p.get_x() + p.get_width() / 2,
                p.get_height() * 0.97,
                f"{p.get_height():,.0f} units",
                ha="center",
                va="top",
            )
    (w,) = _found(fig)
    assert "bar" in w.detail["covered"]


def test_reports_point_labels_on_small_scatter_markers():
    fig, ax = _fig()
    x, y = np.array([1, 2, 3, 4]), np.array([3, 1, 4, 2])
    ax.scatter(x, y, s=30, label="Sites")
    for xi, yi in zip(x, y, strict=True):
        ax.text(xi + 0.02, yi, f"{yi}", ha="left", va="center")
    (w,) = _found(fig)
    assert w.detail["covered"] == ["marker"]
    assert w.detail["artists"] == ["Sites"]


@pytest.mark.parametrize("kind", ["scatter", "plot"])
@pytest.mark.parametrize(("left_pt", "covers"), [(5, True), (30, False)])
def test_reports_a_marker_reaching_in_from_outside_the_axes(
    kind, left_pt, covers
):
    # A 20 pt marker centred 5 pt left of the axes is drawn 5 pt into it,
    # under the label at the edge; centred 30 pt left it stays outside.
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.annotate(
        "1,250",
        (0, 0.5),
        xytext=(1, 0),
        textcoords="offset points",
        ha="left",
        va="center",
    )
    dm.simple_layout(fig)
    edge = ax.transData.transform((0, 0.5))
    x, y = ax.transData.inverted().transform(edge - [left_pt * fig.dpi / 72, 0])
    if kind == "scatter":
        ax.scatter([x], [y], s=20**2, linewidths=0)
    else:
        ax.plot([x], [y], marker="o", markersize=20, markeredgewidth=0)
    found = [w.detail["covered"] for w in _checked(fig)]
    assert found == ([["marker"]] if covers else [])


def test_reports_a_bubble_label_spilling_onto_the_next_bubble():
    # Its own bubble does not count; the neighbour it reaches does.
    fig, ax = _fig()
    ax.set_xlim(0, 4)
    ax.scatter([1.9, 2.1], [1, 1], s=[900, 900])
    ax.text(1.9, 1, "1,250", ha="center", va="center")
    (w,) = _found(fig)
    assert w.detail["covered"] == ["marker"]


def test_reports_one_warning_per_axes_with_the_wire_detail():
    fig, (left, right) = plt.subplots(
        1, 2, figsize=dm.figsize("17cm", "standard")
    )
    for ax in (left, right):
        ax.plot([0, 1, 2], [1, 3, 2], label="Load")
        ax.text(1, 3, "3.0", ha="center", va="center")
        ax.text(0.5, 1.0, "1.0", ha="center", va="bottom")  # off the line
    found = _found(fig)
    assert [w.detail for w in found] == [
        {
            "axes_index": i,
            "count": 1,
            "labels": 2,
            "covered": ["line"],
            "artists": ["Load"],
            "example": "3.0",
        }
        for i in (0, 1)
    ]
    assert found[0].message == (
        "Axes[0]: 1 of 2 value labels are drawn over lines (first '3.0'); "
        "move them off the data"
    )
    tips = dm.validate_fixes.get_fix_suggestions(found[0])
    assert len(tips) == 3
    assert "dm.label_bars(ax)" in tips[0]
    assert "dm.annotate_value(ax, x, y, text)" in tips[1]
    assert "textcoords='offset points'" in tips[2]


# ------------------------------------------------------- must not report
@pytest.mark.parametrize("where", ["auto", "inside", "center"])
def test_clean_when_label_bars_labels_bars_and_stacks(where):
    fig, ax = _fig()
    ax.bar(range(4), [20, 35, 30, 35])
    ax.bar(range(4), [25, 32, 34, 20], bottom=[20, 35, 30, 35])
    dm.label_bars(ax, where=where)
    assert _found(fig) == []


def test_clean_when_label_bars_labels_horizontal_bars():
    fig, ax = _fig()
    ax.barh(range(4), [20, 35, 30, 35])
    dm.label_bars(ax, where="inside")
    assert _found(fig) == []


def test_clean_when_a_label_rests_on_the_bar_end():
    fig, ax = _fig()
    values = [20, 35, 30]
    ax.bar(range(3), values)
    for i, v in enumerate(values):
        ax.text(i, v, f"{v}", ha="center", va="bottom")
    assert _found(fig) == []


def test_clean_when_baseline_labels_sit_on_the_bar_ends():
    # ax.text's default va="baseline": the digits stand on the bar end and
    # only the box's descent (and a comma's tail) reaches into the bar.
    fig, ax = _fig()
    values = [20, 35, 1250]
    ax.bar(range(3), values)
    ax.set_yscale("log")
    for i, v in enumerate(values):
        ax.text(i, v, f"{v:,}", ha="center")
    assert _found(fig) == []


def test_clean_when_punctuated_baseline_labels_sit_on_the_bar_ends():
    # The tails of the marks around a number ($, comma, parentheses) dip
    # into the bar; the number itself stands on its end.
    fig, ax = _fig()
    labels = ["$1,250", "(12)", "€20", "20%", "-3"]
    ax.bar(range(5), [1250, 12, 20, 20, 3])
    ax.set_yscale("log")
    for i, (text, v) in enumerate(
        zip(labels, [1250, 12, 20, 20, 3], strict=True)
    ):
        ax.text(i, v, text, ha="center", fontsize=12)
    assert _found(fig) == []


def test_clean_when_digits_rest_on_a_thick_line():
    # The baseline 0.8 pt over the stroke's centre: 0.2 pt of overlap is a
    # touch (under the 0.5 pt margin), not a cover.
    assert _found(_on_flat_line(0.8, "baseline")) == []


def test_clean_when_a_label_hangs_from_a_line():
    # va="top" puts the box's top on the line; the digits start below the
    # font's ascent, clear of the stroke.
    assert _found(_on_flat_line(0, "top", linewidth=1.5)) == []


def test_clean_when_annotate_value_and_line_end_labels_place_values():
    fig, ax = _fig()
    x, y = np.arange(8), np.array([3, 5, 4, 9, 6, 7, 5, 8])
    ax.plot(x, y, marker="o", label="Sales")
    dm.annotate_value(ax, 3, 9, "9")
    dm.label_line_ends(ax)
    assert _found(fig) == []


def test_clean_when_an_annotation_arrow_points_at_the_data():
    # The arrow reaches the marker on purpose; only the text counts.
    fig, ax = _fig()
    ax.scatter([1, 2, 3], [3, 4, 2], s=60)
    ax.annotate(
        "4",
        (2, 4),
        xytext=(30, 0),
        textcoords="offset points",
        ha="left",
        va="center",
        arrowprops={"arrowstyle": "->", "shrinkA": 0, "shrinkB": 0},
    )
    assert _found(fig) == []


def test_clean_when_text_sits_in_heatmap_cells():
    fig, ax = _fig()
    grid = np.arange(12).reshape(3, 4)
    ax.imshow(grid)
    for (r, c), v in np.ndenumerate(grid):
        ax.text(c, r, f"{v}", ha="center", va="center")
    assert _found(fig) == []


def test_clean_when_labels_sit_inside_their_bubbles():
    fig, ax = _fig()
    ax.scatter([1, 2, 3], [1, 2, 1], s=[900, 1600, 1200])
    for x, y, v in ((1, 1, 30), (2, 2, 40), (3, 1, 35)):
        ax.text(x, y, f"{v}", ha="center", va="center")
    assert _found(fig) == []


def test_clean_when_a_label_has_a_background_box():
    fig, ax = _fig()
    ax.plot(range(6), [1, 3, 2, 4, 3, 5])
    ax.text(
        2,
        2,
        "2.0",
        ha="center",
        va="center",
        bbox={"facecolor": "white", "edgecolor": "none"},
    )
    assert _found(fig) == []


def test_clean_for_contour_labels_and_slanted_labels():
    fig, ax = _fig()
    xx, yy = np.meshgrid(np.linspace(-2, 2, 60), np.linspace(-2, 2, 60))
    cs = ax.contour(xx, yy, np.exp(-(xx**2 + yy**2)), levels=4)
    ax.clabel(cs, fmt="%.1f")
    ax.scatter([0], [0], s=40, marker="*")
    assert _found(fig) == []

    # Level labels set flat on horizontal contours, a track line through them.
    fig, ax = _fig()
    xx, yy = np.meshgrid(np.linspace(0, 4, 40), np.linspace(0, 4, 40))
    cs = ax.contour(xx, yy, yy, levels=[1, 2, 3])
    texts = ax.clabel(cs, fmt="%.0f", manual=[(2, 1), (2, 2), (2, 3)])
    assert {round(t.get_rotation()) % 180 for t in texts} == {0}
    ax.plot([2, 2], [0, 4])
    assert _found(fig) == []

    fig, ax, _line, texts = _line_with_centred_labels()
    for text in texts:
        text.set_rotation(45)
    assert _found(fig) == []


def test_clean_for_reference_lines_and_pies():
    fig, ax = _fig()
    ax.bar(range(3), [5, 7, 6])
    ax.axhline(6, color="0.5")
    ax.axline((0.5, 6), slope=0.5, color="0.5")
    ax.text(0.5, 6, "6", ha="center", va="center")
    assert _found(fig) == []

    fig, ax = _fig()
    ax.pie([30, 45, 25], autopct="%1.0f%%")
    assert _found(fig) == []


def test_clean_when_the_text_is_prose():
    fig, ax = _fig()
    ax.plot(range(5), [1, 2, 3, 2, 1])
    ax.text(2, 3, "Peak season", ha="center", va="center")
    assert _found(fig) == []


@pytest.mark.parametrize(
    "hide",
    [
        pytest.param(lambda line: line.set_visible(False), id="hidden-line"),
        pytest.param(lambda line: line.set_alpha(0), id="transparent-line"),
        pytest.param(lambda line: line.set_color("none"), id="no-colour-line"),
    ],
)
def test_clean_when_the_covered_line_cannot_be_seen(hide):
    fig, _ax, line, _texts = _line_with_centred_labels()
    hide(line)
    assert _found(fig) == []


@pytest.mark.parametrize(
    "hide",
    [
        pytest.param(lambda text: text.set_visible(False), id="hidden-label"),
        pytest.param(lambda text: text.set_alpha(0), id="transparent-label"),
    ],
)
def test_clean_when_the_label_cannot_be_seen(hide):
    fig, _ax, _line, texts = _line_with_centred_labels()
    for text in texts:
        hide(text)
    assert _found(fig) == []


def _clipped_on_line(text_kind, from_line_pt):
    """A 2 pt line through a label clipped to the band above a height.

    The clip keeps what lies ``from_line_pt`` points over the line's centre
    and higher; ``None`` clips the label to a box far from it.
    """
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.plot([0.2, 0.8], [0.5, 0.5], linewidth=2)
    if text_kind == "annotation":
        label = ax.annotate(
            "50",
            (0.5, 0.5),
            xytext=(0, 0),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=20,
            arrowprops={"arrowstyle": "-", "shrinkA": 0, "shrinkB": 0},
        )
    else:
        label = ax.text(0.5, 0.5, "50", ha="center", va="center", fontsize=20)
    dm.simple_layout(fig)
    label.set_clip_on(True)
    if from_line_pt is None:
        label.set_clip_box(Bbox.from_bounds(0, 0, 1, 1))
    else:
        line_y = ax.transData.transform((0.5, 0.5))[1]
        bottom = line_y + from_line_pt * fig.dpi / 72
        label.set_clip_box(Bbox.from_extents(0, bottom, *fig.bbox.size))
    return fig


@pytest.mark.parametrize("text_kind", ["text", "annotation"])
def test_clean_when_the_label_is_clipped_off_the_line(text_kind):
    # Clipped away whole, or down to its part 2 pt over the line's centre
    # (1 pt clear of the 2 pt stroke), the label draws nothing on the line.
    assert _checked(_clipped_on_line(text_kind, None)) == []
    assert _checked(_clipped_on_line(text_kind, 2)) == []
    # The part a clip from 2 pt under the centre leaves crosses the line.
    found = _checked(_clipped_on_line(text_kind, -2))
    assert [w.detail["covered"] for w in found] == [["line"]]


def test_clean_over_invisible_spacer_bars():
    # A waterfall's invisible base bars hold no value for the reader.
    fig, ax = _fig()
    ax.bar(range(3), [10, 20, 15], color="none")
    for i, v in enumerate((10, 20, 15)):
        ax.text(i, v, f"{v}", ha="center", va="center")
    assert _found(fig) == []


def test_clean_beside_transparent_markers():
    fig, ax = _fig()
    ax.scatter([1, 2, 3], [5, 10, 7], s=60, alpha=0)
    for x, y in ((1, 5), (2, 10), (3, 7)):
        ax.annotate(
            f"{y}",
            (x, y),
            xytext=(2, 0),
            textcoords="offset points",
            ha="left",
            va="center",
        )
    assert _found(fig) == []


def _second_masked(values):
    return np.ma.array(values, mask=[False, True])


@pytest.mark.parametrize(
    "masked",
    [
        pytest.param({"x": _second_masked([0.1, 0.5])}, id="x"),
        pytest.param({"y": _second_masked([0.9, 0.5])}, id="y"),
        pytest.param({"s": _second_masked([200.0, 200.0])}, id="size"),
        pytest.param(
            {"c": _second_masked([1.0, 2.0]), "cmap": "viridis"}, id="colour"
        ),
        pytest.param({}, id="none"),
    ],
)
def test_masked_scatter_points_are_not_drawn(masked):
    # scatter draws no marker where x, y, s or c is masked; unmasked, the
    # marker at (0.5, 0.5) is under the label (the one at (0.1, 0.9) is
    # far from it).
    fig, ax = _fig()
    ax.set(xlim=(0, 1), ylim=(0, 1))
    kw = {"x": [0.1, 0.5], "y": [0.9, 0.5], "s": 200, **masked}
    ax.scatter(kw.pop("x"), kw.pop("y"), **kw)
    ax.text(0.5, 0.5, "50", ha="left", va="center", fontsize=20)
    found = [w.detail["covered"] for w in _found(fig)]
    assert found == ([] if masked else [["marker"]])


def test_reports_only_the_markers_markevery_draws():
    # markevery=3 draws markers at 0, 3, 6, 9: the label beside the bare
    # point 1 is clean, the one beside the marker at 3 is not.
    fig, ax = _fig()
    ax.plot(
        range(10),
        [5] * 10,
        linestyle="none",
        marker="o",
        markersize=6,
        markevery=3,
    )
    ax.set_ylim(0, 10)
    for x, text in ((1, "41"), (3, "43")):
        ax.annotate(
            text,
            (x, 5),
            xytext=(1.5, 0),
            textcoords="offset points",
            ha="left",
            va="center",
        )
    (w,) = _found(fig)
    assert (w.detail["count"], w.detail["example"]) == (1, "43")


# ------------------------------------------------------------------ cost
def test_costs_less_than_half_a_draw_on_a_dense_figure():
    """20,000 points x 5 lines, 100 labels, 30 bars on a 17 cm canvas.

    The budget is relative to drawing the same figure once, so a slow or
    busy machine moves both sides; the absolute figure is in the report
    (about 55 ms against 290 ms for the draw on the development host).
    """
    fig, ax = plt.subplots(figsize=dm.figsize("17cm", "standard"))
    rng = np.random.default_rng(0)
    x = np.linspace(0, 30, 20_000)
    ax.bar(np.arange(30), rng.uniform(20, 40, 30), alpha=0.4)
    for k in range(5):
        ax.plot(x, 30 + 8 * np.sin(x / 3 + k) + rng.normal(0, 0.5, x.size))
    for xi, yi in zip(
        rng.uniform(0, 30, 100), rng.uniform(15, 45, 100), strict=True
    ):
        ax.text(xi, yi, f"{yi:.1f}", ha="center", va="center")
    dm.simple_layout(fig)

    def best(fn):
        runs = []
        for _ in range(3):
            start = time.perf_counter()
            fn()
            runs.append(time.perf_counter() - start)
        return min(runs)

    draw = best(fig.canvas.draw)
    renderer = get_renderer(fig)
    found: list[object] = []
    check = best(lambda: found.extend(check_value_label_on_data(fig, renderer)))
    assert found, "the dense figure's labels do cover its lines"
    assert check < 0.5 * draw, (check, draw)
