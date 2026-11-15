"""Write the layout's plan into the figure, and undo it on the next call.

What a layout sets (grid edges, wrapped tick labels and names, turned tick
labels, panel spacing) is kept in one :class:`Record` per figure, in this
module's registry. The next ``simple_layout`` first puts back whatever is
still as it set it, so a second call fits the figure as its author left it
and draws the same. The registry and the records hold the figure and its
artists weakly, so a closed figure is freed.
"""

from __future__ import annotations

import weakref
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, assert_never

from matplotlib.axis import Axis
from matplotlib.gridspec import GridSpec
from matplotlib.text import Text
from matplotlib.ticker import Formatter

from ..vocab import Which
from .measure import grid_axes
from .model import (
    TURN_MODE,
    ArtistId,
    Degrees,
    Edges,
    Gap,
    HSpace,
    Line,
    Mode,
    Share,
    TextPlan,
    WSpace,
    turned_as,
)
from .text import TextArtists, spacing_of

if TYPE_CHECKING:
    from matplotlib.figure import Figure

SIDES = ("left", "right", "bottom", "top")
Optional4 = tuple[float | None, float | None, float | None, float | None]


class WrappedTickFormatter(Formatter):
    """The axis' own formatter with line breaks in some labels (``lines``)."""

    def __init__(
        self, base: Formatter, lines: Mapping[str, str], base_default: bool
    ) -> None:
        """Wrap ``base``; ``base_default``: the axis' default flag before."""
        self.base = base
        self.lines = dict(lines)
        self.base_default = base_default

    def _base(self) -> Formatter:
        """The base formatter, on the axis matplotlib gave this one."""
        if self.base.axis is not self.axis:
            self.base.set_axis(self.axis)
        return self.base

    def __call__(self, x: float, pos: int | None = None) -> str:
        """The base formatter's label, wrapped where ``lines`` says."""
        text = self._base()(x, pos)
        return self.lines.get(text, text)

    def format_ticks(self, values: list[float]) -> list[str]:
        """As the base formatter."""
        return [self.lines.get(t, t) for t in self._base().format_ticks(values)]

    def set_locs(self, locs: list[float]) -> None:
        """As the base formatter."""
        self._base().set_locs(locs)

    def get_offset(self) -> str:
        """As the base formatter."""
        return self._base().get_offset()

    def format_data(self, value: float) -> str:
        """As the base formatter."""
        return self._base().format_data(value)

    def format_data_short(self, value: float) -> str:
        """As the base formatter."""
        return self._base().format_data_short(value)


@dataclass(frozen=True)
class Turned:
    """The angle a layout gave a tick label, and its rotation before."""

    angle: Degrees
    rotation: float
    mode: Mode


@dataclass(frozen=True)
class Named:
    """An axis name a layout wrapped."""

    before: str
    after: str
    group: tuple[ArtistId, Which]


@dataclass(frozen=True)
class Laid:
    """The grid a layout fitted: the edges it started from and left."""

    grid: weakref.ref[GridSpec]
    start: Optional4
    left: Optional4


@dataclass
class Record:
    """Everything one layout set on a figure, to undo on the next."""

    turned: weakref.WeakKeyDictionary[Text, Turned] = field(
        default_factory=weakref.WeakKeyDictionary[Text, Turned]
    )
    axis_turns: weakref.WeakKeyDictionary[Axis, Turned] = field(
        default_factory=weakref.WeakKeyDictionary[Axis, Turned]
    )
    names: weakref.WeakKeyDictionary[Text, Named] = field(
        default_factory=weakref.WeakKeyDictionary[Text, Named]
    )
    gaps: weakref.WeakKeyDictionary[GridSpec, dict[Gap, Share]] = field(
        default_factory=weakref.WeakKeyDictionary[GridSpec, dict[Gap, Share]]
    )
    laid: Laid | None = None

    def gaps_of(self, gs: GridSpec) -> dict[Gap, Share]:
        """The spacing this layout set on ``gs``."""
        return self.gaps.setdefault(gs, {})


_RECORDS: weakref.WeakKeyDictionary[Figure, Record] = (
    weakref.WeakKeyDictionary()
)


def record_of(fig: Figure) -> Record:
    """The record of what this layout set on ``fig``."""
    return _RECORDS.setdefault(fig, Record())


def grid_edges(gs: GridSpec) -> Optional4:
    """``gs``'s edges (``None``: the figure's subplot parameters)."""
    return (gs.left, gs.right, gs.bottom, gs.top)


def write_edges(fig: Figure, gs: GridSpec, edges: Edges | Optional4) -> None:
    """Give ``gs`` the edges and move its Axes there.

    ``GridSpec.update`` moves only the Axes of pyplot's open figures; any
    other figure's Axes follow their SubplotSpec here.
    """
    values = (
        (edges.left, edges.right, edges.bottom, edges.top)
        if isinstance(edges, Edges)
        else edges
    )
    gs.update(**dict(zip(SIDES, values, strict=True)))
    place(fig, gs)


def place(fig: Figure, gs: GridSpec) -> None:
    """Move the Axes of ``gs`` where its edges and spacing say now."""
    for ax in grid_axes(fig, gs):
        spec = ax.get_subplotspec()
        if spec is None:
            continue
        position = spec.get_position(fig)
        if ax.get_position(original=True).bounds != position.bounds:
            ax.set_subplotspec(spec)


def _unwrap(axis: Axis, wrapper: WrappedTickFormatter) -> None:
    axis.set_major_formatter(wrapper.base)
    axis.isDefault_majfmt = wrapper.base_default


def restore(fig: Figure) -> None:
    """Undo what the last layout set, where it is still as set."""
    record = _RECORDS.pop(fig, None) or Record()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            fmt = axis.get_major_formatter()
            if isinstance(fmt, WrappedTickFormatter):
                _unwrap(axis, fmt)
            first = record.axis_turns.get(axis)
            for tick in axis.get_major_ticks():
                label = tick.label1
                turn = record.turned.get(label) or first
                if turn is not None and turned_as(
                    float(label.get_rotation()),
                    label.get_rotation_mode(),
                    turn.angle,
                ):
                    label.set_rotation(turn.rotation)
                    label.set_rotation_mode(turn.mode)
    for label, named in record.names.items():
        if label.get_text() == named.after:
            label.set_text(named.before)
    moved: set[GridSpec] = set()
    laid = record.laid
    gs = None if laid is None else laid.grid()
    if laid is not None and gs is not None and grid_edges(gs) == laid.left:
        gs.update(**dict(zip(SIDES, laid.start, strict=True)))
        moved.add(gs)
    for gs, set_here in record.gaps.items():
        for key, value in set_here.items():
            if spacing_of(gs, key) == value:
                set_spacing(gs, key, None)
                moved.add(gs)
    for gs in moved:
        place(fig, gs)


def remember(fig: Figure, gs: GridSpec, start: Optional4) -> None:
    """While the edges stay as this layout left them, the next starts from
    ``start`` again: where a fit starts decides its last hundredths of a px."""
    record_of(fig).laid = Laid(weakref.ref(gs), start, grid_edges(gs))


# -- text ---------------------------------------------------------------------


def _wrap(axis: Axis, lines: Mapping[Line, Line]) -> Callable[[], None]:
    fmt = axis.get_major_formatter()
    before = (fmt, axis.isDefault_majfmt)
    base = fmt
    if isinstance(fmt, WrappedTickFormatter):
        _unwrap(axis, fmt)
        base = fmt.base
    if lines:
        axis.set_major_formatter(
            WrappedTickFormatter(base, {**lines}, axis.isDefault_majfmt)
        )

    def undo() -> None:
        axis.set_major_formatter(before[0])
        axis.isDefault_majfmt = before[1]

    return undo


def _turn(axis: Axis, angle: Degrees, record: Record) -> Callable[[], None]:
    """Turn the bottom labels (the top ones stay), ends at their ticks."""
    labels = [tick.label1 for tick in axis.get_major_ticks()]
    before: list[tuple[Text, float, Mode, Turned | None]] = [
        (
            t,
            float(t.get_rotation()),
            t.get_rotation_mode(),
            record.turned.get(t),
        )
        for t in labels
    ]
    axis_before = record.axis_turns.get(axis)
    for label, rotation, mode, old in before:
        first = old or Turned(angle, rotation, mode)
        record.turned[label] = Turned(angle, first.rotation, first.mode)
        label.set_rotation(angle)
        label.set_rotation_mode(TURN_MODE)
    record.axis_turns[axis] = record.turned[labels[0]]

    def undo() -> None:
        for label, rotation, mode, old in before:
            label.set_rotation(rotation)
            label.set_rotation_mode(mode)
            if old is None:
                record.turned.pop(label, None)
            else:
                record.turned[label] = old
        if axis_before is None:
            record.axis_turns.pop(axis, None)
        else:
            record.axis_turns[axis] = axis_before

    return undo


def _name(
    label: Text, text: Line, group: tuple[ArtistId, Which], record: Record
) -> Callable[[], None]:
    before = label.get_text()
    record.names[label] = Named(before, text, group)
    label.set_text(text)

    def undo() -> None:
        label.set_text(before)
        record.names.pop(label, None)

    return undo


def set_spacing(gs: GridSpec, key: Gap, value: float | None) -> None:
    """Set ``gs``'s ``wspace`` / ``hspace`` (``None``: the figure's)."""
    match key:
        case WSpace():
            gs.update(wspace=value)
        case HSpace():
            gs.update(hspace=value)
        case _:
            assert_never(key)


def _space(
    gs: GridSpec, key: Gap, gap: Share, record: Record
) -> Callable[[], None]:
    before = spacing_of(gs, key)
    set_spacing(gs, key, gap)
    record.gaps_of(gs)[key] = gap

    def undo() -> None:
        set_spacing(gs, key, before)
        if before is None:
            record.gaps_of(gs).pop(key, None)
        else:
            record.gaps_of(gs)[key] = Share(before)

    return undo


def text(
    gs: GridSpec,
    plan: TextPlan,
    objects: TextArtists,
    groups: Mapping[ArtistId, tuple[ArtistId, Which]],
    record: Record,
) -> Callable[[], None]:
    """Apply ``plan``; the returned call takes all of it back."""
    undos = [
        _name(objects.labels[k], v, groups[k], record)
        for k, v in plan.names.items()
    ]
    undos += [_space(gs, k, v, record) for k, v in plan.spacing.items()]
    undos += [_wrap(objects.axes[k], v) for k, v in plan.wraps.items()]
    undos += [_turn(objects.axes[k], v, record) for k, v in plan.turns.items()]

    def undo() -> None:
        for step in reversed(undos):
            step()

    return undo
