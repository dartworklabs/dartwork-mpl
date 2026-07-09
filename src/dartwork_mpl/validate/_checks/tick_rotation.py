"""TICK_ROTATION: unnecessary or missing x-axis tick-label rotation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._registry import register_check
from ._tick_utils import adjacent_bboxes_overlap, iter_view_ticks

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.text import Text

__all__ = ["check_tick_rotation"]

_ROTATION_EPS = 1e-6
_UNROTATED_LABEL_PAD_PX = 4.0


def _is_math_text(text: str) -> bool:
    stripped = text.strip()
    return (
        len(stripped) >= 2
        and stripped.startswith("$")
        and stripped.endswith("$")
    )


def _unrotated_text_width(label: Text, renderer: RendererBase) -> float | None:
    text = label.get_text()
    if not text.strip():
        return None
    try:
        width, _height, _descent = renderer.get_text_width_height_descent(
            text, label.get_fontproperties(), ismath=_is_math_text(text)
        )
    except (RuntimeError, ValueError, TypeError):
        return None
    return float(width)


@register_check("TICK_ROTATION", order=52)
def check_tick_rotation(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect x-axis tick labels that are tilted unnecessarily or missing tilt."""
    warnings: list[VisualWarning] = []

    for axes_index, ax in enumerate(fig.axes):
        ticks = list(iter_view_ticks(ax, "x", renderer))
        if len(ticks) <= 2:
            continue

        try:
            ax_ext = ax.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        if ax_ext.width <= 0:
            continue

        rotations = [abs(float(tick.get_rotation())) for tick in ticks]
        any_rotated = any(rotation > _ROTATION_EPS for rotation in rotations)
        all_horizontal = all(
            rotation <= _ROTATION_EPS for rotation in rotations
        )
        slot_width = ax_ext.width / len(ticks)

        if any_rotated:
            widths = [
                width
                for tick in ticks
                if (width := _unrotated_text_width(tick, renderer)) is not None
            ]
            if widths and max(widths) + _UNROTATED_LABEL_PAD_PX < slot_width:
                warnings.append(
                    VisualWarning(
                        severity=Severity.INFO,
                        check_id="TICK_ROTATION",
                        message=(
                            f"X-axis[{axes_index}]: 회전 불필요, "
                            "rotation=0으로 수평 배치 가능 "
                            f"(max label {max(widths):.1f}px, "
                            f"slot {slot_width:.1f}px)"
                        ),
                        detail={
                            "axis": "x",
                            "axes_index": axes_index,
                            "recommended_rotation": 0,
                            "max_unrotated_width_px": round(max(widths), 2),
                            "slot_width_px": round(slot_width, 2),
                        },
                    )
                )
            continue

        if not all_horizontal:
            continue

        try:
            bboxes = [tick.get_window_extent(renderer) for tick in ticks]
        except BBOX_ERRORS:
            continue
        if adjacent_bboxes_overlap(bboxes, tol_px=2.0):
            warnings.append(
                VisualWarning(
                    severity=Severity.INFO,
                    check_id="TICK_ROTATION",
                    message=(
                        f"X-axis[{axes_index}]: 라벨 겹침 — "
                        "45° 회전 또는 틱 수 축소 권장"
                    ),
                    detail={
                        "axis": "x",
                        "axes_index": axes_index,
                        "recommended_rotation": 45,
                        "tick_count": len(ticks),
                    },
                )
            )

    return warnings
