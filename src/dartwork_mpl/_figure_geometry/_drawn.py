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
  where an artist's clip box and clip path let it draw;
- :func:`drawn_ink_meets`: whether a path's ink (stroked, or filled) lies in
  a box where its clip lets it draw, the clip cutting the stroke, not the
  centre line;
- :func:`line_draws_stroke`, :func:`line_draws_markers`,
  :func:`patch_inks`, :func:`text_inks`: whether a line, a patch or a text
  draws any ink at all (a style, a width, a colour with alpha);
- :func:`marker_radius_pt`, :func:`drawn_scatter_discs`, :func:`discs_meet`:
  markers and scatter points as discs reaching half their edge past their
  size, and whether any reaches into a box where its clip lets it draw;
- :func:`drawn_patch_box`, :func:`drawn_text_box`: where a patch (its edge
  included) and a text (its background box included) draw.

Everything is in display px for the figure as last drawn.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.markers import MarkerStyle
from matplotlib.transforms import Affine2D, Bbox, TransformedPath

from ._subfigures import drawn_in_tree

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.backend_bases import RendererBase
    from matplotlib.collections import PathCollection
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.path import Path
    from matplotlib.text import Text
    from matplotlib.typing import ColorType

#: The region of an artist drawn without a clip: everywhere.
UNCLIPPED = Bbox.from_extents(-np.inf, -np.inf, np.inf, np.inf)
#: The region of an artist its clip lets draw nowhere: meets nothing.
NOWHERE = Bbox.from_extents(0.0, 0.0, 0.0, 0.0)


class DrawnOutline(NamedTuple):
    """One item a collection draws ink with: its path in display px, the
    half width its own edge is stroked at (0 when it draws no edge) and its
    index, which picks its style (a dash pattern) as the renderer cycles it."""

    path: Path
    half: float
    item: int = 0


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
        found.append(DrawnOutline(path, half, i))
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


def drawn_ink_meets(
    path: Path,
    half: float,
    box: Bbox,
    region: Bbox = UNCLIPPED,
    clip_path: Path | None = None,
    *,
    filled: bool = False,
) -> bool:
    """Whether ``path``'s ink lies in ``box`` where its clip lets it draw.

    The ink is the path stroked ``half`` px either side (and its inside
    when ``filled``). The clip cuts the ink, not the path: a thick line
    whose centre runs just past its clip still draws the part of its
    stroke inside it. So ``box`` is first cut to where the clip lets ink be
    drawn (``region``, then ``clip_path`` by :func:`within_clip_path`),
    and the path then meets that cut box widened by ``half``.
    """
    cut = _intersect(box, region)
    cut = within_clip_path(cut, clip_path)
    if cut is None:
        return False
    reach = cut.padded(half)
    if reach.width <= 0 or reach.height <= 0:
        return False
    return bool(path.intersects_bbox(reach, filled=filled))


# ------------------------------------------------- what an artist inks at all
_NO_STROKE = ("None", "none", "", " ")


def _alpha(color: ColorType, alpha: float | None = None) -> float:
    return float(to_rgba(color, alpha)[3])


def line_draws_stroke(line: Line2D) -> bool:
    """Whether ``line`` strokes its path: shown, with a line style, a width and a colour with alpha."""
    return bool(
        artist_shown(line)
        and line.get_linestyle() not in _NO_STROKE
        and line.get_linewidth() > 0
        and _alpha(line.get_color(), line.get_alpha()) > 0
    )


def line_draws_markers(line: Line2D) -> bool:
    """Whether ``line`` draws markers: shown, a marker of some size with a face or an edge.

    A filled marker draws its face when the face colour has alpha, and, when
    its fill style splits it (``fillstyle="left"`` and the like: the marker
    style has an alternate path), its other half in
    ``markerfacecoloralt``; any marker draws its edge at a width above 0 in
    a colour with alpha. The line's alpha, when set, replaces each colour's.
    """
    if not artist_shown(line):
        return False
    marker = line.get_marker()
    if marker is None or marker in _NO_STROKE or line.get_markersize() <= 0:
        return False
    try:
        style = MarkerStyle(marker, line.get_fillstyle())
        filled = style.is_filled()
        split = filled and style.get_alt_path() is not None
    except (TypeError, ValueError):
        filled, split = True, False
    alpha = line.get_alpha()
    face = filled and _alpha(line.get_markerfacecolor(), alpha) > 0
    alternate = split and _alpha(line.get_markerfacecoloralt(), alpha) > 0
    return face or alternate or _marker_edge_inks(line)


def _marker_edge_inks(line: Line2D) -> bool:
    """Whether a line's markers draw their edge: a width and a colour with alpha."""
    return bool(
        line.get_markeredgewidth() > 0
        and _alpha(line.get_markeredgecolor(), line.get_alpha()) > 0
    )


def patch_inks(patch: Patch) -> bool:
    """A shown patch with a face, an edge (a width, a line style, a colour) or a hatch with a colour.

    A patch's colours already carry its alpha.
    """
    if not artist_shown(patch):
        return False
    if patch.get_fill() and _alpha(patch.get_facecolor()) > 0:
        return True
    if _edge_inks(patch):
        return True
    return bool(
        patch.get_hatch()
        and patch.get_hatch_linewidth() > 0
        and _alpha(patch.get_hatchcolor()) > 0
    )


def _edge_inks(patch: Patch) -> bool:
    return bool(
        patch.get_linewidth() > 0
        and patch.get_linestyle() not in _NO_STROKE
        and _alpha(patch.get_edgecolor()) > 0
    )


def text_inks(text: Text) -> bool:
    """Whether ``text`` draws: drawn, a non-blank string in a colour with alpha.

    The text's own alpha, when set, replaces its colour's alpha, as
    matplotlib draws it.
    """
    return bool(
        drawn_in_tree(text)
        and text.get_text().strip()
        and _alpha(text.get_color(), text.get_alpha()) > 0
    )


# ------------------------------------------------------- markers as discs
def marker_radius_pt(line: Line2D) -> float:
    """How far a line's marker reaches from its centre, in points.

    Half its size plus half its edge width where it draws its edge: the
    edge is stroked on the marker's outline, half of it outside. An edge in
    no colour (``mec="none"``, alpha 0) reaches nowhere.
    """
    if not _marker_edge_inks(line):
        return float(line.get_markersize() / 2)
    return float(line.get_markersize() / 2 + line.get_markeredgewidth() / 2)


_EMPTY_DISCS = (np.empty((0, 2)), np.empty(0))


def drawn_scatter_discs(
    coll: PathCollection, px_per_pt: float
) -> tuple[np.ndarray, np.ndarray]:
    """The points of a scatter that draw ink: centres and radii, display px.

    A point ``sqrt(s)`` pt across reaches half that plus half its edge
    width past its centre where it draws its edge (``px_per_pt`` converts;
    an edge whose colour has no alpha, the collection's alpha applied,
    reaches nowhere). A masked x or y
    (``scatter`` masks both where x, y, s or c is masked) or a non-finite
    offset is not drawn; nor is a point whose face has no alpha and whose
    edge has no alpha or no width, or one of size 0. Each point takes its
    own size, colours and width, each list repeating; a collection without
    sizes has none.
    """
    offsets = np.ma.filled(
        np.ma.asarray(coll.get_offsets(), dtype=np.float64), np.nan
    ).reshape(-1, 2)
    sizes = np.asarray(coll.get_sizes(), dtype=np.float64)
    if not len(offsets) or not sizes.size:
        return _EMPTY_DISCS
    n = len(offsets)
    xy = coll.get_offset_transform().transform(offsets)
    faces = np.asarray(coll.get_facecolor(), dtype=np.float64).reshape(-1, 4)
    edges = np.asarray(coll.get_edgecolor(), dtype=np.float64).reshape(-1, 4)
    widths = np.asarray(coll.get_linewidth(), dtype=np.float64).ravel()
    face = np.resize(faces[:, 3], n) if len(faces) else np.zeros(n)
    edge = np.resize(edges[:, 3], n) if len(edges) else np.zeros(n)
    width = np.resize(widths, n) if widths.size else np.zeros(n)
    size = np.resize(sizes, n)
    # The colours carry the collection's alpha (one, or one per point).
    stroked = np.where(edge > 0, width, 0.0)
    radius = px_per_pt * (np.sqrt(size) + stroked) / 2
    keep = np.isfinite(xy).all(axis=1)
    keep &= (face > 0) | ((edge > 0) & (width > 0))
    keep &= size > 0  # a point of size 0 draws nothing, its edge neither
    return xy[keep], radius[keep]


def discs_meet(
    xy: np.ndarray,
    r: np.ndarray,
    box: Bbox,
    region: Bbox = UNCLIPPED,
    clip_path: Path | None = None,
) -> bool:
    """Whether a disc (centres ``xy``, radii ``r``, display px) reaches into
    ``box`` where its clip lets it draw.

    As :func:`drawn_ink_meets` cuts a stroke: ``box`` is first cut to the
    clip (``region``, then ``clip_path``), and a disc meets the cut box when
    its centre lies nearer to it than its radius.
    """
    cut = within_clip_path(_intersect(box, region), clip_path)
    if cut is None or not len(xy):
        return False
    nx = np.clip(xy[:, 0], cut.x0, cut.x1)
    ny = np.clip(xy[:, 1], cut.y0, cut.y1)
    return bool(np.any((xy[:, 0] - nx) ** 2 + (xy[:, 1] - ny) ** 2 < r**2))


# --------------------------------------------- where a patch, a text draws
def _cut_to_clip(box: Bbox, artist: Artist) -> Bbox | None:
    cut = _intersect(box, clip_region(artist))
    return within_clip_path(cut, clip_path_px(artist))


def drawn_patch_box(patch: Patch, renderer: RendererBase) -> Bbox | None:
    """Where ``patch`` draws ink, display px; ``None`` when nowhere.

    Its path's extent, grown by half its edge width where it draws an edge
    (the stroke is half outside the outline), then cut to where its clip
    lets it draw. A patch that inks nothing (:func:`patch_inks`) draws
    nowhere.
    """
    if not patch_inks(patch):
        return None
    box = patch.get_extents()
    if _edge_inks(patch):
        box = box.padded(
            float(np.asarray(renderer.points_to_pixels(patch.get_linewidth())))
            / 2
        )
    return _cut_to_clip(box, patch)


def drawn_text_box(text: Text, renderer: RendererBase) -> Bbox | None:
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
    return _cut_to_clip(Bbox.union(parts), text)
