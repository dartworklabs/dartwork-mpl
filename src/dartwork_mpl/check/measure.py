"""Read the facts the rules judge from a figure: draw once, measure, touch nothing.

The figure is drawn on its own canvas so every position is current, and once
more into a private Agg buffer to read the colour under each text. No artist
is changed, hidden or moved.
"""

from __future__ import annotations

from contextlib import suppress
from itertools import pairwise
from typing import TYPE_CHECKING, Any

import numpy as np
from matplotlib.category import StrCategoryFormatter
from matplotlib.text import Annotation
from matplotlib.ticker import FixedFormatter, FixedLocator, FuncFormatter
from matplotlib.transforms import Bbox

from ..geometry import (
    BBOX_ERRORS,
    axes_titles,
    drawn_in_tree,
    drawn_tick_labels,
    figure_axes,
    figure_legends,
    get_renderer,
    iter_figure_level_extents,
    same_position_axes,
    shared_axes,
    text_inks,
)
from . import walk
from .ink import (
    Ink,
    cut,
    data_ink,
    legend_inks,
    plain_label,
    text_contrast,
    words_box,
)
from .model import (
    AXES,
    Axis,
    Box,
    Corner,
    Facts,
    Hit,
    Legend,
    Panel,
    Role,
    Text,
    TickRow,
    ValueLabel,
    flat,
)
from .overlap import (
    corner_tick_overlaps,
    label_clearance_px,
    pair_clearance_px,
    pair_gap_px,
    tick_label_overlaps,
)
from .walk import reads_as_axes

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.legend import Legend as MplLegend

_BOLD = {"bold", "heavy", "black", "extra bold", "semibold", "demibold"}


def box_of(bb: Bbox) -> Box:
    """A matplotlib ``Bbox`` as a :class:`Box`."""
    return Box(float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1))


class Reader:
    """One figure being measured: its renderer, scale and what failed."""

    def __init__(self, fig: Figure) -> None:
        """Draw ``fig`` once so every position is current."""
        self.fig = fig
        fig.canvas.draw()  # pyright: ignore[reportUnknownMemberType]
        self.renderer: RendererBase = get_renderer(fig)
        self.pt = fig.dpi / 72.0
        self.skipped: list[str] = []
        self.panels = walk.drawn_axes(fig)
        self.letters = {id(t) for _ax, t in walk.panel_labels(fig)}

    def text(self, t: Any, role: Role, panel: int | None) -> Text | None:
        """A drawn, non-blank text as a fact; ``None`` when it has no box."""
        if not drawn_in_tree(t) or not t.get_text().strip():
            return None
        try:
            if isinstance(t, Annotation):
                bb = words_box(t, self.renderer)
            else:
                bb = walk.text_window_extent(t, self.renderer)
        except BBOX_ERRORS:
            return None
        if bb is None or not np.isfinite(bb.extents).all():
            return None
        if bb.width <= 0 or bb.height <= 0:
            return None
        em = float(t.get_fontsize()) * self.pt
        return Text(t, t.get_text(), role, panel, box_of(bb), em)

    # ------------------------------------------------------------ texts
    def axes_texts(self) -> tuple[Text, ...]:
        """Titles, axis labels and texts of every Axes (a secondary axis'
        and a polar or 3D Axes' tick labels too: they have no tick row)."""
        found: list[Text | None] = []
        for i, ax in self.panels:
            for owner in (ax, *walk.secondary_axes(ax)):
                titles = {id(t) for t in axes_titles(owner).values()}
                labels = {id(owner.xaxis.label), id(owner.yaxis.label)}
                for t in walk.drawn_axes_texts(owner):
                    role = (
                        Role.TITLE
                        if id(t) in titles
                        else Role.AXIS_LABEL
                        if id(t) in labels
                        else Role.PANEL_LETTER
                        if id(t) in self.letters
                        else Role.TEXT
                    )
                    found.append(self.text(t, role, i))
                if not flat(owner.name) or owner is not ax:
                    found.extend(
                        self.text(t, Role.TICK, i)
                        for axis in AXES
                        for t in drawn_tick_labels(owner, axis.mpl)
                    )
        return tuple(t for t in found if t is not None)

    def figure_texts(self) -> tuple[Text, ...]:
        """Suptitles, sup-labels and ``fig.text``, of SubFigures too."""
        found = [
            self.text(t, Role.FIGURE_TEXT, None)
            for t, _ext in iter_figure_level_extents(
                self.fig, self.renderer, legends=False
            )
        ]
        return tuple(t for t in found if t is not None)

    # ------------------------------------------------------------ ticks
    def _sup_label(self, ax: Axes, which: Axis) -> bool:
        fig = ax.get_figure(root=False)
        sup = getattr(fig, which.pick("_supxlabel", "_supylabel"), None)
        return bool(
            sup is not None and sup.get_visible() and sup.get_text().strip()
        )

    def tick_row(self, i: int, ax: Axes, which: Axis) -> TickRow | None:
        """One axis' drawn major labels and what they need along it."""
        axis = which.pick(ax.xaxis, ax.yaxis)
        drawn = [
            t for t in drawn_tick_labels(ax, which.mpl) if t.get_text().strip()
        ]
        first = {id(tick.label1) for tick in axis.get_major_ticks()}
        rows = [
            [t for t in drawn if id(t) in first],
            [t for t in drawn if id(t) not in first],
        ]
        labels = tuple(
            x
            for x in (self.text(t, Role.TICK, i) for t in rows[0] + rows[1])
            if x
        )
        if not labels:
            return None
        frame = ax.get_window_extent(self.renderer)
        span = which.pick(frame.width, frame.height)
        r = self.renderer

        def centre(t: Any) -> float:
            b = t.get_window_extent(r)
            return float(which.pick(b.x0 + b.x1, b.y0 + b.y1))

        need: float | None = 0.0
        closest: float | None = None
        try:
            for row in rows:
                ordered = sorted(row, key=centre)
                if not ordered:
                    continue
                need += 0.5 * (
                    label_clearance_px(ordered[0], r, which)
                    + label_clearance_px(ordered[-1], r, which)
                )
                for a, b in pairwise(ordered):
                    need += pair_clearance_px(a, b, r, which)
                    size = max(float(a.get_fontsize()), float(b.get_fontsize()))
                    em = size * self.pt
                    gap = pair_gap_px(a, b, r) / em
                    closest = gap if closest is None else min(closest, gap)
        except BBOX_ERRORS:
            need = None
        overlaps = tick_label_overlaps(ax, which, r)
        formatter = axis.get_major_formatter()
        names = isinstance(
            formatter, FixedFormatter | StrCategoryFormatter
        ) or (
            isinstance(formatter, FuncFormatter)
            and isinstance(axis.get_major_locator(), FixedLocator)
        )
        twins = [a for a in shared_axes(ax, which.mpl) if a is not ax]
        return TickRow(
            handle=ax,
            panel=i,
            axis=which,
            labels=labels,
            span=float(span),
            need=need,
            closest=closest,
            overlaps=overlaps.pairs,
            deepest=float(overlaps.deepest),
            names=names,
            labelled=bool(
                axis.label.get_visible() and axis.label.get_text().strip()
            ),
            labelled_elsewhere=self._sup_label(ax, which)
            or any(
                which.pick(a.xaxis, a.yaxis).label.get_text().strip()
                for a in twins
            ),
        )

    def ticks(self) -> tuple[tuple[TickRow, ...], tuple[Corner, ...]]:
        """Tick rows of rectilinear Axes, and tick labels meeting at corners."""
        rows: list[TickRow] = []
        corners: list[Corner] = []
        seen: set[int] = set()
        for i, ax in self.panels:
            if not flat(ax.name):
                continue
            for which in AXES:
                row = self.tick_row(i, ax, which)
                if row is not None:
                    rows.append(row)
            if id(ax) in seen:
                continue
            group = [a for a in same_position_axes(ax) if flat(a.name)]
            seen.update(id(a) for a in group)
            pairs = corner_tick_overlaps(group, self.renderer)
            if pairs:
                deep = max(pairs, key=lambda p: p.depth)
                x, y = (
                    self.text(deep.x_label, Role.TICK, i),
                    self.text(deep.y_label, Role.TICK, i),
                )
                if x and y:
                    corners.append(
                        Corner(
                            i, len(pairs), float(deep.depth), x, y, deep.corner
                        )
                    )
        return tuple(rows), tuple(corners)

    # ----------------------------------------------------------- legends
    def _owners(self) -> list[tuple[int, Axes]]:
        """Every drawn Axes with its ``fig.axes`` index, insets after their parent."""
        found: list[tuple[int, Axes]] = []

        def walk(i: int, ax: Axes) -> None:
            if drawn_in_tree(ax):
                found.append((i, ax))
                for child in ax.child_axes:
                    if reads_as_axes(child):
                        walk(i, child)

        for i, ax in enumerate(self.fig.axes):
            walk(i, ax)
        return found

    def _plots(self) -> list[tuple[int, list[Axes], Bbox]]:
        """One entry per rectilinear plot box; twins share it."""
        seen: set[int] = set()
        plots: list[tuple[int, list[Axes], Bbox]] = []
        for i, ax in self._owners():
            if not flat(ax.name) or id(ax) in seen:
                continue
            group = same_position_axes(ax)
            seen.update(id(a) for a in group)
            plots.append((i, group, ax.get_window_extent(self.renderer)))
        return plots

    def legends(self) -> tuple[Legend, ...]:
        """Every drawn legend and what its box covers."""
        held: list[tuple[int | None, Axes | None, MplLegend | None]] = [
            (i, ax, ax.get_legend()) for i, ax in self._owners()
        ]
        held += [(None, None, leg) for leg in figure_legends(self.fig)]
        placed = [
            (i, ax, leg, leg.get_window_extent(self.renderer))
            for i, ax, leg in held
            if leg is not None and drawn_in_tree(leg)
        ]
        placed = [p for p in placed if legend_inks(p[2]) and p[3].width > 0]
        if not placed:
            return ()
        plots = self._plots()
        inks: dict[int, Ink] = {}
        texts = [
            (t, words_box(t, self.renderer))
            for _i, ax in self._owners()
            for t in ax.texts
            if drawn_in_tree(t) and text_inks(t) and t.get_text().strip()
        ]
        touch = 0.5 * self.pt
        found: list[Legend] = []
        for i, ax, leg, bb in placed:
            own: set[int] = (
                {id(a) for a in same_position_axes(ax)}
                if ax is not None
                else set()
            )
            frame = (
                ax.get_window_extent(self.renderer) if ax is not None else None
            )
            inside = frame is not None and cut(bb, frame) == bb
            covers: list[Hit] = []
            for k, (j, group, plot) in enumerate(plots):
                if cut(bb.padded(-touch), plot) is None:
                    continue
                mine = bool(own & {id(a) for a in group})
                if (
                    not mine
                    and inside
                    and frame is not None
                    and cut(frame, plot) == frame
                ):
                    continue  # an inset's legend over the panel it sits on
                if ax is not None and not mine:
                    covers.append(Hit("panel", f"axes[{j}]"))
                if k not in inks:
                    inks[k] = data_ink(
                        group, plot, self.renderer, self.pt, areas=True
                    )
                covers += inks[k].meets(bb, touch)
            for t, tb in texts:
                if tb is not None and cut(bb.padded(-touch), tb) is not None:
                    covers.append(Hit("text", t.get_text().strip()[:30]))
            for _j, _a, other, ob in placed:
                if other is not leg and cut(bb.padded(-touch), ob) is not None:
                    covers.append(Hit("legend", "another legend"))
            if ax is None:
                sub = leg.get_figure(root=False) or self.fig
                area = sum(
                    a.get_window_extent(self.renderer).width
                    * a.get_window_extent(self.renderer).height
                    for a in figure_axes(sub)
                    if drawn_in_tree(a) and same_position_axes(a)[0] is a
                )
            else:
                area = 0.0
            found.append(
                Legend(
                    handle=leg,
                    panel=i,
                    box=box_of(bb),
                    labels=tuple(t.get_text()[:30] for t in leg.get_texts()),
                    plot=box_of(frame) if frame is not None else None,
                    panels_area=float(area),
                    covers=tuple(dict.fromkeys(covers)),
                )
            )
        return tuple(found)

    # ------------------------------------------------------ value labels
    def values(self, texts: tuple[Text, ...]) -> tuple[ValueLabel, ...]:
        """Value labels of rectilinear Axes and the data their box covers."""
        found: list[ValueLabel] = []
        inks: dict[int, Ink] = {}
        touch = 0.5 * self.pt
        for t in texts:
            if not t.role.free or t.number is None or t.panel is None:
                continue
            ax = getattr(t.handle, "axes", None)
            if ax is None or not flat(ax.name) or not plain_label(t.handle, ax):
                continue
            if id(ax) not in inks:
                frame = ax.get_window_extent(self.renderer)
                inks[id(ax)] = data_ink(
                    same_position_axes(ax),
                    frame,
                    self.renderer,
                    self.pt,
                    areas=False,
                )
            bb = Bbox.from_extents(t.box.x0, t.box.y0, t.box.x1, t.box.y1)
            hits = inks[id(ax)].meets(bb, touch, label=bb)
            found.append(ValueLabel(t, tuple(hits)))
        return tuple(found)

    # ----------------------------------------------------------- panels
    def panel_facts(self) -> tuple[Panel, ...]:
        """Every drawn Axes and whether it draws anything."""
        found: list[Panel] = []
        for i, ax in self.panels:
            drawn = any(
                a.get_visible()
                for group in (
                    ax.lines,
                    ax.patches,
                    ax.collections,
                    ax.images,
                    ax.tables,
                )
                for a in group
            )
            leg = ax.get_legend()
            drawn |= leg is not None and leg.get_visible()
            drawn |= any(
                t.get_visible() and t.get_text().strip() for t in ax.texts
            )
            box = box_of(ax.get_window_extent(self.renderer))
            found.append(Panel(ax, i, box, not drawn))
        return tuple(found)

    def content(self) -> Box | None:
        """The box around everything drawn, ``None`` with no Axes."""
        boxes: list[Bbox] = []
        for _i, ax in self.panels:
            with suppress(*BBOX_ERRORS):
                tb = ax.get_tightbbox(self.renderer)
                if tb is not None:
                    boxes.append(tb)
            for t in ax.texts:
                if t.get_visible() and t.get_text().strip():
                    with suppress(*BBOX_ERRORS):
                        boxes.append(t.get_window_extent(self.renderer))
        if not boxes:
            return None
        boxes += [
            ext
            for _a, ext in iter_figure_level_extents(self.fig, self.renderer)
        ]
        return box_of(Bbox.union(boxes))


def measure(fig: Figure) -> Facts:
    """Every fact the rules read, from one draw of ``fig``."""
    r = Reader(fig)
    sections: dict[str, Any] = {}
    for name, read, rules in (
        ("texts", r.axes_texts, "OVERFLOW, TEXT_AT_EDGE, OVERLAP"),
        ("figure_texts", r.figure_texts, "OVERFLOW, TEXT_AT_EDGE"),
        ("ticks", r.ticks, "TICK_*"),
        ("legends", r.legends, "LEGEND_*"),
        ("panels", r.panel_facts, "EMPTY_AXES"),
        ("content", r.content, "MARGIN_ASYMMETRY"),
    ):
        try:
            sections[name] = read()
        except BBOX_ERRORS:
            r.skipped.append(rules)
    texts = sections.get("texts", ())
    rows, corners = sections.get("ticks", ((), ()))
    try:
        values = r.values(texts)
    except BBOX_ERRORS:
        values = ()
        r.skipped.append("VALUE_LABEL_ON_DATA")
    every = (
        texts
        + tuple(t for row in rows for t in row.labels)
        + sections.get("figure_texts", ())
    )
    try:
        contrast = text_contrast(fig, every)
    except BBOX_ERRORS:
        contrast = ()
        r.skipped.append("TEXT_CONTRAST")
    return Facts(
        canvas=box_of(Bbox(fig.bbox.get_points())),
        px_per_pt=r.pt,
        texts=texts,
        figure_texts=sections.get("figure_texts", ()),
        ticks=rows,
        corners=corners,
        legends=sections.get("legends", ()),
        values=values,
        contrast=contrast,
        panels=sections.get("panels", ()),
        content=sections.get("content"),
        skipped=tuple(r.skipped),
    )
