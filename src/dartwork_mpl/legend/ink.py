"""What an Axes draws as data, for a legend to keep clear of.

An :class:`Ink` holds the boxes, lines, discs and clip regions of what
each artist actually draws, in display pixels, and answers whether a box
meets it.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.collections import (
    Collection,
    LineCollection,
    PathCollection,
    QuadMesh,
)
from matplotlib.contour import ContourSet
from matplotlib.transforms import Bbox, BboxBase

from ..geometry import (
    BBOX_ERRORS,
    UNCLIPPED,
    clip_path_px,
    clip_region,
    cut_to_clip,
    discs_meet,
    drawn_collection_outlines,
    drawn_in_tree,
    drawn_ink_meets,
    drawn_patch_box,
    drawn_scatter_discs,
    line_draws_markers,
    line_draws_stroke,
    marker_radius_pt,
    same_position_axes,
    text_inks,
)
from .boxes import Box, Hits
from .model import CLEARANCE_PT

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.lines import Line2D
    from matplotlib.path import Path
    from matplotlib.text import Text


@dataclass
class Ink:
    """Data ink of one plot box, keyed by the artist that drew it."""

    clearance: float
    boxes: list[tuple[int, Bbox]] = field(default_factory=list)
    strokes: list[tuple[int, Path, float, bool]] = field(default_factory=list)
    discs: list[tuple[int, np.ndarray, np.ndarray]] = field(
        default_factory=list
    )
    clips: dict[int, tuple[Bbox, Path | None]] = field(default_factory=dict)

    def clip(self, artist: Artist) -> None:
        """Record where ``artist``'s clip lets it draw, if anything clips it."""
        region, path = clip_region(artist), clip_path_px(artist)
        if region is not UNCLIPPED or path is not None:
            self.clips[id(artist)] = (region, path)

    def meets(self, box: Box) -> Hits:
        """The artists whose ink comes within the clearance of ``box``."""
        g = box.padded(self.clearance)
        grown = Bbox.from_extents(g.x0, g.y0, g.x1, g.y1)
        found = {k for k, bb in self.boxes if box_of(bb).overlaps(g)}
        for key, path, half, filled in self.strokes:
            region, cp = self.clips.get(key, (UNCLIPPED, None))
            if key not in found and drawn_ink_meets(
                path, half, grown, region, cp, filled=filled
            ):
                found.add(key)
        for key, xy, r in self.discs:
            region, cp = self.clips.get(key, (UNCLIPPED, None))
            if key not in found and discs_meet(xy, r, grown, region, cp):
                found.add(key)
        return Hits(len(found))


def _add_box(ink: Ink, artist: Artist, bb: Bbox | None) -> None:
    if bb is not None and bb.width > 0 and bb.height > 0:
        ink.boxes.append((id(artist), bb))


def _add_line(ink: Ink, line: Line2D, renderer: RendererBase) -> None:
    stroke, markers = line_draws_stroke(line), line_draws_markers(line)
    if not (stroke or markers):
        return
    try:
        path = line.get_transform().transform_path(line.get_path())
        ink.clip(line)
    except BBOX_ERRORS:
        return
    if stroke:
        half = px(renderer, line.get_linewidth()) / 2
        ink.strokes.append((id(line), path, half, False))
    if markers:
        xy = np.asarray(path.vertices, dtype=float).reshape(-1, 2)
        xy = xy[np.isfinite(xy).all(axis=1)]
        r = px(renderer, marker_radius_pt(line))
        ink.discs.append((id(line), xy, np.full(len(xy), r)))


def _add_collection(ink: Ink, coll: Collection, renderer: RendererBase) -> None:
    try:
        if isinstance(coll, PathCollection) and len(coll.get_sizes()):
            xy, r = drawn_scatter_discs(coll, px(renderer, 1.0))
            if len(xy):
                ink.discs.append((id(coll), xy, r))
        else:
            stroked = isinstance(coll, LineCollection) or (
                isinstance(coll, ContourSet) and not coll.filled
            )
            for o in drawn_collection_outlines(coll, renderer):
                ink.strokes.append((id(coll), o.path, o.half, not stroked))
        ink.clip(coll)
    except BBOX_ERRORS:
        return


def _drawn_text_box(text: Text, renderer: RendererBase) -> Bbox | None:
    """Where an Axes text draws ink, display px; ``None`` when nowhere.

    A shown, non-blank text draws its glyphs (its window extent, an
    annotation's arrow included) where they ink (:func:`text_inks`) and its
    background box (``bbox=``) where that inks (:func:`drawn_patch_box`,
    its edge included): the two are apart, so glyphs at alpha 0 over an
    opaque box still draw the box. What draws is joined and cut to the
    text's clip: matplotlib clips the background box with the text.
    """
    if not drawn_in_tree(text) or not text.get_text().strip():
        return None
    parts: list[Bbox] = []
    if text_inks(text):
        parts.append(text.get_window_extent(renderer))
    background = text.get_bbox_patch()
    if background is not None:  # placed where the text was last drawn
        drawn = drawn_patch_box(background, renderer)
        if drawn is not None:
            parts.append(drawn)
    if not parts:
        return None
    return cut_to_clip(Bbox.union(parts), text)


def data_ink(ax: Axes, renderer: RendererBase) -> Ink:
    """Lines, patches, collections (not meshes) and texts of ``ax`` and twins."""
    ink = Ink(px(renderer, CLEARANCE_PT))
    for owner in same_position_axes(ax):
        for line in owner.get_lines():
            _add_line(ink, line, renderer)
        for coll in owner.collections:
            if coll.get_visible() and not isinstance(coll, QuadMesh):
                _add_collection(ink, coll, renderer)
        for patch in owner.patches:
            with suppress(*BBOX_ERRORS):
                _add_box(ink, patch, drawn_patch_box(patch, renderer))
        for text in owner.texts:
            with suppress(*BBOX_ERRORS):
                _add_box(ink, text, _drawn_text_box(text, renderer))
    return ink


def box_of(bb: BboxBase) -> Box:
    """A matplotlib ``Bbox`` as a :class:`Box`."""
    return Box(float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1))


def px(renderer: RendererBase, points: float) -> float:
    """``points`` in display px for ``renderer``."""
    return float(np.asarray(renderer.points_to_pixels(points)))
