"""``place_legend`` keeps clear of what is drawn, read as ``LEGEND_ON_DATA`` reads it.

A collection item that draws no ink (a transparent face, an artist alpha of
0, an alpha array with a 0, a transparent line) or that its clip box or clip
path keeps from drawing used to count as an obstacle: the legend left the
first free spot for an empty corner. The oracle is the drawn pixels: the
square in the upper-right corner either changes them or not; where it does
not, the legend takes that corner, and ``LEGEND_ON_DATA`` agrees.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.patches import Circle
from matplotlib.transforms import Bbox

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
