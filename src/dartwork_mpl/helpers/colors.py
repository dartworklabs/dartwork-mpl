"""Curated palette lookup for dartwork-mpl.

`make_palette` returns a list of dartwork color names sized to the
requested series count and palette kind. The four built-in lists
(categorical, sequential blue at two cardinalities, diverging
red-blue at two cardinalities) are the dartwork-mpl recommended
series colors; they live inside this function so the project's
palette curation stays centralised.

Renamed from ``auto_select_colors`` in 0.5 (``#156`` Round 5):

- ``auto_`` prefix collided with ``auto_layout`` (measure-and-adjust).
- ``select_colors`` was a strong verb for what is structurally a list slice.
- Model B discrete family lookup now lives in ``dm.colors(..., n=...)`` and
  cycle application in ``dm.set_colors(...)``.
"""

from __future__ import annotations

from typing import Literal


def make_palette(
    n: int,
    kind: Literal["categorical", "sequential", "diverging"] = "categorical",
    highlight: int | None = None,
) -> list[str]:
    """Return ``n`` curated dartwork color names for ``kind`` series.

    Parameters
    ----------
    n : int
        Number of series the palette must cover. Colors repeat if
        ``n`` exceeds the built-in list for ``kind``.
    kind : {"categorical", "sequential", "diverging"}
        Palette family. ``categorical`` returns distinct hues;
        ``sequential`` returns light→dark blues; ``diverging``
        returns red↔blue through gray.
    highlight : int | None
        If set, the series at this index becomes darker (``oc.*7``)
        and the rest become lighter (``oc.*3``) to emphasise it.
        Only effective for the categorical and (loosely) diverging
        palettes whose names contain a ``"5"`` middle shade.

    Returns
    -------
    list[str]
        Length-``n`` list of dartwork color names.

    Examples
    --------
    >>> make_palette(5)                           # 5 categorical series
    >>> make_palette(3, kind="sequential")        # 3 sequential blues
    >>> make_palette(4, highlight=0)              # emphasise series 0
    """
    if kind == "categorical":
        # Distinct colors for categorical data
        base_colors = [
            "oc.blue5",
            "oc.red5",
            "oc.green5",
            "oc.orange5",
            "oc.purple5",
            "oc.teal5",
            "oc.pink5",
            "oc.yellow5",
        ]
    elif kind == "sequential":
        # Gradient from light to dark
        if n <= 5:
            base_colors = [f"oc.blue{i}" for i in range(3, 8)]
        else:
            base_colors = [f"oc.blue{i}" for i in range(1, 10)]
    elif kind == "diverging":
        # Red to blue through gray
        if n <= 5:
            base_colors = [
                "oc.red6",
                "oc.red4",
                "oc.gray5",
                "oc.blue4",
                "oc.blue6",
            ]
        else:
            base_colors = [
                "oc.red7",
                "oc.red5",
                "oc.red3",
                "oc.gray5",
                "oc.blue3",
                "oc.blue5",
                "oc.blue7",
            ]
    else:
        raise ValueError(f"Unknown kind: {kind!r}")

    # Select colors
    if n <= len(base_colors):
        colors = base_colors[:n]
    else:
        # Repeat colors if needed
        colors = base_colors * (n // len(base_colors) + 1)
        colors = colors[:n]

    # Apply highlighting: emphasise the chosen series with a darker shade and
    # recede the rest with a lighter one, by stepping each colour's *weight
    # index* (higher = darker in Open Color). The previous ``.replace("5", …)``
    # only worked for the categorical set (whose names all carry a "5"); it
    # left sequential/diverging highlights on the wrong series and could
    # corrupt any name containing a stray "5".
    if highlight is not None and 0 <= highlight < n:
        import re as _re

        def _shift(color: str, delta: int) -> str:
            m = _re.match(r"^(.*?)(\d+)$", color)
            if m is None:
                return color
            base, shade = m.group(1), int(m.group(2))
            return f"{base}{max(0, min(9, shade + delta))}"

        colors = [
            _shift(c, 2) if i == highlight else _shift(c, -2)
            for i, c in enumerate(colors)
        ]

    return colors
