"""What ``dm.simple_layout`` does to bar labels at the size it fits.

Each step starts from the same base (every label upright and shown, each
autoscaled value axis at matplotlib's limits for the data), so repeated
layouts give the same result: crowded calls turn vertical (vertical bars),
labels that still meet are hidden from the last position, and autoscaled
value axes grow just enough for the labels beyond the bar ends.
"""

from __future__ import annotations

import logging
import weakref
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from ..geometry import axis_of, shared_axes
from ..hidden import axes_name
from ..vocab import Span, Which, X, Y
from . import decide
from .bar_geometry import CrowdFacts, HeadroomFacts, Pixels, Room, Spot
from .bars import OFFSET_PT, BarFamily, BarLabel, families_of, format_ticks_now
from .measure import bar_centres, px_per_pt

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

# Clear space between neighbouring bar labels, in points.
GAP_PT = 1.5

LOG = logging.getLogger("dartwork_mpl.labels")

#: The value limits the last ``settle_bars`` grew: matplotlib's, then ours.
Limits = tuple[float, float]
GROWN: weakref.WeakKeyDictionary[Axes, dict[Which, tuple[Limits, Limits]]] = (
    weakref.WeakKeyDictionary()
)


def _live(fig: Figure) -> list[BarFamily]:
    """The calls with labels still drawn (a cleared Axes drops its own)."""
    live: list[BarFamily] = []
    for ax in fig.axes:
        families = families_of(ax)
        for family in families:
            for label in list(family.texts):
                if label.axes is None or label.bar.axes is None:
                    family.texts.remove(label)
                    if label.axes is not None:
                        label.remove()
        families[:] = [f for f in families if f.texts]
        live += families
    return live


def _spots(labels: list[BarLabel], renderer: RendererBase) -> tuple[Spot, ...]:
    out: list[Spot] = []
    for label in labels:
        box, bar = (
            label.get_window_extent(renderer),
            label.bar.get_window_extent(),
        )
        if label.vertical:
            out.append(Spot((bar.x0 + bar.x1) / 2, Span(box.x0, box.x1)))
        else:
            out.append(Spot((bar.y0 + bar.y1) / 2, Span(box.y0, box.y1)))
    return tuple(out)


def _crowd(calls: list[list[BarLabel]], renderer: RendererBase) -> None:
    """Turn each crowded call's labels (vertical bars); then, once one call
    is crowded, hide the positions that still meet over every call here."""
    first = calls[0][0]
    centres = bar_centres(first.bar_axes, first.vertical)
    gap = Pixels(GAP_PT * px_per_pt(first))
    crowded = False
    for labels in calls:
        shown = [t for t in labels if t.get_visible()]
        if decide.crowded(CrowdFacts(_spots(shown, renderer), centres, gap)):
            crowded = True
            if first.vertical:
                for t in labels:
                    t.arrange(90.0, shown=True)
    if not crowded:
        return
    shown = [t for labels in calls for t in labels if t.get_visible()]
    keep = decide.keep_apart(CrowdFacts(_spots(shown, renderer), centres, gap))
    for t, kept in zip(shown, keep.flags, strict=True):
        if not kept:
            t.arrange(t.turned, shown=False)


@dataclass(eq=False)
class _ValueAxis:
    """The labels whose bars share one value axis's limits."""

    axes: Axes
    which: Which
    labels: list[BarLabel] = field(default_factory=list)

    @property
    def autoscaled(self) -> bool:
        match self.which:
            case X():
                return bool(self.axes.get_autoscalex_on())
            case Y():
                return bool(self.axes.get_autoscaley_on())

    def reset(self) -> None:
        """Matplotlib's own limits for the data, and the ticks they give."""
        if self.autoscaled:
            self.axes.autoscale_view(
                scalex=self.which.horizontal, scaley=not self.which.horizontal
            )
        format_ticks_now(axis_of(self.axes, self.which))

    def _room(
        self, label: BarLabel, along: int, renderer: RendererBase
    ) -> Room | None:
        """The room a label beyond its bar end needs, in its own Axes' px."""
        if not label.get_visible():
            return None
        ext = label.get_window_extent(renderer)  # places it
        if label.kind.centred:
            return None
        anchor = float(label.bar_axes.transData.transform(label.xy)[along])
        toward = label.outward
        lo, hi = (ext.y0, ext.y1) if along else (ext.x0, ext.x1)
        need = (toward.reach(lo, hi) - anchor) * toward.sign
        need += OFFSET_PT * px_per_pt(label)
        if not (np.isfinite(anchor) and np.isfinite(need)) or need <= 0:
            return None
        return Room(anchor, need, toward)

    def grow(self, renderer: RendererBase) -> None:
        """Grow autoscaled limits just enough for the labels beyond the bar
        ends; each label's room is read in its own Axes and scaled to this
        one's (``sharey`` panels show the view at other sizes)."""
        if not self.autoscaled:
            return
        along = self.which.column
        box = self.axes.get_window_extent(renderer)
        low, high = (box.y0, box.y1) if along else (box.x0, box.x1)
        rooms: list[Room] = []
        for label in self.labels:
            room = self._room(label, along, renderer)
            own = label.bar_axes.get_window_extent(renderer)
            f0, f1 = (own.y0, own.y1) if along else (own.x0, own.x1)
            if room is not None and f1 > f0:
                k = (high - low) / (f1 - f0)
                rooms.append(
                    Room(
                        low + (room.anchor - f0) * k, room.need * k, room.toward
                    )
                )
        grown = decide.headroom(
            HeadroomFacts(Span(low, high), tuple(rooms))
        ).view
        if grown is None:
            return
        middle = ((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
        points = np.array([middle, middle])
        points[:, along] = (grown.low, grown.high)
        limits = self.axes.transData.inverted().transform(points)[:, along]
        # An edge that did not move keeps its exact value (a sticky 0).
        current = self.axes.get_ylim() if along else self.axes.get_xlim()
        for side, (new, old) in enumerate(
            ((grown.low, low), (grown.high, high))
        ):
            if new == old:
                limits[side] = current[side]
        if np.all(np.isfinite(limits)):
            set_lim = self.axes.set_ylim if along else self.axes.set_xlim
            low_new, high_new = float(limits[0]), float(limits[1])
            set_lim(low_new, high_new, auto=None)
            old = (float(current[0]), float(current[1]))
            GROWN.setdefault(self.axes, {})[self.which] = (
                old,
                (low_new, high_new),
            )


def _value_axes(families: list[BarFamily]) -> list[_ValueAxis]:
    groups: dict[tuple[Which, frozenset[int]], _ValueAxis] = {}
    for family in families:
        for label in family.texts:
            which: Which = Y() if label.vertical else X()
            shared = shared_axes(label.bar_axes, which)
            key = (which, frozenset(map(id, shared)))
            groups.setdefault(
                key, _ValueAxis(label.bar_axes, which)
            ).labels.append(label)
    return list(groups.values())


def settle_bars(fig: Figure, renderer: RendererBase) -> bool:
    """``dm.label_bars`` labels at the Axes size now; whether a view limit moved."""
    families = _live(fig)
    if not families:
        return False
    before = [(ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]
    for ax in fig.axes:
        GROWN.pop(ax, None)
    ours = {id(t) for f in families for t in f.texts if not t.authored}
    for label in (t for f in families for t in f.texts if id(t) in ours):
        label.arrange(0.0, shown=True)
    value_axes = _value_axes(families)
    for value_axis in value_axes:
        value_axis.reset()
    areas: dict[tuple[int, bool], list[list[BarLabel]]] = {}
    for family in families:
        for vertical in (True, False):
            mine = [
                t
                for t in family.texts
                if t.vertical is vertical and id(t) in ours
            ]
            if mine:
                key = (id(mine[0].bar_axes), vertical)
                areas.setdefault(key, []).append(mine)
    for calls in areas.values():
        _crowd(calls, renderer)
    for value_axis in value_axes:
        value_axis.grow(renderer)
    return before != [(ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]


def report_bars(fig: Figure) -> None:
    """Say what the last ``settle_bars`` did to the labels of ``fig``:
    labels turned or hidden for room, value limits grown."""
    if not LOG.isEnabledFor(logging.INFO):
        return
    by_axes: dict[Axes, list[BarLabel]] = {}
    for family in _live(fig):
        for label in family.texts:
            by_axes.setdefault(label.bar_axes, []).append(label)
    for ax, labels in by_axes.items():
        name = axes_name(ax)
        if any(t.turned == 90.0 and not t.authored for t in labels):
            LOG.info(
                "turned the value labels of %s vertical: side by side they "
                "ran into each other; widen the figure or label fewer bars "
                "to keep them flat",
                name,
            )
        hidden = sum(t.hidden for t in labels)
        if hidden:
            LOG.info(
                "hid %d of %d value labels of %s: they still ran into their "
                "neighbours; widen the figure or label fewer bars "
                "(dm.label_bars(ax, bars)) to show them all",
                hidden,
                len(labels),
                name,
            )
        held = [t for t in labels if t.kind.centred and not t.hidden]
        cut = sum(not t.get_visible() for t in held)
        if cut:
            LOG.info(
                "left out %d segment labels of %s: their segments are "
                "shorter than the text; make the figure larger to show them",
                cut,
                name,
            )
    for ax in fig.axes:
        for which, (old, new) in GROWN.get(ax, {}).items():
            LOG.info(
                "grew the %s limits of %s from %.4g..%.4g to %.4g..%.4g: "
                "the value labels beyond the bar ends did not fit; set the "
                "limits yourself (ax.set_%slim) to keep matplotlib's",
                which.letter,
                axes_name(ax),
                *old,
                *new,
                which.letter,
            )
