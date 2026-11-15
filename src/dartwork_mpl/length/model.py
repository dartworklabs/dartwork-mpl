"""A physical length and its units: what ``"13cm"`` and ``dm.mm(2)`` mean.

A length is a :class:`Length`, never a bare number: matplotlib's ``figsize``
is in inches while people think in centimetres, so a number without a unit
has no safe reading. A unit string (``"13cm"``, ``"5in"``, ``"170mm"``,
``"24pt"``) is parsed here once; a malformed one raises ``TypeError`` or
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


def pixel_hint(text: str) -> str:
    """Why a pixel size has no length, and how to give one instead."""
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
        return pixel_hint(text)
    close = difflib.get_close_matches(word, list(UNITS), n=1, cutoff=0.4)
    unit = SYNONYMS.get(word) or (close[0] if close else None)
    if unit is None:
        return (
            f" Supported units are {list(UNITS)} "
            f"(got unit-like fragment {word!r})."
        )
    number = re.sub(r"[A-Za-z]", "", text).strip() or "<number>"
    return f" Did you mean {unit!r}-style, e.g. '{number}{unit}'?"


def written_length(text: str) -> bool:
    """Whether ``text`` is a number with a unit (``"8cm"``), not a token."""
    match = _NUMBER_UNIT.match(_unquote(text))
    return match is not None and match["unit"] is not None
