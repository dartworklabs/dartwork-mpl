"""Where a plot's data ink is drawn, to find what a legend covers.

Gathered by ``geometry.DataInk``, as the legend slice gathers it: lines at
their width, markers and scatter points as discs, bars by their drawn
boxes, filled areas by their outlines, each only where its clip lets it
draw. What counts here: data in data coordinates (not an ``axhline``),
named by kind and label for the finding.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
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
    DataInk,
    clip_path_px,
    clip_region,
    drawn_patch_box,
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


@dataclass(frozen=True)
class Ink:
    """The data ink of one plot box (an Axes and its twins), by artist."""

    frame: Bbox
    drawn: DataInk[Hit]

    def meets(self, box: Bbox, touch: float) -> list[Hit]:
        """What ``box`` covers by more than ``touch`` inside the plot box."""
        inner = cut(box.padded(-touch), self.frame)
        return [] if inner is None else self.drawn.meets(inner, touch)


def _hit(coll: Collection) -> Hit | None:
    """How a collection is named when covered (``None``: not counted)."""
    if isinstance(coll, PathCollection):
        return Hit("marker", name_of(coll)) if len(coll.get_sizes()) else None
    if isinstance(coll, PolyCollection):
        return Hit("area", name_of(coll, "filled area"))
    if isinstance(coll, LineCollection):
        return Hit("line", name_of(coll))
    return None


def data_ink(
    owners: list[Axes], frame: Bbox, renderer: RendererBase, px_per_pt: float
) -> Ink:
    """Bars, data lines, markers, scatter points, filled areas and data line
    collections of one plot box."""
    drawn: DataInk[Hit] = DataInk()

    def to_px(points: float) -> float:
        return points * px_per_pt

    for ax in owners:
        for line in ax.get_lines():
            if line.get_visible() and in_data_coords(line, ax):
                name = name_of(line)
                drawn.add_line(
                    line, to_px, Hit("line", name), Hit("marker", name)
                )
        for coll in ax.collections:
            if (coll.get_visible() and in_data_coords(coll, ax)) or (
                isinstance(coll, PathCollection) and coll.get_visible()
            ):
                hit = _hit(coll)
                if hit is not None:
                    drawn.add_collection(
                        coll, renderer, to_px, hit, filled=False
                    )
        for container in ax.containers:
            if not isinstance(container, BarContainer):
                continue
            for patch in container.patches:
                with suppress(*BBOX_ERRORS):
                    drawn.add_box(
                        Hit("bar", name_of(container)),
                        drawn_patch_box(patch, renderer),
                    )
    return Ink(frame, drawn)


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
