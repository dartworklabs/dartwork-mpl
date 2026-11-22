"""The ticks slice's types, and the one place user input becomes them.

``format_axis_myriad`` reads its arguments into a :class:`NumberStyle`: a
:class:`Ladder` of myriad units and the :data:`UnitRule` that picks one.
At draw time the ticks in view (:class:`TickValues`) decide an
:class:`AxisText`: one :class:`Unit` and one decimal count for the axis.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import NewType, TypeAlias, assert_never

from ..vocab import DefaultLocale, KoreanLocale, Locale

Decimals = NewType("Decimals", int)
"""A count of decimal places."""

TickCount = NewType("TickCount", int)
"""A count of major ticks in view."""


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


def preset_ladder(locale: Locale) -> Ladder:
    """The units a preset of ``locale`` counts large numbers in."""
    match locale:
        case KoreanLocale():
            return MYRIAD
        case DefaultLocale():
            return SI
        case _:
            assert_never(locale)


MYRIAD_LOCALES = {
    "ko": MYRIAD,
    "zh": Ladder.of((1e4, "万"), (1e8, "亿"), (1e12, "兆"), (1e16, "京")),
    "ja": Ladder.of((1e4, "万"), (1e8, "億"), (1e12, "兆"), (1e16, "京")),
}


def myriad_ladder(locale: object) -> Ladder:
    """``format_axis_myriad``'s ``locale`` as its ladder; ``ValueError``."""
    if isinstance(locale, str) and locale in MYRIAD_LOCALES:
        return MYRIAD_LOCALES[locale]
    raise ValueError(
        f"locale must be one of 'ko', 'zh', or 'ja' (got {locale!r})"
    )


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
class EachAlone:
    """Fixed decimals under the max rule: each tick in its own unit, trailing
    zeros dropped (``1.5억``), under the first rung whole with none
    (``7,500``)."""


@dataclass(frozen=True)
class DefaultUnit:
    """The preset's numbers on an axis nobody formatted: plain below one
    million, the largest tick's unit from there unless that needs over two
    decimals."""


UnitRule: TypeAlias = MaxUnit | WholeUnit | FixedUnit | EachAlone | DefaultUnit
"""How an axis picks its unit from a ladder."""


@dataclass(frozen=True)
class NumberStyle:
    """Everything a number formatter was asked: ladder, rule and fixed parts."""

    ladder: Ladder
    rule: UnitRule = MaxUnit()
    decimals: Decimals | None = None
    currency: str = ""

    @property
    def unit(self) -> Unit | None:
        """The one unit asked, if the rule fixes it."""
        match self.rule:
            case FixedUnit(unit=unit):
                return unit
            case MaxUnit() | WholeUnit() | EachAlone() | DefaultUnit():
                return None

    @classmethod
    def parse(
        cls,
        ladder: Ladder,
        unit: str = "max",
        *,
        decimals: object = None,
        currency: str = "",
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
        count = None if decimals is None else Decimals(decimals)
        fixed = ladder.find(unit)
        rule: UnitRule
        if unit == "max":
            rule = MaxUnit() if count is None else EachAlone()
        elif unit == "whole":
            rule = WholeUnit()
        elif fixed is not None:
            rule = FixedUnit(fixed)
        else:
            raise ValueError(
                f"unit must be 'max', 'whole' or one of {ladder.labels()} "
                f"(got {unit!r})"
            )
        return cls(ladder, rule, count, currency)


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
class AxisData:
    """Where an axis's lines and points sit along it, in data units."""

    values: tuple[float, ...]

    @classmethod
    def of(cls, values: Sequence[float]) -> AxisData:
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

    ``unit`` is ``None`` when no tick is in view, ``decimals`` ``None`` when
    each tick takes its own count.
    """

    unit: Unit | None
    decimals: Decimals | None


@dataclass(frozen=True, order=True)
class Cost:
    """How a unit prints an axis: decimals, longest label, then the factor."""

    decimals: int
    longest: int
    factor: float
