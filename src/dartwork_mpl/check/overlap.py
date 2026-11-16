"""Tick labels as the rectangles their text fills, turned with it, and where
neighbours along one axis cross (``TICK_OVERLAP``)."""

from __future__ import annotations

import math
from itertools import pairwise
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.text import Text

from ..geometry import BBOX_ERRORS, drawn_tick_labels
from ..vocab import Which

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase

# Overlap (display px) up to which two tick labels only touch.
_TOUCH_PX = 0.5


def _label_corners(label: Text, renderer: RendererBase) -> np.ndarray:
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


def tick_label_overlaps(
    ax: Axes, which: Which, renderer: RendererBase
) -> tuple[int, float]:
    """Neighbouring drawn tick labels of one axis of ``ax`` that overlap.

    How many pairs collide and the deepest overlap (px). Every drawn,
    non-empty label, major or minor, is the rectangle its own text fills,
    turned with it; neighbours are taken in order along the axis on each
    side separately (bottom / top, left / right), and collide when they
    overlap by more than ``_TOUCH_PX``.
    """
    axis = which.pick(ax.xaxis, ax.yaxis)
    # Major and minor labels share the line: a minor label can run into a
    # major one as easily as into another minor one.
    drawn = [
        *drawn_tick_labels(ax, which),
        *drawn_tick_labels(ax, which, minor=True),
    ]
    first_side = {
        id(tick.label1)
        for tick in (*axis.get_major_ticks(), *axis.get_minor_ticks())
    }
    labels = [label for label in drawn if label.get_text().strip()]
    coordinate = which.pick(0, 1)
    pairs, deepest = 0, 0.0
    for side in (True, False):
        group = [t for t in labels if (id(t) in first_side) is side]
        if len(group) < 2:
            continue
        try:
            anchors = [
                float(t.get_transform().transform(t.get_position())[coordinate])
                for t in group
            ]
            rects = [_label_corners(t, renderer) for t in group]
        except BBOX_ERRORS:
            continue
        order = sorted(range(len(group)), key=anchors.__getitem__)
        for a, b in pairwise(order):
            depth = _overlap_px(rects[a], rects[b])
            if depth > _TOUCH_PX:
                pairs += 1
                deepest = max(deepest, depth)
    return pairs, deepest
