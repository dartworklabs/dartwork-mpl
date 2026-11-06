"""Which bar containers of a :func:`~._bar_labels.label_bars` call stack.

Containers drawn on one Axes, in one orientation, at the same positions,
each starting where the ones before it ended, pile up: at every position a
positive bar starts on the positive end, a negative bar on the negative end,
as callers build stacks with ``ax.bar(x, v, bottom=...)`` (``barh``:
``left=``). A zero bar may start on either end; a bar whose value or start
is not finite (NaN) is not drawn and adds nothing. "Where it ended" allows
for rounding: 1e-9 of the two values compared.

A pile is a **stack** when, at some position, two bars of non-zero length
stand together. Containers that never do (a two-colour waterfall's rises
and falls, a highlight split into grey and an accent, an all-NaN container)
pile up without stacking: their bars are labelled as plain bars. Floating
bars, which start anywhere else (a waterfall, ranges, bars overlaid from
one base), and bars at other positions (grouped bars) do not pile at all.

In any pile, a zero bar beside a non-zero bar at its position pads the
position and gets no label; where every bar is zero, the first one keeps
its label. A stack's label at each position is its net sum, written beyond
the end the net points to (:meth:`BarStack.total`).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    from matplotlib.container import BarContainer
    from matplotlib.patches import Rectangle

__all__ = ["BarPiles", "BarStack", "bar_values", "pile_bars"]

FloatArray = npt.NDArray[np.float64]

# Relative slack for "the same position" and "starts at the running end":
# the caller's running sums and ours may round differently.
_REL_TOL = 1e-9


def bar_values(container: BarContainer) -> FloatArray:
    """The container's values; masked (``np.ma``) values read as NaN."""
    return np.ma.filled(
        np.ma.asarray(container.datavalues, dtype=float), np.nan
    )


def _bar(
    patch: Rectangle, orientation: str | None
) -> tuple[float, float, float]:
    """A bar's position (its middle), start and signed length."""
    x, y = float(patch.get_x()), float(patch.get_y())
    width, height = float(patch.get_width()), float(patch.get_height())
    if orientation == "vertical":
        return (x + width / 2, y, height)
    return (y + height / 2, x, width)


class _Geometry(NamedTuple):
    """Each bar's position, start and signed length along the value axis."""

    centres: FloatArray
    starts: FloatArray
    lengths: FloatArray


def _geometry(container: BarContainer) -> _Geometry:
    rows = [_bar(p, container.orientation) for p in container.patches]
    table = np.asarray(rows, dtype=float).reshape(-1, 3)
    return _Geometry(table[:, 0], table[:, 1], table[:, 2])


def _same(a: FloatArray, b: FloatArray) -> npt.NDArray[np.bool_]:
    """Elementwise equal within ``_REL_TOL`` of the larger of each pair."""
    return np.abs(a - b) <= _REL_TOL * np.maximum(np.abs(a), np.abs(b))


def _axes_of(container: BarContainer) -> object:
    """The Axes the container's bars are drawn on (``None``: no bars)."""
    return container.patches[0].axes if container.patches else None


@dataclass(eq=False)
class _Pile:
    """Containers piled so far, with the running ends at each position."""

    axes: object
    orientation: str | None
    centres: FloatArray
    high: FloatArray  # the positive end; NaN until a bar stands there
    low: FloatArray  # the negative end
    # How many bars of non-zero length stand at each position.
    together: npt.NDArray[np.int_]
    containers: list[BarContainer] = field(default_factory=list)
    # Per container: which of its bars stand with zero length.
    zeros: list[npt.NDArray[np.bool_]] = field(default_factory=list)

    @classmethod
    def start(cls, container: BarContainer) -> _Pile:
        centres = _geometry(container).centres
        unknown = np.full(centres.shape, np.nan)
        pile = cls(
            _axes_of(container),
            container.orientation,
            centres,
            unknown,
            unknown.copy(),
            np.zeros(centres.shape, dtype=int),
        )
        pile.add(container)
        return pile

    @property
    def stacked(self) -> bool:
        """Whether two bars of non-zero length stand together somewhere."""
        return bool(np.any(self.together >= 2))

    def padding(self) -> set[tuple[int, int]]:
        """``(id(container), index)`` of the zero bars that pad a position.

        A zero bar pads when a non-zero bar stands at its position, or when
        an earlier zero bar of the pile already stands there.
        """
        out: set[tuple[int, int]] = set()
        seen = self.together > 0
        for container, zero in zip(self.containers, self.zeros, strict=True):
            out.update(
                (id(container), int(i)) for i in np.flatnonzero(zero & seen)
            )
            seen = seen | zero
        return out

    def takes(self, container: BarContainer) -> bool:
        """Whether ``container`` starts on this pile's running ends."""
        if (
            not container.patches
            or _axes_of(container) is not self.axes
            or container.orientation != self.orientation
        ):
            return False
        bars = _geometry(container)
        if bars.centres.shape != self.centres.shape or not np.all(
            _same(bars.centres, self.centres)
        ):
            return False
        on_high = _same(bars.starts, self.high)
        on_low = _same(bars.starts, self.low)
        fits = np.where(
            bars.lengths > 0,
            on_high,
            np.where(bars.lengths < 0, on_low, on_high | on_low),
        )
        checked = _standing(container, bars) & np.isfinite(self.high)
        return bool(np.all(fits[checked]))

    def add(self, container: BarContainer) -> None:
        bars = _geometry(container)
        standing = _standing(container, bars)
        first = standing & np.isnan(self.high)
        self.high[first] = bars.starts[first]
        self.low[first] = bars.starts[first]
        ends = bars.starts + bars.lengths
        up = standing & (bars.lengths > 0)
        down = standing & (bars.lengths < 0)
        self.high[up] = ends[up]
        self.low[down] = ends[down]
        self.together += up | down
        self.containers.append(container)
        self.zeros.append(standing & (bars.lengths == 0))


def _standing(
    container: BarContainer, bars: _Geometry
) -> npt.NDArray[np.bool_]:
    """The bars that are drawn: finite value, start and length."""
    return (
        np.isfinite(bar_values(container))
        & np.isfinite(bars.starts)
        & np.isfinite(bars.lengths)
    )


class _Segment(NamedTuple):
    container: BarContainer
    value: float
    end: float


@dataclass(eq=False)
class BarStack:
    """Containers stacked at the same positions, the base container first."""

    containers: list[BarContainer]

    def segments(self, index: int) -> list[_Segment]:
        """The bars standing at position ``index``, base first."""
        out = []
        for container in self.containers:
            value = float(bar_values(container)[index])
            _, start, length = _bar(
                container.patches[index], container.orientation
            )
            if math.isfinite(value) and math.isfinite(start + length):
                out.append(_Segment(container, value, start + length))
        return out

    def total(self, index: int) -> tuple[float, BarContainer] | None:
        """The net sum at ``index`` and the container whose bar ends the stack
        on the side the net points to (``None`` when no bar stands there).

        A net of zero or more points to the positive end (the farthest end
        of the positive and zero bars), a negative net to the negative end.
        """
        segments = self.segments(index)
        if not segments:
            return None
        net = math.fsum(s.value for s in segments)
        if net >= 0:
            outer = max(
                (s for s in segments if s.value >= 0), key=lambda s: s.end
            )
        else:
            outer = min(
                (s for s in segments if s.value < 0), key=lambda s: s.end
            )
        return net, outer.container


class BarPiles(NamedTuple):
    """How a call's containers pile up."""

    #: The stacks, in the order their bases come.
    stacks: list[BarStack]
    #: ``(id(container), index)`` of the zero bars that get no label.
    padding: frozenset[tuple[int, int]]


def pile_bars(containers: Iterable[BarContainer]) -> BarPiles:
    """The stacks among ``containers`` and the zero bars that pad them.

    Each container joins the first pile whose running ends it starts on,
    or starts its own; a pile is a stack when two bars of non-zero length
    stand together at some position.
    """
    piles: list[_Pile] = []
    for container in containers:
        pile = next((p for p in piles if p.takes(container)), None)
        if pile is None:
            piles.append(_Pile.start(container))
        else:
            pile.add(container)
    return BarPiles(
        [BarStack(p.containers) for p in piles if p.stacked],
        frozenset().union(*(p.padding() for p in piles)),
    )
