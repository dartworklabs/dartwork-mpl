"""Font and line-width scaling helpers relative to rcParams defaults.

Provides ``fs``, ``fw``, and ``lw`` helper functions that add or
subtract fixed offsets from the current matplotlib style defaults.
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
    """Return the base font size plus *n*.

    Parameters
    ----------
    n : int | float
        Offset to add to ``rcParams['font.size']``.
        Positive values increase, negative values decrease.

    Returns
    -------
    float
        Scaled font size.
    """
    return float(plt.rcParams["font.size"]) + float(n)


def fw(n: int) -> int:
    """Return the base font weight plus 100 × *n*.

    String weight names (e.g., ``'normal'``, ``'bold'``) are automatically
    converted to their numeric equivalents (e.g., 400, 700) before computation.

    Parameters
    ----------
    n : int
        Number of weight steps to add (each step = 100).
        For example, n=1 selects one step bolder than the base weight.

    Returns
    -------
    int
        Computed numeric font weight.
    """
    base = plt.rcParams["font.weight"]
    if isinstance(base, str):
        base = _WEIGHT_MAP.get(base.lower(), 400)
    return int(base) + 100 * n


def lw(n: int | float) -> float:
    """Return the base line width plus *n*.

    Parameters
    ----------
    n : int | float
        Offset to add to ``rcParams['lines.linewidth']``.
        Positive values thicken, negative values thin.

    Returns
    -------
    float
        Scaled line width.
    """
    return float(plt.rcParams["lines.linewidth"]) + float(n)
