"""``place_legend(ax)`` on a polar Axes keeps off the angle labels and the circle.

A polar Axes draws its frame (the circle) and its tick labels (the angles
round the circle, the radii inside it) within its own box, where a
rectilinear Axes keeps them outside. An inside spot that only looked at the
data took the bottom of a radar on a slide, over two angle labels and the
circle; it now takes a spot clear of them, or goes outside.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import drawn_tick_labels
from tests.support.mpl_observe import drawn_renderer

PRESETS = ("scientific", "report", "presentation")


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _radar(preset: str):
    """The bundled polar template's radar, its legend left to ``place_legend``."""
    dm.style.use(preset)
    categories = ["Speed", "Cost", "Quality", "Reach", "Trust", "Service"]
    plan_a = [4.0, 3.2, 4.5, 2.8, 4.1, 3.5]
    plan_b = [3.0, 4.5, 3.0, 4.0, 3.2, 4.2]
    theta = np.linspace(0, 2 * np.pi, len(categories), endpoint=False)
    loop = np.concatenate([theta, theta[:1]])
    fig, ax = plt.subplots(
        figsize=dm.figsize_for("matrix"), subplot_kw={"projection": "polar"}
    )
    for name, values in (("Plan A", plan_a), ("Plan B", plan_b)):
        ax.plot(loop, values + values[:1], linewidth=dm.lw(0), label=name)
        ax.fill(loop, values + values[:1], alpha=0.3)
    ax.set_xticks(theta)
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 5)
    legend = dm.place_legend(ax)
    assert legend is not None
    dm.simple_layout(fig)
    return fig, ax


def _crossings(fig, ax) -> list[str]:
    """What the legend box meets: drawn tick labels and the circle's stroke."""
    renderer = drawn_renderer(fig)
    box = ax.get_legend().get_window_extent(renderer)
    met = [
        label.get_text()
        for which in ("x", "y")
        for label in drawn_tick_labels(ax, which)
        if label.get_text().strip()
        and box.overlaps(label.get_window_extent(renderer))
    ]
    spine = ax.spines["polar"]
    path = spine.get_transform().transform_path(spine.get_path())
    if path.intersects_bbox(box, filled=False):
        met.append("circle")
    return met


@pytest.mark.parametrize("preset", PRESETS)
def test_a_radar_legend_clears_the_angle_labels_and_the_circle(
    preset: str,
) -> None:
    fig, ax = _radar(preset)
    assert _crossings(fig, ax) == []
    found = dm.validate_figure(
        fig,
        checks=("LEGEND_OVERLAP", "LEGEND_ON_DATA", "LEGEND_OVERFLOW"),
        quiet=True,
    )
    assert [w.check_id for w in found] == []


def test_a_radar_with_a_free_corner_keeps_its_legend_inside() -> None:
    """In a report the box's corners beyond the circle hold the legend:
    inside first, outside only when no spot is clear."""
    fig, ax = _radar("report")
    renderer = drawn_renderer(fig)
    box = ax.get_legend().get_window_extent(renderer)
    frame = ax.get_window_extent(renderer)
    assert frame.x0 <= box.x0 and box.x1 <= frame.x1
    assert frame.y0 <= box.y0 and box.y1 <= frame.y1
