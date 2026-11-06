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
- Negative ticks use matplotlib's minus sign (U+2212 unless
  ``axes.unicode_minus`` is off), like the axis's other text.

On log and other non-linear scales the ticks span decades, which cannot
share one unit (``0.000001k`` beside ``1,000k``), so there each tick takes
its own unit and the fewest decimals it needs (``0.1, 1, 10, 1k``). A
``"function"`` scale whose functions are affine over the view (a
``secondary_yaxis`` showing the same values, ``x1.3`` or degrees C as F)
draws its ticks evenly and counts as linear (:func:`draws_linearly`).

Text that should read like the ticks (value labels on bars) asks
:func:`tick_scale_of` how an axis printed its ticks at the last draw: the
factor to divide by and the prefix and suffix around the number
(:class:`TickScale`), and prints the number with :func:`number_text`, the
same separators, minus and zero as a tick.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import matplotlib as mpl
import matplotlib.ticker as ticker
import numpy as np
from matplotlib.axis import Axis

from ._decimals import fewest_exact_decimals

__all__ = [
    "FINANCE_LADDER",
    "MYRIAD_LADDER",
    "SI_LADDER",
    "UNIT_RULES",
    "AxisUnitFormatter",
    "TickScale",
    "Unit",
    "draws_linearly",
    "number_text",
    "tick_scale_of",
]

UNIT_RULES = ("max", "whole")
"""Unit rules besides naming one ladder label."""

_TOL = 1e-9
# Points of the view at which a function scale is checked for being affine.
_AFFINE_PROBES = 5


def draws_linearly(axis: Axis) -> bool:
    """Whether ``axis`` draws its view on a linear scale.

    A ``"linear"`` scale does, and so does a ``"function"`` scale (what
    ``ax.secondary_xaxis`` / ``secondary_yaxis`` and ``set_yscale("function",
    ...)`` make) whose transform is affine over the view: the same values,
    ``x1.3``, degrees C shown as F. The functions run on a few points of the
    view with numpy's floating-point warnings off; one that raises (a
    ``Transform`` given as functions fails on 1-D values; ``-W error`` turns
    a warning into one), returns another shape or a non-finite value
    (``1 / 0``) does not draw linearly, nor does ``1 / x``.
    """
    scale = axis.get_scale()
    if scale == "linear":
        return True
    if scale != "function":
        return False
    low, high = sorted(float(v) for v in axis.get_view_interval())
    if not (math.isfinite(low) and math.isfinite(high)) or high <= low:
        return False
    probe = np.linspace(low, high, _AFFINE_PROBES)
    try:
        with np.errstate(all="ignore"):
            drawn = np.asarray(
                axis.get_transform().transform(probe), dtype=float
            )
    except Exception:  # noqa: BLE001 - user functions may raise anything
        return False
    if drawn.shape != probe.shape or not np.all(np.isfinite(drawn)):
        return False
    span = float(drawn[-1] - drawn[0])
    line = drawn[0] + span * (probe - low) / (high - low)
    # Off the straight line by more than float noise: on the span, and on
    # the values themselves when they sit far from zero (1e9 + 1).
    noise = _TOL * abs(span) + 4 * np.finfo(float).eps * np.abs(drawn).max()
    return span != 0 and bool(np.all(np.abs(drawn - line) <= noise))


@dataclass(frozen=True)
class Unit:
    """One rung of a unit ladder: divide by ``factor``, append ``label``."""

    factor: float
    label: str


SI_LADDER = (
    Unit(1.0, ""),
    Unit(1e3, "k"),
    Unit(1e6, "M"),
    Unit(1e9, "G"),
    Unit(1e12, "T"),
)
"""SI prefixes: none, k, M, G, T."""

MYRIAD_LADDER = (
    Unit(1.0, ""),
    Unit(1e4, "만"),
    Unit(1e8, "억"),
    Unit(1e12, "조"),
    Unit(1e16, "경"),
)
"""Korean myriad units: none, 만, 억, 조, 경."""

FINANCE_LADDER = (
    Unit(1.0, ""),
    Unit(1e3, "k"),
    Unit(1e6, "M"),
    Unit(1e9, "B"),
    Unit(1e12, "T"),
)
"""Money abbreviations: none, k, M, B (billion), T (trillion)."""


@dataclass(frozen=True)
class TickScale:
    """How an axis's ticks print a number.

    ``prefix``, then the value divided by ``factor``, then ``suffix``:
    ``TickScale(1e9, "", "G")`` prints ``33e9`` as ``33G``. The plain scale
    (``TickScale()``) prints the value itself.
    """

    factor: float = 1.0
    prefix: str = ""
    suffix: str = ""


def number_text(
    value: float,
    decimals: int,
    *,
    fixed: bool = False,
    prefix: str = "",
    suffix: str = "",
) -> str:
    """``value`` printed as an axis-wide tick prints it.

    Thousands separators, ``decimals`` places, matplotlib's minus (U+2212
    unless ``axes.unicode_minus`` is off) before ``prefix``. A value that
    rounds to zero prints ``0`` without prefix or suffix, or ``0.00`` (as
    many zeros as ``decimals``) when the count is ``fixed`` by the caller.
    """
    number = format(abs(value), f",.{decimals}f")
    if float(number.replace(",", "")) == 0:
        return f"{0:.{decimals}f}" if fixed else "0"
    # The same minus as matplotlib's own ticks (U+2212 unless turned off).
    minus = "\N{MINUS SIGN}" if mpl.rcParams["axes.unicode_minus"] else "-"
    sign = minus if value < 0 else ""
    return f"{sign}{prefix}{number}{suffix}"


def _axis_decimals(values: Sequence[float], unit: Unit) -> int:
    """Fewest decimals that print every tick exactly and distinctly.

    Signed values: the ticks print with their sign, and ``-0.06`` beside
    ``0.06000000000000001`` are two ticks, not one magnitude seen twice
    (as magnitudes they never print apart, and the count climbs to 12).
    """
    return fewest_exact_decimals([v / unit.factor for v in values])


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
        return number_text(
            value / unit.factor,
            decimals,
            fixed=self._decimals is not None,
            prefix=self._currency,
            suffix=unit.label,
        )

    def _cost(
        self, values: Sequence[float], unit: Unit
    ) -> tuple[int, int, float]:
        decimals = _axis_decimals(values, unit)
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
        axis = self.axis
        return not isinstance(axis, Axis) or draws_linearly(axis)

    def _make_plan(self, values: Sequence[float]) -> _Plan:
        finite = [v for v in values if math.isfinite(v)]
        if not self._is_linear() or not finite:
            return _Plan(self._fixed, self._decimals)
        unit = self._axis_unit(finite)
        decimals = self._decimals
        if decimals is None:
            decimals = _axis_decimals(finite, unit)
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
        super().set_locs(locs)
        values = [float(v) for v in locs]
        self._plan = self._make_plan(self._in_view(values)) if values else None

    def format_ticks(self, values: list[float]) -> list[str]:
        """Format every tick with one axis-wide decision."""
        self.set_locs(values)
        return [self(value, pos) for pos, value in enumerate(values)]

    def _decision(self, value: float) -> tuple[Unit, int | None]:
        """The unit and decimals of the last axis decision (or ``value``'s own).

        On a non-linear axis the unit is ``value``'s and the decimals
        ``None`` (each tick settles its own).
        """
        plan = (
            self._plan if self._plan is not None else self._make_plan([value])
        )
        return plan.axis_unit or self._max_unit(abs(value)), plan.decimals

    def __call__(self, x: float, pos: int | None = None) -> str:
        """Format one value with the last axis decision (or its own)."""
        value = float(x)
        if not math.isfinite(value):
            return str(value)
        unit, decimals = self._decision(value)
        if decimals is None:
            decimals = fewest_exact_decimals([abs(value) / unit.factor])
        return self._label(value, unit, decimals)

    def scale_for(self, value: float) -> TickScale:
        """How a tick at ``value`` prints under the last axis decision.

        The axis unit's factor, this formatter's currency prefix and the
        unit label as suffix; on a non-linear axis, ``value``'s own unit.
        Before any draw ``value`` decides alone, as :meth:`__call__` does.
        """
        unit, _decimals = self._decision(float(value))
        return TickScale(unit.factor, self._currency, unit.label)


def tick_scale_of(axis: Axis, value: float) -> TickScale:
    """How ``axis``'s major ticks print ``value``, as of their last formatting.

    A tick formatter decides when it formats the ticks (every draw, or a
    call to its ``format_ticks``), so read this after a draw:

    - :class:`AxisUnitFormatter` (``format_axis_si`` / ``_millions`` /
      ``_billions`` / ``_myriad`` and the library's default numbers): the
      axis unit and currency (``33G``, ``1.2k``); ``dm.axis_unit``'s
      formatter puts the unit in the axis label instead, so its scale has
      no suffix (``33`` under ``Energy (GWh)``).
    - :class:`matplotlib.ticker.PercentFormatter`: ``xmax / 100`` and its
      symbol (``31%``).
    - Any other formatter, matplotlib's own ``ScalarFormatter`` on an axis
      nobody formatted included: the plain scale. Its ticks' text cannot be
      read back as a unit (``dm.simple_layout`` gives such an axis the
      library's numbers first).
    """
    formatter = axis.get_major_formatter()
    if isinstance(formatter, AxisUnitFormatter):
        return formatter.scale_for(value)
    if isinstance(formatter, ticker.PercentFormatter) and formatter.xmax:
        return TickScale(formatter.xmax / 100.0, "", formatter.symbol)
    return TickScale()
