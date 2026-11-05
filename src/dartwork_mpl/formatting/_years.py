"""Year helpers: what counts as a year axis and how its ticks read.

Two-digit years (``16, 18, 20``) are the default tick text on integer year
axes. :func:`is_year_axis` decides from the tick *values* alone (label text
is never evidence); :class:`YearTickFormatter` prints them and falls back to
four digits when two visible years would print alike (``1900`` and ``2000``).
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise
from typing import Literal

import matplotlib.ticker as ticker

__all__ = ["YearTickFormatter", "is_year_axis", "two_digits_repeat"]

_FIRST_YEAR = 1900
_LAST_YEAR = 2099


def is_year_axis(ticks: Sequence[float]) -> bool:
    """Whether the ticks read as calendar years.

    Every tick is an integer in 1900-2099, there are at least two, and they
    step by one whole number of years.
    """
    if len(ticks) < 2:
        return False
    if any(
        t != t or abs(t - round(t)) > 1e-9 or not _FIRST_YEAR <= t <= _LAST_YEAR
        for t in ticks
    ):
        return False
    years = [round(t) for t in ticks]
    steps = {b - a for a, b in pairwise(years)}
    return len(steps) == 1 and 0 not in steps


def two_digits_repeat(years: Sequence[int]) -> bool:
    """Whether two distinct years share their last two digits."""
    seen: dict[int, int] = {}
    return any(seen.setdefault(year % 100, year) != year for year in years)


class YearTickFormatter(ticker.Formatter):
    """Integer years as two digits (``24``) or four (``2024``).

    ``suffix`` is appended to every label (``"년"``). With ``digits=2``,
    :meth:`format_ticks` prints four digits when the years in view would
    otherwise repeat (``00, 50, 00``).
    """

    def __init__(self, digits: Literal[2, 4], suffix: str = "") -> None:
        if digits not in (2, 4):
            raise ValueError(f"digits must be 2 or 4, got {digits!r}")
        self.digits = digits
        self.suffix = suffix
        self._four = digits == 4

    def _text(self, x: float) -> str:
        year = round(x)
        body = f"{year}" if self._four else f"{year % 100:02d}"
        return f"{body}{self.suffix}"

    def __call__(self, x: float, pos: int | None = None) -> str:
        """One year's label, as decided by the last :meth:`format_ticks`."""
        return self._text(x)

    def format_ticks(self, values: Sequence[float]) -> list[str]:
        """Labels for the ticks; four digits if two-digit years would repeat."""
        shown = list(values)
        axis = getattr(self, "axis", None)
        if axis is not None:
            low, high = sorted(float(v) for v in axis.get_view_interval())
            shown = [v for v in shown if low <= float(v) <= high]
        self._four = self.digits == 4 or two_digits_repeat(
            [round(v) for v in shown]
        )
        return [self._text(v) for v in values]
