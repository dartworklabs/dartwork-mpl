"""Read the drawn bars and scatter dots of a figure's flat Axes."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.patches import Rectangle
from matplotlib.transforms import Bbox

from ..geometry import (
    artist_shown,
    cut_to_clip,
    drawn_scatter_discs,
    edge_inks,
    patch_inks,
)
from ..vocab import Box
from .ink import in_data_coords
from .model import Bar, Dot

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def box_of(bb: Bbox) -> Box:
    """A matplotlib ``Bbox`` as a :class:`Box`."""
    return Box(float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1))


def bars(panel: int, ax: Axes) -> Iterator[Bar]:
    """The upright rectangles ``ax`` draws: bars, and bands like ``axhspan``."""
    for p in ax.patches:
        if not isinstance(p, Rectangle) or p.get_angle() or not patch_inks(p):
            continue
        outline = p.get_extents()
        if not np.isfinite(outline.extents).all():
            continue
        box = cut_to_clip(outline, p)
        if box is None:
            continue
        data = in_data_coords(p, ax)
        yield Bar(
            handle=p,
            panel=panel,
            box=box_of(box),
            lengths=(float(p.get_width()), float(p.get_height()))
            if data
            else (),
            outset=float(p.get_linewidth()) / 2 if edge_inks(p) else 0.0,
        )


def dots(panel: int, ax: Axes, px_per_pt: float) -> Iterator[Dot]:
    """The scatter points ``ax`` draws, each as the box around its disc."""
    for coll in ax.collections:
        if not isinstance(coll, PathCollection) or not artist_shown(coll):
            continue
        xy, radii = drawn_scatter_discs(coll, px_per_pt)
        for (x, y), r in zip(xy, radii, strict=True):
            box = cut_to_clip(Bbox([[x - r, y - r], [x + r, y + r]]), coll)
            if box is not None:
                yield Dot(handle=coll, panel=panel, box=box_of(box))
