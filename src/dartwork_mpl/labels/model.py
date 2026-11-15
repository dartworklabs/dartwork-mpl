"""The one place the labels' keywords become types, and the text styles
handed to matplotlib.

``label_bars``' keywords are parsed once here (:func:`parse_bar_options`);
a bad one raises ``ValueError`` naming it. The other helpers' ``side=``,
``loc=`` and ``x=`` become the places of ``places``. The types live by
concept: ``bar_options`` (what a bar label is asked and is),
``bar_geometry`` (what the layout measures of it), ``places`` (where a short
label goes) and ``panels`` (panel letters and line-end names).
"""

from __future__ import annotations

import numbers
import string
from collections.abc import Callable, Mapping, Sequence
from typing import (
    Literal,
    SupportsFloat,
    SupportsIndex,
    TypeAlias,
    TypedDict,
    TypeVar,
)

from ..vocab import HAlignName, VAlignName
from .bar_options import (
    BarOptions,
    ByKind,
    Call,
    Center,
    Crowded,
    Fmt,
    Inside,
    LabelInk,
    NoTotals,
    Outside,
    OwnInk,
    Rgba,
    Rotate,
    SeriesInk,
    Skip,
    Template,
    TextInk,
    TickLike,
    Total,
    TotalsOnly,
    TotalsToo,
    Where,
)
from .places import (
    Above,
    AnySide,
    AtLeft,
    Below,
    FromPanel,
    Left,
    LetterX,
    Right,
    SideChoice,
)

AnyColour: TypeAlias = str | tuple[float, float, float] | Rgba
"""A colour a caller passes: a name or hex, an RGB or an RGBA tuple."""

FontStyleName: TypeAlias = Literal["normal", "italic", "oblique"]


class LetterStyle(TypedDict, total=False):
    """The ``Text`` keywords the label helpers hand on to matplotlib.

    These are the properties a caller styles a label with; matplotlib
    still takes any other ``Text`` property it knows at run time, the
    checker only knows these. Size and weight are in :class:`TextStyle`;
    ``label_axes`` takes them as its own parameters.
    """

    color: AnyColour
    c: AnyColour
    alpha: float | None
    backgroundcolor: AnyColour
    fontfamily: str | Sequence[str]
    family: str | Sequence[str]
    fontname: str
    fontstyle: FontStyleName
    style: FontStyleName
    fontstretch: float | str
    fontvariant: Literal["normal", "small-caps"]
    horizontalalignment: HAlignName
    ha: HAlignName
    verticalalignment: VAlignName
    va: VAlignName
    multialignment: HAlignName
    ma: HAlignName
    rotation: float | Literal["vertical", "horizontal"] | None
    rotation_mode: Literal["default", "anchor"] | None
    linespacing: float | None
    wrap: bool
    usetex: bool | None
    parse_math: bool
    bbox: dict[str, object] | None
    zorder: float
    clip_on: bool
    visible: bool
    in_layout: bool
    label: str
    gid: str | None
    url: str | None
    path_effects: Sequence[object]


class NoteStyle(LetterStyle, total=False):
    """The keywords ``annotate_value`` hands to ``ax.annotate``; their size is their own ``fontsize``."""

    fontweight: float | str
    weight: float | str
    arrowprops: dict[str, object] | None
    annotation_clip: bool | None


class TextStyle(LetterStyle, total=False):
    """The ``Text`` keywords ``add_note`` hands to ``fig.text``."""

    fontsize: float | str
    size: float | str
    fontweight: float | str
    weight: float | str


class AnnotateStyle(NoteStyle, total=False):
    """The keywords ``label_line_ends`` hands to ``ax.annotate``."""

    fontsize: float | str
    size: float | str


def template_fields(template: str) -> list[tuple[str, str, str]]:
    """``(literal, spec, conversion)`` of each ``{}`` field of ``template``."""
    return [
        (literal, spec or "", conversion or "")
        for literal, name, spec, conversion in string.Formatter().parse(
            template
        )
        if name is not None
    ]


T = TypeVar("T")


def _choice(name: str, value: object, table: Mapping[object, T]) -> T:
    """The entry ``value`` names; ``ValueError`` naming the keyword."""
    for key, choice in table.items():
        if value is key or (isinstance(key, str) and value == key):
            return choice
    names = ", ".join(repr(a) for a in table)
    raise ValueError(f"{name} must be one of {names} (got {value!r})")


WHERE: Mapping[object, Where] = {
    "auto": ByKind(),
    "outside": Outside(),
    "inside": Inside(),
    "center": Center(),
}
TOTAL: Mapping[object, Total] = {
    "auto": TotalsToo(),
    "only": TotalsOnly(),
    False: NoTotals(),
}
CROWDED: Mapping[object, Crowded] = {"rotate": Rotate(), "skip": Skip()}
PLUS: Mapping[object, bool] = {"-": False, "+": True}


def _fmt(fmt: object) -> Fmt:
    if isinstance(fmt, str):
        try:
            fields = template_fields(fmt)
            fmt.format(*([1.0] * len(fields)))
        except (ValueError, IndexError, KeyError) as error:
            raise ValueError(
                f"fmt must be a template with '{{}}' for the number, e.g. "
                f"fmt='${{}}B' ({error}; got {fmt!r})"
            ) from None
        if not fields:
            raise ValueError(
                f"fmt must hold a '{{}}' for the number (got {fmt!r})"
            )
        return Template(fmt)
    if fmt is None:
        return TickLike()
    if callable(fmt):
        return Call(fmt)
    raise ValueError(
        f"fmt must be None, a '{{}}' template or a callable (got {fmt!r})"
    )


C = TypeVar("C")
"""A colour as the shell's ``to_rgba`` reads it."""


def _ink(color: C | None, to_rgba: Callable[[C], Rgba]) -> LabelInk:
    if color is None:
        return TextInk()
    if isinstance(color, str) and color == "series":
        return SeriesInk()
    try:
        return OwnInk(to_rgba(color))
    except (ValueError, TypeError):
        raise ValueError(
            f"color must be None, 'series' or a matplotlib colour (got {color!r})"
        ) from None


def parse_bar_options(
    *,
    where: object,
    total: object,
    crowded: object,
    decimals: object,
    fmt: object,
    color: C | None,
    sign: object,
    to_rgba: Callable[[C], Rgba],
) -> BarOptions:
    """The call's keywords as :class:`BarOptions`; ``ValueError`` names a bad one.

    ``to_rgba`` reads a matplotlib colour, raising ``ValueError`` for
    anything else (the shell passes matplotlib's own, so this module stays
    pure).
    """
    parsed_where = _choice("where", where, WHERE)
    parsed_total = _choice("total", total, TOTAL)
    parsed_crowded = _choice("crowded", crowded, CROWDED)
    plus = _choice("sign", sign, PLUS)
    if decimals is not None and (
        isinstance(decimals, bool)
        or not isinstance(decimals, numbers.Integral)
        or int(decimals) < 0
    ):
        raise ValueError(
            f"decimals must be None or an integer >= 0 (got {decimals!r})"
        )
    return BarOptions(
        where=parsed_where,
        total=parsed_total,
        crowded=parsed_crowded,
        decimals=None if decimals is None else int(decimals),
        fmt=_fmt(fmt),
        color=_ink(color, to_rgba),
        plus=plus,
    )


def parse_side(value: object) -> SideChoice:
    """``annotate_value``'s ``side``; ``ValueError`` otherwise."""
    names: dict[str, SideChoice] = {
        "auto": AnySide(),
        "above": Above(),
        "below": Below(),
        "right": Right(),
        "left": Left(),
    }
    if isinstance(value, str) and value in names:
        return names[value]
    raise ValueError(
        "side must be 'auto', 'above', 'below', 'left', or 'right'"
    )


def parse_letter_x(value: object) -> LetterX:
    """``label_axes``' ``x``: ``"auto"`` or an Axes-relative left edge."""
    if isinstance(value, str):
        return FromPanel() if value == "auto" else AtLeft(float(value))
    return AtLeft(_number(value))


def _number(value: object) -> float:
    if isinstance(value, SupportsFloat | SupportsIndex):
        return float(value)
    raise TypeError(f"expected a number, got {value!r}")
