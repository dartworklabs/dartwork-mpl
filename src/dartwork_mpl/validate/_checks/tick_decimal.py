"""TICK_DECIMAL: excessive, missing, or ambiguous tick decimals."""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, Literal

from ...formatting import recommend_tick_decimals
from .._types import Severity, VisualWarning
from ._registry import register_check
from ._tick_utils import iter_view_ticks, split_tick_affixes

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.text import Text

__all__ = ["check_tick_decimal"]

_INTEGER_REL_TOL = 1e-9


def _axis_value(tick: Text, axis: Literal["x", "y"]) -> float | None:
    try:
        x_value, y_value = tick.get_position()
        return float(x_value if axis == "x" else y_value)
    except (TypeError, ValueError):
        return None


def _decimal_places(number_str: str) -> int:
    mantissa = number_str.lower().split("e", 1)[0]
    if "." not in mantissa:
        return 0
    return len(mantissa.split(".", 1)[1])


def _is_integer(value: float) -> bool:
    nearest = round(value)
    return abs(value - nearest) <= _INTEGER_REL_TOL * max(1.0, abs(value))


@register_check("TICK_DECIMAL", order=55)
def check_tick_decimal(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect tick labels with misleading decimal precision."""
    warnings: list[VisualWarning] = []

    for axes_index, ax in enumerate(fig.axes):
        for axis_name in ("x", "y"):
            tick_rows: list[tuple[str, float, float, int]] = []
            for tick in iter_view_ticks(ax, axis_name, renderer):
                parts = split_tick_affixes(tick.get_text())
                axis_value = _axis_value(tick, axis_name)
                if parts is None or axis_value is None:
                    continue
                _prefix, number_str, _suffix = parts
                try:
                    rendered_value = float(number_str)
                except ValueError:
                    continue
                tick_rows.append(
                    (
                        tick.get_text().strip(),
                        rendered_value,
                        axis_value,
                        _decimal_places(number_str),
                    )
                )

            if len(tick_rows) < 3:
                continue

            rendered_texts = [row[0] for row in tick_rows]
            rendered_values = [row[1] for row in tick_rows]
            axis_values = [row[2] for row in tick_rows]
            decimal_places = [row[3] for row in tick_rows]
            rendered_decimals = max(row[3] for row in tick_rows)
            recommended_decimals = recommend_tick_decimals(axis_values)

            duplicate = next(
                (
                    (left, right)
                    for left, right in pairwise(rendered_texts)
                    if left == right
                ),
                None,
            )
            if duplicate is not None:
                warnings.append(
                    VisualWarning(
                        severity=Severity.WARNING,
                        check_id="TICK_DECIMAL",
                        message=(
                            f"{axis_name.upper()}-axis[{axes_index}]: "
                            "adjacent ticks render as the same string "
                            f"({duplicate[0]!r}); increase decimal places"
                        ),
                        detail={
                            "axis": axis_name,
                            "axes_index": axes_index,
                            "rendered_decimals": rendered_decimals,
                            "recommended_decimals": recommended_decimals,
                            "duplicate_label": duplicate[0],
                        },
                    )
                )
                continue

            unique_decimal_places = sorted(set(decimal_places))
            if len(unique_decimal_places) > 1:
                warnings.append(
                    VisualWarning(
                        severity=Severity.WARNING,
                        check_id="TICK_DECIMAL",
                        message=(
                            f"{axis_name.upper()}-axis[{axes_index}]: "
                            "non-uniform decimal places in numeric tick labels "
                            f"({unique_decimal_places})"
                        ),
                        detail={
                            "axis": axis_name,
                            "axes_index": axes_index,
                            "decimal_places": unique_decimal_places,
                            "recommended_decimals": recommended_decimals,
                        },
                    )
                )
                continue

            if all(_is_integer(value) for value in rendered_values) and (
                rendered_decimals >= 1
            ):
                warnings.append(
                    VisualWarning(
                        severity=Severity.INFO,
                        check_id="TICK_DECIMAL",
                        message=(
                            f"{axis_name.upper()}-axis[{axes_index}]: "
                            "trailing zero in integer tick labels "
                            f"(example {rendered_texts[0]!r})"
                        ),
                        detail={
                            "axis": axis_name,
                            "axes_index": axes_index,
                            "rendered_decimals": rendered_decimals,
                            "recommended_decimals": 0,
                        },
                    )
                )
                continue

            if rendered_decimals > recommended_decimals + 1:
                warnings.append(
                    VisualWarning(
                        severity=Severity.INFO,
                        check_id="TICK_DECIMAL",
                        message=(
                            f"{axis_name.upper()}-axis[{axes_index}]: "
                            "excess precision in tick labels "
                            f"({rendered_decimals} decimals; "
                            f"{recommended_decimals} recommended)"
                        ),
                        detail={
                            "axis": axis_name,
                            "axes_index": axes_index,
                            "rendered_decimals": rendered_decimals,
                            "recommended_decimals": recommended_decimals,
                        },
                    )
                )

    return warnings
