"""Short labels attached to a point, a corner or a horizontal line, and the side candidates they choose from."""

from __future__ import annotations

from contextlib import suppress
from itertools import pairwise
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from matplotlib.container import BarContainer
from matplotlib.figure import Figure
from matplotlib.text import Annotation, Text
from matplotlib.transforms import Bbox, IdentityTransform

from .._figure_geometry import BBOX_ERRORS, same_position_axes
from ..scale import fs, fw
from ._kwarg_guard import AXES_ANNOTATE_PARAMETERS, KwargGuard
from ._legend_fit import measure_ink, points_px
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

#: How much farther than ``offset_pt`` ``annotate_value``'s auto side may
#: move a label that lands on data on every side, in the label's own font
#: sizes: 12 pt for ``report`` value labels (7 pt), 29 pt for
#: ``presentation`` ones (16.9 pt). Past that a label reads as another
#: point's.
_VALUE_REACH_EM = 1.75

#: The step of that search, in points.
_VALUE_REACH_STEP_PT = 1.0


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


# --- keywords these helpers cannot honour (#483) -----------------------------
# Every helper here builds its label with ``ax.annotate(text, xy=, xycoords=,
# xytext=, textcoords=, ha=, va=, fontsize=, ...)``; see each call below.

_TEXT_PROPERTIES = (
    "any matplotlib Text property (color=, rotation=, fontstyle=, ...) or "
    "ax.annotate argument (arrowprops=, annotation_clip=)"
)

_ANNOTATE_ESCAPE = (
    "For a different placement API, write the label yourself with "
    "ax.annotate(text, xy, xytext=..., xycoords=..., textcoords=...)."
)

_FONTSIZE = "Set the size with fontsize=."
_SHORT_ALIGNMENT = (
    "The helper passes ha= and va=, which win over the long spelling; pass "
    "ha= / va= instead."
)


def _point_owned(point: str, offset: str) -> dict[str, str]:
    """Owned spellings shared by the three point helpers, with their fixes."""
    return {
        "xy": point,
        "xycoords": point,
        "xytext": offset,
        "textcoords": offset,
        # ax.annotate replaces any transform (IdentityTransform); placement
        # goes through xycoords / textcoords, which the helper sets.
        "transform": offset,
        "size": _FONTSIZE,
        "horizontalalignment": _SHORT_ALIGNMENT,
        "verticalalignment": _SHORT_ALIGNMENT,
    }


_NO_FMT = (
    "There is no format string: pass the finished text, for example "
    "f'{value:.1f}'. "
)
_NO_FONTDICT = (
    "ax.annotate takes no fontdict: pass the properties directly "
    "(color=, fontsize=). "
)

_ANNOTATE_VALUE_SIDE = "Place the label with side= and offset_pt= (points)."
_ANNOTATE_VALUE_AUTO_ALIGNMENT = (
    "side='auto' sets the alignment for the side it picks; pass side= "
    "('above', 'below', 'left' or 'right') to keep your own."
)
_ANNOTATE_VALUE_GUARD = KwargGuard(
    helper="annotate_value",
    artist=Annotation,
    parameters=AXES_ANNOTATE_PARAMETERS,
    owned=_point_owned(
        "The point is x= and y=, in data coordinates.", _ANNOTATE_VALUE_SIDE
    ),
    takes=f"x=, y=, text, side=, offset_pt=, fontsize= and {_TEXT_PROPERTIES}",
    escape=_ANNOTATE_ESCAPE,
    hints={
        "fmt": _NO_FMT,
        "loc": "Choose the side with side=. ",
        "offset": "Use offset_pt= (points). ",
        "fontdict": _NO_FONTDICT,
    },
)

_ANNOTATE_CORNER_INSET = (
    "Choose the corner with loc= and the inset with inset_pt=."
)
_ANNOTATE_CORNER_AUTO_ALIGNMENT = (
    "avoid_overlap=True sets the alignment for the corner it picks; pass "
    "avoid_overlap=False to keep your own."
)
_ANNOTATE_CORNER_GUARD = KwargGuard(
    helper="annotate_corner",
    artist=Annotation,
    parameters=AXES_ANNOTATE_PARAMETERS,
    owned={
        **_point_owned(_ANNOTATE_CORNER_INSET, _ANNOTATE_CORNER_INSET),
        "x": _ANNOTATE_CORNER_INSET,
        "y": _ANNOTATE_CORNER_INSET,
    },
    takes=(
        "text, loc=, inset_pt=, avoid_overlap=, fontsize= and "
        f"{_TEXT_PROPERTIES}"
    ),
    escape=_ANNOTATE_ESCAPE,
    hints={
        "fmt": _NO_FMT,
        "corner": "Choose the corner with loc=. ",
        "inset": "Use inset_pt= (points). ",
        "fontdict": _NO_FONTDICT,
    },
)

_LABEL_HLINE_PLACE = (
    "Place the label with x= (an end, the centre or an axes fraction), "
    "side= and gap_pt= (points)."
)
_LABEL_HLINE_AUTO_ALIGNMENT = (
    "x='auto' sets the horizontal alignment for the end it picks; pass "
    "x='left', 'right' or 'center' to keep your own."
)
_LABEL_HLINE_GUARD = KwargGuard(
    helper="label_hline",
    artist=Annotation,
    parameters=AXES_ANNOTATE_PARAMETERS,
    owned=_point_owned(
        "The line is y=, in data coordinates; the end is x=.",
        _LABEL_HLINE_PLACE,
    ),
    takes=f"y=, text, x=, side=, gap_pt=, fontsize= and {_TEXT_PROPERTIES}",
    escape=_ANNOTATE_ESCAPE,
    hints={
        "fmt": _NO_FMT,
        "loc": "Choose the end with x= and the side with side=. ",
        "gap": "Use gap_pt= (points). ",
        "offset": "Use gap_pt= (points). ",
        "fontdict": _NO_FONTDICT,
    },
)


def _alignment_owned(names: tuple[str, ...], sentence: str) -> dict[str, str]:
    return dict.fromkeys(names, sentence)


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


def _glyph_margins(text: Text, renderer: RendererBase) -> tuple[float, float]:
    """Return the room under and over ``text``'s glyphs inside its text box, in display px.

    matplotlib gives a line of text the font's ascent and descent, which
    digits do not fill; ``VALUE_LABEL_ON_DATA`` reads a label by its glyphs,
    not by that box. The baseline's place comes from laying the same string
    out at the origin, the glyphs' reach from the renderer's metrics. A
    label that is not one upright line of plain text (rotated, multi-line,
    mathtext, TeX) or cannot be measured has no margins: its whole box
    counts.
    """
    string = text.get_text()
    figure = text.get_figure(root=True)
    if (
        figure is None
        or float(text.get_rotation()) % 360 != 0
        or "\n" in string
        or "$" in string
        or text.get_usetex()
    ):
        return 0.0, 0.0
    prop = text.get_fontproperties()
    probe = Text(
        0, 0, string, fontproperties=prop, transform=IdentityTransform()
    )
    probe.set_figure(figure)
    try:
        line = probe.get_window_extent(renderer)  # [-descent, ascent]
        _width, height, descent = renderer.get_text_width_height_descent(
            string, prop, ismath=False
        )
    except BBOX_ERRORS:
        return 0.0, 0.0
    under = max(0.0, -float(line.y0) - float(descent))
    over = max(0.0, float(line.y1) - float(height - descent))
    return under, over


def _spot_off_data(
    ann: Annotation,
    ax: Axes,
    renderer: RendererBase,
    axes_bbox: Bbox,
    tried: dict[_ValueSide, Bbox],
    best: _ValueSide,
    offset_pt: float,
    text_boxes: list[Bbox],
) -> tuple[_ValueSide, float]:
    """Return the side and distance (points) for a label with no free side.

    ``tried`` maps each side measured at ``offset_pt`` to the label's text
    box there (display px), in the order tried; ``best`` is the
    least-colliding of them, where such a label always went. No side being
    free says little: the obstacle boxes are each segment's bounding box,
    which a sloped line fills only along its diagonal. So the label is
    read here as ``VALUE_LABEL_ON_DATA`` reads it: its glyphs against the
    ink (:func:`~._legend_fit.measure_ink`) of what that check counts as
    data in the plot box, the lines at their width with their markers, the
    scatter points and the bars. A span, a filled band or a mesh under the
    label is not data, here as there.

    The label stays on ``best`` at ``offset_pt`` when its glyphs meet no
    data ink there and its text box is off ``text_boxes`` and the Axes'
    legend. Otherwise it takes the nearest spot that is, the sides of
    ``tried`` at each distance from ``offset_pt`` to ``_VALUE_REACH_EM``
    font sizes farther, the text box inside ``axes_bbox``. With no such
    spot it stays on ``best`` at ``offset_pt``, as before.
    """
    ink = measure_ink(ax, renderer)
    data: set[int] = set()
    for owner in same_position_axes(ax):
        data.update(id(line) for line in owner.get_lines())
        data.update(
            id(coll)
            for coll in owner.collections
            if isinstance(coll, PathCollection)
        )
        data.update(
            id(patch)
            for container in owner.containers
            if isinstance(container, BarContainer)
            for patch in container.patches
        )
    under, over = _glyph_margins(ann, renderer)
    taken = list(text_boxes)
    legend = ax.get_legend()
    if legend is not None and legend.get_visible():
        with suppress(*BBOX_ERRORS):
            taken.append(legend.get_window_extent(renderer))

    def clear(box: Bbox) -> bool:
        """Whether a label at ``box`` is off the other texts and its glyphs off the data."""
        if _collision_area(box, taken) > 0:
            return False
        glyphs = Bbox.from_extents(
            box.x0, box.y0 + under, box.x1, box.y1 - over
        )
        return not ink.met(glyphs, 0.0) & data

    if clear(tried[best]):
        return best, float(offset_pt)
    px_per_pt = points_px(renderer, 1.0)
    reach_pt = _VALUE_REACH_EM * float(ann.get_fontsize())
    for step in range(int(reach_pt / _VALUE_REACH_STEP_PT) + 1):
        farther = step * _VALUE_REACH_STEP_PT
        for side, box in tried.items():
            (dx, dy), _ha, _va = _annotation_side_spec(side, farther)
            moved = box.translated(dx * px_per_pt, dy * px_per_pt)
            if _outside_area(moved, axes_bbox) <= 0 and clear(moved):
                return side, float(offset_pt) + farther
    above = tried.get("above")
    if (
        above is not None
        and _free_above_plot(ax, renderer, axes_bbox, above)
        and clear(above)
    ):
        return "above", float(offset_pt)
    return best, float(offset_pt)


def _free_above_plot(
    ax: Axes, renderer: RendererBase, axes_bbox: Bbox, box: Bbox
) -> bool:
    """Whether a label at ``box``, reaching over the top of the plot, is in free space.

    ``box`` is the label straight above its point (display px). It reaches
    over the top when the point is so near it that the label does not fit
    underneath. That space is free when nothing else is drawn there: no
    top spine, no tick labels on top, no title and no other Axes the label
    would meet, and the label no wider than the plot. ``dm.simple_layout``
    keeps such a label inside the figure, as it does any text beyond the
    plot.
    """
    if box.y1 <= axes_bbox.y1:
        return False
    if box.x0 < axes_bbox.x0 or box.x1 > axes_bbox.x1:
        return False
    family = same_position_axes(ax)
    others: list[Bbox] = []
    for owner in family:
        if owner.spines["top"].get_visible():
            return False
        if any(
            tick.label2.get_visible() and tick.label2.get_text()
            for tick in owner.xaxis.get_major_ticks()
        ):
            return False
        titles = (
            owner.title,
            getattr(owner, "_left_title", None),
            getattr(owner, "_right_title", None),
        )
        for title in titles:
            if title is not None and title.get_visible() and title.get_text():
                with suppress(*BBOX_ERRORS):
                    others.append(title.get_window_extent(renderer))
    figure = ax.get_figure(root=False)
    for other in figure.axes if figure is not None else []:
        if other not in family and other.get_visible():
            with suppress(*BBOX_ERRORS):
                others.append(other.get_window_extent(renderer))
    return _collision_area(box, others) <= 0


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

    When no side is free ``offset_pt`` away (on a sloped line the obstacle
    boxes of its segments leave none), the label takes the least-colliding
    side as long as its glyphs stay off the drawn data there: strokes at
    their width, markers, bars. A label that would sit on data moves to the
    nearest spot straight above, below, right or left of its point, up to
    1.75 font sizes farther than ``offset_pt``, that is off the data, the
    other labels and the legend. A point too near the top of the plot for
    its label to fit underneath, with no such spot inside the plot (a flat
    peak, the line on both sides of it), keeps its label straight above it,
    reaching over the top of the plot, while nothing else is drawn there
    (a top spine, tick labels on top, a title or another Axes in its way);
    ``dm.simple_layout`` keeps it inside the figure. With no spot at all the
    label stays on the least-colliding side. The Axes is measured as it
    stands when this is called: ``dm.simple_layout`` run afterwards resizes the Axes while the
    label's offset stays in points.

    The label is one weight step heavier than the preset's base weight
    (``fontweight=fw(1)``) so a data value reads apart from captions;
    pass ``fontweight`` (or ``weight``) to override. ``fontsize`` defaults
    to one step below the base, ``fs(-1)``, the size every value label
    takes (7 pt under ``report``, 16.9 pt under ``presentation``).
    """
    if fontsize is None:
        fontsize = fs(-1)
    requested = _parse_value_side(side)
    _ANNOTATE_VALUE_GUARD.check(
        kw,
        _alignment_owned(
            ("ha", "va", "horizontalalignment", "verticalalignment"),
            _ANNOTATE_VALUE_AUTO_ALIGNMENT,
        )
        if requested == "auto"
        else None,
    )
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

    text_boxes = _text_bboxes(existing_texts, renderer)
    obstacles = [
        *_line_segment_bboxes(ax),
        *_patch_bboxes(ax),
        *_collection_bboxes(ax),
        *text_boxes,
    ]
    scores: list[tuple[float, _ValueSide]] = []
    tried: dict[_ValueSide, Bbox] = {}

    vertical_sides: tuple[_ValueSide, ...] = ("above", "below")
    for candidate in vertical_sides:
        _apply_annotation_side(ann, candidate, offset_pt)
        bbox = _annotation_extent(ann, fig, renderer)
        if bbox is None:
            continue
        outside = _outside_area(bbox, axes_bbox)
        collision = _collision_area(bbox, obstacles)
        scores.append((outside + collision, candidate))
        tried[candidate] = bbox
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
        tried[candidate] = bbox
        if outside <= 0 and collision <= 0:
            return ann

    if scores:
        _score, best_side = min(scores, key=lambda item: item[0])
        side_taken, distance = _spot_off_data(
            ann,
            ax,
            renderer,
            axes_bbox,
            tried,
            best_side,
            offset_pt,
            text_boxes,
        )
        _apply_annotation_side(ann, side_taken, distance)
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
    _ANNOTATE_CORNER_GUARD.check(
        kw,
        _alignment_owned(
            ("ha", "va", "horizontalalignment", "verticalalignment"),
            _ANNOTATE_CORNER_AUTO_ALIGNMENT,
        )
        if avoid_overlap
        else None,
    )

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
    _LABEL_HLINE_GUARD.check(
        kw,
        _alignment_owned(
            ("ha", "horizontalalignment"), _LABEL_HLINE_AUTO_ALIGNMENT
        )
        if anchor == "auto"
        else None,
    )

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
