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
]

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
    (?P<value>[+-]?\d+(?:\.\d+)?)
    \s*
    (?P<unit>cm|in|mm)?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def cm(value: float) -> float:
    """Convert centimeters to inches."""
    return float(value) / CM_PER_INCH


def inch(value: float) -> float:
    """Identity helper — kept for symmetry with cm/mm."""
    return float(value)


def mm(value: float) -> float:
    """Convert millimeters to inches."""
    return float(value) / MM_PER_INCH


def parse_width(value: str | int | float) -> float:
    """Parse a width specification into inches.

    Parameters
    ----------
    value : str | int | float
        A width like ``"9cm"``, ``"6.7in"``, ``"170mm"``, or a bare
        number (interpreted as cm). Surrounding whitespace and matched
        quote characters are stripped.

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
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value <= 0:
            raise ValueError(
                f"width must be positive (got {value}); raw numbers "
                f"are interpreted as cm"
            )
        return cm(value)

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
    if number <= 0:
        raise ValueError(f"width must be positive (got {number})")

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
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        ratio = float(value)
        if ratio <= 0:
            raise ValueError(f"aspect must be positive (got {ratio})")
        return ratio

    if not isinstance(value, str):
        raise ValueError(
            f"aspect must be str, int, or float (got {type(value).__name__})"
        )

    key = value.strip().lower()
    if key not in ASPECT_TOKENS:
        raise ValueError(
            f"unknown aspect token {value!r}; known: "
            f"{sorted(ASPECT_TOKENS)}"
        )
    return ASPECT_TOKENS[key]
