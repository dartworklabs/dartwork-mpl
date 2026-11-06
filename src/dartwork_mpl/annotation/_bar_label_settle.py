"""What ``dm.simple_layout`` does to bar value labels at the size it fits.

:func:`settle_bar_labels` runs in every layout step, after the tick formats
and the twin colours, before the margins are measured. Each pass starts from
the same base (every label as its call placed it, each value axis at
matplotlib's own autoscaled limits for the data), so repeated layouts and
further layout steps give the same result; nothing compounds.

* **Lifecycle.** A label gone from its Axes (``Artist.remove``, ``ax.cla()``)
  or whose bar is gone is dropped, and a call with no label left is
  forgotten. A label whose host is no longer the Axes drawn last in its
  bars' box (a twin made after the call) moves onto that Axes, as it is.
* **Crowding.** A drawn label wider than its bar pitch less :data:`GAP_PT`
  makes its whole call crowded. The pitch is the distance on screen to the
  nearest other bar drawn in the plot area, whichever call labels it, if
  any. The call's ``crowded`` rule applies:

  - ``"rotate"``: vertical text on vertical bars. ``barh`` never turns: rows
    thinner than the text fall back to hiding labels (below).
  - ``"inside"``: plain bars' labels move inside their bar ends (vertical
    text on vertical bars) in readable ink; a bar too short for its label
    keeps it outside. Totals and segment labels stay where they are.
  - ``"skip"``: nothing turns or moves.

  Then, under any rule, labels that would still overlap are hidden a bar
  position at a time, over the labels of every call on the same plot area
  (the Axes drawn in one box) once any of those calls is crowded, so one
  call per series meets the others' labels: from the last position on
  screen (the right end, or the top row of ``barh``), a position whose
  labels come within :data:`GAP_PT` of the last kept position's is hidden,
  so ``"skip"`` keeps every other label of evenly crowded bars.

  Series take turns. When the positions are plain bars of two or more
  containers (grouped bars, one call or one call per series; no stack
  segments or totals, no bars overlaid at one position), a label that
  meets the last kept one at the same bar index takes its place when its
  series' turn there comes first: two series alternate, the first on even
  bar indices and the second on odd ones, so neither disappears whole;
  more series count down (the first at index 0, the last at 1, ...). A
  label hidden only because another series had the turn is hidden for its
  ``"turn"``; any other hidden label for ``"room"`` (``BarLabel.hidden_for``).
  Rows too thin even for one label each (``barh``) still lose labels to
  the overlap rule; :func:`warn_hidden_bar_labels`, run once by
  ``dm.simple_layout`` after its fit, warns when a label was hidden for
  room under a rule other than ``"skip"`` (which asks for hiding), and
  names the cure: a taller (``barh``) or wider figure.

  A kept outside label wider than its bar (a plain bar's, a stack's total)
  is pushed past the ends of the other bars it spans, never drawn on them;
  a label with a longer bar at its own position (a lower stack segment
  asked ``"outside"``, an actual inside its target) stays at its own bar's
  end.
* **Headroom.** A value axis whose limits matplotlib still autoscales
  (``get_autoscaley_on()``) starts from matplotlib's limits for the data
  (``autoscale_view``) and grows, on the side each outside label points to,
  just enough to hold the label and 3 pt (``OFFSET_PT``) inside the axes:
  solved on screen at the Axes' current size and mapped back through the
  data transform (log axes included). Axes sharing the axis (``sharey``
  panels) show the view at other places and sizes: each label's room is
  read in its own Axes. It is written with ``set_ylim(..., auto=None)``:
  autoscaling stays on, and a later ``set_ylim`` of the caller's turns it
  off. Limits the caller set are never touched, nor is a view the caller
  set while autoscaling stays on (``set_ybound``, ``set_ylim(...,
  auto=None)``): neither what this module last wrote nor what
  ``autoscale_view`` gives for the data. New data, ``margins`` or an
  inverted axis are matplotlib's own view again, and the room grows from
  there. A label that does not fit sits outside the axes and the layout
  keeps it inside the figure.
* **Explicit wins.** Rotation, visibility, colour and placement are written
  through :meth:`~._bar_labels.BarLabel.own`: a later ``Text.set_*`` keeps
  its value through every layout.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import numpy as np
import numpy.typing as npt
from matplotlib.artist import Artist
from matplotlib.container import BarContainer

from .._figure_geometry import get_renderer, same_position_axes, shared_axes
from ._bar_label_geometry import OFFSET_PT, fits_on_bar, outward
from ._bar_label_ink import label_ink
from ._bar_label_lifecycle import families_of, prune, rehost
from ._bar_labels import BarLabel, BarLabelFamily, format_ticks_now

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.axis import Axis
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle
    from matplotlib.transforms import Bbox

    from ._bar_label_options import BarLabelOptions

__all__ = [
    "GAP_PT",
    "grown_span",
    "settle_bar_labels",
    "warn_hidden_bar_labels",
]

# The clear space between neighbouring labels: a label wider than its bar
# pitch less this is crowded, and kept labels stay this far apart.
GAP_PT = 1.5
# Two bar middles closer than this (display pixels) are one position.
_SAME_POSITION_PX = 0.5


def settle_bar_labels(fig: Figure, renderer: RendererBase | None = None) -> int:
    """Settle every :func:`~._bar_labels.label_bars` call on ``fig``.

    Drops what is gone, re-hosts, applies crowding and grows autoscaled
    value axes for the labels (module docstring). ``renderer`` measures the
    text (default: the figure's). Returns the number of calls settled (0
    when no call has a label left: nothing else is touched).
    """
    families = _live_families(fig)
    if not families:
        return 0
    if renderer is None:
        renderer = get_renderer(fig)
    value_axes = _value_axes(families)
    for value_axis in value_axes:
        value_axis.reset()
    for area in _areas(families):
        _crowd(area, renderer)
    for value_axis in value_axes:
        value_axis.grow(renderer)
    return len(families)


# ------------------------------------------------------------ lifecycle
def _live_families(fig: Figure) -> list[BarLabelFamily]:
    """The calls with labels still drawn, each moved onto its host now."""
    live: list[BarLabelFamily] = []
    for ax in fig.axes:
        families = families_of(ax)
        families[:] = [family for family in families if prune(family)]
        for family in families:
            rehost(family)
        live.extend(families)
    return live


# ------------------------------------------------------------ crowding
def _px(label: BarLabel, points: float) -> float:
    figure = label.get_figure(root=True)
    return points * (figure.dpi if figure is not None else 72.0) / 72.0


@dataclass(eq=False)
class _Bars:
    """The bars drawn in one plot area, measured once on screen.

    ``spans`` and ``reach`` hold each bar's ``(low, high)`` display extent
    across the bars and along the value axis.
    """

    vertical: bool
    bars: list[Rectangle]
    spans: npt.NDArray[np.float64]
    reach: npt.NDArray[np.float64]
    index: dict[int, int]

    @classmethod
    def around(cls, bar_axes: Axes, vertical: bool) -> _Bars:
        """Every bar drawn in ``bar_axes``' box (its twins' included)."""
        bars = [
            patch
            for member in same_position_axes(bar_axes)
            for container in member.containers
            if isinstance(container, BarContainer)
            for patch in container.patches
            if patch.get_visible()
        ]
        boxes = [bar.get_window_extent() for bar in bars]
        spans = np.array(
            [_across(box, vertical) for box in boxes], dtype=float
        ).reshape(-1, 2)
        reach = np.array(
            [_across(box, not vertical) for box in boxes], dtype=float
        ).reshape(-1, 2)
        spans.sort(axis=1)
        reach.sort(axis=1)
        index = {id(bar): i for i, bar in enumerate(bars)}
        return cls(vertical, bars, spans, reach, index)

    def _extents(self, bar: Rectangle) -> tuple[npt.NDArray[np.float64], ...]:
        i = self.index.get(id(bar))
        if i is not None:
            return self.spans[i], self.reach[i]
        box = bar.get_window_extent()
        return (
            np.sort(_across(box, self.vertical)),
            np.sort(_across(box, not self.vertical)),
        )

    def centre(self, bar: Rectangle) -> float:
        """The bar's middle across the bars, on screen."""
        return float(np.mean(self._extents(bar)[0]))

    def end(self, bar: Rectangle, toward: int) -> float:
        """The bar's end on screen in the direction ``toward`` (+1 up/right)."""
        low, high = self._extents(bar)[1]
        return float(high if toward > 0 else low)

    def pitch(self, centre: float) -> float:
        """The distance on screen from ``centre`` to the nearest other bar.

        Every bar drawn in the plot area counts, labelled or not, by its
        middle; bars at ``centre`` itself (within 0.5 px) do not.
        """
        away = np.abs(self.spans.mean(axis=1) - centre)
        away = away[away > _SAME_POSITION_PX]  # NaN bars drop out too
        return float(away.min()) if away.size else np.inf


@dataclass(eq=False)
class _Position:
    """The drawn labels at one bar position and their extents across it."""

    centre: float
    labels: list[BarLabel] = field(default_factory=list)
    spans: list[tuple[float, float]] = field(default_factory=list)
    low: float = np.inf
    high: float = -np.inf

    def add(self, label: BarLabel, low: float, high: float) -> None:
        self.labels.append(label)
        self.spans.append((low, high))
        self.low, self.high = min(self.low, low), max(self.high, high)

    @property
    def width(self) -> float:
        """The widest label's extent across the bars."""
        return max(high - low for low, high in self.spans)


def _across(box: Bbox, vertical: bool) -> tuple[float, float]:
    """A display box's extent across the bars (x for ``bar``, y for ``barh``)."""
    return (box.x0, box.x1) if vertical else (box.y0, box.y1)


def _positions(
    labels: Sequence[BarLabel], bars: _Bars, renderer: RendererBase
) -> list[_Position]:
    """The drawn labels by bar position, in screen order across the bars."""
    rows: list[tuple[float, BarLabel, float, float]] = []
    for label in labels:
        if not label.get_visible():
            continue
        low, high = _across(label.get_window_extent(renderer), bars.vertical)
        rows.append((bars.centre(label.bar), label, low, high))
    rows.sort(key=lambda row: row[0])
    positions: list[_Position] = []
    for centre, label, low, high in rows:
        if not positions or centre - positions[-1].centre > _SAME_POSITION_PX:
            positions.append(_Position(centre))
        positions[-1].add(label, low, high)
    return positions


def _crowded(positions: list[_Position], bars: _Bars, gap: float) -> bool:
    """Whether a drawn label is wider than its bar pitch less ``gap``.

    The pitch is the distance to the nearest other bar of the plot area,
    whichever call (if any) labels it.
    """
    return any(
        position.width > bars.pitch(position.centre) - gap
        for position in positions
    )


def _reset(label: BarLabel) -> None:
    """The label as its call placed it (what it still owns)."""
    label.where = label.asked
    label.clear_of = ()
    label.hidden_for = None
    label.own_rotation(0.0)
    label.own_visible(True)
    label.own_color(label.ink)


@dataclass(eq=False)
class _Area:
    """The labels of every call on the bars of one plot area, one orientation.

    ``calls`` holds each call's options and its labels here, in call order.
    """

    vertical: bool
    calls: list[tuple[BarLabelOptions, list[BarLabel]]] = field(
        default_factory=list
    )


def _areas(families: list[BarLabelFamily]) -> list[_Area]:
    """The calls' labels by plot area (the Axes drawn in one box) and side.

    Every label is put back as its call placed it first (:func:`_reset`).
    """
    areas: dict[tuple[frozenset[int], bool], _Area] = {}
    for family in families:
        for label in family.texts:
            _reset(label)
        for vertical in (True, False):
            labels = [
                label
                for label in family.texts
                if (label.orientation == "vertical") is vertical
            ]
            if not labels:
                continue
            box = frozenset(map(id, same_position_axes(labels[0].bar_axes)))
            area = areas.setdefault((box, vertical), _Area(vertical))
            area.calls.append((family.options, labels))
    return list(areas.values())


def _crowd(area: _Area, renderer: RendererBase) -> None:
    """Apply each crowded call's rule, then hide what still overlaps.

    A call is crowded by its own labels (against every bar of the area). The
    overlap selection, once any call here is crowded, runs over the labels
    of every call in the area: separate calls (one per series) meet there.
    """
    first = area.calls[0][1][0]
    bars = _Bars.around(first.bar_axes, area.vertical)
    gap = _px(first, GAP_PT)
    crowded = False
    for options, labels in area.calls:
        if _crowded(_positions(labels, bars, renderer), bars, gap):
            _apply(options, labels, bars)
            crowded = True
    if crowded:
        every = [label for _options, labels in area.calls for label in labels]
        positions = _positions(every, bars, renderer)
        kept = _hide_overlaps(positions, gap, _turns(positions, every))
        _clear_neighbours(kept, bars)


def _apply(
    options: BarLabelOptions, labels: list[BarLabel], bars: _Bars
) -> None:
    """The call's ``crowded`` rule: turn its labels, or move them inside."""
    rule = options.crowded
    if bars.vertical and rule in ("rotate", "inside"):
        for label in labels:
            label.own_rotation(90.0)
    if rule == "inside":
        for label in labels:
            if label.kind == "edge" and label.asked == "outside":
                _move_inside(label, options)


def _move_inside(label: BarLabel, options: BarLabelOptions) -> None:
    """Inside the bar end in readable ink, if the bar holds the label."""
    label.where = "inside"
    label.bar_family.follow(label)
    if not label.get_visible() or not fits_on_bar(
        label, label.measured_length()
    ):
        label.where = label.asked
        return
    ink = label_ink(
        options.color, label.kind, "inside", label.bar, label.bar_axes
    )
    label.own_color(label.ink if ink is None else ink)


def _turns(
    positions: list[_Position], labels: Sequence[BarLabel]
) -> dict[int, int] | None:
    """Each position's turn at its bar index, when the positions are series.

    Series apply when every position holds one plain bar's label and those
    come from two or more containers (``labels`` gives their order: call by
    call, container by container). Series ``s`` of ``n`` has turn
    ``(s + i) % n`` at bar index ``i``; turn 0 goes first. Two series
    alternate, the first on even indices. More series count down (the
    first at index 0, the last at 1, the one before it at 2...): grouped
    bars drawn in series order then keep labels at least a bar width
    short of the pitch apart, where counting up would put the last
    series' label next to the first's of the next group. ``None``
    otherwise: a stack's segments or totals, or bars overlaid at one
    position, keep the plain overlap rule.
    """
    if any(
        len(position.labels) != 1 or position.labels[0].kind != "edge"
        for position in positions
    ):
        return None
    drawn = {id(position.labels[0]) for position in positions}
    series: dict[int, int] = {}
    for label in labels:
        if id(label) in drawn:
            series.setdefault(id(label.container), len(series))
    if len(series) < 2:
        return None
    return {
        id(position): (
            series[id(position.labels[0].container)] + position.labels[0].index
        )
        % len(series)
        for position in positions
    }


def _hide_overlaps(
    positions: list[_Position], gap: float, turns: dict[int, int] | None
) -> list[_Position]:
    """Hide the positions that come within ``gap`` of the last kept one.

    Walks from the last position on screen; returns the kept positions.
    With ``turns`` (:func:`_turns`), a position that meets the last kept
    one at the same bar index takes its place when its turn there comes
    first and it clears the kept one before.

    A hidden label is hidden for its ``"turn"`` when another series' turn
    came first at its bar index, else for ``"room"``
    (``BarLabel.hidden_for``).
    """
    kept: list[_Position] = []
    for position in reversed(positions):
        if not kept or position.high + gap <= kept[-1].low:
            kept.append(position)
            continue
        last = kept[-1]
        if (
            turns is not None
            and position.labels[0].index == last.labels[0].index
            and turns[id(position)] < turns[id(last)]
            and (len(kept) < 2 or position.high + gap <= kept[-2].low)
        ):
            kept[-1] = position
    shown = {id(position) for position in kept}
    first: dict[int, int] = {}  # the first turn at each bar index
    if turns is not None:
        for position in positions:
            index, turn = position.labels[0].index, turns[id(position)]
            if turn < first.get(index, turn + 1):
                first[index] = turn
    for position in positions:
        if id(position) in shown:
            continue
        for_turn = (
            turns is not None
            and turns[id(position)] > first[position.labels[0].index]
        )
        for label in position.labels:
            label.own_visible(False)
            if not Artist.get_visible(label):  # not shown by the caller
                label.hidden_for = "turn" if for_turn else "room"
    return kept


def warn_hidden_bar_labels(fig: Figure, *, stacklevel: int = 1) -> int:
    """Warn that the last settle hid labels for want of room, if it did.

    Run by ``dm.simple_layout`` once its fit is done, so the warning speaks
    of the size laid out. It fires when a label of a call whose
    ``crowded`` rule does not ask for hiding (``"skip"`` does) was hidden
    for ``"room"``; labels hidden for another series' ``"turn"`` are the
    rule's own outcome (series alternate), not a loss. The count covers
    every label of those calls the overlap rule hid. ``stacklevel`` counts
    from the caller (1: the line calling this). Returns that count (0:
    nothing to report).
    """
    labels = [
        label
        for ax in fig.axes
        for family in families_of(ax)
        if family.options.crowded != "skip"
        for label in family.texts
    ]
    if not any(label.hidden_for == "room" for label in labels):
        return 0
    hidden = [label for label in labels if label.hidden_for is not None]
    rows = any(label.orientation == "horizontal" for label in hidden)
    columns = any(label.orientation == "vertical" for label in hidden)
    if rows and columns:
        why, fix = "bars too close together for their text", "a larger figure"
    elif rows:
        why, fix = "barh rows thinner than the text", "a taller figure"
    else:
        why, fix = "bars closer together than their text", "a wider figure"
    warnings.warn(
        f"dm.label_bars: {len(hidden)} of {len(labels)} bar value labels are "
        f"hidden where they would overlap ({why}); {fix} brings them back, "
        "and crowded='skip' hides labels on purpose without this warning",
        UserWarning,
        stacklevel=stacklevel + 1,
    )
    return len(hidden)


def _clear_neighbours(positions: list[_Position], bars: _Bars) -> None:
    """Make each drawn outside label clear the other bars it spans.

    Not a label with a bar at its own position that runs past its bar's
    end (a stack segment below the top, asked ``"outside"``; an actual
    inside its target): it sits on that bar already, and lifting it would
    put it on that bar's label. The bars at its position that end short of
    its own count harmlessly.
    """
    middles = bars.spans.mean(axis=1)
    for position in positions:
        here = np.abs(middles - position.centre) <= _SAME_POSITION_PX
        for label, (low, high) in zip(
            position.labels, position.spans, strict=True
        ):
            if label.where != "outside":
                continue
            toward = outward(label)
            ends = bars.reach[:, 1] if toward > 0 else bars.reach[:, 0]
            beyond = (ends - bars.end(label.bar, toward)) * toward
            if np.any(here & (beyond > _SAME_POSITION_PX)):
                continue
            overlap = np.minimum(bars.spans[:, 1], high) - np.maximum(
                bars.spans[:, 0], low
            )
            hit = np.flatnonzero(overlap > _SAME_POSITION_PX)
            label.clear_of = tuple(bars.bars[i] for i in hit)


# ------------------------------------------------------------ headroom
# Where each Axes keeps the bounds this module last wrote on its value axis.
_WRITTEN_ATTR = "_dm_bar_label_bounds"


def _bounds(limits: Sequence[float]) -> tuple[float, float]:
    """A view's limits as ``(low, high)``, whichever way the axis runs."""
    low, high = sorted(float(v) for v in limits)
    return (low, high)


def _same(a: tuple[float, float], b: tuple[float, float] | None) -> bool:
    return b is not None and bool(np.allclose(a, b, rtol=1e-12, atol=0.0))


@dataclass(eq=False)
class _ValueAxis:
    """The labels whose bars share one value axis's limits.

    ``axes`` is one of the Axes sharing it (``siblings``, itself included).
    ``explicit`` is set by :meth:`reset` when the view, though autoscaled,
    is the caller's own (``set_ybound``, ``set_ylim(..., auto=None)``).
    """

    axes: Axes
    name: Literal["x", "y"]
    siblings: list[Axes]
    labels: list[BarLabel] = field(default_factory=list)
    explicit: bool = False

    @property
    def axis(self) -> Axis:
        return self.axes.yaxis if self.name == "y" else self.axes.xaxis

    @property
    def autoscaled(self) -> bool:
        if self.name == "y":
            return bool(self.axes.get_autoscaley_on())
        return bool(self.axes.get_autoscalex_on())

    def limits(self) -> tuple[float, float]:
        low, high = (
            self.axes.get_ylim() if self.name == "y" else self.axes.get_xlim()
        )
        return (float(low), float(high))

    def set_limits(self, low: float, high: float) -> None:
        """Write the view; autoscaling stays as it is (``auto=None``)."""
        if self.name == "y":
            self.axes.set_ylim(low, high, auto=None)
        else:
            self.axes.set_xlim(low, high, auto=None)

    def reset(self) -> None:
        """Matplotlib's own limits for the data, and the ticks they give.

        Not when the view is the caller's: an autoscaled view that is
        neither what this module last wrote nor what ``autoscale_view``
        gives for the data now was set on purpose, and is put back.
        New data, ``margins`` and ``relim`` + ``autoscale_view`` leave
        matplotlib's own view, so the room grows again from there.
        """
        self.explicit = False
        if self.autoscaled:
            view = self.limits()
            written = getattr(self.axes, _WRITTEN_ATTR, {}).get(self.name)
            self.axes.autoscale_view(
                scalex=self.name == "x", scaley=self.name == "y"
            )
            fresh = self.limits()
            if not (
                _same(_bounds(view), written)
                or _same(_bounds(view), _bounds(fresh))
            ):
                self.set_limits(*view)
                self.explicit = True
        format_ticks_now(self.axis)

    def grow(self, renderer: RendererBase) -> None:
        """Grow autoscaled limits just enough for the outside labels.

        Each label's room is read in its own Axes and scaled to this one's:
        Axes sharing the axis show the same view at other places on screen
        (and sizes). The bounds written are remembered on every sibling.
        """
        if not self.autoscaled or self.explicit:
            return
        along = 1 if self.name == "y" else 0
        box = self.axes.get_window_extent(renderer)
        low, high = (box.y0, box.y1) if along else (box.x0, box.x1)
        frames: dict[int, tuple[float, float]] = {}
        wants = []
        for label in self.labels:
            want = _want(label, along, renderer)
            if want is None:
                continue
            frame = frames.get(id(label.bar_axes))
            if frame is None:
                own = label.bar_axes.get_window_extent(renderer)
                frame = (own.y0, own.y1) if along else (own.x0, own.x1)
                frames[id(label.bar_axes)] = frame
            if not frame[1] > frame[0]:
                continue
            anchor, need, toward = want
            scale = (high - low) / (frame[1] - frame[0])
            wants.append(
                (low + (anchor - frame[0]) * scale, need * scale, toward)
            )
        grown = grown_span(low, high, wants)
        if grown is not None:
            middle = ((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
            edges = np.array([middle, middle])
            edges[:, along] = grown
            limits = self.axes.transData.inverted().transform(edges)[:, along]
            # An edge that did not move keeps its exact value: the round
            # trip through display space would turn a sticky 0 into 4e-16.
            # get_*lim() lists the limit at the lower display edge first.
            current = self.axes.get_ylim() if along else self.axes.get_xlim()
            for side, edge in enumerate((low, high)):
                if grown[side] == edge:
                    limits[side] = current[side]
            if np.all(np.isfinite(limits)):
                self.set_limits(float(limits[0]), float(limits[1]))
        written = _bounds(self.limits())
        for member in self.siblings:
            bounds = getattr(member, _WRITTEN_ATTR, None)
            if bounds is None:
                bounds = {}
                setattr(member, _WRITTEN_ATTR, bounds)
            bounds[self.name] = written


def _want(
    label: BarLabel, along: int, renderer: RendererBase
) -> tuple[float, float, int] | None:
    """``(anchor px, px needed to the edge, side)`` of a drawn outside label."""
    if label.where != "outside" or not label.get_visible():
        return None
    box = label.get_window_extent(renderer)  # places it, anchor included
    anchor = float(label.bar_axes.transData.transform(label.xy)[along])
    toward = outward(label)
    if along:
        far = box.y1 if toward > 0 else box.y0
    else:
        far = box.x1 if toward > 0 else box.x0
    need = (far - anchor) * toward + _px(label, OFFSET_PT)
    if not (np.isfinite(anchor) and np.isfinite(need)) or need <= 0:
        return None
    return (anchor, need, toward)


def grown_span(
    low: float, high: float, wants: Sequence[tuple[float, float, int]]
) -> tuple[float, float] | None:
    """The view ``[low, high]`` (display px) widened so every want fits.

    Each want is ``(anchor, need, side)``: a label anchored at ``anchor``
    (px) needs ``need`` px between the anchor and the axes edge ``side``
    points to (+1 the higher edge). The result is where the new limits sit
    at today's scale, the least widening that gives every want its room
    once the view is shrunk back into the Axes; ``None`` when the view
    already does, or when no widening can (labels longer than the Axes).

    Writing ``S`` for the new span, an anchor ``a`` needing ``n`` of the
    Axes' ``L`` px forces ``high' >= a + n S / L``: ``S`` is the least
    fixed point of a convex piecewise-linear map, found exactly by Newton
    steps over its pieces.
    """
    length = high - low
    if not length > 0:
        return None
    tops = [(a, n / length) for a, n, side in wants if side > 0 and n < length]
    downs = [(a, n / length) for a, n, side in wants if side < 0 and n < length]
    top = np.array([(high, 0.0), *tops]).reshape(-1, 2)
    bottom = np.array([(low, 0.0), *downs]).reshape(-1, 2)
    span = length
    for _ in range(len(top) + len(bottom)):
        i = int(np.argmax(top[:, 0] + top[:, 1] * span))
        j = int(np.argmin(bottom[:, 0] - bottom[:, 1] * span))
        rest = 1.0 - top[i, 1] - bottom[j, 1]
        if rest <= 0:
            return None
        nxt = (top[i, 0] - bottom[j, 0]) / rest
        if nxt <= span:
            break
        span = nxt
    new_high = float(np.max(top[:, 0] + top[:, 1] * span))
    new_low = float(np.min(bottom[:, 0] - bottom[:, 1] * span))
    if new_high <= high and new_low >= low:
        return None
    return (new_low, new_high)


def _value_axes(families: list[BarLabelFamily]) -> list[_ValueAxis]:
    """The labels grouped by the limits their bars' value axis shares."""
    groups: dict[tuple[str, frozenset[int]], _ValueAxis] = {}
    keys: dict[tuple[int, str], tuple[str, frozenset[int]]] = {}
    for family in families:
        for label in family.texts:
            axes = label.bar_axes
            name: Literal["x", "y"] = (
                "y" if label.orientation == "vertical" else "x"
            )
            key = keys.get((id(axes), name))
            if key is None:
                shared = shared_axes(axes, name)
                key = (name, frozenset(map(id, shared)))
                keys[(id(axes), name)] = key
                if key not in groups:
                    groups[key] = _ValueAxis(axes, name, list(shared))
            groups[key].labels.append(label)
    return list(groups.values())
