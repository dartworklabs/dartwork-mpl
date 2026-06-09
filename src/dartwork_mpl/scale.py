"""Font and line-width scaling helpers relative to rcParams defaults.

Provides ``fs``, ``fw``, and ``lw`` helper functions that add or
subtract fixed offsets from the current matplotlib style defaults.
"""

from __future__ import annotations

__all__ = ["dpi", "fs", "fw", "lw"]

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


def fw(n: int | float) -> int:
    """Return the base font weight plus 100 * *n*.

    String weight names (e.g., ``'normal'``, ``'bold'``) are automatically
    converted to their numeric equivalents (e.g., 400, 700) before computation.

    Parameters
    ----------
    n : int | float
        Number of weight steps to add (each step = 100).
        For example, n=1 selects one step bolder than the base weight.
        Fractional steps are allowed but the result is rounded to an int,
        since matplotlib font weights are integers (0-1000).

    Returns
    -------
    int
        Computed numeric font weight (always an ``int`` — a fractional
        ``n`` is rounded, so the ``-> int`` contract holds).
    """
    base = plt.rcParams["font.weight"]
    if isinstance(base, str):
        base = _WEIGHT_MAP.get(base.lower(), 400)
    return round(int(base) + 100 * n)


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


# Default DPI ladder step. The 50-DPI step matches the gap between
# matplotlib's screen (~100) and print (~300) defaults closely enough
# to feel natural while still distinguishing the rungs.
_DPI_STEP: float = 50.0


def dpi(n: int | float = 0) -> float:
    """Return the base save DPI plus ``n`` ladder steps.

    The base value is whatever ``rcParams['savefig.dpi']`` resolves to
    (matplotlib's preset-controlled output resolution — ``100`` for
    ``scientific``/``report``, ``300`` for ``poster``, etc.). Each step
    of ``n`` adds 50 DPI, matching the natural gap between the screen
    and print rungs of matplotlib's defaults.

    Use it the same way you use :func:`fs` / :func:`fw` / :func:`lw`:
    pass an integer offset that tracks the active preset instead of
    hardcoding a fixed number that drifts the moment the preset
    changes.

    Parameters
    ----------
    n : int | float, optional
        Offset in steps of 50 DPI. ``0`` (the default) returns the
        active preset's DPI verbatim; ``+1`` is one rung up, ``-1`` one
        rung down. Fractional values are allowed.

    Returns
    -------
    float
        Scaled DPI. Always positive; the lower clamp is 1 DPI so a
        very negative ``n`` cannot produce an invalid value for
        ``savefig.dpi``.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> dm.style.use("scientific")     # savefig.dpi == 100
    >>> dm.dpi()                        # one rung at the base
    100.0
    >>> dm.dpi(1)                       # one rung up
    150.0
    >>> dm.dpi(-1)                      # one rung down
    50.0

    Pair with :func:`dartwork_mpl.save_formats`:

    >>> dm.save_formats(fig, "out", dpi=dm.dpi(1))
    """
    raw = plt.rcParams.get("savefig.dpi", 100)
    if isinstance(raw, str):
        # matplotlib accepts the literal "figure" sentinel — fall back
        # to figure.dpi in that case so the ladder still tracks the
        # preset.
        if raw == "figure":
            base = float(plt.rcParams.get("figure.dpi", 100))
        else:
            base = float(raw)
    else:
        base = float(raw)
    return max(1.0, base + _DPI_STEP * float(n))
