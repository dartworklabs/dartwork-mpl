"""Text checks skip ``ax.text(x, y, z, ...)`` on a 3D axes (Text3D).

A ``Text3D`` is placed by projecting its data position while it draws, so
outside a draw its window extent reads the unprojected ``(x, y)`` through
the 3D axes' 2D transform: thousands of pixels off the canvas. Matplotlib's
own layout leaves it out for that reason (``Text3D.get_tightbbox`` returns
``None``) and so does ``simple_layout``. OVERFLOW and CLIPPED_TEXT used to
read it, so the shipped plot_3d template reported its two minimum labels,
drawn inside the canvas, as thousands of pixels past it. 2D text on a 3D
axes (``ax.text2D``) is measured as before.
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

import dartwork_mpl as dm
from dartwork_mpl.validate import validate_figure

_TEXT_CHECKS = ("OVERFLOW", "CLIPPED_TEXT", "OVERLAP")


def _surface_with_labels() -> tuple[Figure, Any]:
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
    return fig, ax


@pytest.fixture(autouse=True)
def _restore_style() -> Iterator[None]:
    yield
    plt.close("all")
    dm.style.use("report")


def test_text3d_inside_the_canvas_is_not_reported() -> None:
    fig, _ax = _surface_with_labels()
    found = validate_figure(fig, checks=_TEXT_CHECKS, quiet=True)
    assert found == [], [w.message for w in found]


def test_2d_text_on_a_3d_axes_is_still_measured() -> None:
    fig, ax = _surface_with_labels()
    ax.text2D(1.6, 0.5, "Past the right edge", transform=ax.transAxes)
    found = validate_figure(fig, checks=("OVERFLOW",), quiet=True)
    assert [w.detail["text"] for w in found] == ["Past the right edge"]
