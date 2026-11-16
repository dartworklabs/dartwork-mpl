"""What an Axes draws as data, for a legend to keep clear of.

``geometry.DataInk`` gathers, as the check slice gathers it, what each
artist of the plot actually draws, in display pixels; here every line,
collection (not a mesh), patch and text of the Axes and its twins counts,
and a box meets it within the legend's clearance.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.collections import LineCollection, QuadMesh
from matplotlib.contour import ContourSet
from matplotlib.transforms import Bbox, BboxBase

from ..geometry import (
    BBOX_ERRORS,
    DataInk,
    cut_to_clip,
    drawn_in_tree,
    drawn_patch_box,
    same_position_axes,
    text_inks,
)
from ..vocab import Box
from .model import CLEARANCE_PT, Hits

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.text import Text


@dataclass(frozen=True)
class Ink:
    """Data ink of one plot box, keyed by the artist that drew it."""

    clearance: float
    drawn: DataInk[int]

    def meets(self, box: Box) -> Hits:
        """The artists whose ink comes within the clearance of ``box``."""
        g = box.padded(self.clearance)
        grown = Bbox.from_extents(g.x0, g.y0, g.x1, g.y1)
        return Hits(len(self.drawn.meets(grown)))


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
    drawn: DataInk[int] = DataInk()

    def to_px(points: float) -> float:
        return px(renderer, points)

    for owner in same_position_axes(ax):
        for line in owner.get_lines():
            drawn.add_line(line, to_px, id(line), id(line))
        for coll in owner.collections:
            if coll.get_visible() and not isinstance(coll, QuadMesh):
                stroked = isinstance(coll, LineCollection) or (
                    isinstance(coll, ContourSet) and not coll.filled
                )
                drawn.add_collection(
                    coll, renderer, to_px, id(coll), filled=not stroked
                )
        for patch in owner.patches:
            with suppress(*BBOX_ERRORS):
                drawn.add_box(id(patch), drawn_patch_box(patch, renderer))
        for text in owner.texts:
            with suppress(*BBOX_ERRORS):
                drawn.add_box(id(text), _drawn_text_box(text, renderer))
    return Ink(px(renderer, CLEARANCE_PT), drawn)


def box_of(bb: BboxBase) -> Box:
    """A matplotlib ``Bbox`` as a :class:`Box`."""
    return Box(float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1))


def px(renderer: RendererBase, points: float) -> float:
    """``points`` in display px for ``renderer``."""
    return float(np.asarray(renderer.points_to_pixels(points)))
