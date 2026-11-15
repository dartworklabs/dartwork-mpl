"""A text's background box is ink a legend keeps clear of, its glyphs aside."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.transforms import Bbox

import dartwork_mpl as dm
from dartwork_mpl.legend.ink import _drawn_text_box


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


@pytest.mark.parametrize(
    "glyph",
    [{}, {"alpha": 0}, {"color": "none"}],
    ids=["ink", "alpha0", "none"],
)
def test_a_text_draws_its_background_box(glyph) -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.set(xlim=(0, 10), ylim=(0, 10))
    ax.set_axis_off()
    box = {"fc": "oc.gray2", "ec": "oc.gray7", "lw": 4, "pad": 2}
    text = ax.text(5, 5, "Note", bbox=box, **glyph)
    drawn = _drawn_extent(fig, text)
    measured = _drawn_text_box(text, fig.canvas.get_renderer())
    assert measured is not None
    assert np.allclose(measured.extents, drawn.extents, atol=2.0)
    text.set_clip_on(True)
    text.set_clip_box(Bbox.from_extents(0, 0, 1, 1))
    assert _drawn_text_box(text, fig.canvas.get_renderer()) is None
