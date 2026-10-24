"""The library's tick numbers on axes nobody formatted.

Left to matplotlib, an axis prints ``1750`` and ``34000`` without separators
and ``0.5 … 2.5`` under a ``1e6`` corner label, so every agent or person
installs a formatter of their own and the same data reads differently from
figure to figure. :func:`apply_default_tick_format` settles it once:

- an axis whose visible ticks reach 1,000 gets thousands separators
  (``1,750``; ``34,000``) and the fewest exact decimals;
- from one million the axis takes the largest tick's SI unit (``0.5M …
  2.5M``), as ``dm.format_axis_si`` does, unless that needs more than two
  decimals;
- smaller axes (``0, 250 … 750``; ``0.5, 1.0``), x axes whose ticks all sit
  in 1000-2999 (years), log, date and category axes, colorbars and any axis
  with a formatter someone chose keep theirs.

``dm.simple_layout`` calls it before measuring (``format_ticks=False`` opts
out), so the numbers it fits are the numbers saved.
"""

from __future__ import annotations

from collections.abc import Sequence

import matplotlib.ticker as ticker
from matplotlib.axis import Axis
from matplotlib.figure import Figure

from ._axis_wide import AxisUnitFormatter, Unit
from ._decimals import fewest_exact_decimals

__all__ = ["DefaultNumberFormatter", "apply_default_tick_format"]

_SEPARATOR_FROM = 1_000.0
_UNIT_FROM = 1_000_000.0
_MAX_UNIT_DECIMALS = 2
_YEARS = (1_000.0, 2_999.0)


class DefaultNumberFormatter(AxisUnitFormatter):
    """Thousands separators below one million, the largest tick's unit above."""

    def __init__(self, ladder: Sequence[Unit]) -> None:
        super().__init__(ladder, "max")

    def _axis_unit(self, values: Sequence[float]) -> Unit:
        top = max(abs(v) for v in values)
        if top < _UNIT_FROM * (1 - 1e-9):
            return self._ladder[0]
        unit = self._max_unit(top)
        scaled = [abs(v) / unit.factor for v in values]
        if fewest_exact_decimals(scaled) > _MAX_UNIT_DECIMALS:
            return self._ladder[0]
        return unit


def _visible_ticks(axis: Axis) -> list[float]:
    low, high = sorted(float(v) for v in axis.get_view_interval())
    return [
        float(t) for t in axis.get_majorticklocs() if low <= float(t) <= high
    ]


def _untouched(axis: Axis) -> bool:
    # Exactly matplotlib's default: a subclass or another formatter was chosen.
    return type(axis.get_major_formatter()) is ticker.ScalarFormatter


def apply_default_tick_format(fig: Figure) -> int:
    """Install the library's tick numbers on every axis nobody formatted.

    Returns the number of axes changed. Safe to call again: an axis that
    already carries the default formatter is no longer ``ScalarFormatter``.
    """
    from . import _SI_LADDER  # defined after this module is imported

    changed = 0
    for ax in fig.axes:
        if (
            ax.name != "rectilinear"
            or getattr(ax, "_colorbar", None) is not None
        ):
            continue
        for which, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
            if not _untouched(axis) or axis.get_scale() != "linear":
                continue
            ticks = _visible_ticks(axis)
            if not ticks or max(abs(t) for t in ticks) < _SEPARATOR_FROM:
                continue
            if which == "x" and all(_YEARS[0] <= t <= _YEARS[1] for t in ticks):
                continue  # years: 2024, not 2,024
            axis.set_major_formatter(DefaultNumberFormatter(_SI_LADDER))
            changed += 1
    return changed
