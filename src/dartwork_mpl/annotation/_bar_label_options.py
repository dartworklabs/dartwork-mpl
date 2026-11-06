"""The keywords of a :func:`~._bar_labels.label_bars` call and the text they make.

* **Options.** :func:`parse_options` validates the call's keywords into a
  frozen :class:`BarLabelOptions`: ``where``, ``total`` and ``crowded`` are
  strict, ``decimals`` is ``None`` or an integer >= 0, ``fmt`` a ``{}``
  template or a callable, ``color`` ``None``, ``"series"`` or a matplotlib
  colour.
* **Text.** :func:`compose_text` writes one label's text from its value in
  the axis's tick unit: the number with the call's decimals and the ticks'
  prefix and suffix, or the ``fmt`` template around the number (a field with
  a format spec formats the value itself), or what the ``fmt`` callable
  returns.
"""

from __future__ import annotations

import numbers
import string
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeAlias

import matplotlib as mpl
import matplotlib.colors as mcolors

from ..formatting import TickScale, number_text
from ._bar_label_ink import is_series

__all__ = [
    "BarLabelOptions",
    "Crowded",
    "Fmt",
    "HiddenFor",
    "Kind",
    "Orientation",
    "Placement",
    "Total",
    "Where",
    "compose_text",
    "parse_options",
]

Where: TypeAlias = Literal["auto", "outside", "inside", "center"]
# Where one label sits: "auto" resolved for its kind.
Placement: TypeAlias = Literal["outside", "inside", "center"]
# What a label labels: a plain bar's value, a stack segment's, a stack's net.
Kind: TypeAlias = Literal["edge", "segment", "total"]
Total: TypeAlias = Literal["auto", "only", False]
Crowded: TypeAlias = Literal["rotate", "skip", "inside"]
Orientation: TypeAlias = Literal["vertical", "horizontal"]
Fmt: TypeAlias = str | Callable[[float], object] | None
# Why the layout hid a label where it would overlap: another series took
# its bar index ("turn"), or there was no room for it ("room").
HiddenFor: TypeAlias = Literal["turn", "room"]


# ------------------------------------------------------------ the options
def _parse_where(where: str) -> Where:
    match where:
        case "auto" | "outside" | "inside" | "center":
            return where
        case _:
            raise ValueError(
                "where must be 'auto', 'outside', 'inside' or 'center' "
                f"(got {where!r})"
            )


def _parse_total(total: object) -> Total:
    if total is False:
        return False
    match total:
        case "auto" | "only":
            return total
        case _:
            raise ValueError(
                f"total must be 'auto', 'only' or False (got {total!r})"
            )


def _parse_crowded(crowded: str) -> Crowded:
    match crowded:
        case "rotate" | "skip" | "inside":
            return crowded
        case _:
            raise ValueError(
                "crowded must be 'rotate', 'skip' or 'inside' "
                f"(got {crowded!r})"
            )


def _parse_decimals(decimals: object) -> int | None:
    if decimals is None:
        return None
    if (
        isinstance(decimals, bool)
        or not isinstance(decimals, numbers.Integral)
        or int(decimals) < 0
    ):
        raise ValueError(
            f"decimals must be None or an integer >= 0 (got {decimals!r})"
        )
    return int(decimals)


def _template_fields(template: str) -> list[tuple[str, str | None, str, str]]:
    """``string.Formatter().parse`` of ``template`` with ``None`` specs as ``""``."""
    return [
        (literal, name, spec or "", conversion or "")
        for literal, name, spec, conversion in string.Formatter().parse(
            template
        )
    ]


def _minus(text: str) -> str:
    """Matplotlib's minus (U+2212 unless ``axes.unicode_minus`` is off)."""
    if mpl.rcParams["axes.unicode_minus"]:
        return text.replace("-", "\N{MINUS SIGN}")
    return text


def _render_template(template: str, number: str, value: float) -> str:
    """``template`` with each ``{}`` replaced by ``number``.

    A field with a format spec or conversion (``{:.2f}``) formats ``value``
    itself instead, with matplotlib's minus.
    """
    formatter = string.Formatter()
    out: list[str] = []
    for literal, name, spec, conversion in _template_fields(template):
        out.append(literal)
        if name is None:
            continue
        if not spec and not conversion:
            out.append(number)
            continue
        converted = formatter.convert_field(value, conversion or None)
        out.append(_minus(formatter.format_field(converted, spec)))
    return "".join(out)


def _parse_fmt(fmt: object) -> Fmt:
    if fmt is None or callable(fmt):
        return fmt
    if not isinstance(fmt, str):
        raise ValueError(
            f"fmt must be None, a '{{}}' template or a callable (got {fmt!r})"
        )
    hint = "e.g. fmt='${}B'; a callable gets the scaled value"
    try:
        fields = [name for _, name, _, _ in _template_fields(fmt)]
    except ValueError as error:
        raise ValueError(f"fmt {fmt!r} is not a template: {error}") from None
    names = [name for name in fields if name is not None]
    if not names:
        raise ValueError(
            f"fmt must hold a '{{}}' placeholder for the number ({hint}); "
            f"got {fmt!r}"
        )
    if any(name not in ("", "0") for name in names):
        raise ValueError(
            f"fmt placeholders must be '{{}}' or '{{:spec}}' ({hint}); "
            f"got {fmt!r}"
        )
    try:
        _render_template(fmt, "1", 1.0)
    except (ValueError, TypeError) as error:
        raise ValueError(
            f"fmt {fmt!r} cannot format a number: {error}"
        ) from None
    return fmt


def _parse_color(color: object) -> object:
    if color is None or is_series(color):
        return color
    try:
        mcolors.to_rgba(color)  # type: ignore[arg-type]
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"color must be None, 'series' or a matplotlib colour: {error}"
        ) from None
    return color


@dataclass(frozen=True)
class BarLabelOptions:
    """The keywords of one :func:`label_bars` call, validated."""

    where: Where = "auto"
    total: Total = "auto"
    crowded: Crowded = "rotate"
    decimals: int | None = None
    fmt: Fmt = None
    size: float | str | None = None
    color: object = None


def parse_options(
    *,
    where: str,
    total: object,
    crowded: str,
    decimals: object,
    fmt: object,
    size: float | str | None,
    color: object,
) -> BarLabelOptions:
    """The call's keywords, validated (``ValueError`` names the bad one)."""
    return BarLabelOptions(
        where=_parse_where(where),
        total=_parse_total(total),
        crowded=_parse_crowded(crowded),
        decimals=_parse_decimals(decimals),
        fmt=_parse_fmt(fmt),
        size=size,
        color=_parse_color(color),
    )


# ------------------------------------------------------------ the text
def compose_text(
    scaled: float, scale: TickScale, decimals: int, options: BarLabelOptions
) -> str:
    """The label text for a value already divided by ``scale.factor``."""
    fmt = options.fmt
    fixed = options.decimals is not None
    if callable(fmt):
        return str(fmt(scaled))
    if isinstance(fmt, str):
        return _render_template(
            fmt, number_text(scaled, decimals, fixed=fixed), scaled
        )
    return number_text(
        scaled, decimals, fixed=fixed, prefix=scale.prefix, suffix=scale.suffix
    )
