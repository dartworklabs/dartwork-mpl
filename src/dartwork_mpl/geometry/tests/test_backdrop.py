"""What is behind a text's ink, read while the figure is drawn once.

The oracle is a figure whose backgrounds are known colours: a text that
runs from white paper onto a black block.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib import patheffects
from matplotlib.artist import Artist
from matplotlib.backend_bases import RendererBase
from matplotlib.patches import Rectangle

import dartwork_mpl as dm
from dartwork_mpl import geometry as g
from dartwork_mpl.colorspace import LEGIBLE

BLACK, WHITE = (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)


def _half_dark(**text):
    """An Axes whose right half is black, and a grey text across the edge."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("8cm", "standard"))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.add_patch(Rectangle((0.5, 0), 0.5, 1, color="black", zorder=1))
    note = ax.text(
        0.5, 0.5, "across the edge", ha="center", va="center",
        color="#333333", fontsize=dm.fs(4), zorder=3, **text,
    )  # fmt: skip
    return fig, ax, note


def _dark_share(paper: np.ndarray) -> float:
    return float(np.mean(paper.max(axis=1) < 0.1))


def test_each_ink_pixel_is_read_against_the_colour_behind_it():
    """Half the text is on the block: about half its ink has black behind
    it and the rest white, and the ink is the text's own colour."""
    fig, _ax, note = _half_dark()
    (behind,) = g.backdrops(fig, [note])
    assert len(behind.ink) > 200
    assert 0.35 < _dark_share(behind.paper) < 0.65
    assert float(np.mean(behind.paper.min(axis=1) > 0.9)) > 0.3
    assert float(np.median(behind.ink)) < 0.4
    reading = behind.read(LEGIBLE)
    assert not reading.reads and 0.35 < reading.low < 0.65
    assert behind.read_as(np.array(WHITE), LEGIBLE).low > 0.3


@pytest.mark.parametrize("rotation", [0, 90, 30])
def test_a_turned_text_is_judged_along_the_way_it_is_written(rotation: int):
    """Turned text still crosses the block: pixels on it are on the dark
    side, and it is as many half-em windows long however it is turned on
    the canvas."""
    fig, ax, note = _half_dark(rotation=rotation)
    (behind,) = g.backdrops(fig, [note])
    edge = ax.transData.transform((0.5, 0.0))[0]
    on_block = behind.pixels[:, 0] > edge + 2
    assert _dark_share(behind.paper[on_block]) > 0.95
    flat_fig, _ax, flat = _half_dark()
    (level,) = g.backdrops(flat_fig, [flat])
    long = float(np.ptp(level.places[:, 0]))
    assert long > 8
    assert float(np.ptp(behind.places[:, 0])) == pytest.approx(long, abs=0.5)


class _Counted(Artist):
    """An artist of the user's own that counts its draws."""

    def __init__(self) -> None:
        super().__init__()
        self.draws = 0

    def draw(self, renderer: RendererBase) -> None:
        self.draws += 1


def test_the_figure_is_drawn_once_and_its_canvas_holds_it():
    """Reading what is behind the texts draws the figure's artists once
    and fires its ``draw_event`` once, as ``fig.canvas.draw()`` does, and
    leaves the canvas holding the same pixels."""
    fig, ax, note = _half_dark()
    mine = _Counted()
    ax.add_artist(mine)
    events: list[object] = []
    fig.canvas.mpl_connect("draw_event", events.append)
    fig.canvas.draw()
    plain = (mine.draws, len(events))
    own = np.asarray(fig.canvas.buffer_rgba()).copy()
    assert plain == (1, 1)
    g.backdrops(fig, [note])
    assert (mine.draws, len(events)) == (2, 2)
    assert np.array_equal(np.asarray(fig.canvas.buffer_rgba()), own)


def test_a_text_that_is_only_stroked_is_read_as_its_strokes():
    """``path_effects=[Stroke(...)]`` without a fill after it is how the
    text is drawn, not a halo: its ink is read, half of it on the block."""
    fig, _ax, note = _half_dark(
        path_effects=[patheffects.Stroke(linewidth=0.7, foreground="#333333")]
    )
    (behind,) = g.backdrops(fig, [note])
    reading = behind.read(LEGIBLE)
    assert len(behind.ink) > 200
    assert not reading.reads and 0.35 < reading.low < 0.65


def test_a_translucent_text_and_one_drawn_over_are_read_as_shown():
    """A text at a quarter alpha is painted a quarter of its colour over
    what is behind it. Under an opaque band drawn over it, the ink shows
    the band: there it is not seen at all."""
    fig, _ax, faint = _half_dark(alpha=0.25)
    (behind,) = g.backdrops(fig, [faint])
    on_white = behind.paper.min(axis=1) > 0.9
    assert float(np.median(behind.ink[on_white])) == pytest.approx(
        0.25 * 0.2 + 0.75, abs=0.03
    )
    # ... and so would any other colour be: white at a quarter alpha does
    # not read on the black half either (2:1), let alone on the white one.
    assert behind.read_as(np.array(WHITE), LEGIBLE).low > 0.95
    fig, ax, note = _half_dark()
    (before,) = g.backdrops(fig, [note])
    ax.axhspan(0, 1, color="#777777", zorder=5)
    (hidden,) = g.backdrops(fig, [note])
    assert len(hidden.ink) == len(before.ink)
    assert float(np.abs(hidden.ink - hidden.paper).max()) < 0.02
    assert hidden.read(LEGIBLE).low == 1.0


def test_a_halo_and_the_text_s_own_box_are_paper_and_an_arrow_is_not_ink():
    """A stroked outline wide enough to see is read as a plate under the
    glyphs, a hairline is not, and the box is read as drawn; neither they
    nor an annotation's arrow count as ink."""
    fig, ax, note = _half_dark()
    (plain,) = g.backdrops(fig, [note])
    note.set_path_effects(
        [
            patheffects.Stroke(linewidth=4, foreground="white"),
            patheffects.Normal(),
        ]
    )
    (haloed,) = g.backdrops(fig, [note])
    assert _dark_share(haloed.paper) < 0.02
    note.set_path_effects(
        [
            patheffects.Stroke(linewidth=0.05, foreground="white"),
            patheffects.Normal(),
        ]
    )
    (hairline,) = g.backdrops(fig, [note])
    assert _dark_share(hairline.paper) > 0.3  # a hairline is no background
    note.set_path_effects([])
    note.set_bbox({"facecolor": "white", "edgecolor": "none"})
    (boxed,) = g.backdrops(fig, [note])
    assert _dark_share(boxed.paper) < 0.02
    note.set_bbox(None)
    pointer = ax.annotate(
        "across the edge", xy=(0.9, 0.9), xytext=(0.5, 0.5), ha="center",
        va="center", color="#333333", fontsize=dm.fs(4), zorder=3,
        arrowprops={"arrowstyle": "-", "color": "red", "linewidth": 6},
    )  # fmt: skip
    note.set_visible(False)
    (arrowed,) = g.backdrops(fig, [pointer])
    assert abs(len(arrowed.ink) - len(plain.ink)) < 0.05 * len(plain.ink)
    assert float(arrowed.ink[:, 0].max()) < 0.6  # no red arrow pixels


def test_several_lines_are_judged_line_by_line():
    """One line of three on the block is lost though it is a third of the
    ink of every column: a window is one line high."""
    fig, ax, _note = _half_dark()
    _note.set_visible(False)
    ax.add_patch(Rectangle((0, 0.55), 1, 0.45, color="black", zorder=1))
    lines = ax.text(
        0.25, 0.62, "same words\nsame words\nsame words", ha="center",
        va="top", color="#333333", fontsize=dm.fs(4), zorder=3,
    )  # fmt: skip
    (behind,) = g.backdrops(fig, [lines])
    reading = behind.read(LEGIBLE)
    assert 0.2 < reading.low < 0.5 and not reading.reads


def test_a_text_that_paints_nothing_has_no_ink_and_no_texts_draw_nothing():
    """A text clipped out of its Axes reads as empty; an empty request
    does not draw the figure at all."""
    fig, ax, note = _half_dark()
    note.set_position((3.0, 0.5))
    note.set_clip_on(True)
    (behind,) = g.backdrops(fig, [note])
    assert len(behind.ink) == 0 and behind.read(LEGIBLE).reads
    drawn: list[object] = []
    fig.canvas.mpl_connect("draw_event", drawn.append)
    assert g.backdrops(fig, []) == [] and not drawn
