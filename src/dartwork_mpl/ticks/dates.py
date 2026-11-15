"""Date tick formatters and locators: whole periods, quarters, dated categories.

:class:`PeriodDateFormatter` writes whole two-digit dates on matplotlib's
date locator (``24.01``), :class:`QuarterLocator` and
:class:`QuarterDateFormatter` tick and word quarters (``24.Q1``), and
:class:`CategoryDateLocator` / :class:`CategoryDateFormatter` give category
positions that stand for dates the same words.
"""

from __future__ import annotations

import datetime
import math
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

import matplotlib.dates as mdates
import matplotlib.ticker as ticker

from .formatters import shown_values
from .measure import date_zone, num2date
from .model import YearDigits, Zone


class PeriodDateFormatter(mdates.ConciseDateFormatter):
    """Every date tick whole: ``23`` · ``23.01`` · ``23.01.15``.

    Times read ``09:00`` under a dated corner label, left out while a tick
    in view already reads that date (midnight on an hourly axis).
    ``digits=4`` prints ``2023.01``; two digits that would repeat print four.
    """

    TEMPLATES = (
        ("{y}", "{y}.%m", "{y}.%m.%d", "%H:%M", "%H:%M", "%S.%f"),
        ("", "{y}.%m", "{y}.%m.%d", "{y}.%m.%d", "%H:%M", "%H:%M"),
        ("", "", "", "{y}.%m.%d", "{y}.%m.%d", "{y}.%m.%d %H:%M"),
    )

    def __init__(
        self,
        locator: ticker.Locator,
        tz: Zone = None,
        *,
        digits: YearDigits,
        show_offset: bool = True,
        usetex: bool | None = None,
    ) -> None:
        """Keep the settings this formatter or locator was made with."""
        self.digits: YearDigits = digits
        self.zone: Zone = tz
        self._short = self._fill("%y")
        self._long = self._fill("%Y")
        self._corner_shown = False
        formats, zeros, offsets = self._long if digits.four(()) else self._short
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            locator,
            tz=tz,
            formats=formats,
            zero_formats=zeros,
            offset_formats=offsets,
            show_offset=show_offset,
            usetex=usetex,
        )

    @classmethod
    def _fill(cls, year: str) -> tuple[list[str], list[str], list[str]]:
        f, z, o = ([t.replace("{y}", year) for t in g] for g in cls.TEMPLATES)
        return f, z, o

    def format_ticks(self, values: list[float]) -> list[str]:
        """Labels for the ticks; four-digit years if two would repeat."""
        shown = shown_values(self, values)
        four = self.digits.four([num2date(v, self.zone).year for v in shown])
        self.formats, self.zero_formats, self.offset_formats = (
            list(g) for g in (self._long if four else self._short)
        )
        labels: list[str] = super().format_ticks(values)
        inside = set(shown)
        texts = {
            t for v, t in zip(values, labels, strict=True) if float(v) in inside
        }
        self._corner_shown = super().get_offset() in texts
        return labels

    def get_offset(self) -> str:
        """The corner label, empty while a tick in view reads the same date."""
        return "" if self._corner_shown else str(super().get_offset())


QUARTER_STEPS = (1, 2, 4, 8)
LONG_QUARTER_STEPS = (*QUARTER_STEPS, 16, 20, 40, 80, 200, 400)


def quarter_words(
    moments: Sequence[datetime.datetime], digits: YearDigits
) -> list[str]:
    """``23.Q1, 23.Q3``; four-digit years with ``digits=4`` or when two repeat."""
    four = digits.four([m.year for m in moments])
    return [
        f"{m.year if four else f'{m.year % 100:02d}'}.Q{(m.month - 1) // 3 + 1}"
        for m in moments
    ]


@runtime_checkable
class Localizes(Protocol):
    """A pytz zone: a naive time becomes local through ``localize``."""

    def localize(self, dt: datetime.datetime) -> datetime.datetime:
        """``dt`` in this zone, its offset as of that moment."""
        ...


def _quarter_moment(
    index: int, ends: bool, tz: datetime.tzinfo | None
) -> datetime.datetime:
    """Midnight starting (or ending) quarter ``index`` = year * 4 + quarter - 1."""
    year, quarter = divmod(index + (1 if ends else 0), 4)
    naive = datetime.datetime(year, quarter * 3 + 1, 1)
    if ends:
        naive -= datetime.timedelta(days=1)
    if isinstance(tz, Localizes):  # pytz zones
        return tz.localize(naive)
    return naive.replace(tzinfo=tz)


class QuarterLocator(mdates.DateLocator):
    """Every ``step``-th quarter start (or end) in view, counted from year 0.

    Step 2 ticks Q1 and Q3, step 4 every Q1; the layout's thinning moves
    ``step`` through ``steps``.
    """

    def __init__(self, *, ends: bool = False, tz: Zone = None) -> None:
        """Keep the settings this formatter or locator was made with."""
        super().__init__(tz)  # pyright: ignore[reportUnknownMemberType]
        self.steps = LONG_QUARTER_STEPS
        self.step = self.steps[0]
        self.ends = ends

    def take(self, step: int) -> None:
        """Tick every ``step``-th quarter from now on."""
        self.step = step

    def __call__(self) -> list[float]:
        """The quarter ticks inside the axis view."""
        if self.axis is None:
            return []
        return self.tick_values(*self.axis.get_view_interval())

    def tick_values(self, vmin: float, vmax: float) -> list[float]:
        """The quarter ticks in ``[vmin, vmax]`` (date numbers)."""
        low, high = sorted((float(vmin), float(vmax)))
        if not (math.isfinite(low) and math.isfinite(high)):
            return []
        zone = date_zone(self)
        first, last = num2date(low, zone), num2date(high, zone)
        start = max(first.year * 4 + (first.month - 1) // 3 - 1, 4)
        stop = min(last.year * 4 + (last.month - 1) // 3 + 1, 9999 * 4 + 2)
        start += -start % self.step
        ticks: list[float] = []
        for index in range(start, stop + 1, self.step):
            num = float(
                mdates.date2num(_quarter_moment(index, self.ends, zone))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            )
            if low <= num <= high:
                ticks.append(num)
        return list(self.raise_if_exceeds(ticks))


class QuarterDateFormatter(ticker.Formatter):
    """Quarter words for the ticks in view; none for ticks outside it."""

    def __init__(self, digits: YearDigits, tz: Zone = None) -> None:
        """Keep the settings this formatter or locator was made with."""
        self.digits: YearDigits = digits
        self.tz: Zone = tz

    def format_ticks(self, values: list[float]) -> list[str]:
        """Words for the ticks in view, worded together."""
        inside = shown_values(self, values)
        words = quarter_words(
            [num2date(v, self.tz) for v in inside], self.digits
        )
        by_value = dict(zip(inside, words, strict=True))
        return [by_value.get(float(v), "") for v in values]

    def __call__(self, x: float, pos: int | None = None) -> str:
        """One tick's word, alone."""
        return self.format_ticks([float(x)])[0]


# -- dates at category positions ---------------------------------------------------


def _within(position: float, vmin: float, vmax: float) -> bool:
    low, high = sorted((float(vmin), float(vmax)))
    return low - 1e-9 <= position <= high + 1e-9


class CategoryDateLocator(ticker.Locator):
    """Every ``step``-th of ``n`` category positions in view, from its start."""

    def __init__(
        self, n: int, steps: Sequence[int], starts: Sequence[int] | None = None
    ) -> None:
        """Keep the settings this formatter or locator was made with."""
        self.n = n
        self.steps = tuple(steps)
        self.step = self.steps[0]
        self._starts = dict(
            zip(self.steps, starts or [0] * len(steps), strict=True)
        )

    def take(self, step: int) -> None:
        """Tick every ``step``-th position from now on."""
        self.step = step

    def tick_values(self, vmin: float, vmax: float) -> list[float]:
        """Positions ``start, start + step ... < n`` in ``[vmin, vmax]``."""
        grid = range(self._starts.get(self.step, 0), self.n, self.step)
        return [float(i) for i in grid if _within(i, vmin, vmax)]

    def __call__(self) -> list[float]:
        """The positions inside the axis view."""
        if self.axis is None:
            return self.tick_values(-math.inf, math.inf)
        return self.tick_values(*self.axis.get_view_interval())
