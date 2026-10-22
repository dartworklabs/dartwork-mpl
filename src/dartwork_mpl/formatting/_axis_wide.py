"""Tick formatters that settle unit and decimals once per axis.

The ``decimals=None`` default of ``format_axis_si`` / ``_millions`` /
``_billions`` / ``_myriad`` installs one of these. A fixed ``.1f`` turns
integer ticks into ``200.0`` and ``1.0k`` and rounds half steps such as
``1250`` to ``1.2k``. These formatters choose one decimal count per unit
from the ticks the axis actually shows: the fewest decimals that render
every tick exactly and distinctly, so integer ticks print no decimals and
fractional steps keep the same count on every tick (``17.5, 20.0, 22.5``).
On log and other non-linear scales each tick is its own decade, so each
tick takes the fewest decimals it needs (``0.1, 1, 10``). Numbers of 1000
and more carry thousands separators (``1,200``).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import matplotlib.ticker as ticker
import numpy as np

from ._decimals import fewest_exact_decimals

__all__ = ["MyriadFormatter", "SIFormatter", "ScaledFormatter"]

_PREFIX_TOL = 1e-9

_SI_PREFIXES: tuple[tuple[float, str], ...] = (
    (1e12, "T"),
    (1e9, "G"),
    (1e6, "M"),
    (1e3, "k"),
)


@dataclass(frozen=True)
class _Unit:
    factor: float
    label: str


@dataclass(frozen=True)
class _Plan:
    """One axis decision: a shared unit (or per-tick units) and decimals.

    ``decimals`` maps a unit label to its decimal count. ``per_value``
    marks a non-linear axis, where every tick settles its own decimals.
    """

    axis_unit: _Unit | None
    decimals: dict[str, int]
    per_value: bool = False


class ScaledFormatter(ticker.Formatter):
    """Format ticks as ``value / factor`` plus a fixed suffix.

    Used by ``format_axis_millions`` and ``format_axis_billions``. The
    decimal count is chosen once per axis in :meth:`set_locs`, which
    :meth:`format_ticks` calls with every major tick on each draw. Only the
    ticks inside the view interval vote. A value that rounds to zero prints
    as a bare zero with the axis decimals and no suffix.
    """

    def __init__(self, factor: float = 1.0, suffix: str = "") -> None:
        self._unit = _Unit(factor, suffix)
        self._plan: _Plan | None = None

    # -- unit hooks -----------------------------------------------------
    def _axis_unit(self, values: Sequence[float], linear: bool) -> _Unit | None:
        """The unit every tick shares, or ``None`` to pick one per tick."""
        return self._unit

    def _value_unit(self, magnitude: float) -> _Unit:
        """Unit for one tick when the axis has no shared unit."""
        return self._unit

    def _compose(self, sign: str, number: str, unit: str) -> str:
        return f"{sign}{number}{unit}"

    # -- decision -------------------------------------------------------
    def _is_linear(self) -> bool:
        get_scale = getattr(self.axis, "get_scale", None)
        return get_scale is None or get_scale() == "linear"

    def _make_plan(self, values: Sequence[float]) -> _Plan:
        finite = [v for v in values if math.isfinite(v)]
        linear = self._is_linear()
        axis_unit = self._axis_unit(finite, linear)
        if not linear:
            return _Plan(axis_unit, {}, per_value=True)
        groups: dict[str, list[float]] = {}
        for value in finite:
            unit = axis_unit or self._value_unit(abs(value))
            groups.setdefault(unit.label, []).append(abs(value) / unit.factor)
        decimals = {
            label: fewest_exact_decimals(scaled)
            for label, scaled in groups.items()
        }
        return _Plan(axis_unit, decimals)

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
        low -= 1e-9 * abs(low) + slack
        high += 1e-9 * abs(high) + slack
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
        unit = plan.axis_unit or self._value_unit(abs(value))
        scaled = abs(value) / unit.factor
        decimals = None if plan.per_value else plan.decimals.get(unit.label)
        if decimals is None:
            decimals = fewest_exact_decimals([scaled])
        number = format(scaled, f",.{decimals}f")
        if float(number.replace(",", "")) == 0:
            return f"{0:.{decimals}f}"
        return self._compose("-" if value < 0 else "", number, unit.label)


def _unit_cost(values: Sequence[float], unit: _Unit) -> tuple[int, int, float]:
    """``(decimals, longest label, factor)`` for printing ``values`` in ``unit``."""
    scaled = [abs(v) / unit.factor for v in values]
    decimals = fewest_exact_decimals(scaled)
    longest = 0
    for value, magnitude in zip(values, scaled, strict=True):
        number = format(magnitude, f",.{decimals}f")
        if float(number.replace(",", "")) == 0:
            label = number
        else:
            label = ("-" if value < 0 else "") + number + unit.label
        longest = max(longest, len(label))
    return decimals, longest, unit.factor


class SIFormatter(ScaledFormatter):
    """SI-prefix ticks (``k``, ``M``, ``G``, ``T``) with one prefix per axis.

    On a linear axis every tick shares one unit among none/k/M/G/T, chosen
    integers first: of the units in which every visible tick is a whole
    number, the one whose longest label is shortest (``0, 200 … 1,200``;
    ``0, 1k … 5k``; ``-1M … 1M``). Only when no unit gives whole numbers
    does the unit with the fewest decimals win (``0.0, 0.2, 0.4``). Log and
    other non-linear scales span decades, so each tick takes its own prefix
    and decimals there.
    """

    @staticmethod
    def _prefix_for(magnitude: float) -> _Unit:
        for factor, prefix in _SI_PREFIXES:
            # Tolerate float noise so a 999.9999999 tick still reads 1k.
            if magnitude >= factor * (1 - _PREFIX_TOL):
                return _Unit(factor, prefix)
        return _Unit(1.0, "")

    def _axis_unit(self, values: Sequence[float], linear: bool) -> _Unit | None:
        if not linear or not values:
            return None
        candidates = [
            _Unit(1.0, ""),
            *(_Unit(f, p) for f, p in reversed(_SI_PREFIXES)),
        ]
        return min(candidates, key=lambda unit: _unit_cost(values, unit))

    def _value_unit(self, magnitude: float) -> _Unit:
        return self._prefix_for(magnitude)


class MyriadFormatter(ScaledFormatter):
    """East-Asian myriad ticks (``만``/``억``/…) with per-unit decimals.

    Each tick keeps its own unit from the ladder (below 10^4 ticks print
    the plain grouped number). Ticks sharing a unit share one decimal
    count, so ``1.00억, 1.25억, 1.50억`` stay aligned while ``5,000만``
    keeps none.
    """

    def __init__(
        self, ladder: Sequence[tuple[int, str]], currency: str = ""
    ) -> None:
        super().__init__()
        self._ladder = tuple(ladder)
        self._currency = currency

    def _axis_unit(self, values: Sequence[float], linear: bool) -> _Unit | None:
        return None

    def _value_unit(self, magnitude: float) -> _Unit:
        if magnitude < 10_000:
            return _Unit(1.0, "")
        threshold, label = max(
            item for item in self._ladder if item[0] <= magnitude
        )
        return _Unit(float(threshold), label)

    def _compose(self, sign: str, number: str, unit: str) -> str:
        return f"{sign}{self._currency}{number}{unit}"
