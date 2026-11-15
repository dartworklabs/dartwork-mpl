"""The ticks slice's types, and the one place user input becomes them.

A tick axis is read into :class:`AxesFacts` (what the axes show and who set
their formatters) and decided into :class:`AxesPlan` (one :data:`AxisPlan`
per axis and the spines to show). Tick text is decided at draw time from
:class:`TickValues` into an :class:`AxisText`: one :class:`Unit` from a
:class:`Ladder` and one decimal count for the whole axis.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, NewType

Decimals = NewType("Decimals", int)
"""A count of decimal places."""

Ems = NewType("Ems", float)
"""A length in ems of the tick font."""

Digits = Literal[2, 4]
"""Year digits on tick labels: ``24`` or ``2024``."""

Side = Literal["right", "top"]
"""A side whose spine the layout shows for a twin scale."""


@dataclass(frozen=True)
class Unit:
    """One rung of a unit ladder: divide by ``factor``, append ``label``."""

    factor: float
    label: str


PLAIN = Unit(1.0, "")


@dataclass(frozen=True)
class Ladder:
    """Units an axis may print in, smallest first."""

    rungs: tuple[Unit, ...]

    @classmethod
    def of(cls, *rungs: tuple[float, str]) -> Ladder:
        """The plain unit, then ``(factor, label)`` rungs."""
        return cls((PLAIN, *(Unit(f, label) for f, label in rungs)))

    def find(self, label: str) -> Unit | None:
        """The rung printed as ``label``, if any."""
        return next((r for r in self.rungs if r.label == label), None)

    def labels(self) -> str:
        """The rung labels, quoted, for an error message."""
        return ", ".join(repr(r.label) for r in self.rungs)


SI = Ladder.of((1e3, "k"), (1e6, "M"), (1e9, "G"), (1e12, "T"))
MYRIAD = Ladder.of((1e4, "만"), (1e8, "억"), (1e12, "조"), (1e16, "경"))
FINANCE = Ladder.of((1e3, "k"), (1e6, "M"), (1e9, "B"), (1e12, "T"))
MYRIAD_LOCALES = {
    "ko": MYRIAD,
    "zh": Ladder.of((1e4, "万"), (1e8, "亿"), (1e12, "兆"), (1e16, "京")),
    "ja": Ladder.of((1e4, "万"), (1e8, "億"), (1e12, "兆"), (1e16, "京")),
}
LADDERS = {"si": SI, "myriad": MYRIAD, "finance": FINANCE}


class LadderChoice(Enum):
    """``dm.config.number_ladder``: follow the figure's language, or one ladder."""

    AUTO = "auto"
    SI = "si"
    MYRIAD = "myriad"

    @classmethod
    def parse(cls, value: object) -> LadderChoice:
        """The choice ``value`` names; ``ValueError`` naming the config field."""
        for choice in cls:
            if choice.value == value:
                return choice
        raise ValueError(
            "config.number_ladder must be 'auto', 'si' or 'myriad', "
            f"got {value!r}"
        )


@dataclass(frozen=True)
class Language:
    """What picks the large-number ladder: the asked one and the figure's text."""

    asked: LadderChoice
    korean: bool


def parse_digits(value: object, what: str = "years") -> Digits:
    """``2`` or ``4``; ``ValueError`` naming ``what`` otherwise."""
    if value == 2 and not isinstance(value, bool):
        return 2
    if value == 4 and not isinstance(value, bool):
        return 4
    raise ValueError(f"{what} must be 2 or 4, got {value!r}")


# -- tick text ---------------------------------------------------------------


class Rule(Enum):
    """How an axis picks its unit from a ladder.

    ``MAX``: the unit of the largest visible ``|tick|``. ``WHOLE``: a unit in
    which every tick is whole, of those the one with the shortest longest
    label. ``FIXED``: always the one ladder label asked. ``DEFAULT``: the
    library's numbers on an axis nobody formatted: plain below one million,
    the largest tick's unit from there unless that needs over two decimals.
    """

    MAX = "max"
    WHOLE = "whole"
    FIXED = "fixed"
    DEFAULT = "default"


@dataclass(frozen=True)
class PerTick:
    """How a fixed-decimal formatter writes each value alone.

    ``separators``: thousands separators or none. ``zero``: a value that
    prints as zero reads ``0.0`` bare (``"bare"``), keeps currency and unit
    (``"affixed"``: ``$0``) or only an exact zero is ``0`` (``"exact"``).
    ``compact``: trailing zeros go (``1.5억``) and a value under the first
    rung above one prints whole with no unit (``7,500``).
    """

    separators: bool = True
    zero: Literal["bare", "affixed", "exact"] = "bare"
    compact: bool = False


@dataclass(frozen=True)
class NumberStyle:
    """Everything a number formatter was asked: ladder, rule and fixed parts."""

    ladder: Ladder
    rule: Rule = Rule.MAX
    unit: Unit | None = None  # the unit of ``Rule.FIXED``
    decimals: Decimals | None = None
    currency: str = ""
    per_tick: PerTick | None = None

    @classmethod
    def parse(
        cls,
        ladder: Ladder,
        unit: str = "max",
        *,
        decimals: object = None,
        currency: str = "",
        per_tick: PerTick | None = None,
    ) -> NumberStyle:
        """``unit`` is ``"max"``, ``"whole"`` or one ladder label.

        Raises ``ValueError`` for another ``unit`` or negative ``decimals``.
        """
        if decimals is not None and (
            isinstance(decimals, bool)
            or not isinstance(decimals, int)
            or decimals < 0
        ):
            raise ValueError(f"decimals must be non-negative, got {decimals!r}")
        fixed = ladder.find(unit)
        if unit in ("max", "whole"):
            rule = Rule(unit)
        elif fixed is not None:
            rule = Rule.FIXED
        else:
            raise ValueError(
                f"unit must be 'max', 'whole' or one of {ladder.labels()} "
                f"(got {unit!r})"
            )
        count = None if decimals is None else Decimals(decimals)
        return cls(ladder, rule, fixed, count, currency, per_tick)


@dataclass(frozen=True)
class TickValues:
    """The tick values an axis shows, and whether its scale is linear."""

    values: tuple[float, ...]
    linear: bool = True

    @classmethod
    def of(cls, values: Sequence[float], *, linear: bool = True) -> TickValues:
        """The finite values, as floats."""
        finite = tuple(float(v) for v in values if abs(float(v)) < float("inf"))
        return cls(finite, linear)


@dataclass(frozen=True)
class TextFacts:
    """What a number formatter decides from at each draw."""

    ticks: TickValues
    style: NumberStyle


@dataclass(frozen=True)
class AxisText:
    """One axis decision: one unit and one decimal count for every tick.

    ``unit`` is ``None`` when each tick takes its own unit, ``decimals``
    ``None`` when each tick takes its own count.
    """

    unit: Unit | None
    decimals: Decimals | None


@dataclass(frozen=True, order=True)
class Cost:
    """How a unit prints an axis: decimals, longest label, then the factor."""

    decimals: int
    longest: int
    factor: float


@dataclass(frozen=True)
class TickScale:
    """How an axis's ticks print a number, for text that should read alike.

    ``prefix``, the value divided by ``factor``, ``suffix``:
    ``TickScale(1e9, "", "G")`` prints ``33e9`` as ``33G``. ``zero``: a value
    that prints as zero drops the affixes (``"bare"``) or keeps them
    (``"affixed"``: ``$0``).
    """

    factor: float = 1.0
    prefix: str = ""
    suffix: str = ""
    zero: Literal["bare", "affixed"] = "bare"


# -- axis formats on axes nobody formatted -------------------------------------


class Kind(Enum):
    """What an axis shows, as far as the library's default format goes."""

    NUMBERS = "numbers"  # linear, no unit converter
    DATES = "dates"  # matplotlib's stock concise date formatter
    OTHER = "other"  # log, category, a formatter someone set ...


@dataclass(frozen=True)
class AxisFacts:
    """One axis as the library's default format reads it, before the layout.

    ``own_formatter`` / ``own_locator``: still matplotlib's defaults, nobody
    set or configured them. ``fixed_texts``: label texts someone fixed by
    order (``set_xticklabels``); ``pinnable`` when the locator gives as many
    ticks now as there are texts. ``years``: the plotted data along this
    axis are integer years. ``quarter_ends``: date data that are quarterly
    (``False``: quarter starts or mid-quarter; ``None``: not quarterly).
    """

    x: bool
    kind: Kind
    ticks: TickValues
    own_formatter: bool = True
    own_locator: bool = True
    fixed_texts: bool = False
    pinnable: bool = False
    years: bool = False
    quarter_ends: bool | None = None


@dataclass(frozen=True)
class TwinFacts:
    """How an Axes draws a twin scale on the right and the top.

    Per side: ``draws`` it draws its own scale there in a shared box;
    ``hides_other`` its other axis is hidden, as ``twinx`` hides a twin's x;
    ``twin_draws`` some member of the box with its other axis hidden draws
    there; ``settled`` a layout showed this side's line before.
    """

    draws: frozenset[Side] = frozenset()
    hides_other: frozenset[Side] = frozenset()
    twin_draws: frozenset[Side] = frozenset()
    settled: frozenset[Side] = frozenset()


@dataclass(frozen=True)
class AxesFacts:
    """An Axes before the layout: its two axes, twins and the year setting."""

    x: AxisFacts
    y: AxisFacts
    digits: Digits = 2
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

    digits: Digits


@dataclass(frozen=True)
class QuarterDates:
    """Quarter ticks and words: ``24.Q1``, on quarter starts or ends."""

    digits: Digits
    ends: bool


@dataclass(frozen=True)
class YearTicks:
    """Whole-year ticks (if ``locator``) and year words (if ``formatter``)."""

    digits: Digits
    locator: bool
    formatter: bool


@dataclass(frozen=True)
class PinTicks:
    """Keep the ticks under fixed texts where they are now."""


AxisPlan = Leave | Numbers | PeriodDates | QuarterDates | YearTicks | PinTicks


@dataclass(frozen=True)
class AxesPlan:
    """What the layout gives one Axes: a plan per axis, spines to show."""

    x: AxisPlan
    y: AxisPlan
    spines: frozenset[Side] = frozenset()


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
