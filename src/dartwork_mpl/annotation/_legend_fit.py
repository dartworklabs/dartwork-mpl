"""Data ink of a plot box, as ``annotate_value`` reads it for its labels.

What remains here after ``place_legend`` moved to the ``legend`` slice: the
ink is read as drawn, by the rules of
:mod:`~dartwork_mpl._figure_geometry` that ``LEGEND_ON_DATA`` reads it by:
line paths at their width (``Path.intersects_bbox``), markers and scatter
points as discs reaching half their edge past their size, bars and other
patches by their extents grown by half their edge, filled collections by
their paths and edges, and the Axes' texts (value labels, annotations) with
their background boxes. Only what inks counts (a style, a width, a colour
with alpha), and only where its clip lets it draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from matplotlib.collections import LineCollection, PathCollection, QuadMesh
from matplotlib.contour import ContourSet
from matplotlib.transforms import Bbox

from .._figure_geometry import (
    BBOX_ERRORS,
    UNCLIPPED,
    clip_path_px,
    clip_region,
    discs_meet,
    drawn_collection_outlines,
    drawn_ink_meets,
    drawn_patch_box,
    drawn_scatter_discs,
    drawn_text_box,
    drawn_tick_labels,
    line_draws_markers,
    line_draws_stroke,
    marker_radius_pt,
    same_position_axes,
)

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.path import Path


@dataclass
class Ink:
    """The data ink of one plot box (an Axes and its twins), in display px.

    Each item is keyed by the ``id`` of the artist that drew it, so a
    label's cost counts artists, not segments.
    """

    lines: list[tuple[int, Path, float]] = field(default_factory=list)
    #: A filled path and half the width of the edge drawn on it (0: none).
    filled: list[tuple[int, Path, float]] = field(default_factory=list)
    points: list[tuple[int, np.ndarray, np.ndarray]] = field(
        default_factory=list
    )
    #: Boxes already cut to where their artist's clip lets it draw.
    boxes: list[tuple[int, Bbox]] = field(default_factory=list)
    #: Where a line's or a collection's clip lets it draw (its clip region
    #: and clip path), by the ``id`` of the artist; an artist not here is
    #: drawn wherever its ink lies.
    clips: dict[int, tuple[Bbox, Path | None]] = field(default_factory=dict)

    def clip(self, key: int, artist: Artist) -> None:
        """Record where ``artist``'s clip lets it draw, if anything clips it."""
        region, clip_path = clip_region(artist), clip_path_px(artist)
        if region is not UNCLIPPED or clip_path is not None:
            self.clips[key] = (region, clip_path)

    def met(self, box: Bbox, clearance: float) -> set[int]:
        """The artists whose ink comes within ``clearance`` px of ``box``.

        A clipped artist's ink counts where its clip lets it draw; the clip
        cuts its stroke (or its disc), not its centre line
        (:func:`~dartwork_mpl._figure_geometry.drawn_ink_meets`,
        :func:`~dartwork_mpl._figure_geometry.discs_meet`).
        """
        found: set[int] = set()
        grown = box.padded(clearance)
        for key, bb in self.boxes:
            if _overlaps(grown, bb):
                found.add(key)
        for key, path, half in self.lines:
            if key in found:
                continue
            region, clip_path = self.clips.get(key, (UNCLIPPED, None))
            if drawn_ink_meets(path, half, grown, region, clip_path):
                found.add(key)
        for key, path, half in self.filled:
            if key in found:
                continue
            region, clip_path = self.clips.get(key, (UNCLIPPED, None))
            if drawn_ink_meets(
                path, half, grown, region, clip_path, filled=True
            ):
                found.add(key)
        for key, xy, r in self.points:
            if key in found:
                continue
            region, clip_path = self.clips.get(key, (UNCLIPPED, None))
            if discs_meet(xy, r, grown, region, clip_path):
                found.add(key)
        return found


def _overlaps(a: Bbox, b: Bbox) -> bool:
    return bool(
        min(a.x1, b.x1) > max(a.x0, b.x0) and min(a.y1, b.y1) > max(a.y0, b.y0)
    )


def points_px(renderer: RendererBase, points: float) -> float:
    """``points`` in display px for ``renderer``."""
    return float(np.asarray(renderer.points_to_pixels(points)))


def _finite(xy: np.ndarray) -> np.ndarray:
    xy = np.asarray(xy, dtype=float).reshape(-1, 2)
    kept: np.ndarray = xy[np.isfinite(xy).all(axis=1)]
    return kept


def _measure_line(ink: Ink, line: Any, renderer: RendererBase) -> None:
    """A line's stroke at its width and its markers as discs, where drawn.

    Only what the line inks (a stroke, markers with a face or an edge), and
    the markers reaching half their edge past their size, as
    ``LEGEND_ON_DATA`` reads them; every vertex counts as a marker.
    """
    stroke, markers = line_draws_stroke(line), line_draws_markers(line)
    if not (stroke or markers):
        return
    key = id(line)
    try:
        path = line.get_transform().transform_path(line.get_path())
        ink.clip(key, line)
    except BBOX_ERRORS:
        return
    if stroke:
        ink.lines.append(
            (key, path, points_px(renderer, line.get_linewidth()) / 2)
        )
    if markers:
        xy = _finite(path.vertices)
        r = points_px(renderer, marker_radius_pt(line))
        ink.points.append((key, xy, np.full(len(xy), r)))


def _measure_collection(ink: Ink, coll: Any, renderer: RendererBase) -> None:
    key = id(coll)
    if isinstance(coll, PathCollection) and len(coll.get_sizes()):
        # Scatter points as discs, each by its own size, edge and colours,
        # as LEGEND_ON_DATA reads them (masked and transparent points out).
        try:
            xy, r = drawn_scatter_discs(coll, points_px(renderer, 1.0))
            ink.clip(key, coll)
        except BBOX_ERRORS:
            return
        if len(xy):
            ink.points.append((key, xy, r))
        return
    try:
        # Only the items that draw ink, each where Collection.draw puts it
        # (offsets included) and by its own colours, alpha and width, and
        # only where its clip lets it draw: the rule LEGEND_ON_DATA reads
        # collections by too.
        outlines = drawn_collection_outlines(coll, renderer)
        ink.clip(key, coll)
    except BBOX_ERRORS:
        return
    if not outlines:
        return
    stroked = isinstance(coll, LineCollection) or (
        isinstance(coll, ContourSet) and not coll.filled
    )
    if stroked:
        ink.lines.extend((key, o.path, o.half) for o in outlines)
    else:
        # A filled item with its edge: the stroke reaches half its width
        # past the outline.
        ink.filled.extend((key, o.path, o.half) for o in outlines)


def _measure_box(ink: Ink, artist: Artist, bb: Bbox | None) -> None:
    if bb is not None and bb.width > 0 and bb.height > 0:
        ink.boxes.append((id(artist), bb))


def _measure_frame(ink: Ink, ax: Axes, renderer: RendererBase) -> None:
    """What a non-rectilinear Axes draws in its own box besides data.

    A polar Axes (any projection but the rectilinear one) draws its frame,
    the circle, and its tick labels, the angles round the circle and the
    radii inside it, within the box a legend's inside spots are tried in;
    a rectilinear Axes keeps them on its edges and outside. The spines
    count at their width, each drawn tick label by its box, and only what
    is drawn: matplotlib draws the spines only while the Axes draws its
    frame and its axis (``set_frame_on(False)`` and ``set_axis_off()``
    keep each spine's own flag on), and the tick labels by
    :func:`~dartwork_mpl._figure_geometry.drawn_tick_labels` (turning the
    frame off alone keeps them).
    """
    frame_drawn = bool(getattr(ax, "axison", True) and ax.get_frame_on())
    for spine in ax.spines.values():
        if not frame_drawn or not spine.get_visible():
            continue
        try:
            path = spine.get_transform().transform_path(spine.get_path())
        except BBOX_ERRORS:
            continue
        half = points_px(renderer, spine.get_linewidth()) / 2
        ink.lines.append((id(spine), path, half))
    axes: tuple[Literal["x", "y"], ...] = ("x", "y")
    for which in axes:
        for label in drawn_tick_labels(ax, which):
            if not label.get_text().strip():
                continue
            try:
                _measure_box(ink, label, label.get_window_extent(renderer))
            except BBOX_ERRORS:
                continue


def measure_ink(ax: Axes, renderer: RendererBase) -> Ink:
    """The ink of ``ax`` and every twin drawn in its box.

    Lines (with their markers), patches (their edges included), collections
    other than meshes and the Axes' texts (their background boxes
    included); only what an artist inks counts, where its clip lets it
    draw. A non-rectilinear Axes (polar) adds its frame and tick labels,
    which it draws inside its box (:func:`_measure_frame`).
    """
    ink = Ink()
    if ax.name != "rectilinear":
        _measure_frame(ink, ax, renderer)
    for owner in same_position_axes(ax):
        for line in owner.get_lines():
            _measure_line(ink, line, renderer)
        for patch in owner.patches:
            try:
                _measure_box(ink, patch, drawn_patch_box(patch, renderer))
            except BBOX_ERRORS:
                continue
        for coll in owner.collections:
            if coll.get_visible() and not isinstance(coll, QuadMesh):
                _measure_collection(ink, coll, renderer)
        for text in owner.texts:
            try:
                _measure_box(ink, text, drawn_text_box(text, renderer))
            except BBOX_ERRORS:
                continue
    return ink


__all__ = ["Ink", "measure_ink", "points_px"]
