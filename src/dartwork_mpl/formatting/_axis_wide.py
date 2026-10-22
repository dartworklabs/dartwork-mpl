"""Tick formatters that settle unit and decimals once per axis.

The ``decimals=None`` default of ``format_axis_si`` / ``_millions`` /
``_billions`` / ``_myriad`` installs one of these. A fixed ``.1f`` turns
integer ticks into ``200.0`` and ``1.0k`` and rounds half steps such as
``1250`` to ``1.2k``. These formatters choose one decimal count per unit
from the ticks the axis actually shows: the fewest decimals that render
every tick exactly and distinctly, so integer ticks print no decimals and
fractional steps keep the same count on every tick (``17.5, 20.0, 22.5``).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import matplotlib.ticker as ticker
import numpy as np

__all__ = [
    "MyriadFormatter",
    "SIFormatter",
    "ScaledFormatter",
    "fewest_exact_decimals",
]

# Decimal counts tried before falling back to "distinct only" rendering.
_MAX_DECIMALS = 6
_EXACT_REL_TOL = 1e-9
_EXACT_ABS_TOL = 1e-6

_SI_PREFIXES: tuple[tuple[float, str], ...] = (
    (1e12, "T"),
    (1e9, "G"),
    (1e6, "M"),
    (1e3, "k"),
)


def _is_exact(value: float, decimals: int) -> bool:
    scaled = value * 10.0**decimals
    return math.isclose(
        scaled, round(scaled), rel_tol=_EXACT_REL_TOL, abs_tol=_EXACT_ABS_TOL
    )


def _all_distinct(values: Sequence[float], decimals: int) -> bool:
    return len({f"{value:.{decimals}f}" for value in values}) == len(values)


def fewest_exact_decimals(values: Sequence[float]) -> int:
    """Fewest decimals that render every value exactly and distinctly.

    Returns ``0`` when every value is an integer. Values that no count up
    to six decimals renders exactly (irregular steps such as thirds) get
    the fewest decimals that still keep the values apart.
    """
    finite = sorted({float(v) for v in values if math.isfinite(v)})
    for decimals in range(_MAX_DECIMALS + 1):
        if all(_is_exact(v, decimals) for v in finite) and _all_distinct(
            finite, decimals
        ):
            return decimals
    for decimals in range(_MAX_DECIMALS + 1):
        if _all_distinct(finite, decimals):
            return decimals
    return _MAX_DECIMALS


@dataclass(frozen=True)
class _Unit:
    factor: float
    label: str


@dataclass(frozen=True)
class _Plan:
    """One axis decision: a shared unit (or per-tick units) and decimals."""

    axis_unit: _Unit | None
    decimals: dict[str, int]


class ScaledFormatter(ticker.Formatter):
    """Format ticks as ``value / factor`` plus a fixed suffix.

    Used by ``format_axis_millions`` and ``format_axis_billions``. The
    decimal count is chosen once per axis in :meth:`set_locs`, which
    :meth:`format_ticks` calls with every major tick on each draw. Only the
    ticks inside the view interval vote. A value that rounds to zero prints
    as a bare zero with the axis decimals and no suffix.
    """

    _grouping = False

    def __init__(self, factor: float = 1.0, suffix: str = "") -> None:
        self._unit = _Unit(factor, suffix)
        self._plan: _Plan | None = None

    # -- unit hooks -----------------------------------------------------
    def _axis_unit(self, values: Sequence[float]) -> _Unit | None:
        """The unit every tick shares, or ``None`` to pick one per tick."""
        return self._unit

    def _value_unit(self, magnitude: float) -> _Unit:
        """Unit for one tick when the axis has no shared unit."""
        return self._unit

    def _compose(self, sign: str, number: str, unit: str) -> str:
        return f"{sign}{number}{unit}"

    # -- decision -------------------------------------------------------
    def _make_plan(self, values: Sequence[float]) -> _Plan:
        finite = [v for v in values if math.isfinite(v)]
        axis_unit = self._axis_unit(finite)
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
        decimals = plan.decimals.get(unit.label)
        if decimals is None:
            decimals = fewest_exact_decimals([scaled])
        spec = f",.{decimals}f" if self._grouping else f".{decimals}f"
        number = format(scaled, spec)
        if float(number.replace(",", "")) == 0:
            return f"{0:.{decimals}f}"
        return self._compose("-" if value < 0 else "", number, unit.label)


class SIFormatter(ScaledFormatter):
    """SI-prefix ticks (``k``, ``M``, ``G``, ``T``) with one prefix per axis.

    On a linear axis the prefix comes from the largest visible ``|tick|``
    and applies to every tick, so an axis never mixes ``800`` with
    ``1.2k``. Log and other non-linear scales span decades, so each tick
    takes its own prefix there and decimals are settled per prefix.
    """

    @staticmethod
    def _prefix_for(magnitude: float) -> _Unit:
        for factor, prefix in _SI_PREFIXES:
            # Tolerate float noise so a 999.9999999 tick still reads 1k.
            if magnitude >= factor * (1 - _EXACT_REL_TOL):
                return _Unit(factor, prefix)
        return _Unit(1.0, "")

    def _axis_unit(self, values: Sequence[float]) -> _Unit | None:
        axis = self.axis
        get_scale = getattr(axis, "get_scale", None)
        if get_scale is not None and get_scale() != "linear":
            return None
        if not values:
            return None
        return self._prefix_for(max(abs(v) for v in values))

    def _value_unit(self, magnitude: float) -> _Unit:
        return self._prefix_for(magnitude)


class MyriadFormatter(ScaledFormatter):
    """East-Asian myriad ticks (``만``/``억``/…) with per-unit decimals.

    Each tick keeps its own unit from the ladder (below 10^4 ticks print
    the plain grouped number). Ticks sharing a unit share one decimal
    count, so ``1.00억, 1.25억, 1.50억`` stay aligned while ``5,000만``
    keeps none.
    """

    _grouping = True

    def __init__(
        self, ladder: Sequence[tuple[int, str]], currency: str = ""
    ) -> None:
        super().__init__()
        self._ladder = tuple(ladder)
        self._currency = currency

    def _axis_unit(self, values: Sequence[float]) -> _Unit | None:
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
