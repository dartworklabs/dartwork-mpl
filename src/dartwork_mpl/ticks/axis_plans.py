"""What the layout-time tick steps read and decide.

``prepare`` reads an Axes nobody formatted into :class:`AxesFacts` (what
its axes show, who set their formatters, its twins) and decides an
:class:`AxesPlan`: one :data:`AxisPlan` per axis and the spines to show.
``thin_dates`` reads crowded date labels at the fitted size into a
:class:`Crowding` and decides a :class:`Thinning`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

from .model import Ems, TickValues, TwinSide, TwoDigits, YearDigits

# -- axis formats on axes nobody formatted -------------------------------------


@dataclass(frozen=True)
class NumberAxis:
    """A linear axis with no unit converter; ``years``: x data that are
    integer years."""

    years: bool = False


@dataclass(frozen=True)
class DateAxis:
    """Dates on matplotlib's stock concise formatter.

    ``quarter_ends``: the plotted dates are quarterly, on quarter ends
    (``True``) or starts and mid-quarter (``False``); ``None``: not
    quarterly.
    """

    quarter_ends: bool | None = None


@dataclass(frozen=True)
class OtherAxis:
    """Log, category, a formatter someone set ..."""


AxisKind: TypeAlias = NumberAxis | DateAxis | OtherAxis
"""What an axis shows, as far as the library's default format goes."""


@dataclass(frozen=True)
class AxisFacts:
    """One axis as the library's default format reads it, before the layout.

    ``own_formatter`` / ``own_locator``: still matplotlib's defaults, nobody
    set or configured them. ``fixed_texts``: label texts someone fixed by
    order (``set_xticklabels``).
    """

    x: bool
    kind: AxisKind
    ticks: TickValues
    own_formatter: bool = True
    own_locator: bool = True
    fixed_texts: bool = False


@dataclass(frozen=True)
class TwinFacts:
    """How an Axes draws a twin scale on the right and the top.

    Per side: ``draws`` it draws its own scale there in a shared box;
    ``hides_other`` its other axis is hidden, as ``twinx`` hides a twin's x;
    ``twin_draws`` some member of the box with its other axis hidden draws
    there; ``settled`` a layout showed this side's line before.
    """

    draws: frozenset[TwinSide] = frozenset()
    hides_other: frozenset[TwinSide] = frozenset()
    twin_draws: frozenset[TwinSide] = frozenset()
    settled: frozenset[TwinSide] = frozenset()


@dataclass(frozen=True)
class AxesFacts:
    """An Axes before the layout: its two axes, twins and the year setting."""

    x: AxisFacts
    y: AxisFacts
    digits: YearDigits = field(default_factory=TwoDigits)
    twin: TwinFacts = field(default_factory=TwinFacts)


@dataclass(frozen=True)
class Leave:
    """Keep the axis as it is."""


@dataclass(frozen=True)
class Numbers:
    """The library's numbers: separators, a unit from one million."""


@dataclass(frozen=True)
class PeriodDates:
    """Whole two-digit dates on the converter's locator: ``24.01``."""

    digits: YearDigits


@dataclass(frozen=True)
class QuarterDates:
    """Quarter ticks and words: ``24.Q1``, on quarter starts or ends."""

    digits: YearDigits
    ends: bool


@dataclass(frozen=True)
class YearTicks:
    """Whole-year ticks (if ``locator``) and year words (if ``formatter``)."""

    digits: YearDigits
    locator: bool
    formatter: bool


AxisPlan = Leave | Numbers | PeriodDates | QuarterDates | YearTicks


@dataclass(frozen=True)
class AxesPlan:
    """What the layout gives one Axes: a plan per axis, spines to show."""

    x: AxisPlan
    y: AxisPlan
    spines: frozenset[TwinSide] = frozenset()


# -- thinning crowded date labels after the fit --------------------------------


@dataclass(frozen=True)
class Candidate:
    """A sparser tick set: its position in the locator's order and label gap."""

    index: int
    gap: Ems


@dataclass(frozen=True)
class Crowding:
    """The current label gap of a date axis and its sparser candidates."""

    gap: Ems
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True)
class Thinning:
    """The candidate to take, or ``None`` to keep the ticks."""

    index: int | None = None
