"""The size slice's types, and the one place user input becomes them.

A width is a :class:`Length`, never a bare number: matplotlib's ``figsize`` is
in inches while people think in centimetres, so a number without a unit has no
safe reading. A height is an :class:`Aspect` (a share of the width) or a
:class:`Length`. Everything a user may type (``"13cm"``, ``"wide"``,
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

CM_PER_INCH = 2.54
MM_PER_INCH = 25.4
PT_PER_INCH = 72.0  # PostScript point: matplotlib's font and line unit

UNITS: Mapping[str, float] = {
    "cm": CM_PER_INCH,
    "in": 1.0,
    "mm": MM_PER_INCH,
    "pt": PT_PER_INCH,
}
# Spellings agents write for the canonical units.
SYNONYMS: Mapping[str, str] = {
    **dict.fromkeys(("centi", "centimeter", "centimeters", "cms"), "cm"),
    **dict.fromkeys(("inch", "inches"), "in"),
    **dict.fromkeys(("milli", "millimeter", "millimeters", "mms"), "mm"),
    **dict.fromkeys(("point", "points", "pts"), "pt"),
}
PIXELS = frozenset({"px", "pixel", "pixels"})

_NUMBER_UNIT = re.compile(
    r"^\s*(?P<value>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(?P<unit>cm|in|mm|pt)?\s*$",
    re.IGNORECASE,
)
_RATIO = re.compile(r"^\s*(?P<w>\d+(?:\.\d+)?)\s*:\s*(?P<h>\d+(?:\.\d+)?)\s*$")


def _positive(value: object, what: str) -> float:
    """``value`` as a positive finite float; ``TypeError`` for a non-number."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(
            f"{what} value must be int or float (got {type(value).__name__})"
        )
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{what} must be positive and finite (got {number})")
    return number


def _unquote(text: str) -> str:
    return text.strip().strip('"').strip("'")


@dataclass(frozen=True, kw_only=True, order=True)
class Length:
    """A positive physical length, stored in inches.

    Not a ``float``: handing one to matplotlib would silently pick a unit, so
    crossing out of dartwork-mpl always names it (``.inch``, ``.cm``,
    ``.mm``, ``.pt``). Build one with :func:`cm` / :func:`inch` / :func:`mm` /
    :func:`pt` or parse a unit string with :meth:`parse`.
    """

    inch: float

    def __post_init__(self) -> None:
        """Reject a non-number and a length that is not positive and finite."""
        _positive(self.inch, "length")

    @property
    def cm(self) -> float:
        """The length in centimetres."""
        return self.inch * CM_PER_INCH

    @property
    def mm(self) -> float:
        """The length in millimetres."""
        return self.inch * MM_PER_INCH

    @property
    def pt(self) -> float:
        """The length in PostScript points (1/72 in)."""
        return self.inch * PT_PER_INCH

    @classmethod
    def parse(cls, value: object, what: str = "width") -> Length:
        """A :class:`Length`, or a unit string such as ``"13cm"`` / ``"5in"``.

        A bare number raises ``TypeError`` (it carries no unit); a string
        without a known unit raises ``ValueError`` with a correction.
        """
        if isinstance(value, Length):
            return value
        if isinstance(value, bool | int | float):
            raise TypeError(
                f"{what} must be a unit string like '13cm' / '5in' / '170mm' "
                f"or a Length value (dm.cm(13), dm.col1). Got "
                f"{type(value).__name__} {value!r} — bare numbers carry no "
                f"unit. For 13 cm write '13cm' or dm.cm(13); for 13 inches "
                f"write '13in' or dm.inch(13)."
            )
        if not isinstance(value, str):
            raise TypeError(
                f"{what} must be a unit string or a Length value "
                f"(got {type(value).__name__})"
            )
        text = _unquote(value)
        match = _NUMBER_UNIT.match(text)
        if match is None:
            raise ValueError(
                f"could not parse length {value!r}; expected '<number>' with "
                f"optional unit suffix (cm, in, mm, pt).{_unit_hint(text)}"
            )
        number, unit = match.group("value"), match.group("unit")
        if unit is None:
            raise ValueError(
                f"length {value!r} has no unit; add a unit suffix (e.g. "
                f"'{number}cm', '{number}in', '{number}mm', '{number}pt') "
                f"or use dm.cm(...) / dm.inch(...)."
            )
        return cls(
            inch=_positive(float(number), "length") / UNITS[unit.lower()]
        )


def cm(value: float) -> Length:
    """A :class:`Length` of ``value`` centimetres."""
    return Length(inch=_positive(value, "length") / CM_PER_INCH)


def inch(value: float) -> Length:
    """A :class:`Length` of ``value`` inches."""
    return Length(inch=_positive(value, "length"))


def mm(value: float) -> Length:
    """A :class:`Length` of ``value`` millimetres."""
    return Length(inch=_positive(value, "length") / MM_PER_INCH)


def pt(value: float) -> Length:
    """A :class:`Length` of ``value`` PostScript points."""
    return Length(inch=_positive(value, "length") / PT_PER_INCH)


#: Academic single- and double-column figure widths.
col1: Length = cm(9)
col2: Length = cm(17)


def _pixel_hint(text: str) -> str:
    number = re.sub(r"[A-Za-z\s]", "", text) or "<n>"
    return (
        f" 'px' has no physical size until a DPI is chosen "
        f"(inches = pixels / DPI). Give a physical length such as '13cm', "
        f"or convert it yourself: {number} px at 200 DPI is "
        f"dm.inch({number} / 200), saved with dm.save_formats(..., dpi=200)."
    )


def _unit_hint(text: str) -> str:
    """A "did you mean" sentence for a length string that did not parse."""
    letters = re.search(r"[A-Za-z]+", text)
    if letters is None:
        return " Use '<number>cm', '<number>in', or '<number>mm'."
    word = letters.group(0).lower()
    if word in PIXELS:
        return _pixel_hint(text)
    close = difflib.get_close_matches(word, list(UNITS), n=1, cutoff=0.4)
    unit = SYNONYMS.get(word) or (close[0] if close else None)
    if unit is None:
        return (
            f" Supported units are {list(UNITS)} "
            f"(got unit-like fragment {word!r})."
        )
    number = re.sub(r"[A-Za-z]", "", text).strip() or "<number>"
    return f" Did you mean {unit!r}-style, e.g. '{number}{unit}'?"


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


def _aspect_hint(value: str) -> str:
    """A "did you mean" sentence for an aspect string that did not parse."""
    unit = re.fullmatch(r"\s*[\d.]+\s*([A-Za-z]+)\s*", value)
    if unit is not None and unit.group(1).lower() in PIXELS:
        return _pixel_hint(value)
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
    if isinstance(value, str):
        match = _NUMBER_UNIT.match(_unquote(value))
        if _unquote(value).lower() not in ASPECTS and match and match["unit"]:
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
