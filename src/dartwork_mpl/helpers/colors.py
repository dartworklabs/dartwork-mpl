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
- ``palette`` is the existing domain term used by ``list_palettes`` and ``show_palette``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from matplotlib.axes import Axes


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

    # Apply highlighting
    if highlight is not None and 0 <= highlight < n:
        # Make highlighted series darker, others lighter
        new_colors = []
        for i, color in enumerate(colors):
            if i == highlight:
                # Keep original or make darker
                new_colors.append(color.replace("5", "7"))
            else:
                # Make lighter
                new_colors.append(color.replace("5", "3"))
        colors = new_colors

    return colors


def _palette_color_names(name: str) -> list[str]:
    """Return every colour name in palette ``name``, sorted by weight.

    ``name`` may be a fully-qualified base (``"dc.trustworthy"``,
    ``"oc.blue"``) or a bare dartwork name (``"trustworthy"`` resolves to
    ``"dc.trustworthy"``).
    """
    import re

    import matplotlib.colors as mcolors

    from ..colors._loader import ensure_loaded

    ensure_loaded()
    base = name if "." in name else f"dc.{name}"
    pattern = re.compile(rf"^{re.escape(base)}(\d+)$")
    found: list[tuple[int, str]] = []
    for cname in mcolors.get_named_colors_mapping():
        match = pattern.match(cname)
        if match:
            found.append((int(match.group(1)), cname))
    if not found:
        raise ValueError(
            f"Palette {base!r} not found or has no numbered shades. "
            f"See dm.list_palettes()."
        )
    found.sort(key=lambda t: t[0])
    return [cname for _, cname in found]


def get_palette(
    name: str,
    n: int | None = None,
    subset: Literal["first", "even", "last"] = "first",
) -> list[str]:
    """Return colour names from a discrete palette.

    Parameters
    ----------
    name : str
        Palette base name — ``"trustworthy"`` / ``"dc.trustworthy"`` /
        ``"oc.blue"``. Bare names resolve under the ``dc.`` namespace.
    n : int | None
        Number of colours. ``None`` returns the whole palette (8 for the
        dartwork categorical set). If ``n`` exceeds the palette size the
        colours repeat (matching :func:`make_palette`).
    subset : {"first", "even", "last"}
        How to pick ``n`` of the palette's colours. ``"first"`` (default)
        takes the leading ``n`` — the dartwork palettes are ordered so the
        first ``n`` are the best-separated subset. ``"even"`` spreads the
        picks across the whole palette; ``"last"`` takes the trailing ``n``.

    Returns
    -------
    list[str]
        Length-``n`` (or full) list of dartwork colour names, usable
        directly as matplotlib colours or via :func:`set_cycle`.

    Examples
    --------
    >>> get_palette("trustworthy")            # all 8
    >>> get_palette("trustworthy", n=5)       # first 5 (best-separated)
    >>> get_palette("coolwarm", n=7, subset="even")
    """
    base = _palette_color_names(name)
    if n is None:
        return base
    if n <= 0:
        return []
    if subset == "first":
        sel = base[:n]
    elif subset == "last":
        sel = base[-n:]
    elif subset == "even":
        if n >= len(base):
            sel = list(base)
        elif n == 1:
            sel = [base[0]]
        else:
            step = (len(base) - 1) / (n - 1)
            sel = [base[round(i * step)] for i in range(n)]
    else:
        raise ValueError(f"Unknown subset: {subset!r}")
    if len(sel) < n:  # repeat to fill when n exceeds palette size
        sel = (sel * (n // len(sel) + 1))[:n]
    return sel


def set_cycle(
    palette: str | list[str], ax: Axes | None = None, n: int | None = None
) -> None:
    """Set the matplotlib colour cycle from a palette name or colour list.

    Parameters
    ----------
    palette : str | list[str]
        A palette base name (``"trustworthy"``, ``"dc.spectrum"``) or an
        explicit list of colours / colour names.
    ax : matplotlib.axes.Axes | None
        If given, set the cycle on that Axes only (``ax.set_prop_cycle``).
        If ``None`` (default), update the global
        ``rcParams["axes.prop_cycle"]`` so every subsequent Axes uses it.
    n : int | None
        When ``palette`` is a name, how many colours to use (see
        :func:`get_palette`). Ignored for an explicit list.

    Examples
    --------
    >>> set_cycle("spectrum")                 # global, all 8
    >>> set_cycle("trustworthy", n=5)         # global, first 5
    >>> set_cycle("focus", ax=ax)             # this Axes only
    """
    import matplotlib.pyplot as plt
    from cycler import cycler

    colors = (
        get_palette(palette, n=n) if isinstance(palette, str) else list(palette)
    )
    cyc = cycler(color=colors)
    if ax is None:
        plt.rcParams["axes.prop_cycle"] = cyc
    else:
        ax.set_prop_cycle(cyc)
