"""What a marker, a scatter point, a patch and a text draw, against their pixels.

``dm.place_legend`` and ``LEGEND_ON_DATA`` read these artists by the rules of
``_figure_geometry``: a marker or a scatter point is a disc reaching half its
edge past its size, a patch a box grown by half its edge, a text its glyphs
joined by its background box; what inks nothing, or draws only past its
clip, counts nowhere. The oracle is the drawn pixels: the extent of what the
artist changes on a blank Axes.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.patches import Circle, Rectangle
from matplotlib.transforms import Bbox, TransformedBbox

import dartwork_mpl as dm
from dartwork_mpl import _figure_geometry as fg
from tests.support.mpl_observe import drawn_renderer

GRAY = "oc.gray7"
SLACK_PX = 2.0  # antialiasing at each side of a drawn extent


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _axes():
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.set_axis_off()
    return fig, ax


def _drawn_extent(fig, artist) -> Bbox:
    """Where ``artist`` changes pixels (display px, origin at the bottom)."""

    def rgba() -> np.ndarray:
        fig.canvas.draw()
        return np.asarray(fig.canvas.buffer_rgba()).copy()

    shown = rgba()
    artist.set_visible(False)
    hidden = rgba()
    artist.set_visible(True)
    rows, cols = np.nonzero(np.any(shown != hidden, axis=2))
    h = shown.shape[0]
    return Bbox.from_extents(
        cols.min(), h - rows.max() - 1, cols.max() + 1, h - rows.min()
    )


def _close_to(a: Bbox, b: Bbox) -> bool:
    return bool(np.allclose(a.extents, b.extents, atol=SLACK_PX))


# ----------------------------------------------------------- discs
def test_a_scatter_point_reaches_half_its_edge_past_its_size() -> None:
    fig, ax = _axes()
    point = ax.scatter([5], [5], s=400, linewidths=8, color=GRAY)
    drawn = _drawn_extent(fig, point)
    xy, r = fg.drawn_scatter_discs(point, fig.dpi / 72.0)
    assert r[0] == pytest.approx((20 + 8) / 2 * fig.dpi / 72.0)
    (x, y), radius = xy[0], r[0]
    disc = Bbox.from_extents(x - radius, y - radius, x + radius, y + radius)
    assert _close_to(disc, drawn)


def test_points_that_draw_nothing_are_no_discs() -> None:
    fig, ax = _axes()
    xs = np.ma.masked_array([1, 2, 3, 4], mask=[True, False, False, False])
    points = ax.scatter(
        xs, [5, 5, 5, 5], s=[100, 100, 0, 100], alpha=[1, 0, 1, 1]
    )
    fig.canvas.draw()
    xy, _r = fg.drawn_scatter_discs(points, fig.dpi / 72.0)
    # masked, alpha 0 and size 0 are left out: only x = 4 draws
    assert np.allclose(xy[:, 0], ax.transData.transform([(4, 5)])[:, 0])


def test_a_transparent_edge_adds_nothing_to_a_disc() -> None:
    """Review of #672: an edge drawn in no colour reaches no further than the
    face, for a scatter point and a line's marker alike."""
    fig, ax = _axes()
    point = ax.scatter(
        [3], [5], s=400, linewidths=30, facecolors=GRAY, edgecolors="none"
    )
    (marker,) = ax.plot(
        [7], [5], "o", ms=20, mew=30, mfc=GRAY, mec="none", ls="none"
    )
    px = fig.dpi / 72.0
    xy, r = fg.drawn_scatter_discs(point, px)
    assert r[0] == pytest.approx(10 * px)
    assert fg.marker_radius_pt(marker) == pytest.approx(10)
    for artist, centre, radius in (
        (point, xy[0], r[0]),
        (marker, ax.transData.transform((7, 5)), 10 * px),
    ):
        x, y = centre
        disc = Bbox.from_extents(x - radius, y - radius, x + radius, y + radius)
        assert _close_to(disc, _drawn_extent(fig, artist))


def test_a_marker_reaches_half_its_edge_past_its_size() -> None:
    fig, ax = _axes()
    (line,) = ax.plot([5], [5], "o", ms=20, mew=8, color=GRAY)
    drawn = _drawn_extent(fig, line)
    radius = fg.marker_radius_pt(line) * fig.dpi / 72.0
    x, y = ax.transData.transform((5, 5))
    assert _close_to(
        Bbox.from_extents(x - radius, y - radius, x + radius, y + radius), drawn
    )


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
        (  # a full marker has no alternate half to draw
            {
                "ls": "none",
                "marker": "o",
                "mfc": "none",
                "mew": 0,
                "mfcalt": GRAY,
                "fillstyle": "full",
            },
            (False, False),
        ),
    ],
    ids=[
        "stroke",
        "alpha0",
        "no_width",
        "markers",
        "marker_no_ink",
        "alternate_face",
        "alternate_unused",
    ],
)
def test_a_line_inks_its_stroke_and_markers_by_style(style, inks) -> None:
    _fig, ax = _axes()
    (line,) = ax.plot([1, 9], [5, 5], color=GRAY, **style)
    assert (fg.line_draws_stroke(line), fg.line_draws_markers(line)) == inks


def test_a_disc_meets_a_box_only_where_its_clip_lets_it_draw() -> None:
    xy, r = np.array([[100.0, 100.0]]), np.array([10.0])
    box = Bbox.from_extents(105, 95, 150, 105)
    assert fg.discs_meet(xy, r, box)
    assert not fg.discs_meet(xy, r, Bbox.from_extents(115, 95, 150, 105))
    away = Bbox.from_extents(120, 0, 200, 200)  # the clip keeps it off the box
    assert not fg.discs_meet(xy, r, box, away)
    fig, ax = _axes()
    circle = Circle((180, 180), 5, transform=None)
    circle.set_figure(fig)
    holder = ax.plot([0], [0])[0]
    holder.set_clip_path(circle)
    path = fg.clip_path_px(holder)
    assert not fg.discs_meet(xy, r, box, fg.UNCLIPPED, path)


# ----------------------------------------------------------- boxes
def test_a_patch_draws_half_its_edge_past_its_outline() -> None:
    fig, ax = _axes()
    patch = ax.add_patch(Rectangle((3, 3), 4, 4, fc="oc.gray3", ec=GRAY, lw=16))
    drawn = _drawn_extent(fig, patch)
    box = fg.drawn_patch_box(patch, drawn_renderer(fig))
    assert box is not None and _close_to(box, drawn)


def test_a_patch_that_draws_nothing_or_only_past_its_clip_has_no_box() -> None:
    fig, ax = _axes()
    clear = ax.add_patch(Rectangle((3, 3), 1, 1, alpha=0))
    clipped = ax.add_patch(Rectangle((6, 6), 1, 1, fc=GRAY))
    clipped.set_clip_box(
        TransformedBbox(Bbox.from_extents(0, 0, 4, 4), ax.transData)
    )
    renderer = drawn_renderer(fig)
    assert fg.drawn_patch_box(clear, renderer) is None
    assert fg.drawn_patch_box(clipped, renderer) is None


def test_a_text_draws_its_background_box() -> None:
    fig, ax = _axes()
    text = ax.text(
        5,
        5,
        "Note",
        ha="center",
        va="center",
        bbox={
            "boxstyle": "square",
            "pad": 1.2,
            "fc": "oc.gray2",
            "ec": GRAY,
            "lw": 4,
        },
    )
    drawn = _drawn_extent(fig, text)
    box = fg.drawn_text_box(text, drawn_renderer(fig))
    assert box is not None and _close_to(box, drawn)
    assert box.width > text.get_window_extent(drawn_renderer(fig)).width + 10


@pytest.mark.parametrize(
    "glyph", [{"alpha": 0}, {"color": "none"}], ids=["alpha0", "colour_none"]
)
def test_a_clear_texts_background_box_still_draws(glyph) -> None:
    """Review of #672: the glyphs draw nothing, the background box does."""
    fig, ax = _axes()
    text = ax.text(5, 5, "Note", bbox={"fc": GRAY, "pad": 2}, **glyph)
    drawn = _drawn_extent(fig, text)
    assert not fg.text_inks(text)
    box = fg.drawn_text_box(text, drawn_renderer(fig))
    assert box is not None and _close_to(box, drawn)


def test_a_text_that_draws_nothing_or_only_past_its_clip_has_no_box() -> None:
    fig, ax = _axes()
    clear = ax.text(2, 2, "Hidden", alpha=0)
    clipped = ax.text(7, 7, "Clipped", clip_on=True)
    clipped.set_clip_box(
        TransformedBbox(Bbox.from_extents(0, 0, 4, 4), ax.transData)
    )
    renderer = drawn_renderer(fig)
    assert fg.text_inks(clipped) and not fg.text_inks(clear)
    assert fg.drawn_text_box(clear, renderer) is None
    assert fg.drawn_text_box(clipped, renderer) is None
