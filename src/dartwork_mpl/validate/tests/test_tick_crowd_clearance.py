"""TICK_CROWD speaks only where neighbouring tick labels stand closer than
half an em: the layout's own target for them.

It reported a row whenever its labels, plus 15 % of their footprint, were
longer than the axis. Long names on the widest slide canvas stood 0.52 em
apart, flat, and still "filled 105 % of the axis": the layout had nothing
left to do and the canvas no wider width to take, so an agent had nothing
to act on. Two y labels 1.24 em apart in a short panel read as crowded the
same way. Now a row is crowded where it fills the axis *and* some
neighbouring pair stands closer than half an em; labels that close are
still reported, whatever else holds.
"""

from __future__ import annotations

from itertools import pairwise

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import get_renderer
from dartwork_mpl.validate import validate_figure

LONG = [
    "Variant A control",
    "Variant B low fee",
    "Variant C high fee",
    "Variant D hybrid",
]


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _crowd(fig, axis: str) -> list:
    return [
        w
        for w in validate_figure(fig, checks=["TICK_CROWD"], quiet=True)
        if w.detail.get("axis") == axis
    ]


def _row(labels, renderer, which: str) -> tuple[float, float]:
    """Closest neighbours' gap (ems) and the labels' summed length (px)
    along the axis, upright labels."""
    boxes = sorted(
        (t.get_window_extent(renderer) for t in labels if t.get_text()),
        key=(lambda b: b.x0) if which == "x" else (lambda b: b.y0),
    )
    em = labels[0].get_fontsize() * labels[0].figure.dpi / 72
    if which == "x":
        gap = min(b.x0 - a.x1 for a, b in pairwise(boxes))
        return gap / em, sum(b.width for b in boxes)
    gap = min(b.y0 - a.y1 for a, b in pairwise(boxes))
    return gap / em, sum(b.height for b in boxes)


def test_long_names_half_an_em_apart_on_the_widest_slide_are_not_crowded():
    """The long-name boxplot on 23.4 cm slides: flat, 0.52 em apart, and
    longer with 15 % than the axis. Nothing is left to act on."""
    dm.style.use("presentation")
    fig, ax = plt.subplots(
        figsize=dm.figsize_for(n_points=4, n_series=1, labels=LONG)
    )
    rng = np.random.default_rng(42)
    ax.boxplot([rng.normal(1, 1, 80) for _ in LONG], widths=0.55)
    ax.set_xticks(range(1, 5), LONG)
    ax.set(xlabel="Portfolio variant", ylabel="Weekly return (%)")
    dm.simple_layout(fig, margin=dm.inch(0.08))
    fig.canvas.draw()
    renderer = get_renderer(fig)
    labels = ax.get_xticklabels()
    gap, length = _row(labels, renderer, "x")
    # precondition: flat, half an em apart, and over the old 15 % budget
    assert {t.get_rotation() for t in labels} == {0.0}
    assert gap >= 0.5
    assert 1.15 * length > ax.get_window_extent(renderer).width
    assert _crowd(fig, "x") == []


def test_two_y_labels_far_apart_in_a_short_panel_are_not_crowded():
    """Two y labels over 1 em apart; the panel is shorter than their
    heights plus 15 %."""
    fig = plt.figure(figsize=dm.figsize("12cm", "6cm"))
    ax = fig.add_axes((0.2, 0.3, 0.6, 0.2))
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 1])
    fig.canvas.draw()
    renderer = get_renderer(fig)
    height = ax.get_yticklabels()[0].get_window_extent(renderer).height
    # the axes as tall as two labels: they stand one label height apart
    left, bottom, width, _ = ax.get_position().bounds
    ax.set_position((left, bottom, width, 2 * height / fig.bbox.height))
    fig.canvas.draw()
    gap, length = _row(ax.get_yticklabels(), renderer, "y")
    assert gap >= 0.5  # precondition
    assert 1.15 * length > ax.get_window_extent(renderer).height
    assert _crowd(fig, "y") == []


def _close_names(gap_em: float):
    """Five names at 0..4, flat, ``gap_em`` apart: the axes 4.1 steps
    wide, so the row with 15 % is longer than the axis; no layout."""
    dm.style.use("report")
    fig = plt.figure(figsize=dm.figsize("12cm", "6cm"))
    ax = fig.add_axes((0.05, 0.3, 0.9, 0.6))
    ax.set_xlim(-0.05, 4.05)
    ax.set_xticks(range(5), [f"Region name {k}" for k in range(5)])
    fig.canvas.draw()
    renderer = get_renderer(fig)
    label = ax.get_xticklabels()[0]
    em = label.get_fontsize() * fig.dpi / 72
    step = label.get_window_extent(renderer).width + gap_em * em
    left, bottom, _, height = ax.get_position().bounds
    ax.set_position((left, bottom, 4.1 * step / fig.bbox.width, height))
    fig.canvas.draw()
    return fig, ax


def test_names_closer_than_half_an_em_that_fill_the_axis_stay_crowded():
    fig, ax = _close_names(0.3)
    renderer = get_renderer(fig)
    gap, length = _row(ax.get_xticklabels(), renderer, "x")
    assert 0 < gap < 0.5  # precondition
    assert 1.15 * length > ax.get_window_extent(renderer).width
    assert len(_crowd(fig, "x")) == 1


def test_the_report_names_the_closest_neighbours():
    """An agent reads how close the labels stand, not only how much of the
    axis they fill."""
    fig, _ax = _close_names(0.3)
    (warning,) = _crowd(fig, "x")
    assert "0.30 em apart" in warning.message


def test_the_check_and_the_layout_share_the_clearance() -> None:
    from dartwork_mpl.layout._fit_labels import _TARGET_EM
    from dartwork_mpl.validate._checks import tick_crowd

    assert getattr(tick_crowd, "_NEIGHBOUR_CLEARANCE_EM", None) == _TARGET_EM
