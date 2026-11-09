"""TICK_CROWD measures turned tick labels by the room each neighbour pair needs.

A label turned by an angle fills a slanted rectangle. Two neighbours clear
each other once the distance between them along the axis reaches what the
two rectangles, each at its own angle, need under the separating-axis test,
not once each passes its whole axis-aligned window extent. TICK_CROWD used
to sum those window extents, so turned labels that stood apart (the
waterfall and boxplot templates under 30 degrees) read as filling over
100 % of the axis; a first fix measured each label against a copy of
itself, which missed neighbours turned the other way (+45 / -45) that cross
(PR #661 review). Upright labels are measured as before: their widths
along x, their heights along y.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any, Literal

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import tick_label_overlaps
from dartwork_mpl.validate import validate_figure


@pytest.fixture(autouse=True)
def _close() -> Iterator[None]:
    yield
    plt.close("all")
    dm.style.use("report")


def _labelled(
    which: Literal["x", "y"],
    angles: Sequence[float],
    aligns: Sequence[str] | None = None,
) -> tuple[Figure, Any, Any]:
    """``len(angles)`` category labels on one axis, label ``i`` at ``angles[i]``.

    Each label ends at its tick (``ha="right"``) unless ``aligns`` says
    otherwise; ``"left"`` starts it there.
    """
    fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
    n = len(angles)
    ax.plot(range(n), range(n))
    ticks = ax.set_xticks if which == "x" else ax.set_yticks
    ticks(range(n))
    labels = (ax.set_xticklabels if which == "x" else ax.set_yticklabels)(
        [f"Category name {i}" for i in range(n)],
        rotation_mode="anchor",
        fontsize=8,
    )
    for label, angle, align in zip(
        labels, angles, aligns or ["right"] * n, strict=True
    ):
        label.set_rotation(angle)
        label.set_horizontalalignment(align)
    fig.subplots_adjust(left=0.4, bottom=0.4)
    fig.canvas.draw()
    return fig, ax, fig.canvas.get_renderer()  # type: ignore[attr-defined]


def _crowd(fig: Figure, which: str) -> list[float]:
    found = validate_figure(fig, checks=("TICK_CROWD",), quiet=True)
    return [w.detail["occupancy"] for w in found if w.detail["axis"] == which]


@pytest.mark.parametrize(("which", "n"), [("x", 8), ("y", 5)])
def test_labels_turned_alike_that_stand_apart_are_not_crowded(
    which: Literal["x", "y"], n: int
) -> None:
    fig, ax, renderer = _labelled(which, [45] * n)
    assert tick_label_overlaps(ax, which, renderer).pairs == 0
    # Their window extents alone fill more than the axis: the old measure.
    labels = ax.get_xticklabels() if which == "x" else ax.get_yticklabels()
    boxes = [t.get_window_extent(renderer) for t in labels]
    frame = ax.get_window_extent(renderer)
    if which == "x":
        assert sum(b.width for b in boxes) * 1.15 > frame.width
    else:
        assert sum(b.height for b in boxes) * 1.15 > frame.height
    assert _crowd(fig, which) == []


@pytest.mark.parametrize(
    ("which", "aligns"),
    [
        # Below the x axis: -45 starting at its tick runs down to the
        # right, +45 ending at the next one runs down to the left.
        ("x", ["left", "right"] * 4),
        # Left of the y axis, both ending at their ticks: -45 runs up to
        # the left, +45 from the tick above down to the left.
        ("y", ["right", "right"] * 4),
    ],
)
def test_labels_turned_opposite_ways_that_cross_are_crowded(
    which: Literal["x", "y"], aligns: list[str]
) -> None:
    fig, ax, renderer = _labelled(which, [-45, 45] * 4, aligns)
    assert tick_label_overlaps(ax, which, renderer).pairs > 0
    assert len(_crowd(fig, which)) == 1


def test_labels_turned_alike_that_crowd_are_reported() -> None:
    fig, ax, renderer = _labelled("x", [45] * 30)
    assert tick_label_overlaps(ax, "x", renderer).pairs > 0
    assert len(_crowd(fig, "x")) == 1


@pytest.mark.parametrize("which", ["x", "y"])
def test_upright_labels_keep_their_size(which: Literal["x", "y"]) -> None:
    fig, ax, renderer = _labelled(which, [0] * 8)
    labels = ax.get_xticklabels() if which == "x" else ax.get_yticklabels()
    boxes = [t.get_window_extent(renderer) for t in labels]
    frame = ax.get_window_extent(renderer)
    size = sum(b.width if which == "x" else b.height for b in boxes)
    span = frame.width if which == "x" else frame.height
    expected = size * 1.15 / span
    found = _crowd(fig, which)
    if expected > 1.0:
        assert found == [pytest.approx(round(expected, 2), abs=1e-9)]
    else:
        assert found == []


def test_review_case_mixed_y_rotations_stay_crowded() -> None:
    """The PR #661 review's case: four crossing pairs on the y axis."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    fig.subplots_adjust(left=0.35)
    ax.plot([0, 1], [0, 7])
    ax.set(ylim=(-0.5, 7.5), xlabel="Response", ylabel="Category")
    ax.set_yticks(range(8))
    ax.set_yticklabels(
        [f"Category name {i:02d}" for i in range(8)],
        ha="right",
        rotation_mode="anchor",
        fontsize=8,
    )
    for i, label in enumerate(ax.get_yticklabels()):
        label.set_rotation(45 if i % 2 else -45)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    assert tick_label_overlaps(ax, "y", renderer).pairs == 4
    assert len(_crowd(fig, "y")) == 1
