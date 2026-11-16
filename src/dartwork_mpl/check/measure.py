"""Read the facts the rules judge from a figure: draw once, measure, touch nothing.

The figure is drawn on its own canvas so every position is current. No
artist is changed, hidden or moved.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Annotation
from matplotlib.text import Text as MplText
from matplotlib.transforms import Bbox

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
)
from ..vocab import Which
from . import roles
from .ink import data_ink, legend_inks, words_box
from .model import AXES, Box, Facts, Hit, Legend, Text, TickRow
from .overlap import tick_label_overlaps

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
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
        """Suptitles, sup-labels and ``fig.text``, of SubFigures too, and the
        entries of every drawn legend (only the canvas edge judges them)."""
        found = [
            self.text(t, roles.FigureText(), None)
            for t, _ext in iter_figure_level_extents(
                self.fig, self.renderer, legends=False
            )
            if isinstance(t, MplText)
        ]
        found += [
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
        return TickRow(ax, i, which, labels, pairs, float(deepest))

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
                )
            )
        return tuple(found)


def measure(fig: Figure) -> Facts:
    """Every fact the rules read, from one draw of ``fig``."""
    r = Reader(fig)
    return Facts(
        canvas=box_of(Bbox(fig.bbox.get_points())),
        px_per_pt=r.pt,
        texts=r.attempt(r.axes_texts, (), "OVERFLOW, OVERLAP, TEXT_CROWD"),
        figure_texts=r.attempt(r.figure_texts, (), "OVERFLOW"),
        ticks=r.attempt(r.ticks, (), "TICK_OVERLAP"),
        legends=r.attempt(r.legends, (), "LEGEND_ON_DATA"),
        skipped=tuple(r.skipped),
    )
