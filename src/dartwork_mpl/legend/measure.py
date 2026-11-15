"""Read the facts a legend decision needs from a figure drawn once.

A trial legend is a detached ``Legend`` built only to read its size, so
trying a spot or a column count draws nothing. Data ink is read by the drawn
rules ``check`` shares (``geometry.ink``): lines at their width, markers
and scatter points as discs, patches and texts by their drawn boxes, filled
collections by their outlines, each only where its clip lets it draw.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import matplotlib as mpl
import numpy as np
from matplotlib.legend import Legend
from matplotlib.transforms import Bbox, BboxBase

from ..geometry import (
    BBOX_ERRORS,
    axes_titles,
    drawn_in_tree,
    same_position_axes,
)
from .boxes import Box, Entries, Size, Span
from .ink import box_of, data_ink, px
from .model import (
    Columns,
    Inherit,
    LabelColourWord,
    LegendStyle,
    LocName,
    Request,
    trial_keywords,
)
from .plans import (
    AnchorFacts,
    EntryFacts,
    FigureFacts,
    LegendFacts,
    LegendPlan,
    Owner,
    TitleBox,
    TitleFacts,
)
from .sides import FALLBACK_SIDES, Side

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.font_manager import FontProperties
    from matplotlib.legend_handler import HandlerBase
    from matplotlib.text import Text
    from matplotlib.transforms import Transform
    from matplotlib.typing import ColorType


class LegendKeywords(LegendStyle, total=False):
    """:class:`LegendStyle` and the keywords whose values are matplotlib's."""

    prop: FontProperties | dict[str, object] | None
    title_fontproperties: FontProperties | dict[str, object] | None
    labelcolor: ColorType | Sequence[ColorType] | LabelColourWord | None
    edgecolor: ColorType | Inherit | None
    facecolor: ColorType | Inherit | None
    bbox_to_anchor: (
        BboxBase
        | tuple[float, float]
        | tuple[float, float, float, float]
        | None
    )
    bbox_transform: Transform | None
    handler_map: dict[Artist | type, HandlerBase] | None


# --------------------------------------------------------- trial legends
class Trials:
    """Trial legends of one set of handles: sizes and pad."""

    def __init__(
        self,
        parent: Axes | Figure,
        handles: Sequence[Artist],
        entries: Entries,
        kw: LegendKeywords,
        renderer: RendererBase,
        loc: LocName = "upper right",
    ) -> None:
        """Build the 1-column trial that gives the pad."""
        self.parent, self.handles, self.renderer = (
            parent,
            list(handles),
            renderer,
        )
        self.kw = trial_keywords(kw)
        self.loc: LocName = loc  # never matplotlib's "best" search
        self.sizes: dict[tuple[Entries, Columns], Size] = {}
        self.base = self.trial(entries, Columns(1))
        em = px(renderer, float(self.base.prop.get_size_in_points()))
        self.pad = float(self.base.borderaxespad) * em

    def trial(self, entries: Entries, columns: Columns) -> Legend:
        """A detached legend of ``entries`` in ``columns`` (nothing drawn)."""
        labels = list(entries.labels)
        return Legend(
            self.parent,
            self.handles,
            labels,
            loc=self.loc,
            ncols=columns.n,
            **self.kw,
        )

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
def _root_position(ax: Axes) -> Bbox:
    """``ax.get_position()`` as a fraction of the root Figure, through its SubFigure."""
    position = ax.get_position()
    parent = ax.get_figure(root=False)
    root = ax.get_figure(root=True)
    if parent is None or root is None or parent is root:
        return position
    return position.transformed(parent.transSubfigure).transformed(
        root.transFigure.inverted()
    )


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
    me, eps = box_of(_root_position(ax)), 1e-6
    others = [box_of(_root_position(o)) for o in _others(ax)]
    return tuple(
        side
        for side in FALLBACK_SIDES
        if not any(me.behind(side, pos, eps) for pos in others)
    )


def _titles(ax: Axes, renderer: RendererBase) -> list[Bbox]:
    found: list[Bbox] = []
    for title in axes_titles(ax).values():
        if title.get_visible() and title.get_text().strip():
            try:
                found.append(title.get_window_extent(renderer))
            except BBOX_ERRORS:
                continue
    return found


def _decoration_extents(ax: Axes, renderer: RendererBase) -> list[Bbox]:
    """Window extents of ``ax``'s in-view tick labels (major and minor), axis
    labels and offset texts (``1e6``) on visible axes; titles, ``ax.texts``
    and legends are not included. An out-of-view tick stays on the artist
    tree undrawn; it and blank, hidden, unmeasurable or empty texts are
    skipped.
    """
    texts: list[Text] = []
    for axis, index in ((ax.xaxis, 0), (ax.yaxis, 1)):
        if not axis.get_visible():
            continue
        vmin, vmax = sorted(axis.get_view_interval())
        tol = abs(vmax - vmin) * 1e-5
        for tick in axis.get_ticklabels(which="both"):
            value = tick.get_position()[index]
            if vmin - tol <= value <= vmax + tol:
                texts.append(tick)
        texts.extend((axis.label, axis.get_offset_text()))
    extents: list[Bbox] = []
    for text in texts:
        if not text.get_visible() or not text.get_text().strip():
            continue
        try:
            ext = text.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if ext.width > 0 and ext.height > 0:
            extents.append(ext)
    return extents


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
                *_decoration_extents(other, renderer),
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
        for ext in _decoration_extents(owner, renderer)
    )


# ----------------------------------------------------------------- facts
def legend_facts(
    ax: Axes,
    handles: Sequence[Artist],
    entries: Entries,
    request: Request,
    kw: LegendKeywords,
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
    handles: Sequence[Artist],
    entries: Entries,
    request: Request,
    kw: LegendKeywords,
    renderer: RendererBase,
) -> FigureFacts:
    """What placing a figure legend reads: its sizes.

    The trials hang on the root figure: a trial is never drawn, its size
    is the same under a SubFigure of it, and matplotlib types a
    ``Legend``'s parent as an Axes or a Figure only.
    """
    root = fig.get_figure(root=True)
    trials = Trials(root, handles, entries, kw, renderer, loc="upper center")
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
) -> tuple[EntryFacts, list[list[Artist]]]:
    """Each twin's labelled artists, draw order and current legend."""
    parent = focus.get_figure(root=False)
    order = list(parent.axes) if parent is not None else list(owners)
    found: list[Owner] = []
    handles: list[list[Artist]] = []
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
