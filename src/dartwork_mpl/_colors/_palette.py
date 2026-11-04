"""Curated color-name palettes, independent of registry and family lookup."""

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
        Non-negative number of series the palette must cover. Colors repeat if
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
        An index outside ``0..n-1`` is ignored, leaving every series at its
        base shade. A fractional index inside that range is rejected instead
        of receding every series without emphasising any.

    Returns
    -------
    list[str]
        Length-``n`` list of dartwork color names.

    Raises
    ------
    ValueError
        If ``n`` is negative, ``kind`` is unknown, or an in-range ``highlight``
        is not a whole number.

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

    if n < 0:
        raise ValueError("n must be non-negative; use 0 for an empty palette")

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
        # A fractional index passes the range test but never equals a series
        # position, so every series would recede and none would be emphasised:
        # a plausible-looking palette that answers a different question.
        if highlight != int(highlight):
            raise ValueError(
                f"highlight must be a whole number index in 0..{n - 1}; "
                f"got {highlight!r}, which would recede every series and "
                "emphasise none. Pass the index of the series to emphasise, "
                "or highlight=None to keep every series at its base shade."
            )
        highlight = int(highlight)

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


# Preserve historical imports and protocol-compatible function pickles.
make_palette.__module__ = "dartwork_mpl.helpers.colors"
