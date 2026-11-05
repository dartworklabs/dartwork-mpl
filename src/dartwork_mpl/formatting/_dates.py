"""Date-axis tick text: the period and short concise styles.

``dm.config.date_style`` and ``dm.config.tick_years`` choose how untouched
date axes read (:func:`date_formatter`):

- ``"period"`` (default): every tick a whole date, ``23`` · ``23.01`` ·
  ``23.01.15``, times under a dated corner label (:class:`PeriodDateFormatter`);
- ``"concise"``: matplotlib's concise words with two-digit years, ``23, May,
  Sep`` (:class:`ShortConciseDateFormatter`), Korean ``23년, 5월`` in Korean
  figures (:class:`KoreanConciseDateFormatter` with ``digits=2``);
- ``tick_years=4`` prints four-digit years; with ``"concise"`` that is
  matplotlib's stock concise formatter (and
  :class:`KoreanConciseDateFormatter`'s ``2024년, 3월``).

Two-digit years never repeat on one axis: when two years in view share their
last two digits (an axis spanning a century) the formatter prints four.
Quarterly data reads quarters instead; see :mod:`._quarters`.
"""

from __future__ import annotations

import datetime
import re
from collections.abc import Sequence
from typing import Any, Literal

import matplotlib.dates as mdates
import matplotlib.ticker as ticker

from ._years import two_digits_repeat

__all__ = [
    "KoreanConciseDateFormatter",
    "PeriodDateFormatter",
    "ShortConciseDateFormatter",
    "date_formatter",
    "reads_quarters",
]

Digits = Literal[2, 4]
DateStyle = Literal["period", "concise"]

# Marks a day-of-month number so ShortConciseDateFormatter can drop its zero
# padding (``8``, not ``08``) without touching a two-digit year (``05``).
_DAY = "\u2060"
# "03월" -> "3월", "08일" -> "8일": Korean dates drop the zero padding.
_PADDED = re.compile(r"(?<!\d)0(\d)(?=[월일])")


def _num2date(
    value: float, tz: datetime.tzinfo | str | None = None
) -> datetime.datetime:
    """``mdates.num2date`` for one value, typed."""
    moment: datetime.datetime = mdates.num2date(value, tz=tz)  # type: ignore[no-untyped-call]
    return moment


def _date2num(moment: datetime.datetime) -> float:
    """``mdates.date2num`` for one datetime, typed."""
    return float(mdates.date2num(moment))  # type: ignore[no-untyped-call]


def _in_view(
    formatter: ticker.Formatter, values: Sequence[float]
) -> list[float]:
    """The values inside the formatter's axis view (all of them unattached)."""
    axis = getattr(formatter, "axis", None)
    if axis is None:
        return [float(v) for v in values]
    low, high = sorted(float(v) for v in axis.get_view_interval())
    return [float(v) for v in values if low <= float(v) <= high]


class _YearDigitsDates(mdates.ConciseDateFormatter):
    """Concise date ticks whose year directive is two digits or four.

    Subclasses give ``_TEMPLATES`` (formats, zero formats, offset formats)
    with ``{y}`` for the year. With ``digits=2`` :meth:`format_ticks`
    prints four digits while two years in view share their last two digits.
    Format lists someone edited are left as they are.
    """

    _TEMPLATES: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]

    def __init__(
        self,
        locator: mdates.DateLocator,
        tz: datetime.tzinfo | str | None = None,
        *,
        digits: Digits = 2,
        show_offset: bool = True,
        usetex: bool | None = None,
    ) -> None:
        if digits not in (2, 4):
            raise ValueError(f"digits must be 2 or 4, got {digits!r}")
        self.digits = digits
        self._short = self._fill("%y")
        self._long = self._fill("%Y")
        formats, zero_formats, offset_formats = (
            self._short if digits == 2 else self._long
        )
        super().__init__(  # type: ignore[no-untyped-call]
            locator,
            tz=tz,
            formats=list(formats),
            zero_formats=list(zero_formats),
            offset_formats=list(offset_formats),
            show_offset=show_offset,
            usetex=usetex,
        )

    @classmethod
    def _fill(cls, year: str) -> tuple[list[str], list[str], list[str]]:
        formats, zero_formats, offset_formats = (
            [t.replace("{y}", year) for t in group] for group in cls._TEMPLATES
        )
        return formats, zero_formats, offset_formats

    def _tidy(self, text: str) -> str:
        return text

    def format_ticks(self, values: Sequence[float]) -> list[str]:
        """Labels for the ticks; four-digit years if two digits would repeat."""
        current = (
            list(self.formats),
            list(self.zero_formats),
            list(self.offset_formats),
        )
        if current in (self._short, self._long):
            years = [
                _num2date(v, self._tz).year for v in _in_view(self, values)
            ]
            four = self.digits == 4 or two_digits_repeat(years)
            chosen = self._long if four else self._short
            self.formats, self.zero_formats, self.offset_formats = (
                list(group) for group in chosen
            )
        labels: list[str] = super().format_ticks(values)  # type: ignore[no-untyped-call]
        return [self._tidy(label) for label in labels]

    def get_offset(self) -> str:
        """The corner label of the last :meth:`format_ticks`."""
        offset: str = super().get_offset()  # type: ignore[no-untyped-call]
        return self._tidy(offset)


class PeriodDateFormatter(_YearDigitsDates):
    """Every date tick whole: ``23`` · ``23.01`` · ``23.01.15``.

    Times read ``09:00`` under a dated corner label (``26.05.02``); midnight
    ticks of an hourly axis read the date. ``digits=4`` prints ``2023.01``.
    """

    _TEMPLATES = (
        ("{y}", "{y}.%m", "{y}.%m.%d", "%H:%M", "%H:%M", "%S.%f"),
        ("", "{y}.%m", "{y}.%m.%d", "{y}.%m.%d", "%H:%M", "%H:%M"),
        ("", "", "", "{y}.%m.%d", "{y}.%m.%d", "{y}.%m.%d %H:%M"),
    )


class ShortConciseDateFormatter(_YearDigitsDates):
    """Matplotlib's concise English words with two-digit years: ``23, May, Sep``.

    Days drop their zero padding (``Mar, 8, 15``); years keep theirs (``05``).
    """

    _TEMPLATES = (
        ("{y}", "%b", f"{_DAY}%d", "%H:%M", "%H:%M", "%S.%f"),
        ("", "{y}", "%b", f"%b-{_DAY}%d", "%H:%M", "%H:%M"),
        (
            "",
            "{y}",
            "{y}-%b",
            f"{{y}}-%b-{_DAY}%d",
            f"{{y}}-%b-{_DAY}%d",
            f"{{y}}-%b-{_DAY}%d %H:%M",
        ),
    )

    def _tidy(self, text: str) -> str:
        return text.replace(f"{_DAY}0", "").replace(_DAY, "")


class KoreanConciseDateFormatter(_YearDigitsDates):
    """Matplotlib's concise date ticks with Korean year, month and day units.

    ``digits=4`` (default) reads ``2024년, 3월, 5월``; ``digits=2`` reads
    ``24년, 3월, 5월``. Months and days drop their zero padding (``3월``,
    ``8일``).
    """

    _TEMPLATES = (
        ("{y}년", "%m월", "%d일", "%H:%M", "%H:%M", "%S.%f"),
        ("", "{y}년", "%m월", "%m월 %d일", "%H:%M", "%H:%M"),
        (
            "",
            "{y}년",
            "{y}년 %m월",
            "{y}년 %m월 %d일",
            "{y}년 %m월 %d일",
            "{y}년 %m월 %d일 %H:%M",
        ),
    )

    def __init__(
        self,
        locator: mdates.DateLocator,
        tz: datetime.tzinfo | str | None = None,
        *,
        show_offset: bool = True,
        usetex: bool | None = None,
        digits: Digits = 4,
    ) -> None:
        super().__init__(
            locator, tz, digits=digits, show_offset=show_offset, usetex=usetex
        )

    def _tidy(self, text: str) -> str:
        # "05년" keeps its two digits: only 월 and 일 drop the padding.
        return _PADDED.sub(r"\1", text)


def date_formatter(
    locator: mdates.DateLocator,
    *,
    years: Digits,
    style: DateStyle,
    korean: bool,
    tz: datetime.tzinfo | str | None = None,
    show_offset: bool = True,
    usetex: bool | None = None,
) -> mdates.ConciseDateFormatter:
    """The concise date formatter for a style, year digits and language."""
    options: dict[str, Any] = {"show_offset": show_offset, "usetex": usetex}
    if style == "period":
        return PeriodDateFormatter(locator, tz, digits=years, **options)
    if korean:
        return KoreanConciseDateFormatter(locator, tz, digits=years, **options)
    if years == 4:
        return mdates.ConciseDateFormatter(locator, tz=tz, **options)  # type: ignore[no-untyped-call]
    return ShortConciseDateFormatter(locator, tz, **options)


def reads_quarters(years: Digits, style: DateStyle) -> bool:
    """Whether quarterly data reads quarters: all but four-digit concise.

    Four-digit years in the concise style are matplotlib's own concise
    formatter, which words quarters as months.
    """
    return not (years == 4 and style == "concise")
