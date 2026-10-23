"""Tick formatters that settle one unit and one decimal count per axis.

The ``decimals=None`` default of ``format_axis_si`` / ``_millions`` /
``_billions`` / ``_myriad`` installs :class:`AxisUnitFormatter`. A fixed
``.1f`` turns integer ticks into ``200.0`` and ``1.0k``, rounds half steps
such as ``1250`` to ``1.2k``, and a per-tick unit mixes ``800`` with
``1.2k`` on one axis. This formatter decides once per axis, from the ticks
the axis actually shows:

- **One unit for the whole axis**, picked from a unit ladder (none/k/M/G/T,
  or none/만/억/조/경) by a rule: ``"max"`` takes the unit of the largest
  visible ``|tick|``, so digit counts read at a glance; ``"whole"`` takes a
  unit in which every tick is a whole number; a ladder label fixes the unit.
- **One decimal count for the whole axis**: the fewest decimals that render
  every scaled tick exactly and distinctly, so integer ticks print none and
  fractional steps keep the same count on every tick (``0.5M, 1.0M``).
- Zero prints as ``0``; numbers of 1000 and more carry thousands separators.

On log and other non-linear scales the ticks span decades, which cannot
share one unit (``0.000001k`` beside ``1,000k``), so there each tick takes
its own unit and the fewest decimals it needs (``0.1, 1, 10, 1k``).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import matplotlib.ticker as ticker
import numpy as np

from ._decimals import fewest_exact_decimals

__all__ = ["UNIT_RULES", "AxisUnitFormatter", "Unit"]

UNIT_RULES = ("max", "whole")
"""Unit rules besides naming one ladder label."""

_TOL = 1e-9


@dataclass(frozen=True)
class Unit:
    """One rung of a unit ladder: divide by ``factor``, append ``label``."""

    factor: float
    label: str


@dataclass(frozen=True)
class _Plan:
    """One axis decision.

    ``axis_unit`` is ``None`` on a non-linear axis (a unit per tick);
    ``decimals`` is ``None`` when each tick settles its own.
    """

    axis_unit: Unit | None
    decimals: int | None


class AxisUnitFormatter(ticker.Formatter):
    """Format ticks with one unit and one decimal count per axis.

    ``unit`` is ``"max"`` (the unit of the largest visible ``|tick|``),
    ``"whole"`` (a unit in which every visible tick is whole; of those, the
    one with the shortest longest label; with no such unit, the fewest
    decimals) or one ladder label (that unit, always). ``decimals`` fixes
    the decimal count instead of choosing it.

    The decision is made in :meth:`set_locs`, which :meth:`format_ticks`
    calls with every major tick on each draw; only ticks inside the view
    interval vote. Called without a draw, a value decides for itself.
    """

    def __init__(
        self,
        ladder: Sequence[Unit],
        unit: str = "max",
        *,
        decimals: int | None = None,
        currency: str = "",
    ) -> None:
        self._ladder = tuple(sorted(ladder, key=lambda rung: rung.factor))
        self._fixed = next(
            (rung for rung in self._ladder if rung.label == unit), None
        )
        if unit not in UNIT_RULES and self._fixed is None:
            labels = ", ".join(repr(rung.label) for rung in self._ladder)
            raise ValueError(
                f"unit must be 'max', 'whole' or one of {labels} (got {unit!r})"
            )
        self._rule = unit
        self._decimals = decimals
        self._currency = currency
        self._plan: _Plan | None = None

    # -- unit choice ----------------------------------------------------
    def _max_unit(self, magnitude: float) -> Unit:
        """The largest rung at or below ``magnitude`` (else the smallest)."""
        chosen = self._ladder[0]
        for rung in self._ladder:
            # Tolerate float noise so a 999.9999999 tick still reads 1k.
            if magnitude >= rung.factor * (1 - _TOL):
                chosen = rung
        return chosen

    def _label(self, value: float, unit: Unit, decimals: int) -> str:
        number = format(abs(value) / unit.factor, f",.{decimals}f")
        if float(number.replace(",", "")) == 0:
            return "0" if self._decimals is None else f"{0:.{decimals}f}"
        sign = "-" if value < 0 else ""
        return f"{sign}{self._currency}{number}{unit.label}"

    def _cost(
        self, values: Sequence[float], unit: Unit
    ) -> tuple[int, int, float]:
        decimals = fewest_exact_decimals([abs(v) / unit.factor for v in values])
        longest = max(len(self._label(v, unit, decimals)) for v in values)
        return decimals, longest, unit.factor

    def _axis_unit(self, values: Sequence[float]) -> Unit:
        if self._fixed is not None:
            return self._fixed
        if self._rule == "whole":
            return min(self._ladder, key=lambda rung: self._cost(values, rung))
        return self._max_unit(max(abs(v) for v in values))

    # -- decision -------------------------------------------------------
    def _is_linear(self) -> bool:
        get_scale = getattr(self.axis, "get_scale", None)
        return get_scale is None or get_scale() == "linear"

    def _make_plan(self, values: Sequence[float]) -> _Plan:
        finite = [v for v in values if math.isfinite(v)]
        if not self._is_linear() or not finite:
            return _Plan(self._fixed, self._decimals)
        unit = self._axis_unit(finite)
        decimals = self._decimals
        if decimals is None:
            decimals = fewest_exact_decimals(
                [abs(v) / unit.factor for v in finite]
            )
        return _Plan(unit, decimals)

    def _in_view(self, values: list[float]) -> list[float]:
        axis = self.axis
        if axis is None:
            return values
        interval = np.asarray(axis.get_view_interval(), dtype=float)
        low, high = float(interval.min()), float(interval.max())
        # Keep ticks sitting on a limit despite float noise. The tolerance
        # scales with each limit, not the span, so a log axis does not
        # pull in the decade below its lower limit.
        slack = 1e-12 * (high - low)
        low -= _TOL * abs(low) + slack
        high += _TOL * abs(high) + slack
        shown = [v for v in values if low <= v <= high]
        return shown or values

    def set_locs(self, locs: list[float]) -> None:
        """Record the tick locations and settle this axis's unit/decimals."""
        self.locs = locs
        values = [float(v) for v in locs]
        self._plan = self._make_plan(self._in_view(values)) if values else None

    def format_ticks(self, values: list[float]) -> list[str]:
        """Format every tick with one axis-wide decision."""
        self.set_locs(values)
        return [self(value, pos) for pos, value in enumerate(values)]

    def __call__(self, x: float, pos: int | None = None) -> str:
        """Format one value with the last axis decision (or its own)."""
        value = float(x)
        if not math.isfinite(value):
            return str(value)
        plan = (
            self._plan if self._plan is not None else self._make_plan([value])
        )
        unit = plan.axis_unit or self._max_unit(abs(value))
        decimals = plan.decimals
        if decimals is None:
            decimals = fewest_exact_decimals([abs(value) / unit.factor])
        return self._label(value, unit, decimals)
