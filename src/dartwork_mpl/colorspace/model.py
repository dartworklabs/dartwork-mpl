"""Colour spaces: encoded sRGB, OKLab, OKLCH, and the exact arithmetic between them;
WCAG contrast and the facts and plans of a contrast lift.

A colour is held as OKLab coordinates (:class:`Color`) and rendered to
encoded sRGB (:class:`Rgb`) by reducing chroma at fixed lightness and hue
until it fits the gamut. This is the shipped arithmetic: the multiply/add
order of every kernel is part of what makes ``dm.cspace`` and ``dm.oklch``
return the same hex on every machine, so do not "simplify" it.
"""

from __future__ import annotations

import colorsys
import math
import re
from dataclasses import dataclass
from typing import NewType, TypeVar

import numpy as np

T = TypeVar("T")

# An encoded ``#rrggbb`` string, as shipped in the colour tables.
Hex = NewType("Hex", str)

_GAMUT_STEPS = 24
_GAMUT_TOLERANCE = 1e-6
# D65 sRGB -> CIE Y, unrounded; WCAG's rounded weights are in ``wcag_luminance``.
_SRGB_Y = (0.21267287873271212, 0.7151521284847872, 0.07217499278250072)


def finite(value: object, what: str) -> float:
    """``value`` as a finite float; ``TypeError`` for a non-number."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{what} must be a number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{what}={value!r} must be a finite number")
    return number


def _to_linear(channel: float) -> float:
    if channel <= 0.04045:
        return channel / 12.92
    return float(((channel + 0.055) / 1.055) ** 2.4)


def _to_encoded(channel: float) -> float:
    if channel <= 0.0031308:
        return 12.92 * channel
    return float(1.055 * channel ** (1.0 / 2.4) - 0.055)


@dataclass(frozen=True)
class Rgb:
    """Encoded sRGB channels, nominally in ``[0, 1]``."""

    r: float
    g: float
    b: float

    @classmethod
    def of(cls, channels: tuple[float, ...]) -> Rgb:
        """The first three channels of an RGB or RGBA tuple."""
        return cls(float(channels[0]), float(channels[1]), float(channels[2]))

    @classmethod
    def from_hex(cls, text: str) -> Rgb:
        """``#rgb`` or ``#rrggbb`` (the ``#`` optional)."""
        clean = text.strip().removeprefix("#")
        if not re.fullmatch(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}", clean):
            raise ValueError(f"Invalid hex color format: {text}")
        if len(clean) == 3:
            clean = "".join(ch * 2 for ch in clean)
        r, g, b = (int(clean[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
        return cls(r, g, b)

    @property
    def channels(self) -> tuple[float, float, float]:
        """``(r, g, b)``."""
        return (self.r, self.g, self.b)

    def hex(self) -> Hex:
        """``#rrggbb``, each channel clamped to ``[0, 1]`` and rounded."""
        for value in self.channels:
            if not math.isfinite(value):
                raise ValueError(f"RGB channels must be finite, got {self}")
        r, g, b = (round(max(0.0, min(1.0, v)) * 255) for v in self.channels)
        return Hex(f"#{r:02x}{g:02x}{b:02x}")

    def linear(self) -> tuple[float, float, float]:
        """The channels in linear light."""
        r, g, b = self.channels
        return (_to_linear(r), _to_linear(g), _to_linear(b))

    def oklab(self) -> Oklab:
        """The same colour in OKLab."""
        r, g, b = self.linear()
        lms_l = float(
            np.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
        )
        lms_m = float(
            np.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
        )
        lms_s = float(
            np.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
        )
        return Oklab(
            0.2104542553 * lms_l + 0.7936177850 * lms_m - 0.0040720468 * lms_s,
            1.9779984951 * lms_l - 2.4285922050 * lms_m + 0.4505937099 * lms_s,
            0.0259040371 * lms_l + 0.7827717662 * lms_m - 0.8086757660 * lms_s,
        )

    def wcag_luminance(self) -> float:
        """WCAG 2.x relative luminance, with its rounded weights."""
        r, g, b = self.linear()
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def relative_y(self) -> float:
        """Modeled relative CIE Y of nominal D65 sRGB (white is 1.0)."""
        r, g, b = self.linear()
        return float(_SRGB_Y[0] * r + _SRGB_Y[1] * g + _SRGB_Y[2] * b)


@dataclass(frozen=True)
class Rgba:
    """An sRGB colour with an alpha, as painted over what is below it."""

    rgb: Rgb
    alpha: float

    @classmethod
    def of(cls, channels: tuple[float, ...]) -> Rgba:
        """An RGBA tuple."""
        return cls(Rgb.of(channels), float(channels[3]))


def _linear_from_oklab(
    L: float, a: float, b: float
) -> tuple[float, float, float]:
    lms_l = L + 0.3963377774 * a + 0.2158037573 * b
    lms_m = L - 0.1055613458 * a - 0.0638541728 * b
    lms_s = L - 0.0894841775 * a - 1.2914855480 * b
    lms_l, lms_m, lms_s = (
        lms_l * lms_l * lms_l,
        lms_m * lms_m * lms_m,
        lms_s * lms_s * lms_s,
    )
    return (
        +4.0767416621 * lms_l - 3.3077115913 * lms_m + 0.2309699292 * lms_s,
        -1.2684380046 * lms_l + 2.6097574011 * lms_m - 0.3413193965 * lms_s,
        -0.0041960863 * lms_l - 0.7034186147 * lms_m + 1.7076147010 * lms_s,
    )


def _in_gamut(linear: tuple[float, float, float]) -> bool:
    return all(-_GAMUT_TOLERANCE <= v <= 1.0 + _GAMUT_TOLERANCE for v in linear)


def _encode(linear: tuple[float, float, float]) -> Rgb:
    r, g, b = (_to_encoded(max(0.0, min(1.0, v))) for v in linear)
    return Rgb(r, g, b)


@dataclass(frozen=True)
class Oklab:
    """OKLab coordinates: lightness ``L`` and the opponent axes ``a``, ``b``."""

    L: float
    a: float
    b: float

    def __post_init__(self) -> None:
        """Hold each coordinate as a finite float."""
        object.__setattr__(self, "L", finite(self.L, "OKLab L"))
        object.__setattr__(self, "a", finite(self.a, "OKLab a"))
        object.__setattr__(self, "b", finite(self.b, "OKLab b"))

    def rgb(self) -> Rgb:
        """Encoded sRGB; out of gamut, chroma is bisected at fixed L and h."""
        linear = _linear_from_oklab(self.L, self.a, self.b)
        if _in_gamut(linear):
            return _encode(linear)
        chroma, hue = (
            math.sqrt(self.a * self.a + self.b * self.b),
            math.atan2(self.b, self.a),
        )
        lower, upper = 0.0, chroma
        for _ in range(_GAMUT_STEPS):
            middle = (lower + upper) / 2.0
            probe = _linear_from_oklab(
                self.L, middle * math.cos(hue), middle * math.sin(hue)
            )
            if _in_gamut(probe):
                lower = middle
            else:
                upper = middle
        return _encode(
            _linear_from_oklab(
                self.L, lower * math.cos(hue), lower * math.sin(hue)
            )
        )

    def lch(self) -> Oklch:
        """The same colour in OKLCH, hue in ``[0, 360)``."""
        hue = math.degrees(math.atan2(self.b, self.a)) % 360.0
        return Oklch(self.L, math.sqrt(self.a * self.a + self.b * self.b), hue)


@dataclass(frozen=True)
class Oklch:
    """OKLCH coordinates: lightness, chroma and hue in degrees."""

    L: float
    C: float
    h: float

    def __post_init__(self) -> None:
        """Reject a negative or non-finite chroma."""
        if finite(self.C, "OKLCH C") < 0:
            raise ValueError(f"OKLCH C={self.C!r} must be >= 0")

    def lab(self) -> Oklab:
        """The same colour in OKLab."""
        hue = math.radians(self.h)
        return Oklab(self.L, self.C * math.cos(hue), self.C * math.sin(hue))


@dataclass(frozen=True)
class Color:
    """One colour, held as OKLab; ``dm.color(...)`` and ``dm.cspace`` return it.

    Equal coordinates are equal colours. ``to_hex()`` is what a plotting
    call wants: ``ax.bar(x, y, color=dm.color("dc.teal4").to_hex())``.
    """

    lab: Oklab

    def to_hex(self) -> str:
        """``"#rrggbb"``, gamut-mapped."""
        return self.lab.rgb().hex()

    def to_rgb(self) -> tuple[float, float, float]:
        """sRGB channels in ``[0, 1]``, gamut-mapped."""
        return self.lab.rgb().channels

    def to_oklab(self) -> tuple[float, float, float]:
        """``(L, a, b)``."""
        return (self.lab.L, self.lab.a, self.lab.b)

    def to_oklch(self) -> tuple[float, float, float]:
        """``(L, C, h)``, hue in degrees."""
        lch = self.lab.lch()
        return (lch.L, lch.C, lch.h)

    def __repr__(self) -> str:
        """``Color(oklab=(L, a, b))`` to four places."""
        L, a, b = self.to_oklab()
        return f"Color(oklab=({L:.4f}, {a:.4f}, {b:.4f}))"


# -- contrast ------------------------------------------------------------------


@dataclass(frozen=True)
class Ratio:
    """A WCAG contrast ratio, at least 1 (1:1) and at most 21 (black on white)."""

    value: float


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
