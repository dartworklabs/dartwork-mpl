"""``text_window_extent`` measures a 3D axes' text where it draws.

``Text3D`` (``ax.text(x, y, z, ...)``) is placed by projection only while
it draws; its own ``get_window_extent`` reads the unprojected ``(x, y)``.
The oracle here is the box matplotlib itself reports during that draw, read
from inside ``Text.draw`` while ``Text3D.draw`` has the projected point and
angle applied.
"""

from __future__ import annotations

from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from dartwork_mpl._figure_geometry import text_window_extent


def _drawn_boxes(monkeypatch: pytest.MonkeyPatch, fig: Any) -> dict[str, Bbox]:
    seen: dict[str, Bbox] = {}
    original = Text.draw

    def draw(self: Text, renderer: Any) -> None:
        if hasattr(self, "get_position_3d"):
            seen[self.get_text()] = Text.get_window_extent(self, renderer)
        original(self, renderer)

    monkeypatch.setattr(Text, "draw", draw)
    fig.canvas.draw()
    monkeypatch.setattr(Text, "draw", original)
    return seen


def _cube() -> tuple[Any, Any]:
    fig = plt.figure(figsize=(4, 4), dpi=100)
    ax = fig.add_subplot(projection="3d")
    ax.set(xlim=(0, 1), ylim=(0, 1), zlim=(0, 1))
    return fig, ax


@pytest.mark.parametrize("zdir", [None, "x", "y", (1, 1, 0)])
def test_text3d_extent_is_the_box_it_draws(
    monkeypatch: pytest.MonkeyPatch, zdir: Any
) -> None:
    fig, ax = _cube()
    ax.view_init(elev=25, azim=-60)
    label = ax.text(0.2, 0.7, 0.4, "Projected label", zdir=zdir)
    drawn = _drawn_boxes(monkeypatch, fig)["Projected label"]
    measured = text_window_extent(label, fig.canvas.get_renderer())
    np.testing.assert_allclose(measured.extents, drawn.extents, atol=0.01)
    plt.close(fig)


def test_text3d_extent_follows_a_log_axis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fig, ax = _cube()
    ax.set_xscale("log")
    ax.set_xlim(1, 100)
    label = ax.text(10, 0.5, 0.5, "On a log axis")
    drawn = _drawn_boxes(monkeypatch, fig)["On a log axis"]
    measured = text_window_extent(label, fig.canvas.get_renderer())
    np.testing.assert_allclose(measured.extents, drawn.extents, atol=0.01)
    plt.close(fig)


def test_text3d_draw_hides_has_an_empty_extent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fig, ax = _cube()
    hidden = ax.text(2.0, 0.5, 0.5, "Clipped away", axlim_clip=True)
    # Text3D.draw hands Text.draw a NaN position, which draws nothing.
    drawn = _drawn_boxes(monkeypatch, fig)["Clipped away"]
    assert not np.isfinite(drawn.extents).any()
    measured = text_window_extent(hidden, fig.canvas.get_renderer())
    assert measured.width == 0 and measured.height == 0
    plt.close(fig)


def test_2d_text_is_its_window_extent() -> None:
    fig, ax = _cube()
    flat = ax.text2D(0.1, 0.9, "flat", transform=ax.transAxes)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    np.testing.assert_allclose(
        text_window_extent(flat, renderer).extents,
        flat.get_window_extent(renderer).extents,
    )
    plt.close(fig)
