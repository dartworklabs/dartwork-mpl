"""Measurement shared by the placement helpers: the renderer, bbox areas and the obstacles of an Axes."""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from .._figure_geometry import BBOX_ERRORS, get_renderer

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import SubFigure


def _renderer_for_axes(ax: Axes) -> tuple[Figure | SubFigure, RendererBase]:
    fig = ax.get_figure()
    if fig is None or fig.canvas is None:
        raise ValueError("Axes must be part of a Figure with a canvas")
    fig.canvas.draw()
    return fig, get_renderer(fig)


def _padded_bbox(
    x0: float, y0: float, x1: float, y1: float, pad: float
) -> Bbox:
    return Bbox.from_extents(x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def _overlap_area(a: Bbox, b: Bbox) -> float:
    width = min(a.x1, b.x1) - max(a.x0, b.x0)
    height = min(a.y1, b.y1) - max(a.y0, b.y0)
    if width <= 0 or height <= 0:
        return 0.0
    return float(width * height)


def _intersection_area(a: Bbox, b: Bbox) -> float:
    return _overlap_area(a, b)


def _outside_area(inner: Bbox, outer: Bbox) -> float:
    area = max(float(inner.width * inner.height), 0.0)
    return area - _intersection_area(inner, outer)


def _collision_area(bbox: Bbox, obstacles: list[Bbox]) -> float:
    return sum(_overlap_area(bbox, obstacle) for obstacle in obstacles)


def _line_segment_bboxes(ax: Axes, pad_px: float = 2.0) -> list[Bbox]:
    bboxes: list[Bbox] = []
    for line in ax.lines:
        if not line.get_visible():
            continue
        xy = np.asarray(line.get_xydata(), dtype=float)
        if len(xy) < 2:
            continue
        points = line.get_transform().transform(xy)
        points = points[np.isfinite(points).all(axis=1)]
        if len(points) < 2:
            continue
        for left, right in pairwise(points):
            bboxes.append(
                _padded_bbox(
                    float(min(left[0], right[0])),
                    float(min(left[1], right[1])),
                    float(max(left[0], right[0])),
                    float(max(left[1], right[1])),
                    pad_px,
                )
            )
    return bboxes


def _patch_bboxes(ax: Axes) -> list[Bbox]:
    bboxes: list[Bbox] = []
    for patch in ax.patches:
        if not patch.get_visible():
            continue
        try:
            bbox = (
                patch.get_path()
                .transformed(patch.get_transform())
                .get_extents()
            )
        except (RuntimeError, ValueError, AttributeError):
            continue
        if bbox.width > 0 and bbox.height > 0:
            bboxes.append(bbox)
    return bboxes


def _collection_bboxes(ax: Axes, pad_px: float = 6.0) -> list[Bbox]:
    bboxes: list[Bbox] = []
    for collection in ax.collections:
        if not collection.get_visible():
            continue
        try:
            offsets = collection.get_offsets()
            points = collection.get_offset_transform().transform(offsets)
        except (RuntimeError, ValueError, AttributeError):
            continue
        if len(points) == 0:
            continue
        points = points[np.isfinite(points).all(axis=1)]
        for x, y in points:
            bboxes.append(
                _padded_bbox(float(x), float(y), float(x), float(y), pad_px)
            )
    return bboxes


def _text_bboxes(texts: list[Text], renderer: Any) -> list[Bbox]:
    bboxes: list[Bbox] = []
    for text in texts:
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            bbox = text.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if bbox.width > 0 and bbox.height > 0:
            bboxes.append(bbox)
    return bboxes
