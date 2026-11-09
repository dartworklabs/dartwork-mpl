"""One rule for what an artist draws: ``dm.place_legend`` and the validate checks share it.

The placer (``annotation._legend_fit``, ``annotation._bar_label_settle``) and
the checks (``validate._checks.legend_on_data``, ``value_label_on_data``) used
to carry their own copies of how a collection's paths are placed, which of
its items draw ink and where a clip lets an artist draw. They now call the
functions of ``_figure_geometry``; the first group of tests pins that each
of them holds the same function object (a local copy would not be it), the
second pins what the shared rule answers, against the drawn pixels where it
matters.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.patches import Circle, Rectangle
from matplotlib.transforms import Bbox

import dartwork_mpl as dm
from dartwork_mpl import _figure_geometry as fg
from dartwork_mpl.annotation import _bar_label_settle, _legend_fit
from dartwork_mpl.validate._checks import legend_on_data, value_label_on_data


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


# ------------------------------------------------- one function, every caller
@pytest.mark.parametrize(
    ("module", "name", "shared"),
    [
        (
            _legend_fit,
            "drawn_collection_outlines",
            fg.drawn_collection_outlines,
        ),
        (_legend_fit, "clip_region", fg.clip_region),
        (_legend_fit, "clip_path_px", fg.clip_path_px),
        (_legend_fit, "within_clip_path", fg.within_clip_path),
        (
            legend_on_data,
            "drawn_collection_outlines",
            fg.drawn_collection_outlines,
        ),
        (legend_on_data, "artist_shown", fg.artist_shown),
        (legend_on_data, "clip_region", fg.clip_region),
        (legend_on_data, "clip_path_px", fg.clip_path_px),
        (legend_on_data, "within_clip_path", fg.within_clip_path),
        (value_label_on_data, "_clip_region", fg.clip_region),
        (value_label_on_data, "_clip_path", fg.clip_path_px),
        (value_label_on_data, "_within_path", fg.within_clip_path),
        (_bar_label_settle, "clip_region", fg.clip_region),
    ],
    ids=lambda v: getattr(v, "__name__", str(v)).rsplit(".", 1)[-1],
)
def test_the_placer_and_the_checks_hold_the_shared_function(
    module, name, shared
) -> None:
    assert getattr(module, name) is shared


@pytest.mark.parametrize(
    ("module", "name"),
    [
        (_legend_fit, "_collection_paths"),
        (legend_on_data, "_drawn_paths"),
        (legend_on_data, "_drawn_outlines"),
        (legend_on_data, "_shown"),
        (_bar_label_settle, "_clip_extents"),
    ],
)
def test_no_private_copy_of_the_rule_is_left(module, name: str) -> None:
    assert not hasattr(module, name)


# ------------------------------------------------------------ what it answers
def _axes():
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.set(xlim=(0, 10), ylim=(0, 10))
    return fig, ax


def _pixels(fig) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


def test_paths_are_placed_by_their_offsets_in_display_px() -> None:
    """A LineCollection given offsets draws each segment at its offset."""
    fig, ax = _axes()
    coll = LineCollection(
        [[(0, 0), (1, 0)]],
        offsets=[(2, 3), (6, 7)],
        offset_transform=ax.transData,
        transform=ax.transData,
    )
    ax.add_collection(coll)
    fig.canvas.draw()
    drawn = fg.drawn_collection_paths(coll)
    assert [i for i, _path in drawn] == [0, 1]
    starts = np.array([path.vertices[0] for _i, path in drawn])
    # The segment's own (0, 0) in data maps to the origin's display point,
    # then moves by the offset's display position.
    origin = ax.transData.transform((0, 0))
    shifts = ax.transData.transform([(2, 3), (6, 7)])
    assert starts == pytest.approx(origin + shifts, abs=1e-6)


@pytest.mark.parametrize(
    ("style", "kept"),
    [
        (
            {"facecolors": [(0, 0, 0, 0), (0, 0, 0, 1)], "edgecolors": "none"},
            [1],
        ),
        ({"facecolors": "k", "edgecolors": "none", "alpha": [0.0, 1.0]}, [1]),
        (
            {
                "facecolors": "none",
                "edgecolors": "none",
                "hatch": "//",
                "alpha": [1.0, 0.0],
            },
            [0],
        ),
        (
            {"facecolors": "none", "edgecolors": "k", "linewidths": [0.0, 2.0]},
            [1],
        ),
    ],
    ids=["face_alpha", "artist_alpha_array", "hatch_alpha_array", "edge_width"],
)
def test_only_the_items_that_draw_ink_are_outlined(style, kept) -> None:
    """Each item by its own colour, alpha and width; the oracle is the
    pixels of each item drawn alone."""
    square = [(1, 1), (3, 1), (3, 3), (1, 3)]
    other = [(6, 6), (8, 6), (8, 8), (6, 8)]
    fig, ax = _axes()
    coll = PolyCollection([square, other], **style)
    ax.add_collection(coll)
    blank = _axes()[0]
    outlines = fg.drawn_collection_outlines(coll, fig.canvas.get_renderer())
    drawn_alone = []
    for i, poly in enumerate((square, other)):
        f, a = _axes()
        alone = {
            k: (v[i] if isinstance(v, list) else v) for k, v in style.items()
        }
        a.add_collection(PolyCollection([poly], **alone))
        drawn_alone.append(not np.array_equal(_pixels(f), _pixels(blank)))
    assert [i for i, drawn in enumerate(drawn_alone) if drawn] == kept
    assert len(outlines) == len(kept)


def test_an_edge_counts_at_its_own_width() -> None:
    fig, ax = _axes()
    coll = PolyCollection(
        [[(1, 1), (2, 1), (2, 2)], [(5, 5), (6, 5), (6, 6)]],
        facecolors="none",
        edgecolors="k",
        linewidths=[1.0, 4.0],
    )
    ax.add_collection(coll)
    renderer = fig.canvas.get_renderer()
    halves = [o.half for o in fg.drawn_collection_outlines(coll, renderer)]
    px = float(np.asarray(renderer.points_to_pixels(1.0)))
    assert halves == pytest.approx([0.5 * px, 2.0 * px])


def test_artist_shown_reads_an_alpha_per_item() -> None:
    _fig, ax = _axes()
    assert fg.artist_shown(ax.scatter([1, 2], [1, 2], alpha=[0.0, 0.6]))
    assert not fg.artist_shown(ax.scatter([1, 2], [1, 2], alpha=[0.0, 0.0]))
    hidden = ax.scatter([1, 2], [1, 2])
    hidden.set_visible(False)
    assert not fg.artist_shown(hidden)


def test_the_clip_region_is_the_clip_box_and_the_clip_paths_extent() -> None:
    fig, ax = _axes()
    coll = PolyCollection([[(1, 1), (3, 1), (3, 3)]], facecolors="k")
    ax.add_collection(coll)
    fig.canvas.draw()
    frame = ax.get_window_extent()
    assert fg.clip_region(coll).bounds == pytest.approx(frame.bounds)
    coll.set_clip_box(Bbox.from_bounds(0, 0, 1, 1))
    assert fg.clip_region(coll).bounds == pytest.approx((0, 0, 1, 1))
    coll.set_clip_on(False)
    assert fg.clip_region(coll) is fg.UNCLIPPED
    assert fg.clip_path_px(coll) is None


def test_a_rectangle_clip_path_is_a_clip_box() -> None:
    """matplotlib stores a Rectangle clip path as a clip box: no path."""
    fig, ax = _axes()
    coll = PolyCollection([[(1, 1), (3, 1), (3, 3)]], facecolors="k")
    ax.add_collection(coll)
    coll.set_clip_path(Rectangle((8, 8), 1, 1, transform=ax.transData))
    fig.canvas.draw()
    assert fg.clip_path_px(coll) is None
    corners = ax.transData.transform([(8, 8), (9, 9)])
    assert fg.clip_region(coll).bounds == pytest.approx(
        Bbox(corners).bounds, abs=1e-6
    )


def test_a_clip_path_away_from_a_box_lets_none_of_it_through() -> None:
    fig, ax = _axes()
    coll = PolyCollection([[(1, 1), (3, 1), (3, 3)]], facecolors="k")
    ax.add_collection(coll)
    coll.set_clip_path(Circle((8.5, 8.5), 0.5, transform=ax.transData))
    fig.canvas.draw()
    path = fg.clip_path_px(coll)
    assert path is not None
    near = Bbox(ax.transData.transform([(8.2, 8.2), (8.8, 8.8)]))
    far = Bbox(ax.transData.transform([(1, 1), (3, 3)]))
    assert fg.within_clip_path(near, path) is near
    assert fg.within_clip_path(far, path) is None
    region = fg.clip_region(coll)
    assert region.bounds == pytest.approx(path.get_extents().bounds)
