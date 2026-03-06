"""Font and line scaling relative to rcParams defaults.

Provides ``fs``, ``fw``, and ``lw`` helpers that offset from the
current matplotlib style's base sizes.
"""

from __future__ import annotations

__all__ = ["fs", "fw", "lw"]

import matplotlib.pyplot as plt

_WEIGHT_MAP: dict[str, int] = {
    "ultralight": 100,
    "light": 200,
    "normal": 400,
    "regular": 400,
    "book": 400,
    "medium": 500,
    "roman": 500,
    "semibold": 600,
    "demibold": 600,
    "demi": 600,
    "bold": 700,
    "heavy": 800,
    "extra bold": 800,
    "black": 900,
}


def fs(n: int | float) -> float:
    """Return base font size + *n*.

    Parameters
    ----------
    n : int or float
        Value to add to ``rcParams['font.size']``.

    Returns
    -------
    float
        Base font size + *n*.
    """
    return plt.rcParams["font.size"] + n


def fw(n: int) -> int:
    """Return base font weight + 100 × *n*.

    String weights (e.g. ``'normal'``, ``'bold'``) are converted to
    their numeric equivalents before arithmetic.

    Parameters
    ----------
    n : int
        Value to multiply by 100 and add to base font weight.

    Returns
    -------
    int
        Base font weight + 100 × *n*.
    """
    base = plt.rcParams["font.weight"]
    if isinstance(base, str):
        base = _WEIGHT_MAP.get(base.lower(), 400)
    return int(base) + 100 * n


def lw(n: int | float) -> float:
    """Return base line width + *n*.

    Parameters
    ----------
    n : int or float
        Value to add to ``rcParams['lines.linewidth']``.

    Returns
    -------
    float
        Base line width + *n*.
    """
    return plt.rcParams["lines.linewidth"] + n
