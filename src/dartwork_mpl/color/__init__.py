"""Colour names and values, palettes and contrast.

Importing the slice registers every shipped colour with matplotlib, so
``color="dc.teal5"``, ``color="oc.red5"`` and ``cmap="dc.aurora"`` work in
any plotting call. ``dm.colors(name, n)`` returns a family's designed
``n``-colour form, ``dm.color(text)`` one :class:`Color`, and ``dm.ensure_contrast`` / ``dm.readable_text_color``
keep text legible. Each call parses its input (``model``), decides
(``decide`` and the named ``edges``) and hands back plain values.
"""

from __future__ import annotations

from typing import overload

import matplotlib as mpl
import matplotlib.colors as mcolors

from ..colorspace import (
    Color,
    ContrastFacts,
    Oklab,
    Oklch,
    Rgb,
    lifted,
    readable,
)
from ..edgecase import settle
from ..vocab import DefaultLocale, Locale
from . import apply, decide, measure
from .catalog import CATALOG
from .edges import FULL_LADDER, KR_TOKENS
from .family import Count, Family, parse_kind
from .model import (
    Form,
    Name,
    SemanticFacts,
    parse_ratio,
    parse_written,
    rgb_color,
)

__all__ = [
    "apply_semantic",
    "color",
    "colors",
    "ensure_contrast",
    "hex",
    "list_color_libraries",
    "list_colors",
    "oklab",
    "oklch",
    "readable_text_color",
    "rgb",
]

# For other slices (validation, labels): tuples in, numbers out.

RGB = tuple[float, float, float]
RGBA = tuple[float, float, float, float]


# -- single colours ------------------------------------------------------------


def color(value: Color | str) -> Color:
    """Parse a colour into a :class:`Color`.

    Accepts a hex (``"#ff0000"``), ``"rgb(1, 0, 0)"`` (channels in 0-1 or
    0-255), ``"oklch(0.7, 0.15, 30)"`` (hue in degrees),
    ``"oklab(0.6, 0.1, -0.1)"``, any matplotlib colour name (``"oc.red5"``,
    ``"dc.teal4"``, ``"tab:blue"``) or a :class:`Color`::

        accent = dm.color("dc.amber5").to_hex()

    An unknown name raises ``ValueError`` naming the closest registered ones.
    """
    if isinstance(value, Color):
        return value
    written = parse_written(value)
    if isinstance(written, Color):
        return written
    return Color(measure.rgb(written).oklab())


def oklch(L: float, C: float, h: float) -> Color:
    """A colour from OKLCH lightness, chroma and hue in degrees."""
    return Color(Oklch(L, C, h).lab())


def oklab(L: float, a: float, b: float) -> Color:
    """A colour from OKLab coordinates."""
    return Color(Oklab(L, a, b))


def rgb(r: float, g: float, b: float) -> Color:
    """A colour from RGB channels, all in 0-1 or all in 0-255."""
    return rgb_color(r, g, b)


def hex(text: str) -> Color:
    """A colour from ``"#rgb"`` or ``"#rrggbb"``."""
    return Color(Rgb.from_hex(text).oklab())


# -- contrast ------------------------------------------------------------------


def ensure_contrast(
    color: object, background: object, *, min_ratio: float = 4.5
) -> str:
    """``color``, darkened or lightened until it reaches ``min_ratio`` WCAG
    contrast on ``background``.

    A colour that already passes comes back unchanged (as given when it is
    a string). Otherwise its HLS lightness moves toward black or white,
    whichever contrasts more, by the least that passes, and the result is a
    ``"#rrggbb"``; an unreachable ratio ends at the pole::

        ax.text(x, y, "peak", color=dm.ensure_contrast("dc.amber5", ax.get_facecolor()))
    """
    target = parse_ratio(min_ratio)
    facts = ContrastFacts(measure.rgb(color), measure.rgb(background), target)
    lift = lifted(facts)
    if lift is not None:
        return lift.rgb().hex()
    return color if isinstance(color, str) else facts.color.hex()


def readable_text_color(
    background: object, *, light: str = "white", dark: str = "black"
) -> str:
    """``light`` or ``dark``, whichever has more contrast on ``background``."""
    ink = readable(
        measure.rgb(background), measure.rgb(light), measure.rgb(dark)
    )
    return ink.pick(light, dark)


# -- families ------------------------------------------------------------------


def family(name: object) -> Family:
    """The ``dc.*`` family ``name`` (``"teal"`` or ``"dc.teal"``)."""
    if not isinstance(name, str):
        raise TypeError(
            f"color family name must be str, got {type(name).__name__}"
        )
    bare = name.removeprefix("dc.")
    if bare in CATALOG.families:
        return CATALOG.families[bare]
    nearest = ", ".join(decide.nearest_families(Name(bare), CATALOG).names)
    raise ValueError(
        f"Unknown color family {bare!r}. Nearest names: {nearest}."
    )


def discrete(found: Family, n: object) -> list[str]:
    form = Form(found, Count.parse(n, found))
    return list(settle(form, decide.discrete(form), (FULL_LADDER,)).plan)


@overload
def colors(
    name: str, n: None = None, *, reverse: bool = False
) -> mcolors.Colormap: ...
@overload
def colors(name: str, n: int, *, reverse: bool = False) -> list[str]: ...
def colors(
    name: str, n: int | None = None, *, reverse: bool = False
) -> mcolors.Colormap | list[str]:
    """A ``dc.*`` family's colormap, or its designed ``n``-colour form.

    ``"teal"`` and ``"dc.teal"`` are the same family; see
    :func:`list_colors`. With ``n`` the result is ``n`` hex strings, chosen
    by design (never resampled), light to dark for a ladder::

        dm.colors("dc.teal", n=4)          # four steps of one family
        dm.colors("dc.vivid", n=3)         # the first three of a set

    ``n`` past a family's form raises ``ValueError``.
    """
    found = family(name)
    if n is not None:
        form = discrete(found, n)
        return form[::-1] if reverse else form
    cmap_name = f"dc.{found.name}"
    if not reverse:
        return mpl.colormaps[cmap_name]
    if f"{cmap_name}_r" in mpl.colormaps:
        return mpl.colormaps[f"{cmap_name}_r"]
    return mpl.colormaps[cmap_name].reversed(name=f"{cmap_name}_r")


def list_colors(kind: str | None = None) -> list[dict[str, object]]:
    """The ``dc.*`` families, optionally of one kind: ``"sequential"``,
    ``"multi-hue"``, ``"diverging"``, ``"cyclic"`` or ``"qualitative"``.

    Each record has ``name``, ``kind``, ``continuous`` and ``discrete_size``
    (None when any ``n`` up to the limit is designed).
    """
    wanted = None if kind is None else parse_kind(kind)
    return [
        {
            "name": found.name,
            "kind": found.kind.value,
            "continuous": found.kind.continuous,
            "discrete_size": found.size,
        }
        for found in CATALOG.families.values()
        if wanted is None or found.kind == wanted
    ]


def list_color_libraries() -> list[dict[str, str]]:
    """The colour libraries registered with matplotlib, ``dc.`` first.

    Each record has ``prefix`` (``"oc."``), the start of every name the
    library registers (``color="oc.red5"``), and ``label``, what it is
    (``"OpenColor"``). :func:`list_colors` lists the ``dc.*`` families.
    """
    return [
        {"prefix": library.prefix, "label": library.label}
        for library in CATALOG.libraries
    ]


def apply_semantic(locale: Locale) -> None:
    """Bind the role colours ``dc.pos``/``neg``/``ref``/``hl`` for ``locale``
    (Korean: gains red, losses blue; the default: gains green)."""
    facts = SemanticFacts(locale, CATALOG)
    tokens = settle(facts, decide.semantic(facts), (KR_TOKENS,)).plan
    apply.apply_semantic(tokens)


apply.register(CATALOG)
apply_semantic(DefaultLocale())
