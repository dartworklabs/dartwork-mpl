"""Read colours from matplotlib: any colour-like value as :class:`Rgb`.

A name is resolved by matplotlib's live registry, so ``"C0"``, ``"tab:blue"``
and names registered after import work too. A string matplotlib does not
know is rejected with the closest registered names, so a typo does not
have to be guessed at.
"""

from __future__ import annotations

from collections.abc import Iterable

import matplotlib.colors as mcolors

from .decide import suggest
from .model import Lookup, Name
from .space import Rgb, Rgba


def registry() -> tuple[Name, ...]:
    """Every registered colour name, sorted (non-string keys dropped)."""
    return names(mcolors.get_named_colors_mapping())


def names(keys: Iterable[object]) -> tuple[Name, ...]:
    """The string keys, sorted: a caller may leave a non-string key in
    matplotlib's live, mutable mapping, whatever its stub says."""
    return tuple(sorted(Name(n) for n in keys if isinstance(n, str)))


def unknown_name(name: str) -> str:
    """Why ``name`` is not a colour, and where a valid one can be found."""
    lookup = Lookup(Name(name), registry())
    close = suggest(lookup).names
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
        # The public colour arguments take what matplotlib reads at run
        # time (arrays too), wider than its ColorType stub; it validates.
        return Rgba.of(mcolors.to_rgba(value))  # pyright: ignore[reportArgumentType]
    except ValueError as exc:
        if not isinstance(value, str):
            raise
        raise ValueError(unknown_name(value)) from exc


def rgb(value: object) -> Rgb:
    """``value`` as matplotlib reads it, alpha dropped."""
    return rgba(value).rgb
