"""LEGEND_ON_DATA reads line collections as data, as it reads plotted lines.

``ax.vlines``, ``ax.hlines``, errorbar bars, stem lines, ``ax.eventplot``
and a ``LineCollection`` added in data coordinates draw lines the reader
reads values from; a legend over them hid them without a word, while
``dm.place_legend`` kept clear of them. The oracle is the drawn pixels: the
collection changes pixels under the legend (drawn with the legend hidden)
and the check reports ``line``. A collection that draws nothing there
(transparent, clipped away), a reference drawn with x in data and y in Axes
coordinates (as ``axvline`` is not data) and a touch of half a point do not
count.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.collections import LineCollection
from matplotlib.transforms import Bbox, TransformedBbox

import dartwork_mpl as dm
from tests.support.mpl_observe import drawn_renderer

ID = "LEGEND_ON_DATA"
GRAY = "oc.gray7"


@pytest.fixture(autouse=True)
def _style():
    dm.style.use("report")
    yield
    plt.close("all")


def _kinds(fig) -> list[tuple[str, object]]:
    found = dm.validate_figure(fig, checks=(ID,), quiet=True)
    return [(w.check_id, (w.detail or {}).get("covered")) for w in found]


def _axes():
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot([0, 10], [1, 2], label="Low line")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    return fig, ax


def _add(ax, kind: str) -> list:
    """The line collection ``kind`` across the upper right; its artists."""
    if kind == "vlines":
        return [ax.vlines([8.0, 8.6, 9.2, 9.8], 0, 10, colors=GRAY, lw=1.5)]
    if kind == "hlines":
        return [ax.hlines([8.4, 9.0, 9.6], 0, 10, colors=GRAY, lw=1.5)]
    if kind == "line_collection":
        coll = LineCollection([[(5, 9.7), (10, 9.7)]], colors=GRAY, lw=2)
        return [ax.add_collection(coll)]
    if kind == "errorbar":
        bars = ax.errorbar(
            [8.4, 9.2], [8.8, 9.0], yerr=1.0, fmt="none", ecolor=GRAY, capsize=0
        )
        return list(bars.lines[2])
    if kind == "stem":
        stem = ax.stem([8.4, 9.2], [9.6, 9.8], markerfmt=" ", basefmt=" ")
        return [stem.stemlines]
    if kind == "eventplot":
        return list(
            ax.eventplot(
                [[8.4, 9.0, 9.6]], lineoffsets=9, linelengths=2, colors=GRAY
            )
        )
    raise ValueError(kind)


def _rgba(fig) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


def _under(fig, legend, artists) -> int:
    """Pixels the artists draw under the legend (drawn with it hidden)."""
    box = legend.get_window_extent(drawn_renderer(fig))
    legend.set_visible(False)
    shown = _rgba(fig)
    for artist in artists:
        artist.set_visible(False)
    hidden = _rgba(fig)
    for artist in artists:
        artist.set_visible(True)
    legend.set_visible(True)
    h = shown.shape[0]
    rows = slice(h - int(box.y1), h - int(box.y0))
    cols = slice(int(box.x0), int(box.x1))
    return int(np.any(shown[rows, cols] != hidden[rows, cols], axis=2).sum())


@pytest.mark.parametrize(
    "kind",
    ["vlines", "hlines", "line_collection", "errorbar", "stem", "eventplot"],
)
def test_a_legend_on_a_line_collection_is_reported(kind: str) -> None:
    fig, ax = _axes()
    made = _add(ax, kind)
    legend = ax.legend(loc="upper right")
    assert _under(fig, legend, made) > 0  # the oracle: it draws there
    assert _kinds(fig) == [(ID, ["line"])]


@pytest.mark.parametrize("mode", ["transparent", "clipped_away", "reference"])
def test_a_line_collection_that_is_no_data_under_the_legend_does_not_count(
    mode: str,
) -> None:
    fig, ax = _axes()
    if mode == "reference":  # x in data, y in Axes: drawn, but not data
        coll = ax.vlines(
            [8.0, 8.6, 9.2, 9.8],
            0,
            1,
            colors=GRAY,
            transform=ax.get_xaxis_transform(),
        )
    else:
        colors = [(0, 0, 0, 0)] if mode == "transparent" else GRAY
        coll = ax.vlines([8.0, 8.6, 9.2, 9.8], 0, 10, colors=colors, lw=1.5)
    if mode == "clipped_away":
        coll.set_clip_box(
            TransformedBbox(Bbox.from_extents(0, 0, 10, 4), ax.transData)
        )
    legend = ax.legend(loc="upper right")
    assert (_under(fig, legend, [coll]) > 0) is (mode == "reference")
    assert _kinds(fig) == []


def _hline_near_the_legend_bottom(overlap_pt: float):
    """A 1 pt ``hlines`` stroke reaching ``overlap_pt`` into the legend's bottom."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot([], [], label="Mean")
    ax.set(xlim=(0, 10), ylim=(0, 10))
    legend = ax.legend(loc="upper left")
    box = legend.get_window_extent(drawn_renderer(fig))
    half = 0.5 * fig.dpi / 72.0
    y_px = box.y0 - half + overlap_pt * fig.dpi / 72.0
    ((_x, y),) = ax.transData.inverted().transform([(box.x0, y_px)])
    ax.hlines([y], 0, 10, lw=1.0, colors="oc.gray5")
    return fig


def test_a_line_collection_within_half_a_point_is_a_touch() -> None:
    assert _kinds(_hline_near_the_legend_bottom(0.25)) == []


def test_a_line_collection_more_than_half_a_point_in_is_a_cover() -> None:
    assert _kinds(_hline_near_the_legend_bottom(1.0)) == [(ID, ["line"])]


@pytest.mark.parametrize(
    ("style", "covered"),
    [
        ({"linestyles": [(0, (1, 1000))]}, False),  # one dash, then a gap
        ({"linestyles": "--"}, True),  # dashes under the legend
        ({"linestyles": [(0, (1, 1000))], "gapcolor": "oc.gray3"}, True),
    ],
    ids=["gap_under_the_legend", "dashes_under_the_legend", "gap_drawn"],
)
def test_a_dashed_line_collection_counts_where_its_dashes_draw(
    style: dict, covered: bool
) -> None:
    """Review of #672: the gap of a dashed ``hlines`` draws nothing, as a
    dashed line's does; a gap colour draws the gaps."""
    fig, ax = _axes()
    coll = ax.hlines([9.7], 0, 10, colors=GRAY, lw=3, **style)
    legend = ax.legend(loc="upper right")
    assert (_under(fig, legend, [coll]) > 0) is covered  # the oracle
    assert _kinds(fig) == ([(ID, ["line"])] if covered else [])
