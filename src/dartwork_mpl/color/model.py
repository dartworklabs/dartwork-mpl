"""The color slice's types, and the one place user input becomes them.

User input (``"#a1b2c3"``, ``"rgb(255, 0, 0)"``, ``"oklch(0.7, 0.15, 30)"``,
a family name, a count, a palette request) is parsed here once; the
decisions only see these types. The colour values themselves (sRGB, OKLab,
OKLCH) are in ``space``. A malformed input raises ``TypeError`` or
``ValueError``.
"""

from __future__ import annotations

import colorsys
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

from .family import Count, Family
from .space import Color, Hex, Oklab, Oklch, Rgb, finite

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


@dataclass(frozen=True)
class Ratio:
    """A WCAG contrast ratio, at least 1 (1:1) and at most 21 (black on white)."""

    value: float

    @classmethod
    def parse(cls, value: object) -> Ratio:
        """A positive finite ratio; else ``ValueError``."""
        number = real(value)
        if not math.isfinite(number) or number <= 0:
            raise ValueError("min_ratio must be a positive finite number")
        return cls(number)


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
class Locale:
    """Whose convention the semantic gain/loss colours follow.

    ``red_gains``: gains are red and losses blue (Korea's markets).
    """

    word: str
    red_gains: bool

    DEFAULT: ClassVar[Locale]
    KR: ClassVar[Locale]

    @classmethod
    def parse(cls, text: str) -> Locale:
        """``"kr"`` is Korea's convention; anything else the default."""
        return cls.KR if text == "kr" else cls.DEFAULT


Locale.DEFAULT = Locale("default", red_gains=False)
Locale.KR = Locale("kr", red_gains=True)


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


SEMANTIC_NAMES = ("dc.pos", "dc.neg", "dc.ref", "dc.hl")


@dataclass(frozen=True)
class Categorical:
    """Unordered series: distinct hues."""

    value: ClassVar[str] = "categorical"


@dataclass(frozen=True)
class Ordered:
    """Series in order: one hue, light to dark."""

    value: ClassVar[str] = "sequential"


@dataclass(frozen=True)
class TwoSided:
    """Series either side of a midpoint: two hues and a grey."""

    value: ClassVar[str] = "diverging"


#: What ``dm.make_palette`` encodes.
PaletteKind = Categorical | Ordered | TwoSided


def parse_palette_kind(text: object) -> PaletteKind:
    """A palette kind; ``ValueError`` for anything else."""
    for kind in (Categorical(), Ordered(), TwoSided()):
        if text == kind.value:
            return kind
    raise ValueError(f"Unknown kind: {text!r}")


@dataclass(frozen=True)
class PaletteRequest:
    """``n`` series of ``kind``."""

    n: int
    kind: PaletteKind

    @classmethod
    def parse(cls, n: object, kind: object) -> PaletteRequest:
        """Check ``n`` and ``kind``."""
        palette_kind = parse_palette_kind(kind)
        if not isinstance(n, int) or isinstance(n, bool):
            raise TypeError(f"n must be an int, got {type(n).__name__}")
        if n < 0:
            raise ValueError(
                "n must be non-negative; use 0 for an empty palette"
            )
        return cls(n, palette_kind)


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
class ContrastFacts:
    """A foreground that must reach ``target`` contrast on ``background``."""

    color: Rgb
    background: Rgb
    target: Ratio


@dataclass(frozen=True)
class Lift:
    """A foreground moved in HLS lightness, hue and saturation held."""

    hue: float
    lightness: float
    saturation: float
    lighten: bool

    def rgb(self) -> Rgb:
        """The moved colour in sRGB."""
        return Rgb(
            *colorsys.hls_to_rgb(self.hue, self.lightness, self.saturation)
        )


@dataclass(frozen=True)
class LightInk:
    """The light text colour reads better."""

    def pick(self, light: T, dark: T) -> T:
        """``light``."""
        return light


@dataclass(frozen=True)
class DarkInk:
    """The dark text colour reads better."""

    def pick(self, light: T, dark: T) -> T:
        """``dark``."""
        return dark


#: Which of two text colours reads better on a background.
Ink = LightInk | DarkInk


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
