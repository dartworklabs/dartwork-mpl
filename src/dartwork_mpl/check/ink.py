"""Where a plot's data ink is drawn, to find what a legend covers.

Read by the drawn rules the legend slice also uses (``geometry.ink``):
lines at their width, markers and scatter points as discs, bars by their
drawn boxes, filled areas by their outlines, each only where its clip lets
it draw. A dashed line counts as solid and every vertex of a marked line as
a marker: both can only add a cover.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

import numpy as np
from matplotlib.collections import (
    Collection,
    LineCollection,
    PathCollection,
    PolyCollection,
)
from matplotlib.container import BarContainer
from matplotlib.text import Text as MplText
from matplotlib.transforms import Bbox

from ..geometry import (
    BBOX_ERRORS,
    UNCLIPPED,
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
    patch_inks,
    text_inks,
    within_clip_path,
)
from .model import Hit

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.legend import Legend as MplLegend
    from matplotlib.lines import Line2D
    from matplotlib.path import Path


class Named(Protocol):
    """An artist or container: it has a legend label."""

    def get_label(self) -> object:
        """The legend label."""
        ...


def name_of(artist: Named, unnamed: str = "") -> str:
    """The artist's legend label, ``unnamed`` for a ``_``-label."""
    label = str(artist.get_label() or "")
    return unnamed if not label or label.startswith("_") else label


def in_data_coords(artist: Artist, ax: Axes) -> bool:
    """Drawn in data coordinates on both axes (``axhline`` is a reference)."""
    try:
        both = artist.get_transform().contains_branch_seperately(ax.transData)
    except BBOX_ERRORS:
        return False
    return bool(all(both))


def cut(box: Bbox, frame: Bbox) -> Bbox | None:
    """``box`` cut to ``frame``; ``None`` when nothing is left."""
    x0, y0 = max(box.x0, frame.x0), max(box.y0, frame.y0)
    x1, y1 = min(box.x1, frame.x1), min(box.y1, frame.y1)
    return Bbox.from_extents(x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


@dataclass
class Ink:
    """The data ink of one plot box (an Axes and its twins), by artist."""

    frame: Bbox
    bars: list[tuple[Hit, Bbox]] = field(default_factory=list)
    strokes: list[tuple[Hit, Path, float, Bbox, Path | None]] = field(
        default_factory=list
    )
    discs: list[tuple[Hit, np.ndarray, np.ndarray, Bbox, Path | None]] = field(
        default_factory=list
    )

    def meets(self, box: Bbox, touch: float) -> list[Hit]:
        """What ``box`` covers by more than ``touch`` inside the plot box."""
        inner = cut(box.padded(-touch), self.frame)
        if inner is None:
            return []
        found = [hit for hit, bar in self.bars if cut(inner, bar) is not None]
        for hit, path, half, region, clip in self.strokes:
            if drawn_ink_meets(path, half, inner, region, clip):
                found.append(hit)
        for hit, xy, r, region, clip in self.discs:
            if discs_meet(xy, np.maximum(r - touch, 0.0), inner, region, clip):
                found.append(hit)
        return list(dict.fromkeys(found))


def _line(ink: Ink, line: Line2D, px_per_pt: float) -> None:
    stroke, marks = line_draws_stroke(line), line_draws_markers(line)
    if not (stroke or marks):
        return
    path = line.get_transform().transform_path(line.get_path())
    region, clip = clip_region(line), clip_path_px(line)
    hit = Hit("line", name_of(line))
    if stroke:
        half = line.get_linewidth() * px_per_pt / 2
        ink.strokes.append((hit, path, half, region, clip))
    if marks:
        xy = np.asarray(path.vertices, dtype=float).reshape(-1, 2)
        xy = xy[np.isfinite(xy).all(axis=1)]
        r = np.full(len(xy), marker_radius_pt(line) * px_per_pt)
        ink.discs.append((Hit("marker", name_of(line)), xy, r, region, clip))


def _collection(
    ink: Ink, coll: Collection, renderer: RendererBase, px_per_pt: float
) -> None:
    region, clip = clip_region(coll), clip_path_px(coll)
    if isinstance(coll, PathCollection) and len(coll.get_sizes()):
        xy, r = drawn_scatter_discs(coll, px_per_pt)
        if len(xy):
            ink.discs.append(
                (Hit("marker", name_of(coll)), xy, r, region, clip)
            )
    elif isinstance(coll, PolyCollection):
        hit = Hit("area", name_of(coll, "filled area"))
        for o in drawn_collection_outlines(coll, renderer):
            ink.strokes.append((hit, o.path, o.half, region, clip))
    elif isinstance(coll, LineCollection):
        hit = Hit("line", name_of(coll))
        for o in drawn_collection_outlines(coll, renderer):
            ink.strokes.append((hit, o.path, o.half, region, clip))


def data_ink(
    owners: list[Axes], frame: Bbox, renderer: RendererBase, px_per_pt: float
) -> Ink:
    """Bars, data lines, markers, scatter points, filled areas and data line
    collections of one plot box."""
    ink = Ink(frame)
    for ax in owners:
        for line in ax.get_lines():
            if line.get_visible() and in_data_coords(line, ax):
                with suppress(*BBOX_ERRORS):
                    _line(ink, line, px_per_pt)
        for coll in ax.collections:
            if (coll.get_visible() and in_data_coords(coll, ax)) or (
                isinstance(coll, PathCollection) and coll.get_visible()
            ):
                with suppress(*BBOX_ERRORS):
                    _collection(ink, coll, renderer, px_per_pt)
        for container in ax.containers:
            if not isinstance(container, BarContainer):
                continue
            for patch in container.patches:
                with suppress(*BBOX_ERRORS):
                    box = drawn_patch_box(patch, renderer)
                    if box is not None and box.width > 0 and box.height > 0:
                        ink.bars.append((Hit("bar", name_of(container)), box))
    return ink


def words_box(text: MplText, renderer: RendererBase) -> Bbox | None:
    """Where a text's words draw (not an annotation's arrow), cut to its clip."""
    box = MplText.get_window_extent(text, renderer)
    if not np.isfinite(box.extents).all() or box.width <= 0 or box.height <= 0:
        return None
    region = clip_region(text)
    seen = box if region is UNCLIPPED else cut(box, region)
    return within_clip_path(seen, clip_path_px(text))


def legend_inks(leg: MplLegend) -> bool:
    """A legend that draws a frame, a title or an entry text."""
    if leg.get_frame_on() and patch_inks(leg.get_frame()):
        return True
    return any(text_inks(t) for t in (leg.get_title(), *leg.get_texts()))
