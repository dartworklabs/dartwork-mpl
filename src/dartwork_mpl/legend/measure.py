"""Read the facts a legend decision needs from a figure drawn once.

A trial legend is a detached ``Legend`` built only to read its size, so
trying a spot or a column count draws nothing. Data ink is read by the drawn
rules ``check`` shares (``_figure_geometry``): lines at their width, markers
and scatter points as discs, patches and texts by their drawn boxes, filled
collections by their outlines, each only where its clip lets it draw.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import matplotlib as mpl
import numpy as np
from matplotlib.collections import LineCollection, PathCollection, QuadMesh
from matplotlib.contour import ContourSet
from matplotlib.legend import Legend
from matplotlib.transforms import Bbox, BboxBase

from .._figure_geometry import (
    BBOX_ERRORS,
    UNCLIPPED,
    axes_decoration_extents,
    axes_titles,
    clip_path_px,
    clip_region,
    discs_meet,
    drawn_collection_outlines,
    drawn_in_tree,
    drawn_ink_meets,
    drawn_patch_box,
    drawn_scatter_discs,
    drawn_text_box,
    line_draws_markers,
    line_draws_stroke,
    marker_radius_pt,
    root_position,
    same_position_axes,
)
from .model import (
    CLEARANCE_PT,
    FALLBACK_SIDES,
    AnchorFacts,
    Box,
    Columns,
    Entries,
    EntryFacts,
    FigureFacts,
    Hits,
    LegendFacts,
    LegendPlan,
    Owner,
    Request,
    Side,
    Size,
    Span,
    TitleBox,
    TitleFacts,
)

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.path import Path


def box_of(bb: BboxBase) -> Box:
    """A matplotlib ``Bbox`` as a :class:`Box`."""
    return Box(float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1))


def px(renderer: RendererBase, points: float) -> float:
    """``points`` in display px for ``renderer``."""
    return float(np.asarray(renderer.points_to_pixels(points)))


# ------------------------------------------------------------------ ink
@dataclass
class Ink:
    """Data ink of one plot box, keyed by the artist that drew it."""

    clearance: float
    boxes: list[tuple[int, Bbox]] = field(default_factory=list)
    strokes: list[tuple[int, Path, float, bool]] = field(default_factory=list)
    discs: list[tuple[int, np.ndarray, np.ndarray]] = field(
        default_factory=list
    )
    clips: dict[int, tuple[Bbox, Path | None]] = field(default_factory=dict)

    def clip(self, artist: Artist) -> None:
        """Record where ``artist``'s clip lets it draw, if anything clips it."""
        region, path = clip_region(artist), clip_path_px(artist)
        if region is not UNCLIPPED or path is not None:
            self.clips[id(artist)] = (region, path)

    def meets(self, box: Box) -> Hits:
        """The artists whose ink comes within the clearance of ``box``."""
        g = box.padded(self.clearance)
        grown = Bbox.from_extents(g.x0, g.y0, g.x1, g.y1)
        found = {k for k, bb in self.boxes if box_of(bb).overlaps(g)}
        for key, path, half, filled in self.strokes:
            region, cp = self.clips.get(key, (UNCLIPPED, None))
            if key not in found and drawn_ink_meets(
                path, half, grown, region, cp, filled=filled
            ):
                found.add(key)
        for key, xy, r in self.discs:
            region, cp = self.clips.get(key, (UNCLIPPED, None))
            if key not in found and discs_meet(xy, r, grown, region, cp):
                found.add(key)
        return Hits(len(found))


def _add_box(ink: Ink, artist: Artist, bb: Bbox | None) -> None:
    if bb is not None and bb.width > 0 and bb.height > 0:
        ink.boxes.append((id(artist), bb))


def _add_line(ink: Ink, line: Any, renderer: RendererBase) -> None:
    stroke, markers = line_draws_stroke(line), line_draws_markers(line)
    if not (stroke or markers):
        return
    try:
        path = line.get_transform().transform_path(line.get_path())
        ink.clip(line)
    except BBOX_ERRORS:
        return
    if stroke:
        half = px(renderer, line.get_linewidth()) / 2
        ink.strokes.append((id(line), path, half, False))
    if markers:
        xy = np.asarray(path.vertices, dtype=float).reshape(-1, 2)
        xy = xy[np.isfinite(xy).all(axis=1)]
        r = px(renderer, marker_radius_pt(line))
        ink.discs.append((id(line), xy, np.full(len(xy), r)))


def _add_collection(ink: Ink, coll: Any, renderer: RendererBase) -> None:
    try:
        if isinstance(coll, PathCollection) and len(coll.get_sizes()):
            xy, r = drawn_scatter_discs(coll, px(renderer, 1.0))
            if len(xy):
                ink.discs.append((id(coll), xy, r))
        else:
            stroked = isinstance(coll, LineCollection) or (
                isinstance(coll, ContourSet) and not coll.filled
            )
            for o in drawn_collection_outlines(coll, renderer):
                ink.strokes.append((id(coll), o.path, o.half, not stroked))
        ink.clip(coll)
    except BBOX_ERRORS:
        return


def data_ink(ax: Axes, renderer: RendererBase) -> Ink:
    """Lines, patches, collections (not meshes) and texts of ``ax`` and twins."""
    ink = Ink(px(renderer, CLEARANCE_PT))
    for owner in same_position_axes(ax):
        for line in owner.get_lines():
            _add_line(ink, line, renderer)
        for coll in owner.collections:
            if coll.get_visible() and not isinstance(coll, QuadMesh):
                _add_collection(ink, coll, renderer)
        for patch in owner.patches:
            with suppress(*BBOX_ERRORS):
                _add_box(ink, patch, drawn_patch_box(patch, renderer))
        for text in owner.texts:
            with suppress(*BBOX_ERRORS):
                _add_box(ink, text, drawn_text_box(text, renderer))
    return ink


# --------------------------------------------------------- trial legends
class Trials:
    """Trial legends of one set of handles: sizes and pad."""

    def __init__(
        self,
        parent: Axes | Figure | SubFigure,
        handles: Sequence[Any],
        entries: Entries,
        kw: dict[str, Any],
        renderer: RendererBase,
        loc: str = "upper right",
    ) -> None:
        """Build the 1-column trial that gives the pad."""
        self.parent, self.handles, self.renderer = (
            parent,
            list(handles),
            renderer,
        )
        self.kw = {k: v for k, v in kw.items() if k != "draggable"}
        self.kw.setdefault("loc", loc)  # never matplotlib's "best" search
        self.sizes: dict[tuple[Entries, Columns], Size] = {}
        self.base = self.trial(entries, Columns(1))
        em = px(renderer, float(self.base.prop.get_size_in_points()))
        self.pad = float(self.base.borderaxespad) * em

    def trial(self, entries: Entries, columns: Columns) -> Legend:
        """A detached legend of ``entries`` in ``columns`` (nothing drawn)."""
        owner = cast("Axes | Figure", self.parent)
        labels = list(entries.labels)
        return Legend(owner, self.handles, labels, ncols=columns.n, **self.kw)

    def size_of(self, entries: Entries, columns: Columns) -> Size:
        """The trial legend's size, measured once per entries and columns."""
        key = (entries, columns)
        if key not in self.sizes:
            try:
                bb = self.trial(entries, columns).get_window_extent(
                    self.renderer
                )
                self.sizes[key] = Size(float(bb.width), float(bb.height))
            except BBOX_ERRORS:
                self.sizes[key] = Size(float("inf"), float("inf"))
        return self.sizes[key]


# ----------------------------------------------------------------- sides
def _others(ax: Axes) -> list[Axes]:
    """The figure's other panels: drawn, in the layout, not ``ax``'s twins."""
    root = ax.get_figure(root=True)
    if root is None:
        return []
    own = {id(a) for a in same_position_axes(ax)}
    return [
        o
        for o in root.axes
        if id(o) not in own and drawn_in_tree(o) and o.get_in_layout()
    ]


def free_sides(ax: Axes) -> tuple[Side, ...]:
    """The fallback sides of ``ax`` no other panel sits beyond."""
    me, eps = root_position(ax), 1e-6
    others = [root_position(o) for o in _others(ax)]

    def blocked(side: Side) -> bool:
        for pos in others:
            across = min(pos.x1, me.x1) - max(pos.x0, me.x0) > eps
            along = min(pos.y1, me.y1) - max(pos.y0, me.y0) > eps
            if (
                (side is Side.ABOVE and pos.y0 >= me.y1 - eps and across)
                or (side is Side.BELOW and pos.y1 <= me.y0 + eps and across)
                or (side is Side.RIGHT and pos.x0 >= me.x1 - eps and along)
            ):
                return True
        return False

    return tuple(side for side in FALLBACK_SIDES if not blocked(side))


def _titles(ax: Axes, renderer: RendererBase) -> list[Bbox]:
    found: list[Bbox] = []
    for title in axes_titles(ax).values():
        if title.get_visible() and title.get_text().strip():
            try:
                found.append(title.get_window_extent(renderer))
            except BBOX_ERRORS:
                continue
    return found


def span(ax: Axes, side: Side, renderer: RendererBase, margin: float) -> Span:
    """Where a legend outside ``side`` may lie along it: the canvas less
    ``margin``, ended ``margin`` short of the panels beside ``ax``."""
    root = ax.get_figure(root=True)
    if root is None:
        return Span(-np.inf, np.inf)
    canvas = box_of(root.bbox)
    low, high = canvas.along(side)
    low, high = low + margin, high - margin
    try:
        me = box_of(ax.get_window_extent(renderer))
    except BBOX_ERRORS:
        return Span(low, high)
    for other in _others(ax):
        try:
            frame = other.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        ext = [
            box_of(e)
            for e in (
                frame,
                *axes_decoration_extents(other, renderer),
                *_titles(other, renderer),
            )
        ]
        f0, f1 = box_of(frame).along(side)
        m0, m1 = me.along(side)
        if f1 <= m0 + 0.5:
            low = max(low, max(e.along(side)[1] for e in ext) + margin)
        elif f0 >= m1 - 0.5:
            high = min(high, min(e.along(side)[0] for e in ext) - margin)
    return Span(float(low), float(high))


def decorations(ax: Axes, renderer: RendererBase) -> tuple[Box, ...]:
    """Tick labels, axis labels and offset texts of ``ax`` and its twins."""
    return tuple(
        box_of(ext)
        for owner in same_position_axes(ax)
        for ext in axes_decoration_extents(owner, renderer)
    )


# ----------------------------------------------------------------- facts
def legend_facts(
    ax: Axes,
    handles: Sequence[Any],
    entries: Entries,
    request: Request,
    kw: dict[str, Any],
    renderer: RendererBase,
    current: LegendPlan | None = None,
) -> LegendFacts:
    """What placing the legend of ``ax`` reads, at the size it has now."""
    trials = Trials(ax, handles, entries, kw, renderer)
    parent = Bbox(trials.base.get_bbox_to_anchor().get_points())
    return LegendFacts(
        request=request,
        entries=entries,
        axes=box_of(ax.get_window_extent(renderer)),
        parent=box_of(parent),
        pad=trials.pad,
        free_sides=free_sides(ax),
        size_of=trials.size_of,
        meets=data_ink(ax, renderer).meets,
        span_of=lambda side: span(ax, side, renderer, trials.pad),
        current=current,
    )


def anchor_facts(ax: Axes, side: Side, renderer: RendererBase) -> AnchorFacts:
    """An outside legend against ``side`` of ``ax``: the labels beyond it."""
    return AnchorFacts(
        side=side,
        axes=box_of(ax.get_window_extent(renderer)),
        decorations=decorations(ax, renderer),
    )


def title_facts(ax: Axes, renderer: RendererBase) -> TitleFacts | None:
    """The drawn titles of ``ax`` and the legends of it and its twins above it."""
    root = ax.get_figure(root=True)
    try:
        top = ax.get_window_extent(renderer).y1
    except BBOX_ERRORS:
        return None
    titles: list[TitleBox] = []
    for title in axes_titles(ax).values():
        if not (title.get_visible() and title.get_text().strip()):
            continue
        try:
            ext = title.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        pos = title.get_position()
        base = float(ax.transAxes.transform(pos)[1])
        pad = float(title.get_transform().transform(pos)[1]) - base
        titles.append(TitleBox(box_of(ext), base, pad))
    above: list[Box] = []
    for owner in same_position_axes(ax):
        legend = owner.get_legend()
        if legend is None or not legend.get_visible():
            continue
        try:
            ext = legend.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if ext.width > 0 and ext.height > 0 and (ext.y0 + ext.y1) / 2 > top:
            above.append(box_of(ext))
    if root is None or not titles or not above:
        return None
    gap = float(mpl.rcParams["axes.titlepad"]) * root.dpi / 72.0
    return TitleFacts(tuple(titles), tuple(above), gap)


def figure_facts(
    fig: Figure | SubFigure,
    handles: Sequence[Any],
    entries: Entries,
    request: Request,
    kw: dict[str, Any],
    renderer: RendererBase,
) -> FigureFacts:
    """What placing a figure legend reads: its sizes."""
    trials = Trials(fig, handles, entries, kw, renderer, loc="upper center")
    return FigureFacts(
        side=request.side,
        columns=request.columns,
        entries=entries,
        figure=box_of(fig.bbox),
        pad=trials.pad,
        size_of=trials.size_of,
    )


def entry_facts(
    owners: Sequence[Axes], focus: Axes
) -> tuple[EntryFacts, list[list[Any]]]:
    """Each twin's labelled artists, draw order and current legend."""
    parent = focus.get_figure(root=False)
    order = list(parent.axes) if parent is not None else list(owners)
    found: list[Owner] = []
    handles: list[list[Any]] = []
    for owner in owners:
        hs, labels = owner.get_legend_handles_labels()
        legend = owner.get_legend()
        texts = (
            None
            if legend is None
            else Entries(tuple(t.get_text() for t in legend.get_texts()))
        )
        rank = (
            float(owner.get_zorder()),
            order.index(owner) if owner in order else -1,
        )
        found.append(Owner(Entries(tuple(labels)), rank, texts))
        handles.append(list(hs))
    return EntryFacts(tuple(found), list(owners).index(focus)), handles
