"""What ``dm.simple_layout`` does to bar labels at the size it fits.

Each step starts from the same base (every label upright and shown, each
autoscaled value axis at matplotlib's limits for the data), so repeated
layouts give the same result: crowded calls turn vertical (vertical bars),
labels that still meet are hidden from the last position, and autoscaled
value axes grow just enough for the labels beyond the bar ends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from ..geometry import axis_of, same_position_axes, shared_axes
from ..vocab import Which, X, Y
from . import decide
from .bar_geometry import CrowdFacts, HeadroomFacts, Pixels, Room, Span, Spot
from .bar_options import Rotate, Skip
from .bars import OFFSET_PT, BarFamily, BarLabel, families_of, format_ticks_now
from .measure import bar_centres, px_per_pt

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

# Clear space between neighbouring bar labels, in points.
GAP_PT = 1.5


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


def _crowd(
    calls: list[tuple[BarFamily, list[BarLabel]]], renderer: RendererBase
) -> None:
    """Turn each crowded call's labels (vertical bars); then, once one call
    is crowded, hide the positions that still meet over every call here."""
    first = calls[0][1][0]
    centres = bar_centres(first.bar_axes, first.vertical)
    gap = Pixels(GAP_PT * px_per_pt(first))
    crowded = False
    for family, labels in calls:
        shown = [t for t in labels if t.get_visible()]
        if decide.crowded(CrowdFacts(_spots(shown, renderer), centres, gap)):
            crowded = True
            match family.options.crowded:
                case Rotate() if first.vertical:
                    for t in labels:
                        t.set_rotation(90.0)
                case Rotate() | Skip():
                    pass
    if not crowded:
        return
    shown = [t for _f, labels in calls for t in labels if t.get_visible()]
    keep = decide.keep_apart(CrowdFacts(_spots(shown, renderer), centres, gap))
    for t, kept in zip(shown, keep.flags, strict=True):
        if not kept:
            t.set_visible(False)
            t.hidden = True


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
        if not label.beyond_end:
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
            set_lim(float(limits[0]), float(limits[1]), auto=None)


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
    for label in (t for f in families for t in f.texts):
        label.set_rotation(0.0)
        label.set_visible(True)
        label.hidden = False
    value_axes = _value_axes(families)
    for value_axis in value_axes:
        value_axis.reset()
    areas: dict[
        tuple[frozenset[int], bool], list[tuple[BarFamily, list[BarLabel]]]
    ] = {}
    for family in families:
        for vertical in (True, False):
            mine = [t for t in family.texts if t.vertical is vertical]
            if mine:
                box = frozenset(map(id, same_position_axes(mine[0].bar_axes)))
                areas.setdefault((box, vertical), []).append((family, mine))
    for calls in areas.values():
        _crowd(calls, renderer)
    for value_axis in value_axes:
        value_axis.grow(renderer)
    return before != [(ax.get_xlim(), ax.get_ylim()) for ax in fig.axes]
