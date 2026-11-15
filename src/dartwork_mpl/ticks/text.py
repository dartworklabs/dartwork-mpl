"""Numbers as tick text: decimal counts and the printed value. Pure.

``fewest_exact_decimals`` is the axis rule: the fewest decimals that print
every value exactly and distinctly (a 2.5 step keeps one: ``17.5, 20.0``).
``value_label_decimals`` is the value-label rule: three significant digits
on the largest value, cut to the fewest exact ones. ``number_text`` prints a
value as an axis-wide tick does: thousands separators, ``0`` for zero and
the minus sign matplotlib draws.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from itertools import pairwise

from ..vocab import AffixedZero, BareZero, ScaleZero
from .model import PLAIN, NumberStyle, Unit

BARE = BareZero()
MAX_DECIMALS = 12  # a 1e-9 tick needs nine
_EXACT_ABS_TOL = 1e-6
_EXACT_REL_TOL = 1e-14


def minus(unicode_minus: bool) -> str:
    """The minus sign matplotlib draws (U+2212 unless turned off)."""
    return "\N{MINUS SIGN}" if unicode_minus else "-"


def _step_decimals(values: Sequence[float]) -> int:
    """Decimals the smallest step between sorted values needs, at most four."""
    steps = [b - a for a, b in pairwise(values) if b - a > 0]
    if not steps:
        return 0
    return min(4, max(0, math.ceil(-math.log10(min(steps)) - 1e-9)))


def _is_exact(value: float, decimals: int) -> bool:
    scaled = value * 10.0**decimals
    nearest = round(scaled)
    if nearest == 0 and value != 0:
        return False  # a nonzero value must not print as 0
    return abs(scaled - nearest) <= _EXACT_ABS_TOL + _EXACT_REL_TOL * abs(
        scaled
    )


def _distinct(values: Sequence[float], decimals: int) -> bool:
    return len({f"{v:.{decimals}f}" for v in values}) == len(values)


def _significant(value: float, digits: int = 3) -> int:
    if value == 0:
        return 0
    return max(0, digits - 1 - math.floor(math.log10(abs(value))))


def fewest_exact_decimals(values: Sequence[float]) -> int:
    """Fewest decimals that print every value exactly and distinctly.

    Values no count prints exactly (thirds) fall back to the step rule
    widened until they stay apart; a lone value to three significant digits.
    """
    finite = sorted({float(v) for v in values if math.isfinite(v)})
    largest = max((abs(v) for v in finite), default=0.0)
    if len(finite) > 1:  # float noise on a zero tick is zero
        finite = sorted(
            {0.0 if abs(v) <= 1e-9 * largest else v for v in finite}
        )
    for decimals in range(MAX_DECIMALS + 1):
        if all(_is_exact(v, decimals) for v in finite) and _distinct(
            finite, decimals
        ):
            return decimals
    if len(finite) == 1:
        return min(MAX_DECIMALS, _significant(finite[0]))
    decimals = _step_decimals(finite)
    while decimals < MAX_DECIMALS and not _distinct(finite, decimals):
        decimals += 1
    return decimals


def value_label_decimals(values: Sequence[float]) -> int:
    """One decimal count for a family of value labels.

    Three significant digits on the largest ``|value|``, cut to the fewest
    that print every value exactly: ``120, 135``; ``21.4, 18.0, 21.5``.
    """
    finite = [float(v) for v in values if math.isfinite(v)]
    largest = max((abs(v) for v in finite), default=0.0)
    if largest == 0:
        return 0
    return min(_significant(largest), fewest_exact_decimals(finite))


def number_text(
    value: float,
    decimals: int,
    *,
    fixed: bool = False,
    prefix: str = "",
    suffix: str = "",
    zero: ScaleZero = BARE,
    unicode_minus: bool | None = None,
) -> str:
    """``value`` printed as an axis-wide tick prints it.

    Thousands separators and ``decimals`` places, the minus before
    ``prefix``. A value that rounds to zero prints ``0`` without sign (or
    ``0.00`` when the count is ``fixed``), bare or with its affixes.
    ``unicode_minus`` defaults to ``axes.unicode_minus``.
    """
    number = format(abs(value), f",.{decimals}f")
    if float(number.replace(",", "")) == 0:
        digits = f"{0:.{decimals}f}" if fixed else "0"
        match zero:
            case AffixedZero():
                return f"{prefix}{digits}{suffix}"
            case BareZero():
                return digits
    sign = minus(_unicode_minus(unicode_minus)) if value < 0 else ""
    return f"{sign}{prefix}{number}{suffix}"


def _unicode_minus(asked: bool | None) -> bool:
    if asked is not None:
        return asked
    import matplotlib as mpl  # the rc setting is read where text is made

    return bool(mpl.rcParams["axes.unicode_minus"])


def alone_text(value: float, style: NumberStyle) -> str:
    """``value`` alone in its own unit with ``style.decimals`` places.

    The largest rung at or below its magnitude, trailing zeros dropped; a
    value under the first rung above one prints whole with no unit, and only
    an exact zero reads ``0``.
    """
    if value == 0:
        return "0"
    unit = _own_unit(abs(value), style)
    decimals = 0 if unit.factor == 1 else style.decimals or 0
    number = format(abs(value) / unit.factor, f",.{decimals}f")
    if decimals:
        number = number.rstrip("0").rstrip(".")
    sign = minus(_unicode_minus(None)) if value < 0 else ""
    return f"{sign}{style.currency}{number}{unit.label}"


def _own_unit(magnitude: float, style: NumberStyle) -> Unit:
    """No float tolerance here: ``9,999.9999999`` stays under ``만``."""
    above = [r for r in style.ladder.rungs if r.factor > 1]
    if magnitude < above[0].factor:
        return PLAIN
    return [r for r in above if r.factor <= magnitude][-1]
