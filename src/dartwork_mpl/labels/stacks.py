"""Which of a ``label_bars`` call's containers stack, read from their bars.

Containers at the same positions, each starting where the ones before it
ended (``bottom=`` / ``left=``), pile up; a pile with two non-zero bars
standing together somewhere is a stack. Pure: positions and lengths in,
piles out.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TypeAlias

import numpy as np
import numpy.typing as npt

from .model import Kind, Total

FloatArray: TypeAlias = npt.NDArray[np.float64]
# Relative slack for "the same position" and "starts at the running end":
# the caller's running sums and ours may round differently.
REL_TOL = 1e-9


@dataclass(frozen=True)
class BarRun:
    """One container's bars: middle across, start and signed length along
    the value axis, and value (NaN: not drawn). ``host`` tells plot areas
    and orientations apart."""

    centres: tuple[float, ...]
    starts: tuple[float, ...]
    lengths: tuple[float, ...]
    values: tuple[float, ...]
    host: tuple[object, ...]

    def arrays(self) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
        """Centres, starts, lengths and values as float arrays."""
        c, s, n, v = (
            np.asarray(x, dtype=float)
            for x in (self.centres, self.starts, self.lengths, self.values)
        )
        return c, s, n, v

    def standing(self) -> npt.NDArray[np.bool_]:
        """The bars drawn: finite value, start and length."""
        _c, s, n, v = self.arrays()
        return np.isfinite(v) & np.isfinite(s) & np.isfinite(n)


def _same(a: FloatArray, b: FloatArray) -> npt.NDArray[np.bool_]:
    return np.abs(a - b) <= REL_TOL * np.maximum(np.abs(a), np.abs(b))


@dataclass(eq=False)
class Pile:
    """Containers piled at the same positions, each starting on the running
    ends of the ones before it (``bottom=`` / ``left=``)."""

    host: tuple[object, ...]
    centres: FloatArray
    high: FloatArray
    low: FloatArray
    together: npt.NDArray[np.int_]
    members: list[int] = field(default_factory=list)
    zeros: list[npt.NDArray[np.bool_]] = field(default_factory=list)

    @property
    def stacked(self) -> bool:
        """Two bars of non-zero length stand together somewhere."""
        return bool(np.any(self.together >= 2))

    def takes(self, run: BarRun) -> bool:
        """Whether ``run`` starts on this pile's running ends."""
        centres, starts, lengths, _v = run.arrays()
        if run.host != self.host or centres.shape != self.centres.shape:
            return False
        if not np.all(_same(centres, self.centres)):
            return False
        on_high, on_low = _same(starts, self.high), _same(starts, self.low)
        fits = np.where(
            lengths > 0,
            on_high,
            np.where(lengths < 0, on_low, on_high | on_low),
        )
        return bool(np.all(fits[run.standing() & np.isfinite(self.high)]))

    def add(self, i: int, run: BarRun) -> None:
        """Pile container ``i``'s bars onto the running ends."""
        _c, starts, lengths, _v = run.arrays()
        standing = run.standing()
        first = standing & np.isnan(self.high)
        self.high[first] = starts[first]
        self.low[first] = starts[first]
        up, down = standing & (lengths > 0), standing & (lengths < 0)
        self.high[up] = (starts + lengths)[up]
        self.low[down] = (starts + lengths)[down]
        self.together += up | down
        self.members.append(i)
        self.zeros.append(standing & (lengths == 0))

    def padding(self) -> set[tuple[int, int]]:
        """Zero bars beside a non-zero bar (or an earlier zero) there."""
        out: set[tuple[int, int]] = set()
        seen = self.together > 0
        for i, zero in zip(self.members, self.zeros, strict=True):
            out.update((i, int(j)) for j in np.flatnonzero(zero & seen))
            seen = seen | zero
        return out


@dataclass(frozen=True)
class Planned:
    """One label to make: on bar ``index`` of container ``run``."""

    run: int
    index: int
    kind: Kind
    value: float
    stack: int | None = None


@dataclass(frozen=True)
class BarsFacts:
    """A ``label_bars`` call's containers and what it asked for."""

    runs: tuple[BarRun, ...]
    total: Total

    def piles(self) -> list[Pile]:
        """Each container joins the first pile it starts on, or starts one."""
        piles: list[Pile] = []
        for i, run in enumerate(self.runs):
            if not run.centres:
                continue
            pile = next((p for p in piles if p.takes(run)), None)
            if pile is None:
                centres = run.arrays()[0]
                unknown = np.full(centres.shape, np.nan)
                pile = Pile(
                    run.host,
                    centres,
                    unknown,
                    unknown.copy(),
                    np.zeros(centres.shape, dtype=int),
                )
                piles.append(pile)
            pile.add(i, run)
        return piles

    def total_at(
        self, members: list[int], index: int, stack: int
    ) -> Planned | None:
        """The stack's net at ``index``, on the container whose bar ends the
        stack on the side the net points to (``None``: no bar there)."""
        ends = []
        for i in members:
            run = self.runs[i]
            value, end = (
                run.values[index],
                run.starts[index] + run.lengths[index],
            )
            if math.isfinite(value) and math.isfinite(end):
                ends.append((i, value, end))
        if not ends:
            return None
        net = math.fsum(v for _, v, _ in ends)
        side = [e for e in ends if (e[1] >= 0) == (net >= 0)]
        outer = max(side, key=lambda e: e[2] if net >= 0 else -e[2])
        return Planned(outer[0], index, "total", net, stack)


@dataclass(frozen=True)
class BarsPlan:
    """The labels to make, containers in order, then the stacks' totals."""

    labels: tuple[Planned, ...]
