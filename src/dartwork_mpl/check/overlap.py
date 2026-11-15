"""Tick labels as the rectangles their text fills, turned with it, and where they cross.

Read by the tick rules: neighbours along one axis (``TICK_OVERLAP``), how
far apart they must sit, and an x and a y label meeting at a plot corner.
"""

from __future__ import annotations

import math
from itertools import pairwise
from typing import TYPE_CHECKING, Literal, NamedTuple

import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.text import Text

from ..geometry import BBOX_ERRORS, drawn_tick_labels

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase

# Overlap (display px) up to which two tick labels only touch.
_TOUCH_PX = 0.5


class TickOverlaps(NamedTuple):
    """Neighbouring tick labels of one axis that overlap.

    ``pairs`` overlapping neighbours, ``labels`` drawn labels (both sides,
    major and minor), ``deepest`` the deepest overlap (px) and ``rotation``
    that pair's angle in degrees.
    """

    pairs: int
    labels: int
    deepest: float
    rotation: float


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


def _half_reach(corners: np.ndarray, normal: np.ndarray) -> float:
    """Half the extent of a rectangle (its 4 corners) along a unit ``normal``."""
    return 0.5 * (
        abs(float((corners[1] - corners[0]) @ normal))
        + abs(float((corners[3] - corners[0]) @ normal))
    )


def pair_clearance_px(
    a: Text, b: Text, renderer: RendererBase, which: Literal["x", "y"]
) -> float:
    """How far apart along the x or y axis the centres of ``a`` and ``b`` must be.

    Each label fills its own rectangle (:func:`_label_corners`, turned with
    it, at its own angle). Moved along the axis, the two are apart once,
    along one edge direction of either rectangle, the distance covers both
    half-extents (the separating-axis test of :func:`_overlap_px`): the
    least, over the four edge directions, of the two half-extents over the
    axis' share of that direction. Upright neighbours need half their two
    widths along x (heights along y); two labels turned alike need their
    heights over the sine of the slant; two turned opposite ways, crossing
    where they meet, need far more.
    """
    rect_a, rect_b = _label_corners(a, renderer), _label_corners(b, renderer)
    direction = np.array([1.0, 0.0] if which == "x" else [0.0, 1.0])
    reach = math.inf
    for rect in (rect_a, rect_b):
        for edge in (rect[1] - rect[0], rect[3] - rect[0]):
            length = float(np.hypot(*edge))
            if length == 0.0:
                continue
            normal = edge / length
            along = abs(float(direction @ normal))
            if along > 1e-9:
                need = _half_reach(rect_a, normal) + _half_reach(rect_b, normal)
                reach = min(reach, need / along)
    return reach


def label_clearance_px(
    label: Text, renderer: RendererBase, which: Literal["x", "y"]
) -> float:
    """How far along the x or y axis a copy of ``label`` must move to clear it.

    :func:`pair_clearance_px` of the label with itself: its width over the
    cosine of its slant against the axis, or its height over the sine,
    whichever is shorter. An upright label needs its width along x and its
    height along y; one turned 45 degrees its height times the square root
    of two, however long its text.
    """
    return pair_clearance_px(label, label, renderer, which)


def pair_gap_px(a: Text, b: Text, renderer: RendererBase) -> float:
    """The room (display px) between the rectangles ``a`` and ``b`` fill.

    Each at its own angle (:func:`_label_corners`): the widest gap their
    projections leave on an edge normal of either (the separating-axis
    test of :func:`_overlap_px`); negative, how deep they cross. Upright
    neighbours on one baseline get the gap between their edges, two turned
    alike the gap across their slant. It is never more than the distance
    between them, so two labels it puts ``d`` apart are at least ``d``
    apart.
    """
    return -_overlap_px(
        _label_corners(a, renderer), _label_corners(b, renderer)
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
    ax: Axes, which: Literal["x", "y"], renderer: RendererBase
) -> TickOverlaps:
    """Neighbouring drawn tick labels of one axis of ``ax`` that overlap.

    Every drawn, non-empty label, major or minor, is the rectangle its own
    text fills, turned with it; neighbours are taken in order along the
    axis on each side separately (bottom / top, left / right), and collide
    when they overlap by more than ``_TOUCH_PX``. The measure of
    ``TICK_OVERLAP``.
    """
    axis = ax.xaxis if which == "x" else ax.yaxis
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
            rects = [_label_corners(t, renderer) for t in group]
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
    return TickOverlaps(pairs, len(labels), deepest, rotation)


class CornerOverlap(NamedTuple):
    """An x and a y tick label of one plot box that overlap.

    ``depth`` is how deep they cross (px, separating axes, the measure of
    :func:`tick_label_overlaps`); ``down`` and ``across`` how far their boxes
    overlap vertically and horizontally (px): what the x labels must move
    out (down below, up above) or the y labels out (left, right) to clear
    the pair. ``corner``: ``"lower left"``, ``"lower right"``, ``"upper
    left"`` or ``"upper right"``, the sides of the plot the pair sits at.
    ``x_minor`` / ``y_minor``: whether that label is a minor tick's, whose
    pad (``tick_params(which="minor")``) is its own. ``x_axes`` / ``y_axes``
    own the labels: of a ``twinx`` pair, the right labels are the twin's.
    """

    x_label: Text
    y_label: Text
    x_axes: Axes
    y_axes: Axes
    depth: float
    down: float
    across: float
    corner: str
    x_minor: bool = False
    y_minor: bool = False


def _ink_alpha(text: Text) -> float:
    """The alpha ``text`` draws its glyphs with: the artist's alpha when it
    has one (matplotlib's GraphicsContext then forces it over the colour's),
    else its colour's. At 0 the text draws nothing."""
    alpha = text.get_alpha()
    if alpha is not None:
        return float(alpha)
    return float(to_rgba(text.get_color())[3])


def corner_tick_overlaps(
    axes: Sequence[Axes], renderer: RendererBase
) -> list[CornerOverlap]:
    """The x tick labels that overlap a y tick label, among ``axes``.

    ``axes`` are drawn in one box (an Axes and its ``twinx`` / ``twiny``,
    :func:`same_position_axes`): a bottom label at the left end of the
    plot meets the lowest left label when both axes end on a tick
    (``-3`` and ``-3`` of a -3..3 square), or when the first category name
    is wide enough to reach under the y labels; the other corners alike,
    with labels on top or on the right, and the right labels of a twin.
    Every drawn, non-empty label counts, major and minor, as the rectangle
    its own text fills, turned with it, but for one drawn at alpha 0
    (:func:`_ink_alpha`), which leaves no ink; a pair collides when it
    overlaps by more than ``_TOUCH_PX``. Neither ``TICK_OVERLAP``
    (neighbours along one axis) nor ``CROSS_AXES_OVERLAP`` (other plots)
    sees these pairs.
    """
    # (owner Axes, label, minor) of every drawn label, per axis
    xs: list[tuple[Axes, Text, bool]] = []
    ys: list[tuple[Axes, Text, bool]] = []
    sides: tuple[
        tuple[Literal["x", "y"], list[tuple[Axes, Text, bool]]], ...
    ] = (("x", xs), ("y", ys))
    for ax in axes:
        for which, out in sides:
            out += [
                (ax, label, minor)
                for minor in (False, True)
                for label in drawn_tick_labels(ax, which, minor=minor)
                if label.get_text().strip() and _ink_alpha(label) > 0
            ]
    found: list[CornerOverlap] = []
    if not xs or not ys:
        return found
    try:
        plot = axes[0].get_window_extent(renderer)
        x_rects = [_label_corners(t, renderer) for _, t, _ in xs]
        y_rects = [_label_corners(t, renderer) for _, t, _ in ys]
    except BBOX_ERRORS:
        return found
    middle = ((plot.x0 + plot.x1) / 2, (plot.y0 + plot.y1) / 2)
    for (x_ax, x_label, x_minor), x_rect in zip(xs, x_rects, strict=True):
        for (y_ax, y_label, y_minor), y_rect in zip(ys, y_rects, strict=True):
            depth = _overlap_px(x_rect, y_rect)
            if depth <= _TOUCH_PX:
                continue
            down = min(x_rect[:, 1].max(), y_rect[:, 1].max()) - max(
                x_rect[:, 1].min(), y_rect[:, 1].min()
            )
            across = min(x_rect[:, 0].max(), y_rect[:, 0].max()) - max(
                x_rect[:, 0].min(), y_rect[:, 0].min()
            )
            level = "lower" if x_rect[:, 1].mean() < middle[1] else "upper"
            side = "left" if y_rect[:, 0].mean() < middle[0] else "right"
            found.append(
                CornerOverlap(
                    x_label,
                    y_label,
                    x_ax,
                    y_ax,
                    float(depth),
                    float(down),
                    float(across),
                    f"{level} {side}",
                    x_minor,
                    y_minor,
                )
            )
    return found
