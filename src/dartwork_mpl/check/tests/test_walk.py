"""A 3D axes' text is measured where it draws: its box holds its inked pixels."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import Bbox
from mpl_toolkits.mplot3d.axes3d import Axes3D

from dartwork_mpl.check import walk


def _cube() -> tuple[Figure, Axes3D]:
    fig = plt.figure(figsize=(4, 4), dpi=100)
    ax = fig.add_subplot(projection="3d")
    assert isinstance(ax, Axes3D)
    ax.set(xlim=(0, 1), ylim=(0, 1), zlim=(0, 1))
    ax.view_init(elev=25, azim=-60)
    return fig, ax


def _pixels(fig: Figure) -> np.ndarray:
    w, h = fig.bbox.size
    agg = RendererAgg(int(w), int(h), fig.dpi)
    fig.draw(agg)
    return np.asarray(agg.buffer_rgba())[..., :3].astype(int)


def _ink(fig: Figure, text: Text) -> Bbox | None:
    """The pixels that change when ``text`` alone is hidden, in display px."""
    shown = _pixels(fig)
    text.set_visible(False)
    hidden = _pixels(fig)
    text.set_visible(True)
    rows, cols = np.nonzero((shown != hidden).any(axis=2))
    if not len(rows):
        return None
    height = shown.shape[0]
    return Bbox.from_extents(
        cols.min(), height - rows.max() - 1, cols.max() + 1, height - rows.min()
    )


@pytest.mark.parametrize("zdir", [None, "x", "y", "z", (1, 1, 0)])
def test_text3d_box_holds_its_ink(
    zdir: str | tuple[int, int, int] | None,
) -> None:
    fig, ax = _cube()
    label = ax.text(0.2, 0.7, 0.4, "Projected label", zdir=zdir, color="red")
    ink = _ink(fig, label)
    assert ink is not None
    box = walk.placed(label)
    assert box.padded(1.5).containsx(ink.x0) and box.padded(1.5).containsx(
        ink.x1
    )
    assert box.padded(1.5).containsy(ink.y0) and box.padded(1.5).containsy(
        ink.y1
    )
    assert box.width * box.height < 2.5 * ink.width * ink.height
    plt.close(fig)


def test_a_text3d_the_draw_hides_has_no_box() -> None:
    fig, ax = _cube()
    hidden = ax.text(2.0, 0.5, 0.5, "Clipped away", axlim_clip=True)
    assert _ink(fig, hidden) is None
    box = walk.placed(hidden)
    assert not np.isfinite(box.extents).all() or box.width * box.height == 0
    plt.close(fig)
