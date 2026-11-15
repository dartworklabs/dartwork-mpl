"""The color slice's types, and the one place user input becomes them.

User input (``"#a1b2c3"``, ``"rgb(255, 0, 0)"``, ``"oklch(0.7, 0.15, 30)"``,
a family name, a count, a palette request) is parsed here once; the
decisions only see these types. The colour values themselves (sRGB, OKLab,
OKLCH) are in ``space``. A malformed input raises ``TypeError`` or
``ValueError``.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import (
    ClassVar,
    NamedTuple,
    NewType,
    Protocol,
    SupportsFloat,
    SupportsIndex,
    TypeVar,
    runtime_checkable,
)

from ..colorspace import Color, Hex, Oklab, Oklch, Ratio, Rgb, finite
from ..vocab import Locale
from .family import Count, Family

T = TypeVar("T")

# A matplotlib colour name (``"oc.red5"``, ``"tab:blue"``) or any text.
Name = NewType("Name", str)


def rgb_color(r: object, g: object, b: object) -> Color:
    """RGB channels as a colour: all in ``[0, 1]``, or all in ``[0, 255]``.

    When any channel exceeds 1 every channel is read as a byte, so ``0`` and
    ``1`` are byte values there; a fraction among bytes is ambiguous and
    rejected, as is anything negative or above 255.
    """
    values = [
        finite(v, f"rgb {n}") for n, v in zip("rgb", (r, g, b), strict=True)
    ]
    if any(v < 0.0 for v in values):
        raise ValueError(f"rgb channels must be non-negative, got {values}")
    if any(v > 1.0 for v in values):
        if any(v > 255.0 or 0.0 < v < 1.0 for v in values):
            raise ValueError(
                f"rgb{tuple(values)} mixes 0-1 and 0-255 channels; pass every "
                "channel in 0-1 or every channel in 0-255"
            )
        values = [v / 255.0 for v in values]
    return Color(Rgb(*values).oklab())


_FUNCTIONAL = re.compile(
    r"^(?P<func>rgb|oklch|oklab)\s*\(\s*(?P<args>.+?)\s*\)$", re.IGNORECASE
)


def parse_written(text: object) -> Color | Name:
    """A colour written out (hex or ``rgb()``/``oklch()``/``oklab()``), or
    the text back as a :data:`Name` for the registry to resolve."""
    if not isinstance(text, str):
        raise TypeError(
            f"a colour must be a str or Color, got {type(text).__name__}"
        )
    text = text.strip()
    if text.startswith("#"):
        return Color(Rgb.from_hex(text).oklab())
    match = _FUNCTIONAL.match(text)
    if match is None:
        return Name(text)
    func, raw = match.group("func").lower(), match.group("args")
    try:
        nums = [float(part.strip()) for part in raw.split(",")]
    except ValueError as exc:
        raise ValueError(
            f"{func}(...) arguments must be numeric: {raw!r}"
        ) from exc
    if len(nums) != 3:
        raise ValueError(
            f"{func}(...) expects 3 arguments, got {len(nums)}: {raw!r}"
        )
    if func == "rgb":
        return rgb_color(*nums)
    if func == "oklch":
        return Color(Oklch(*nums).lab())
    return Color(Oklab(*nums))


@runtime_checkable
class Items(Protocol):
    """A value read for its items, in order (a list, a tuple, an array)."""

    def __iter__(self) -> Iterator[object]:
        """The items."""
        ...


def real(value: object) -> float:
    """``value`` as ``float()`` reads it; ``TypeError`` for what it cannot."""
    if isinstance(value, str | SupportsFloat | SupportsIndex):
        return float(value)
    raise TypeError(
        "float() argument must be a string or a real number, "
        f"not {type(value).__name__!r}"
    )


def parse_ratio(value: object) -> Ratio:
    """A positive finite contrast ratio; else ``ValueError``."""
    number = real(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("min_ratio must be a positive finite number")
    return Ratio(number)


@dataclass(frozen=True)
class Weight:
    """The share of the first colour in a mix, in ``[0, 1]``."""

    value: float

    @classmethod
    def parse(cls, value: object) -> Weight:
        """A share in ``[0, 1]``; else ``ValueError``."""
        number = real(value)
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            raise ValueError(
                f"alpha must be a finite number in [0, 1], got {value!r}"
            )
        return cls(number)


@dataclass(frozen=True)
class Steps:
    """How many colours a gradient has, ends included."""

    n: int


@dataclass(frozen=True)
class InOklch:
    """A gradient through OKLCH, the hue the short way round (the default)."""

    value: ClassVar[str] = "oklch"


@dataclass(frozen=True)
class InOklab:
    """A gradient along the straight OKLab line."""

    value: ClassVar[str] = "oklab"


@dataclass(frozen=True)
class InRgb:
    """A gradient along the straight sRGB line."""

    value: ClassVar[str] = "rgb"


#: Where a gradient interpolates.
Space = InOklch | InOklab | InRgb


def parse_space(text: object) -> Space:
    """A space name; ``ValueError`` for anything else."""
    for space in (InOklch(), InOklab(), InRgb()):
        if text == space.value:
            return space
    raise ValueError(
        f"Unsupported color space: {text}. Must be 'oklch', 'oklab', or 'rgb'"
    )


@dataclass(frozen=True)
class Semantic:
    """The four role colours: gain, loss, reference, highlight."""

    pos: Hex
    neg: Hex
    ref: Hex
    hl: Hex

    def names(self) -> dict[str, Hex]:
        """The tokens as matplotlib colour names."""
        return {
            "dc.pos": self.pos,
            "dc.neg": self.neg,
            "dc.ref": self.ref,
            "dc.hl": self.hl,
        }


@dataclass(frozen=True)
class Lookup:
    """A colour name to correct, and every registered name."""

    name: Name
    registry: tuple[Name, ...]


@dataclass(frozen=True)
class Suggestions:
    """Registered names close to a rejected one, nearest first."""

    names: tuple[Name, ...]


class Library(NamedTuple):
    """One bundled colour library: ``(key, prefix, source, label)``."""

    key: str
    prefix: str
    source: str
    label: str


@dataclass(frozen=True)
class Catalog:
    """Every shipped colour: libraries, ``dc.*`` families and named values."""

    libraries: tuple[Library, ...]
    families: Mapping[str, Family]
    named: Mapping[str, Hex]

    def ladder(self, name: str) -> tuple[Hex, ...]:
        """The 10-step ladder of the sequential family ``name``."""
        return self.families[name].stops


@dataclass(frozen=True)
class DivergingSource:
    """What a diverging family's canonical row is built from."""

    low: tuple[Hex, ...]
    high: tuple[Hex, ...]
    curated: tuple[Hex, ...] | None


@dataclass(frozen=True)
class Gradient:
    """The two OKLCH ends a gradient runs between."""

    start: Oklch
    end: Oklch


@dataclass(frozen=True)
class Form:
    """A request for ``family``'s designed ``n``-colour form."""

    family: Family
    n: Count


@dataclass(frozen=True)
class SemanticFacts:
    """The locale the role colours are for, and the ladders they come from."""

    locale: Locale
    catalog: Catalog


Row = tuple[Hex, ...]


def paired(name: str) -> bool:
    """A diverging colormap's name: two ladders, ``low_high``."""
    return "_" in name
