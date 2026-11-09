"""TICK_CROWD: too many tick labels for the axis length to comfortably hold.

Measures the room the visible labels need along their axis as rendered (so
it scales with font size, weight, rotation and text length) instead of a
fixed ticks-per-inch density. Turned labels need the spacing at which each
neighbour pair, each label at its own angle, clears, not their whole
axis-aligned extents.

A row that fills the axis is crowded only where some neighbouring pair
stands closer than half an em (``_NEIGHBOUR_CLEARANCE_EM``), the target
``dm.simple_layout`` wraps and turns bottom labels to. Labels at least that
far apart leave an agent nothing to act on however much of the axis they
fill: long names flat 0.52 em apart on the widest slide canvas, or two y
labels over an em apart in a short panel, were reported as filling 105 %
and 102 % of it.
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, Literal, TypedDict

from ..._figure_geometry import (
    drawn_axes,
    label_clearance_px,
    pair_clearance_px,
    pair_gap_px,
)
from .._types import BBOX_ERRORS, Severity, VisualWarning
from ._detail import AXES, Axis, choice, number, wire
from ._registry import register_check, register_fix
from ._tick_utils import iter_view_ticks

if TYPE_CHECKING:
    from matplotlib.axis import XAxis, YAxis
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.text import Text

__all__ = ["check_tick_crowding"]

# Minimum inter-label gap, as a fraction of the summed label footprint,
# below which ticks read as crowded. 0.15 ⇒ labels must leave ≥15% of the
# axis dimension as breathing room collectively.
_TICK_CROWD_MIN_GAP_FRAC = 0.15

# Fallback density (ticks per inch) used only when label extents cannot be
# measured (e.g. a renderer that refuses get_window_extent). The measured
# path is font- and label-length-aware and is preferred.
_TICK_CROWD_FALLBACK_DENSITY = 4.0

# Room (ems of the pair's larger font) neighbouring labels need for a row
# that fills its axis still to read as separate labels: the layout's own
# target (``layout._fit_labels._TARGET_EM``), which wraps and turns bottom
# labels closer than this.
_NEIGHBOUR_CLEARANCE_EM = 0.5


LabelKind = Literal["names", "numbers"]
_LABEL_KINDS: tuple[LabelKind, ...] = ("names", "numbers")


class TickCrowdDetail(TypedDict):
    """``count`` tick labels crowd one axis; ``occupancy`` when measured.

    ``label_kind`` is ``"names"`` when the labels are fixed strings, one per
    position (``set_xticks(positions, labels)``, ``set_xticklabels``,
    categories as from ``ax.bar(names, ...)``), which a locator would drop
    or misplace; ``"numbers"`` when a formatter writes them from the
    ticks a locator places.
    """

    axis: Axis
    axes_index: int
    count: int
    occupancy: float | None
    label_kind: LabelKind


def _row_need_px(
    row: list[Text], renderer: RendererBase, which: Literal["x", "y"]
) -> float:
    """The length one row of labels needs along its axis.

    The row in order along the axis: every neighbour pair's centre distance
    at which the two clear (each at its own angle,
    :func:`~dartwork_mpl._figure_geometry.pair_clearance_px`), plus half of
    each end label's own room. Upright labels sum to their widths along x
    and heights along y.
    """
    if not row:
        return 0.0

    def centre(label: Text) -> float:
        box = label.get_window_extent(renderer)
        return float((box.x0 + box.x1) if which == "x" else (box.y0 + box.y1))

    ordered = sorted(row, key=centre)
    need = 0.5 * (
        label_clearance_px(ordered[0], renderer, which)
        + label_clearance_px(ordered[-1], renderer, which)
    )
    for a, b in pairwise(ordered):
        need += pair_clearance_px(a, b, renderer, which)
    return need


def _label_kind(axis: XAxis | YAxis) -> LabelKind:
    """``"names"`` for fixed strings, one per position, else ``"numbers"``."""
    from matplotlib.category import StrCategoryFormatter
    from matplotlib.ticker import FixedFormatter

    formatter = axis.get_major_formatter()
    if isinstance(formatter, (FixedFormatter, StrCategoryFormatter)):
        return "names"
    return "numbers"


def _closest_gap_em(
    rows: list[list[Text]],
    renderer: RendererBase,
    which: Literal["x", "y"],
    dpi: float,
) -> float | None:
    """The least room between neighbouring labels of any row (ems of the
    pair's larger font): each row in order along the axis, each pair the
    gap :func:`~dartwork_mpl._figure_geometry.pair_gap_px` finds between
    the rectangles they fill, never more than the true one. ``None`` when
    no row has two labels."""

    def centre(label: Text) -> float:
        box = label.get_window_extent(renderer)
        return float((box.x0 + box.x1) if which == "x" else (box.y0 + box.y1))

    least: float | None = None
    for row in rows:
        for a, b in pairwise(sorted(row, key=centre)):
            size = max(float(a.get_fontsize()), float(b.get_fontsize()))
            em = size * dpi / 72.0
            gap = pair_gap_px(a, b, renderer) / em
            least = gap if least is None else min(least, gap)
    return least


def _tick_crowd_for_axis(
    rows: list[list[Text]],
    axis_span_px: float,
    *,
    horizontal: bool,
    renderer: RendererBase,
) -> tuple[float | None, bool] | None:
    """Return ``(occupancy, measured)`` for one axis, or ``None`` to skip.

    ``occupancy`` is the fraction of the axis dimension consumed by the
    tick labels plus the required minimum gap. ``occupancy > 1`` means the
    labels (at their *actual* rendered size — font, weight, rotation and
    text length all baked in) cannot fit without touching, i.e. crowded.
    ``rows`` are the labels on each side of the axis (bottom / top or left
    / right); each row counts the length it needs (:func:`_row_need_px`):
    its labels' widths along x and heights along y when upright, less than
    their axis-aligned extents when turned alike, more when neighbours turn
    opposite ways and cross.

    Falls back to a fixed ticks-per-inch density only when a label extent
    cannot be measured, so the common path stays font-aware.
    """
    if axis_span_px <= 0 or sum(len(row) for row in rows) < 2:
        return None
    which: Literal["x", "y"] = "x" if horizontal else "y"
    try:
        need = sum(_row_need_px(row, renderer, which) for row in rows)
    except BBOX_ERRORS:
        # Unmeasurable → density fallback (dpi folded into axis_span_px by caller)
        return None, False
    footprint = need * (1.0 + _TICK_CROWD_MIN_GAP_FRAC)
    return footprint / axis_span_px, True


@register_check("TICK_CROWD", order=50)
def check_tick_crowding(
    fig: Figure, renderer: RendererBase
) -> list[VisualWarning]:
    """Detect overcrowded tick labels on axes."""
    warnings: list[VisualWarning] = []
    dpi = fig.get_dpi()

    for i, ax in drawn_axes(fig):
        # A row of labels along a straight axis: a polar theta ring or a 3D
        # axis has no width or height to share out.
        if getattr(ax, "name", None) != "rectilinear":
            continue
        try:
            ax_ext = ax.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue

        axis_specs: tuple[tuple[Literal["x", "y"], float, bool], ...] = (
            ("x", ax_ext.width, True),
            ("y", ax_ext.height, False),
        )
        for axis_name, span_px, horizontal in axis_specs:
            ticks = list(iter_view_ticks(ax, axis_name, renderer))
            # Bottom / left labels and top / right ones are separate rows.
            target = ax.xaxis if axis_name == "x" else ax.yaxis
            first = {id(tick.label1) for tick in target.get_major_ticks()}
            rows = [
                [t for t in ticks if id(t) in first],
                [t for t in ticks if id(t) not in first],
            ]
            result = _tick_crowd_for_axis(
                rows, span_px, horizontal=horizontal, renderer=renderer
            )
            crowded = False
            occupancy: float | None = None
            measured = False
            closest: float | None = None
            if result is not None:
                occupancy, measured = result
                crowded = occupancy is not None and occupancy > 1.0
            if crowded:
                # Filling the axis is crowding only where neighbours stand
                # closer than half an em. A row with no pair, or one that
                # cannot be measured, keeps the occupancy's verdict.
                try:
                    closest = _closest_gap_em(rows, renderer, axis_name, dpi)
                except BBOX_ERRORS:
                    closest = None
                if closest is not None and closest >= _NEIGHBOUR_CLEARANCE_EM:
                    crowded = False
            if not measured and len(ticks) > 1:
                # Density fallback (extents unmeasurable).
                span_in = span_px / dpi
                if span_in > 0:
                    density = len(ticks) / span_in
                    crowded = density > _TICK_CROWD_FALLBACK_DENSITY

            if not crowded:
                continue

            span_in = span_px / dpi
            if measured and occupancy is not None:
                detail_extra = f"labels fill {occupancy:.0%} of the axis"
                if closest is not None and closest < 0:
                    detail_extra += f"; neighbours overlap by {-closest:.2f} em"
                elif closest is not None:
                    detail_extra += (
                        f"; closest neighbours {closest:.2f} em apart, "
                        f"under {_NEIGHBOUR_CLEARANCE_EM:g} em"
                    )
            else:
                detail_extra = (
                    f"density {len(ticks) / span_in:.1f} ticks/in "
                    f"> {_TICK_CROWD_FALLBACK_DENSITY:.1f}"
                )
            warnings.append(
                VisualWarning(
                    severity=Severity.INFO,
                    check_id="TICK_CROWD",
                    message=(
                        f"{axis_name.upper()}-axis[{i}] has {len(ticks)} "
                        f"ticks in {span_in:.2f}in ({detail_extra})"
                    ),
                    detail=wire(
                        TickCrowdDetail(
                            axis=axis_name,
                            axes_index=i,
                            count=len(ticks),
                            occupancy=(
                                round(occupancy, 2)
                                if measured and occupancy is not None
                                else None
                            ),
                            label_kind=_label_kind(target),
                        )
                    ),
                )
            )

    return warnings


_NAME_FIXES_X = [
    "# Let the layout choose: drop a rotation you set, then lay out again\n"
    "# (it wraps, then turns, names closer than half an em)\n"
    "ax.tick_params(axis='x', labelrotation=0)\n"
    "dm.simple_layout(fig)",
    "# A canvas of the preset's own widths at which the names stand flat\n"
    "names = [t.get_text() for t in ax.get_xticklabels()]\n"
    "fig.set_size_inches(dm.figsize_for(n_points=len(names), labels=names))\n"
    "dm.simple_layout(fig)",
    "# Or horizontal bars: the names read along y (values: your bar values)\n"
    "names = [t.get_text() for t in ax.get_xticklabels()]\n"
    "fig, ax = plt.subplots(figsize=dm.figsize_for('barh', n_points=len(names)))\n"
    "ax.barh(names, values)\n"
    "dm.simple_layout(fig)",
    "# Or fewer categories: group the smallest into 'Other', or split them\n"
    "# across panels, before plotting",
]
_NAME_FIXES_Y = [
    "# More names than the axis holds: a taller canvas, same width\n"
    "fig.set_size_inches(dm.figsize(f'{fig.get_figwidth()}in', 'tall'))\n"
    "dm.simple_layout(fig)",
    "# Or fewer categories: group the smallest into 'Other', or split them\n"
    "# across panels, before plotting",
]


@register_fix("TICK_CROWD")
def _fix_tick_crowd(warning: VisualWarning) -> list[str]:
    """Names: the layout, a canvas sized for them, horizontal bars, fewer
    categories; never a locator (it drops or misplaces fixed names) nor a
    turn (the layout turns only what would not clear). Numbers: fewer
    ticks, as before; a warning without ``label_kind`` reads as numbers."""
    suggestions: list[str] = []
    axis = choice(warning.detail, "axis", AXES)
    count = number(warning.detail, "count", 0)
    if choice(warning.detail, "label_kind", _LABEL_KINDS) == "names":
        return list(_NAME_FIXES_Y if axis == "y" else _NAME_FIXES_X)
    if axis == "x":
        suggestions.append(
            f"# Reduce x-ticks\nax.xaxis.set_major_locator(plt.MaxNLocator(nbins={count // 2}))"
        )
        suggestions.append(
            "# Rotate labels\nax.tick_params(axis='x', rotation=45)"
        )
    else:
        suggestions.append(
            f"# Reduce y-ticks\nax.yaxis.set_major_locator(plt.MaxNLocator(nbins={count // 2}))"
        )
    return suggestions
