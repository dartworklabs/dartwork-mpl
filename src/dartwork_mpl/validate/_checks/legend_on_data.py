"""LEGEND_ON_DATA: a legend drawn over data, a text, another legend or another panel.

``LEGEND_OVERLAP`` compares a legend with titles, axis labels, tick labels
and figure text. This check compares it with what the reader reads values
from. It takes every Axes legend (inset Axes from ``ax.inset_axes``
included) and figure legend that draws any ink, a frame or an entry, and
reports, per legend, what its box meets:

* data in any plot box (an Axes and its ``twinx`` / ``twiny`` partners,
  insets too), measured as VALUE_LABEL_ON_DATA measures it: bars, drawn
  line segments at their width, markers and scatter points at their size,
  clipped to the plot box. A legend over another panel's data counts too;
* line collections drawn in data coordinates (``vlines``, ``hlines``,
  errorbar bars, stem lines, ``eventplot``, a ``LineCollection``), as
  lines: each segment at its own width and colour where its clip lets it
  draw, read as ``dm.place_legend`` reads them. One drawn with an axis in
  Axes coordinates is a reference, not data, as an ``axvline`` is not;
* filled areas in any plot box (``PolyCollection``: ``fill_between``
  bands, ``stackplot`` layers, violin bodies, ``broken_barh``) that draw
  ink, by their outline where it is drawn (at the edge's width): what a
  reader reads from an area is its shape, so a legend crossing an area's
  edge, down to a violin's thinnest tail, or holding a whole area counts,
  and one lying inside a region's plain interior (a phase region, a band
  wider than the legend) does not. Only what is drawn: each polygon by
  its own face, edge and hatch ink (an alpha per polygon included), where
  the collection's clip box and clip path let it draw;
* the texts inside any Axes (``ax.texts``: value labels, annotations,
  line-end labels) where they are drawn: the text itself, not an
  annotation's arrow, cut to its clip box and clip path; a text clipped
  away or drawn without ink (its colour's alpha, replaced by the text's
  own alpha when that is set) does not count;
* another legend's box;
* another panel's plot box, even where that panel draws no data: an Axes
  legend reaching into a neighbouring Axes is drawn over or under it.

Contact up to half a point is a touch, not a cover. A legend inside its own
Axes is drawn over the panels that Axes sits on (an inset, or an Axes added
on top of another with ``fig.add_axes``), so those do not count. A legend
whose frame, title, entry texts and handles all draw no ink is left out
(``ax.legend([], [], frameon=False)``, everything at alpha 0, or handles
with no stroke, fill, marker or hatch in a colour with alpha; every
artist an entry draws is read, an errorbar's bars too); one with entries
but no frame is compared by its box. Images, meshes,
contours and polar plots are not data here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, NamedTuple, TypeAlias, TypedDict

import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import Collection, LineCollection, PolyCollection
from matplotlib.colors import to_rgba_array
from matplotlib.lines import Line2D
from matplotlib.offsetbox import DrawingArea, OffsetBox
from matplotlib.patches import Patch
from matplotlib.text import Text

from ..._figure_geometry import (
    DrawnOutline,
    artist_shown,
    clip_path_px,
    clip_region,
    discs_meet,
    drawn_collection_outlines,
    drawn_in_tree,
    drawn_ink_meets,
    figure_legends,
    line_draws_markers,
    line_draws_stroke,
    patch_inks,
    same_position_axes,
    text_inks,
    within_clip_path,
)
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import wire
from ._registry import register_check, register_fix
from .value_label_on_data import (
    _clip,
    _is_data_line,
    _measure,
    _name,
    _segments_hit,
    _text_box,
    _window,
)

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.legend import Legend
    from matplotlib.path import Path
    from matplotlib.transforms import Bbox

    from .value_label_on_data import _Data

__all__ = ["check_legend_on_data"]

Covered: TypeAlias = Literal[
    "area", "bar", "line", "marker", "text", "legend", "panel"
]

_TOUCH_PT = 0.5
_UNNAMED_AREA = "filled area"
_NAME_CHARS = 30  # names in the message and detail are cut to this length
_MAX_NAMES = 3
_MAX_LABELS = 5


class LegendOnDataDetail(TypedDict):
    """The legend of ``legend_axes`` (``None``: a figure legend) covers ``covered``.

    ``legend_axes`` is the ``fig.axes`` index of the Axes that holds the
    legend, or of the Axes an inset holding it belongs to; then
    ``legend_inset`` is the path of ``child_axes`` indices down to the inset
    (``[]`` otherwise). ``legend_labels`` holds the legend's first five
    entry texts, so a figure legend can be told apart; ``artists`` names up
    to three covered artists (series labels, text, ``legend of axes[i]``,
    ``axes[i]`` or ``axes[i].insets[j]``); ``panels`` lists the ``fig.axes``
    indices whose plot box, or whose inset's, holds the covered data.
    """

    legend_axes: int | None
    legend_inset: list[int]
    legend_labels: list[str]
    covered: list[Covered]
    artists: list[str]
    panels: list[int]


class _Hit(NamedTuple):
    kind: Covered
    name: str


class _Owner(NamedTuple):
    """An Axes the reader sees, named as figure_review names it.

    ``top`` is its ``fig.axes`` index, or that of the Axes its inset path
    starts from; ``inset`` the ``child_axes`` indices down to it.
    """

    name: str
    top: int
    inset: tuple[int, ...]
    ax: Axes


class _PlotBox(NamedTuple):
    """One rectilinear plot box: its first Axes, the owners and the frame."""

    owner: _Owner
    owners: list[Axes]
    frame: Bbox


class _Placed(NamedTuple):
    """A legend that draws ink, the Axes it belongs to (``None``: figure) and its box."""

    owner: _Owner | None
    legend: Legend
    box: Bbox


def _cut(name: str) -> str:
    return name.strip()[:_NAME_CHARS]


def _owners(fig: Figure) -> list[_Owner]:
    """Every drawn Axes: ``fig.axes`` in order, each followed by its insets.

    ``ax.inset_axes`` keeps an inset in ``ax.child_axes``, not in
    ``fig.axes``; a hidden Axes hides its insets too.
    """
    found: list[_Owner] = []

    def walk(ax: Axes, name: str, top: int, inset: tuple[int, ...]) -> None:
        if not drawn_in_tree(ax):  # a hidden SubFigure hides its Axes
            return
        found.append(_Owner(name, top, inset, ax))
        children = [c for c in ax.child_axes if isinstance(c, Axes)]
        for j, child in enumerate(children):
            walk(child, f"{name}.insets[{j}]", top, (*inset, j))

    for i, ax in enumerate(fig.axes):
        walk(ax, f"axes[{i}]", i, ())
    return found


def _any_alpha(colors: Any) -> bool:
    """Whether any of ``colors`` (one colour, or an RGBA array) has alpha."""
    return bool(np.any(to_rgba_array(colors)[:, 3] > 0))


def _collection_inks(collection: Collection) -> bool:
    """Any face or edge with alpha, or a hatch; scatter points at size 0 draw nothing."""
    if not artist_shown(collection):
        return False
    sizes = getattr(collection, "get_sizes", None)
    if sizes is not None:
        drawn = sizes()
        if (
            drawn is not None
            and len(drawn)
            and not np.any(np.asarray(drawn) > 0)
        ):
            return False
    if _any_alpha(collection.get_facecolor()):
        return True
    widths = np.asarray(collection.get_linewidth(), dtype=float)
    if np.any(widths > 0) and _any_alpha(collection.get_edgecolor()):
        return True
    return bool(
        collection.get_hatch()
        and collection.get_hatch_linewidth() > 0
        and _any_alpha(collection.get_hatchcolor())
    )


def _inks(artist: Artist) -> bool:
    """Whether ``artist`` draws anything, read by what its type draws.

    An artist of another type counts when it is shown at all.
    """
    if isinstance(artist, Line2D):
        return line_draws_stroke(artist) or line_draws_markers(artist)
    if isinstance(artist, Patch):
        return patch_inks(artist)
    if isinstance(artist, Collection):
        return _collection_inks(artist)
    if isinstance(artist, Text):
        return text_inks(artist)
    return artist_shown(artist)


def _handle_artists(legend: Legend) -> list[Artist]:
    """Every artist the legend's entries draw: each handle box's contents.

    ``legend.legend_handles`` holds only each entry's first artist; an
    errorbar or a tuple handle draws more. Read through the public
    ``get_children`` of the legend's offset boxes.
    """
    found: list[Artist] = []

    def walk(box: OffsetBox) -> None:
        for child in box.get_children():
            if isinstance(child, DrawingArea):
                found.extend(child.get_children())
            elif isinstance(child, OffsetBox):
                walk(child)

    for child in legend.get_children():
        if isinstance(child, OffsetBox):
            walk(child)
    return found or [h for h in legend.legend_handles if h]


def _draws_ink(legend: Legend) -> bool:
    """Whether ``legend`` draws a frame, a title or an entry the reader sees."""
    if legend.get_frame_on() and patch_inks(legend.get_frame()):
        return True
    texts = [legend.get_title(), *legend.get_texts()]
    if any(text_inks(text) for text in texts):
        return True
    return any(_inks(artist) for artist in _handle_artists(legend))


def _legends(fig: Figure, renderer: RendererBase) -> list[_Placed]:
    found: list[tuple[_Owner | None, Legend]] = []
    for owner in _owners(fig):
        legend = owner.ax.get_legend()
        if legend is not None and drawn_in_tree(legend):
            found.append((owner, legend))
    # A SubFigure's legends are on it, not on ``fig.legends``.
    found.extend(
        (None, legend)
        for legend in figure_legends(fig)
        if drawn_in_tree(legend)
    )
    placed: list[_Placed] = []
    for holder, legend in found:
        if not _draws_ink(legend):
            continue
        try:
            box = legend.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if box.width > 0 and box.height > 0:
            placed.append(_Placed(holder, legend, box))
    return placed


def _plot_boxes(owners: list[_Owner], renderer: RendererBase) -> list[_PlotBox]:
    """One entry per rectilinear plot box; twins share their first Axes' entry."""
    seen: set[int] = set()
    boxes: list[_PlotBox] = []
    for owner in owners:
        ax = owner.ax
        if ax.name != "rectilinear" or id(ax) in seen:
            continue
        partners = same_position_axes(ax)
        seen.update(id(partner) for partner in partners)
        try:
            frame = ax.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        boxes.append(_PlotBox(owner, partners, frame))
    return boxes


def _meets(a: Bbox, b: Bbox, touch: float) -> bool:
    return bool(
        min(a.x1, b.x1) - max(a.x0, b.x0) > touch
        and min(a.y1, b.y1) - max(a.y0, b.y0) > touch
    )


def _within(inner: Bbox, outer: Bbox) -> bool:
    return bool(
        inner.x0 >= outer.x0
        and inner.y0 >= outer.y0
        and inner.x1 <= outer.x1
        and inner.y1 <= outer.y1
    )


def _data_hits(box: Bbox, data: _Data, frame: Bbox, touch: float) -> list[_Hit]:
    """Bars, lines and markers of one plot box that ``box`` covers."""
    found: list[_Hit] = []
    if len(data.bars.box):
        x0, y0, x1, y1 = data.bars.box.T
        meets = np.minimum(box.x1, x1) - np.maximum(box.x0, x0) > touch
        meets &= np.minimum(box.y1, y1) - np.maximum(box.y0, y0) > touch
        found += [
            _Hit("bar", data.bars.names[i]) for i in np.flatnonzero(meets)
        ]
    clipped = _clip(box, frame)
    if clipped is None:
        return found
    lined: set[int] = set()
    for line in data.lines:
        # Where the line's clip lets it draw (the clip cuts the stroke, not
        # the centre line), the stroke reaches ``half`` past its path;
        # contact within ``touch`` of the legend's edge is a touch.
        cut = within_clip_path(_clip(clipped, line.region), line.clip_path)
        if cut is None:
            continue
        reach = cut.padded(line.half - touch)
        if reach.width > 0 and reach.height > 0 and _segments_hit(line, reach):
            found.append(_Hit("line", line.name))
            lined.add(line.key)
    for marks in data.markers:
        if marks.key in lined or not len(marks.xy):
            continue
        run = _window(marks.xy[:, 0], marks.reach, clipped.x0, clipped.x1)
        r = np.maximum(marks.r[run] - touch, 0.0)
        if discs_meet(marks.xy[run], r, clipped, marks.region, marks.clip_path):
            found.append(_Hit("marker", marks.name))
    return found


class _Area(NamedTuple):
    """A filled or line collection where it is drawn: its kind, the items
    that draw ink, and where its clip lets them be drawn (a region and a
    clip path, in px)."""

    kind: Covered
    name: str
    outlines: list[DrawnOutline]
    region: Bbox
    clip_path: Path | None


def _area_kind(coll: Collection, owner: Axes) -> tuple[Covered, str] | None:
    """``("area", name)`` for a filled collection, ``("line", name)`` for a
    line collection drawn in data coordinates on both axes; else ``None``."""
    if isinstance(coll, PolyCollection):
        return "area", _name(coll) or _UNNAMED_AREA
    if isinstance(coll, LineCollection) and _is_data_line(coll, owner):
        return "line", _name(coll)
    return None


def _areas(owners: list[Axes], renderer: RendererBase) -> list[_Area]:
    """The filled areas and data line collections of one plot box that draw
    ink, and their clip.

    The items and their ink are read as ``dm.place_legend`` reads them
    (:func:`~dartwork_mpl._figure_geometry.drawn_collection_outlines`), and
    the clip as a label's is (:func:`~dartwork_mpl._figure_geometry.clip_region`,
    :func:`~dartwork_mpl._figure_geometry.clip_path_px`: its clip box and the
    extent of its clip path, when ``clip_on``).
    """
    found: list[_Area] = []
    for owner in owners:
        for coll in owner.collections:
            kind = _area_kind(coll, owner) if coll.get_visible() else None
            if kind is None:
                continue
            try:
                outlines = drawn_collection_outlines(coll, renderer)
                region = clip_region(coll)
                clip_path = clip_path_px(coll)
            except BBOX_ERRORS:
                continue
            if outlines:
                found.append(_Area(*kind, outlines, region, clip_path))
    return found


def _area_hits(
    box: Bbox, areas: list[_Area], frame: Bbox, touch: float
) -> list[_Hit]:
    """Areas whose drawn outline ``box`` crosses, or holds whole, and line
    collections whose drawn segments it meets.

    The legend's box is cut to the plot box; contact within ``touch`` of its
    edge is a touch. Each item's outline (a polygon's, a segment) is stroked
    its ``half`` past its path, and the collection's clip cuts that stroke
    where it lets it draw, as ``dm.place_legend`` reads it
    (:func:`~dartwork_mpl._figure_geometry.drawn_ink_meets`; a clip path
    that lets none of the box through draws none of it there). A box inside
    an area's interior meets no outline (``filled=False``).
    """
    clipped = _clip(box, frame)
    if clipped is None:
        return []
    inner = clipped.padded(-touch)
    return [
        _Hit(area.kind, area.name)
        for area in areas
        if any(
            drawn_ink_meets(
                outline.path, outline.half, inner, area.region, area.clip_path
            )
            for outline in area.outlines
        )
    ]


def _drawn_text_box(text: Text, renderer: RendererBase) -> Bbox | None:
    """Where ``text`` is drawn: its own box (not an arrow), clipped; ``None`` if nowhere.

    As VALUE_LABEL_ON_DATA reads a label: the box of the text itself, cut to
    the clip box and to the clip path's extent when ``clip_on``; a clip path
    that lets none of it through, or a text drawn at alpha 0, draws nothing.
    """
    if not text_inks(text):
        return None
    try:
        box = _text_box(text, renderer)
    except BBOX_ERRORS:
        return None
    if box is None:
        return None
    return within_clip_path(_clip(box, clip_region(text)), clip_path_px(text))


def _text_hits(
    owners: list[_Owner], box: Bbox, renderer: RendererBase, touch: float
) -> list[_Hit]:
    found: list[_Hit] = []
    for owner in owners:
        for text in owner.ax.texts:
            drawn = _drawn_text_box(text, renderer)
            if drawn is not None and _meets(box, drawn, touch):
                found.append(_Hit("text", _cut(text.get_text())))
    return found


class _Measured:
    """Each plot box's data, measured the first time a legend meets the box."""

    def __init__(self, fig: Figure, renderer: RendererBase) -> None:
        self._fig = fig
        self._renderer = renderer
        self._data: dict[str, _Data] = {}
        self._areas: dict[str, list[_Area]] = {}

    def of(self, plot: _PlotBox) -> _Data:
        key = plot.owner.name
        if key not in self._data:
            self._data[key] = _measure(
                plot.owners, plot.frame, self._renderer, self._fig
            )
        return self._data[key]

    def areas(self, plot: _PlotBox) -> list[_Area]:
        key = plot.owner.name
        if key not in self._areas:
            self._areas[key] = _areas(plot.owners, self._renderer)
        return self._areas[key]


def _hits(
    placed: _Placed,
    legends: list[_Placed],
    owners: list[_Owner],
    boxes: list[_PlotBox],
    measured: _Measured,
    renderer: RendererBase,
    touch: float,
) -> tuple[list[_Hit], list[int]]:
    box = placed.box
    own: set[int] = set()
    own_frame: Bbox | None = None
    if placed.owner is not None:
        ax = placed.owner.ax
        own = {id(a) for a in same_position_axes(ax)}
        try:
            own_frame = ax.get_window_extent(renderer)
        except BBOX_ERRORS:
            own_frame = None
    inside_own = own_frame is not None and _within(box, own_frame)
    hits: list[_Hit] = []
    panels: list[int] = []
    for plot in boxes:
        if not _meets(box, plot.frame, touch):
            continue
        mine = bool(own & {id(owner) for owner in plot.owners})
        if (
            not mine
            and inside_own
            and own_frame is not None
            and _within(own_frame, plot.frame)
        ):
            continue  # drawn over the panel its own Axes sits on
        if placed.owner is not None and not mine:
            hits.append(_Hit("panel", plot.owner.name))
        found = _data_hits(box, measured.of(plot), plot.frame, touch)
        found += _area_hits(box, measured.areas(plot), plot.frame, touch)
        if found:
            hits += found
            panels.append(plot.owner.top)
    hits += _text_hits(owners, box, renderer, touch)
    for other in legends:
        if other.legend is not placed.legend and _meets(box, other.box, touch):
            name = (
                "figure legend"
                if other.owner is None
                else f"legend of {other.owner.name}"
            )
            hits.append(_Hit("legend", name))
    return hits, list(dict.fromkeys(panels))


@register_check("LEGEND_ON_DATA", order=46)
def check_legend_on_data(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Flag legends drawn over data, texts, other legends or other panels."""
    legends = _legends(fig, renderer)
    if not legends:
        return []
    touch = _TOUCH_PT * fig.dpi / 72.0
    owners = _owners(fig)
    boxes = _plot_boxes(owners, renderer)
    measured = _Measured(fig, renderer)
    warnings: list[VisualWarning] = []
    for placed in legends:
        hits, panels = _hits(
            placed, legends, owners, boxes, measured, renderer, touch
        )
        if not hits:
            continue
        kinds: list[Covered] = sorted({hit.kind for hit in hits})
        names = list(dict.fromkeys(hit.name for hit in hits))
        labels = [_cut(text.get_text()) for text in placed.legend.get_texts()][
            :_MAX_LABELS
        ]
        owner = (
            "Figure legend"
            if placed.owner is None
            else f"Legend of {placed.owner.name}"
        )
        shown = ", ".join(repr(name) for name in names[:_MAX_NAMES])
        more = ", ..." if len(names) > _MAX_NAMES else ""
        warnings.append(
            VisualWarning(
                severity=Severity.WARNING,
                check_id="LEGEND_ON_DATA",
                message=(
                    f"{owner} covers "
                    f"{', '.join(kind + 's' for kind in kinds)} "
                    f"({shown}{more})"
                ),
                detail=wire(
                    LegendOnDataDetail(
                        legend_axes=(
                            None if placed.owner is None else placed.owner.top
                        ),
                        legend_inset=(
                            []
                            if placed.owner is None
                            else list(placed.owner.inset)
                        ),
                        legend_labels=labels,
                        covered=kinds,
                        artists=names[:_MAX_NAMES],
                        panels=panels,
                    )
                ),
            )
        )
    return warnings


@register_fix("LEGEND_ON_DATA")
def _fix_legend_on_data(_warning: VisualWarning) -> list[str]:
    """Placements that keep a legend off the data."""
    return [
        "# Inside where it covers nothing, else outside its Axes\n"
        "dm.place_legend(ax)\ndm.simple_layout(fig)",
        "# Panels sharing one set of series: one legend for the figure\n"
        "dm.figure_legend(fig)\ndm.simple_layout(fig)",
        "# Many lines: name them at their ends instead of a legend\n"
        "dm.label_line_ends(ax)\ndm.simple_layout(fig)",
    ]
