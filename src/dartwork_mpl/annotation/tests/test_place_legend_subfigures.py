"""``place_legend`` sees the panels of other SubFigures as neighbours.

The middle of three stacked panels has its data over the whole plot, so
the legend goes outside; above and below are taken by its own column's
panels. Beside it, the right column's panels block the right side as well:
in one ``plt.subplots`` grid the placer knew that and kept the legend
inside. When the columns were SubFigures it saw only its own column, took
the right side and laid the legend on the next panel's tick labels. The
oracle is geometric: the legend box against every other panel's frame and
axis decorations.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import axes_decoration_extents
from tests.support.mpl_observe import drawn_renderer


@pytest.fixture(autouse=True)
def _close():
    dm.style.use("report")
    yield
    plt.close("all")


def _filled(ax) -> None:
    """Data over the whole plot: no inside spot is free."""
    x = np.linspace(0, 10, 50)
    for i in range(4):
        ax.fill_between(x, 0, 100, alpha=0.15, label=f"Band {i + 1}")
    ax.set(xlim=(0, 10), ylim=(0, 100), xlabel="Time [h]", ylabel="Load [kW]")


def _plain(ax) -> None:
    ax.plot([0, 1, 2], [3, 1, 2])
    ax.set(xlabel="Distance [km]", ylabel="Elevation [m]")


def _columns(kind: str):
    """Three stacked panels left and right; the middle left one is filled."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    if kind == "grid":
        (a1, b1), (a2, b2), (a3, b3) = fig.subplots(3, 2)
        right = [b1, b2, b3]
    else:
        left_fig, right_fig = fig.subfigures(1, 2)
        a1, a2, a3 = left_fig.subplots(3, 1)
        if kind == "subfigures":
            right = list(right_fig.subplots(3, 1))
        else:  # "nested": each right panel in a SubFigure of its own
            right = [sub.subplots() for sub in right_fig.subfigures(3, 1)]
    for ax in (a1, a3, *right):
        _plain(ax)
    _filled(a2)
    return fig, a2


def _on_other_panels(fig, ax, legend) -> float:
    """Area (px^2) of the legend box on any other panel's frame or labels."""
    renderer = drawn_renderer(fig)
    box = legend.get_window_extent(renderer)
    total = 0.0
    for other in fig.axes:
        if other is ax:
            continue
        for part in (
            other.get_window_extent(renderer),
            *axes_decoration_extents(other, renderer),
        ):
            w = min(box.x1, part.x1) - max(box.x0, part.x0)
            h = min(box.y1, part.y1) - max(box.y0, part.y0)
            total += max(w, 0.0) * max(h, 0.0)
    return total


@pytest.mark.parametrize("kind", ["subfigures", "nested"])
def test_a_panel_in_another_subfigure_blocks_that_side(kind: str) -> None:
    fig, ax = _columns(kind)
    legend = dm.place_legend(ax)
    assert _on_other_panels(fig, ax, legend) == 0
    assert not getattr(legend, "_dm_outside_fallback", False)


def test_the_same_panels_in_one_grid_keep_the_legend_inside() -> None:
    """The control, true before the fix: one grid's panels block the side."""
    fig, ax = _columns("grid")
    legend = dm.place_legend(ax)
    assert _on_other_panels(fig, ax, legend) == 0
    assert not getattr(legend, "_dm_outside_fallback", False)


def test_a_free_side_beside_a_subfigure_column_is_still_taken() -> None:
    """With only hidden panels to the right, the right side stays free: the
    left column's middle panel, filled, takes it."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    left_fig, right_fig = fig.subfigures(1, 2)
    a1, a2, a3 = left_fig.subplots(3, 1)
    for ax in (a1, a3):
        _plain(ax)
    _filled(a2)
    for hidden in right_fig.subplots(3, 1):
        hidden.set_visible(False)
    legend = dm.place_legend(a2)
    assert getattr(legend, "_dm_outside_fallback", False)
    assert _on_other_panels(fig, a2, legend) == 0
