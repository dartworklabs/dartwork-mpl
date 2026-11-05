"""Quarterly dates: detected from the data, ticked and worded as quarters.

Quarter labels on a real date axis come from the plotted dates, not the
tick step: :func:`plotted_dates` reads the values the data sits on and
:func:`quarterly` checks they run 89-92 days apart. Such an axis reads
``23.Q1 · 23.Q3`` in the period style, ``23, Q2, Q3`` (``23년, Q2``) in the
concise style (:func:`quarter_words`, :class:`QuarterDateFormatter`).
:class:`QuarterLocator` ticks quarter starts, or quarter ends for quarter-end
data, every 1, 2, 4 or 8 quarters, so a thinned axis keeps Q1 and never
switches to month notation.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Literal

import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from matplotlib.container import BarContainer

from ._dates import DateStyle, Digits, _date2num, _in_view, _num2date
from ._years import two_digits_repeat

__all__ = [
    "QUARTER_STEPS",
    "QuarterDateFormatter",
    "QuarterLocator",
    "plotted_dates",
    "quarter_anchor",
    "quarter_words",
    "quarterly",
]

# Neighbouring plotted dates this many days apart are quarterly data.
_QUARTER_DAYS = (89.0, 92.0)
# Quarter steps a thinned axis moves through: every quarter, half year, year,
# two years. Steps of 4 or more show only Q1.
QUARTER_STEPS = (1, 2, 4, 8)
# A real date axis can span decades; past two years it keeps the quarter
# notation with 4, 5, 10, 20, 50 and 100-year steps.
_LONG_QUARTER_STEPS = (*QUARTER_STEPS, 16, 20, 40, 80, 200, 400)
_FIRST_YEAR, _LAST_YEAR = 1, 9999  # what datetime can hold


def quarterly(nums: Sequence[float] | npt.ArrayLike) -> bool:
    """Whether date numbers are quarterly: 2+ distinct, 89-92 days apart."""
    values = np.unique(np.asarray(nums, dtype=float))
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return False
    gaps = np.diff(values)
    low, high = _QUARTER_DAYS
    return bool(np.all((gaps >= low) & (gaps <= high)))


def _bar_positions(
    container: BarContainer, which: Literal["x", "y"], slot: float | None
) -> npt.NDArray[np.float64]:
    """Where bars stand: their centres, or with ``slot`` the slot they fill.

    A bar that lies inside the slot of width ``slot`` around the multiple of
    ``slot`` nearest its centre stands for that multiple: bars grouped side
    by side at ``year -/+ w/2`` stand for the year (``slot=1``).
    """
    starts, sizes = (
        (
            [p.get_x() for p in container.patches],
            [p.get_width() for p in container.patches],
        )
        if which == "x"
        else (
            [p.get_y() for p in container.patches],
            [p.get_height() for p in container.patches],
        )
    )
    start = np.asarray(starts, dtype=float)
    end = start + np.asarray(sizes, dtype=float)
    centre: npt.NDArray[np.float64] = (start + end) / 2
    if slot is None:
        return centre
    near = np.rint(centre / slot) * slot
    low, high = np.minimum(start, end), np.maximum(start, end)
    tol = 1e-6 * slot
    inside = (low >= near - slot / 2 - tol) & (high <= near + slot / 2 + tol)
    placed: npt.NDArray[np.float64] = np.where(inside, near, centre)
    return placed


def plotted_dates(
    ax: Axes, which: Literal["x", "y"], *, bar_slot: float | None = None
) -> npt.NDArray[np.float64]:
    """The x (or y) values the data sits on (date numbers on a date axis).

    Reads the axes' lines, scatter offsets and bar centres (vertical bars
    for x, horizontal for y), and those of every axes sharing that axis
    (a ``twinx`` line counts for the shared x). Lines count only when they
    are in data units on both axes: an ``axhline`` (x from 0 to 1 in axes
    fractions) or an ``axvline`` (a date marker spanning the height) marks
    a value rather than plotting data. Collections without offsets
    (``fill_between``) are left out. ``bar_slot`` (``1`` for years) reads
    a bar inside one slot as the slot's centre (:func:`_bar_positions`), so
    grouped bars stand for their year.
    """
    column = 0 if which == "x" else 1
    shared = ax.get_shared_x_axes() if which == "x" else ax.get_shared_y_axes()
    bars = "vertical" if which == "x" else "horizontal"
    chunks: list[npt.NDArray[np.float64]] = []
    for member in shared.get_siblings(ax):
        data = member.transData
        for line in member.lines:
            # Data units on both axes: axhline / axvline span an axes
            # fraction across, so they mark a value rather than plot data.
            if all(line.get_transform().contains_branch_seperately(data)):
                xy = np.asarray(line.get_xydata(), dtype=float)
                chunks.append(xy.reshape(-1, 2)[:, column])
        for coll in member.collections:
            if (
                isinstance(coll, PathCollection)
                and (
                    coll.get_offset_transform().contains_branch_seperately(
                        data
                    )[column]
                )
            ):
                offsets: npt.NDArray[np.float64] = np.asarray(
                    np.ma.filled(
                        np.ma.asarray(coll.get_offsets(), dtype=float), np.nan
                    ),
                    dtype=float,
                )
                chunks.append(offsets.reshape(-1, 2)[:, column])
        for container in member.containers:
            if not isinstance(container, BarContainer):
                continue
            if container.orientation != bars:
                continue
            chunks.append(_bar_positions(container, which, bar_slot))
    if not chunks:
        return np.empty(0, dtype=float)
    values: npt.NDArray[np.float64] = np.concatenate(chunks)
    finite = np.isfinite(values)
    if finite.all():
        return values  # no copy for the usual all-finite data
    kept: npt.NDArray[np.float64] = values[finite]
    return kept


def _quarter_end(day: datetime.date) -> bool:
    following = day + datetime.timedelta(days=1)
    return following.day == 1 and following.month in (1, 4, 7, 10)


def quarter_anchor(
    nums: Sequence[float] | npt.ArrayLike,
    tz: datetime.tzinfo | str | None = None,
) -> Literal["start", "end"]:
    """``"end"`` when every date is a quarter's last day, else ``"start"``."""
    days = {
        _num2date(float(v), tz).date()
        for v in np.unique(np.asarray(nums, dtype=float))
    }
    if days and all(_quarter_end(day) for day in days):
        return "end"
    return "start"


def quarter_words(
    moments: Sequence[datetime.datetime],
    *,
    style: DateStyle,
    digits: Digits,
    korean: bool,
) -> tuple[list[str], str]:
    """Quarter labels and the corner label for dates shown together.

    ``"period"``: ``23.Q1, 23.Q3`` and no corner label. ``"concise"``: the
    year on Q1 (``23``; ``23년`` when ``korean``) and ``Q2, Q3, Q4``
    otherwise, with the last year in the corner when no Q1 is shown. Years
    print four digits with ``digits=4`` or when two would repeat.
    """
    four = digits == 4 or two_digits_repeat([m.year for m in moments])

    def year(moment: datetime.datetime) -> str:
        return f"{moment.year}" if four else f"{moment.year % 100:02d}"

    quarters = [(m.month - 1) // 3 + 1 for m in moments]
    if style == "period":
        return [
            f"{year(m)}.Q{q}" for m, q in zip(moments, quarters, strict=True)
        ], ""
    unit = "년" if korean else ""
    words = [
        f"{year(m)}{unit}" if q == 1 else f"Q{q}"
        for m, q in zip(moments, quarters, strict=True)
    ]
    offset = ""
    if moments and 1 not in quarters:
        offset = f"{year(moments[-1])}{unit}"
    return words, offset


def _quarter_moment(
    index: int, anchor: str, tz: datetime.tzinfo
) -> datetime.datetime:
    """Midnight starting (or ending) quarter ``index`` = year * 4 + quarter - 1."""
    year, quarter = divmod(index + (1 if anchor == "end" else 0), 4)
    naive = datetime.datetime(year, quarter * 3 + 1, 1)
    if anchor == "end":
        naive -= datetime.timedelta(days=1)
    localize = getattr(tz, "localize", None)  # pytz zones
    if callable(localize):
        moment: datetime.datetime = localize(naive)
        return moment
    return naive.replace(tzinfo=tz)


class QuarterLocator(mdates.DateLocator):
    """Ticks on every ``step``-th quarter start (or end) inside the view.

    Quarters are counted from year 0 (``year * 4 + quarter - 1``), so step 2
    ticks Q1 and Q3, step 4 every Q1, step 8 the Q1 of even years; the grid
    is the same whatever the view. ``steps`` lists the steps
    :func:`~dartwork_mpl.formatting.thin_crowded_date_ticks` may move
    through, smallest first; ``step`` starts at the first. ``anchor="end"``
    ticks each quarter's last day, for quarter-end data.
    """

    def __init__(
        self,
        steps: Sequence[int] = _LONG_QUARTER_STEPS,
        *,
        anchor: Literal["start", "end"] = "start",
        tz: datetime.tzinfo | str | None = None,
    ) -> None:
        if anchor not in ("start", "end"):
            raise ValueError(f"anchor must be 'start' or 'end', got {anchor!r}")
        if not steps or any(s < 1 for s in steps):
            raise ValueError("QuarterLocator needs steps >= 1")
        super().__init__(tz)  # type: ignore[no-untyped-call]
        self.steps = tuple(steps)
        self.step = self.steps[0]
        self.anchor = anchor

    def __call__(self) -> list[float]:
        """Return the quarter ticks inside the axis view."""
        if self.axis is None:
            return []
        return self.tick_values(*self.axis.get_view_interval())

    def tick_values(self, vmin: float, vmax: float) -> list[float]:
        """Return the quarter ticks in ``[vmin, vmax]`` (date numbers)."""
        low, high = sorted((float(vmin), float(vmax)))
        if not (np.isfinite(low) and np.isfinite(high)):
            return []
        first = _num2date(low, self.tz)
        last = _num2date(high, self.tz)
        start = max(
            first.year * 4 + (first.month - 1) // 3 - 1, _FIRST_YEAR * 4
        )
        stop = min(
            last.year * 4 + (last.month - 1) // 3 + 1, _LAST_YEAR * 4 + 2
        )
        start += -start % self.step
        ticks = []
        for index in range(start, stop + 1, self.step):
            num = _date2num(_quarter_moment(index, self.anchor, self.tz))
            if low <= num <= high:
                ticks.append(num)
        return list(self.raise_if_exceeds(ticks))


class QuarterDateFormatter(ticker.Formatter):
    """Quarter words for :class:`QuarterLocator` ticks (:func:`quarter_words`).

    Ticks outside the view get no label, so the words, the four-digit
    fallback and the corner label follow the quarters someone can see.
    """

    def __init__(
        self,
        *,
        style: DateStyle,
        digits: Digits = 2,
        korean: bool = False,
        tz: datetime.tzinfo | str | None = None,
        show_offset: bool = True,
    ) -> None:
        if digits not in (2, 4):
            raise ValueError(f"digits must be 2 or 4, got {digits!r}")
        self.style = style
        self.digits = digits
        self.korean = korean
        self.tz = tz
        self.show_offset = show_offset
        self._offset = ""

    def format_ticks(self, values: Sequence[float]) -> list[str]:
        """Words for the ticks in view, worded together as one axis."""
        shown = set(_in_view(self, values))
        inside = [float(v) for v in values if float(v) in shown]
        words, offset = quarter_words(
            [_num2date(v, self.tz) for v in inside],
            style=self.style,
            digits=self.digits,
            korean=self.korean,
        )
        self._offset = offset if self.show_offset else ""
        by_value = dict(zip(inside, words, strict=True))
        return [by_value.get(float(v), "") for v in values]

    def __call__(self, x: float, pos: int | None = None) -> str:
        """One tick's word, worded on its own."""
        return self.format_ticks([x])[0]

    def format_data_short(self, value: float) -> str:
        """The full date, for the cursor read-out."""
        return _num2date(value, self.tz).strftime("%Y-%m-%d")

    def get_offset(self) -> str:
        """The corner label of the last :meth:`format_ticks`."""
        return self._offset
