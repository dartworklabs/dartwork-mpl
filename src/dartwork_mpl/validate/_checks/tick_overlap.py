"""TICK_OVERLAP: neighbouring tick labels of one axis drawn on top of each other.

Rectilinear Axes only (a polar or 3D axis has no line to take neighbours
along). Every drawn, non-empty tick label is the rectangle its own text
occupies, turned with the label, so two 45 degree labels whose upright
boxes cross while their text does not are not reported. Neighbours are
taken in order along the axis, on each side separately (bottom and top
labels of an x axis, left and right of a y axis). Two labels collide when
they overlap by more than ``_TOUCH_PX`` across the thinner direction of
their overlap (a separating-axis test); labels that only touch pass.

The fixes never make text smaller. What is left for the author is a
horizontal bar chart (many or long category names), a wider or taller
canvas, or fewer categories; labels the author turned get the layout's
choice first (drop the rotation, lay out again).
"""

from __future__ import annotations

import math
from itertools import pairwise
from typing import TYPE_CHECKING, TypedDict

import numpy as np
from matplotlib.text import Text

from ..._figure_geometry import drawn_tick_labels
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import AXES, Axis, choice, number, wire
from ._registry import register_check, register_fix

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_tick_overlap"]

# Overlap (display px) up to which two labels only touch.
_TOUCH_PX = 0.5


class TickOverlapDetail(TypedDict):
    """``pairs`` neighbouring tick labels of one axis overlap, by up to ``px``.

    ``labels`` counts the axis' drawn labels (both sides); ``rotation`` is
    the angle of the deepest overlapping pair, in degrees.
    """

    axis: Axis
    axes_index: int
    pairs: int
    labels: int
    px: float
    rotation: float


def _corners(label: Text, renderer: RendererBase) -> np.ndarray:
    """The 4 corners (display px) of the rectangle the label's text fills.

    An upright or quarter-turned label fills its window extent. A label at
    another angle fills the rectangle of its unturned size, turned about
    the centre of that extent (the centre of a turned rectangle).
    """
    box = label.get_window_extent(renderer)
    upright = np.array(
        [[box.x0, box.y0], [box.x1, box.y0], [box.x1, box.y1], [box.x0, box.y1]]
    )
    angle = float(label.get_rotation())
    figure = label.get_figure(root=True)
    if math.isclose(angle % 90.0, 0.0, abs_tol=1e-6) or figure is None:
        return upright
    flat = Text(0, 0, label.get_text())
    flat.update_from(label)
    flat.set_rotation(0)
    flat.set_figure(figure)
    size = flat.get_window_extent(renderer)
    centre = upright.mean(axis=0)
    turn = math.radians(angle)
    along = np.array([math.cos(turn), math.sin(turn)]) * size.width / 2
    across = np.array([-math.sin(turn), math.cos(turn)]) * size.height / 2
    return np.array(
        [
            centre - along - across,
            centre + along - across,
            centre + along + across,
            centre - along + across,
        ]
    )


def _overlap_px(p: np.ndarray, q: np.ndarray) -> float:
    """How far two rectangles overlap along their edge normals (<= 0: apart).

    The separating-axis test: two convex shapes are apart when their
    projections on some edge normal are; otherwise the smallest projection
    overlap is how deep they cross.
    """
    least = math.inf
    for rect in (p, q):
        for k in (0, 1):  # a rectangle has two edge directions
            edge = rect[k + 1] - rect[k]
            length = float(np.hypot(*edge))
            if length == 0.0:
                continue
            normal = np.array([-edge[1], edge[0]]) / length
            a, b = p @ normal, q @ normal
            least = min(
                least, float(min(a.max(), b.max()) - max(a.min(), b.min()))
            )
    return least


def _axis_overlaps(
    ax: Axes, which: Axis, renderer: RendererBase
) -> tuple[int, int, float, float]:
    """``(pairs, labels, deepest px, its rotation)`` for one axis of ``ax``."""
    axis = ax.xaxis if which == "x" else ax.yaxis
    first_side = {id(tick.label1) for tick in axis.get_major_ticks()}
    labels = [
        label
        for label in drawn_tick_labels(ax, which)
        if label.get_text().strip()
    ]
    coordinate = 0 if which == "x" else 1
    pairs, deepest, rotation = 0, 0.0, 0.0
    for side in (True, False):
        group = [t for t in labels if (id(t) in first_side) is side]
        if len(group) < 2:
            continue
        try:
            anchors = [
                float(t.get_transform().transform(t.get_position())[coordinate])
                for t in group
            ]
            rects = [_corners(t, renderer) for t in group]
        except BBOX_ERRORS:
            continue
        order = sorted(range(len(group)), key=anchors.__getitem__)
        for a, b in pairwise(order):
            depth = _overlap_px(rects[a], rects[b])
            if depth > _TOUCH_PX:
                pairs += 1
                if depth > deepest:
                    deepest = depth
                    rotation = float(group[a].get_rotation())
    return pairs, len(labels), deepest, rotation


@register_check("TICK_OVERLAP", order=51)
def check_tick_overlap(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Report neighbouring tick labels of one axis that overlap."""
    warnings: list[VisualWarning] = []
    for index, ax in enumerate(fig.axes):
        if getattr(ax, "name", None) != "rectilinear":
            continue
        for which in AXES:
            pairs, labels, deepest, rotation = _axis_overlaps(
                ax, which, renderer
            )
            if not pairs:
                continue
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="TICK_OVERLAP",
                    message=(
                        f"{which.upper()}-axis[{index}]: {pairs} pair(s) of "
                        f"neighbouring tick labels overlap (up to "
                        f"{deepest:.1f}px, labels at {rotation:g} deg)"
                    ),
                    detail=wire(
                        TickOverlapDetail(
                            axis=which,
                            axes_index=index,
                            pairs=pairs,
                            labels=labels,
                            px=round(deepest, 1),
                            rotation=round(rotation, 1),
                        )
                    ),
                )
            )
    return warnings


@register_fix("TICK_OVERLAP")
def _fix_tick_overlap(warning: VisualWarning) -> list[str]:
    """The layout's choice first, then the author's; never smaller text."""
    axis = choice(warning.detail, "axis", AXES)
    rotation = number(warning.detail, "rotation", 0)
    if axis == "y":
        return [
            "# More rows than the axis holds: a taller canvas, same width\n"
            "fig.set_size_inches(dm.figsize(width, 'tall'))"
        ]
    out = []
    if rotation:
        out.append(
            "# Let the layout choose: drop your rotation, then lay out again\n"
            "ax.tick_params(axis='x', labelrotation=0)\n"
            "dm.simple_layout(fig)"
        )
    out += [
        "# Many or long category names: horizontal bars\n"
        "fig, ax = plt.subplots(figsize=dm.figsize_for('barh', n_points=n))\n"
        "ax.barh(names, values)",
        "# Or a wider canvas\n"
        "fig.set_size_inches(dm.figsize('17cm', 'standard'))",
    ]
    return out
