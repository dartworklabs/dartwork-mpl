"""Read the facts the rules judge from a figure: draw once, measure, touch nothing.

The figure is drawn on its own canvas so every position is current. No
artist is changed, hidden or moved.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent
from matplotlib.category import StrCategoryFormatter
from matplotlib.collections import Collection, PathCollection
from matplotlib.colors import to_rgba
from matplotlib.dates import DateLocator
from matplotlib.image import AxesImage
from matplotlib.patches import Patch
from matplotlib.text import Annotation
from matplotlib.text import Text as MplText
from matplotlib.ticker import FixedFormatter, FixedLocator, FuncFormatter
from matplotlib.transforms import Bbox

from ..colorspace import Rgb, Rgba, composite_over, contrast
from ..geometry import (
    BBOX_ERRORS,
    axes_titles,
    drawn_in_tree,
    drawn_tick_labels,
    draws_axis,
    figure_legends,
    get_renderer,
    iter_figure_level_extents,
    panel_letters,
    projection,
    same_position_axes,
    shared_axes,
)
from ..vocab import Which
from . import roles
from .ink import Ink, data_ink, legend_inks, words_box
from .model import (
    AXES,
    Box,
    Facts,
    Frame,
    Hit,
    Inked,
    Legend,
    OnData,
    Panel,
    Text,
    TickRow,
)
from .overlap import tick_label_overlaps

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.gridspec import SubplotSpec
    from matplotlib.legend import Legend as MplLegend

T = TypeVar("T")


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
        self.axes = [
            (i, ax) for i, ax in enumerate(fig.axes) if drawn_in_tree(ax)
        ]
        self.panels = [(i, ax) for i, ax in self.axes if projection(ax).flat]
        self.letters = {id(t) for _ax, t in panel_letters(fig)}

    def text(
        self, t: MplText, role: roles.Role, panel: int | None
    ) -> Text | None:
        """A drawn, non-blank text as a fact; ``None`` when it has no box."""
        if not drawn_in_tree(t) or not t.get_text().strip():
            return None
        try:
            if isinstance(t, Annotation):
                bb = words_box(t, self.renderer)
            else:
                bb = t.get_window_extent(self.renderer)
        except BBOX_ERRORS:
            return None
        if bb is None or not np.isfinite(bb.extents).all():
            return None
        if bb.width <= 0 or bb.height <= 0:
            return None
        em = float(t.get_fontsize()) * self.pt
        return Text(t, t.get_text(), role, panel, box_of(bb), em)

    def attempt(self, read: Callable[[], T], failed: T, rules: str) -> T:
        """``read()``; ``failed`` when a box cannot be read, the rules it
        feeds then listed as skipped."""
        try:
            return read()
        except BBOX_ERRORS:
            self.skipped.append(rules)
            return failed

    def axes_texts(self) -> tuple[Text, ...]:
        """Titles, drawn axis labels and texts of every rectilinear Axes."""
        found: list[Text | None] = []
        for i, ax in self.panels:
            titles = axes_titles(ax).values()
            labels = [
                a.label for a in (ax.xaxis, ax.yaxis) if draws_axis(ax, a)
            ]
            found += [self.text(t, roles.Title(), i) for t in titles]
            found += [self.text(t, roles.AxisLabel(), i) for t in labels]
            found += [
                self.text(
                    t,
                    roles.PanelLetter()
                    if id(t) in self.letters
                    else roles.FreeText(),
                    i,
                )
                for t in ax.texts
            ]
        return tuple(t for t in found if t is not None)

    def figure_texts(self) -> tuple[Text, ...]:
        """Suptitles, sup-labels and ``fig.text``, of SubFigures too."""
        found = [
            self.text(t, roles.FigureText(), None)
            for t, _ext in iter_figure_level_extents(
                self.fig, self.renderer, legends=False
            )
            if isinstance(t, MplText)
        ]
        return tuple(t for t in found if t is not None)

    def legend_texts(self) -> tuple[Text, ...]:
        """The entries of every drawn legend (only the canvas edge judges
        them)."""
        found = [
            self.text(t, roles.FigureText(), None)
            for _i, leg, _axes in self.drawn_legends()
            for t in leg.get_texts()
        ]
        return tuple(t for t in found if t is not None)

    def tick_row(self, i: int, ax: Axes, which: Which) -> TickRow | None:
        """One axis' drawn major labels and how many neighbours collide."""
        labels = tuple(
            x
            for x in (
                self.text(t, roles.TickLabel(), i)
                for t in drawn_tick_labels(ax, which)
            )
            if x
        )
        if not labels:
            return None
        pairs, deepest = tick_label_overlaps(ax, which, self.renderer)
        axis = which.pick(ax.xaxis, ax.yaxis)
        formatter, locator = (
            axis.get_major_formatter(),
            axis.get_major_locator(),
        )
        names = isinstance(
            formatter, FixedFormatter | StrCategoryFormatter
        ) or (
            isinstance(formatter, FuncFormatter)
            and isinstance(locator, FixedLocator)
        )  # set_xticks(ticks, labels) prints names
        numbers = not names and not isinstance(locator, DateLocator)
        return TickRow(
            ax,
            i,
            which,
            labels,
            pairs,
            float(deepest),
            numbers=numbers and any(t.value for t in labels),
            named=named(ax, which),
        )

    def ticks(self) -> tuple[TickRow, ...]:
        """Tick rows of rectilinear Axes."""
        return tuple(
            row
            for i, ax in self.panels
            for which in AXES
            if (row := self.tick_row(i, ax, which)) is not None
        )

    def drawn_legends(self) -> list[tuple[int | None, MplLegend, list[Axes]]]:
        """Every drawn legend, its panel and the Axes whose data it explains:
        its own and their twins, every rectilinear one for a figure legend."""
        held: list[tuple[int | None, MplLegend | None, list[Axes]]] = [
            (i, ax.get_legend(), same_position_axes(ax)) for i, ax in self.axes
        ]
        every = [ax for _i, ax in self.panels]
        held += [(None, leg, every) for leg in figure_legends(self.fig)]
        return [
            (i, leg, axes)
            for i, leg, axes in held
            if leg is not None and drawn_in_tree(leg) and legend_inks(leg)
        ]

    def legends(self) -> tuple[Legend, ...]:
        """Every drawn legend and the data its box covers."""
        touch = 0.5 * self.pt
        found: list[Legend] = []
        for i, leg, axes in self.drawn_legends():
            box = leg.get_window_extent(self.renderer)
            covers: list[Hit] = []
            for ax in axes:
                if not projection(ax).flat:
                    continue
                frame = ax.get_window_extent(self.renderer)
                ink = data_ink([ax], frame, self.renderer, self.pt)
                covers += ink.meets(box, touch)
            found.append(
                Legend(
                    handle=leg,
                    panel=i,
                    labels=tuple(t.get_text()[:30] for t in leg.get_texts()),
                    covers=tuple(dict.fromkeys(covers)),
                    box=box_of(box),
                )
            )
        return tuple(found)

    def values(self, texts: tuple[Text, ...]) -> tuple[OnData, ...]:
        """Value labels and the lines, markers and error bars they cover (a
        label inside its bar or area is on purpose)."""
        found: list[OnData] = []
        inks: dict[int, Ink] = {}
        for t in texts:
            ax = t.handle.axes if isinstance(t.handle, MplText) else None
            if not (t.role.free and t.value and isinstance(ax, Axes)):
                continue
            if id(ax) not in inks:
                frame = ax.get_window_extent(self.renderer)
                inks[id(ax)] = data_ink(
                    same_position_axes(ax), frame, self.renderer, self.pt
                )
            box = Bbox.from_extents(t.box.x0, t.box.y0, t.box.x1, t.box.y1)
            hits = inks[id(ax)].meets(box, 0.5 * self.pt)
            if strokes := tuple(h for h in hits if h.stroke):
                found.append(OnData(t, strokes))
        return tuple(found)

    def inks(self, texts: tuple[Text, ...]) -> tuple[Inked, ...]:
        """Texts the user placed in an Axes, against what is behind them."""
        found: list[Inked] = []
        for t in texts:
            h = t.handle
            if t.role.free and isinstance(h, MplText):
                b = t.box
                paper = backdrop(h, (b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2)
                rgba = to_rgba(h.get_color(), h.get_alpha())
                ink = composite_over(Rgba.of(rgba), paper)
                found.append(
                    Inked(t, ink.hex(), paper.hex(), contrast(ink, paper))
                )
        return tuple(found)

    def empty(self) -> tuple[Panel, ...]:
        """Framed Axes where nothing is drawn, nor in a twin sharing the box."""
        return tuple(
            Panel(ax, i)
            for i, ax in self.panels
            if ax.axison and not any(map(draws, same_position_axes(ax)))
        )

    def frames(self) -> tuple[Frame, ...]:
        """The plot area of every flat Axes."""
        return tuple(
            Frame(ax, i, box_of(ax.get_window_extent(self.renderer)))
            for i, ax in self.panels
        )


def named(ax: Axes, which: Which) -> bool:
    """A label names ``ax``'s axis: its own, one of an Axes sharing it or
    in its grid row (y) or column (x), or the figure's sup label."""
    fig = ax.get_figure(root=False)
    spec = ax.get_subplotspec()
    if fig is None:
        return False

    def line(s: SubplotSpec) -> range:
        return which.pick(s.colspan, s.rowspan)

    grid = [
        other
        for other in fig.axes
        if spec is not None
        and (s := other.get_subplotspec()) is not None
        and s.get_gridspec() is spec.get_gridspec()
        and line(s) == line(spec)
    ]
    sup = which.pick(fig.get_supxlabel(), fig.get_supylabel())
    return bool(sup.strip()) or any(
        which.pick(o.xaxis, o.yaxis).label.get_text().strip()
        for o in (*shared_axes(ax, which), *grid)
    )


def backdrop(text: MplText, x: float, y: float) -> Rgb:
    """The colour drawn behind ``(x, y)`` (px) under ``text``: the figure,
    its Axes, then every patch, filled collection and image cell below the
    text in draw order, and the text's own box."""
    fig, ax = text.get_figure(root=True), text.axes
    layers: list[Artist] = [fig.patch] if fig else []
    inside = ax is not None and ax.get_window_extent().contains(x, y)
    if ax is not None and inside:
        layers += [ax.patch] if ax.axison and ax.get_frame_on() else []
        layers += sorted(
            (
                a
                for a in (*ax.patches, *ax.collections, *ax.images)
                if a.get_visible() and a.get_zorder() <= text.get_zorder()
            ),
            key=lambda a: a.get_zorder(),
        )
    layers += [b] if (b := text.get_bbox_patch()) else []
    paper = Rgb(1.0, 1.0, 1.0)
    for a in layers:
        if (colour := colour_at(a, x, y)) is not None:
            paper = composite_over(Rgba.of(colour), paper)
    return paper


def colour_at(a: Artist, x: float, y: float) -> tuple[float, ...] | None:
    """The RGBA ``a`` paints at ``(x, y)`` px, ``None`` where it paints
    nothing (a scatter's markers are not read)."""
    if isinstance(a, Patch):
        return to_rgba(a.get_facecolor()) if a.contains_point((x, y)) else None
    if isinstance(a, AxesImage):
        fig = a.get_figure(root=True)
        event = MouseEvent("", fig.canvas, round(x), round(y)) if fig else None
        value = a.get_cursor_data(event) if event else None
        if value is None or np.ma.is_masked(value) or np.ndim(value):
            return None
        rgba = a.to_rgba(np.asarray(value), alpha=a.get_alpha())
        return tuple(float(c) for c in np.ravel(rgba))
    if isinstance(a, Collection) and not isinstance(a, PathCollection):
        faces = np.asarray(a.get_facecolor(), dtype=float).reshape(-1, 4)
        hit = [
            i
            for i, p in enumerate(a.get_paths())
            if p.contains_point((x, y), transform=a.get_transform())
        ]
        return (
            tuple(faces[hit[-1] % len(faces)]) if hit and len(faces) else None
        )
    return None


def draws(ax: Axes) -> bool:
    """``ax`` draws data, a text or a legend."""
    drawn = (*ax.lines, *ax.patches, *ax.collections, *ax.images, *ax.tables)
    texts = (t for t in ax.texts if t.get_text().strip())
    return any(a.get_visible() for a in (*drawn, *texts, ax.get_legend()) if a)


def measure(fig: Figure) -> Facts:
    """Every fact the rules read, from one draw of ``fig``."""
    r = Reader(fig)
    texts = r.attempt(r.axes_texts, (), "OVERFLOW, OVERLAP, TEXT_CROWD")
    return Facts(
        canvas=box_of(Bbox(fig.bbox.get_points())),
        px_per_pt=r.pt,
        texts=texts,
        figure_texts=r.attempt(r.figure_texts, (), "OVERFLOW"),
        legend_texts=r.attempt(r.legend_texts, (), "OVERFLOW"),
        ticks=r.attempt(r.ticks, (), "TICK_OVERLAP"),
        legends=r.attempt(r.legends, (), "LEGEND_ON_DATA"),
        empty=r.empty(),
        values=r.attempt(lambda: r.values(texts), (), "VALUE_LABEL_ON_DATA"),
        inks=r.attempt(lambda: r.inks(texts), (), "TEXT_CONTRAST"),
        frames=r.attempt(r.frames, (), "SMALL_PANEL"),
        skipped=tuple(r.skipped),
    )
