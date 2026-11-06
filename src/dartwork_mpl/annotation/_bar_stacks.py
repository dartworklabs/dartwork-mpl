"""Which bar containers of a :func:`~._bar_labels.label_bars` call stack.

A stack is two or more containers drawn on one Axes, in one orientation, at
the same positions, each starting where the ones before it ended: at every
position a positive bar starts on the positive end, a negative bar on the
negative end, as callers build stacks with ``ax.bar(x, v, bottom=...)``
(``barh``: ``left=``). A zero bar may start on either end; a bar whose value
or start is not finite (NaN) is not drawn and adds nothing.

Floating bars, which start anywhere else (a waterfall, ranges, bars overlaid
from one base), form no stack, and neither do bars at other positions
(grouped bars). A stack's label at each position is its net sum, written
beyond the end the net points to (:meth:`BarStack.total`).
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

__all__ = ["BarStack", "bar_values", "find_stacks"]

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
    """Elementwise equal within ``_REL_TOL`` of the values' magnitude."""
    both = np.abs(np.concatenate([a, b]))
    finite = both[np.isfinite(both)]
    scale = float(finite.max()) if finite.size else 0.0
    return np.abs(a - b) <= _REL_TOL * scale


def _axes_of(container: BarContainer) -> object:
    """The Axes the container's bars are drawn on (``None``: no bars)."""
    return container.patches[0].axes if container.patches else None


@dataclass(eq=False)
class _Pile:
    """Containers stacked so far, with the running ends at each position."""

    axes: object
    orientation: str | None
    centres: FloatArray
    high: FloatArray  # the positive end; NaN until a bar stands there
    low: FloatArray  # the negative end
    containers: list[BarContainer] = field(default_factory=list)

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
        )
        pile.add(container)
        return pile

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
        self.containers.append(container)


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


def find_stacks(containers: Iterable[BarContainer]) -> list[BarStack]:
    """The stacks among ``containers``, in the order their bases come.

    Each container joins the first stack whose running ends it starts on,
    or starts its own; only piles of two or more containers are stacks.
    """
    piles: list[_Pile] = []
    for container in containers:
        pile = next((p for p in piles if p.takes(container)), None)
        if pile is None:
            piles.append(_Pile.start(container))
        else:
            pile.add(container)
    return [BarStack(p.containers) for p in piles if len(p.containers) > 1]
