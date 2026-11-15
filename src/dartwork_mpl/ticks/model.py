"""The ticks slice's types, and the one place user input becomes them.

A tick axis is read into :class:`AxesFacts` (what the axes show and who set
their formatters) and decided into :class:`AxesPlan` (one :data:`AxisPlan`
per axis and the spines to show). Tick text is decided at draw time from
:class:`TickValues` into an :class:`AxisText`: one :class:`Unit` from a
:class:`Ladder` and one decimal count for the whole axis.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import ClassVar, Literal, NewType, TypeAlias, TypedDict

import numpy as np

from ..vocab import AffixedZero, BareZero

Decimals = NewType("Decimals", int)
"""A count of decimal places."""

Ems = NewType("Ems", float)
"""A length in ems of the tick font."""

Digits = Literal[2, 4]
"""Year digits on tick labels, as a caller writes them: ``2`` or ``4``."""

Zone: TypeAlias = datetime.tzinfo | str | None
"""A time zone as matplotlib's date functions take it: a ``tzinfo``, its
name (``"Asia/Seoul"``), or ``None`` for ``rcParams["timezone"]``."""

DateLike: TypeAlias = str | datetime.date | np.datetime64
"""One date as a caller writes it: an ISO string, a ``date`` / ``datetime``
(a pandas ``Timestamp`` is one) or a ``datetime64``."""


class MaxNParams(TypedDict, total=False):
    """The ``MaxNLocator.set_params`` keywords other than ``nbins``."""

    steps: Sequence[float] | None
    integer: bool
    symmetric: bool
    prune: Literal["lower", "upper", "both"] | None
    min_n_ticks: int


def repeat_two_digits(years: Sequence[int]) -> bool:
    """Whether two distinct years share their last two digits (1965, 2065)."""
    seen: dict[int, int] = {}
    return any(seen.setdefault(y % 100, y) != y for y in years)


@dataclass(frozen=True)
class TwoDigits:
    """Years as ``24``, unless two in view would repeat (1965, 2065)."""

    def four(self, years: Sequence[int]) -> bool:
        """Whether ``years`` print with four digits."""
        return repeat_two_digits(years)


@dataclass(frozen=True)
class FourDigits:
    """Years as ``2024``."""

    def four(self, years: Sequence[int]) -> bool:
        """Always four digits."""
        return True


YearDigits: TypeAlias = TwoDigits | FourDigits
"""How many digits a tick year prints."""


@dataclass(frozen=True)
class RightSide:
    """The right side, where a ``twinx`` draws its y scale."""

    spine: ClassVar[Literal["right"]] = "right"


@dataclass(frozen=True)
class TopSide:
    """The top side, where a ``twiny`` draws its x scale."""

    spine: ClassVar[Literal["top"]] = "top"


TwinSide: TypeAlias = RightSide | TopSide
"""A side whose spine the layout shows for a twin scale."""

TWIN_SIDES: tuple[TwinSide, ...] = (RightSide(), TopSide())


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


def myriad_ladder(locale: object) -> Ladder:
    """``format_axis_myriad``'s ``locale`` as its ladder; ``ValueError``."""
    if isinstance(locale, str) and locale in MYRIAD_LOCALES:
        return MYRIAD_LOCALES[locale]
    raise ValueError(
        f"locale must be one of 'ko', 'zh', or 'ja' (got {locale!r})"
    )


CurrencyPosition: TypeAlias = Literal["prefix", "suffix"]
"""Where ``format_axis_currency`` writes the symbol, as a caller says it."""


@dataclass(frozen=True)
class SymbolFirst:
    """``"prefix"``: the symbol before the number, after the minus (``-$5``)."""

    def parts(self, symbol: str) -> tuple[str, str]:
        """``(currency, unit label)`` for ``symbol``."""
        return symbol, ""


@dataclass(frozen=True)
class SymbolLast:
    """``"suffix"``: the symbol after the number (``5€``)."""

    def parts(self, symbol: str) -> tuple[str, str]:
        """``(currency, unit label)`` for ``symbol``."""
        return "", symbol


SymbolPlace: TypeAlias = SymbolFirst | SymbolLast


def parse_currency_position(value: object) -> SymbolPlace:
    """``format_axis_currency``'s ``position``; ``ValueError`` otherwise."""
    if value == "prefix":
        return SymbolFirst()
    if value == "suffix":
        return SymbolLast()
    raise ValueError(f"position must be 'prefix' or 'suffix', got {value!r}")


LadderName: TypeAlias = Literal["auto", "myriad", "finance", "si"]
"""``dm.axis_unit``'s ``ladder``."""

NumberLadder: TypeAlias = Literal["auto", "si", "myriad"]
"""``dm.config.number_ladder``."""


@dataclass(frozen=True)
class FollowFigure:
    """``"auto"``: the ladder follows the figure's language."""


LadderChoice: TypeAlias = FollowFigure | Ladder
"""A ladder asked by name, or the one the figure's language picks."""


def parse_number_ladder(value: object) -> LadderChoice:
    """``config.number_ladder``; ``ValueError`` naming the config field."""
    if value == "auto":
        return FollowFigure()
    if value == "si":
        return SI
    if value == "myriad":
        return MYRIAD
    raise ValueError(
        f"config.number_ladder must be 'auto', 'si' or 'myriad', got {value!r}"
    )


def parse_ladder_name(value: object) -> LadderChoice:
    """``dm.axis_unit``'s ``ladder``; ``ValueError`` otherwise."""
    if value == "auto":
        return FollowFigure()
    if isinstance(value, str) and value in LADDERS:
        return LADDERS[value]
    raise ValueError(
        f"ladder must be 'auto', 'myriad', 'finance' or 'si', got {value!r}"
    )


@dataclass(frozen=True)
class ByFigure:
    """``"auto"``: the ladder follows the figure; ``korean`` its text is."""

    korean: bool


@dataclass(frozen=True)
class Asked:
    """A ladder asked by name, whatever the figure's language."""

    ladder: Ladder


Language: TypeAlias = ByFigure | Asked
"""What picks the large-number ladder."""


def unit_template(label: str) -> str:
    """An axis label with ``{unit}`` marking where the unit goes."""
    if "{unit}" in label:
        return label
    return f"{label} ({{unit}})" if label.strip() else "({unit})"


def parse_digits(value: object, what: str = "years") -> YearDigits:
    """``2`` or ``4``; ``ValueError`` naming ``what`` otherwise."""
    if value == 2 and not isinstance(value, bool):
        return TwoDigits()
    if value == 4 and not isinstance(value, bool):
        return FourDigits()
    raise ValueError(f"{what} must be 2 or 4, got {value!r}")


# -- tick text ---------------------------------------------------------------


@dataclass(frozen=True)
class MaxUnit:
    """The unit of the largest visible ``|tick|``."""


@dataclass(frozen=True)
class WholeUnit:
    """A unit in which every tick is whole; of those, the shortest longest
    label."""


@dataclass(frozen=True)
class FixedUnit:
    """Always the one ladder rung asked."""

    unit: Unit


@dataclass(frozen=True)
class DefaultUnit:
    """The library's numbers on an axis nobody formatted: plain below one
    million, the largest tick's unit from there unless that needs over two
    decimals."""


UnitRule: TypeAlias = MaxUnit | WholeUnit | FixedUnit | DefaultUnit
"""How an axis picks its unit from a ladder."""


@dataclass(frozen=True)
class ExactZero:
    """Only an exact zero reads ``0``; a small value keeps its digits."""


ZeroText: TypeAlias = BareZero | AffixedZero | ExactZero
"""How a value written alone prints when it rounds to zero."""


@dataclass(frozen=True)
class PerTick:
    """How a fixed-decimal formatter writes each value alone.

    ``separators``: thousands separators or none. ``zero``: how a value
    that prints as zero reads (:data:`ZeroText`). ``compact``: trailing zeros go (``1.5억``) and a value under the first
    rung above one prints whole with no unit (``7,500``).
    """

    separators: bool = True
    zero: ZeroText = field(default_factory=BareZero)
    compact: bool = False


@dataclass(frozen=True)
class NumberStyle:
    """Everything a number formatter was asked: ladder, rule and fixed parts."""

    ladder: Ladder
    rule: UnitRule = MaxUnit()
    decimals: Decimals | None = None
    currency: str = ""
    per_tick: PerTick | None = None

    @property
    def unit(self) -> Unit | None:
        """The one unit asked, if the rule fixes it."""
        match self.rule:
            case FixedUnit(unit=unit):
                return unit
            case MaxUnit() | WholeUnit() | DefaultUnit():
                return None

    def each_alone(self, per_tick: PerTick) -> NumberStyle:
        """Fixed decimals under the max rule write each tick alone."""
        match self.rule:
            case MaxUnit() if self.decimals is not None:
                return replace(self, per_tick=per_tick)
            case MaxUnit() | WholeUnit() | FixedUnit() | DefaultUnit():
                return self

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
        rule: UnitRule
        if unit == "max":
            rule = MaxUnit()
        elif unit == "whole":
            rule = WholeUnit()
        elif fixed is not None:
            rule = FixedUnit(fixed)
        else:
            raise ValueError(
                f"unit must be 'max', 'whole' or one of {ladder.labels()} "
                f"(got {unit!r})"
            )
        count = None if decimals is None else Decimals(decimals)
        return cls(ladder, rule, count, currency, per_tick)


@dataclass(frozen=True)
class TickValues:
    """The tick values an axis shows."""

    values: tuple[float, ...]

    @classmethod
    def of(cls, values: Sequence[float]) -> TickValues:
        """The finite values, as floats."""
        finite = tuple(float(v) for v in values if abs(float(v)) < float("inf"))
        return cls(finite)


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
