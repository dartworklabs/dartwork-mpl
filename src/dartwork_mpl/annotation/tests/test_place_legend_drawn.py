"""``place_legend`` keeps clear of what is drawn, read as ``LEGEND_ON_DATA`` reads it.

A collection item that draws no ink (a transparent face, an artist alpha of
0, an alpha array with a 0, a transparent line) or that its clip box or clip
path keeps from drawing used to count as an obstacle: the legend left the
first free spot for an empty corner. The oracle is the drawn pixels: the
square in the upper-right corner either changes them or not; where it does
not, the legend takes that corner, and ``LEGEND_ON_DATA`` agrees.

A clip cuts a line's stroke, not its centre line: a thick line whose centre
runs just past its clip still draws inside it, and the legend keeps clear of
those pixels (review of #662).
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.patches import Circle
from matplotlib.transforms import Bbox, TransformedBbox

import dartwork_mpl as dm
from tests.support.mpl_observe import drawn_renderer

SQUARE = [(7.0, 7.0), (9.8, 7.0), (9.8, 9.8), (7.0, 9.8)]
FAR = [(0.3, 4.0), (0.8, 4.0), (0.8, 4.5), (0.3, 4.5)]


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _axes():
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot([0, 10], [1, 2], label="Low line")
    ax.plot([0, 10], [2, 3], label="Lower line")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    return fig, ax


def _add(ax, case: str):
    """The upper-right square (or a line across it) as ``case`` draws it."""
    if case == "opaque":
        coll = PolyCollection(
            [SQUARE], facecolors="oc.gray5", edgecolors="none"
        )
    elif case == "face_alpha0":
        coll = PolyCollection(
            [SQUARE], facecolors=[(0, 0, 0, 0)], edgecolors="none"
        )
    elif case == "artist_alpha0":
        coll = PolyCollection(
            [SQUARE], facecolors="oc.gray5", edgecolors="none", alpha=0.0
        )
    elif case == "mixed_alpha":
        coll = PolyCollection(
            [SQUARE, FAR],
            facecolors=[(0, 0, 0, 0), (0.3, 0.3, 0.3, 1)],
            edgecolors="none",
        )
    elif case == "array_alpha":
        coll = PolyCollection(
            [SQUARE, FAR],
            facecolors="oc.gray5",
            edgecolors="none",
            alpha=[0, 1],
        )
    elif case in ("clip_box", "clip_path"):
        coll = PolyCollection(
            [SQUARE], facecolors="oc.gray5", edgecolors="none"
        )
    elif case == "line_alpha0":
        coll = LineCollection(
            [[(7, 9.4), (9.8, 9.4)]], colors=[(0, 0, 0, 0)], linewidths=2
        )
    else:
        raise ValueError(case)
    ax.add_collection(coll)
    if case == "clip_box":
        coll.set_clip_box(Bbox.from_bounds(0, 0, 1, 1))
    if case == "clip_path":
        coll.set_clip_path(Circle((1, 8), 0.5, transform=ax.transData))
    return coll


def _square_draws(case: str) -> bool:
    """Whether the square changes any pixel inside its own extent."""

    def pixels(with_square: bool) -> np.ndarray:
        fig, ax = _axes()
        if with_square:
            _add(ax, case)
        fig.canvas.draw()
        x0, y0 = ax.transData.transform((7.0, 7.0))
        x1, y1 = ax.transData.transform((9.8, 9.8))
        rgba = np.asarray(fig.canvas.buffer_rgba())
        h = rgba.shape[0]
        return rgba[int(h - y1) : int(h - y0), int(x0) : int(x1)].copy()

    return not np.array_equal(pixels(False), pixels(True))


def _upper_right(fig, ax) -> bool:
    renderer = drawn_renderer(fig)
    box = ax.get_legend().get_window_extent(renderer)
    frame = ax.get_window_extent(renderer)
    cx = (box.x0 + box.x1) / 2 - frame.x0
    cy = (box.y0 + box.y1) / 2 - frame.y0
    return bool(cx > frame.width * 0.6 and cy > frame.height * 0.6)


@pytest.mark.parametrize(
    "case",
    [
        "face_alpha0",
        "artist_alpha0",
        "mixed_alpha",
        "array_alpha",
        "clip_box",
        "clip_path",
        "line_alpha0",
    ],
)
def test_a_corner_that_draws_nothing_holds_the_legend(case: str) -> None:
    assert not _square_draws(case)  # the oracle: nothing drawn there
    fig, ax = _axes()
    _add(ax, case)
    dm.place_legend(ax)
    assert _upper_right(fig, ax)
    assert dm.validate_figure(fig, checks=("LEGEND_ON_DATA",), quiet=True) == []


def test_a_corner_that_draws_keeps_the_legend_away() -> None:
    assert _square_draws("opaque")
    fig, ax = _axes()
    _add(ax, "opaque")
    dm.place_legend(ax)
    assert not _upper_right(fig, ax)
    assert dm.validate_figure(fig, checks=("LEGEND_ON_DATA",), quiet=True) == []


# ------------------------------------------------- the clip cuts the stroke
#: Where the upper-right legend of ``_axes`` sits, in data (a little inside).
CORNER = [(8.4, 9.1), (9.9, 9.85)]


def _thick_stroke(ax, case: str) -> LineCollection:
    """A thick line whose centre runs past its clip, across the corner.

    ``axes_edge`` is the review's repro (#662): the Axes clips a line just
    above it, 35 pt wide, so half its stroke draws inside. ``clip_box_edge``
    and ``circle_clip_path`` cut a 20 pt line the same way with a clip box
    and a circle; ``outside_clip`` keeps that line wholly past its clip box.
    """
    y, width = {
        "axes_edge": (10.1, 35),
        "clip_box_edge": (9.75, 20),
        "circle_clip_path": (9.75, 20),
        "outside_clip": (9.95, 20),
    }[case]
    coll = LineCollection(
        [[(6.5, y), (10, y)]], colors="oc.gray5", linewidths=width
    )
    ax.add_collection(coll)
    if case == "clip_box_edge":
        coll.set_clip_box(
            TransformedBbox(Bbox.from_extents(5, 0, 10, 9.5), ax.transData)
        )
    elif case == "outside_clip":
        coll.set_clip_box(
            TransformedBbox(Bbox.from_extents(5, 0, 10, 9.2), ax.transData)
        )
    elif case == "circle_clip_path":
        coll.set_clip_path(Circle((9, 8.6), 0.8, transform=ax.transData))
    return coll


def _rgba(fig) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


def _changed(before: np.ndarray, after: np.ndarray, box: Bbox) -> int:
    """How many pixels inside ``box`` (display px) differ between renders."""
    h = before.shape[0]
    rows = slice(h - int(box.y1), h - int(box.y0))
    cols = slice(max(0, int(box.x0)), int(box.x1))
    return int(np.any(before[rows, cols] != after[rows, cols], axis=2).sum())


@pytest.mark.parametrize(
    "case", ["axes_edge", "clip_box_edge", "circle_clip_path"]
)
def test_a_stroke_reaching_in_from_past_its_clip_keeps_the_legend_away(
    case: str,
) -> None:
    """The clip cuts the stroke, not its centre line: the legend covers none
    of the pixels the stroke draws (the review's measure)."""
    fig, ax = _axes()
    blank = _rgba(fig)
    _thick_stroke(ax, case)
    inked = _rgba(fig)
    corner = Bbox(ax.transData.transform(CORNER))
    assert _changed(blank, inked, corner) > 0  # the oracle: it draws there
    dm.place_legend(ax)
    box = ax.get_legend().get_window_extent(drawn_renderer(fig))
    assert _changed(blank, inked, box) == 0


def test_a_stroke_wholly_past_its_clip_leaves_the_corner_free() -> None:
    fig, ax = _axes()
    blank = _rgba(fig)
    _thick_stroke(ax, "outside_clip")
    assert np.array_equal(blank, _rgba(fig))  # the oracle: it draws nothing
    dm.place_legend(ax)
    assert _upper_right(fig, ax)
