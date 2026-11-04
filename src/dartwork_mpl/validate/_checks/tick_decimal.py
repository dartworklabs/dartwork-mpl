"""TICK_DECIMAL: excessive, missing, or ambiguous tick decimals.

Decimal consistency is judged among ticks that share a unit suffix, so an
axis that changes unit part-way (``7,500만`` then ``1.25억``) needs one
decimal count per unit, not one per axis. A bare ``0`` carries no unit and
needs no decimals, so ``-1.0M, -0.5M, 0, 0.5M, 1.0M`` and ``0, 0.5, 1.0``
are uniform: the ``.0`` on ``1.0M`` is what the half step needs. Precision
advice uses the rendered (scaled) numbers, so ``0.25k, 0.50k`` is a 0.25
step, not a 250 step.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict

from ...formatting import recommend_tick_decimals
from .._types import Severity, VisualWarning
from ._detail import AXES, Axis, choice, number, wire
from ._registry import register_check, register_fix
from ._tick_utils import iter_view_ticks, split_tick_affixes

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.text import Text

__all__ = ["check_tick_decimal"]

_INTEGER_REL_TOL = 1e-9

# Named in the trailing-zero message and fix: these dm formatters print
# integer ticks without decimals when ``decimals`` is left at None.
_FORMATTER_HINT = (
    "dm.format_axis_si / _millions / _billions / _myriad print integer "
    "ticks without decimals when decimals= is left unset (None)"
)

Reason: TypeAlias = Literal[
    "duplicate", "non_uniform", "trailing_zero", "excess_precision"
]
"""Which TICK_DECIMAL rule fired; the fix handler branches on it."""

_REASONS: tuple[Reason, ...] = (
    "duplicate",
    "non_uniform",
    "trailing_zero",
    "excess_precision",
)


class TickDecimalDuplicateDetail(TypedDict):
    """Rendered precision makes two adjacent tick labels identical."""

    axis: Axis
    axes_index: int
    reason: Literal["duplicate"]
    rendered_decimals: int
    recommended_decimals: int
    duplicate_label: str


class TickDecimalMixedDetail(TypedDict):
    """Ticks sharing a unit suffix use different numbers of decimal places."""

    axis: Axis
    axes_index: int
    reason: Literal["non_uniform"]
    decimal_places: list[int]
    recommended_decimals: int


class TickDecimalTrailingZeroDetail(TypedDict):
    """Every tick sharing a unit is a whole number yet prints decimals."""

    axis: Axis
    axes_index: int
    reason: Literal["trailing_zero"]
    rendered_decimals: int
    recommended_decimals: int


class TickDecimalPrecisionDetail(TypedDict):
    """Tick labels carry more decimals than their rendered step needs."""

    axis: Axis
    axes_index: int
    reason: Literal["excess_precision"]
    rendered_decimals: int
    recommended_decimals: int


@dataclass(frozen=True)
class _TickRow:
    text: str
    suffix: str
    rendered: float
    axis_value: float
    decimals: int


def _axis_value(tick: Text, axis: Axis) -> float | None:
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


def _tick_rows(
    ax: Axes, axis_name: Axis, renderer: RendererBase
) -> list[_TickRow]:
    rows: list[_TickRow] = []
    for tick in iter_view_ticks(ax, axis_name, renderer):
        parts = split_tick_affixes(tick.get_text())
        axis_value = _axis_value(tick, axis_name)
        if parts is None or axis_value is None:
            continue
        _prefix, number_str, suffix = parts
        try:
            rendered_value = float(number_str)
        except ValueError:
            continue
        rows.append(
            _TickRow(
                text=tick.get_text().strip(),
                suffix=suffix.strip(),
                rendered=rendered_value,
                axis_value=axis_value,
                decimals=_decimal_places(number_str),
            )
        )
    return rows


def _is_bare_zero(row: _TickRow) -> bool:
    return row.rendered == 0 and row.decimals == 0 and not row.suffix


def _unit_groups(rows: list[_TickRow]) -> list[list[_TickRow]]:
    """Rows grouped by unit suffix, in first-seen order."""
    groups: dict[str, list[_TickRow]] = {}
    for row in rows:
        groups.setdefault(row.suffix, []).append(row)
    return list(groups.values())


def _axis_warnings(
    rows: list[_TickRow], axis_name: Axis, axes_index: int
) -> VisualWarning | None:
    label = f"{axis_name.upper()}-axis[{axes_index}]"
    texts = [row.text for row in rows]
    recommended = recommend_tick_decimals([row.axis_value for row in rows])

    duplicate = next(
        (left for left, right in pairwise(texts) if left == right), None
    )
    if duplicate is not None:
        return VisualWarning(
            severity=Severity.WARNING,
            check_id="TICK_DECIMAL",
            message=(
                f"{label}: adjacent ticks render as the same string "
                f"({duplicate!r}); increase decimal places"
            ),
            detail=wire(
                TickDecimalDuplicateDetail(
                    axis=axis_name,
                    axes_index=axes_index,
                    reason="duplicate",
                    rendered_decimals=max(row.decimals for row in rows),
                    recommended_decimals=recommended,
                    duplicate_label=duplicate,
                )
            ),
        )

    # A bare "0" is unit-less: it joins no group's decimal count.
    unit_rows = [row for row in rows if not _is_bare_zero(row)]
    groups = [group for group in _unit_groups(unit_rows) if len(group) >= 2]

    for group in groups:
        places = sorted({row.decimals for row in group})
        if len(places) > 1:
            return VisualWarning(
                severity=Severity.WARNING,
                check_id="TICK_DECIMAL",
                message=(
                    f"{label}: non-uniform decimal places in numeric tick "
                    f"labels ({places})"
                ),
                detail=wire(
                    TickDecimalMixedDetail(
                        axis=axis_name,
                        axes_index=axes_index,
                        reason="non_uniform",
                        decimal_places=places,
                        recommended_decimals=recommended,
                    )
                ),
            )

    for group in groups:
        decimals = max(row.decimals for row in group)
        if decimals >= 1 and all(_is_integer(row.rendered) for row in group):
            return VisualWarning(
                severity=Severity.WARNING,
                check_id="TICK_DECIMAL",
                message=(
                    f"{label}: trailing zero in integer tick labels "
                    f"(example {group[0].text!r}); every tick is a whole "
                    f"number, print it without decimals ({_FORMATTER_HINT})"
                ),
                detail=wire(
                    TickDecimalTrailingZeroDetail(
                        axis=axis_name,
                        axes_index=axes_index,
                        reason="trailing_zero",
                        rendered_decimals=decimals,
                        recommended_decimals=0,
                    )
                ),
            )

    for group in groups:
        decimals = max(row.decimals for row in group)
        needed = recommend_tick_decimals([row.rendered for row in group])
        if decimals > needed + 1:
            return VisualWarning(
                severity=Severity.INFO,
                check_id="TICK_DECIMAL",
                message=(
                    f"{label}: excess precision in tick labels "
                    f"({decimals} decimals; {needed} recommended)"
                ),
                detail=wire(
                    TickDecimalPrecisionDetail(
                        axis=axis_name,
                        axes_index=axes_index,
                        reason="excess_precision",
                        rendered_decimals=decimals,
                        recommended_decimals=needed,
                    )
                ),
            )
    return None


@register_check("TICK_DECIMAL", order=55)
def check_tick_decimal(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect tick labels with misleading decimal precision."""
    warnings: list[VisualWarning] = []
    for axes_index, ax in enumerate(fig.axes):
        for axis_name in AXES:
            rows = _tick_rows(ax, axis_name, renderer)
            if len(rows) < 3:
                continue
            warning = _axis_warnings(rows, axis_name, axes_index)
            if warning is not None:
                warnings.append(warning)
    return warnings


@register_fix("TICK_DECIMAL")
def _fix_tick_decimal(warning: VisualWarning) -> list[str]:
    """Formatter suggestions at the recommended precision (defaults: y, 0).

    A trailing-zero warning leads with the dm formatter option.
    """
    axis = choice(warning.detail, "axis", AXES) or "y"
    decimals = int(number(warning.detail, "recommended_decimals", 0))
    fixes = [
        "# Match tick precision to the tick step\n"
        f"ax.{axis}axis.set_major_formatter(mticker.StrMethodFormatter('{{x:.{decimals}f}}'))",
        "# Or let matplotlib choose compact numeric labels\n"
        f"ax.{axis}axis.set_major_formatter(mticker.ScalarFormatter())",
    ]
    if choice(warning.detail, "reason", _REASONS) == "trailing_zero":
        fixes.insert(
            0,
            f"# {_FORMATTER_HINT}\n"
            f"dm.format_axis_si(ax, axis='{axis}')  # not decimals=1",
        )
    return fixes
