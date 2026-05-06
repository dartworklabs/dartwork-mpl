"""Free-form length and aspect parsing helpers.

dartwork-mpl 0.4+ accepts user-supplied widths in physical units
(cm/in/mm/pt) rather than fixed tokens. This module is the parser
that converts those inputs into a :class:`Length` value matplotlib's
``figsize=`` (and friends) can ultimately consume.

It also resolves named aspect tokens (square/portrait/standard/
golden/wide/cinema) into a height/width ratio.
"""

from __future__ import annotations

__all__ = [
    "ASPECT_TOKENS",
    "DEFAULT_ASPECT",
    "Length",
    "cm",
    "figsize",
    "inch",
    "length",
    "mm",
    "parse_aspect",
    "parse_width",
    "pt",
]

import difflib
import math
import re

CM_PER_INCH: float = 2.54
MM_PER_INCH: float = 25.4
PT_PER_INCH: float = 72.0  # PostScript point — matplotlib font/linewidth unit.

_KNOWN_WIDTH_UNITS: tuple[str, ...] = ("cm", "in", "mm", "pt")

# Common spellings AI agents emit when they meant the canonical short
# form. Looked up before the difflib fallback so that obvious synonyms
# resolve regardless of edit distance.
_WIDTH_UNIT_SYNONYMS: dict[str, str] = {
    "centi": "cm",
    "centimeter": "cm",
    "centimeters": "cm",
    "cms": "cm",
    "inch": "in",
    "inches": "in",
    "milli": "mm",
    "millimeter": "mm",
    "millimeters": "mm",
    "mms": "mm",
    "point": "pt",
    "points": "pt",
    "pts": "pt",
}

# Named aspect tokens: ratio = height / width.
ASPECT_TOKENS: dict[str, float] = {
    "square": 1.0,
    "portrait": 5.0 / 4.0,
    "standard": 3.0 / 4.0,
    "golden": 1.0 / 1.618,
    "wide": 2.0 / 3.0,
    "cinema": 1.0 / 2.0,
}

DEFAULT_ASPECT: str = "standard"

_WIDTH_RE = re.compile(
    r"""
    ^\s*
    (?P<value>[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
    \s*
    (?P<unit>cm|in|mm|pt)?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


class Length:
    """Physical length with multi-unit views.

    Mirrors the :class:`~dartwork_mpl.color.Color` design: an opaque
    wrapper with a single canonical store (inches) and per-unit
    property views (``length.cm``, ``length.mm``, ``length.inch``,
    ``length.pt``). Deliberately **not** a ``float`` subclass —
    passing a :class:`Length` directly to a matplotlib API would
    silently mis-interpret the unit at non-inch boundaries
    (``fontsize=`` / ``linewidth=`` are pt; transform offsets are
    px), so callers must always pick a unit explicitly when crossing
    out of dartwork-mpl. For figsize specifically, use
    :func:`dartwork_mpl.figsize` (the recommended idiom) or the
    explicit ``length.inch`` view.

    DPI-dependent units (``px``) are not exposed on the class itself
    — a caller that needs pixels can write ``length.inch * fig.dpi``
    and keep the dependency explicit at the call site.

    Parameters
    ----------
    value : str | Length
        Either a parseable unit string (``"13cm"``, ``"5in"``,
        ``"170mm"``, ``"24pt"``) or another :class:`Length`. Bare
        ``int``/``float`` are rejected — they carry no unit and the
        cm/inch ambiguity is exactly the bug this class exists to
        prevent. Use :meth:`from_cm` / :meth:`from_inch` /
        :meth:`from_mm` / :meth:`from_pt` (or the top-level wrappers
        :func:`cm` / :func:`inch` / :func:`mm` / :func:`pt`) for
        already-typed numeric input.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> w = dm.Length("13cm")
    >>> w.cm, w.mm, w.inch, w.pt
    (13.0, 130.0, 5.118110236220472, 368.5039370078739)
    >>> # Crossing into matplotlib — pick the unit explicitly:
    >>> import matplotlib.pyplot as plt
    >>> fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
    >>> ax.set_xlabel("x", fontsize=dm.pt(10).pt)
    """

    __slots__ = ("_inch",)

    def __init__(self, value: str | Length) -> None:
        if isinstance(value, Length):
            self._inch: float = value._inch
            return
        if isinstance(value, (bool, int, float)):
            # ``bool`` is an ``int`` subclass; trap before the numeric
            # branch so ``Length(True)`` and ``Length(1)`` produce the
            # same TypeError.
            raise TypeError(
                f"Length(value) requires a unit string like '13cm' / "
                f"'5in' / '170mm' / '24pt' or another Length. Got "
                f"{type(value).__name__} {value!r} — bare numbers carry "
                f"no unit. For 13 cm write Length('13cm') or dm.cm(13); "
                f"for 13 inches write Length('13in') or dm.inch(13)."
            )
        if not isinstance(value, str):
            raise TypeError(
                f"Length(value) accepts str or Length (got "
                f"{type(value).__name__})"
            )
        self._inch = _parse_unit_string(value)

    # ------------------------------------------------------------------ #
    # Constructors                                                        #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_cm(cls, value: float) -> Length:
        """Construct from centimeters."""
        return cls._from_inch(_validate_positive(value) / CM_PER_INCH)

    @classmethod
    def from_mm(cls, value: float) -> Length:
        """Construct from millimeters."""
        return cls._from_inch(_validate_positive(value) / MM_PER_INCH)

    @classmethod
    def from_inch(cls, value: float) -> Length:
        """Construct from inches."""
        return cls._from_inch(_validate_positive(value))

    @classmethod
    def from_pt(cls, value: float) -> Length:
        """Construct from PostScript points (1 pt = 1/72 in)."""
        return cls._from_inch(_validate_positive(value) / PT_PER_INCH)

    @classmethod
    def _from_inch(cls, inch_value: float) -> Length:
        # Internal fast-path that skips str-parsing in __init__.
        obj = cls.__new__(cls)
        obj._inch = float(inch_value)
        return obj

    # ------------------------------------------------------------------ #
    # Unit views                                                          #
    # ------------------------------------------------------------------ #

    @property
    def cm(self) -> float:
        """Length expressed in centimeters."""
        return self._inch * CM_PER_INCH

    @property
    def mm(self) -> float:
        """Length expressed in millimeters."""
        return self._inch * MM_PER_INCH

    @property
    def inch(self) -> float:
        """Length expressed in inches (the canonical internal unit)."""
        return self._inch

    @property
    def pt(self) -> float:
        """Length expressed in PostScript points (1 pt = 1/72 in)."""
        return self._inch * PT_PER_INCH

    # ------------------------------------------------------------------ #
    # Arithmetic — preserve the Length tag for Length operands; reject   #
    # bare scalars at every binary op so callers must always pick a     #
    # unit explicitly when leaving dartwork-mpl. The cm/inch guard      #
    # the class exists for sits at every boundary, not just the parser. #
    # ------------------------------------------------------------------ #

    def __add__(self, other: Length) -> Length:
        if not isinstance(other, Length):
            return NotImplemented
        return Length._from_inch(self._inch + other._inch)

    def __radd__(self, other: Length) -> Length:
        if not isinstance(other, Length):
            return NotImplemented
        return Length._from_inch(other._inch + self._inch)

    def __sub__(self, other: Length) -> Length:
        if not isinstance(other, Length):
            return NotImplemented
        return Length._from_inch(self._inch - other._inch)

    def __rsub__(self, other: Length) -> Length:
        if not isinstance(other, Length):
            return NotImplemented
        return Length._from_inch(other._inch - self._inch)

    def __mul__(self, other: float) -> Length:
        # ``Length * Length`` (area) has no representation here.
        # ``bool`` is an ``int`` subclass — reject before the numeric
        # branch so ``cm(9) * True`` doesn't silently scale by 1.
        if isinstance(other, Length):
            return NotImplemented
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            return NotImplemented
        return Length._from_inch(self._inch * float(other))

    def __rmul__(self, other: float) -> Length:
        return self.__mul__(other)

    def __truediv__(self, other: float | Length) -> Length | float:
        if isinstance(other, Length):
            # Ratio of two lengths — dimensionless float.
            return self._inch / other._inch
        if isinstance(other, bool) or not isinstance(other, (int, float)):
            return NotImplemented
        return Length._from_inch(self._inch / float(other))

    def __neg__(self) -> Length:
        return Length._from_inch(-self._inch)

    def __abs__(self) -> Length:
        return Length._from_inch(abs(self._inch))

    # ------------------------------------------------------------------ #
    # Comparison & hashing                                                #
    # ------------------------------------------------------------------ #

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Length):
            return self._inch == other._inch
        return NotImplemented

    def __lt__(self, other: Length) -> bool:
        if not isinstance(other, Length):
            return NotImplemented
        return self._inch < other._inch

    def __le__(self, other: Length) -> bool:
        if not isinstance(other, Length):
            return NotImplemented
        return self._inch <= other._inch

    def __gt__(self, other: Length) -> bool:
        if not isinstance(other, Length):
            return NotImplemented
        return self._inch > other._inch

    def __ge__(self, other: Length) -> bool:
        if not isinstance(other, Length):
            return NotImplemented
        return self._inch >= other._inch

    def __hash__(self) -> int:
        return hash((Length, self._inch))

    def __repr__(self) -> str:
        # Show cm at sub-decimeter scales, otherwise prefer inches —
        # matches how users typically thought about the value at input.
        if self._inch < 1.0:
            return f"Length({self.cm:.4f}cm)"
        return f"Length({self._inch:.4f}in)"


# ---------------------------------------------------------------------- #
# Internal helpers                                                        #
# ---------------------------------------------------------------------- #


def _validate_positive(value: float) -> float:
    """Reject non-finite or non-positive numeric input with a clear message."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(
            f"length value must be int or float (got {type(value).__name__})"
        )
    v = float(value)
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"length must be positive and finite (got {v})")
    return v


def _parse_unit_string(value: str) -> float:
    """Parse a unit string like ``"13cm"`` into inches."""
    text = value.strip().strip('"').strip("'")
    match = _WIDTH_RE.match(text)
    if match is None:
        raise ValueError(
            f"could not parse length {value!r}; expected '<number>' "
            f"with optional unit suffix (cm, in, mm, pt)."
            f"{_suggest_width_correction(text)}"
        )

    number = float(match.group("value"))
    unit = (match.group("unit") or "cm").lower()
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"length must be positive and finite (got {number})")

    if unit == "cm":
        return number / CM_PER_INCH
    if unit == "in":
        return number
    if unit == "mm":
        return number / MM_PER_INCH
    return number / PT_PER_INCH  # pt


# ---------------------------------------------------------------------- #
# Top-level wrappers (mirror the Color module's oklab/oklch/rgb/hex)     #
# ---------------------------------------------------------------------- #


def cm(value: float) -> Length:
    """Construct a :class:`Length` from centimeters."""
    return Length.from_cm(value)


def inch(value: float) -> Length:
    """Construct a :class:`Length` from inches."""
    return Length.from_inch(value)


def mm(value: float) -> Length:
    """Construct a :class:`Length` from millimeters."""
    return Length.from_mm(value)


def pt(value: float) -> Length:
    """Construct a :class:`Length` from PostScript points."""
    return Length.from_pt(value)


def length(value: str | Length) -> Length:
    """Parse a unit string (or pass through a Length) into :class:`Length`.

    The string-parser counterpart to :func:`cm` / :func:`inch` /
    :func:`mm` / :func:`pt`. Mirrors :func:`dartwork_mpl.color.hex`.
    """
    return Length(value)


# ---------------------------------------------------------------------- #
# Width / aspect / figsize parsers                                        #
# ---------------------------------------------------------------------- #


def _suggest_width_correction(text: str) -> str:
    """Build a one-sentence "did you mean" suffix for a malformed width.

    The goal is that an AI agent reading the ``ValueError.message`` can
    infer the corrected call without a second probing call. Returns
    either a leading-space-prefixed suggestion or an empty string.
    """
    letters = re.search(r"[A-Za-z]+", text)
    if letters is not None:
        unit_word = letters.group(0).lower()
        canonical = _WIDTH_UNIT_SYNONYMS.get(unit_word)
        if canonical is None:
            close = difflib.get_close_matches(
                unit_word, _KNOWN_WIDTH_UNITS, n=1, cutoff=0.4
            )
            canonical = close[0] if close else None
        if canonical is not None:
            number = re.sub(r"[A-Za-z]", "", text).strip() or "<number>"
            return f" Did you mean {canonical!r}-style, e.g. '{number}{canonical}'?"
        return (
            f" Supported units are {list(_KNOWN_WIDTH_UNITS)} "
            f"(got unit-like fragment {unit_word!r})."
        )
    return f" Use '<number>{_KNOWN_WIDTH_UNITS[0]}', '<number>in', or '<number>mm'."


def parse_width(value: str | Length) -> float:
    """Parse a width specification into inches.

    Parameters
    ----------
    value : str | Length
        A unit string like ``"9cm"``, ``"6.7in"``, ``"170mm"``,
        ``"24pt"`` or a :class:`Length` value. Surrounding whitespace
        and matched quote characters are stripped from string inputs.

        Bare ``int``/``float`` are rejected: matplotlib's ``figsize``
        is in inches but dartwork-mpl widths are typically given in
        cm, so an unannotated number has no safe interpretation.

    Returns
    -------
    float
        Width in inches. Always strictly positive.

    Raises
    ------
    TypeError
        If ``value`` is a bare ``int``/``float``/``bool`` (no unit).
    ValueError
        If the input cannot be parsed, has an unknown unit, or is
        non-positive.
    """
    if isinstance(value, Length):
        v = value._inch
        if not math.isfinite(v) or v <= 0:
            raise ValueError(f"width must be positive and finite (got {v})")
        return v

    # bool is a subclass of int; trap it before the int/float branch so
    # the message is the same as for any other unit-less number.
    if isinstance(value, (bool, int, float)):
        raise TypeError(
            f"width must be a unit string like '13cm' / '5in' / '170mm' "
            f"or a Length value (dm.cm(13), dm.col1). Got "
            f"{type(value).__name__} {value!r} — bare numbers carry no "
            f"unit. For 13 cm write '13cm' or dm.cm(13); for 13 inches "
            f"write '13in' or dm.inch(13)."
        )

    if not isinstance(value, str):
        raise TypeError(
            f"width must be a unit string or a Length value "
            f"(got {type(value).__name__})"
        )

    return _parse_unit_string(value)


def figsize(
    width: str | Length, aspect: str | float = DEFAULT_ASPECT
) -> tuple[float, float]:
    """Return a matplotlib ``figsize`` tuple from a physical width and aspect.

    Drop-in replacement for inline ``figsize=(w, h)`` literals. Pairs
    cleanly with ``plt.subplots`` and ``plt.figure``::

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
        fig = plt.figure(figsize=dm.figsize(dm.col1, "standard"))

    Parameters
    ----------
    width : str | Length
        Physical width — either a unit string (``"13cm"``, ``"5in"``,
        ``"170mm"``, ``"24pt"``) or a :class:`Length` value
        (``dm.cm(13)``, ``dm.col1``, ``dm.col2``). Bare
        ``int``/``float`` are rejected.
    aspect : str | float, optional
        Height / width ratio. Either a named token in
        ``{"square", "portrait", "standard", "golden", "wide",
        "cinema"}`` or a positive float. Default ``"standard"``
        (3 : 4).

    Returns
    -------
    tuple[float, float]
        ``(width_in_inches, height_in_inches)``.
    """
    w_in = parse_width(width)
    ratio = parse_aspect(aspect)
    return (w_in, w_in * ratio)


def _suggest_aspect_correction(value: str) -> str:
    """Build a one-sentence "did you mean" suffix for an unknown aspect.

    Recognises three failure shapes: numeric literals quoted as strings
    (``"0.75"``), close-but-misspelt token names (``"sqaure"``), and
    everything else (no suggestion appended). Returns either a leading-
    space-prefixed suggestion or an empty string.
    """
    try:
        as_number = float(value)
    except ValueError:
        as_number = math.nan
    if math.isfinite(as_number) and as_number > 0:
        return f" To pass a numeric ratio, drop the quotes: aspect={as_number}."
    close = difflib.get_close_matches(
        value.strip().lower(), list(ASPECT_TOKENS), n=1, cutoff=0.5
    )
    if close:
        return f" Did you mean {close[0]!r}?"
    return ""


def parse_aspect(value: str | int | float) -> float:
    """Resolve an aspect specification to a height/width ratio.

    Parameters
    ----------
    value : str | int | float
        Either a known aspect token (``"square"``, ``"portrait"``,
        ``"standard"``, ``"golden"``, ``"wide"``, ``"cinema"``) or a
        positive number interpreted directly as ``height / width``.

    Returns
    -------
    float
        The height/width ratio. Always strictly positive.
    """
    if isinstance(value, bool):
        # bool is a subclass of int — reject before the int/float branch.
        raise ValueError(
            "aspect must be a positive number; bool is not accepted "
            "(use a token like 'standard' or a float like 0.5)"
        )

    if isinstance(value, (int, float)):
        ratio = float(value)
        if not math.isfinite(ratio) or ratio <= 0:
            raise ValueError(
                f"aspect must be positive and finite (got {ratio})"
            )
        return ratio

    if not isinstance(value, str):
        raise ValueError(
            f"aspect must be str, int, or float (got {type(value).__name__})"
        )

    key = value.strip().lower()
    if key not in ASPECT_TOKENS:
        raise ValueError(
            f"unknown aspect token {value!r}; known: "
            f"{sorted(ASPECT_TOKENS)}.{_suggest_aspect_correction(value)}"
        )
    return ASPECT_TOKENS[key]
