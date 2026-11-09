"""The root grid's edge reservations count the Figure's own artists only.

``simple_layout`` reserves each figure edge for a suptitle, ``fig.text`` or
figure legend there. A SubFigure keeps its legend and suptitle in its own
box, which may sit in the middle of the canvas: reserving a root edge for
it would pull the whole grid in for nothing. The figure-level walk now
reads SubFigures for the checks; the reservations keep to the root.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.layout._reservations import _figure_artist_reservations


@pytest.fixture(autouse=True)
def _close():
    dm.style.use("report")
    yield
    plt.close("all")


@pytest.mark.parametrize("owner", ["figure", "subfigure"])
def test_only_the_figures_own_legend_reserves_an_edge(owner: str) -> None:
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    left, right = fig.subfigures(1, 2)
    left.subplots().plot([0, 1], [0, 1])
    ax = right.subplots()
    ax.plot([0, 1], [1, 0], label="Series")
    holder = fig if owner == "figure" else right
    holder.legend(loc="center left", bbox_to_anchor=(0.0, 0.5))
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    w, h = fig.bbox.width, fig.bbox.height
    sides = _figure_artist_reservations(fig, renderer, w, h)
    reserved = max(sides.left, sides.right, sides.bottom, sides.top)
    assert bool(reserved > 0) is (owner == "figure")
