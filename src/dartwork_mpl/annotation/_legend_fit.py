"""Legend fitting for ``place_legend``: data ink, inside spots, free sides and label wrapping.

Everything here is measured with matplotlib's public API on a figure drawn
once. A trial legend is a detached :class:`~matplotlib.legend.Legend` built
only to read its size, and a spot's box is where matplotlib anchors a box of
that size (``Bbox.anchored``), so trying a spot draws nothing. The data a
legend must keep clear of is read as drawn: line paths at their width
(``Path.intersects_bbox``), markers and scatter points at their size, bars
and other patches by their extents, filled collections by their paths, and
the Axes' texts (value labels, annotations).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, cast

import numpy as np
from matplotlib.collections import LineCollection, PathCollection, QuadMesh
from matplotlib.contour import ContourSet
from matplotlib.legend import Legend
from matplotlib.transforms import Bbox

from .._figure_geometry import BBOX_ERRORS, same_position_axes

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.font_manager import FontProperties
    from matplotlib.path import Path

#: Room kept between a legend box and the nearest data ink, in points.
CLEARANCE_PT = 2.0

#: A one-column legend taller than this share of the Axes is tried last.
TALL_SHARE = 0.55

#: Inside spots in order of preference (ties go to the earlier one).
INSIDE_LOCS: tuple[str, ...] = (
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "upper center",
    "lower center",
    "center right",
    "center left",
)

_Anchor = Literal["NE", "NW", "SW", "SE", "N", "S", "E", "W"]

_ANCHOR: dict[str, _Anchor] = {
    "upper right": "NE",
    "upper left": "NW",
    "lower left": "SW",
    "lower right": "SE",
    "upper center": "N",
    "lower center": "S",
    "center right": "E",
    "center left": "W",
}

_NO_LINE = ("None", "none", "", " ")
_NO_MARKER = (None, "None", "none", "", " ")
_DEFAULT_SCATTER_SIZE = 36.0  # matplotlib's ``lines.markersize`` ** 2


@dataclass
class Ink:
    """The data ink of one plot box (an Axes and its twins), in display px.

    Each item is keyed by the ``id`` of the artist that drew it, so a
    legend's cost counts artists, not segments.
    """

    lines: list[tuple[int, Path, float]] = field(default_factory=list)
    filled: list[tuple[int, Path]] = field(default_factory=list)
    points: list[tuple[int, np.ndarray, np.ndarray]] = field(
        default_factory=list
    )
    boxes: list[tuple[int, Bbox]] = field(default_factory=list)

    def met(self, box: Bbox, clearance: float) -> set[int]:
        """The artists whose ink comes within ``clearance`` px of ``box``."""
        found: set[int] = set()
        grown = box.padded(clearance)
        for key, bb in self.boxes:
            if _overlaps(grown, bb):
                found.add(key)
        for key, path, half in self.lines:
            if key not in found and path.intersects_bbox(
                grown.padded(half), filled=False
            ):
                found.add(key)
        for key, path in self.filled:
            if key not in found and path.intersects_bbox(grown, filled=True):
                found.add(key)
        for key, xy, r in self.points:
            if key in found or not len(xy):
                continue
            nx = np.clip(xy[:, 0], grown.x0, grown.x1)
            ny = np.clip(xy[:, 1], grown.y0, grown.y1)
            if np.any((xy[:, 0] - nx) ** 2 + (xy[:, 1] - ny) ** 2 < r**2):
                found.add(key)
        return found


def _overlaps(a: Bbox, b: Bbox) -> bool:
    return bool(
        min(a.x1, b.x1) > max(a.x0, b.x0) and min(a.y1, b.y1) > max(a.y0, b.y0)
    )


def points_px(renderer: RendererBase, points: float) -> float:
    """``points`` in display px for ``renderer``."""
    return float(np.asarray(renderer.points_to_pixels(points)))


def _finite(xy: np.ndarray) -> np.ndarray:
    xy = np.asarray(xy, dtype=float).reshape(-1, 2)
    kept: np.ndarray = xy[np.isfinite(xy).all(axis=1)]
    return kept


def _measure_line(ink: Ink, line: Any, renderer: RendererBase) -> None:
    key = id(line)
    try:
        path = line.get_transform().transform_path(line.get_path())
    except BBOX_ERRORS:
        return
    if line.get_linestyle() not in _NO_LINE:
        ink.lines.append(
            (key, path, points_px(renderer, line.get_linewidth()) / 2)
        )
    if line.get_marker() not in _NO_MARKER:
        xy = _finite(path.vertices)
        r = points_px(renderer, line.get_markersize()) / 2
        ink.points.append((key, xy, np.full(len(xy), r)))


def _measure_collection(ink: Ink, coll: Any, renderer: RendererBase) -> None:
    key = id(coll)
    if isinstance(coll, PathCollection):
        try:
            xy = coll.get_offset_transform().transform(coll.get_offsets())
        except BBOX_ERRORS:
            return
        xy = _finite(xy)
        sizes = np.asarray(coll.get_sizes(), dtype=float)
        if not len(sizes):
            sizes = np.array([_DEFAULT_SCATTER_SIZE])
        radii = np.resize(np.sqrt(sizes) / 2, len(xy))
        ink.points.append(
            (key, xy, np.asarray([points_px(renderer, v) for v in radii]))
        )
        return
    try:
        transform = coll.get_transform()
        paths = [transform.transform_path(p) for p in coll.get_paths()]
    except BBOX_ERRORS:
        return
    stroked = isinstance(coll, LineCollection) or (
        isinstance(coll, ContourSet) and not coll.filled
    )
    if stroked:
        widths = np.atleast_1d(coll.get_linewidth())
        width = float(widths.max()) if len(widths) else 1.0
        half = points_px(renderer, width) / 2
        ink.lines.extend((key, p, half) for p in paths)
    else:
        ink.filled.extend((key, p) for p in paths)


def _measure_box(ink: Ink, artist: Artist, bb: Bbox) -> None:
    if bb.width > 0 and bb.height > 0:
        ink.boxes.append((id(artist), bb))


def measure_ink(ax: Axes, renderer: RendererBase) -> Ink:
    """The ink of ``ax`` and every twin drawn in its box.

    Lines (with their markers), patches, collections other than meshes and
    the Axes' texts; artists that are not visible draw no ink.
    """
    ink = Ink()
    for owner in same_position_axes(ax):
        for line in owner.get_lines():
            if line.get_visible():
                _measure_line(ink, line, renderer)
        for patch in owner.patches:
            if not patch.get_visible():
                continue
            try:
                _measure_box(ink, patch, patch.get_extents())
            except BBOX_ERRORS:
                continue
        for coll in owner.collections:
            if coll.get_visible() and not isinstance(coll, QuadMesh):
                _measure_collection(ink, coll, renderer)
        for text in owner.texts:
            if not text.get_visible() or not text.get_text().strip():
                continue
            try:
                _measure_box(ink, text, text.get_window_extent(renderer))
            except BBOX_ERRORS:
                continue
    return ink


# ----------------------------------------------------------- trial legends
def probe(
    parent: Axes | Figure | SubFigure,
    handles: list[Any],
    labels: list[str] | tuple[str, ...],
    **kw: Any,
) -> Legend:
    """A legend built only to be measured: not attached, nothing drawn.

    ``draggable`` is left out, so a trial connects no canvas events. With
    no ``loc`` it sits at the upper right: its size does not depend on
    where it sits, and matplotlib's ``"best"`` would search the data for a
    spot each time it is measured.
    """
    kw.pop("draggable", None)
    kw.setdefault("loc", "upper right")
    # matplotlib's stubs name Axes | Figure; SubFigure.legend builds the
    # same Legend on a SubFigure.
    owner = cast("Axes | Figure", parent)
    return Legend(owner, list(handles), list(labels), **kw)


def legend_size(legend: Legend, renderer: RendererBase) -> tuple[float, float]:
    """Width and height of a built legend, in display px (no canvas draw)."""
    bb = legend.get_window_extent(renderer)
    return float(bb.width), float(bb.height)


def legend_em(legend: Legend, renderer: RendererBase) -> float:
    """The legend's font size in display px."""
    return points_px(renderer, float(legend.prop.get_size_in_points()))


def legend_pad(legend: Legend, renderer: RendererBase) -> float:
    """The legend's ``borderaxespad`` in display px."""
    return float(legend.borderaxespad) * legend_em(legend, renderer)


def anchored_box(
    loc: str, size: tuple[float, float], parent: Bbox, pad: float
) -> Bbox:
    """Where matplotlib draws a legend of ``size`` at ``loc`` inside ``parent``."""
    box = Bbox.from_bounds(0, 0, size[0], size[1])
    return box.anchored(_ANCHOR[loc], container=parent.padded(-pad))


def outside_area(inner: Bbox, outer: Bbox) -> float:
    """The area of ``inner`` that lies outside ``outer``."""
    width = min(inner.x1, outer.x1) - max(inner.x0, outer.x0)
    height = min(inner.y1, outer.y1) - max(inner.y0, outer.y0)
    inside = max(width, 0.0) * max(height, 0.0)
    return max(float(inner.width * inner.height), 0.0) - float(inside)


@dataclass(frozen=True)
class InsideSpot:
    """An inside placement and what it costs.

    ``met`` counts the artists whose ink comes within the clearance,
    ``overflow`` is the share of the box outside the Axes and ``tall`` how
    far a one-column legend's height exceeds :data:`TALL_SHARE` of the Axes.
    """

    loc: str
    ncol: int
    met: int
    overflow: float
    tall: float

    @property
    def free(self) -> bool:
        """Meets no ink and stays inside the Axes."""
        return self.met == 0 and self.overflow <= 1e-3

    def rank(self) -> tuple[float, float, float]:
        """Sort key of the least covering spot: artists met, overflow, height."""
        return (float(self.met), self.overflow, self.tall)


# --------------------------------------------------------------- free sides
OutsideChoice = Literal["above", "right", "below"]

_SIDE_ORDER: tuple[OutsideChoice, ...] = ("above", "right", "below")


def free_sides(ax: Axes) -> list[OutsideChoice]:
    """The sides of ``ax`` no other panel sits beyond (twins and insets aside).

    A legend outside a side another panel occupies lands on that panel: the
    layout fits the outer margins only. Panels are compared by
    ``get_position``; Axes out of the layout (``set_in_layout(False)``) and
    hidden ones do not count.
    """
    fig = ax.get_figure(root=False)
    if fig is None:
        return list(_SIDE_ORDER)
    own = {id(a) for a in same_position_axes(ax)}
    me = ax.get_position()
    eps = 1e-6
    others = [
        other.get_position()
        for other in fig.axes
        if id(other) not in own
        and other.get_visible()
        and other.get_in_layout()
    ]

    def blocked(side: OutsideChoice) -> bool:
        for pos in others:
            across = min(pos.x1, me.x1) - max(pos.x0, me.x0) > eps
            along = min(pos.y1, me.y1) - max(pos.y0, me.y0) > eps
            match side:
                case "above":
                    hit = pos.y0 >= me.y1 - eps and across
                case "below":
                    hit = pos.y1 <= me.y0 + eps and across
                case "right":
                    hit = pos.x0 >= me.x1 - eps and along
            if hit:
                return True
        return False

    return [side for side in _SIDE_ORDER if not blocked(side)]


# --------------------------------------------------------------- label wrap
_UNIT_TAIL = re.compile(r"\s*([([][^)\]]{1,32}[)\]])\s*$")


def text_width(
    text: str, prop: FontProperties, renderer: RendererBase
) -> float:
    """Width of the widest line of ``text`` in display px."""
    widths = [
        renderer.get_text_width_height_descent(part, prop, ismath=False)[0]
        for part in text.split("\n")
    ]
    return float(max(widths)) if widths else 0.0


def wrap_label(text: str, max_px: float, width: Callable[[str], float]) -> str:
    """Wrap ``text`` at spaces so each line is at most ``max_px`` wide.

    ``width`` measures one line in px (:func:`text_width` in the legend's
    font). Greedy, word by word; a word wider than the limit keeps its own
    line. A trailing unit in brackets (``(2019 = 100)``) stays one piece.
    Text that already fits, or holds a line break or mathtext, is returned
    as is.
    """
    if "\n" in text or "$" in text or width(text) <= max_px:
        return text
    unit = ""
    body = text
    match = _UNIT_TAIL.search(text)
    if match:
        unit = match.group(1)
        body = text[: match.start()]
    words = body.split()
    if unit:
        words.append(unit)
    if len(words) < 2:
        return text
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if width(trial) <= max_px:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return "\n".join(lines)


def handle_overhead(legend: Legend, renderer: RendererBase) -> float:
    """Px a legend adds around one column's text: handle, gaps, border pad."""
    em = legend_em(legend, renderer)
    return em * (
        float(legend.handlelength)
        + float(legend.handletextpad)
        + 2 * float(legend.borderpad)
    )


def ceil_div(a: int, b: int) -> int:
    """``ceil(a / b)`` for positive integers."""
    return -(-a // b)


__all__ = [
    "CLEARANCE_PT",
    "INSIDE_LOCS",
    "TALL_SHARE",
    "Ink",
    "InsideSpot",
    "OutsideChoice",
    "anchored_box",
    "ceil_div",
    "free_sides",
    "handle_overhead",
    "legend_em",
    "legend_pad",
    "legend_size",
    "measure_ink",
    "outside_area",
    "points_px",
    "probe",
    "text_width",
    "wrap_label",
]
