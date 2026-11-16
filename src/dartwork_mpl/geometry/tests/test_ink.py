"""What an artist draws, the one rule ``dm.place_legend`` and ``dm.check`` share.

The oracle, where it matters, is the pixels the figure draws.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.patches import Circle, Rectangle
from matplotlib.path import Path
from matplotlib.transforms import Bbox, TransformedBbox

import dartwork_mpl as dm
from dartwork_mpl import geometry as g

GRAY = "oc.gray7"
SLACK_PX = 2.0  # antialiasing at each side of a drawn extent


def _axes():
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.set_axis_off()
    return fig, ax


def _pixels(fig) -> np.ndarray:
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


def _drawn_extent(fig, artist) -> Bbox:
    """Where ``artist`` changes pixels (display px, origin at the bottom)."""
    shown = _pixels(fig)
    artist.set_visible(False)
    hidden = _pixels(fig)
    artist.set_visible(True)
    rows, cols = np.nonzero(np.any(shown != hidden, axis=2))
    h = shown.shape[0]
    return Bbox.from_extents(
        cols.min(), h - rows.max() - 1, cols.max() + 1, h - rows.min()
    )


def _close_to(a: Bbox, b: Bbox) -> bool:
    return bool(np.allclose(a.extents, b.extents, atol=SLACK_PX))


def _disc(x: float, y: float, r: float) -> Bbox:
    return Bbox.from_extents(x - r, y - r, x + r, y + r)


@pytest.mark.parametrize(
    ("style", "kept"),
    [
        ({"facecolors": [(0, 0, 0, 0), (0, 0, 0, 1)], "edgecolors": "none"}, 1),
        ({"facecolors": "k", "edgecolors": "none", "alpha": [0.0, 1.0]}, 1),
        ({"facecolors": "none", "edgecolors": "k", "linewidths": [0, 2]}, 1),
    ],
    ids=["face_alpha", "alpha_per_item", "edge_width"],
)
def test_only_the_items_that_draw_ink_are_outlined(style, kept) -> None:
    fig, ax = _axes()
    square = [(1, 1), (3, 1), (3, 3), (1, 3)]
    coll = PolyCollection([square, [(6, 6), (8, 6), (8, 8)]], **style)
    ax.add_collection(coll)
    fig.canvas.draw()
    outlines = g.drawn_collection_outlines(coll, fig.canvas.get_renderer())
    assert [o.item for o in outlines] == [kept]


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
    halves = [o.half for o in g.drawn_collection_outlines(coll, renderer)]
    px = float(np.asarray(renderer.points_to_pixels(1.0)))
    assert halves == pytest.approx([0.5 * px, 2.0 * px])


def test_offset_paths_are_placed_where_they_draw() -> None:
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
    outlines = g.drawn_collection_outlines(coll, fig.canvas.get_renderer())
    starts = np.array([o.path.vertices[0] for o in outlines])
    origin = ax.transData.transform((0, 0))
    shifts = ax.transData.transform([(2, 3), (6, 7)])
    assert starts == pytest.approx(origin + shifts, abs=1e-6)


def test_the_clip_region_is_the_clip_box_or_nothing() -> None:
    fig, ax = _axes()
    coll = PolyCollection([[(1, 1), (3, 1), (3, 3)]], facecolors="k")
    ax.add_collection(coll)
    fig.canvas.draw()
    assert g.clip_region(coll).bounds == pytest.approx(
        ax.get_window_extent().bounds
    )
    coll.set_clip_on(False)
    assert g.clip_region(coll) is g.UNCLIPPED
    assert g.clip_path_px(coll) is None


#: A horizontal centre line at y = 110 px, and a clip region below it.
_LINE = Path([(0.0, 110.0), (200.0, 110.0)])
_BELOW = Bbox.from_extents(0, 0, 200, 100)
_NEAR_TOP = Bbox.from_extents(50, 80, 150, 98)


@pytest.mark.parametrize(
    ("half", "region", "meets"),
    [
        (15.0, _BELOW, True),  # its stroke reaches 95 px: inside the clip
        (5.0, _BELOW, False),  # its stroke stops at 105 px: clipped away
        (5.0, g.UNCLIPPED, False),  # 12 px from the box: not reached
    ],
    ids=["straddles", "wholly_past", "short"],
)
def test_a_clip_cuts_the_stroke_not_the_centre_line(half, region, meets):
    assert g.drawn_ink_meets(_LINE, half, _NEAR_TOP, region) is meets


def test_a_clip_path_cuts_the_stroke_too() -> None:
    """A circle of radius 20 px at (100, 90): a line 5 px past its top,
    stroked 10 px either side, draws into it; at 4 px it does not."""
    circle = Path.circle((100.0, 90.0), 20.0)
    region = circle.get_extents()
    line = Path([(0.0, 115.0), (200.0, 115.0)])
    near = Bbox.from_extents(90, 100, 110, 112)
    assert g.drawn_ink_meets(line, 10.0, near, region, circle)
    assert not g.drawn_ink_meets(line, 4.0, near, region, circle)
    # A corner of the circle's extent lies outside the circle.
    corner = Bbox.from_extents(81, 71, 85, 75)
    across = Path([(0.0, 72.0), (200.0, 72.0)])
    assert not g.drawn_ink_meets(across, 1.0, corner, region, circle)


def test_a_scatter_point_reaches_half_its_edge_past_its_size() -> None:
    fig, ax = _axes()
    point = ax.scatter([5], [5], s=400, linewidths=8, color=GRAY)
    drawn = _drawn_extent(fig, point)
    xy, r = g.drawn_scatter_discs(point, fig.dpi / 72.0)
    assert r[0] == pytest.approx((20 + 8) / 2 * fig.dpi / 72.0)
    assert _close_to(_disc(*xy[0], r[0]), drawn)


def test_points_that_draw_nothing_are_no_discs() -> None:
    fig, ax = _axes()
    xs = np.ma.masked_array([1, 2, 3, 4], mask=[True, False, False, False])
    points = ax.scatter(
        xs, [5, 5, 5, 5], s=[100, 100, 0, 100], alpha=[1, 0, 1, 1]
    )
    fig.canvas.draw()
    xy, _r = g.drawn_scatter_discs(points, fig.dpi / 72.0)
    # masked, alpha 0 and size 0 are left out: only x = 4 draws
    assert np.allclose(xy[:, 0], ax.transData.transform([(4, 5)])[:, 0])


def test_a_transparent_edge_adds_nothing_to_a_marker() -> None:
    fig, ax = _axes()
    (marker,) = ax.plot(
        [7], [5], "o", ms=20, mew=30, mfc=GRAY, mec="none", ls="none"
    )
    assert g.marker_radius_pt(marker) == pytest.approx(10)
    x, y = ax.transData.transform((7, 5))
    disc = _disc(x, y, 10 * fig.dpi / 72.0)
    assert _close_to(disc, _drawn_extent(fig, marker))


@pytest.mark.parametrize(
    ("style", "inks"),
    [
        ({}, (True, False)),
        ({"alpha": 0}, (False, False)),
        ({"lw": 0}, (False, False)),
        ({"ls": "none", "marker": "o"}, (False, True)),
        (
            {"ls": "none", "marker": "o", "mfc": "none", "mew": 0},
            (False, False),
        ),
        (  # the left half draws the alternate face
            {
                "ls": "none",
                "marker": "o",
                "mfc": "none",
                "mew": 0,
                "mfcalt": GRAY,
                "fillstyle": "left",
            },
            (False, True),
        ),
    ],
    ids=["stroke", "alpha0", "no_width", "markers", "no_ink", "alternate"],
)
def test_a_line_inks_its_stroke_and_markers_by_style(style, inks) -> None:
    _fig, ax = _axes()
    (line,) = ax.plot([1, 9], [5, 5], color=GRAY, **style)
    assert (g.line_draws_stroke(line), g.line_draws_markers(line)) == inks


def test_a_disc_meets_a_box_only_where_its_clip_lets_it_draw() -> None:
    xy, r = np.array([[100.0, 100.0]]), np.array([10.0])
    box = Bbox.from_extents(105, 95, 150, 105)
    assert g.discs_meet(xy, r, box)
    assert not g.discs_meet(xy, r, Bbox.from_extents(115, 95, 150, 105))
    assert not g.discs_meet(xy, r, box, Bbox.from_extents(120, 0, 200, 200))
    fig, ax = _axes()
    circle = Circle((180, 180), 5, transform=None)
    circle.set_figure(fig)
    holder = ax.plot([0], [0])[0]
    holder.set_clip_path(circle)
    path = g.clip_path_px(holder)
    assert not g.discs_meet(xy, r, box, g.UNCLIPPED, path)


def test_a_patch_draws_half_its_edge_past_its_outline() -> None:
    fig, ax = _axes()
    patch = ax.add_patch(Rectangle((3, 3), 4, 4, fc="oc.gray3", ec=GRAY, lw=16))
    drawn = _drawn_extent(fig, patch)
    box = g.drawn_patch_box(patch, fig.canvas.get_renderer())
    assert box is not None and _close_to(box, drawn)


def test_a_patch_that_draws_nothing_or_only_past_its_clip_has_no_box() -> None:
    fig, ax = _axes()
    clear = ax.add_patch(Rectangle((3, 3), 1, 1, alpha=0))
    clipped = ax.add_patch(Rectangle((6, 6), 1, 1, fc=GRAY))
    clipped.set_clip_box(
        TransformedBbox(Bbox.from_extents(0, 0, 4, 4), ax.transData)
    )
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    assert g.drawn_patch_box(clear, renderer) is None
    assert g.drawn_patch_box(clipped, renderer) is None
