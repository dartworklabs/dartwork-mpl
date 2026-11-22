"""Write the layout's plan into the figure: grid edges, wrapped tick labels
and names, turned tick labels, panel spacing.

A second ``simple_layout`` first puts upright the labels the first turned
and reads our wrap through it; a wrapped name and a spacing it set stay as
the author's.
"""

from __future__ import annotations

import logging
import weakref
from collections.abc import Mapping
from typing import TYPE_CHECKING, assert_never

from matplotlib.gridspec import GridSpec
from matplotlib.ticker import Formatter

from ..hidden import axes_name
from .measure import cartesian, grid_axes
from .model import (
    FACING,
    TURN_MODE,
    HSpace,
    Sides,
    TextPlan,
    WSpace,
    tick_spine,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.axis import Axis
    from matplotlib.figure import Figure

    from .model import Degrees, Gap, Line, Share
    from .text import TextArtists

LOG = logging.getLogger("dartwork_mpl.layout")

#: The Axes whose scale spines a layout has seen to: shown once, they are
#: the caller's to hide again.
SPINES_SEEN: weakref.WeakSet[Axes] = weakref.WeakSet()

#: The angle a layout last turned each x axis' bottom labels to, to tell its
#: turn from the caller's. Kept per axis: matplotlib makes new ticks as the
#: view changes, the axis stays.
_TURNED: weakref.WeakKeyDictionary[Axis, Degrees] = weakref.WeakKeyDictionary()


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


def write_edges(fig: Figure, gs: GridSpec, edges: Sides) -> None:
    """Give ``gs`` the edges and move its Axes there.

    ``GridSpec.update`` moves only the Axes of pyplot's open figures; any
    other figure's Axes follow their SubplotSpec here.
    """
    gs.update(
        left=edges.left, right=edges.right, bottom=edges.bottom, top=edges.top
    )
    for ax in grid_axes(fig, gs):
        spec = ax.get_subplotspec()
        if spec is None:
            continue
        position = spec.get_position(fig)
        if ax.get_position(original=True).bounds != position.bounds:
            ax.set_subplotspec(spec)


def _wrap(axis: Axis, lines: Mapping[Line, Line]) -> None:
    """Our wrap of ``axis``' labels (none: the formatter as it was)."""
    fmt = axis.get_major_formatter()
    if isinstance(fmt, WrappedTickFormatter):
        axis.set_major_formatter(fmt.base)
        axis.isDefault_majfmt = fmt.base_default
        fmt = fmt.base
    if lines:
        default = axis.isDefault_majfmt
        axis.set_major_formatter(WrappedTickFormatter(fmt, {**lines}, default))


def show_scale_spines(fig: Figure) -> None:
    """Show the hidden spine an axis ticks on while the facing one shows:
    a ``twinx`` draws its scale on the right, which the presets hide, and
    without the spine its tick marks read as minus signs. An Axes with no
    frame on that axis (a colorbar, the minimal look) stays as it is. Once
    per Axes: a spine hidden after the first layout stays hidden."""
    for ax in fig.axes:
        if not cartesian(ax) or ax in SPINES_SEEN:
            continue
        SPINES_SEEN.add(ax)
        for axis in (ax.xaxis, ax.yaxis):
            side = tick_spine(axis.get_ticks_position())
            if side is None or not axis.get_visible():
                continue
            spine = ax.spines[side]
            if (
                ax.spines[FACING[side]].get_visible()
                and not spine.get_visible()
            ):
                spine.set_visible(True)
                LOG.info(
                    "showed the %s spine of %s: its %s axis ticks on that "
                    "side, and without the spine its tick marks read as minus "
                    'signs; hide it again with ax.spines["%s"].set_visible(False)',
                    side,
                    axes_name(ax),
                    "x" if axis is ax.xaxis else "y",
                    side,
                )


def turned(axis: Axis) -> Degrees | None:
    """The angle a layout turned ``axis``' bottom labels to, while they still
    read so (``None``: not turned, or turned since by the caller)."""
    angle = _TURNED.get(axis)
    ticks = axis.get_major_ticks()
    if angle is None or not ticks:
        return None
    label = ticks[0].label1
    if float(label.get_rotation()) != angle:
        return None
    return angle if label.get_rotation_mode() == TURN_MODE else None


def unturn(fig: Figure) -> None:
    """Put back upright the tick labels a previous layout turned, so a
    second call fits the labels as they read now. Labels the caller turned
    stay as they are, at any angle and mode."""
    for ax in fig.axes:
        axis = ax.xaxis
        angle = turned(axis)
        _TURNED.pop(axis, None)
        if angle is None:
            continue
        for tick in axis.get_major_ticks():
            label = tick.label1
            if float(label.get_rotation()) == angle:
                label.set_rotation(0.0)
                label.set_rotation_mode("default")


def _turn(axis: Axis, angle: Degrees) -> None:
    """Turn the bottom labels (the top ones stay), ends at their ticks."""
    for tick in axis.get_major_ticks():
        tick.label1.set_rotation(angle)
        tick.label1.set_rotation_mode(TURN_MODE)
    _TURNED[axis] = angle


def unspace(gs: GridSpec, key: Gap) -> None:
    """Give ``key`` back to the figure's spacing (``gs`` sets none)."""
    match key:
        case WSpace():
            gs.update(wspace=None)
        case HSpace():
            gs.update(hspace=None)
        case _:
            assert_never(key)


def _space(gs: GridSpec, key: Gap, value: Share) -> None:
    match key:
        case WSpace():
            gs.update(wspace=value)
        case HSpace():
            gs.update(hspace=value)
        case _:
            assert_never(key)


def text(gs: GridSpec, plan: TextPlan, objects: TextArtists) -> None:
    """Apply ``plan``."""
    for k, name in plan.names.items():
        objects.labels[k].set_text(name)
    for key, value in plan.spacing.items():
        _space(gs, key, value)
    for k, lines in plan.wraps.items():
        _wrap(objects.axes[k], lines)
    for k, angle in plan.turns.items():
        _turn(objects.axes[k], angle)
