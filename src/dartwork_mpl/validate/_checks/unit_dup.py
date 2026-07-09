"""UNIT_DUP: duplicated unit markers in axis labels and tick labels."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from .._types import Severity, VisualWarning
from ._registry import register_check
from ._tick_utils import iter_view_ticks, split_tick_affixes

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_unit_dup"]

_AXIS_UNIT_RE = re.compile(r"[([]([^)\]]{1,16})[)\]]\s*$")
_COMMON_AFFIX_THRESHOLD = 0.60


def _compact_token(text: str) -> str:
    return "".join(text.lower().split())


def _axis_unit(label: str) -> str | None:
    match = _AXIS_UNIT_RE.search(label)
    if match is None:
        return None
    unit = match.group(1).strip()
    return unit or None


def _common_affix(
    parts: list[tuple[str, str, str]], kind: Literal["prefix", "suffix"]
) -> str | None:
    index = 0 if kind == "prefix" else 2
    counts: dict[str, tuple[str, int]] = {}
    for part in parts:
        affix = part[index]
        if not affix.strip():
            continue
        key = _compact_token(affix)
        if not key:
            continue
        first, count = counts.get(key, (affix, 0))
        counts[key] = (first, count + 1)
    if not counts:
        return None

    affix, count = max(counts.values(), key=lambda item: item[1])
    if count / len(parts) < _COMMON_AFFIX_THRESHOLD:
        return None
    return affix


def _affix_overlaps_unit(affix: str, unit: str) -> bool:
    affix_norm = _compact_token(affix)
    unit_norm = _compact_token(unit)
    if not affix_norm or not unit_norm:
        return False
    return affix_norm in unit_norm or unit_norm in affix_norm


@register_check("UNIT_DUP", order=25)
def check_unit_dup(fig: Figure, renderer: RendererBase) -> list[VisualWarning]:
    """Detect duplicated axis unit text and tick-label affixes."""
    warnings: list[VisualWarning] = []

    for axes_index, ax in enumerate(fig.axes):
        axis_specs: tuple[tuple[Literal["x", "y"], str], ...] = (
            ("x", ax.get_xlabel()),
            ("y", ax.get_ylabel()),
        )
        for axis_name, axis_label in axis_specs:
            label_unit = _axis_unit(axis_label)
            if label_unit is None:
                continue

            tick_parts = [
                parts
                for tick in iter_view_ticks(ax, axis_name, renderer)
                if (parts := split_tick_affixes(tick.get_text())) is not None
            ]
            if not tick_parts:
                continue

            candidates: list[tuple[Literal["suffix", "prefix"], str]] = []
            for kind in ("suffix", "prefix"):
                affix = _common_affix(tick_parts, kind)
                if affix is not None:
                    candidates.append((kind, affix))
            if not candidates:
                continue

            selected_kind, selected_affix = candidates[0]
            severity = Severity.INFO
            message = (
                f"{axis_name.upper()}-axis[{axes_index}]: "
                f"축 라벨이 단위를 선언했는데 틱에 별도 "
                f"{'접미' if selected_kind == 'suffix' else '접두'} 존재 "
                f"(label unit={label_unit!r}, tick {selected_kind}="
                f"{selected_affix!r}). Fix: 단위는 축 라벨에만; "
                "틱은 순수 숫자 포맷터"
            )
            for kind, affix in candidates:
                if _affix_overlaps_unit(affix, label_unit):
                    selected_kind, selected_affix = kind, affix
                    severity = Severity.WARNING
                    message = (
                        f"{axis_name.upper()}-axis[{axes_index}]: "
                        "축 라벨과 틱 라벨에 단위 중복 "
                        f"(label unit={label_unit!r}, tick {kind}="
                        f"{affix!r}). Fix: 단위는 축 라벨에만; "
                        "틱은 순수 숫자 포맷터"
                    )
                    break

            warnings.append(
                VisualWarning(
                    severity=severity,
                    check_id="UNIT_DUP",
                    message=message,
                    detail={
                        "axis": axis_name,
                        "axes_index": axes_index,
                        "label_unit": label_unit,
                        "tick_affix": selected_affix,
                        "affix_kind": selected_kind,
                    },
                )
            )

    return warnings
