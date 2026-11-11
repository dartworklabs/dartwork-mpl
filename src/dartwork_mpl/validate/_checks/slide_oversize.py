"""SLIDE_OVERSIZE: slide-preset text shrinks on an oversized root canvas."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from ...style import SLIDE_SCALE, step_pt
from .._types import Severity, VisualWarning
from ._detail import wire
from ._registry import register_check, register_fix

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_slide_oversize"]

# The largest common slide; the skill tells agents its text reads 25 % smaller.
_MAX_WIDTH_IN = 13.33
_MAX_HEIGHT_IN = 7.5
_TOLERANCE = 0.01
# The 16:9 slide the slide presets size their text for.
_SLIDE_CM = (25.4, 14.29)


class SlideOversizeDetail(TypedDict):
    """Root dimensions, the scale that fits them on the slide, and the limits."""

    width_cm: float
    height_cm: float
    scale: float
    max_width_cm: float
    max_height_cm: float
    tolerance: float


@register_check("SLIDE_OVERSIZE", order=96)
def check_slide_oversize(
    fig: Figure, _renderer: RendererBase
) -> list[VisualWarning]:
    """Warn above either slide limit plus 1%, only under a slide preset.

    SubFigures use their shared root canvas. The scale is the one that fits
    the whole figure on the 25.4 x 14.29 cm slide, so a figure that is only
    too tall reports how much its height shrinks the text.
    """
    if step_pt() != SLIDE_SCALE:
        return []
    root = fig.get_figure(root=True)
    width, height = (float(v) for v in root.get_size_inches())
    if width <= _MAX_WIDTH_IN * (
        1 + _TOLERANCE
    ) and height <= _MAX_HEIGHT_IN * (1 + _TOLERANCE):
        return []
    width_cm, height_cm = width * 2.54, height * 2.54
    scale = min(_SLIDE_CM[0] / width_cm, _SLIDE_CM[1] / height_cm)
    return [
        VisualWarning(
            severity=Severity.WARNING,
            check_id="SLIDE_OVERSIZE",
            message=(
                f"Figure is {width_cm:.2f} x {height_cm:.2f} cm; on a 25.4 x "
                f"14.29 cm slide its text is shown at about {scale:.2f}x its size, so draw "
                'it at the slide\'s size instead (dm.figsize_for("full_slide") '
                'for the whole slide, dm.figsize_for("slide") under a slide title).'
            ),
            detail=wire(
                SlideOversizeDetail(
                    width_cm=width_cm,
                    height_cm=height_cm,
                    scale=scale,
                    max_width_cm=_MAX_WIDTH_IN * 2.54,
                    max_height_cm=_MAX_HEIGHT_IN * 2.54,
                    tolerance=_TOLERANCE,
                )
            ),
        )
    ]


@register_fix("SLIDE_OVERSIZE")
def _fix_slide_oversize(_warning: VisualWarning) -> list[str]:
    """Suggest redrawing at the whole-slide or under-title canvas size."""
    return [
        'fig.set_size_inches(dm.figsize_for("full_slide"))\ndm.simple_layout(fig)',
        "# Under a slide title instead:\n"
        'fig.set_size_inches(dm.figsize_for("slide"))\ndm.simple_layout(fig)',
    ]
