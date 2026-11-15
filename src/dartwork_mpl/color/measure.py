"""Read colours from matplotlib: any colour-like value as :class:`Rgb`.

A name is resolved by matplotlib's live registry, so ``"C0"``, ``"tab:blue"``
and names registered after import work too. A string matplotlib does not
know is rejected with the closest registered names, so a typo does not
have to be guessed at.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import SupportsFloat

import matplotlib.colors as mcolors

from .decide import suggest
from .model import Items, Lookup, Name
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


Plain = str | tuple[float, float, float] | tuple[float, float, float, float]


def number(part: object, value: object) -> float:
    """One channel of ``value``; ``ValueError`` as matplotlib raises it."""
    if isinstance(part, str) or not isinstance(part, SupportsFloat):
        raise ValueError(f"Invalid RGBA argument: {value!r}")
    return float(part)


def plain(value: object) -> Plain:
    """A colour string, or three or four channels from any sequence."""
    if isinstance(value, str):
        return value
    if not isinstance(value, Items):
        raise ValueError(f"Invalid RGBA argument: {value!r}")
    channels = [number(part, value) for part in value]
    if len(channels) == 3:
        r, g, b = channels
        return (r, g, b)
    if len(channels) == 4:
        r, g, b, a = channels
        return (r, g, b, a)
    raise ValueError(f"Invalid RGBA argument: {value!r}")


def spec(value: object) -> tuple[Plain, float | None]:
    """``value`` as a colour in a shape matplotlib's ``ColorType`` names,
    and the alpha that overrides its own (``None``: none).

    The public colour arguments take what matplotlib reads at run time: a
    string, three or four channels in any sequence (a list, an array), or
    a colour and an alpha; anything else raises ``ValueError``.
    """
    if isinstance(value, Items) and not isinstance(value, str):
        parts = list(value)
        if len(parts) == 2 and not isinstance(parts[0], SupportsFloat):
            return plain(parts[0]), number(parts[1], value)
    return plain(value), None


def rgba(value: object) -> Rgba:
    """``value`` as matplotlib reads it, alpha included."""
    try:
        colour, alpha = spec(value)
        return Rgba.of(mcolors.to_rgba(colour, alpha))
    except ValueError as exc:
        if not isinstance(value, str):
            raise
        raise ValueError(unknown_name(value)) from exc


def rgb(value: object) -> Rgb:
    """``value`` as matplotlib reads it, alpha dropped."""
    return rgba(value).rgb
