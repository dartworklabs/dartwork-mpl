"""PRESET_OVERRIDE: grid, spines or backgrounds that differ from the active preset.

The active dartwork preset owns an Axes' grid, spines and background and the
figure background. A difference from it is usually an unrequested restyle by
the code that drew the figure, but this check cannot see the request, so the
finding is INFO: keep the change only if the user asked for it.

Axes whose look legitimately departs from the preset are not inspected:
hidden Axes and Axes with the axis turned off, non-rectilinear projections
(polar, 3-D), colorbar Axes, pie and donut Axes (``Axes.pie`` turns the frame
off itself) and the second and later members of a twin group (``twinx`` /
``twiny``: the twin draws its own spine and no background). Child Axes from
``ax.inset_axes`` or ``secondary_xaxis`` are not in ``fig.axes`` and are never
inspected. A background that is not drawn (invisible patch or frame off) is
not compared.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal, TypeAlias, TypedDict, cast

import matplotlib as mpl
import matplotlib.colors as mcolors
from matplotlib.patches import Wedge

from ..._figure_geometry import twin_partners
from ...style import active_preset_rcparams
from .._types import Severity, VisualWarning
from ._detail import AXES, SIDES, Axis, Side, choice, wire
from ._registry import register_check, register_fix

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.typing import RcKeyType

__all__ = ["check_preset_override"]

Property: TypeAlias = Literal[
    "grid.x",
    "grid.y",
    "spines.left",
    "spines.right",
    "spines.bottom",
    "spines.top",
    "axes.facecolor",
    "figure.facecolor",
]
"""The preset-owned property a finding reports on."""

_PROPERTIES: tuple[Property, ...] = (
    "grid.x",
    "grid.y",
    "spines.left",
    "spines.right",
    "spines.bottom",
    "spines.top",
    "axes.facecolor",
    "figure.facecolor",
)

_GRID_PROPERTY: dict[Axis, Property] = {"x": "grid.x", "y": "grid.y"}
_SPINE_PROPERTY: dict[Side, Property] = {
    "left": "spines.left",
    "right": "spines.right",
    "bottom": "spines.bottom",
    "top": "spines.top",
}

# Up to one 8-bit channel step apart counts as the same colour.
_RGBA_TOL = 1.5 / 255


class PresetOverrideAxesDetail(TypedDict):
    """Axes ``axes_index`` shows ``figure`` where the preset sets ``preset``."""

    axes_index: int
    property: Property
    preset: bool | str
    figure: bool | str


class PresetOverrideFigureDetail(TypedDict):
    """The figure background differs from the preset; it belongs to no Axes."""

    axes_index: None
    property: Literal["figure.facecolor"]
    preset: str
    figure: str


def _preset_value(preset: Mapping[str, object], key: str) -> object:
    """The preset's value for ``key``; an undeclared key is the live rcParam."""
    return (
        preset[key] if key in preset else mpl.rcParams[cast("RcKeyType", key)]
    )


def _is_twin(ax: Axes, fig_axes: list[Axes]) -> bool:
    """Whether an earlier Axes of this figure is twinned with ``ax``.

    ``twinx`` / ``twiny`` partners share the box of the Axes they came from;
    ``sharex`` / ``sharey`` panels are not twins.
    """
    if ax not in fig_axes:
        return False
    earlier = fig_axes[: fig_axes.index(ax)]
    return any(other in earlier for other in twin_partners(ax))


def _is_inspected(ax: Axes, fig_axes: list[Axes]) -> bool:
    """Whether ``ax`` is an ordinary data Axes whose look the preset owns."""
    return (
        ax.get_visible()
        and ax.axison
        and ax.name == "rectilinear"
        and getattr(ax, "_colorbar", None) is None
        and not hasattr(ax, "_colorbar_info")
        and not any(isinstance(patch, Wedge) for patch in ax.patches)
        and not _is_twin(ax, fig_axes)
    )


def _hex(rgba: tuple[float, float, float, float]) -> str:
    """``#rrggbb``, or ``#rrggbbaa`` when the colour is not opaque."""
    return mcolors.to_hex(rgba, keep_alpha=rgba[3] < 1.0)


def _color_differs(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> bool:
    """Whether two RGBA colours are more than one 8-bit step apart."""
    return any(abs(a - b) > _RGBA_TOL for a, b in zip(left, right, strict=True))


def _preset_draws_grid(preset: Mapping[str, object], axis: Axis) -> bool:
    """Whether the preset draws major gridlines on ``axis``."""
    return (
        bool(_preset_value(preset, "axes.grid"))
        and _preset_value(preset, "axes.grid.axis") in ("both", axis)
        and _preset_value(preset, "axes.grid.which") in ("major", "both")
    )


def _axes_finding(
    axes_index: int,
    prop: Property,
    preset: bool | str,
    figure: bool | str,
    message: str,
) -> VisualWarning:
    """One INFO finding for one Axes property."""
    return VisualWarning(
        severity=Severity.INFO,
        check_id="PRESET_OVERRIDE",
        message=f"Axes {axes_index}: {message}",
        detail=wire(
            PresetOverrideAxesDetail(
                axes_index=axes_index,
                property=prop,
                preset=preset,
                figure=figure,
            )
        ),
    )


def _grid_findings(
    ax: Axes, axes_index: int, preset: Mapping[str, object]
) -> list[VisualWarning]:
    """Major gridlines on a visible axis that the preset does (not) draw."""
    findings: list[VisualWarning] = []
    for axis_name in AXES:
        axis = ax.xaxis if axis_name == "x" else ax.yaxis
        ticks = axis.get_major_ticks()
        # No ticks or a hidden axis draws no grid either way.
        if not axis.get_visible() or not ticks:
            continue
        shown = any(tick.gridline.get_visible() for tick in ticks)
        expected = _preset_draws_grid(preset, axis_name)
        if shown == expected:
            continue
        message = (
            f"{axis_name} grid lines are on but the preset draws none; "
            "keep them only if the user asked for a grid."
            if shown
            else f"{axis_name} grid lines are off but the preset draws them; "
            "keep them off only if the user asked for no grid."
        )
        findings.append(
            _axes_finding(
                axes_index, _GRID_PROPERTY[axis_name], expected, shown, message
            )
        )
    return findings


def _spine_findings(
    ax: Axes, axes_index: int, preset: Mapping[str, object]
) -> list[VisualWarning]:
    """Spines shown or hidden against ``axes.spines.<side>``."""
    findings: list[VisualWarning] = []
    for side in SIDES:
        if side not in ax.spines:
            continue
        # Axes.draw skips every spine when the frame is off.
        shown = ax.get_frame_on() and ax.spines[side].get_visible()
        expected = bool(_preset_value(preset, f"axes.spines.{side}"))
        if shown == expected:
            continue
        message = (
            f"the {side} spine is shown but the preset hides it; "
            "show it only if the user asked."
            if shown
            else f"the {side} spine is hidden but the preset shows it; "
            "hide it only if the user asked."
        )
        findings.append(
            _axes_finding(
                axes_index, _SPINE_PROPERTY[side], expected, shown, message
            )
        )
    return findings


def _axes_facecolor_findings(
    ax: Axes, axes_index: int, preset: Mapping[str, object]
) -> list[VisualWarning]:
    """A drawn Axes background that differs from ``axes.facecolor``."""
    if not (ax.get_frame_on() and ax.patch.get_visible()):
        return []
    shown = mcolors.to_rgba(ax.patch.get_facecolor())
    expected = mcolors.to_rgba(_preset_value(preset, "axes.facecolor"))  # type: ignore[arg-type]
    if not _color_differs(shown, expected):
        return []
    message = (
        f"the axes background is {_hex(shown)} but the preset uses "
        f"{_hex(expected)}; change it only if the user asked."
    )
    return [
        _axes_finding(
            axes_index, "axes.facecolor", _hex(expected), _hex(shown), message
        )
    ]


def _figure_facecolor_findings(
    fig: Figure, preset: Mapping[str, object]
) -> list[VisualWarning]:
    """A drawn figure background that differs from ``figure.facecolor``."""
    if not fig.patch.get_visible():
        return []
    shown = mcolors.to_rgba(fig.patch.get_facecolor())
    expected = mcolors.to_rgba(_preset_value(preset, "figure.facecolor"))  # type: ignore[arg-type]
    if not _color_differs(shown, expected):
        return []
    return [
        VisualWarning(
            severity=Severity.INFO,
            check_id="PRESET_OVERRIDE",
            message=(
                f"Figure: the figure background is {_hex(shown)} but the "
                f"preset uses {_hex(expected)}; change it only if the user "
                "asked."
            ),
            detail=wire(
                PresetOverrideFigureDetail(
                    axes_index=None,
                    property="figure.facecolor",
                    preset=_hex(expected),
                    figure=_hex(shown),
                )
            ),
        )
    ]


@register_check("PRESET_OVERRIDE", order=95)
def check_preset_override(
    fig: Figure, _renderer: RendererBase | None = None
) -> list[VisualWarning]:
    """Report grid, spine and background settings that differ from the preset.

    Compares each inspected Axes' major gridlines, spine visibility and drawn
    background, and the figure background, with the active dartwork preset
    (:func:`dartwork_mpl.style.active_preset_rcparams`; a key the preset does
    not declare falls back to the live rcParam). Reports nothing when no
    dartwork preset is active. ``_renderer`` is accepted for signature parity
    with the other checks; the state is read from the artists directly.
    """
    preset = active_preset_rcparams()
    if not preset:
        return []

    warnings: list[VisualWarning] = []
    fig_axes = list(fig.axes)
    for axes_index, ax in enumerate(fig_axes):
        if not _is_inspected(ax, fig_axes):
            continue
        warnings.extend(_grid_findings(ax, axes_index, preset))
        warnings.extend(_spine_findings(ax, axes_index, preset))
        warnings.extend(_axes_facecolor_findings(ax, axes_index, preset))
    warnings.extend(_figure_facecolor_findings(fig, preset))
    return warnings


@register_fix("PRESET_OVERRIDE")
def _fix_preset_override(warning: VisualWarning) -> list[str]:
    """Leave the property to the preset unless the user asked for the change."""
    prop = choice(warning.detail, "property", _PROPERTIES)
    preset = warning.detail.get("preset")
    suggestions = [
        "# Unless the user asked for this change, delete the call that made "
        "it;\n# the preset owns grid, spines and backgrounds"
    ]
    restore = "# Or restore the preset value explicitly\n"
    if prop in ("grid.x", "grid.y") and isinstance(preset, bool):
        suggestions.append(restore + f"ax.grid({preset}, axis={prop[-1]!r})")
    elif prop is not None and prop.startswith("spines."):
        if isinstance(preset, bool):
            side = prop.split(".", 1)[1]
            suggestions.append(
                restore + f"ax.spines[{side!r}].set_visible({preset})"
            )
    elif prop is not None and isinstance(preset, str):
        owner = "fig" if prop == "figure.facecolor" else "ax"
        suggestions.append(restore + f"{owner}.set_facecolor({preset!r})")
    return suggestions
