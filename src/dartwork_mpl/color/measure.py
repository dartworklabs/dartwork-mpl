"""Read colours from matplotlib: any colour-like value as :class:`Rgb`.

A name is resolved by matplotlib's live registry, so ``"C0"``, ``"tab:blue"``
and names registered after import work too. A string matplotlib does not
know is rejected with the closest registered names, so a typo does not
have to be guessed at.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

import matplotlib.colors as mcolors

from ..edgecase import settle
from .decide import suggest
from .edges import SAME_NAMESPACE
from .model import Lookup, Name
from .space import Rgb, Rgba


def registry() -> tuple[Name, ...]:
    """Every registered colour name, sorted (non-string keys dropped)."""
    # A caller may leave a non-string key in this live, mutable mapping.
    keys = cast("Iterable[object]", mcolors.get_named_colors_mapping())
    return tuple(sorted(Name(n) for n in keys if isinstance(n, str)))


def unknown_name(name: str) -> str:
    """Why ``name`` is not a colour, and where a valid one can be found."""
    lookup = Lookup(Name(name), registry())
    close = settle(lookup, suggest(lookup), (SAME_NAMESPACE,)).plan.names
    if close:
        found = "Closest registered names: " + ", ".join(map(repr, close))
    else:
        found = "No registered name is close to it"
    return (
        f"Invalid color name: {name!r}. {found}. dm.list_colors() lists the "
        "dartwork-mpl colour families and "
        "matplotlib.colors.get_named_colors_mapping() every registered name."
    )


def rgba(value: object) -> Rgba:
    """``value`` as matplotlib reads it, alpha included."""
    try:
        return Rgba.of(mcolors.to_rgba(value))  # type: ignore[arg-type]
    except ValueError as exc:
        if not isinstance(value, str):
            raise
        raise ValueError(unknown_name(value)) from exc


def rgb(value: object) -> Rgb:
    """``value`` as matplotlib reads it, alpha dropped."""
    return rgba(value).rgb
