"""Read the facts the rules judge from a figure: draw, measure, touch nothing.

The figure is drawn once so every position is current, and that same draw
keeps what is behind the texts the user placed (``geometry.draw``). No
artist is changed, hidden or moved.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from math import isclose
from typing import TYPE_CHECKING, TypeVar

import numpy as np
from matplotlib.axes import Axes
from matplotlib.inset import InsetIndicator
from matplotlib.projections.polar import PolarAxes
from matplotlib.text import Annotation
from matplotlib.text import Text as MplText
from matplotlib.transforms import Bbox

from ..colorspace import LEGIBLE
from ..geometry import (
    BBOX_ERRORS,
    Backdrop,
    axes_titles,
    draw,
    drawn_in_tree,
    drawn_ink_meets,
    drawn_tick_labels,
    draws_axis,
    figure_legends,
    get_renderer,
    iter_figure_level_extents,
    panel_letters,
    patch_inks,
    projection,
    same_position_axes,
    text_inks,
)
from ..vocab import AlignCentre, X, Y, parse_halign
from . import roles
from .alignment_measure import alignment_samples
from .axis_labels import minus_tick, tick_row
from .canvas import content_box, shape_panel
from .ink import Ink, data_artists, data_ink, data_shows, legend_inks, words_box
from .model import (
    AXES,
    LETTER_CLEARANCE_PT,
    THROUGH_EM,
    Box,
    CanvasUse,
    Connected,
    Facts,
    Frame,
    Hit,
    Inked,
    Inset,
    Legend,
    OnData,
    Panel,
    PolarTheta,
    Text,
    TickOcclusion,
    TickRow,
    ascii_minus_value,
)
from .occlusion import measure_occlusion

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
        """Draw ``fig`` once so every position is current, and read what
        that draw put behind the texts the user placed.

        A figure without such texts is drawn by ``fig.canvas.draw()``. One
        with them is drawn by ``geometry.draw``, which keeps the paper
        under the texts: either way its artists are drawn once and its
        ``draw_event`` fires once.
        """
        self.fig = fig
        self.skipped: list[str] = []
        indices = {ax: i for i, ax in enumerate(fig.axes)}
        self.inset_parents: dict[Axes, Axes] = {}
        for ax in fig.axes:
            if drawn_in_tree(ax):
                for parent, child in drawn_insets(ax):
                    indices.setdefault(child, len(indices))
                    self.inset_parents[child] = parent
        self.axes = [(i, ax) for ax, i in indices.items() if drawn_in_tree(ax)]
        self.panels = [(i, ax) for i, ax in self.axes if projection(ax).flat]
        self.letters = {id(t) for _ax, t in panel_letters(fig)}
        self.placed = [
            (i, t)
            for i, ax in self.axes
            for t in ax.texts
            if id(t) not in self.letters
            and drawn_in_tree(t)
            and t.get_text().strip()
        ]
        self.behind: list[Backdrop] = []
        if texts := [t for _i, t in self.placed]:
            drawn = draw(fig)
            self.behind = self.attempt(
                lambda: drawn.backdrops(texts), [], "TEXT_CONTRAST"
            )
        else:
            fig.canvas.draw()  # pyright: ignore[reportUnknownMemberType]
        self.renderer: RendererBase = get_renderer(fig)
        self.pt = fig.dpi / 72.0

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

    def centred_titles(self) -> tuple[Text, ...]:
        """Upright titles centred on their Axes, of any projection."""
        return tuple(
            t
            for i, ax in self.axes
            for title in axes_titles(ax).values()
            if parse_halign(title.get_horizontalalignment()) == AlignCentre()
            and float(title.get_rotation()) == 0.0
            and (t := self.text(title, roles.Title(), i)) is not None
        )

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

    def ticks(self) -> tuple[TickRow, ...]:
        """Tick rows of rectilinear Axes."""
        return tuple(
            row
            for i, ax in self.panels
            for which in AXES
            if (row := tick_row(i, ax, which, self.renderer, self.text))
            is not None
        )

    def minus_labels(self, figure_texts: tuple[Text, ...]) -> tuple[Text, ...]:
        """Drawn numeric annotations and figure texts with a hyphen-minus."""
        labels = [
            t
            for t in figure_texts
            if ascii_minus_value(t.text)
            and isinstance(t.handle, MplText)
            and text_inks(t.handle)
        ]
        labels.extend(
            text
            for i, ax in self.axes
            for label in ax.texts
            if ascii_minus_value(label.get_text())
            and text_inks(label)
            and (text := self.text(label, roles.FreeText(), i)) is not None
        )
        return tuple(labels)

    def radial_occlusion(self) -> tuple[TickOcclusion, ...]:
        """Visible radial tick labels and the fill drawn over them."""
        found: list[TickOcclusion] = []
        for i, ax in self.axes:
            if not isinstance(ax, PolarAxes):
                continue
            labels = tuple(
                t
                for label in (
                    *drawn_tick_labels(ax, Y()),
                    *drawn_tick_labels(ax, Y(), minor=True),
                )
                if text_inks(label)
                and (t := self.text(label, roles.TickLabel(), i)) is not None
            )
            if labels:
                found.extend(measure_occlusion(ax, labels))
        return tuple(found)

    def polar_theta(self) -> tuple[PolarTheta, ...]:
        """Angle labels and disc extents, for visible full-circle polar plots."""
        found: list[PolarTheta] = []
        for i, ax in self.axes:
            if not isinstance(ax, PolarAxes) or not isclose(
                ax.get_thetamax() - ax.get_thetamin(), 360.0
            ):
                continue
            drawn = (
                *drawn_tick_labels(ax, X()),
                *drawn_tick_labels(ax, X(), minor=True),
            )
            labels = tuple(
                t
                for label in drawn
                if text_inks(label)
                and (t := self.text(label, roles.TickLabel(), i)) is not None
            )
            disc = box_of(ax.patch.get_extents())
            if labels and disc.area > 0:
                found.append(PolarTheta(Panel(ax, i), disc, labels))
        return tuple(found)

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

    def struck(self, texts: tuple[Text, ...]) -> tuple[OnData, ...]:
        """Names and notes (placed texts that print no value) and the lines
        drawn through them. A text on a box of its own covers the line, a
        line that only reaches the text's edge is its leader, and a text
        turned to run along a line is that line's name: its upright box
        would take in the line beside it."""
        found: list[OnData] = []
        inks: dict[int, Ink] = {}
        for t in texts:
            h = t.handle
            ax = h.axes if isinstance(h, MplText) else None
            if (
                not (t.role.free and not t.value and isinstance(ax, Axes))
                or not isinstance(h, MplText)
                or h.get_bbox_patch() is not None
                or float(h.get_rotation()) % 90.0 != 0.0
            ):
                continue
            if id(ax) not in inks:
                frame = ax.get_window_extent(self.renderer)
                inks[id(ax)] = data_ink(
                    same_position_axes(ax), frame, self.renderer, self.pt
                )
            inner = t.box.padded(-THROUGH_EM * t.em)
            if inner.width <= 0 or inner.height <= 0:
                continue
            box = Bbox.from_extents(inner.x0, inner.y0, inner.x1, inner.y1)
            hits = inks[id(ax)].meets(box, 0.5 * self.pt)
            if lines := tuple(h for h in hits if h.line):
                found.append(OnData(t, lines))
        return tuple(found)

    def connected(self, texts: tuple[Text, ...]) -> tuple[Connected, ...]:
        """Inset tick and axis labels a zoom connector
        (``ax.indicate_inset_zoom``) is drawn through, per inset. Measured
        like a line through a name: inside the label's box, not at its edge."""
        indices = {ax: i for i, ax in self.axes}
        found: list[Connected] = []
        for child, parent in self.inset_parents.items():
            lines = [
                (
                    c.get_transform().transform_path(c.get_path()),
                    float(c.get_linewidth()) * self.pt / 2,
                )
                for artist in parent.artists
                if isinstance(artist, InsetIndicator) and artist.get_visible()
                for c in artist.connectors or ()
                if c.get_visible() and patch_inks(c)
            ]
            if not lines:
                continue
            i = indices[child]
            ticks = [
                self.text(label, roles.TickLabel(), i)
                for axis in (X(), Y())
                for label in drawn_tick_labels(child, axis)
                if text_inks(label)
            ]
            names = [
                t
                for t in texts
                if t.panel == i and isinstance(t.role, roles.AxisLabel)
            ]
            hit: list[Text] = []
            for t in (*ticks, *names):
                if t is None:
                    continue
                inner = t.box.padded(-THROUGH_EM * t.em)
                if inner.width <= 0 or inner.height <= 0:
                    continue
                box = Bbox.from_extents(inner.x0, inner.y0, inner.x1, inner.y1)
                if any(
                    drawn_ink_meets(path, half, box) for path, half in lines
                ):
                    hit.append(t)
            if hit:
                found.append(Connected(i, tuple(hit)))
        return tuple(found)

    def letters_on_data(self, texts: tuple[Text, ...]) -> tuple[OnData, ...]:
        """Panel letters and the data they are drawn on (a letter inside
        its plot)."""
        found: list[OnData] = []
        for t in texts:
            ax = t.handle.axes if isinstance(t.handle, MplText) else None
            if not (
                isinstance(t.role, roles.PanelLetter) and isinstance(ax, Axes)
            ):
                continue
            frame = ax.get_window_extent(self.renderer)
            ink = data_ink(
                same_position_axes(ax), frame, self.renderer, self.pt
            )
            box = Bbox.from_extents(t.box.x0, t.box.y0, t.box.x1, t.box.y1)
            # A letter reads as part of data it nearly touches: it keeps
            # LETTER_CLEARANCE_PT of air.
            room = box.padded(LETTER_CLEARANCE_PT * self.pt)
            if hits := ink.meets(room, 0.5 * self.pt):
                found.append(OnData(t, tuple(hits)))
        return tuple(found)

    def inks(self, texts: tuple[Text, ...]) -> tuple[Inked, ...]:
        """Texts the user placed in an Axes of any projection, each pixel
        of their ink against what is drawn behind it."""
        known = {id(t.handle): t for t in texts}
        found: list[Inked] = []
        for (panel, placed), behind in zip(
            self.placed, self.behind, strict=False
        ):
            fact = known.get(id(placed)) or self.text(
                placed, roles.FreeText(), panel
            )
            if fact is not None and len(behind.ink):
                found.append(Inked(fact, behind.read(LEGIBLE)))
        return tuple(found)

    def canvas_use(self, texts: tuple[Text, ...]) -> CanvasUse | None:
        """The body of one shape chart without a legend or other panel."""
        if len(self.axes) != 1:
            return None
        [(i, ax)] = self.axes
        if not shape_panel(ax) or self.drawn_legends():
            return None
        labels = tuple(
            t
            for t in texts
            if t.role.free
            and isinstance(t.handle, MplText)
            and text_inks(t.handle)
        )
        body = content_box(ax, labels, self.renderer, self.pt)
        if body is None:
            return None
        inside = Bbox.intersection(body, self.fig.bbox)
        return (
            None if inside is None else CanvasUse(Panel(ax, i), box_of(inside))
        )

    def frames(self) -> tuple[Frame, ...]:
        """The plot areas a text of another Axes must keep off: Axes that
        draw something or a frame."""
        return tuple(
            Frame(ax, i, box_of(ax.get_window_extent(self.renderer)))
            for i, ax in self.panels
            if draws(ax) or (ax.axison and ax.get_frame_on())
        )

    def insets(self, texts: tuple[Text, ...]) -> tuple[Inset, ...]:
        """Inset labels and the visible straight spines of their parents."""
        indices = {ax: i for i, ax in self.axes}
        found: list[Inset] = []
        for child, parent in self.inset_parents.items():
            i = indices[child]
            labels = tuple(
                t
                for t in texts
                if t.panel == i and isinstance(t.role, roles.AxisLabel)
            )
            if labels:
                spines = tuple(
                    box
                    for spine in parent.spines.values()
                    if parent.axison
                    and spine.get_visible()
                    and patch_inks(spine)
                    and (box := box_of(spine.get_extents())).area == 0
                    and max(box.width, box.height) > 0
                )
                found.append(
                    Inset(Panel(parent, indices[parent]), i, labels, spines)
                )
        return tuple(found)

    def empty(self) -> tuple[Panel, ...]:
        """Framed Axes where nothing is drawn, nor in a twin sharing the box."""
        found: list[Panel] = []
        canvas = Bbox(self.fig.bbox.get_points())
        for i, ax in self.panels:
            if not ax.axison:
                continue
            owners = same_position_axes(ax)
            if any(data_artists(owner) for owner in owners):
                if not any(
                    data_shows(owner, canvas, self.renderer, self.pt)
                    for owner in owners
                ):
                    found.append(Panel(ax, i))
            elif not any(map(draws, owners)):
                found.append(Panel(ax, i))
        return tuple(found)


def drawn_insets(ax: Axes) -> Iterator[tuple[Axes, Axes]]:
    """Drawn parent and child Axes pairs, including nested native insets."""
    for child in ax.child_axes:
        if isinstance(child, Axes) and drawn_in_tree(child):
            yield ax, child
            yield from drawn_insets(child)


def draws(ax: Axes) -> bool:
    """``ax`` draws data, a text or a legend."""
    drawn = (
        *ax.lines,
        *ax.patches,
        *ax.collections,
        *ax.images,
        *ax.tables,
        *(child for child in ax.child_axes if isinstance(child, Axes)),
    )
    texts = (t for t in ax.texts if t.get_text().strip())
    return any(a.get_visible() for a in (*drawn, *texts, ax.get_legend()) if a)


def measure(fig: Figure) -> Facts:
    """Every fact the rules read, from one draw of ``fig``."""
    r = Reader(fig)
    texts = r.attempt(
        r.axes_texts, (), "OVERFLOW, OVERLAP, TEXT_CROWD, TEXT_TOO_CLOSE"
    )
    figure_texts = r.attempt(r.figure_texts, (), "OVERFLOW, MIXED_MINUS")
    minus_labels = r.attempt(
        lambda: r.minus_labels(figure_texts), (), "MIXED_MINUS"
    )
    return Facts(
        canvas=box_of(Bbox(fig.bbox.get_points())),
        px_per_pt=r.pt,
        texts=texts,
        figure_texts=figure_texts,
        legend_texts=r.attempt(r.legend_texts, (), "OVERFLOW"),
        ticks=r.attempt(r.ticks, (), "TICK_OVERLAP"),
        legends=r.attempt(r.legends, (), "LEGEND_ON_DATA"),
        empty=r.attempt(r.empty, (), "EMPTY_AXES"),
        values=r.attempt(lambda: r.values(texts), (), "VALUE_LABEL_ON_DATA"),
        letters=r.attempt(
            lambda: r.letters_on_data(texts), (), "LETTER_ON_DATA"
        ),
        struck=r.attempt(lambda: r.struck(texts), (), "TEXT_ON_LINE"),
        connected=r.attempt(lambda: r.connected(texts), (), "TEXT_ON_LINE"),
        inks=r.attempt(lambda: r.inks(texts), (), "TEXT_CONTRAST"),
        frames=r.attempt(r.frames, (), "CROSS_AXES_OVERLAP, SMALL_PANEL"),
        insets=r.attempt(lambda: r.insets(texts), (), "CROSS_AXES_OVERLAP"),
        polar_theta=r.attempt(r.polar_theta, (), "POLAR_TICK_ON_PLOT"),
        minus_labels=minus_labels,
        minus_tick=r.attempt(
            lambda: minus_tick(r.axes, r.text), None, "MIXED_MINUS"
        )
        if minus_labels
        else None,
        alignment=r.attempt(
            lambda: alignment_samples(texts, r.renderer),
            (),
            "TEXT_MISALIGNMENT",
        ),
        occluded_ticks=r.attempt(r.radial_occlusion, (), "RADIAL_TICK_COVERED"),
        edge_texts=r.attempt(
            lambda: tuple(
                t
                for t in texts
                if t.role.free
                and isinstance(t.handle, MplText)
                and text_inks(t.handle)
            ),
            (),
            "TEXT_AT_EDGE",
        ),
        edge_titles=r.attempt(r.centred_titles, (), "TEXT_AT_EDGE"),
        canvas_use=r.attempt(
            lambda: r.canvas_use(texts), None, "UNDERUSED_CANVAS"
        ),
        skipped=tuple(r.skipped),
    )
