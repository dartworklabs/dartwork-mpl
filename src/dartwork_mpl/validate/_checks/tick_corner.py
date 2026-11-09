"""TICK_CORNER_OVERLAP: an x tick label on a y tick label at a plot corner.

When both axes end on a tick, the first bottom label and the lowest left
label meet at the corner (the ``-3`` and ``-3`` of a -3..3 square); a first
category name wide enough reaches under the y labels the same way. Any
corner counts, labels on top or on the right too, and the right labels of
a ``twinx``. ``TICK_OVERLAP`` compares neighbours along one axis and
``CROSS_AXES_OVERLAP`` other plots, so neither sees such a pair. Rectilinear
Axes only; the measure is ``_figure_geometry.corner_tick_overlaps``, which
the layout's ``pad`` step also uses.

``dm.simple_layout`` moves the labels of one axis out by the overlap plus a
hair space (the axis whose labels move less, through its tick pad); what
this check reports after a layout is what is left: both pads set by hand,
or a change the layout took back. The fix grows that pad by hand, on the
Axes that owns the colliding labels (a twin's right labels are the twin's)
and for the ticks they belong to (a minor label's pad is the minor one);
it never hides a label, makes text smaller or moves the axis limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict

from ..._figure_geometry import (
    CORNER_GAP_EM,
    CornerOverlap,
    corner_tick_overlaps,
    same_position_axes,
    tick_pad,
)
from .._types import Severity, VisualWarning
from ._detail import AXES, Axis, choice, number, wire
from ._registry import register_check, register_fix

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure

__all__ = ["check_tick_corner_overlap"]

Which = Literal["major", "minor"]
WHICH: tuple[Which, ...] = ("major", "minor")


class CornerTarget(TypedDict):
    """Labels the fix moves: those of ``which`` ticks of one axis of the
    Axes ``fig.axes[axes_index]``, out to the label pad ``pad`` (pt)."""

    axes_index: int
    axis: Axis
    which: Which
    pad: float


class TickCornerOverlapDetail(TypedDict):
    """``pairs`` x / y tick label pairs of one plot box overlap, by up to ``px``.

    ``axes_index`` is the Axes the pairs were found at; ``corner`` and
    ``x_label`` / ``y_label`` name the deepest pair; ``axis`` is the axis
    whose labels move less to clear every pair and ``pad`` the label pad
    (pt) that clears the deepest pair, of ``which`` ticks of the Axes
    ``fig.axes[owner_index]`` (a twin, for its right labels). ``targets``
    lists every Axes and kind of tick the move needs, each with its pad.
    """

    axes_index: int
    corner: str
    x_label: str
    y_label: str
    pairs: int
    px: float
    axis: Axis
    pad: float
    owner_index: int
    which: Which
    targets: list[CornerTarget]


@register_check("TICK_CORNER_OVERLAP", order=53)
def check_tick_corner_overlap(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Report x tick labels that overlap a y tick label of the same plot box."""
    warnings: list[VisualWarning] = []
    seen: set[int] = set()
    for index, ax in enumerate(fig.axes):
        if id(ax) in seen or not _rectilinear(ax):
            continue
        group = [m for m in same_position_axes(ax) if _rectilinear(m)]
        seen.update(id(m) for m in group)
        pairs = corner_tick_overlaps(group, renderer)
        if not pairs:
            continue
        deepest = max(pairs, key=lambda pair: pair.depth)
        moves = {side: _moves(pairs, side, fig.dpi) for side in AXES}
        # the x labels (down / up) or the y labels (left / right), whichever
        # moves less
        axis_name: Axis = (
            "x" if max(moves["x"].values()) <= max(moves["y"].values()) else "y"
        )
        targets = _targets(fig, axis_name, moves[axis_name])
        owner, which = _owner(deepest, axis_name)
        main = next(
            t
            for t in targets
            if t["axes_index"] == fig.axes.index(owner) and t["which"] == which
        )
        warnings.append(
            VisualWarning(
                severity=Severity.WARNING,
                check_id="TICK_CORNER_OVERLAP",
                message=(
                    f"Axes[{index}]: x tick label "
                    f"{deepest.x_label.get_text()!r} overlaps y tick label "
                    f"{deepest.y_label.get_text()!r} at the {deepest.corner} "
                    f"corner ({len(pairs)} pair(s), up to "
                    f"{deepest.depth:.1f}px)"
                ),
                detail=wire(
                    TickCornerOverlapDetail(
                        axes_index=index,
                        corner=deepest.corner,
                        x_label=deepest.x_label.get_text(),
                        y_label=deepest.y_label.get_text(),
                        pairs=len(pairs),
                        px=round(deepest.depth, 1),
                        axis=axis_name,
                        pad=main["pad"],
                        owner_index=main["axes_index"],
                        which=which,
                        targets=targets,
                    )
                ),
            )
        )
    return warnings


def _rectilinear(ax: Axes) -> bool:
    return ax.get_visible() and getattr(ax, "name", None) == "rectilinear"


def _owner(pair: CornerOverlap, side: Axis) -> tuple[Axes, Which]:
    """The Axes owning ``pair``'s ``side`` label, and its kind of tick."""
    if side == "x":
        return pair.x_axes, "minor" if pair.x_minor else "major"
    return pair.y_axes, "minor" if pair.y_minor else "major"


def _moves(
    pairs: Sequence[CornerOverlap], side: Axis, dpi: float
) -> dict[tuple[Axes, Which], float]:
    """How far (pt) the ``side`` labels of each owning Axes and kind of
    tick move out to clear every pair: the overlap plus ``CORNER_GAP_EM``."""
    to_pt = 72.0 / dpi
    moves: dict[tuple[Axes, Which], float] = {}
    for pair in pairs:
        key = _owner(pair, side)
        depth = pair.down if side == "x" else pair.across
        label = pair.x_label if side == "x" else pair.y_label
        need = depth * to_pt + CORNER_GAP_EM * float(label.get_fontsize())
        moves[key] = max(moves.get(key, 0.0), need)
    return moves


def _targets(
    fig: Figure, side: Axis, moves: dict[tuple[Axes, Which], float]
) -> list[CornerTarget]:
    """One target per owning Axes and kind of tick: its pad now plus the
    move, to 0.1 pt (the hair space in the move absorbs the rounding)."""
    targets: list[CornerTarget] = []
    for (owner, which), need in moves.items():
        axis = owner.xaxis if side == "x" else owner.yaxis
        ticks = axis.majorTicks if which == "major" else axis.minorTicks
        pad = round(tick_pad(ticks[0]) + need, 1)
        targets.append(
            CornerTarget(
                axes_index=fig.axes.index(owner),
                axis=side,
                which=which,
                pad=pad,
            )
        )
    return sorted(targets, key=lambda t: (t["axes_index"], t["which"]))


@register_fix("TICK_CORNER_OVERLAP")
def _fix_tick_corner_overlap(warning: VisualWarning) -> list[str]:
    """The layout's move first, then the same pads by hand, on the Axes and
    ticks that collide; never hide or shrink."""
    lines = []
    raw = warning.detail.get("targets")
    for target in raw if isinstance(raw, list) else []:
        if not isinstance(target, dict):
            continue
        index = number(target, "axes_index", -1)
        axis = choice(target, "axis", AXES)
        which = choice(target, "which", WHICH)
        pad = number(target, "pad", 0)
        if isinstance(index, int) and index >= 0 and axis and which:
            lines.append(
                f"fig.axes[{index}].tick_params("
                f"axis={axis!r}, which={which!r}, pad={pad:g})"
            )
    if not lines:  # a detail without targets: the deepest pair's axis
        axis = choice(warning.detail, "axis", AXES) or "x"
        pad = number(warning.detail, "pad", 0)
        lines.append(f"ax.tick_params(axis={axis!r}, pad={pad:g})")
    return [
        "# The layout moves the labels of one axis out (its tick pad)\n"
        "dm.simple_layout(fig)",
        "# Pads you set stay as set: grow the one that moves less\n"
        + "\n".join(lines),
    ]
