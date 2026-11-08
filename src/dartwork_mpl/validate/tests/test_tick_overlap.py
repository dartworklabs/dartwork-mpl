"""TICK_OVERLAP: neighbouring tick labels of one axis drawn on top of each other.

The oracle for upright labels is their window extents (overlap along the
axis, more than half a pixel); turned labels are checked against the
rectangle their text fills, which the upright extent overstates.
"""

from __future__ import annotations

from itertools import pairwise

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.ticker import FixedFormatter, FixedLocator

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import drawn_tick_labels, get_renderer
from dartwork_mpl.validate import Severity, VisualWarning
from dartwork_mpl.validate.fixes import get_fix_suggestions


@pytest.fixture(autouse=True)
def _scientific():
    with matplotlib.rc_context():
        dm.style.use("scientific")
        yield
    plt.close("all")


def _findings(fig) -> list[VisualWarning]:
    return dm.validate_figure(fig, checks=("TICK_OVERLAP",), quiet=True)


def _bars(labels: list[str], width: str = "9cm"):
    fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"))
    ax.bar(range(len(labels)), np.arange(len(labels)) + 1.0)
    ax.set_xticks(range(len(labels)), labels)
    return fig, ax


def _upright_overlaps(ax, which: str = "x") -> list[float]:
    """Overlap (px) along the axis of each neighbouring pair, from extents."""
    fig = ax.get_figure()
    fig.canvas.draw()
    renderer = get_renderer(fig)
    boxes = [
        t.get_window_extent(renderer) for t in drawn_tick_labels(ax, which)
    ]
    if which == "x":
        spans = sorted((b.x0, b.x1) for b in boxes)
    else:
        spans = sorted((b.y0, b.y1) for b in boxes)
    return [a[1] - b[0] for a, b in pairwise(spans)]


def test_crowded_x_labels_warn_once_per_axis_with_every_pair() -> None:
    fig, ax = _bars([f"Variant {c}" for c in "ABCDEFGH"])
    expected = [d for d in _upright_overlaps(ax) if d > 0.5]
    assert expected, "precondition: the labels overlap"
    [warning] = _findings(fig)
    assert warning.severity is Severity.WARNING
    assert warning.detail["axis"] == "x"
    assert warning.detail["axes_index"] == 0
    assert warning.detail["pairs"] == len(expected)
    assert warning.detail["labels"] == 8
    assert warning.detail["rotation"] == 0
    # depth across the thinner direction: the overlap along x here
    assert warning.detail["px"] == pytest.approx(max(expected), abs=0.1)


def test_labels_that_only_come_close_pass() -> None:
    fig, ax = _bars(["North", "South", "East", "West"])
    assert max(_upright_overlaps(ax)) <= 0.5
    assert _findings(fig) == []


def test_turned_labels_whose_boxes_cross_but_whose_text_does_not_pass() -> None:
    names = [f"A rather long category name, number {i}" for i in range(6)]
    fig, ax = _bars(names, width="17cm")
    ax.tick_params(axis="x", labelrotation=45, labelrotation_mode="xtick")
    assert min(_upright_overlaps(ax)) > 0.5, "precondition: the boxes cross"
    assert _findings(fig) == []


def test_upright_labels_turned_a_quarter_still_crowded_warn() -> None:
    fig, ax = _bars([f"Item {i}" for i in range(80)])
    ax.tick_params(axis="x", labelrotation=90)
    [warning] = _findings(fig)
    assert warning.detail["rotation"] == 90


def test_bottom_and_top_labels_are_neighbours_only_on_their_side() -> None:
    labels = [f"Variant {c}" for c in "ABCDEFGH"]
    fig, ax = _bars(labels)
    [bottom] = _findings(fig)
    ax.tick_params(axis="x", labeltop=True)
    [both] = _findings(fig)
    assert both.detail["pairs"] == 2 * bottom.detail["pairs"]
    assert both.detail["labels"] == 16


def test_crowded_rows_of_horizontal_bars_warn_on_y() -> None:
    names = [f"Region {i}" for i in range(60)]
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.barh(names, np.arange(60.0))
    assert max(_upright_overlaps(ax, "y")) > 0.5
    [warning] = _findings(fig)
    assert warning.detail["axis"] == "y"


def test_a_polar_axes_is_not_read() -> None:
    fig = plt.figure(figsize=dm.figsize("6cm", "square"))
    ax = fig.add_subplot(projection="polar")
    ax.plot(np.linspace(0, 6, 50), np.ones(50))
    ax.set_thetagrids(
        range(0, 360, 10), labels=[f"Label {i}" for i in range(36)]
    )
    fig.canvas.draw()
    renderer = get_renderer(fig)
    boxes = [
        t.get_window_extent(renderer)
        for t in ax.get_xticklabels()
        if t.get_text()
    ]
    assert any(a.overlaps(b) for a, b in pairwise(boxes)), (
        "precondition: neighbouring theta labels cross"
    )
    assert _findings(fig) == []


def test_a_hidden_axes_is_not_reported() -> None:
    # The idiom for an empty grid slot: nothing of the Axes is drawn.
    fig, ax = _bars([f"Variant {c}" for c in "ABCDEFGH"])
    assert _findings(fig), "precondition: shown, the labels overlap"
    ax.set_visible(False)
    assert _findings(fig) == []


_LONG = "A long tick label, the same width twice"


def _minor_labels(places: list[float], *, major: tuple[float, ...] = ()):
    """Labelled minor ticks at ``places`` (and major ones at ``major``)."""
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.set_xlim(0, 1)
    ax.set_xticks(list(major), [_LONG] * len(major))
    ax.xaxis.set_minor_locator(FixedLocator(places))
    ax.xaxis.set_minor_formatter(FixedFormatter([_LONG] * len(places)))
    ax.tick_params(axis="x", which="minor", labelbottom=True)
    return fig, ax


def _two_label_overlap(ax) -> float:
    """Overlap (px) of the two drawn x labels, major or minor, from extents.

    Upright rectangles: the depth is the thinner of the overlaps along x
    and along y.
    """
    fig = ax.get_figure()
    fig.canvas.draw()
    renderer = get_renderer(fig)
    labels = [
        *drawn_tick_labels(ax, "x"),
        *drawn_tick_labels(ax, "x", minor=True),
    ]
    [a, b] = sorted(
        (t.get_window_extent(renderer) for t in labels), key=lambda e: e.x0
    )
    return min(a.x1 - b.x0, min(a.y1, b.y1) - max(a.y0, b.y0))


def test_minor_labels_that_overlap_are_reported() -> None:
    fig, ax = _minor_labels([0.3, 0.7])
    depth = _two_label_overlap(ax)
    assert depth > 0.5, "precondition: the minor labels overlap"
    [warning] = _findings(fig)
    assert (warning.detail["pairs"], warning.detail["labels"]) == (1, 2)
    assert warning.detail["px"] == pytest.approx(depth, abs=0.1)


def test_a_minor_label_running_into_a_major_one_is_reported() -> None:
    fig, ax = _minor_labels([0.7], major=(0.3,))
    depth = _two_label_overlap(ax)
    assert depth > 0.5, "precondition: the major and minor labels overlap"
    [warning] = _findings(fig)
    assert (warning.detail["pairs"], warning.detail["labels"]) == (1, 2)


def test_minor_labels_are_neighbours_only_on_their_side() -> None:
    fig, ax = _minor_labels([0.3, 0.7])
    [bottom] = _findings(fig)
    ax.tick_params(axis="x", which="minor", labeltop=True)
    [both] = _findings(fig)
    assert (both.detail["pairs"], both.detail["labels"]) == (
        2 * bottom.detail["pairs"],
        4,
    )


def _fixes(detail: dict) -> list[str]:
    return get_fix_suggestions(
        VisualWarning(Severity.WARNING, "TICK_OVERLAP", "m", detail)
    )


@pytest.mark.parametrize(
    "detail",
    [
        {"axis": "x", "rotation": 30},
        {"axis": "x", "rotation": 0},
        {"axis": "y"},
    ],
)
def test_fixes_never_make_text_smaller(detail: dict) -> None:
    fixes = _fixes(detail)
    assert fixes
    for fix in fixes:
        assert "fontsize" not in fix
        assert "labelsize" not in fix
        assert "dm.fs(" not in fix


def test_turned_labels_are_offered_the_layout_first() -> None:
    first = _fixes({"axis": "x", "rotation": 30})[0]
    assert "labelrotation=0" in first
    assert "dm.simple_layout(fig)" in first


def test_upright_x_labels_get_horizontal_bars_or_a_wider_canvas() -> None:
    fixes = _fixes({"axis": "x", "rotation": 0})
    assert not any("labelrotation" in f for f in fixes)
    assert any("ax.barh(" in f for f in fixes)
    assert any("figsize('17cm'" in f for f in fixes)


def test_crowded_rows_get_a_taller_canvas() -> None:
    [fix] = _fixes({"axis": "y"})
    assert "'tall'" in fix
