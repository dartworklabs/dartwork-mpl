"""How an axis's ticks print a number, for text that should read alike.

A bar value label prints its value in the unit its axis's ticks use
(``1.2억``, ``31%``). The ticks slice says which scale an axis
prints in; the labels slice prints with it. This is the scale they share.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class BareZero:
    """A value that prints as zero reads ``0.0``, without sign or affixes."""


@dataclass(frozen=True)
class AffixedZero:
    """A value that prints as zero keeps currency and unit: ``$0``."""


ScaleZero: TypeAlias = BareZero | AffixedZero
"""How tick-like text prints a value that rounds to zero."""


@dataclass(frozen=True)
class TickScale:
    """How an axis's ticks print a number, for text that should read alike.

    ``prefix``, the value divided by ``factor``, ``suffix``:
    ``TickScale(1e8, "", "억")`` prints ``1.2e8`` as ``1.2억``. ``zero``: a value
    that prints as zero drops the affixes (:class:`BareZero`) or keeps them
    (:class:`AffixedZero`: ``$0``).
    """

    factor: float = 1.0
    prefix: str = ""
    suffix: str = ""
    zero: ScaleZero = BareZero()
