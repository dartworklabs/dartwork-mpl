"""TICK_OVERLAP: neighbouring tick labels of one axis drawn on top of each other.

Rectilinear Axes only (a polar or 3D axis has no line to take neighbours
along). Every drawn, non-empty tick label, major or minor, of a visible
Axes is the rectangle its own text
occupies, turned with the label, so two 45 degree labels whose upright
boxes cross while their text does not are not reported. Neighbours are
taken in order along the axis, on each side separately (bottom and top
labels of an x axis, left and right of a y axis). Two labels collide when
they overlap by more than half a pixel across the thinner direction of
their overlap (a separating-axis test); labels that only touch pass. The
measure is ``_figure_geometry.tick_label_overlaps``, which the layout also
uses to check that a fitting step made nothing worse.

``dm.simple_layout`` wraps and then turns crowded bottom tick labels it
may change (``layout/_fit_labels.py``); what this check reports after a
layout is what is left: labels you rotated, wrapped or aligned yourself,
labels on a vertical axis, and labels too many or too long to clear even
turned. The fixes never make text smaller. Labels you turned get the
layout's choice first (drop the rotation, lay out again); unturned ones
the layout; then the author's choices: a horizontal bar chart (many or
long category names), a wider canvas, a taller one for crowded rows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from ..._figure_geometry import tick_label_overlaps
from .._types import Severity, VisualWarning
from ._detail import AXES, Axis, choice, number, wire
from ._registry import register_check, register_fix

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_tick_overlap"]


class TickOverlapDetail(TypedDict):
    """``pairs`` neighbouring tick labels of one axis overlap, by up to ``px``.

    ``labels`` counts the axis' drawn labels (both sides); ``rotation`` is
    the angle of the deepest overlapping pair, in degrees.
    """

    axis: Axis
    axes_index: int
    pairs: int
    labels: int
    px: float
    rotation: float


@register_check("TICK_OVERLAP", order=51)
def check_tick_overlap(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Report neighbouring tick labels of one axis that overlap."""
    warnings: list[VisualWarning] = []
    for index, ax in enumerate(fig.axes):
        if getattr(ax, "name", None) != "rectilinear":
            continue
        for which in AXES:
            pairs, labels, deepest, rotation = tick_label_overlaps(
                ax, which, renderer
            )
            if not pairs:
                continue
            warnings.append(
                VisualWarning(
                    severity=Severity.WARNING,
                    check_id="TICK_OVERLAP",
                    message=(
                        f"{which.upper()}-axis[{index}]: {pairs} pair(s) of "
                        f"neighbouring tick labels overlap (up to "
                        f"{deepest:.1f}px, labels at {rotation:g} deg)"
                    ),
                    detail=wire(
                        TickOverlapDetail(
                            axis=which,
                            axes_index=index,
                            pairs=pairs,
                            labels=labels,
                            px=round(deepest, 1),
                            rotation=round(rotation, 1),
                        )
                    ),
                )
            )
    return warnings


@register_fix("TICK_OVERLAP")
def _fix_tick_overlap(warning: VisualWarning) -> list[str]:
    """The layout's choice first, then the author's; never smaller text."""
    axis = choice(warning.detail, "axis", AXES)
    rotation = number(warning.detail, "rotation", 0)
    if axis == "y":
        return [
            "# More rows than the axis holds: a taller canvas, same width\n"
            "fig.set_size_inches(dm.figsize(width, 'tall'))"
        ]
    if rotation:
        out = [
            "# Let the layout choose: drop your rotation, then lay out again\n"
            "ax.tick_params(axis='x', labelrotation=0)\n"
            "dm.simple_layout(fig)"
        ]
    else:
        out = [
            "# Not laid out yet: the layout wraps, then turns, crowded labels\n"
            "dm.simple_layout(fig)"
        ]
    out += [
        "# Many or long category names: horizontal bars\n"
        "fig, ax = plt.subplots(figsize=dm.figsize_for('barh', n_points=n))\n"
        "ax.barh(names, values)",
        "# Or a wider canvas\n"
        "fig.set_size_inches(dm.figsize('17cm', 'standard'))",
    ]
    return out
