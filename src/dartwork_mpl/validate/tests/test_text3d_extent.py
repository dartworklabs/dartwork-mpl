"""Text checks measure ``ax.text(x, y, z, ...)`` (Text3D) where it draws.

A ``Text3D`` is placed by projection only while it draws, so outside a
draw its ``get_window_extent`` reads the unprojected ``(x, y)`` through the
3D axes' 2D transform: thousands of pixels off. OVERFLOW and CLIPPED_TEXT
read that and reported the shipped plot_3d template's two minimum labels,
drawn inside the canvas, as far past it; leaving Text3D out instead hid
real clipping and overlaps. The checks now measure the projected box
(``_figure_geometry.text_window_extent``), the box this file reads from
inside the draw as the oracle. 2D text on a 3D axes is measured as before.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import Bbox

import dartwork_mpl as dm
from dartwork_mpl.validate import validate_figure

_TEXT_CHECKS = ("OVERFLOW", "CLIPPED_TEXT", "OVERLAP")


@pytest.fixture(autouse=True)
def _restore_style() -> Iterator[None]:
    yield
    plt.close("all")
    dm.style.use("report")


def _cube() -> tuple[Figure, Any]:
    dm.style.use("scientific")
    fig = plt.figure(figsize=dm.figsize("9cm", "square"))
    ax = fig.add_subplot(projection="3d")
    ax.set(xlim=(0, 1), ylim=(0, 1), zlim=(0, 1))
    return fig, ax


def _drawn_box(monkeypatch: pytest.MonkeyPatch, fig: Figure, text: str) -> Bbox:
    """The box matplotlib reports for ``text`` during its own draw."""
    seen: dict[str, Bbox] = {}
    original = Text.draw

    def draw(self: Text, renderer: Any) -> None:
        if hasattr(self, "get_position_3d"):
            seen[self.get_text()] = Text.get_window_extent(self, renderer)
        original(self, renderer)

    monkeypatch.setattr(Text, "draw", draw)
    fig.canvas.draw()
    monkeypatch.setattr(Text, "draw", original)
    return seen[text]


def test_text3d_inside_the_canvas_is_not_reported() -> None:
    dm.style.use("scientific")
    fig = plt.figure(figsize=dm.figsize_for("matrix"))
    ax = fig.add_subplot(projection="3d")
    x = np.linspace(-3, 3, 30)
    X, Y = np.meshgrid(x, x)
    ax.plot_surface(X, Y, -np.exp(-(X**2 + Y**2)), cmap="viridis")
    # Two labels in the middle of the cube, apart from each other.
    ax.text(-1.0, -0.5, -0.9, "Min 1", ha="center")
    ax.text(1.2, 1.0, -0.6, "Min 2", ha="center")
    dm.simple_layout(fig)
    found = validate_figure(fig, checks=_TEXT_CHECKS, quiet=True)
    assert found == [], [w.message for w in found]


def test_text3d_partly_past_the_edge_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fig, ax = _cube()
    ax.text(
        1.4, 0.5, 0.5, "Projected outside", fontsize=dm.fs(0), clip_on=False
    )
    drawn = _drawn_box(monkeypatch, fig, "Projected outside")
    past = drawn.x1 - fig.bbox.x1
    assert drawn.x0 < fig.bbox.x1 < drawn.x1  # partly on the canvas
    found = validate_figure(
        fig, checks=("OVERFLOW", "CLIPPED_TEXT"), quiet=True
    )
    by_id = {w.check_id: w.detail for w in found}
    assert set(by_id) == {"OVERFLOW", "CLIPPED_TEXT"}, [
        w.message for w in found
    ]
    assert by_id["OVERFLOW"]["side"] == "right"
    assert by_id["OVERFLOW"]["px"] == pytest.approx(past, abs=0.1)
    assert by_id["CLIPPED_TEXT"]["margin_px"] == pytest.approx(-past, abs=0.1)


def test_text3d_wholly_outside_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fig, ax = _cube()
    ax.text(
        3.0, 0.5, 0.5, "Projected outside", fontsize=dm.fs(0), clip_on=False
    )
    drawn = _drawn_box(monkeypatch, fig, "Projected outside")
    assert drawn.x0 > fig.bbox.x1  # nothing of it on the canvas
    found = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
    assert [w.detail["side"] for w in found] == ["right"]
    assert found[0].detail["px"] == pytest.approx(
        drawn.x1 - fig.bbox.x1, abs=0.1
    )


def test_text3d_labels_on_one_point_overlap() -> None:
    fig, ax = _cube()
    ax.text(0.5, 0.5, 0.5, "Overlap alpha")
    ax.text(0.5, 0.5, 0.5, "Overlap beta")
    found = validate_figure(fig, checks=("OVERLAP",), quiet=True)
    assert [(w.detail["label_a"], w.detail["label_b"]) for w in found] == [
        ("Overlap alpha", "Overlap beta")
    ]


def test_2d_text_on_a_3d_axes_is_still_measured() -> None:
    fig, ax = _cube()
    ax.text(0.5, 0.5, 0.5, "Inside")
    ax.text2D(1.6, 0.5, "Past the right edge", transform=ax.transAxes)
    found = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
    assert [w.detail["text"] for w in found] == ["Past the right edge"]
