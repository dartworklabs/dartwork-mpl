"""What the labels are given by other slices, as typed arguments.

Label text is sized and weighted relative to the active preset, and a bar
value label prints in its axis's tick unit. Neither is the labels slice's to
know: ``compose.labels`` passes the style slice's ``fs`` / ``fw`` and the
ticks slice's number printing in these records.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from ..vocab import BareZero, ScaleZero, TickScale

if TYPE_CHECKING:
    from matplotlib.axis import Axis


@dataclass(frozen=True)
class PresetText:
    """The active preset's text: ``size(n)`` and ``weight(n)`` move its font
    size and weight by ``n`` steps (``dm.fs``, ``dm.fw``)."""

    size: Callable[[float], float]
    weight: Callable[[float], int]


class NumberText(Protocol):
    """A value printed as an axis-wide tick prints it."""

    def __call__(
        self,
        value: float,
        decimals: int,
        *,
        prefix: str = "",
        suffix: str = "",
        zero: ScaleZero = BareZero(),  # noqa: B008  (frozen, never mutated)
    ) -> str:
        """``value`` with ``decimals`` places and the scale's affixes."""
        ...


@dataclass(frozen=True)
class TickText:
    """How an axis's ticks print a number, for value labels that read alike.

    ``scale_of(axis, value)``: the scale the axis's ticks print ``value`` in,
    as of their last draw; ``decimals(values)``: one decimal count for a
    family of labels; ``number``: the printed value.
    """

    scale_of: Callable[[Axis, float], TickScale]
    decimals: Callable[[Sequence[float]], int]
    number: NumberText
