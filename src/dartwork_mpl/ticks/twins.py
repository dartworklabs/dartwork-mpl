"""An Axes and its twins: which scale each draws, and the spines a layout showed.

A ``twinx`` / ``twiny`` pair shares one box; each twin draws the scale on its
own side and hides the other. The facts here say which twin owns which
side, read from public state, and remember the twin spines a layout showed.
"""

from __future__ import annotations

import weakref
from collections.abc import Sequence

from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.figure import Figure

from ..geometry import (
    axis_of,
    label_side,
    projection,
    same_position_axes,
    shared_axes,
)
from ..vocab import Curved, Far, Near, Rectilinear, ThreeD, Which, X, Y
from .axis_plans import AxesFacts, TwinFacts
from .measure import axis_facts, with_insets
from .model import TWIN_SIDES, RightSide, TopSide, TwinSide, YearDigits

# The sides of each Axes whose twin spine a layout showed (or found showing).
SETTLED: weakref.WeakKeyDictionary[Axes, set[TwinSide]] = (
    weakref.WeakKeyDictionary()
)


def _scale(side: TwinSide) -> Which:
    """The axis whose scale sits on ``side`` (a twin hides the other)."""
    match side:
        case RightSide():
            return Y()
        case TopSide():
            return X()


def plain(ax: Axes) -> bool:
    """Whether ``ax`` is matplotlib's plain 2D Axes."""
    match projection(ax):
        case Rectilinear():
            return True
        case ThreeD() | Curved():
            return False


def _rectilinear(ax: Axes) -> bool:
    return ax.get_visible() and plain(ax)


def boxes(fig: Figure) -> dict[Axes, list[Axes]]:
    """Each visible rectilinear Axes drawn in a box with others, and that box.

    Walked with insets, depth first: an inset is not in ``fig.axes`` but its
    ``twinx`` is, so the inset finds its twin and the twin its box.
    """
    found: dict[Axes, list[Axes]] = {}
    for ax in with_insets(fig.axes):
        if ax in found or not _rectilinear(ax):
            continue
        group = [m for m in same_position_axes(ax) if _rectilinear(m)]
        if len(group) >= 2:
            found.update(dict.fromkeys(group, group))
    return found


def _owns(ax: Axes, group: Sequence[Axes], scale: Which) -> bool:
    """``ax`` shows its ``scale`` axis, which no box member shares while the other is shared."""
    shared_other = shared_axes(ax, scale.other)
    shared_scale = shared_axes(ax, scale)
    return axis_of(ax, scale).get_visible() and any(
        m is not ax and m in shared_other and m not in shared_scale
        for m in group
    )


def _far_side(axis: Axis) -> bool:
    """Tick labels (else marks) show on the right / top and not the left / bottom."""
    tick = (axis.get_major_ticks() or axis.get_major_ticks(1))[0]
    labels = (tick.label1.get_visible(), tick.label2.get_visible())
    marks = (tick.tick1line.get_visible(), tick.tick2line.get_visible())
    near, far = labels if any(labels) else marks
    return far and not near


def _draws(ax: Axes, group: Sequence[Axes], side: TwinSide) -> bool:
    """``ax`` draws its own scale on ``side``: ticks and label there (one, for a twin)."""
    scale = _scale(side)
    other = scale.other
    if not _owns(ax, group, scale):
        return False
    axis = axis_of(ax, scale)
    match label_side(axis):
        case Far():
            label = True
        case Near():
            label = False
    ticks = _far_side(axis)
    if axis_of(ax, other).get_visible():
        return ticks and label
    return ticks or label


def twin_facts(ax: Axes, group: Sequence[Axes]) -> TwinFacts:
    """How ``ax`` and its box draw twin scales on the right and the top."""
    if len(group) < 2:
        return TwinFacts()
    draws: set[TwinSide] = set()
    hides: set[TwinSide] = set()
    twin_draws: set[TwinSide] = set()
    for side in TWIN_SIDES:
        other = _scale(side).other
        if _draws(ax, group, side):
            draws.add(side)
        if not axis_of(ax, other).get_visible():
            hides.add(side)
        if any(
            _draws(m, group, side) and not axis_of(m, other).get_visible()
            for m in group
        ):
            twin_draws.add(side)
    return TwinFacts(
        frozenset(draws),
        frozenset(hides),
        frozenset(twin_draws),
        settled_twin_spines(ax),
    )


def axes_facts(
    ax: Axes, digits: YearDigits, box: Sequence[Axes] = ()
) -> AxesFacts:
    """An Axes before the layout, drawn in ``box`` with its twins."""
    twin = twin_facts(ax, box)
    return AxesFacts(axis_facts(ax, X()), axis_facts(ax, Y()), digits, twin)


def settled_twin_spines(ax: Axes) -> frozenset[TwinSide]:
    """The sides of ``ax`` whose twin spine a layout showed (or found showing)."""
    return frozenset(SETTLED.get(ax, ()))


def settle_twin_spine(ax: Axes, side: TwinSide) -> None:
    """Record that a layout showed the twin spine on ``side`` of ``ax``."""
    SETTLED.setdefault(ax, set()).add(side)
