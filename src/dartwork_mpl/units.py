"""Free-form width and aspect parsing helpers.

dartwork-mpl 0.4+ accepts user-supplied widths in physical units
(cm/in/mm) rather than fixed tokens. This module is the parser
that converts those inputs to inches for matplotlib.

It also resolves named aspect tokens (square/portrait/standard/
golden/wide/cinema) into a height/width ratio.
"""

from __future__ import annotations

__all__ = [
    "cm",
    "inch",
    "mm",
    "parse_width",
    "parse_aspect",
    "ASPECT_TOKENS",
    "DEFAULT_ASPECT",
    "Inches",
]

import math
import re

CM_PER_INCH: float = 2.54
MM_PER_INCH: float = 25.4

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
    values from raw numbers (which are interpreted as cm).

    Arithmetic with another scalar preserves the ``Inches`` tag —
    ``dm.cm(9) * 2`` returns ``Inches(7.087)``, not a plain
    ``float`` that ``parse_width`` would re-interpret as cm. This
    closes a unit-corruption hole where doubled widths silently lost
    the cm→inches conversion.

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
        return value  # type: ignore[return-value]

    def __add__(self, other):
        return self._wrap(float.__add__(self, other))

    def __radd__(self, other):
        return self._wrap(float.__radd__(self, other))

    def __sub__(self, other):
        return self._wrap(float.__sub__(self, other))

    def __rsub__(self, other):
        return self._wrap(float.__rsub__(self, other))

    def __mul__(self, other):
        return self._wrap(float.__mul__(self, other))

    def __rmul__(self, other):
        return self._wrap(float.__rmul__(self, other))

    def __truediv__(self, other):
        return self._wrap(float.__truediv__(self, other))

    def __rtruediv__(self, other):
        return self._wrap(float.__rtruediv__(self, other))

    def __neg__(self):
        return Inches(float.__neg__(self))

    def __abs__(self):
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


def parse_width(value: str | int | float) -> float:
    """Parse a width specification into inches.

    Parameters
    ----------
    value : str | int | float
        A width like ``"9cm"``, ``"6.7in"``, ``"170mm"``, an
        :class:`Inches` value (returned by :func:`cm`/:func:`inch`/
        :func:`mm`), or a bare number (interpreted as cm).
        Surrounding whitespace and matched quote characters are
        stripped.

    Returns
    -------
    float
        Width in inches. Always strictly positive.

    Raises
    ------
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

    if isinstance(value, bool):
        raise ValueError(
            "width must be a positive number or string; bool is not accepted"
        )

    if isinstance(value, (int, float)):
        v = float(value)
        if not math.isfinite(v) or v <= 0:
            raise ValueError(
                f"width must be positive and finite (got {value}); raw "
                f"numbers are interpreted as cm"
            )
        return float(cm(v))

    if not isinstance(value, str):
        raise ValueError(
            f"width must be str, int, or float (got {type(value).__name__})"
        )

    text = value.strip().strip('"').strip("'")
    match = _WIDTH_RE.match(text)
    if match is None:
        raise ValueError(
            f"could not parse width {value!r}; expected '<number>' "
            f"with optional unit suffix (cm, in, mm)"
        )

    number = float(match.group("value"))
    unit = (match.group("unit") or "cm").lower()
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"width must be positive and finite (got {number})")

    if unit == "cm":
        return cm(number)
    if unit == "in":
        return inch(number)
    if unit == "mm":
        return mm(number)
    raise ValueError(f"unknown width unit: {unit!r}")


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
            f"unknown aspect token {value!r}; known: {sorted(ASPECT_TOKENS)}"
        )
    return ASPECT_TOKENS[key]
