"""The keywords of a :func:`~._bar_labels.label_bars` call and the text they make.

* **Options.** :func:`parse_options` validates the call's keywords into a
  frozen :class:`BarLabelOptions`: ``where``, ``total`` and ``crowded`` are
  strict, ``decimals`` is ``None`` or an integer >= 0, ``fmt`` a ``{}``
  template or a callable, ``color`` ``None``, ``"series"`` or a matplotlib
  colour, ``sign`` ``"-"`` or ``"+"``.
* **Text.** :func:`compose_text` writes one label's text from its value in
  the axis's tick unit: the number with the label's decimals and the ticks'
  prefix, suffix and zero rule, or the ``fmt`` template around the number
  (a field with a format spec formats the value itself), or what the
  ``fmt`` callable returns. A non-zero value that the label rule's decimals
  round to zero prints the bound it lies within (``<0.1M``, ``>-0.1M`` with
  matplotlib's minus), unless the call fixed the precision. Under
  ``sign="+"`` a positive number that does not print as zero takes ``+``
  where a negative one takes the minus.
"""

from __future__ import annotations

import math
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
    "Sign",
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
# The sign field of Python's format spec: "-" signs negatives only, "+"
# positives too.
Sign: TypeAlias = Literal["-", "+"]
# Why the layout hid a label where it would overlap: another series took
# its bar index ("turn"), there was no room for it ("room"), a legend
# covers it ("legend"), or, beyond the limit its bar runs past, it would
# cover other text: tick labels, an axis label, a title ("text").
HiddenFor: TypeAlias = Literal["turn", "room", "legend", "text"]


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


def _parse_sign(sign: object) -> Sign:
    match sign:
        case "-" | "+":
            return sign
        case _:
            raise ValueError(f"sign must be '-' or '+' (got {sign!r})")


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
    sign: Sign = "-"


def parse_options(
    *,
    where: str,
    total: object,
    crowded: str,
    decimals: object,
    fmt: object,
    size: float | str | None,
    color: object,
    sign: object = "-",
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
        sign=_parse_sign(sign),
    )


# ------------------------------------------------------------ the text
def _caller_writes_precision(options: BarLabelOptions) -> bool:
    """Whether the call fixed how the number prints.

    ``decimals=``, a ``fmt`` callable, or a ``fmt`` template whose field
    carries a format spec or conversion (``"{:.3f} mn"``). A plain ``{}``
    template takes the number the label rule wrote.
    """
    fmt = options.fmt
    if options.decimals is not None or callable(fmt):
        return True
    if isinstance(fmt, str):
        return any(
            spec or conversion
            for _, name, spec, conversion in _template_fields(fmt)
            if name is not None
        )
    return False


def _rounds_to_zero(value: float, decimals: int) -> bool:
    """A finite non-zero ``value`` that prints as zero at ``decimals``."""
    if value == 0 or not math.isfinite(value):
        return False
    return float(format(abs(value), f".{decimals}f")) == 0


def _bound_text(
    scaled: float, scale: TickScale, decimals: int, options: BarLabelOptions
) -> str:
    """The bound a value rounding to zero lies within: one last place.

    ``<0.1M`` for 0.03M at one decimal, ``>-0.1M`` for -0.04M (matplotlib's
    minus: U+2212 unless ``axes.unicode_minus`` is off), ``<1M`` at none;
    the ticks' prefix and suffix as for any other value (``<$0.1``,
    ``<0.1€``), or the ``fmt`` template around the signed bound
    (``"${}B"``: ``>$-0.1B``).
    """
    step = 10.0**-decimals
    bound = step if scaled > 0 else -step
    relation = "<" if scaled > 0 else ">"
    if isinstance(options.fmt, str):
        number = number_text(bound, decimals)
        return relation + _render_template(options.fmt, number, bound)
    return relation + number_text(
        bound, decimals, prefix=scale.prefix, suffix=scale.suffix
    )


def compose_text(
    scaled: float, scale: TickScale, decimals: int, options: BarLabelOptions
) -> str:
    """The label text for a value already divided by ``scale.factor``.

    ``decimals`` is fixed (a zero prints ``0.00``, not ``0``) when the call
    fixed it. A zero keeps the ticks' prefix and suffix when theirs does
    (``$0``); a ``fmt`` template supplies its own. A non-zero value that
    rounds to zero under the label rule prints the bound it lies within
    (``<0.1M``, ``>-0.1M``), never ``0``, and takes no ``+`` (the bound
    already says which side); a precision the call fixed
    (:func:`_caller_writes_precision`) prints as asked. Under ``sign="+"``
    a positive value that does not print as zero starts with ``+``
    (``+30``, ``+$800``), and so does a template's ``{}``; a field with a
    format spec and a callable write their own sign.
    """
    fmt = options.fmt
    fixed = options.decimals is not None
    if callable(fmt):
        return str(fmt(scaled))
    if not _caller_writes_precision(options) and _rounds_to_zero(
        scaled, decimals
    ):
        return _bound_text(scaled, scale, decimals, options)
    plus = (
        "+"
        if options.sign == "+" and _prints_positive(scaled, decimals)
        else ""
    )
    if isinstance(fmt, str):
        return _render_template(
            fmt, plus + number_text(scaled, decimals, fixed=fixed), scaled
        )
    return plus + number_text(
        scaled,
        decimals,
        fixed=fixed,
        prefix=scale.prefix,
        suffix=scale.suffix,
        zero=scale.zero,
    )


def _prints_positive(value: float, decimals: int) -> bool:
    """Whether ``value`` is positive at ``decimals`` places (not ``0``)."""
    return value > 0 and float(format(value, f".{decimals}f")) != 0
