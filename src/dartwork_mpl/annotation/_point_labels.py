"""Short labels attached to a point, a corner or a horizontal line, and the side candidates they choose from."""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from .._figure_geometry import BBOX_ERRORS
from ..scale import fs, fw
from ._placement_geometry import (
    _collection_bboxes,
    _collision_area,
    _line_segment_bboxes,
    _outside_area,
    _patch_bboxes,
    _renderer_for_axes,
    _text_bboxes,
)

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import SubFigure


HorizontalAlign = Literal["left", "center", "right"]

VerticalAlign = Literal[
    "bottom", "baseline", "center", "center_baseline", "top"
]

# Internal vocabularies. The public parameters stay ``str``; each entry point
# parses its string once into one of these and the helpers take only them.
_ValueSide = Literal["above", "below", "right", "left"]

_Corner = Literal["upper left", "upper right", "lower left", "lower right"]

_HlineSide = Literal["above", "below"]

_HlineAnchor = Literal["left", "center", "right"]


def _parse_value_side(side: str) -> _ValueSide | Literal["auto"]:
    """Return ``annotate_value``'s ``side`` as its literal; raise ``ValueError`` if unknown."""
    match side:
        case "auto" | "above" | "below" | "left" | "right":
            return side
        case _:
            raise ValueError(
                "side must be 'auto', 'above', 'below', 'left', or 'right'"
            )


def _parse_corner(loc: str) -> _Corner:
    """Return ``annotate_corner``'s ``loc`` as its literal; raise ``ValueError`` if unknown."""
    match loc:
        case "upper left" | "upper right" | "lower left" | "lower right":
            return loc
        case _:
            raise ValueError(
                "loc must be 'upper left', 'upper right', 'lower left', "
                "or 'lower right'"
            )


def _parse_hline_side(side: str) -> _HlineSide:
    """Return ``label_hline``'s ``side`` as its literal; raise ``ValueError`` if unknown."""
    match side:
        case "above" | "below":
            return side
        case _:
            raise ValueError("side must be 'above' or 'below'")


def _parse_hline_x(x: str | float) -> _HlineAnchor | Literal["auto"] | float:
    """Return ``label_hline``'s ``x`` as an anchor literal, ``"auto"`` or an axes fraction.

    Raises ``ValueError`` for any other string.
    """
    if not isinstance(x, str):
        return float(x)
    match x:
        case "auto" | "left" | "center" | "right":
            return x
        case _:
            raise ValueError(
                "x must be 'auto', 'left', 'center', 'right', or a float"
            )


def _set_annotation_offset(text: Text, offset: tuple[float, float]) -> None:
    text.set_position(offset)
    if hasattr(text, "xyann"):
        text.xyann = offset


def _annotation_side_spec(
    side: _ValueSide, offset_pt: float
) -> tuple[tuple[float, float], HorizontalAlign, VerticalAlign]:
    """Return the point offset and alignment that put a label on ``side`` of its point."""
    offset = float(offset_pt)
    match side:
        case "above":
            return (0.0, offset), "center", "bottom"
        case "below":
            return (0.0, -offset), "center", "top"
        case "right":
            return (offset, 0.0), "left", "center"
        case "left":
            return (-offset, 0.0), "right", "center"


def _apply_annotation_side(
    text: Text, side: _ValueSide, offset_pt: float
) -> None:
    """Move ``text`` to ``side`` of its anchor point, ``offset_pt`` points away."""
    offset, ha, va = _annotation_side_spec(side, offset_pt)
    text.set_horizontalalignment(ha)
    text.set_verticalalignment(va)
    _set_annotation_offset(text, offset)


def _annotation_extent(
    text: Text, fig: Figure | SubFigure, renderer: RendererBase
) -> Bbox | None:
    fig.canvas.draw()
    try:
        return text.get_window_extent(renderer)
    except BBOX_ERRORS:
        return None


def annotate_value(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    *,
    side: str = "auto",
    offset_pt: float = 3.0,
    fontsize: float | None = None,
    **kw: Any,
) -> Text:
    """Annotate one data value with a compact point-offset label.

    ``side="auto"`` evaluates above, below, right, then left. Above/below are
    used only when the rendered label stays inside the axes spine and avoids
    same-axes data/text. If vertical placement would leave the spine region,
    the label moves horizontally from the data point instead of flipping to the
    opposite vertical side. Explicit ``side="left"`` / ``"right"`` is
    supported, including ``arrowprops``; all offsets are single-axis point
    offsets so arrows remain straight horizontal or vertical connectors.

    The label is one weight step heavier than the preset's base weight
    (``fontweight=fw(1)``) so a data value reads apart from captions;
    pass ``fontweight`` (or ``weight``) to override. ``fontsize`` defaults
    to one step below the base, ``fs(-1)``, the size every value label
    takes (7 pt under ``report``, 16.9 pt under ``presentation``).
    """
    if fontsize is None:
        fontsize = fs(-1)
    requested = _parse_value_side(side)
    if "fontweight" not in kw and "weight" not in kw:
        kw["fontweight"] = fw(1)

    existing_texts = list(ax.texts)
    initial_side: _ValueSide = "above" if requested == "auto" else requested
    offset, ha, va = _annotation_side_spec(initial_side, offset_pt)

    ann = ax.annotate(
        text,
        xy=(x, y),
        xycoords="data",
        xytext=offset,
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", va),
        fontsize=fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )

    if requested != "auto":
        return ann

    fig, renderer = _renderer_for_axes(ax)
    try:
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return ann

    obstacles = [
        *_line_segment_bboxes(ax),
        *_patch_bboxes(ax),
        *_collection_bboxes(ax),
        *_text_bboxes(existing_texts, renderer),
    ]
    scores: list[tuple[float, _ValueSide]] = []

    vertical_sides: tuple[_ValueSide, ...] = ("above", "below")
    for candidate in vertical_sides:
        _apply_annotation_side(ann, candidate, offset_pt)
        bbox = _annotation_extent(ann, fig, renderer)
        if bbox is None:
            continue
        outside = _outside_area(bbox, axes_bbox)
        collision = _collision_area(bbox, obstacles)
        scores.append((outside + collision, candidate))
        if outside <= 0 and collision <= 0:
            return ann
        if outside > 0:
            break

    horizontal_sides: tuple[_ValueSide, ...] = ("right", "left")
    for candidate in horizontal_sides:
        _apply_annotation_side(ann, candidate, offset_pt)
        bbox = _annotation_extent(ann, fig, renderer)
        if bbox is None:
            continue
        outside = _outside_area(bbox, axes_bbox)
        collision = _collision_area(bbox, obstacles)
        scores.append((outside + collision, candidate))
        if outside <= 0 and collision <= 0:
            return ann

    if scores:
        _score, best_side = min(scores, key=lambda item: item[0])
        _apply_annotation_side(ann, best_side, offset_pt)
        fig.canvas.draw()

    return ann


_CORNER_SPECS: dict[
    _Corner,
    tuple[
        tuple[float, float], tuple[float, float], HorizontalAlign, VerticalAlign
    ],
] = {
    "upper left": ((0.0, 1.0), (1.0, -1.0), "left", "top"),
    "upper right": ((1.0, 1.0), (-1.0, -1.0), "right", "top"),
    "lower left": ((0.0, 0.0), (1.0, 1.0), "left", "bottom"),
    "lower right": ((1.0, 0.0), (-1.0, 1.0), "right", "bottom"),
}


def _corner_order(loc: _Corner) -> list[_Corner]:
    """Return the corners to try: ``loc`` first, then the rest in reading order."""
    order: list[_Corner] = [
        "upper left",
        "upper right",
        "lower left",
        "lower right",
    ]
    if loc == "upper left":
        return order
    return [loc, *[candidate for candidate in order if candidate != loc]]


def _apply_corner(text: Text, loc: _Corner, inset_pt: float) -> None:
    """Align ``text`` to corner ``loc`` and inset it ``inset_pt`` points inward."""
    _anchor, offset_direction, ha, va = _CORNER_SPECS[loc]
    text.set_horizontalalignment(ha)
    text.set_verticalalignment(va)
    _set_annotation_offset(
        text,
        (
            offset_direction[0] * float(inset_pt),
            offset_direction[1] * float(inset_pt),
        ),
    )


def annotate_corner(
    ax: Axes,
    text: str,
    *,
    loc: str = "upper left",
    inset_pt: float = 3.0,
    avoid_overlap: bool = True,
    fontsize: float | None = None,
    **kw: Any,
) -> Text:
    """Place narrative text tightly inside an axes corner.

    The anchor is in axes-fraction coordinates with a point inset toward the
    plot interior, so multi-line text stays attached to the selected spine
    corner. With ``avoid_overlap=True`` the helper measures rendered data and
    existing text, then tries corners in upper-left, upper-right, lower-left,
    lower-right order (starting with an explicit ``loc`` when provided).
    """
    if fontsize is None:
        fontsize = fs(-2)
    corner = _parse_corner(loc)

    existing_texts = list(ax.texts)
    anchor, offset_direction, ha, va = _CORNER_SPECS[corner]
    ann = ax.annotate(
        text,
        xy=anchor,
        xycoords="axes fraction",
        xytext=(
            offset_direction[0] * float(inset_pt),
            offset_direction[1] * float(inset_pt),
        ),
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", va),
        fontsize=fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )
    if not avoid_overlap:
        return ann

    fig, renderer = _renderer_for_axes(ax)
    try:
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return ann
    obstacles = [
        *_line_segment_bboxes(ax),
        *_patch_bboxes(ax),
        *_collection_bboxes(ax),
        *_text_bboxes(existing_texts, renderer),
    ]

    scores: list[tuple[float, _Corner]] = []
    for candidate in _corner_order(corner):
        anchor, _offset_direction, _ha, _va = _CORNER_SPECS[candidate]
        ann.xy = anchor
        _apply_corner(ann, candidate, inset_pt)
        bbox = _annotation_extent(ann, fig, renderer)
        if bbox is None:
            continue
        outside = _outside_area(bbox, axes_bbox)
        collision = _collision_area(bbox, obstacles)
        scores.append((outside + collision, candidate))
        if outside <= 0 and collision <= 0:
            return ann

    if scores:
        _score, best_loc = min(scores, key=lambda item: item[0])
        anchor, _offset_direction, _ha, _va = _CORNER_SPECS[best_loc]
        ann.xy = anchor
        _apply_corner(ann, best_loc, inset_pt)
        fig.canvas.draw()
    return ann


def _display_x_to_data(ax: Axes, display_x: float, y: float) -> float:
    display_y = ax.transData.transform((ax.get_xlim()[0], y))[1]
    return float(ax.transData.inverted().transform((display_x, display_y))[0])


def _axes_fraction_to_data_x(ax: Axes, fraction: float, y: float) -> float:
    fig, renderer = _renderer_for_axes(ax)
    del fig
    axes_bbox = ax.get_window_extent(renderer)
    display_x = axes_bbox.x0 + axes_bbox.width * float(fraction)
    return _display_x_to_data(ax, display_x, y)


def _visible_hline_span(ax: Axes, y: float) -> tuple[float, float]:
    fig, renderer = _renderer_for_axes(ax)
    del fig
    axes_bbox = ax.get_window_extent(renderer)
    target_y = ax.transData.transform((ax.get_xlim()[0], y))[1]
    display_xs: list[float] = []
    tolerance = 2.0

    for line in ax.lines:
        if not line.get_visible():
            continue
        xy = np.asarray(line.get_xydata(), dtype=float)
        if len(xy) < 2:
            continue
        try:
            points = line.get_transform().transform(xy)
        except (RuntimeError, ValueError, AttributeError):
            continue
        points = points[np.isfinite(points).all(axis=1)]
        for left, right in pairwise(points):
            if (
                abs(float(left[1]) - target_y) > tolerance
                or abs(float(right[1]) - target_y) > tolerance
            ):
                continue
            x0 = max(min(float(left[0]), float(right[0])), axes_bbox.x0)
            x1 = min(max(float(left[0]), float(right[0])), axes_bbox.x1)
            if x1 >= x0:
                display_xs.extend([x0, x1])

    if not display_xs:
        return (
            _display_x_to_data(ax, axes_bbox.x0, y),
            _display_x_to_data(ax, axes_bbox.x1, y),
        )

    left_data = _display_x_to_data(ax, min(display_xs), y)
    right_data = _display_x_to_data(ax, max(display_xs), y)
    return (left_data, right_data)


def _hline_x_spec(
    ax: Axes, y: float, x: _HlineAnchor | float
) -> tuple[float, HorizontalAlign]:
    """Return the data x and alignment for a label at anchor ``x`` of the line at ``y``.

    A float ``x`` is an axes fraction; an anchor attaches to the visible
    line's left end, right end or midpoint.
    """
    left, right = _visible_hline_span(ax, y)
    match x:
        case "left":
            return left, "left"
        case "right":
            return right, "right"
        case "center":
            return (left + right) / 2.0, "center"
        case float():
            return _axes_fraction_to_data_x(ax, x, y), "center"


def label_hline(
    ax: Axes,
    y: float,
    text: str,
    *,
    x: str | float = "right",
    side: str = "above",
    gap_pt: float = 2.0,
    fontsize: float | None = None,
    **kw: Any,
) -> Text:
    """Place a label tightly against a horizontal reference line.

    ``x="left"`` / ``"right"`` attaches to the visible horizontal line
    endpoint inside the axes; ``"center"`` is available when central placement
    is intentional. ``x="auto"`` measures both endpoints and chooses the less
    obstructed side. Float ``x`` values keep the legacy axes-fraction meaning.
    Vertical movement uses a single-axis point offset so the label stays
    attached to the reference line rather than drifting diagonally.
    """
    if fontsize is None:
        fontsize = fs(-2)
    line_side = _parse_hline_side(side)
    anchor = _parse_hline_x(x)

    va = "bottom" if line_side == "above" else "top"
    offset = (0.0, float(gap_pt) if line_side == "above" else -float(gap_pt))
    existing_texts = list(ax.texts)
    x_pos, ha = _hline_x_spec(ax, y, "right" if anchor == "auto" else anchor)
    ann = ax.annotate(
        text,
        xy=(x_pos, y),
        xycoords="data",
        xytext=offset,
        textcoords="offset points",
        ha=kw.pop("ha", ha),
        va=kw.pop("va", va),
        fontsize=fontsize,
        annotation_clip=kw.pop("annotation_clip", False),
        **kw,
    )
    if anchor != "auto":
        return ann

    fig, renderer = _renderer_for_axes(ax)
    try:
        axes_bbox = ax.get_window_extent(renderer)
    except BBOX_ERRORS:
        return ann
    obstacles = [
        *_patch_bboxes(ax),
        *_collection_bboxes(ax),
        *_text_bboxes(existing_texts, renderer),
    ]
    scores: list[tuple[float, _HlineAnchor]] = []
    end_anchors: tuple[_HlineAnchor, ...] = ("right", "left")
    for candidate in end_anchors:
        x_pos, ha = _hline_x_spec(ax, y, candidate)
        ann.xy = (x_pos, y)
        ann.set_horizontalalignment(ha)
        bbox = _annotation_extent(ann, fig, renderer)
        if bbox is None:
            continue
        score = _outside_area(bbox, axes_bbox) + _collision_area(
            bbox, obstacles
        )
        scores.append((score, candidate))
        if score <= 0:
            return ann

    if scores:
        _score, best_side = min(scores, key=lambda item: item[0])
        x_pos, ha = _hline_x_spec(ax, y, best_side)
        ann.xy = (x_pos, y)
        ann.set_horizontalalignment(ha)
        fig.canvas.draw()
    return ann
