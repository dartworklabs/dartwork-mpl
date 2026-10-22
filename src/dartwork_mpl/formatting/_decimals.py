"""Decimal-count rules shared by the tick formatters and the validator.

``recommend_tick_decimals`` is the public step rule (re-exported as
``dm.recommend_tick_decimals``). ``fewest_exact_decimals`` is the stricter
rule the axis-wide formatters use: a 2.5 step needs one decimal to stay
exact (``17.5, 20.0, 22.5``) even though the step rule would say zero.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from itertools import pairwise

__all__ = ["fewest_exact_decimals", "recommend_tick_decimals"]

# Most decimals tried for an exact rendering (a 1e-9 log tick needs nine).
_MAX_DECIMALS = 12
# A scaled value counts as exact when it sits this close to an integer in
# units of its last printed digit; the relative term absorbs float noise.
_EXACT_ABS_TOL = 1e-6
_EXACT_REL_TOL = 1e-14


def recommend_tick_decimals(values: Sequence[float]) -> int:
    """Recommend the minimum decimal places needed for numeric tick values.

    The recommendation is based on the smallest positive step between
    adjacent sorted values, with a conservative cap of four decimals.
    Duplicate and non-finite values are ignored.
    """
    finite: list[float] = []
    for value in values:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            finite.append(numeric)
    if len(finite) < 2:
        return 0

    ordered = sorted(finite)
    diffs = [
        right - left for left, right in pairwise(ordered) if right - left > 0
    ]
    if not diffs:
        return 0

    step = min(diffs)
    return min(4, max(0, math.ceil(-math.log10(step) - 1e-9)))


def _is_exact(value: float, decimals: int) -> bool:
    scaled = value * 10.0**decimals
    nearest = round(scaled)
    if nearest == 0 and value != 0:
        return False  # a nonzero value must not print as 0
    gap = abs(scaled - nearest)
    return gap <= _EXACT_ABS_TOL + _EXACT_REL_TOL * abs(scaled)


def _all_distinct(values: Sequence[float], decimals: int) -> bool:
    return len({f"{value:.{decimals}f}" for value in values}) == len(values)


def _significant_decimals(value: float, digits: int = 3) -> int:
    if value == 0:
        return 0
    return max(0, digits - 1 - math.floor(math.log10(abs(value))))


def fewest_exact_decimals(values: Sequence[float]) -> int:
    """Fewest decimals that render every value exactly and distinctly.

    Returns ``0`` when every value is an integer. Values no decimal count
    renders exactly (irregular steps such as thirds) fall back to the
    step rule of :func:`recommend_tick_decimals` (three significant digits
    for a lone value), widened until the values stay apart.
    """
    finite = sorted({float(v) for v in values if math.isfinite(v)})
    # Float noise on a zero tick (5.6e-17 beside 0.2, 0.4) is zero.
    largest = max((abs(v) for v in finite), default=0.0)
    if len(finite) > 1:
        finite = sorted(
            {0.0 if abs(v) <= 1e-9 * largest else v for v in finite}
        )
    for decimals in range(_MAX_DECIMALS + 1):
        if all(_is_exact(v, decimals) for v in finite) and _all_distinct(
            finite, decimals
        ):
            return decimals
    if len(finite) == 1:
        return min(_MAX_DECIMALS, _significant_decimals(finite[0]))
    decimals = recommend_tick_decimals(finite)
    while decimals < _MAX_DECIMALS and not _all_distinct(finite, decimals):
        decimals += 1
    return decimals
