"""The size slice's types, and the one place user input becomes them.

A width is a :class:`~dartwork_mpl.length.Length`; a height is an
:class:`Aspect` (a share of the width) or a length. Everything a user may type (``"13cm"``, ``"wide"``,
``"16:9"``, ``0.6``, a list of category names) is parsed here once; the
decisions only ever see these types. A malformed input raises ``TypeError`` or
``ValueError`` with a hint an agent can act on without a second try.
"""

from __future__ import annotations

import difflib
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass

from ..length import PIXELS, Length, pixel_hint, written_length

_RATIO = re.compile(r"^\s*(?P<w>\d+(?:\.\d+)?)\s*:\s*(?P<h>\d+(?:\.\d+)?)\s*$")


def _ratio(ratio: object) -> float:
    """``ratio`` when it is a positive finite number; else ``ValueError``."""
    if isinstance(ratio, bool):
        raise ValueError(
            "aspect must be a positive number; bool is not accepted "
            "(use a token like 'standard' or a float like 0.5)"
        )
    if not isinstance(ratio, int | float):
        raise ValueError(
            f"aspect must be str, int, or float (got {type(ratio).__name__})"
        )
    if not math.isfinite(ratio) or ratio <= 0:
        raise ValueError(
            f"aspect must be positive and finite (got {float(ratio)})"
        )
    return ratio


@dataclass(frozen=True)
class Aspect:
    """A figure's height as a share of its width (``height / width``)."""

    ratio: float

    def __post_init__(self) -> None:
        """Reject a ratio that is not positive and finite."""
        _ratio(self.ratio)  # unchecked callers pass anything

    @classmethod
    def parse(cls, value: object) -> Aspect:
        """A token (``"wide"``), a ``"W:H"`` string (``"16:9"``) or a number."""
        if isinstance(value, Aspect):
            return value
        if not isinstance(value, str):
            return cls(_ratio(value))
        key = _unquote(value).lower()
        if key in ASPECTS:
            return ASPECTS[key]
        ratio = _RATIO.match(key)
        if ratio is None:
            raise ValueError(
                f"unknown aspect token {value!r}; known: {sorted(ASPECTS)}."
                f"{_aspect_hint(value)}"
            )
        width, height = float(ratio.group("w")), float(ratio.group("h"))
        if width <= 0 or height <= 0 or not math.isfinite(height / width):
            raise ValueError(
                f"aspect ratio {value!r} needs two positive numbers as "
                f"'width:height', e.g. '16:9' or '4:3'."
            )
        return cls(height / width)


# Named aspects, height / width. Keep a new one at least 5 % from the others.
ASPECTS: Mapping[str, Aspect] = {
    "square": Aspect(1.0),  # 1:1, symmetric scatter
    "portrait": Aspect(5.0 / 4.0),  # 4:5 portrait
    "tall": Aspect(3.0 / 2.0),  # 2:3 portrait, mobile reading
    "standard": Aspect(3.0 / 4.0),  # 4:3, paper figures (the default)
    "golden": Aspect(1.0 / 1.618),  # 1:phi
    "wide": Aspect(2.0 / 3.0),  # 3:2
    "a4": Aspect(1.0 / 1.4142),  # 1:sqrt 2, ISO 216
    "slide": Aspect(9.0 / 16.0),  # 16:9
    "cinema": Aspect(1.0 / 2.0),  # 2:1, wide hero figures
    "panoramic": Aspect(1.0 / 3.0),  # 3:1, banners and sparklines
}
STANDARD = ASPECTS["standard"]


def _unquote(text: str) -> str:
    return text.strip().strip('"').strip("'")


def _aspect_hint(value: str) -> str:
    """A "did you mean" sentence for an aspect string that did not parse."""
    unit = re.fullmatch(r"\s*[\d.]+\s*([A-Za-z]+)\s*", value)
    if unit is not None and unit.group(1).lower() in PIXELS:
        return pixel_hint(value)
    if ":" in value:
        return " Write a ratio as 'width:height', e.g. '16:9' or '4:3'."
    try:
        number = float(value)
    except ValueError:
        number = math.nan
    if math.isfinite(number) and number > 0:
        return f" To pass a numeric ratio, drop the quotes: aspect={number}."
    close = difflib.get_close_matches(
        value.strip().lower(), list(ASPECTS), n=1, cutoff=0.5
    )
    return f" Did you mean {close[0]!r}?" if close else ""


def parse_height(value: object) -> Aspect | Length:
    """The second ``figsize`` argument: an aspect, or a height with a unit."""
    if isinstance(value, Length | Aspect):
        return value
    if (
        isinstance(value, str)
        and _unquote(value).lower() not in ASPECTS
        and written_length(value)
    ):
        return Length.parse(value, "height")
    return Aspect.parse(value)


@dataclass(frozen=True)
class FigureSize:
    """A figure's width and height."""

    width: Length
    height: Length

    @property
    def inches(self) -> tuple[float, float]:
        """``(width, height)`` in inches, as matplotlib's ``figsize`` wants."""
        return (self.width.inch, self.height.inch)


def count(name: str, value: object, minimum: int) -> int:
    """``value`` as an int of at least ``minimum``, naming ``name`` if not."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


@dataclass(frozen=True)
class Panels:
    """How many small-multiple panels a figure holds (at least one)."""

    n: int

    def __post_init__(self) -> None:
        """Reject a count that is not an int of at least one."""
        count("n", self.n, 1)


@dataclass(frozen=True)
class Grid:
    """Panel rows and columns, each at least one."""

    nrows: int = 1
    ncols: int = 1

    def __post_init__(self) -> None:
        """Reject a count that is not an int of at least one."""
        count("nrows", self.nrows, 1)
        count("ncols", self.ncols, 1)

    @property
    def single(self) -> bool:
        """Whether the figure is one panel."""
        return self.nrows * self.ncols == 1
