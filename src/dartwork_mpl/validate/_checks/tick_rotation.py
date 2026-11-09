"""TICK_ROTATION: unnecessary or missing x-axis tick-label rotation.

A turn is unneeded where the labels, flat, would stand half an em apart
(``_FLAT_CLEARANCE_EM``) and each fits its slot, as the warning's detail
says:

- every neighbouring pair: their ticks' distance less their two unturned
  half widths, the gaps the flat labels draw. ``dm.simple_layout`` turns
  bottom labels closer than half an em, so it keeps such a row flat;
- the widest label plus half an em within the axis width over the label
  count. A long name that overruns its share stays turned though short
  neighbours leave its pairs room ('North America' among 'EMEA', 'LATAM',
  'APAC' and 'MEA' turned by hand on a 9 cm column).

(It compared the widest label plus 4 px with the slot alone, wider than
the ticks' spacing on a bar axis, and so called unneeded the layout's own
turns. Then the closest two ticks less the widest label, which on uneven
ticks set a long name far from the rest against the closest pair.)
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, Literal, TypedDict

from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import number, wire
from ._registry import register_check, register_fix
from ._tick_utils import adjacent_bboxes_overlap, iter_view_ticks

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.text import Text

__all__ = ["check_tick_rotation"]

_ROTATION_EPS = 1e-6
# Room (ems of the labels) flat neighbours need for a turn to be unneeded:
# the layout's own target (``layout._fit_labels._TARGET_EM``), which turns
# bottom labels closer than this. Closer, two names read as one.
_FLAT_CLEARANCE_EM = 0.5
# Slack (display px) under which a gap still counts as the clearance, as
# the layout allows (``_TOUCH_PX``).
_SLACK_PX = 0.5


class TickRotationUnneededDetail(TypedDict):
    """Rotated x tick labels would fit their slots unrotated."""

    axis: Literal["x"]
    axes_index: int
    recommended_rotation: Literal[0]
    max_unrotated_width_px: float
    slot_width_px: float


class TickRotationNeededDetail(TypedDict):
    """Unrotated x tick labels overlap their neighbours."""

    axis: Literal["x"]
    axes_index: int
    recommended_rotation: Literal[45]
    tick_count: int


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


def _flat_room(
    ax: Axes, ticks: list[Text], renderer: RendererBase
) -> float | None:
    """The room (px) neighbouring labels would at least leave were they
    flat and centred on their ticks: per row (bottom, top), the least over
    neighbouring pairs of their ticks' distance less their two unturned
    half widths. These are the gaps the flat labels draw, which the layout
    turns below half an em. ``None`` when no row has two measurable
    labels."""
    bottom = {id(tick.label1) for tick in ax.xaxis.get_major_ticks()}
    least: float | None = None
    for side in (True, False):
        row: list[tuple[float, float]] = []
        for label in ticks:
            if (id(label) in bottom) is not side:
                continue
            width = _unrotated_text_width(label, renderer)
            if width is None:
                continue
            centre = label.get_transform().transform(label.get_position())[0]
            row.append((float(centre), width))
        for (left, w_left), (right, w_right) in pairwise(sorted(row)):
            room = right - left - (w_left + w_right) / 2
            least = room if least is None else min(least, room)
    return least


@register_check("TICK_ROTATION", order=52)
def check_tick_rotation(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect x-axis tick labels that are tilted unnecessarily or missing tilt."""
    warnings: list[VisualWarning] = []

    for axes_index, ax in enumerate(fig.axes):
        # A row of x labels under a straight axis: not a polar theta ring
        # or a 3D axis.
        if getattr(ax, "name", None) != "rectilinear":
            continue
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
            room = _flat_room(ax, ticks, renderer)
            needed = (
                _FLAT_CLEARANCE_EM
                * max(float(tick.get_fontsize()) for tick in ticks)
                * fig.dpi
                / 72.0
            )
            if (
                widths
                and room is not None
                and room >= needed - _SLACK_PX
                and max(widths) + needed <= slot_width + _SLACK_PX
            ):
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
                        detail=wire(
                            TickRotationUnneededDetail(
                                axis="x",
                                axes_index=axes_index,
                                recommended_rotation=0,
                                max_unrotated_width_px=round(max(widths), 2),
                                slot_width_px=round(slot_width, 2),
                            )
                        ),
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
                        f"X-axis[{axes_index}]: 라벨 겹침 — 날짜면 "
                        "dm.format_axis_dates(ax, dates), 아니면 눈금 수 "
                        "축소, 45° 회전은 마지막 수단"
                    ),
                    detail=wire(
                        TickRotationNeededDetail(
                            axis="x",
                            axes_index=axes_index,
                            recommended_rotation=45,
                            tick_count=len(ticks),
                        )
                    ),
                )
            )

    return warnings


@register_fix("TICK_ROTATION")
def _fix_tick_rotation(warning: VisualWarning) -> list[str]:
    """Suggest the fix for the warning's direction.

    Rotated labels that fit flat: rotate back to the recommended angle (0).
    Flat labels that overlap: date labels first (the library's date words,
    thinned by ``dm.simple_layout``), then fewer ticks, rotation last.
    """
    rotation = number(warning.detail, "recommended_rotation", 45)
    rotate = (
        "# Adjust x tick label rotation\n"
        f"dm.rotate_tick_labels(ax, axis='x', rotation={rotation})"
    )
    if rotation == 0:
        return [rotate]
    return [
        "# Dates under bars: the library's date words, thinned to fit\n"
        "dm.format_axis_dates(ax, dates)",
        "# Other categories: fewer ticks\n"
        "ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=6))",
        "# Last resort: rotate\n" + rotate.split("\n", 1)[1],
    ]
