"""Whose convention a figure follows where conventions differ by country.

A preset says it (the ``-kr`` presets are Korean); the colour slice reads it
for the role colours ``dc.pos`` / ``dc.neg``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeAlias


@dataclass(frozen=True)
class DefaultLocale:
    """Gains green, losses red."""

    red_gains: ClassVar[bool] = False


@dataclass(frozen=True)
class KoreanLocale:
    """Korea's markets: gains red, losses blue."""

    red_gains: ClassVar[bool] = True


Locale: TypeAlias = DefaultLocale | KoreanLocale
