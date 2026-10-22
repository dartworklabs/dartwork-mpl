"""VALUE_LABEL_DECIMAL: whole-number value labels printed with decimals.

The value-label analogue of TICK_DECIMAL's trailing-zero rule. When every
numeric label inside an axes (bar labels, ``ax.text`` / ``annotate_value``
numbers) is a whole number yet some print a trailing ``.0``, the decimals
carry no information: ``120.0, 135.0`` should read ``120, 135``. Labels
whose values include a real fraction (``88.9%, 90.0%``) are left alone.

Only short single-line labels count, so prose that happens to contain a
number ("24 months") does not vote; unit and percent suffixes are parsed
off the number (``1,200 MWh``, ``45.0%``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from .._types import Severity, VisualWarning
from ._detail import number, wire
from ._registry import register_check, register_fix
from ._tick_utils import split_tick_affixes
from .tick_decimal import _decimal_places, _is_integer

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_value_label_decimal"]

# Longest prefix / suffix (after stripping) a value label may carry —
# "Total: ", "Median = ", " MWh". Longer affixes are prose, not labels.
_MAX_AFFIX_CHARS = 12


class ValueLabelDecimalDetail(TypedDict):
    """Whole-number value labels in one axes that print trailing zeros."""

    axes_index: int
    labels: int
    with_decimals: int
    example: str


def _value_label(text: str) -> tuple[float, int] | None:
    """``(value, decimal places)`` when ``text`` is a short numeric label."""
    stripped = text.strip()
    if not stripped or "\n" in stripped:
        return None
    parts = split_tick_affixes(stripped)
    if parts is None:
        return None
    prefix, number_str, suffix = parts
    if len(prefix.strip()) > _MAX_AFFIX_CHARS:
        return None
    if len(suffix.strip()) > _MAX_AFFIX_CHARS:
        return None
    # A letter glued to the number ("v2.0", "x1.5") is a token, not a value.
    if prefix and prefix[-1].isalpha():
        return None
    if "e" in number_str.lower():
        return None
    return float(number_str), _decimal_places(number_str)


@register_check("VALUE_LABEL_DECIMAL", order=56)
def check_value_label_decimal(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Flag axes whose whole-number value labels print trailing zeros."""
    warnings: list[VisualWarning] = []
    for axes_index, ax in enumerate(fig.axes):
        labels: list[tuple[str, float, int]] = []
        for artist in ax.texts:
            if not artist.get_visible():
                continue
            text = artist.get_text()
            parsed = _value_label(text)
            if parsed is not None:
                labels.append((text.strip(), *parsed))
        if len(labels) < 2:
            continue
        if not all(_is_integer(value) for _text, value, _places in labels):
            continue
        with_decimals = [text for text, _value, places in labels if places]
        if not with_decimals:
            continue
        warnings.append(
            VisualWarning(
                severity=Severity.WARNING,
                check_id="VALUE_LABEL_DECIMAL",
                message=(
                    f"Axes[{axes_index}]: whole-number value labels print "
                    f"trailing zeros (example {with_decimals[0]!r}, "
                    f"{len(with_decimals)} of {len(labels)} labels); "
                    "format them without decimals"
                ),
                detail=wire(
                    ValueLabelDecimalDetail(
                        axes_index=axes_index,
                        labels=len(labels),
                        with_decimals=len(with_decimals),
                        example=with_decimals[0],
                    )
                ),
            )
        )
    return warnings


@register_fix("VALUE_LABEL_DECIMAL")
def _fix_value_label_decimal(warning: VisualWarning) -> list[str]:
    """Whole-number label formats; names how many labels print decimals."""
    count = int(number(warning.detail, "with_decimals", 0))
    which = f"{count} labels print" if count else "labels print"
    return [
        f"# Every value is a whole number but {which} decimals: drop them\n"
        "ax.bar_label(bars, fmt='{:,.0f}')",
        "# Or in a manual label\nax.text(x, y, f'{value:,.0f}')",
    ]
