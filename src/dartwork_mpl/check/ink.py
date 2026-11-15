"""Where ink is drawn: a plot's data, under a legend or a value label, and a
text's glyphs against the paper under them.

Read by the drawn rules the legend slice also uses (``geometry.ink``):
lines at their width, markers and scatter points as discs, bars by their
drawn boxes, filled areas by their outlines, each only where its clip lets
it draw. A dashed line counts as solid and every vertex of a marked line as
a marker: both can only add a cover.
"""

from __future__ import annotations

import math
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

import matplotlib.colors as mcolors
import numpy as np
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.collections import (
    Collection,
    LineCollection,
    PathCollection,
    PolyCollection,
)
from matplotlib.container import BarContainer
from matplotlib.contour import ContourSet
from matplotlib.text import Text as MplText
from matplotlib.transforms import Bbox

from ..colorspace import Rgb, contrast
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
from .model import Contrast, Hit, Text, lies_across

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
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
    bars: list[tuple[Hit, Bbox, bool]] = field(default_factory=list)
    strokes: list[tuple[Hit, Path, float, Bbox, Path | None]] = field(
        default_factory=list
    )
    discs: list[tuple[Hit, np.ndarray, np.ndarray, Bbox, Path | None]] = field(
        default_factory=list
    )

    def meets(
        self, box: Bbox, touch: float, label: Bbox | None = None
    ) -> list[Hit]:
        """What ``box`` covers by more than ``touch`` inside the plot box.

        With ``label`` (a value label's own box), the bar it sits on and the
        marker it sits inside are its own and do not count.
        """
        inner = cut(box.padded(-touch), self.frame)
        if inner is None:
            return []
        found: list[Hit] = []
        cx, cy = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
        for hit, bar, horizontal in self.bars:
            if cut(inner, bar) is None:
                continue
            if label is not None and (
                (
                    bar.y0 <= cy <= bar.y1
                    and bar.x0 - touch <= box.x0
                    and box.x1 <= bar.x1 + touch
                )
                if horizontal
                else (
                    bar.x0 <= cx <= bar.x1
                    and bar.y0 - touch <= box.y0
                    and box.y1 <= bar.y1 + touch
                )
            ):
                continue  # a label on its own bar
            found.append(hit)
        for hit, path, half, region, clip in self.strokes:
            if drawn_ink_meets(path, half, inner, region, clip):
                found.append(hit)
        for hit, xy, r, region, clip in self.discs:
            if label is not None:
                bubble = (xy[:, 0] - cx) ** 2 + (xy[:, 1] - cy) ** 2 <= r**2
                bubble &= r >= max(box.width, box.height) / 2
                xy, r = xy[~bubble], r[~bubble]
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
    ink: Ink,
    coll: Collection,
    renderer: RendererBase,
    px_per_pt: float,
    areas: bool,
) -> None:
    region, clip = clip_region(coll), clip_path_px(coll)
    if isinstance(coll, PathCollection) and len(coll.get_sizes()):
        xy, r = drawn_scatter_discs(coll, px_per_pt)
        if len(xy):
            ink.discs.append(
                (Hit("marker", name_of(coll)), xy, r, region, clip)
            )
    elif areas and isinstance(coll, PolyCollection):
        hit = Hit("area", name_of(coll, "filled area"))
        for o in drawn_collection_outlines(coll, renderer):
            ink.strokes.append((hit, o.path, o.half, region, clip))
    elif areas and isinstance(coll, LineCollection):
        hit = Hit("line", name_of(coll))
        for o in drawn_collection_outlines(coll, renderer):
            ink.strokes.append((hit, o.path, o.half, region, clip))


def data_ink(
    owners: list[Axes],
    frame: Bbox,
    renderer: RendererBase,
    px_per_pt: float,
    *,
    areas: bool,
) -> Ink:
    """Bars, data lines, markers and scatter points of one plot box; with
    ``areas``, filled areas and data line collections too."""
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
                    _collection(ink, coll, renderer, px_per_pt, areas)
        for container in ax.containers:
            if not isinstance(container, BarContainer):
                continue
            for patch in container.patches:
                with suppress(*BBOX_ERRORS):
                    box = drawn_patch_box(patch, renderer)
                    if box is not None and box.width > 0 and box.height > 0:
                        hit = Hit("bar", name_of(container))
                        horizontal = lies_across(container.orientation)
                        ink.bars.append((hit, box, horizontal))
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


def plain_label(text: MplText, ax: Axes) -> bool:
    """A value label measured by its box: inked, upright, no background box,
    not a contour label."""
    if not text_inks(text) or float(text.get_rotation()) % 90:
        return False
    for coll in ax.collections:
        if isinstance(coll, ContourSet) and text in coll.labelTexts:
            return False
    patch = text.get_bbox_patch()
    return patch is None or not patch_inks(patch)


_BOLD = {"bold", "heavy", "black", "extra bold", "semibold", "demibold"}


def _large(artist: MplText) -> bool:
    """WCAG large text: 18 pt, or 14 pt bold."""
    size, weight = float(artist.get_fontsize()), artist.get_fontweight()
    bold = str(weight).lower() in _BOLD or (
        isinstance(weight, int | float) and weight >= 600
    )
    return size >= 18 or (size >= 14 and bold)


def text_contrast(fig: Figure, texts: tuple[Text, ...]) -> tuple[Contrast, ...]:
    """Each text's ink against the median colour under its box.

    The root figure is drawn, as it is, into a private Agg buffer; the
    pixels near the text's own colour (its glyphs) are left out of the
    median. A text with path effects (a halo, an outline) is taken as
    readable.
    """
    root = fig.get_figure(root=True) or fig
    w, h = root.bbox.size
    agg = RendererAgg(int(w), int(h), root.dpi)
    root.draw(agg)
    rgba = np.asarray(agg.buffer_rgba(), dtype=float) / 255.0
    pixels = rgba[..., :3] * rgba[..., 3:] + (1.0 - rgba[..., 3:])
    rows, cols = pixels.shape[:2]
    found: list[Contrast] = []
    for t in texts:
        artist = t.handle
        if not isinstance(artist, MplText):
            continue
        ink = mcolors.to_rgba(artist.get_color(), artist.get_alpha())
        if ink[3] <= 0 or artist.get_path_effects():
            continue
        top = max(0, math.floor(rows - t.box.y1))
        bottom = min(rows, math.ceil(rows - t.box.y0))
        left, right = (
            max(0, math.floor(t.box.x0)),
            min(cols, math.ceil(t.box.x1)),
        )
        if bottom <= top or right <= left:
            continue
        under = pixels[top:bottom, left:right].reshape(-1, 3)
        paper = under[np.abs(under - np.asarray(ink[:3])).max(axis=1) > 0.2]
        median = np.median(paper if len(paper) else under, axis=0)
        bg = (float(median[0]), float(median[1]), float(median[2]))
        found.append(
            Contrast(
                text=t,
                ratio=contrast(Rgb.of(ink), Rgb.of(bg)).value,
                large=_large(artist),
                ink=mcolors.to_hex(ink[:3]),
                paper=mcolors.to_hex(bg),
            )
        )
    return tuple(found)
