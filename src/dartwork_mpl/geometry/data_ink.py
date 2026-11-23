"""A plot's data ink: what its artists draw, gathered by the rules of
:mod:`.ink`, each piece under its caller's key.

``dm.place_legend`` and ``dm.check`` both ask "which artists' ink does
this box meet"; they pick which artists count and how a hit is named, and
this records and answers the same way for both.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, TypeVar

import numpy as np
from matplotlib.collections import PathCollection, PolyCollection

from .ink import (
    artist_shown,
    clip_path_px,
    clip_region,
    discs_meet,
    drawn_collection_outlines,
    drawn_ink_meets,
    drawn_patch_box,
    drawn_scatter_discs,
    line_draws_markers,
    line_draws_stroke,
    marker_radius_pt,
)
from .renderer import BBOX_ERRORS

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.collections import Collection
    from matplotlib.lines import Line2D
    from matplotlib.path import Path
    from matplotlib.transforms import Bbox

K = TypeVar("K")


def _overlaps(a: Bbox, b: Bbox) -> bool:
    """The boxes share some area."""
    return min(a.x1, b.x1) > max(a.x0, b.x0) and min(a.y1, b.y1) > max(
        a.y0, b.y0
    )


#: Points to display px for the figure being measured.
ToPx = Callable[[float], float]


#: How much of a one-line text box its digits and capitals fill, top to
#: bottom (cap height over line height, 0.7 for the bundled faces).
LINE_INK = 0.7


@dataclass
class DataInk(Generic[K]):
    """The data ink of one plot, each piece under the key it was added with:
    boxes (bars, patches, texts), paths stroked at a half width (filled
    when ``True``) and discs (markers, scatter points), each with where its
    clip lets it draw. Which artists count is the caller's choice."""

    boxes: list[tuple[K, Bbox]] = field(default_factory=list)
    strokes: list[tuple[K, Path, float, bool, Bbox, Path | None]] = field(
        default_factory=list
    )
    discs: list[tuple[K, np.ndarray, np.ndarray, Bbox, Path | None]] = field(
        default_factory=list
    )

    def add_box(self, key: K, box: Bbox | None) -> None:
        """A box of ink (none for an empty one)."""
        if box is not None and box.width > 0 and box.height > 0:
            self.boxes.append((key, box))

    def add_line(self, line: Line2D, to_px: ToPx, stroke: K, marker: K) -> None:
        """A line's stroke at its width and every vertex as a marker disc
        (a dashed line counts as solid)."""
        stroked, marks = line_draws_stroke(line), line_draws_markers(line)
        if not (stroked or marks):
            return
        try:
            path = line.get_transform().transform_path(line.get_path())
            region, clip = clip_region(line), clip_path_px(line)
        except BBOX_ERRORS:
            return
        if stroked:
            half = to_px(line.get_linewidth()) / 2
            self.strokes.append((stroke, path, half, False, region, clip))
        if marks:
            xy = np.asarray(path.vertices, dtype=float).reshape(-1, 2)
            xy = xy[np.isfinite(xy).all(axis=1)]
            r = np.full(len(xy), to_px(marker_radius_pt(line)))
            self.discs.append((marker, xy, r, region, clip))

    def add_collection(
        self,
        coll: Collection,
        renderer: RendererBase,
        to_px: ToPx,
        key: K,
        *,
        filled: bool,
    ) -> None:
        """Scatter points as discs; any other collection by its outlines."""
        try:
            region, clip = clip_region(coll), clip_path_px(coll)
            if isinstance(coll, PathCollection) and len(coll.get_sizes()):
                xy, r = drawn_scatter_discs(coll, to_px(1.0))
                if len(xy):
                    self.discs.append((key, xy, r, region, clip))
                return
            for o in drawn_collection_outlines(coll, renderer):
                self.strokes.append((key, o.path, o.half, filled, region, clip))
        except BBOX_ERRORS:
            return

    def meets(self, box: Bbox, shrink: float = 0.0) -> list[K]:
        """The keys whose ink lies in ``box``, each once in the order added;
        discs count ``shrink`` px smaller."""
        found = [k for k, b in self.boxes if _overlaps(box, b)]
        for key, path, half, filled, region, clip in self.strokes:
            if drawn_ink_meets(path, half, box, region, clip, filled=filled):
                found.append(key)
        for key, xy, r, region, clip in self.discs:
            if discs_meet(xy, np.maximum(r - shrink, 0.0), box, region, clip):
                found.append(key)
        return list(dict.fromkeys(found))

    def holds(self, box: Bbox, off: float) -> bool:
        """Whether one disc holds the text in ``box``: the box's middle
        within ``off`` px of the disc's, and the corners of its ink inside
        the disc. The ink of digits and capitals is about
        :data:`LINE_INK` of the line box a text measures as."""
        cx, cy = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
        reach = float(np.hypot(box.width, LINE_INK * box.height)) / 2
        for _key, xy, r, _region, _clip in self.discs:
            away = np.hypot(xy[:, 0] - cx, xy[:, 1] - cy)
            if bool(np.any((away <= off) & (away + reach <= r))):
                return True
        return False


def in_data_coords(artist: Artist, ax: Axes) -> bool:
    """Drawn in data coordinates on both axes (``axhline`` is a reference)."""
    try:
        both = artist.get_transform().contains_branch_seperately(ax.transData)
    except BBOX_ERRORS:
        return False
    return bool(all(both))


def marks_ink(
    axes: Iterable[Axes], renderer: RendererBase, px_per_pt: float
) -> DataInk[object]:
    """Every mark the Axes draw in data coordinates, keyed by its artist
    (an ``axvline`` runs past every row, so it is beside none of them)."""
    drawn: DataInk[object] = DataInk()

    def to_px(points: float) -> float:
        return points * px_per_pt

    for ax in axes:
        for line in ax.lines:
            if artist_shown(line) and in_data_coords(line, ax):
                drawn.add_line(line, to_px, line, line)
        for coll in ax.collections:
            if artist_shown(coll):
                filled = isinstance(coll, PolyCollection)
                drawn.add_collection(coll, renderer, to_px, coll, filled=filled)
        for patch in ax.patches:
            if artist_shown(patch):
                with suppress(*BBOX_ERRORS):
                    drawn.add_box(patch, drawn_patch_box(patch, renderer))
        for image in ax.images:
            if artist_shown(image):
                drawn.add_box(image, image.get_window_extent(renderer))
    return drawn
