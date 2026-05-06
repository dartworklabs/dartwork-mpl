"""Free-form width and aspect parsing helpers.

dartwork-mpl 0.4+ accepts user-supplied widths in physical units
(cm/in/mm) rather than fixed tokens. This module is the parser
that converts those inputs to inches for matplotlib.

It also resolves named aspect tokens (square/portrait/standard/
golden/wide/cinema) into a height/width ratio.
"""

from __future__ import annotations

__all__ = [
    "ASPECT_TOKENS",
    "DEFAULT_ASPECT",
    "Inches",
    "cm",
    "figsize",
    "inch",
    "mm",
    "parse_aspect",
    "parse_width",
]

import difflib
import math
import re

CM_PER_INCH: float = 2.54
MM_PER_INCH: float = 25.4

_KNOWN_WIDTH_UNITS: tuple[str, ...] = ("cm", "in", "mm")

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
    (?P<unit>cm|in|mm)?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


class Inches(float):
    """A ``float`` carrying the contract "I am already inches.".

    Returned by :func:`cm`, :func:`inch`, and :func:`mm` so that
    :func:`parse_width` can distinguish "user already converted"
    values from bare numbers (which carry no unit and are rejected).

    Arithmetic with another scalar preserves the ``Inches`` tag —
    ``dm.cm(9) * 2`` returns ``Inches(7.087)``, not a plain
    ``float`` that downstream callers would have to re-interpret.
    This closes a unit-corruption hole where doubled widths silently
    decayed into ambiguous floats.

    Setting ``__array_ufunc__ = None`` opts this class out of numpy
    universal-function dispatch. Without it, ``np.float64(2) * cm(9)``
    would route through numpy's multiply ufunc and return a bare
    ``np.float64``, dropping the ``Inches`` tag and re-opening the
    cm/inches corruption hole at array boundaries.
    """

    __slots__ = ()
    __array_ufunc__ = None

    def _wrap(self, value: float) -> Inches:
        if isinstance(value, Inches):
            return value
        if isinstance(value, float):
            return Inches(value)
        # Defensive: ``float.__add__`` and friends return ``float``
        # in practice, but the typeshed signature is broader.
        return Inches(float(value))

    def __add__(self, other: float) -> Inches:
        return self._wrap(float.__add__(self, other))

    def __radd__(self, other: float) -> Inches:
        return self._wrap(float.__radd__(self, other))

    def __sub__(self, other: float) -> Inches:
        return self._wrap(float.__sub__(self, other))

    def __rsub__(self, other: float) -> Inches:
        return self._wrap(float.__rsub__(self, other))

    def __mul__(self, other: float) -> Inches:
        return self._wrap(float.__mul__(self, other))

    def __rmul__(self, other: float) -> Inches:
        return self._wrap(float.__rmul__(self, other))

    def __truediv__(self, other: float) -> Inches:
        return self._wrap(float.__truediv__(self, other))

    def __rtruediv__(self, other: float) -> Inches:
        return self._wrap(float.__rtruediv__(self, other))

    def __neg__(self) -> Inches:
        return Inches(float.__neg__(self))

    def __abs__(self) -> Inches:
        return Inches(float.__abs__(self))


def cm(value: float) -> Inches:
    """Convert centimeters to inches."""
    return Inches(float(value) / CM_PER_INCH)


def inch(value: float) -> Inches:
    """Identity helper — tags the value as already-in-inches."""
    return Inches(float(value))


def mm(value: float) -> Inches:
    """Convert millimeters to inches."""
    return Inches(float(value) / MM_PER_INCH)


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


def parse_width(value: str | Inches) -> float:
    """Parse a width specification into inches.

    Parameters
    ----------
    value : str | Inches
        A unit string like ``"9cm"``, ``"6.7in"``, ``"170mm"`` or an
        :class:`Inches` value (returned by :func:`cm`/:func:`inch`/
        :func:`mm`). Surrounding whitespace and matched quote
        characters are stripped from string inputs.

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
    # An Inches instance is "already in inches" — pass through.
    if isinstance(value, Inches):
        v = float(value)
        if not math.isfinite(v) or v <= 0:
            raise ValueError(f"width must be positive and finite (got {v})")
        return v

    # bool is a subclass of int; trap it before the int/float branch so
    # the message is the same as for any other unit-less number.
    if isinstance(value, (bool, int, float)):
        raise TypeError(
            f"width must be a unit string like '13cm' / '5in' / '170mm' "
            f"or an Inches value (dm.cm(13), dm.col1). Got "
            f"{type(value).__name__} {value!r} — bare numbers carry no "
            f"unit. For 13 cm write '13cm' or dm.cm(13); for 13 inches "
            f"write '13in' or dm.inch(13)."
        )

    if not isinstance(value, str):
        raise TypeError(
            f"width must be a unit string or an Inches value "
            f"(got {type(value).__name__})"
        )

    text = value.strip().strip('"').strip("'")
    match = _WIDTH_RE.match(text)
    if match is None:
        raise ValueError(
            f"could not parse width {value!r}; expected '<number>' "
            f"with optional unit suffix (cm, in, mm)."
            f"{_suggest_width_correction(text)}"
        )

    number = float(match.group("value"))
    unit = (match.group("unit") or "cm").lower()
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"width must be positive and finite (got {number})")

    if unit == "cm":
        return cm(number)
    if unit == "in":
        return inch(number)
    return mm(number)


def figsize(
    width: str | Inches, aspect: str | float = DEFAULT_ASPECT
) -> tuple[float, float]:
    """Return a matplotlib ``figsize`` tuple from a physical width and aspect.

    Drop-in replacement for inline ``figsize=(w, h)`` literals. Pairs
    cleanly with ``plt.subplots`` and ``plt.figure``::

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
        fig = plt.figure(figsize=dm.figsize(dm.col1, "standard"))

    Parameters
    ----------
    width : str | Inches
        Physical width — either a unit string (``"13cm"``, ``"5in"``,
        ``"170mm"``) or an :class:`Inches` value (``dm.cm(13)``,
        ``dm.col1``, ``dm.col2``). Bare ``int``/``float`` are rejected.
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
