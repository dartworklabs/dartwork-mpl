"""What an artist actually draws: a collection's paths and ink, and an artist's clip.

One rule for every caller that asks "is there ink here": ``dm.place_legend``
keeps clear of it and ``LEGEND_ON_DATA`` (with the other validate checks)
reports what covers it. The two used to read collections, transparency and
clipping each in their own way, so a legend could avoid what was not drawn,
or a check count what the placer ignored.

- :func:`drawn_collection_paths`: each item's path where ``Collection.draw``
  puts it (its own transform, the collection's, then its offset in display
  px), with the item's index;
- :func:`drawn_collection_outlines`: those items that draw ink, each by its
  own face, edge and hatch colour, alpha and line width;
- :func:`artist_shown`: visible and not at an artist alpha of 0 (one alpha
  per item: any above 0);
- :func:`clip_region`, :func:`clip_path_px`, :func:`within_clip_path`:
  where an artist's clip box and clip path let it draw.

Everything is in display px for the figure as last drawn.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np
from matplotlib.transforms import Affine2D, Bbox, TransformedPath

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.backend_bases import RendererBase
    from matplotlib.path import Path

#: The region of an artist drawn without a clip: everywhere.
UNCLIPPED = Bbox.from_extents(-np.inf, -np.inf, np.inf, np.inf)
#: The region of an artist its clip lets draw nowhere: meets nothing.
NOWHERE = Bbox.from_extents(0.0, 0.0, 0.0, 0.0)


class DrawnOutline(NamedTuple):
    """One item a collection draws ink with: its path in display px and the
    half width its own edge is stroked at (0 when it draws no edge)."""

    path: Path
    half: float


def drawn_collection_paths(coll: Any) -> list[tuple[int, Path]]:
    """Each item's path of ``coll`` where matplotlib draws it, in display px.

    As ``Collection.draw`` does: item ``i`` is path ``i``, through its own
    transform (``get_transforms``) and the collection's, then moved by
    offset ``i`` in display px (``get_offset_transform``), each list
    repeated to the longest. ``ax.quiver`` and a ``LineCollection`` given
    ``offsets`` place their paths this way; without the offsets their ink
    would sit at the origin. An item at a non-finite offset is not drawn.
    Each path comes with its item index, which picks its colours and width.
    """
    paths = list(coll.get_paths())
    if not paths:
        return []
    transform = coll.get_transform()
    items = np.asarray(coll.get_transforms(), dtype=float).reshape(-1, 3, 3)
    offsets = np.asarray(coll.get_offsets(), dtype=float).reshape(-1, 2)
    shifts = (
        coll.get_offset_transform().transform(offsets)
        if len(offsets)
        else np.zeros((0, 2))
    )
    drawn: list[tuple[int, Path]] = []
    for i in range(max(len(paths), len(shifts))):
        path = paths[i % len(paths)]
        if len(items):
            path = Affine2D(items[i % len(items)]).transform_path(path)
        path = transform.transform_path(path)
        if len(shifts):
            dx, dy = shifts[i % len(shifts)]
            if not (np.isfinite(dx) and np.isfinite(dy)):
                continue
            path = Affine2D().translate(dx, dy).transform_path(path)
        drawn.append((i, path))
    return drawn


def drawn_collection_outlines(
    coll: Any, renderer: RendererBase
) -> list[DrawnOutline]:
    """The items ``coll`` draws ink with, each by its own style.

    Item ``i`` takes its face, edge, hatch colour and line width as the
    renderer cycles them (each list repeating); its alpha is its colour's
    times the collection's alpha for it (one value, or one per item;
    matplotlib also writes that alpha into the colours). An item whose
    face, hatch and edge all draw nothing is left out, and an edge counts
    at its own width, not the widest of the collection.
    """
    faces = np.asarray(coll.get_facecolor(), dtype=float).reshape(-1, 4)
    edges = np.asarray(coll.get_edgecolor(), dtype=float).reshape(-1, 4)
    widths = np.asarray(coll.get_linewidth(), dtype=float).reshape(-1)
    alpha = coll.get_alpha()
    alphas = np.asarray(1.0 if alpha is None else alpha, dtype=float).reshape(
        -1
    )
    hatches = (
        np.asarray(coll.get_hatchcolor(), dtype=float).reshape(-1, 4)
        if coll.get_hatch() and coll.get_hatch_linewidth() > 0
        else np.zeros((0, 4))
    )
    found: list[DrawnOutline] = []
    for i, path in drawn_collection_paths(coll):
        a = float(alphas[i % len(alphas)]) if len(alphas) else 1.0
        face = bool(len(faces)) and faces[i % len(faces), 3] * a > 0
        hatch = bool(len(hatches)) and hatches[i % len(hatches), 3] * a > 0
        width = float(widths[i % len(widths)]) if len(widths) else 0.0
        edge = (
            bool(len(edges)) and width > 0 and edges[i % len(edges), 3] * a > 0
        )
        if not (face or edge or hatch):
            continue
        half = (
            float(np.asarray(renderer.points_to_pixels(width))) / 2
            if edge
            else 0.0
        )
        found.append(DrawnOutline(path, half))
    return found


def artist_shown(artist: Artist) -> bool:
    """Visible and not at an artist alpha of 0 (one per item: any above 0)."""
    alpha = artist.get_alpha()
    return bool(
        artist.get_visible()
        and (alpha is None or np.any(np.asarray(alpha, dtype=float) > 0))
    )


def _intersect(box: Bbox, frame: Bbox) -> Bbox | None:
    x0, y0 = max(box.x0, frame.x0), max(box.y0, frame.y0)
    x1, y1 = min(box.x1, frame.x1), min(box.y1, frame.y1)
    if x1 <= x0 or y1 <= y0:
        return None
    return Bbox.from_extents(x0, y0, x1, y1)


def clip_region(artist: Artist) -> Bbox:
    """Where ``artist``'s clip lets it draw, in display px.

    An artist draws clipped to its clip box and clip path when ``clip_on``
    (an ``ax.text`` is unclipped unless asked; data artists clip to their
    Axes). A clip path counts by its bounding box here; the path itself then
    decides whether the ink it lets through is any at all
    (:func:`within_clip_path`). :data:`UNCLIPPED` when nothing clips,
    :data:`NOWHERE` when the clip lets nothing through.
    """
    region = UNCLIPPED
    if not artist.get_clip_on():
        return region
    clip_box = artist.get_clip_box()
    if clip_box is not None:
        region = _intersect(region, clip_box) or NOWHERE
    clip_path = artist.get_clip_path()  # set_clip_path stores it transformed
    if isinstance(clip_path, TransformedPath):
        extent = clip_path.get_fully_transformed_path().get_extents()
        region = _intersect(region, extent) or NOWHERE
    return region


def clip_path_px(artist: Artist) -> Path | None:
    """``artist``'s clip path in display px, when ``clip_on`` uses one."""
    clip_path = artist.get_clip_path()
    if not artist.get_clip_on() or not isinstance(clip_path, TransformedPath):
        return None
    return clip_path.get_fully_transformed_path()


def within_clip_path(box: Bbox | None, clip_path: Path | None) -> Bbox | None:
    """``box`` when its clip path (as filled) lets any of it through."""
    if box is None or clip_path is None:
        return box
    return box if clip_path.intersects_bbox(box, filled=True) else None
