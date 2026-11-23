"""Read the drawn bars and scatter dots of a figure's flat Axes."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection, PolyCollection
from matplotlib.colors import to_rgba
from matplotlib.patches import ConnectionPatch, Patch, Rectangle, Wedge
from matplotlib.text import Text as MplText
from matplotlib.transforms import Bbox

from ..geometry import (
    artist_shown,
    cut_to_clip,
    drawn_scatter_discs,
    edge_inks,
    line_draws_stroke,
    patch_inks,
)
from ..vocab import Box
from .ink import in_data_coords, name_of
from .model import Bar, Boxed, Dot, Hit, LineEnd, Text

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

#: A text box at least this opaque hides what is under it.
OPAQUE = 0.5
#: Colours this close on every channel are the same colour.
SAME_COLOUR = 0.02


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


def filled(patch: Patch) -> bool:
    """A shown patch whose face draws."""
    return (
        patch_inks(patch)
        and bool(patch.get_fill())
        and to_rgba(patch.get_facecolor())[3] > 0
    )


def under(ax: Axes, box: Bbox) -> Iterator[Hit]:
    """The filled data marks of ``ax`` that reach into ``box``."""
    for p in ax.patches:
        if filled(p) and in_data_coords(p, ax):
            outline = p.get_transform().transform_path(p.get_path())
            if outline.intersects_bbox(box, filled=True):
                kind = "bar" if isinstance(p, Rectangle) else "area"
                yield Hit(kind, name_of(p))
    for coll in ax.collections:
        if (
            isinstance(coll, PolyCollection)
            and artist_shown(coll)
            and in_data_coords(coll, ax)
        ):
            to_px = coll.get_transform()
            if any(
                to_px.transform_path(path).intersects_bbox(box, filled=True)
                for path in coll.get_paths()
            ):
                yield Hit("area", name_of(coll, "filled area"))


def boxed(
    texts: tuple[Text, ...], renderer: RendererBase, px_per_pt: float
) -> tuple[Boxed, ...]:
    """Placed texts on an opaque box of their own that covers filled marks."""
    found: list[Boxed] = []
    for t in texts:
        h = t.handle
        ax = h.axes if isinstance(h, MplText) else None
        if not (
            t.role.free and isinstance(h, MplText) and isinstance(ax, Axes)
        ):
            continue
        patch = h.get_bbox_patch()
        if patch is None or not filled(patch):
            continue
        if to_rgba(patch.get_facecolor())[3] < OPAQUE:
            continue
        box = patch.get_window_extent(renderer).padded(-0.5 * px_per_pt)
        if box.width <= 0 or box.height <= 0:
            continue
        if covers := tuple(dict.fromkeys(under(ax, box))):
            found.append(Boxed(t, covers))
    return tuple(found)


def corners(patch: Patch) -> np.ndarray:
    """The corners of a rectangle or a wedge, display px (none for others)."""
    if isinstance(patch, Rectangle):
        return np.asarray(patch.get_corners(), dtype=np.float64)
    if isinstance(patch, Wedge):
        centre = np.asarray(patch.center, dtype=np.float64)
        radii = [float(patch.r)]
        if patch.width:
            radii.append(float(patch.r) - float(patch.width))
        return np.array(
            [
                centre + r * np.array([np.cos(a), np.sin(a)])
                for a in np.radians([patch.theta1, patch.theta2])
                for r in radii
            ]
        )
    return np.empty((0, 2))


def hidden_rims(
    ax: Axes, paper: tuple[float, ...]
) -> Iterator[tuple[Patch, np.ndarray]]:
    """The filled rectangles and wedges of ``ax`` outlined in the colour
    of the paper, each with its corners in display px."""
    for p in ax.patches:
        if not (filled(p) and edge_inks(p) and in_data_coords(p, ax)):
            continue
        edge = to_rgba(p.get_edgecolor())
        if (
            max(abs(a - b) for a, b in zip(edge[:3], paper[:3], strict=True))
            > SAME_COLOUR
        ):
            continue
        at = corners(p)
        if len(at):
            yield p, ax.transData.transform(at)


def ends(fig: Figure) -> Iterator[tuple[object, np.ndarray]]:
    """Both ends of every straight two-point line and connector, display px."""
    for ax in fig.axes:
        for line in ax.lines:
            xy = np.asarray(line.get_xydata(), dtype=np.float64)
            if artist_shown(line) and line_draws_stroke(line) and len(xy) == 2:
                yield line, line.get_transform().transform(xy)
    links = [*fig.artists, *(p for ax in fig.axes for p in ax.patches)]
    for link in links:
        if isinstance(link, ConnectionPatch) and artist_shown(link):
            # get_path() is in the patch's own coordinates: figure
            # fractions for one added to the figure.
            path = link.get_transform().transform_path(link.get_path())
            tips = np.asarray(path.vertices, dtype=np.float64)
            if len(tips) >= 2:
                yield link, tips[[0, -1]]


def line_ends(fig: Figure, px_per_pt: float) -> tuple[LineEnd, ...]:
    """Line ends on an outer corner of a mark with a paper-coloured outline.

    A corner two such marks share is the seam between them: a line that
    ends there ends on the gap, where it was aimed.
    """
    rims: list[tuple[Patch, np.ndarray]] = []
    for ax in fig.axes:
        face = to_rgba(ax.get_facecolor())
        paper = face if face[3] > 0 else to_rgba(fig.get_facecolor())
        rims.extend(hidden_rims(ax, paper))
    if not rims:
        return ()
    touch = 0.5 * px_per_pt
    every = np.concatenate([at for _p, at in rims])
    found: list[LineEnd] = []
    for line, tips in ends(fig):
        for tip in tips[np.isfinite(tips).all(axis=1)]:
            if (np.hypot(*(every - tip).T) <= touch).sum() != 1:
                continue
            for patch, at in rims:
                if (np.hypot(*(at - tip).T) <= touch).any():
                    found.append(
                        LineEnd(line, patch, float(patch.get_linewidth()) / 2)
                    )
    return tuple(found)
