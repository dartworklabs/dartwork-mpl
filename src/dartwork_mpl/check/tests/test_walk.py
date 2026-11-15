"""A 3D axes' text is measured where ``Text3D.draw`` puts it, not where it sits."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from dartwork_mpl.check.walk import text_window_extent


def _drawn_boxes(monkeypatch: pytest.MonkeyPatch, fig: Any) -> dict[str, Bbox]:
    """Each 3D text's extent read inside ``Text.draw``, at its projected place."""
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
    ax.view_init(elev=25, azim=-60)
    return fig, ax


@pytest.mark.parametrize("zdir", [None, "x", (1, 1, 0)])
def test_text3d_extent_is_the_box_it_draws(monkeypatch, zdir) -> None:
    fig, ax = _cube()
    label = ax.text(0.2, 0.7, 0.4, "Projected label", zdir=zdir)
    drawn = _drawn_boxes(monkeypatch, fig)["Projected label"]
    measured = text_window_extent(label, fig.canvas.get_renderer())
    np.testing.assert_allclose(measured.extents, drawn.extents, atol=0.01)


def test_a_text3d_draw_hides_has_an_empty_extent(monkeypatch) -> None:
    fig, ax = _cube()
    hidden = ax.text(2.0, 0.5, 0.5, "Clipped away", axlim_clip=True)
    drawn = _drawn_boxes(monkeypatch, fig)["Clipped away"]
    assert not np.isfinite(drawn.extents).any()  # drawn at a NaN position
    measured = text_window_extent(hidden, fig.canvas.get_renderer())
    assert measured.width == 0 and measured.height == 0
