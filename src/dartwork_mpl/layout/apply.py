"""Write the layout's plan into the figure, and undo it on the next call.

What a layout sets (grid edges, wrapped tick labels and names, turned tick
labels, panel spacing) is kept in one :class:`Record` on the figure. The
next ``simple_layout`` first puts back whatever is still as it set it, so a
second call fits the figure as its author left it and draws the same.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from matplotlib.axis import Axis
from matplotlib.gridspec import GridSpec
from matplotlib.text import Text
from matplotlib.ticker import Formatter

from .measure import grid_axes
from .model import ArtistId, Degrees, Edges, Gap, Line, Share, TextPlan, Which

if TYPE_CHECKING:
    from matplotlib.figure import Figure

RECORD_ATTR = "_dm_layout_record"
SIDES = ("left", "right", "bottom", "top")
Optional4 = tuple[float | None, float | None, float | None, float | None]
Mode = Literal["default", "anchor", "xtick", "ytick"]


class WrappedTickFormatter(Formatter):
    """The axis' own formatter with line breaks in some labels (``lines``)."""

    def __init__(
        self, base: Formatter, lines: Mapping[str, str], base_default: bool
    ) -> None:
        """Wrap ``base``; ``base_default``: the axis' default flag before."""
        self.base = base
        self.lines = dict(lines)
        self.base_default = base_default

    def __call__(self, x: float, pos: int | None = None) -> str:
        """The base formatter's label, wrapped where ``lines`` says."""
        text = self.base(x, pos)
        return self.lines.get(text, text)

    def format_ticks(self, values: list[float]) -> list[str]:
        """As the base formatter."""
        return [self.lines.get(t, t) for t in self.base.format_ticks(values)]

    def set_locs(self, locs: list[float]) -> None:
        """As the base formatter."""
        self.base.set_locs(locs)

    def get_offset(self) -> str:
        """As the base formatter."""
        return self.base.get_offset()

    def format_data(self, value: float) -> str:
        """As the base formatter."""
        return self.base.format_data(value)

    def format_data_short(self, value: float) -> str:
        """As the base formatter."""
        return self.base.format_data_short(value)

    def set_axis(self, axis: Any) -> None:
        """As the base formatter."""
        super().set_axis(axis)
        self.base.set_axis(axis)


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


@dataclass
class Record:
    """Everything one layout set on a figure, to undo on the next."""

    turned: dict[Text, Turned] = field(default_factory=dict)
    axis_turns: dict[Axis, Turned] = field(default_factory=dict)
    names: dict[Text, Named] = field(default_factory=dict)
    gaps: dict[tuple[GridSpec, Gap], Share] = field(default_factory=dict)
    laid: tuple[GridSpec, Optional4, Optional4] | None = None


def record_of(fig: Figure) -> Record:
    """The record of what this layout set on ``fig``."""
    record = getattr(fig, RECORD_ATTR, None)
    if not isinstance(record, Record):
        record = Record()
        setattr(fig, RECORD_ATTR, record)
    return record


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
        position = spec.get_position(ax.get_figure(root=False))  # type: ignore[arg-type]
        if ax.get_position(original=True).bounds != position.bounds:
            ax.set_subplotspec(spec)


def _unwrap(axis: Axis, wrapper: WrappedTickFormatter) -> None:
    axis.set_major_formatter(wrapper.base)
    axis.isDefault_majfmt = wrapper.base_default


def restore(fig: Figure) -> None:
    """Undo what the last layout set, where it is still as set."""
    record = getattr(fig, RECORD_ATTR, None)
    if isinstance(record, Record):
        delattr(fig, RECORD_ATTR)
    else:
        record = Record()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            fmt = axis.get_major_formatter()
            if isinstance(fmt, WrappedTickFormatter):
                _unwrap(axis, fmt)
            first = record.axis_turns.get(axis)
            for tick in axis.get_major_ticks():
                label = tick.label1
                turn = record.turned.get(label) or first
                if turn is not None and (
                    float(label.get_rotation()),
                    label.get_rotation_mode(),
                ) == (turn.angle, "xtick"):
                    label.set_rotation(turn.rotation)
                    label.set_rotation_mode(turn.mode)
    for label, named in record.names.items():
        if label.get_text() == named.after:
            label.set_text(named.before)
    moved: set[GridSpec] = set()
    if record.laid is not None:
        gs, start, left = record.laid
        if grid_edges(gs) == left:
            gs.update(**dict(zip(SIDES, start, strict=True)))
            moved.add(gs)
    for (gs, key), value in record.gaps.items():
        if getattr(gs, key.value) == value:
            gs.update(**{key.value: None})
            moved.add(gs)
    for gs in moved:
        place(fig, gs)


def remember(fig: Figure, gs: GridSpec, start: Optional4) -> None:
    """While the edges stay as this layout left them, the next starts from
    ``start`` again: where a fit starts decides its last hundredths of a px."""
    record_of(fig).laid = (gs, start, grid_edges(gs))


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
        label.set_rotation_mode("xtick")
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


def _space(
    gs: GridSpec, key: Gap, gap: Share, record: Record
) -> Callable[[], None]:
    before = getattr(gs, key.value)
    gs.update(**{key.value: gap})
    record.gaps[(gs, key)] = gap

    def undo() -> None:
        gs.update(**{key.value: before})
        if before is None:
            record.gaps.pop((gs, key), None)
        else:
            record.gaps[(gs, key)] = before

    return undo


def text(
    gs: GridSpec,
    plan: TextPlan,
    objects: Mapping[int, Any],
    groups: Mapping[ArtistId, tuple[ArtistId, Which]],
    record: Record,
) -> Callable[[], None]:
    """Apply ``plan``; the returned call takes all of it back."""
    undos = [
        _name(objects[k], v, groups[k], record) for k, v in plan.names.items()
    ]
    undos += [_space(gs, k, v, record) for k, v in plan.spacing.items()]
    undos += [_wrap(objects[k], v) for k, v in plan.wraps.items()]
    undos += [_turn(objects[k], v, record) for k, v in plan.turns.items()]

    def undo() -> None:
        for step in reversed(undos):
            step()

    return undo
